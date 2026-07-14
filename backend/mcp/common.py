"""
Common utilities and classes for UNHCR MCP Server

This module contains shared classes, helper functions, and constants used by both
the server and individual tool implementations.
"""

from __future__ import annotations

import logging
import os
import re
from dataclasses import dataclass
from datetime import datetime
from functools import lru_cache
from pathlib import Path
from typing import Any, Optional, Union

import duckdb
import numpy as np
import requests
from sentence_transformers import SentenceTransformer

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None

logger = logging.getLogger(__name__)

# Vector database configuration
VECTOR_DB_PATH = os.getenv(
    "UNHCR_VECTOR_DB",
    "/app/data/vector_store/unhcr_reports.duckdb",
)

DEFAULT_RAG_EMBED_MODEL = os.getenv(
    "UNHCR_RAG_EMBED_MODEL",
    "BAAI/bge-small-en-v1.5",
)

DEFAULT_RAG_TOP_K = int(os.getenv("UNHCR_RAG_TOP_K", "5"))

DEFAULT_RAG_FETCH_K = int(os.getenv("UNHCR_RAG_FETCH_K", "20"))

DEFAULT_RAG_RERANK_MODEL = os.getenv(
    "UNHCR_RAG_RERANK_MODEL",
    "cross-encoder/ms-marco-MiniLM-L-6-v2",
)

DEFAULT_RAG_DEVICE = os.getenv("UNHCR_RAG_DEVICE", None)

TABLE_CHUNKS = "report_chunks"
TABLE_METADATA = "index_metadata"


# Class for RAG retrieval from vector store
@dataclass
class RetrievedChunk:
    chunk_id: str
    title: Optional[str]
    year: Optional[str]
    report_type: Optional[str]
    source_url: Optional[str]
    markdown_path: Optional[str]
    section_path: Optional[str]
    chunk_index: int
    distance: float
    rerank_score: Optional[float]
    text: str

    @property
    def similarity(self) -> float:
        # For cosine distance, similarity ≈ 1 - distance.
        return 1.0 - float(self.distance)


def summarize_retrieved_context_for_story(context_block: str, max_chars: int = 1200) -> str:
    """
    Lightweight compression of retrieved RAG context for deterministic story generation.

    This is not an LLM summary. It extracts the most usable sentences from the
    retrieved context block.
    """
    text = re.sub(r"\s+", " ", context_block).strip()

    # Remove verbose metadata lines but keep source content.
    text = re.sub(r"\[Retrieved context \d+\]", " ", text)
    text = re.sub(r"Source: .*? URL: .*? ", " ", text)

    sentences = re.split(r"(?<=[.!?])\s+", text)

    useful = []
    for sentence in sentences:
        s = sentence.strip()

        if len(s) < 40:
            continue

        if s.lower().startswith(("source:", "section:", "similarity:", "url:")):
            continue

        useful.append(s)

        if sum(len(x) for x in useful) > max_chars:
            break

    summary = " ".join(useful).strip()

    if len(summary) > max_chars:
        summary = summary[: max_chars - 3] + "..."

    return summary


def _vector_literal(vector: list[float], dim: int) -> str:
    values = ", ".join(f"{x:.8f}" for x in vector)
    return f"[{values}]::FLOAT[{dim}]"


def _get_index_metadata(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    try:
        rows = conn.execute(f"SELECT key, value FROM {TABLE_METADATA};").fetchall()
        return {key: value for key, value in rows}
    except Exception:
        return {}


@lru_cache(maxsize=2)
def _load_embedding_model(model_name: str, device: Optional[str]) -> SentenceTransformer:
    kwargs: dict[str, Any] = {}
    if device:
        kwargs["device"] = device

    logger.info("Loading embedding model: %s", model_name)
    return SentenceTransformer(model_name, **kwargs)


@lru_cache(maxsize=2)
def _load_cross_encoder(model_name: str, device: Optional[str]):
    if CrossEncoder is None:
        raise RuntimeError(
            "CrossEncoder is unavailable. Install sentence-transformers with torch/transformers support."
        )

    kwargs: dict[str, Any] = {}
    if device:
        kwargs["device"] = device

    logger.info("Loading cross-encoder reranker: %s", model_name)
    return CrossEncoder(model_name, **kwargs)


# Class for RAG retrieval from vector store
class UNHCRVectorRetriever:
    """
    Local RAG retriever over the DuckDB vector store built from UNHCR reports.

    Expected DB schema is produced by scripts/build_reports_vector_index.py.
    """

    def __init__(
        self,
        db_path: str = VECTOR_DB_PATH,
        embedding_model: str = DEFAULT_RAG_EMBED_MODEL,
        device: Optional[str] = DEFAULT_RAG_DEVICE,
    ) -> None:
        self.db_path = Path(db_path)
        self.embedding_model_name = embedding_model
        self.device = device

    def available(self) -> bool:
        return self.db_path.exists()

    def _connect(self) -> duckdb.DuckDBPyConnection:
        if not self.db_path.exists():
            raise FileNotFoundError(f"Vector DB not found: {self.db_path}")
        return duckdb.connect(str(self.db_path))

    def _model_name_from_db(self, conn: duckdb.DuckDBPyConnection) -> str:
        metadata = _get_index_metadata(conn)
        return metadata.get("model_name") or self.embedding_model_name

    def _embedding_dim_from_db(self, conn: duckdb.DuckDBPyConnection) -> int:
        metadata = _get_index_metadata(conn)
        dim = int(metadata.get("embedding_dim", "0"))
        if dim <= 0:
            raise RuntimeError("Could not determine embedding dimension from index_metadata.")
        return dim

    def formulate_query(
        self,
        user_request: str,
        data_summary: Optional[str] = None,
        topics: Optional[list[str]] = None,
    ) -> str:
        """
        Build a retrieval query from the MCP tool request.
        Keep it compact but semantically rich.
        """
        import re
        
        parts = [user_request.strip()]

        if data_summary:
            # Sanitize data_summary to remove markdown tables and non-text content
            # This prevents embedding model errors
            sanitized_summary = data_summary
            
            # Remove markdown table patterns
            sanitized_summary = re.sub(r'\|.*?\|\n', '', sanitized_summary)
            sanitized_summary = re.sub(r'\|[-:\s]+\|', '', sanitized_summary)
            sanitized_summary = re.sub(r'^\|[^\n]*\n', '', sanitized_summary, flags=re.MULTILINE)
            sanitized_summary = re.sub(r'\|', '', sanitized_summary)
            sanitized_summary = re.sub(r'\s+', ' ', sanitized_summary).strip()
            
            # Only add if we have meaningful content after sanitization
            if sanitized_summary and len(sanitized_summary.strip()) > 0:
                parts.append(f"Data summary: {sanitized_summary[:200]}")  # Limit to 200 chars

        if topics:
            clean_topics = [t.strip() for t in topics if t and t.strip()]
            if clean_topics:
                parts.append("Topics: " + ", ".join(clean_topics))

        return "\n".join(parts)

    def retrieve(
        self,
        query: str,
        top_k: int = DEFAULT_RAG_TOP_K,
        fetch_k: int = DEFAULT_RAG_FETCH_K,
        year: Optional[str] = None,
        report_type: Optional[str] = None,
        section_contains: Optional[str] = None,
        exclude_figures_tables: bool = False,
        rerank: bool = False,
        rerank_model: str = DEFAULT_RAG_RERANK_MODEL,
    ) -> list[RetrievedChunk]:
        """
        Retrieve top-k semantically similar chunks.

        If rerank=True, fetches fetch_k candidates and re-ranks them with a cross-encoder.
        """
        if not query or not query.strip():
            return []

        conn = self._connect()

        try:
            model_name = self._model_name_from_db(conn)
            embedding_dim = self._embedding_dim_from_db(conn)
            model = _load_embedding_model(model_name, self.device)

            try:
                query_embedding = model.encode(
                    [query],
                    normalize_embeddings=True,
                    convert_to_numpy=True,
                ).astype("float32")[0]
            except (ValueError, TypeError, AttributeError) as e:
                # Handle cases where the query contains non-encodable content
                # (e.g., markdown tables, invalid characters)
                logger.warning(f"Embedding failed for query, retrying with sanitized version: {e}")
                # Clean the query by removing problematic characters
                import re
                sanitized_query = re.sub(r'[^\w\s.,;:!?\'-]', ' ', query)
                sanitized_query = re.sub(r'\s+', ' ', sanitized_query).strip()
                if sanitized_query and len(sanitized_query) > 0:
                    query_embedding = model.encode(
                        [sanitized_query],
                        normalize_embeddings=True,
                        convert_to_numpy=True,
                    ).astype("float32")[0]
                else:
                    # If sanitization results in empty string, return empty results
                    logger.warning(f"Query could not be sanitized for embedding: {query[:100]}")
                    return []

            if len(query_embedding) != embedding_dim:
                raise ValueError(
                    f"Query embedding dim {len(query_embedding)} does not match DB dim {embedding_dim}"
                )

            qvec = _vector_literal(query_embedding.tolist(), embedding_dim)

            where_clauses: list[str] = []
            params: list[Any] = []

            if year:
                where_clauses.append("year = ?")
                params.append(str(year))

            if report_type:
                where_clauses.append("lower(report_type) = lower(?)")
                params.append(report_type)

            if section_contains:
                where_clauses.append("lower(section_path) LIKE lower(?)")
                params.append(f"%{section_contains}%")

            if exclude_figures_tables:
                where_clauses.append("is_figure_or_table = FALSE")

            where_sql = ""
            if where_clauses:
                where_sql = "WHERE " + " AND ".join(where_clauses)

            limit = max(int(fetch_k), int(top_k))

            sql = f"""
                SELECT
                    chunk_id,
                    title,
                    year,
                    report_type,
                    source_url,
                    markdown_path,
                    section_path,
                           array_cosine_distance(embedding, {qvec}) AS distance,
                    text
                FROM {TABLE_CHUNKS}
                {where_sql}
                ORDER BY distance
                LIMIT {limit};
            """

            rows = conn.execute(sql, params).fetchall()

            candidates = [
                RetrievedChunk(
                    chunk_id=row[0],
                    title=row[1],
                    year=row[2],
                    report_type=row[3],
                    source_url=row[4],
                    markdown_path=row[5],
                    section_path=row[6],
                    chunk_index=row[7],
                    distance=float(row[8]),
                    rerank_score=None,
                    text=row[9],
                )
                for row in rows
            ]

            if rerank and candidates:
                candidates = self._rerank(
                    query=query,
                    chunks=candidates,
                    top_k=top_k,
                    rerank_model=rerank_model,
                )
            else:
                candidates = candidates[:top_k]

            return candidates

        finally:
            conn.close()

    def _rerank(
        self,
        query: str,
        chunks: list[RetrievedChunk],
        top_k: int,
        rerank_model: str,
    ) -> list:
        """
        Re-rank retrieved chunks with a CrossEncoder.
        """
        try:
            reranker = _load_cross_encoder(rerank_model, self.device)
        except Exception as exc:
            logger.warning("Cross-encoder unavailable; returning vector ranking only: %s", exc)
            return chunks[:top_k]

        pairs = [(query, chunk.text[:3000]) for chunk in chunks]
        scores = reranker.predict(pairs)

        scored: list[RetrievedChunk] = []

        for chunk, score in zip(chunks, scores):
            chunk.rerank_score = float(score)
            scored.append(chunk)

        scored.sort(key=lambda c: c.rerank_score if c.rerank_score is not None else -9999, reverse=True)
        return scored[:top_k]

    def build_context_block(
        self,
        chunks: list[RetrievedChunk],
        max_chars: int = 6000,
    ) -> str:
        """
        Build a compact context block to inject into generate_data_story.
        """
        if not chunks:
            return ""

        blocks: list[str] = []
        total = 0

        for i, chunk in enumerate(chunks, start=1):
            source_label = f"{chunk.title or 'UNHCR report'}"
            if chunk.year:
                source_label += f" ({chunk.year})"

            header = (
                f"[Context {i}] {source_label}\n"
                f"Section: {chunk.section_path or 'Unknown'}\n"
                f"Similarity: {chunk.similarity:.4f}\n"
                f"Source: {chunk.source_url or chunk.markdown_path or 'Unknown'}\n"
            )

            body = chunk.text.strip()
            block = f"{header}\n{body}\n"

            if total + len(block) > max_chars:
                remaining = max_chars - total
                if remaining > 500:
                    blocks.append(block[:remaining].rstrip() + "\n...[truncated]\n")
                break

            blocks.append(block)
            total += len(block)

        return "\n---\n".join(blocks)

    def sources_payload(self, chunks: list[RetrievedChunk]) -> list[dict[str, Any]]:
        return [
            {
                "rank": i,
                "chunk_id": chunk.chunk_id,
                "title": chunk.title,
                "year": chunk.year,
                "report_type": chunk.report_type,
                "section_path": chunk.section_path,
                "source_url": chunk.source_url,
                "markdown_path": chunk.markdown_path,
                "chunk_index": chunk.chunk_index,
                "distance": chunk.distance,
                "similarity": chunk.similarity,
                "rerank_score": chunk.rerank_score,
            }
            for i, chunk in enumerate(chunks, start=1)
        ]


# Class for API retrieval
class UNHCRAPIClient:
    """Client for UNHCR API."""

    BASE_URL = "https://api.unhcr.org/population/v1"

    def _fetch(self, endpoint: str,
             coo: Optional[str] = None,
             coa: Optional[str] = None,
             year: Optional[Union[str, int]] = None,
             coo_all: bool = False,
             coa_all: bool = False,
             pop_type: Optional[bool] = None) -> dict[str, Any]:
        """
        Generic function to fetch data from various UNHCR API endpoints.
        """
        params = {"cf_type": "ISO"}
        
        if coo:
            params["coo"] = coo
        if coa:
            params["coa"] = coa
        if coo_all:
            params["coo_all"] = "true"
        if coa_all:
            params["coa_all"] = "true"
        
        if pop_type is True:
            params["pop_type"] = "true"            
        
        if year is None:
            # Default to current year
            current_year = datetime.now().year
            params["year[]"] = str(current_year)
        else:
            year_str = str(year)
            if "," in year_str:
                years = [y.strip() for y in year_str.split(",")]
                params["year[]"] = years
            else:
                params["year[]"] = year_str
        
        url = f"{self.BASE_URL}/{endpoint}/"
        
        try:
            logger.info(f"Fetching UNHCR {endpoint} data with params: {params}")
            response = requests.get(url, params=params)
            response.raise_for_status()
            return response.json()
        except requests.RequestException as e:
            logger.error(f"Error fetching UNHCR {endpoint} data: {e}")
            return {"error": str(e), "status": "error"}

    def get_population(self, coo: Optional[str] = None, coa: Optional[str] = None, 
                      year: Optional[Union[str, int]] = None, coo_all: bool = False, 
                      coa_all: bool = False) -> dict[str, Any]:
        return self._fetch("population", coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all)

    def get_demographics(self, coo: Optional[str] = None, coa: Optional[str] = None, 
                         year: Optional[Union[str, int]] = None, coo_all: bool = False, 
                         coa_all: bool = False, pop_type: bool = False) -> dict[str, Any]:
        return self._fetch("demographics", coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all, pop_type=pop_type)

    def get_asylum_applications(self, coo: Optional[str] = None, coa: Optional[str] = None, 
                               year: Optional[Union[str, int]] = None,
                               coo_all: bool = False, coa_all: bool = False) -> dict[str, Any]:
        return self._fetch("asylum-applications", coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all)

    def get_asylum_decisions(self, coo: Optional[str] = None, coa: Optional[str] = None, 
                            year: Optional[Union[str, int]] = None, coo_all: bool = False, 
                            coa_all: bool = False) -> dict[str, Any]:
        return self._fetch("asylum-decisions", coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all)

    def get_solutions(self, coo: Optional[str] = None, coa: Optional[str] = None, 
                      year: Optional[Union[str, int]] = None, coo_all: bool = False, 
                      coa_all: bool = False) -> dict[str, Any]:
        return self._fetch("solutions", coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all)


def _get_population_color(population_type: str) -> str:
    """Helper function to get UNHCR standard colors for population types."""
    color_map = {
        'refugees': '#0072BC',
        'asylum_seekers': '#6CD8FD',
        'idps': '#32C189',
        'stateless': '#FFC740',
        'oip': '#D25A45',
        'ooc': '#A097E3',
        'hst': '#BFBFBF',
        'returned_refugees': '#00B398',
        'returned_idps': '#00B398'
    }
    return color_map.get(population_type, '#333333')
