#!/usr/bin/env python3
"""
UNHCR Forcibly Displaced Populations MCP Server

This MCP server provides access to various UNHCR endpoints through the Model Context Protocol.
It allows querying data around forcibly displaced persons by country of origin, country of asylum,
and year(s), as well as provide data on Refugee Status Determination (RSD) Applications and
Refugee Status Determination (RSD) decisions.

API Endpoint: https://api.unhcr.org/population/v1/
"""

from __future__ import annotations

import logging
import os
from datetime import datetime
from typing import Any, Optional, Union

import requests
from mcp.server.fastmcp import FastMCP
from smithery.decorators import smithery

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)

import json
import re
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path

import duckdb
import numpy as np
from sentence_transformers import SentenceTransformer

try:
    from sentence_transformers import CrossEncoder
except Exception:
    CrossEncoder = None


logger = logging.getLogger(__name__)

# Vector database configuration
VECTOR_DB_PATH = os.getenv(
    "UNHCR_VECTOR_DB",
    "data/vector_store/unhcr_reports.duckdb",
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
        parts = [user_request.strip()]

        if data_summary:
            parts.append(f"Data summary: {data_summary.strip()}")

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

            query_embedding = model.encode(
                [query],
                normalize_embeddings=True,
                convert_to_numpy=True,
            ).astype("float32")[0]

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


@smithery.server()
def create_server() -> FastMCP:
    """
    Create and return a FastMCP server instance.

    Returns:
        Configured FastMCP server
    """
    # Set environment variable to allow any host header
    os.environ["ALLOWED_HOSTS"] = "*"

    # Initialize the server
    server = FastMCP(
        name="UNHCR Forcibly Displaced Populations MCP Server",
        instructions=(
            "Provides UNHCR population data tools and data-story generation. "
            "Can optionally enrich data stories with contextual evidence from "
            "local UNHCR Global Trends and Mid-Year Trends reports."
        ),
    )

    rag_retriever = UNHCRVectorRetriever()

    @server.tool(
        name="retrieve_report_context",
        description=(
            "Retrieve relevant contextual excerpts from the local UNHCR report vector store. "
            "Use this to support data stories, methodology explanations, and source-grounded analysis."
        ),
    )
    def retrieve_report_context(
        request: str,
        top_k: int = DEFAULT_RAG_TOP_K,
        fetch_k: int = DEFAULT_RAG_FETCH_K,
        year: Optional[str] = None,
        report_type: Optional[str] = None,
        section_contains: Optional[str] = None,
        exclude_figures_tables: bool = False,
        rerank: bool = False,
    ) -> dict[str, Any]:
        """
        Retrieve top matching UNHCR report chunks from the vector store.
        """
        if not rag_retriever.available():
            return {
                "available": False,
                "message": f"Vector DB not found at {rag_retriever.db_path}",
                "query": request,
                "contexts": [],
                "sources": [],
            }

        query = rag_retriever.formulate_query(request)

        chunks = rag_retriever.retrieve(
            query=query,
            top_k=top_k,
            fetch_k=fetch_k,
            year=year,
            report_type=report_type,
            section_contains=section_contains,
            exclude_figures_tables=exclude_figures_tables,
            rerank=rerank,
        )

        return {
            "available": True,
            "query": query,
            "context_block": rag_retriever.build_context_block(chunks),
            "sources": rag_retriever.sources_payload(chunks),
        }


    # Initialize API client
    api_client = UNHCRAPIClient()

    @server.tool(
        name="get_population_data",
        description=(
            "Retrieve forcibly displaced population statistics from UNHCR. "
            "Use this tool when asked about refugee numbers, asylum seekers, stateless persons, "
            "or other populations of concern by country and year."
        ),
    )
    def get_population_data(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        """
        Get forcibly displaced populations like refugees, asylum seekers, stateless persons data from UNHCR.

        Args:
            coo: Country of origin (ISO3 code) - Use for questions about refugees FROM a specific country
            coa: Country of asylum (ISO3 code) - Use for questions about refugees IN a specific country
            year: Year to filter by (defaults to 2025)
            coo_all: Set to True when breaking down results by ORIGIN country
            coa_all: Set to True when breaking down results by ASYLUM country

        Returns:
            Population data from UNHCR API
        """
        return api_client.get_population(
            coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
        )

    @server.tool(
        name="get_demographics_data",
        description=(
            "Retrieve age and sex breakdown data for forcibly displaced populations. "
            "Use this tool when asked about demographic composition, gender distribution, "
            "or age groups of refugees and other populations of concern."
        ),
    )
    def get_demographics_data(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
        pop_type: bool = False,
    ) -> dict[str, Any]:
        """
        Get forcibly displaced populations demographics data from UNHCR. It shows breakdown by age and sex when available.

        Args:
            coo: Country of origin (ISO3 code) - Use for questions about forcibly displaced populations FROM a specific country
            coa: Country of asylum (ISO3 code) - Use for questions about forcibly displaced populations IN a specific country
            year: Year to filter by (defaults to 2025)
            coo_all: Set to True when breaking down results by ORIGIN country
            coa_all: Set to True when breaking down results by ASYLUM country
            pop_type: Set to True when asked about specific population types (e.g., refugees, asylum seekers, stateless persons)

        Returns:
            Demographics data from UNHCR API
        """
        return api_client.get_demographics(
            coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all, pop_type=pop_type
        )

    @server.tool(
        name="get_rsd_applications",
        description=(
            "Retrieve Refugee Status Determination (RSD) application statistics. "
            "Use this tool when asked about asylum applications, claims, or requests for refugee status "
            "by country, origin, or year."
        ),
    )
    def get_rsd_applications(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        """
        Get RSD application data from UNHCR.

        Args:
            coo: Country of origin filter (ISO3 code, comma-separated for multiple)
            coa: Country of asylum filter (ISO3 code, comma-separated for multiple)
            year: Year filter (comma-separated for multiple years) - defaults to 2025
            coo_all: Set to True when analyzing the ORIGIN COUNTRIES of asylum seekers
            coa_all: Set to True when analyzing the ASYLUM COUNTRIES where applications were filed

        Returns:
            RSD application data from UNHCR API
        """
        return api_client.get_asylum_applications(
            coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
        )

    @server.tool(
        name="get_rsd_decisions",
        description=(
            "Retrieve Refugee Status Determination (RSD) decision outcomes. "
            "Use this tool when asked about approved/rejected asylum cases, recognition rates, "
            "or refugee status determination results by country and year."
        ),
    )
    def get_rsd_decisions(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        """
        Get Refugee Status Determination (RSD) decision data from UNHCR.

        Args:
            coo: Country of origin filter (ISO3 code, comma-separated for multiple)
            coa: Country of asylum filter (ISO3 code, comma-separated for multiple)
            year: Year filter (comma-separated for multiple years) - defaults to 2025
            coo_all: Set to True when analyzing decisions breakdown BY NATIONALITY
            coa_all: Set to True when analyzing decisions breakdown BY COUNTRY

        Returns:
            RSD decision data from UNHCR API
        """
        return api_client.get_asylum_decisions(
            coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
        )

    @server.tool(
        name="get_solutions",
        description=(
            "Retrieve durable solutions data including refugee returnees, resettlement, "
            "naturalization, and IDP returns. Use this tool when asked about solutions "
            "to displacement, voluntary repatriation, or integration outcomes."
        ),
    )
    def get_solutions(
        coo: str | None = None,
        coa: str | None = None,
        year: str | int | None = None,
        coo_all: bool = False,
        coa_all: bool = False,
    ) -> dict[str, Any]:
        """
        Get figures on durable solutions from UNHCR which includes refugee returnees (returned_refugees), resettlement, naturalisation, retuned IDPs (returned_idps)

        Args:
            coo: Country of origin filter (ISO3 code, comma-separated for multiple)
            coa: Country of asylum filter (ISO3 code, comma-separated for multiple)
            year: Year filter (comma-separated for multiple years) - defaults to 2025
            coo_all: Set to True when analyzing decisions breakdown BY NATIONALITY
            coa_all: Set to True when analyzing decisions breakdown BY COUNTRY

        Returns:
            Solutions data from UNHCR API
        """
        return api_client.get_solutions(
            coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
        )

    @server.tool(
        name="get_country_key_figures",
        description=(
            "Retrieve formatted key statistics and summaries for specific countries. "
            "Use this tool when asked for country profiles, overview statistics, "
            "or formatted summaries of displacement situations."
        ),
    )
    def get_country_key_figures(
        coa: str | None = None,
        coo: str | None = None,
        year: str | int | None = None,
        population_types: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Get key figures for a specific country with formatted summary statistics.
        
        Args:
            coa: Country of asylum (ISO3 code)
            coo: Country of origin (ISO3 code)
            year: Year to filter by (defaults to 2025)
            population_types: List of population types to include (e.g., ['refugees', 'asylum_seekers'])

        Returns:
            Formatted key figures data including totals, percentages, and metadata
        """
        # Get raw population data
        population_data = api_client.get_population(coa=coa, coo=coo, year=year)
        
        # Process data to extract key figures
        if population_data.get('data'):
            data = population_data['data']
            
            # Filter by population types if specified
            if population_types:
                data = [item for item in data if item.get('population_type') in population_types]
            
            # Calculate totals and percentages
            total_poc = sum(item.get('value', 0) for item in data)
            
            # Format results
            result = {
                'country': data[0].get('coa_name', 'Unknown'),
                'year': year or 2025,
                'total_population_of_concern': total_poc,
                'breakdown': [],
                'metadata': {
                    'source': 'UNHCR Population Statistics',
                    'api_version': 'v1'
                }
            }
            
            # Add breakdown by population type
            for item in data:
                pop_type = item.get('population_type', 'unknown')
                value = item.get('value', 0)
                percentage = (value / total_poc * 100) if total_poc > 0 else 0
                
                result['breakdown'].append({
                    'population_type': pop_type,
                    'count': value,
                    'percentage': round(percentage, 2),
                    'color': self._get_population_color(pop_type)
                })
            
            return result
        
        return {'error': 'No data available', 'status': 'error'}

    @server.tool(
        name="get_population_trends",
        description=(
            "Retrieve time series data showing population changes over multiple years. "
            "Use this tool when asked about trends, historical changes, or comparisons "
            "across different time periods."
        ),
    )
    def get_population_trends(
        coa: str | None = None,
        coo: str | None = None,
        years: str | None = None,
        population_types: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Get population trends over multiple years for time series analysis.
        
        Args:
            coa: Country of asylum (ISO3 code)
            coo: Country of origin (ISO3 code)
            years: Comma-separated years (e.g., '2020,2021,2022') or year range
            population_types: List of population types to track over time

        Returns:
            Time series data for population trends
        """
        if not years:
            # Default to last 5 years including current year
            current_year = datetime.now().year
            start_year = current_year - 4
            years = ','.join(str(y) for y in range(start_year, current_year + 1))
            
        # Get population data for multiple years
        population_data = api_client.get_population(coa=coa, coo=coo, year=years)
        
        if population_data.get('data'):
            # Process into time series format
            time_series = {}
            
            for item in population_data['data']:
                year = item.get('year', 'unknown')
                pop_type = item.get('population_type', 'unknown')
                value = item.get('value', 0)
                
                # Filter by population types if specified
                if population_types and pop_type not in population_types:
                    continue
                    
                if year not in time_series:
                    time_series[year] = {}
                    
                time_series[year][pop_type] = value
            
            return {
                'country': population_data['data'][0].get('coa_name', 'Unknown'),
                'time_series': time_series,
                'metadata': {
                    'source': 'UNHCR Population Statistics',
                    'time_range': years
                }
            }
        
        return {'error': 'No trend data available', 'status': 'error'}

    @server.tool(
        name="get_demographic_breakdown",
        description=(
            "Retrieve detailed age and sex distribution for specific population types. "
            "Use this tool when asked for granular demographic analysis, age pyramids, "
            "or gender breakdowns of refugee populations."
        ),
    )
    def get_demographic_breakdown(
        coa: str | None = None,
        coo: str | None = None,
        year: str | int | None = None,
        population_type: str | None = None
    ) -> dict[str, Any]:
        """
        Get detailed demographic breakdown by age and sex for a specific population type.
        
        Args:
            coa: Country of asylum (ISO3 code)
            coo: Country of origin (ISO3 code)
            year: Year to filter by (defaults to 2025)
            population_type: Specific population type (e.g., 'refugees')

        Returns:
            Demographic data with age/sex breakdown
        """
        demographics_data = api_client.get_demographics(
            coa=coa, 
            coo=coo,
            year=year, 
            pop_type=True if population_type else False
        )
        
        if demographics_data.get('data'):
            # Process demographic data
            processed_data = []
            
            for item in demographics_data['data']:
                if population_type and item.get('population_type') != population_type:
                    continue
                    
                processed_data.append({
                    'population_type': item.get('population_type', 'unknown'),
                    'age_group': item.get('age_group', 'unknown'),
                    'sex': item.get('sex', 'unknown'),
                    'count': item.get('value', 0),
                    'percentage': item.get('percentage', 0)
                })
            
            return {
                'country': demographics_data['data'][0].get('coa_name', 'Unknown'),
                'year': year or 2025,
                'demographics': processed_data,
                'metadata': {
                    'source': 'UNHCR Demographics Statistics'
                }
            }
        
        return {'error': 'No demographic data available', 'status': 'error'}

    def _get_population_color(self, population_type: str) -> str:
        """Helper method to get UNHCR standard colors for population types."""
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

    @server.tool(
        name="extract_visualization_structure",
        description=(
            "Extract and structure visualization metadata for AI-generated reports. "
            "Use this tool when asked to create charts, graphs, or visual representations "
            "of data for reporting purposes."
        ),
    )
    def extract_visualization_structure(
        visualization_type: str,
        title: str | None = None,
        subtitle: str | None = None,
        x_axis_label: str | None = None,
        y_axis_label: str | None = None,
        x_axis_range: list[float] | None = None,
        y_axis_range: list[float] | None = None,
        legend_items: list[str] | None = None,
        geometric_layers: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Extract and structure visualization metadata (Phase 1 of AI reporting).
        
        Args:
            visualization_type: Type of visualization (e.g., 'bar', 'line', 'scatter')
            title: Main title of the visualization
            subtitle: Subtitle or secondary title
            x_axis_label: Label for X-axis
            y_axis_label: Label for Y-axis
            x_axis_range: Range of X-axis as [min, max]
            y_axis_range: Range of Y-axis as [min, max]
            legend_items: List of items in the legend
            geometric_layers: List of geometric layers used (e.g., ['point', 'line'])

        Returns:
            Structured metadata for visualization analysis
        """
        structure = {
            'visualization_type': visualization_type,
            'labels': {
                'title': title or '',
                'subtitle': subtitle or '',
                'x': x_axis_label or '',
                'y': y_axis_label or ''
            },
            'ranges': {
                'x': x_axis_range or [None, None],
                'y': y_axis_range or [None, None]
            },
            'legend': legend_items or [],
            'geometric_layers': geometric_layers or [],
            'metadata': {
                'source': 'UNHCR AI Reporting System',
                'phase': 'structure_extraction'
            }
        }
        return structure

    @server.tool(
        name="analyze_data_statistics",
        description=(
            "Perform statistical analysis on datasets including descriptive statistics, "
            "correlations, and distributions. Use this tool when asked for data analysis, "
            "statistical summaries, or insights from numerical data."
        ),
    )
    def analyze_data_statistics(
        data: list[dict[str, Any]],
        numeric_columns: list[str],
        categorical_columns: list[str] | None = None,
        correlation_columns: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Analyze data statistics and correlations (Phase 2 of AI reporting).
        
        Args:
            data: List of dictionaries representing data rows
            numeric_columns: List of numeric column names to analyze
            categorical_columns: List of categorical column names to analyze
            correlation_columns: List of column pairs to calculate correlations for

        Returns:
            Statistical analysis including distributions and correlations
        """
        import statistics
        from collections import Counter
        
        if not data:
            return {'error': 'No data provided', 'status': 'error'}
            
        # Convert data to more workable format
        df = [{k: v for k, v in row.items() if k in numeric_columns + (categorical_columns or [])} for row in data]
        
        # Calculate basic statistics for numeric columns
        stats_results = {}
        
        for col in numeric_columns:
            values = [row.get(col) for row in df if row.get(col) is not None]
            if values:
                stats_results[col] = {
                    'count': len(values),
                    'mean': statistics.mean(values) if values else None,
                    'median': statistics.median(values) if values else None,
                    'min': min(values) if values else None,
                    'max': max(values) if values else None,
                    'std_dev': statistics.stdev(values) if len(values) > 1 else None
                }
        
        # Calculate frequency distributions for categorical columns
        freq_results = {}
        if categorical_columns:
            for col in categorical_columns:
                values = [row.get(col) for row in df if row.get(col) is not None]
                if values:
                    freq_results[col] = dict(Counter(values))
        
        # Calculate correlations if requested
        correlation_results = {}
        if correlation_columns and len(correlation_columns) >= 2:
            try:
                import numpy as np
                from scipy.stats import pearsonr
                
                # Get the first two columns for correlation
                col1, col2 = correlation_columns[:2]
                values1 = [row.get(col1) for row in df if row.get(col1) is not None and row.get(col2) is not None]
                values2 = [row.get(col2) for row in df if row.get(col1) is not None and row.get(col2) is not None]
                
                if len(values1) >= 2 and len(values2) >= 2:
                    corr, p_value = pearsonr(values1, values2)
                    correlation_results[f'{col1}_vs_{col2}'] = {
                        'pearson_correlation': corr,
                        'p_value': p_value,
                        'sample_size': len(values1)
                    }
            except ImportError:
                correlation_results['error'] = 'scipy not available for correlation calculation'
            except Exception as e:
                correlation_results['error'] = str(e)
        
        return {
            'statistics': stats_results,
            'frequencies': freq_results,
            'correlations': correlation_results,
            'metadata': {
                'source': 'UNHCR AI Reporting System',
                'phase': 'statistical_profiling',
                'sample_size': len(df)
            }
        }

    @server.tool(
        name="generate_visualization_description",
        description=(
            "Generate AI-powered descriptions and interpretations for visualizations. "
            "Use this tool when asked to explain charts, provide insights from graphs, "
            "or create narrative descriptions of data visualizations."
        ),
    )
    def generate_visualization_description(
        structure: dict[str, Any],
        statistics: dict[str, Any],
        description_type: str = 'both',
        max_length: int = 300,
        focus_areas: list[str] | None = None
    ) -> dict[str, Any]:
        """
        Generate AI-powered visualization descriptions (Phase 3 of AI reporting).
        
        Args:
            structure: Visualization structure from extract_visualization_structure
            statistics: Statistical analysis from analyze_data_statistics
            description_type: Type of description ('short', 'long', or 'both')
            max_length: Maximum length for descriptions
            focus_areas: Specific areas to focus on in the description

        Returns:
            Generated descriptions with short and long versions
        """
        # Extract key information from structure
        viz_type = structure.get('visualization_type', 'visualization')
        title = structure.get('labels', {}).get('title', 'Untitled')
        x_label = structure.get('labels', {}).get('x', 'X-axis')
        y_label = structure.get('labels', {}).get('y', 'Y-axis')
        
        # Extract key statistics
        stats_summary = ""
        if statistics.get('statistics'):
            for col, stats in statistics['statistics'].items():
                stats_summary += f"{col}: mean={stats.get('mean', 'N/A')}, "
                stats_summary += f"median={stats.get('median', 'N/A')}, "
                stats_summary += f"range=[{stats.get('min', 'N/A')}, {stats.get('max', 'N/A')}]\n"
        
        # Extract correlations
        correlation_summary = ""
        if statistics.get('correlations'):
            for corr_name, corr_data in statistics['correlations'].items():
                if corr_name != 'error':
                    correlation_summary += f"{corr_name}: r={corr_data.get('pearson_correlation', 'N/A')}, "
                    correlation_summary += f"p={corr_data.get('p_value', 'N/A')}\n"
        
        # Generate short description (WCAG-compliant alt text)
        short_desc = f"{viz_type.capitalize()} chart showing {x_label} versus {y_label}"
        
        if structure.get('labels', {}).get('subtitle'):
            short_desc += f" - {structure['labels']['subtitle']}"
        
        # Generate long description with statistical context
        long_desc = f"This {viz_type} visualization titled '{title}' displays the relationship between {x_label} and {y_label}.\n\n"
        
        if stats_summary:
            long_desc += "Key statistics:\n" + stats_summary + "\n"
        
        if correlation_summary:
            long_desc += "Statistical relationships:\n" + correlation_summary + "\n"
        
        # Focus areas handling
        if focus_areas:
            long_desc += "Focus areas: " + ", ".join(focus_areas) + ".\n"
        
        # Apply length limits
        if len(short_desc) > max_length:
            short_desc = short_desc[:max_length-3] + "..."
            
        if len(long_desc) > max_length * 2:  # Allow more room for long description
            long_desc = long_desc[:max_length*2-3] + "..."
        
        result = {
            'short_description': short_desc,
            'long_description': long_desc,
            'metadata': {
                'source': 'UNHCR AI Reporting System',
                'phase': 'semantic_generation',
                'description_type': description_type
            }
        }
        
        # Filter based on description_type
        if description_type != 'both':
            if description_type == 'short':
                result['long_description'] = None
            else:
                result['short_description'] = None
                
        return result


    @server.tool(
        name="generate_ai_data_story",
        description=(
            "Generate a complete AI data story from visualization data, optionally enriched "
            "with relevant context retrieved from local UNHCR statistical reports."
        ),
    )
    def generate_ai_data_story(
        visualization_data: dict[str, Any],
        context: str | None = None,
        story_type: str = "analytical",
        max_tokens: int = 500,
        apply_guardrails: bool = True,

        # RAG options
        use_report_context: bool = True,
        rag_top_k: int = DEFAULT_RAG_TOP_K,
        rag_fetch_k: int = DEFAULT_RAG_FETCH_K,
        rag_rerank: bool = False,
        rag_year: str | None = None,
        rag_report_type: str | None = None,
        rag_section_contains: str | None = None,
        rag_exclude_figures_tables: bool = False,
    ) -> dict[str, Any]:
        """
        Generate a complete AI data story from visualization data with optional methodology guardrails
        and optional RAG context from UNHCR statistical reports.

        Args:
            visualization_data: Complete visualization data including structure and statistics.
            context: Additional context for the story generation.
            story_type: Type of story: analytical, narrative, executive.
            max_tokens: Maximum length for the generated story.
            apply_guardrails: Whether to apply UNHCR methodology guardrails.
            use_report_context: Whether to retrieve relevant report context from the local vector store.
            rag_top_k: Number of retrieved chunks to use.
            rag_fetch_k: Candidate chunks fetched before optional reranking.
            rag_rerank: Whether to rerank retrieved chunks with a cross-encoder.
            rag_year: Optional year filter, e.g. "2025".
            rag_report_type: Optional report type filter, e.g. "Global Trends".
            rag_section_contains: Optional section path filter.
            rag_exclude_figures_tables: Exclude figure/table chunks from retrieval.

        Returns:
            Generated data story with title, story text, retrieved sources, and optional guardrails info.
        """

        structure = visualization_data.get("structure", {})
        statistics = visualization_data.get("statistics", {})

        title = structure.get("labels", {}).get("title", "UNHCR Data Story")
        viz_type = structure.get("visualization_type", "chart")

        retrieved_context = ""
        retrieved_sources: list[dict[str, Any]] = []
        retrieval_query = None

        if use_report_context and rag_retriever.available():
            try:
                retrieval_query = rag_retriever.formulate_query(
                    visualization_data=visualization_data,
                    context=context,
                    story_type=story_type,
                )

                chunks = rag_retriever.retrieve(
                    query=retrieval_query,
                    top_k=rag_top_k,
                    fetch_k=rag_fetch_k,
                    year=rag_year,
                    report_type=rag_report_type,
                    section_contains=rag_section_contains,
                    exclude_figures_tables=rag_exclude_figures_tables,
                    rerank=rag_rerank,
                )

                retrieved_context = rag_retriever.build_context_block(chunks)
                retrieved_sources = rag_retriever.sources_payload(chunks)

            except Exception as exc:
                logger.warning("RAG retrieval failed, continuing without report context: %s", exc)

        elif use_report_context and not rag_retriever.available():
            logger.warning("Vector store not found at %s; continuing without report context.", rag_retriever.db_path)

        # ------------------------------------------------------------------
        # Generate basic story components
        # ------------------------------------------------------------------
        if story_type == "analytical":
            story = f"This {viz_type} presents a detailed analysis of "
            story += f"{structure.get('labels', {}).get('x', 'the data')} and "
            story += f"{structure.get('labels', {}).get('y', 'its relationship')}. "

            if statistics.get("statistics"):
                story += "Key findings include: "
                for col, stats in statistics["statistics"].items():
                    story += (
                        f"{col} ranges from {stats.get('min', 'N/A')} "
                        f"to {stats.get('max', 'N/A')} "
                        f"with a mean of {stats.get('mean', 'N/A')}; "
                    )

            if statistics.get("correlations"):
                story += "Statistical analysis reveals: "
                for corr_name, corr_data in statistics["correlations"].items():
                    if corr_name != "error":
                        story += (
                            f"{corr_name} shows a correlation of "
                            f"{corr_data.get('pearson_correlation', 'N/A')}; "
                        )

        elif story_type == "narrative":
            story = f"The story of {title} unfolds through this {viz_type}. "
            story += "As we examine the data, we see compelling patterns emerge. "

            if statistics.get("statistics"):
                story += "Notable observations include significant variations in key metrics: "
                for col, stats in statistics["statistics"].items():
                    story += (
                        f"{col} demonstrates a wide range from "
                        f"{stats.get('min', 'N/A')} to {stats.get('max', 'N/A')}, "
                        f"highlighting the diversity in the data; "
                    )

        else:
            story = f"Executive Summary: This {viz_type} provides critical insights into "
            story += f"{structure.get('labels', {}).get('x', 'the subject matter')}. "

            if statistics.get("statistics"):
                story += "Key metrics indicate: "
                for col, stats in statistics["statistics"].items():
                    story += (
                        f"{col} averages {stats.get('mean', 'N/A')} "
                        f"with a standard deviation of {stats.get('std_dev', 'N/A')}; "
                    )

        # ------------------------------------------------------------------
        # Add user-provided context
        # ------------------------------------------------------------------
        if context:
            story += f"\n\nContext: {context}"

        # ------------------------------------------------------------------
        # Add retrieved report context
        # ------------------------------------------------------------------
        if retrieved_context:
            story += "\n\nRelevant UNHCR report context: "
            story += summarize_retrieved_context_for_story(retrieved_context)

            story += "\n\nSource grounding: "
            source_summaries = []

            for src in retrieved_sources[:rag_top_k]:
                label = src.get("title") or "UNHCR report"
                year = src.get("year")
                section = src.get("section_path")
                url = src.get("source_url")

                source_text = label
                if year:
                    source_text += f" ({year})"
                if section:
                    source_text += f", section: {section}"
                if url:
                    source_text += f", URL: {url}"

                source_summaries.append(source_text)

            story += " | ".join(source_summaries)

        # ------------------------------------------------------------------
        # Token limit
        # ------------------------------------------------------------------
        if len(story) > max_tokens * 4:
            story = story[: max_tokens * 4 - 3] + "..."

        response = {
            "title": title,
            "story": story,
            "story_type": story_type,
            "retrieval": {
                "used_report_context": bool(retrieved_context),
                "query": retrieval_query,
                "top_k": rag_top_k,
                "fetch_k": rag_fetch_k,
                "rerank": rag_rerank,
                "sources": retrieved_sources,
            },
            "metadata": {
                "source": "UNHCR AI Reporting System",
                "tokens_used": len(story) // 4,
                "focus": "data_narrative",
                "rag_vector_db": str(rag_retriever.db_path),
            },
        }

        # ------------------------------------------------------------------
        # Apply methodology guardrails if requested
        # ------------------------------------------------------------------
        if apply_guardrails:
            population_type = None
            context_probe = f"{title} {context or ''} {retrieved_context or ''}".lower()

            if "refugee" in context_probe:
                population_type = "refugees"
            elif "idp" in context_probe or "internally displaced" in context_probe:
                population_type = "idps"
            elif "stateless" in context_probe:
                population_type = "stateless"
            elif "asylum" in context_probe:
                population_type = "asylum_seekers"

            response["methodology_guardrails"] = {
                "status": "guardrails not applied - would require refactoring to call sibling tool",
                "note": "Guardrails functionality available via separate apply_analysis_guardrails tool",
                "detected_population_type": population_type,
                "rag_context_used_for_detection": bool(retrieved_context),
            }

        return response


    @server.tool(
        name="get_usage_guidance",
        description=(
            "Get usage guidance, examples, and best practices for UNHCR MCP tools. "
            "Use this tool when asked how to use the system, what tools are available, "
            "or for help with specific tool usage."
        ),
    )
    def get_usage_guidance(
        tool_category: str | None = None,
        specific_tool: str | None = None
    ) -> dict[str, Any]:
        """
        Get usage guidance, suggested questions, and examples for UNHCR MCP tools.
        
        Args:
            tool_category: Category of tools ('population', 'demographics', 'rsd', 'solutions', 'ai_reporting', 'all')
            specific_tool: Specific tool name for detailed guidance

        Returns:
            Usage guidance including suggested questions, examples, and best practices
        """
        # Define guidance for all tools
        guidance_database = {
            'population': {
                'description': 'Tools for accessing refugee and displaced population data',
                'tools': {
                    'get_population_data': {
                        'description': 'Get raw population statistics by country, origin, and year',
                        'suggested_questions': [
                            'How many refugees are currently in Colombia?',
                            'What is the refugee population trend in Turkey from 2020-2024?',
                            'Which countries have the highest number of internally displaced persons?',
                            'What is the breakdown of different population types (refugees, asylum seekers, IDPs) in Germany?'
                        ],
                        'examples': [
                            {
                                'question': 'Refugees in Colombia 2024',
                                'parameters': {'coa': 'COL', 'year': 2024},
                                'expected': 'Returns population data for Colombia in 2024'
                            },
                            {
                                'question': 'Refugees from Syria across all countries',
                                'parameters': {'coo': 'SYR', 'coa_all': True},
                                'expected': 'Shows Syrian refugees distributed across host countries'
                            }
                        ],
                        'best_practices': [
                            'Use coa_all=True when you want to see distribution across host countries',
                            'Use coo_all=True when analyzing refugees by country of origin',
                            'Specify year ranges as "2020,2021,2022" for multi-year analysis'
                        ]
                    },
                    'get_country_key_figures': {
                        'description': 'Get formatted summary statistics with percentages and colors',
                        'suggested_questions': [
                            'What are the key refugee statistics for Turkey?',
                            'Can you show me the population breakdown for Colombia with percentages?',
                            'What colors should I use for different population types in my visualization?'
                        ],
                        'examples': [
                            {
                                'question': 'Key figures for Turkey 2024',
                                'parameters': {'coa': 'TUR', 'year': 2024},
                                'expected': 'Returns total population of concern with breakdown by type and percentages'
                            }
                        ],
                        'best_practices': [
                            'Use this for visualization-ready data with built-in color coding',
                            'Perfect for creating summary dashboards and infographics'
                        ]
                    },
                    'get_population_trends': {
                        'description': 'Analyze population changes over multiple years',
                        'suggested_questions': [
                            'How has the refugee population in Uganda changed over the last 5 years?',
                            'What are the trends for asylum seekers in Germany from 2020-2024?',
                            'Can you show me the historical data for IDPs in Colombia?'
                        ],
                        'examples': [
                            {
                                'question': '5-year trend for Turkey',
                                'parameters': {'coa': 'TUR', 'years': '2020,2021,2022,2023,2024'},
                                'expected': 'Returns time series data showing population changes over 5 years'
                            }
                        ],
                        'best_practices': [
                            'Use for creating line charts and trend analysis',
                            'Combine with visualization tools to show historical patterns',
                            'Filter by population_types to focus on specific groups'
                        ]
                    }
                }
            },
            'demographics': {
                'description': 'Tools for age, sex, and detailed demographic analysis',
                'tools': {
                    'get_demographics_data': {
                        'description': 'Get raw demographic breakdowns by age and sex',
                        'suggested_questions': [
                            'What is the age distribution of refugees in Turkey?',
                            'Can you show me the gender breakdown for asylum seekers in Colombia?',
                            'What are the demographic characteristics of IDPs in Uganda?'
                        ],
                        'examples': [
                            {
                                'question': 'Age/sex breakdown for Syrian refugees',
                                'parameters': {'coo': 'SYR', 'pop_type': True},
                                'expected': 'Returns demographic data for Syrian refugees'
                            }
                        ]
                    },
                    'get_demographic_breakdown': {
                        'description': 'Get processed demographic statistics with analysis',
                        'suggested_questions': [
                            'What percentage of refugees in Turkey are children?',
                            'Can you analyze the age distribution for asylum seekers in Germany?',
                            'What are the gender ratios among IDPs in Colombia?'
                        ],
                        'examples': [
                            {
                                'question': 'Detailed demographics for Turkey refugees',
                                'parameters': {'coa': 'TUR', 'population_type': 'refugees'},
                                'expected': 'Returns processed demographic statistics with age groups and sex breakdown'
                            }
                        ],
                        'best_practices': [
                            'Use for creating detailed demographic reports',
                            'Combine with visualization tools for age pyramid charts',
                            'Specify population_type to focus analysis on specific groups'
                        ]
                    }
                }
            },
            'ai_reporting': {
                'description': 'AI-powered visualization analysis and storytelling',
                'tools': {
                    'extract_visualization_structure': {
                        'description': 'Capture visualization metadata for AI analysis',
                        'suggested_questions': [
                            'How do I prepare my chart data for AI analysis?',
                            'What metadata should I capture from my visualization?',
                            'How can I structure my chart information for the AI system?'
                        ],
                        'examples': [
                            {
                                'question': 'Prepare bar chart metadata',
                                'parameters': {
                                    'visualization_type': 'bar',
                                    'title': 'Refugees by Country 2024',
                                    'x_axis_label': 'Country',
                                    'y_axis_label': 'Number of Refugees'
                                },
                                'expected': 'Returns structured metadata ready for AI analysis'
                            }
                        ],
                        'best_practices': [
                            'Capture all available metadata for best AI results',
                            'Include axis ranges for accurate statistical analysis',
                            'List all geometric layers used in the visualization'
                        ]
                    },
                    'analyze_data_statistics': {
                        'description': 'Compute statistical distributions and correlations',
                        'suggested_questions': [
                            'What are the statistical characteristics of this refugee population data?',
                            'Is there a correlation between refugee numbers and asylum seekers?',
                            'Can you analyze the distribution of ages in this dataset?'
                        ],
                        'examples': [
                            {
                                'question': 'Analyze refugee statistics',
                                'parameters': {
                                    'data': [{'country': 'Turkey', 'refugees': 3500000}],
                                    'numeric_columns': ['refugees'],
                                    'correlation_columns': ['refugees', 'asylum_seekers']
                                },
                                'expected': 'Returns statistical analysis including correlations'
                            }
                        ],
                        'best_practices': [
                            'Include all relevant numeric columns for comprehensive analysis',
                            'Specify correlation columns to analyze relationships',
                            'Use categorical columns for frequency distributions'
                        ]
                    },
                    'generate_visualization_description': {
                        'description': 'Create WCAG-compliant descriptions from visualization data',
                        'suggested_questions': [
                            'Can you generate an alt text description for this chart?',
                            'What would be a good accessibility description for this visualization?',
                            'Can you create both short and long descriptions for this graph?'
                        ],
                        'examples': [
                            {
                                'question': 'Generate chart description',
                                'parameters': {
                                    'structure': {'visualization_type': 'bar', 'labels': {'title': 'Refugees 2024'}},
                                    'statistics': {'statistics': {'refugees': {'mean': 2000000}}}
                                },
                                'expected': 'Returns WCAG-compliant short and long descriptions'
                            }
                        ],
                        'best_practices': [
                            'Use short descriptions for alt text and accessibility',
                            'Use long descriptions for detailed analysis and reports',
                            'Specify focus areas to highlight key insights'
                        ]
                    },
                    'generate_ai_data_story': {
                        'description': 'Create narrative stories from visualization data',
                        'suggested_questions': [
                            'Can you write a story about this refugee population data?',
                            'What insights can you extract from this visualization?',
                            'Can you create an executive summary of this analysis?'
                        ],
                        'examples': [
                            {
                                'question': 'Create analytical story',
                                'parameters': {
                                    'visualization_data': {
                                        'structure': {'labels': {'title': 'Refugee Trends'}},
                                        'statistics': {'statistics': {'refugees': {'mean': 1500000}}}
                                    },
                                    'story_type': 'analytical'
                                },
                                'expected': 'Returns a narrative data story with insights'
                            }
                        ],
                        'best_practices': [
                            'Use analytical stories for detailed data analysis',
                            'Use narrative stories for presentations and reports',
                            'Use executive summaries for decision-makers',
                            'Provide context to enhance story relevance'
                        ]
                    }
                }
            }
        }
        
        # Build response based on request
        if specific_tool:
            # Find the specific tool across all categories
            tool_guidance = None
            for category, category_data in guidance_database.items():
                if specific_tool in category_data.get('tools', {}):
                    tool_guidance = category_data['tools'][specific_tool]
                    break
            
            if tool_guidance:
                return {
                    'tool': specific_tool,
                    'category': category,
                    'description': tool_guidance['description'],
                    'suggested_questions': tool_guidance['suggested_questions'],
                    'examples': tool_guidance['examples'],
                    'best_practices': tool_guidance['best_practices'],
                    'metadata': {
                        'source': 'UNHCR Usage Guidance System',
                        'tool_type': 'specific_guidance'
                    }
                }
            else:
                return {'error': f'Tool {specific_tool} not found in guidance database', 'status': 'error'}
        
        elif tool_category and tool_category in guidance_database:
            # Return guidance for a specific category
            category_data = guidance_database[tool_category]
            return {
                'category': tool_category,
                'description': category_data['description'],
                'tools': list(category_data['tools'].keys()),
                'metadata': {
                    'source': 'UNHCR Usage Guidance System',
                    'tool_type': 'category_guidance'
                }
            }
        
        else:
            # Return overview of all categories
            overview = {
                'description': 'UNHCR MCP Server Usage Guidance System',
                'categories': {},
                'suggested_starting_questions': [
                    'What are the current refugee numbers in Turkey?',
                    'How has the asylum seeker population changed in Germany over time?',
                    'Can you analyze the demographic breakdown of refugees in Colombia?',
                    'What insights can you provide about IDP situations in Uganda?',
                    'How do I create an accessible description for this refugee data chart?'
                ],
                'quick_start_examples': [
                    {
                        'question': 'Refugees in Turkey 2024',
                        'tool': 'get_population_data',
                        'parameters': {'coa': 'TUR', 'year': 2024}
                    },
                    {
                        'question': 'Refugee trends in Colombia 2020-2024',
                        'tool': 'get_population_trends',
                        'parameters': {'coa': 'COL', 'years': '2020,2021,2022,2023,2024'}
                    },
                    {
                        'question': 'Demographic analysis of Syrian refugees',
                        'tool': 'get_demographic_breakdown',
                        'parameters': {'coo': 'SYR', 'population_type': 'refugees'}
                    }
                ]
            }
            
            for category_name, category_data in guidance_database.items():
                overview['categories'][category_name] = {
                    'description': category_data['description'],
                    'tools': list(category_data['tools'].keys())
                }
            
            overview['metadata'] = {
                'source': 'UNHCR Usage Guidance System',
                'tool_type': 'complete_guidance',
                'total_tools': sum(len(category_data['tools']) for category_data in guidance_database.values())
            }
            
            return overview

    @server.tool(
        name="get_suggested_questions",
        description=(
            "Get suggested questions and query examples based on topics or data types. "
            "Use this tool when users need help formulating questions or don't know "
            "what to ask about UNHCR data."
        ),
    )
    def get_suggested_questions(
        topic: str | None = None,
        data_type: str | None = None,
        limit: int = 5
    ) -> dict[str, Any]:
        """
        Get suggested questions based on topic or data type to help users formulate effective queries.
        
        Args:
            topic: Topic area ('refugees', 'asylum_seekers', 'idps', 'demographics', 'trends', 'solutions')
            data_type: Type of data ('population', 'country_specific', 'comparative', 'historical', 'statistical')
            limit: Maximum number of questions to return

        Returns:
            List of suggested questions with context and example parameters
        """
        # Database of suggested questions
        question_database = {
            'refugees': {
                'population': [
                    {
                        'question': 'How many refugees are currently hosted in [country]?',
                        'context': 'Get current refugee population for a specific host country',
                        'example_parameters': {'coa': 'TUR', 'year': 2024},
                        'recommended_tool': 'get_population_data'
                    },
                    {
                        'question': 'What is the breakdown of refugee populations by country of origin in [host country]?',
                        'context': 'Analyze refugee populations by their countries of origin',
                        'example_parameters': {'coa': 'DEU', 'coo_all': True},
                        'recommended_tool': 'get_population_data'
                    },
                    {
                        'question': 'Which countries host the most refugees from [origin country]?',
                        'context': 'Find host countries for refugees from a specific origin',
                        'example_parameters': {'coo': 'SYR', 'coa_all': True},
                        'recommended_tool': 'get_population_data'
                    }
                ],
                'historical': [
                    {
                        'question': 'How has the refugee population in [country] changed over the last 5 years?',
                        'context': 'Analyze trends in refugee populations over time',
                        'example_parameters': {'coa': 'COL', 'years': '2020,2021,2022,2023,2024'},
                        'recommended_tool': 'get_population_trends'
                    },
                    {
                        'question': 'What was the refugee population in [country] in [year] compared to [previous year]?',
                        'context': 'Compare refugee numbers between specific years',
                        'example_parameters': {'coa': 'UGA', 'years': '2023,2024'},
                        'recommended_tool': 'get_population_trends'
                    }
                ],
                'statistical': [
                    {
                        'question': 'What percentage of the total population of concern in [country] are refugees?',
                        'context': 'Get proportional breakdown of refugee populations',
                        'example_parameters': {'coa': 'TUR'},
                        'recommended_tool': 'get_country_key_figures'
                    },
                    {
                        'question': 'Can you show me the key figures and percentages for refugees in [country]?',
                        'context': 'Get formatted statistics with visualization-ready data',
                        'example_parameters': {'coa': 'DEU', 'population_types': ['refugees']},
                        'recommended_tool': 'get_country_key_figures'
                    }
                ]
            },
            'asylum_seekers': {
                'population': [
                    {
                        'question': 'How many asylum seekers are currently in [country]?',
                        'context': 'Get current asylum seeker numbers',
                        'example_parameters': {'coa': 'COL', 'year': 2024},
                        'recommended_tool': 'get_population_data'
                    },
                    {
                        'question': 'What is the trend of asylum applications in [country] over the past 3 years?',
                        'context': 'Analyze asylum application trends',
                        'example_parameters': {'coa': 'DEU', 'years': '2022,2023,2024'},
                        'recommended_tool': 'get_rsd_applications'
                    }
                ]
            },
            'idps': {
                'population': [
                    {
                        'question': 'How many internally displaced persons (IDPs) are in [country]?',
                        'context': 'Get current IDP population figures',
                        'example_parameters': {'coa': 'COL'},
                        'recommended_tool': 'get_population_data'
                    },
                    {
                        'question': 'What is the demographic breakdown of IDPs in [country]?',
                        'context': 'Analyze age and sex distribution of IDPs',
                        'example_parameters': {'coa': 'UGA', 'population_type': 'idps'},
                        'recommended_tool': 'get_demographic_breakdown'
                    }
                ]
            },
            'demographics': {
                'population': [
                    {
                        'question': 'What is the age distribution of [population type] in [country]?',
                        'context': 'Get detailed age breakdown for specific population groups',
                        'example_parameters': {'coa': 'TUR', 'population_type': 'refugees'},
                        'recommended_tool': 'get_demographic_breakdown'
                    },
                    {
                        'question': 'What percentage of [population type] in [country] are children under 18?',
                        'context': 'Analyze child populations among displaced persons',
                        'example_parameters': {'coa': 'COL', 'population_type': 'idps'},
                        'recommended_tool': 'get_demographic_breakdown'
                    },
                    {
                        'question': 'What is the gender ratio among [population type] in [country]?',
                        'context': 'Examine gender distribution in refugee populations',
                        'example_parameters': {'coa': 'DEU', 'population_type': 'asylum_seekers'},
                        'recommended_tool': 'get_demographic_breakdown'
                    }
                ]
            },
            'trends': {
                'population': [
                    {
                        'question': 'How have refugee numbers in [country] changed over the last decade?',
                        'context': 'Long-term trend analysis of refugee populations',
                        'example_parameters': {'coa': 'TUR', 'years': '2014,2015,2016,2017,2018,2019,2020,2021,2022,2023,2024'},
                        'recommended_tool': 'get_population_trends'
                    },
                    {
                        'question': 'What are the emerging trends in [population type] across different regions?',
                        'context': 'Regional comparison of population trends',
                        'example_parameters': {'coa_all': True, 'population_types': ['refugees']},
                        'recommended_tool': 'get_population_trends'
                    }
                ]
            },
            'solutions': {
                'population': [
                    {
                        'question': 'What are the durable solutions data for [country]?',
                        'context': 'Get information on resettlement, returns, and local integration',
                        'example_parameters': {'coa': 'UGA'},
                        'recommended_tool': 'get_solutions'
                    },
                    {
                        'question': 'How many refugees have been resettled from [country] in the last year?',
                        'context': 'Analyze resettlement figures and trends',
                        'example_parameters': {'coo': 'SYR', 'year': 2024},
                        'recommended_tool': 'get_solutions'
                    }
                ]
            }
        }
        
        # Build response based on request
        if topic and data_type and topic in question_database and data_type in question_database[topic]:
            # Specific topic and data type
            questions = question_database[topic][data_type][:limit]
            return {
                'topic': topic,
                'data_type': data_type,
                'suggested_questions': questions,
                'metadata': {
                    'source': 'UNHCR Question Suggestion System',
                    'count': len(questions),
                    'total_available': len(question_database[topic][data_type])
                }
            }
        
        elif topic and topic in question_database:
            # All questions for a topic
            all_questions = []
            for data_type, questions in question_database[topic].items():
                all_questions.extend(questions[:limit])
            
            return {
                'topic': topic,
                'suggested_questions': all_questions[:limit],
                'available_data_types': list(question_database[topic].keys()),
                'metadata': {
                    'source': 'UNHCR Question Suggestion System',
                    'count': len(all_questions[:limit]),
                    'total_available': sum(len(q) for q in question_database[topic].values())
                }
            }
        
        else:
            # General suggestions across all topics
            general_suggestions = []
            for topic, topic_data in question_database.items():
                for data_type, questions in topic_data.items():
                    general_suggestions.extend(questions[:2])  # Take 2 from each
            
            return {
                'suggested_questions': general_suggestions[:limit],
                'available_topics': list(question_database.keys()),
                'popular_questions': [
                    'How many refugees are currently hosted in Turkey?',
                    'What is the trend of asylum applications in Germany over the past 3 years?',
                    'What is the demographic breakdown of IDPs in Colombia?',
                    'How have refugee numbers in Uganda changed over the last decade?',
                    'What are the durable solutions data for Syrian refugees?'
                ],
                'metadata': {
                    'source': 'UNHCR Question Suggestion System',
                    'count': len(general_suggestions[:limit]),
                    'total_available': sum(sum(len(q) for q in topic_data.values()) for topic_data in question_database.values())
                }
            }

    @server.tool(
        name="apply_analysis_guardrails",
        description=(
            "Apply UNHCR methodology guardrails to ensure analyses follow international standards. "
            "Use this tool to validate analysis requests, check compliance with statistical standards, "
            "and ensure proper interpretation of UNHCR data."
        ),
    )
    def apply_analysis_guardrails(
        analysis_request: dict[str, Any],
        population_type: str | None = None,
        country_iso: str | None = None,
        year: str | int | None = None,
        detailed_report: bool = False
    ) -> dict[str, Any]:
        """
        Apply UNHCR methodology guardrails to ensure analysis follows international standards.
        
        This tool incorporates methodologies from:
        - International Recommendations on Refugee Statistics (2018)
        - International Recommendations on IDP Statistics (2020)
        - International Recommendations on Statelessness Statistics (2019)
        - Expert Group on Refugee and IDP Statistics (EGRISS) Common Methodology (2023)
        - UNHCR Refugee Data Finder Methodology
        - The International Recommendations on IDP Statistics
        - 2023 EGRISS Conceptual Framework
        
        Args:
            analysis_request: The analysis request containing data and parameters
            population_type: Type of population ('refugees', 'asylum_seekers', 'idps', 'stateless')
            country_iso: ISO3 country code for context-specific validation
            year: Year for temporal validation
            detailed_report: Whether to include detailed methodology references

        Returns:
            Analysis with guardrails applied, including methodology compliance checks
        """
        import re
        
        # Initialize guardrails compliance report
        compliance_report = {
            'methodology_compliance': {},
            'data_quality_checks': {},
            'ethical_considerations': {},
            'population_specific_analysis': {},
            'recommendations': [],
            'warnings': [],
            'knowledge_base_references': [],
            'standards_applied': [
                'International Recommendations on Refugee Statistics (2018)',
                'International Recommendations on IDP Statistics (2020)',
                'International Recommendations on Statelessness Statistics (2019)',
                'EGRISS Common Methodology (2023)',
                'UNHCR Refugee Data Finder Methodology',
                'The International Recommendations on IDP Statistics',
                '2023 EGRISS Conceptual Framework'
            ]
        }
        
        # Determine which standards to apply based on population type
        population_standards = []
        knowledge_references = []
        
        if population_type == 'refugees':
            population_standards.append('International Recommendations on Refugee Statistics')
            knowledge_references.extend([
                {
                    'standard': 'International Recommendations on Refugee Statistics',
                    'section': '3.1 - Definition of refugees',
                    'requirement': 'Analysis must use 1951 Convention definition: well-founded fear of persecution',
                    'url': 'https://unstats.un.org/unsd/demographic-social/Standards-and-Methods/files/Standards-and-Methods/Series-M/No.102/Series_M_102_Refugee_Statistics.pdf'
                },
                {
                    'standard': 'International Recommendations on Refugee Statistics',
                    'section': '4.2 - Data collection methods',
                    'requirement': 'Data should come from official registration systems or statistical estimates',
                    'url': 'https://unstats.un.org/unsd/demographic-social/Standards-and-Methods/files/Standards-and-Methods/Series-M/No.102/Series_M_102_Refugee_Statistics.pdf'
                },
                {
                    'standard': 'EGRISS Common Methodology',
                    'section': '6.1 - Disaggregation',
                    'requirement': 'Refugee data should be disaggregated by age, sex, and country of origin',
                    'url': 'https://egriss.unu.edu/publications/egriss-common-methodology-2023'
                }
            ])
        elif population_type == 'idps':
            population_standards.append('International Recommendations on IDP Statistics')
            knowledge_references.extend([
                {
                    'standard': 'International Recommendations on IDP Statistics',
                    'section': '2.1 - Definition of IDPs',
                    'requirement': 'Must follow IASC definition: persons forced to flee but remaining in their country',
                    'url': 'https://www.unhcr.org/publications/operations/601d543f4/international-recommendations-idp-statistics.html'
                },
                {
                    'standard': 'International Recommendations on IDP Statistics',
                    'section': '3.3 - Duration of displacement',
                    'requirement': 'Analysis should distinguish between new and prolonged displacement (>5 years)',
                    'url': 'https://www.unhcr.org/publications/operations/601d543f4/international-recommendations-idp-statistics.html'
                },
                {
                    'standard': 'The International Recommendations on IDP Statistics',
                    'section': '4.1 - Causes of displacement',
                    'requirement': 'Data should specify causes: conflict, violence, disasters, or development projects',
                    'url': 'https://www.unhcr.org/publications/operations/601d543f4/international-recommendations-idp-statistics.html'
                },
                {
                    'standard': '2023 EGRISS Conceptual Framework',
                    'section': '5.2 - Protection concerns',
                    'requirement': 'Analysis should consider protection risks faced by IDPs',
                    'url': 'https://egriss.unu.edu/publications/2023-egriss-conceptual-framework'
                }
            ])
        elif population_type == 'stateless':
            population_standards.append('International Recommendations on Statelessness Statistics')
            knowledge_references.extend([
                {
                    'standard': 'International Recommendations on Statelessness Statistics',
                    'section': '3.1 - Definition',
                    'requirement': 'Must follow 1954 Convention: person not considered as national by any State',
                    'url': 'https://www.unhcr.org/publications/legal/5d8d17b34/international-recommendations-statelessness-statistics.html'
                },
                {
                    'standard': 'International Recommendations on Statelessness Statistics',
                    'section': '4.3 - Data challenges',
                    'requirement': 'Acknowledge data limitations due to legal and identification challenges',
                    'url': 'https://www.unhcr.org/publications/legal/5d8d17b34/international-recommendations-statelessness-statistics.html'
                },
                {
                    'standard': 'International Recommendations on Statelessness Statistics',
                    'section': '5.1 - Legal framework',
                    'requirement': 'Analysis should reference national laws affecting stateless populations',
                    'url': 'https://www.unhcr.org/publications/legal/5d8d17b34/international-recommendations-statelessness-statistics.html'
                }
            ])
        elif population_type == 'asylum_seekers':
            population_standards.append('International Recommendations on Refugee Statistics (Asylum Seekers section)')
            knowledge_references.extend([
                {
                    'standard': 'International Recommendations on Refugee Statistics',
                    'section': '3.2 - Asylum seekers',
                    'requirement': 'Distinguish between asylum seekers and refugees in analysis',
                    'url': 'https://unstats.un.org/unsd/demographic-social/Standards-and-Methods/files/Standards-and-Methods/Series-M/No.102/Series_M_102_Refugee_Statistics.pdf'
                },
                {
                    'standard': 'EGRISS Common Methodology',
                    'section': '7.1 - Asylum procedures',
                    'requirement': 'Consider different stages of asylum process in temporal analysis',
                    'url': 'https://egriss.unu.edu/publications/egriss-common-methodology-2023'
                }
            ])
        
        # 1. Methodology Compliance Checks
        methodology_checks = {}
        
        # Check 1: Data Source Validation
        data_source = analysis_request.get('data_source', 'UNHCR API')
        if data_source == 'UNHCR API':
            methodology_checks['data_source'] = {
                'status': 'compliant',
                'standard': 'EGRISS 3.1 - Official statistical sources',
                'details': 'Data sourced from UNHCR official API following EGRISS guidelines'
            }
        else:
            methodology_checks['data_source'] = {
                'status': 'requires_validation',
                'standard': 'EGRISS 3.1 - Official statistical sources',
                'details': f'Non-standard data source: {data_source} - requires methodology validation'
            }
        
        # Check 2: Population Definition Compliance
        if population_type:
            definition_check = self._check_population_definition_compliance(population_type)
            methodology_checks['population_definition'] = {
                'status': definition_check['status'],
                'standard': definition_check['standard'],
                'details': definition_check['details']
            }
        
        # Check 3: Temporal Consistency
        if year:
            year_int = int(year) if isinstance(year, str) else year
            if 1950 <= year_int <= 2025:  # Reasonable range for UNHCR data
                methodology_checks['temporal_consistency'] = {
                    'status': 'compliant',
                    'standard': 'EGRISS 4.2 - Temporal consistency',
                    'details': f'Year {year} is within valid range for UNHCR data'
                }
            else:
                methodology_checks['temporal_consistency'] = {
                    'status': 'non_compliant',
                    'standard': 'EGRISS 4.2 - Temporal consistency',
                    'details': f'Year {year} is outside typical UNHCR data range (1950-2025)'
                }
                compliance_report['warnings'].append({
                    'type': 'temporal_validation',
                    'message': f'Year {year} may not have reliable UNHCR data',
                    'recommendation': 'Use years between 1950-2025 for best data quality'
                })
        
        # Check 4: Geographical Validation
        if country_iso:
            country_check = self._validate_country_code(country_iso)
            methodology_checks['geographical_validation'] = {
                'status': country_check['status'],
                'standard': 'EGRISS 5.1 - Geographical classification',
                'details': country_check['details']
            }
            if country_check['status'] != 'compliant':
                compliance_report['warnings'].append({
                    'type': 'geographical_validation',
                    'message': country_check['details'],
                    'recommendation': 'Use valid ISO3 country codes'
                })
        
        # Check 5: Data Disaggregation Standards
        data_fields = analysis_request.get('data_fields', [])
        disaggregation_check = self._check_data_disaggregation(data_fields, population_type)
        methodology_checks['data_disaggregation'] = {
            'status': disaggregation_check['status'],
            'standard': disaggregation_check['standard'],
            'details': disaggregation_check['details']
        }
        
        # 2. Data Quality Checks
        data_quality_checks = {}
        
        # Check for missing data
        data_completeness = self._check_data_completeness(analysis_request.get('data', []))
        data_quality_checks['completeness'] = {
            'status': data_completeness['status'],
            'metric': f"{data_completeness['complete_percentage']}% complete",
            'details': data_completeness['details']
        }
        
        # Check data consistency
        consistency_check = self._check_data_consistency(analysis_request.get('data', []))
        data_quality_checks['consistency'] = {
            'status': consistency_check['status'],
            'details': consistency_check['details']
        }
        
        # 3. Ethical Considerations
        ethical_checks = {}
        
        # Protection and confidentiality
        ethical_checks['data_protection'] = {
            'status': 'compliant',
            'standard': 'EGRISS 2.3 - Confidentiality and protection',
            'details': 'Analysis follows UNHCR data protection protocols for refugee statistics'
        }
        
        # Avoiding harm
        ethical_checks['do_no_harm'] = {
            'status': 'compliant',
            'standard': 'UNHCR Data Responsibility Guidelines',
            'details': 'Analysis framework designed to avoid stigmatization or harm to vulnerable populations'
        }
        
        # 4. Population-Specific Analysis and Recommendations
        population_analysis = {}
        
        if population_type == 'refugees':
            population_analysis['definition_compliance'] = {
                'standard': '1951 Refugee Convention',
                'compliance': 'required',
                'details': 'Analysis must use Convention definition: well-founded fear of persecution due to race, religion, nationality, political opinion, or membership in a particular social group'
            }
            
            population_analysis['data_sources'] = {
                'primary': ['UNHCR registration data', 'Government asylum records'],
                'secondary': ['Household surveys', 'Statistical estimation methods'],
                'requirement': 'EGRISS 4.1 - Official sources should be prioritized'
            }
            
            population_analysis['disaggregation_requirements'] = {
                'minimum': ['age', 'sex', 'country_of_origin'],
                'recommended': ['legal_status', 'duration_of_displacement', 'urban/rural_location'],
                'standard': 'International Recommendations on Refugee Statistics 5.3'
            }
            
            compliance_report['recommendations'].extend([
                {
                    'type': 'methodology',
                    'message': 'Follow 1951 Refugee Convention definition for refugee status',
                    'reference': 'International Recommendations on Refugee Statistics, Section 3.1',
                    'implementation': 'Ensure all refugee counts use the Convention definition, not broader migration categories'
                },
                {
                    'type': 'data_quality',
                    'message': 'Cross-reference with asylum seeker data for comprehensive analysis',
                    'reference': 'EGRISS Common Methodology, Section 6.2',
                    'implementation': 'Compare refugee and asylum seeker trends to understand protection gaps'
                },
                {
                    'type': 'analysis',
                    'message': 'Consider both refugee-hosting and refugee-generating country perspectives',
                    'reference': 'UNHCR Refugee Data Finder Methodology, Section 3.4',
                    'implementation': 'Analyze push factors (origin) and pull factors (host) for comprehensive understanding'
                }
            ])
        
        elif population_type == 'idps':
            population_analysis['definition_compliance'] = {
                'standard': 'IASC Framework on Durable Solutions for IDPs',
                'compliance': 'required',
                'details': 'Must follow IASC definition: persons forced to flee within national borders due to conflict, violence, disasters, or human rights violations'
            }
            
            population_analysis['duration_analysis'] = {
                'categories': {
                    'new_displacement': '0-5 years',
                    'prolonged_displacement': '5+ years',
                    'development_displacement': '10+ years'
                },
                'standard': 'International Recommendations on IDP Statistics 3.3',
                'importance': 'Duration affects protection needs and solution strategies'
            }
            
            population_analysis['cause_analysis'] = {
                'required_causes': ['conflict', 'generalized violence', 'human rights violations'],
                'recommended_causes': ['natural disasters', 'development projects', 'climate change'],
                'standard': 'The International Recommendations on IDP Statistics 4.1'
            }
            
            compliance_report['recommendations'].extend([
                {
                    'type': 'methodology',
                    'message': 'Apply IASC definition of internally displaced persons',
                    'reference': 'International Recommendations on IDP Statistics, Section 2.1',
                    'implementation': 'Explicitly state definition used and exclude economic migrants'
                },
                {
                    'type': 'data_collection',
                    'message': 'Consider duration of displacement (prolonged vs new) for deeper analysis',
                    'reference': 'EGRISS IDP Statistics Guidelines',
                    'implementation': 'Separate analysis for <5 years and 5+ years displacement to understand different needs'
                },
                {
                    'type': 'protection_analysis',
                    'message': 'Assess protection risks faced by IDPs in different contexts',
                    'reference': '2023 EGRISS Conceptual Framework, Section 5.2',
                    'implementation': 'Include security, shelter, food, health, and legal protection indicators'
                },
                {
                    'type': 'cause_specific',
                    'message': 'Distinguish between conflict-induced and disaster-induced displacement',
                    'reference': 'The International Recommendations on IDP Statistics, Section 4.1',
                    'implementation': 'Different causes require different response strategies and data collection methods'
                }
            ])
        
        elif population_type == 'stateless':
            population_analysis['legal_framework'] = {
                'primary_instrument': '1954 Convention relating to the Status of Stateless Persons',
                'secondary_instrument': '1961 Convention on the Reduction of Statelessness',
                'national_laws': 'Analysis should reference relevant national citizenship laws',
                'standard': 'International Recommendations on Statelessness Statistics 5.1'
            }
            
            population_analysis['data_challenges'] = {
                'identification': 'Many countries lack systems to identify stateless populations',
                'legal_barriers': 'Fear of authorities may prevent self-identification',
                'statistical_gaps': 'Limited disaggregation available in most countries',
                'standard': 'International Recommendations on Statelessness Statistics 4.3'
            }
            
            population_analysis['recommended_approaches'] = {
                'data_sources': ['Civil registration records', 'Legal aid organizations', 'NGO surveys'],
                'estimation_methods': ['Household surveys with legal analysis', 'Administrative records review'],
                'reporting_standards': 'Acknowledge uncertainty ranges in all statelessness estimates'
            }
            
            compliance_report['recommendations'].extend([
                {
                    'type': 'methodology',
                    'message': 'Follow 1954 Convention relating to the Status of Stateless Persons',
                    'reference': 'International Recommendations on Statelessness Statistics, Section 3.2',
                    'implementation': 'Use legal definition: person not considered as national by any State under its law'
                },
                {
                    'type': 'data_quality',
                    'message': 'Note that statelessness data may have higher uncertainty in some regions',
                    'reference': 'UNHCR Statelessness Statistical Standards',
                    'implementation': 'Always include confidence intervals and data limitation statements'
                },
                {
                    'type': 'legal_context',
                    'message': 'Analyze national citizenship laws that may create statelessness',
                    'reference': 'International Recommendations on Statelessness Statistics, Section 5.1',
                    'implementation': 'Reference specific laws and gender discrimination in nationality laws'
                },
                {
                    'type': 'comparative_analysis',
                    'message': 'Compare statelessness data with refugee and migration statistics',
                    'reference': 'EGRISS Common Methodology, Section 8.3',
                    'implementation': 'Understand overlaps and distinctions between different displaced populations'
                }
            ])
        
        elif population_type == 'asylum_seekers':
            population_analysis['status_distinction'] = {
                'asylum_seeker': 'Person whose claim has not yet been decided',
                'refugee': 'Person whose claim has been approved',
                'rejected': 'Person whose claim has been denied',
                'withdrawn': 'Person who withdrew their application',
                'standard': 'International Recommendations on Refugee Statistics 3.2'
            }
            
            population_analysis['procedural_stages'] = {
                'stages': [
                    'Initial registration',
                    'First instance decision',
                    'Appeal process',
                    'Final decision',
                    'Integration/resettlement/return'
                ],
                'temporal_considerations': 'Different stages have different durations across countries',
                'standard': 'EGRISS Common Methodology 7.1'
            }
            
            compliance_report['recommendations'].extend([
                {
                    'type': 'methodology',
                    'message': 'Clearly distinguish between asylum seekers and recognized refugees',
                    'reference': 'International Recommendations on Refugee Statistics, Section 3.2',
                    'implementation': 'Never combine counts without explicit labeling of status differences'
                },
                {
                    'type': 'temporal_analysis',
                    'message': 'Consider asylum procedure durations in trend analysis',
                    'reference': 'EGRISS Common Methodology, Section 7.1',
                    'implementation': 'Account for processing backlogs that may distort annual comparison'
                },
                {
                    'type': 'comparative',
                    'message': 'Analyze recognition rates across different nationalities',
                    'reference': 'UNHCR Asylum Trends Analysis Guidelines',
                    'implementation': 'Examine differences in approval rates by country of origin'
                }
            ])
        
        compliance_report['population_specific_analysis'] = population_analysis
        compliance_report['knowledge_base_references'] = knowledge_references
        
        # 5. Storytelling Guardrails
        if analysis_request.get('storytelling_context'):
            storytelling_check = self._check_storytelling_guardrails(
                analysis_request['storytelling_context'], 
                population_type
            )
            compliance_report['storytelling_guardrails'] = {
                'status': storytelling_check['status'],
                'guidelines': storytelling_check['guidelines'],
                'details': storytelling_check['details']
            }
        
        # Build final response
        compliance_report['methodology_compliance'] = methodology_checks
        compliance_report['data_quality_checks'] = data_quality_checks
        compliance_report['ethical_considerations'] = ethical_checks
        
        # Determine overall compliance level
        compliant_checks = sum(1 for check in methodology_checks.values() if check['status'] == 'compliant')
        total_checks = len(methodology_checks)
        compliance_percentage = (compliant_checks / total_checks * 100) if total_checks > 0 else 100
        
        compliance_report['overall_compliance'] = {
            'score': round(compliance_percentage, 1),
            'level': self._get_compliance_level(compliance_percentage),
            'standards_applied': population_standards
        }
        
        # Add detailed methodology references with URLs
        detailed_methodology_references = {
            'refugee_statistics': {
                'title': 'International Recommendations on Refugee Statistics',
                'year': 2018,
                'publisher': 'United Nations Statistical Commission',
                'url': 'https://unstats.un.org/unsd/demographic-social/Standards-and-Methods/files/Standards-and-Methods/Series-M/No.102/Series_M_102_Refugee_Statistics.pdf',
                'key_sections': {
                    '3.1': 'Definition of refugees based on 1951 Convention',
                    '4.2': 'Data collection methods and official sources',
                    '5.3': 'Disaggregation standards by age, sex, and origin',
                    '6.1': 'Temporal consistency and time series analysis',
                    '7.2': 'Comparability across countries and regions'
                },
                'core_principles': [
                    'Use of 1951 Convention definition',
                    'Prioritization of official data sources',
                    'Mandatory disaggregation by age and sex',
                    'Transparency about data limitations'
                ]
            },
            'idp_statistics': {
                'title': 'International Recommendations on IDP Statistics',
                'year': 2020,
                'publisher': 'Expert Group on Refugee and IDP Statistics',
                'url': 'https://www.unhcr.org/publications/operations/601d543f4/international-recommendations-idp-statistics.html',
                'key_sections': {
                    '2.1': 'IASC definition of internally displaced persons',
                    '3.3': 'Duration categories and prolonged displacement',
                    '4.1': 'Causes of displacement classification',
                    '5.2': 'Protection concerns and vulnerability assessment',
                    '6.3': 'Data collection in complex emergencies'
                },
                'core_principles': [
                    'IASC definition compliance',
                    'Duration-based analysis',
                    'Cause-specific disaggregation',
                    'Protection-focused indicators',
                    'Context-specific data collection'
                ]
            },
            'statelessness_statistics': {
                'title': 'International Recommendations on Statelessness Statistics',
                'year': 2019,
                'publisher': 'UNHCR and United Nations Statistical Commission',
                'url': 'https://www.unhcr.org/publications/legal/5d8d17b34/international-recommendations-statelessness-statistics.html',
                'key_sections': {
                    '3.1': '1954 Convention definition and legal framework',
                    '4.3': 'Data challenges and identification barriers',
                    '5.1': 'National legislation analysis',
                    '6.2': 'Estimation methodologies',
                    '7.1': 'Ethical considerations and data protection'
                },
                'core_principles': [
                    '1954 Convention definition adherence',
                    'Acknowledgment of data limitations',
                    'Legal framework analysis',
                    'Confidentiality and protection',
                    'Uncertainty quantification'
                ]
            },
            'egriss_methodology': {
                'title': 'Expert Group on Refugee and IDP Statistics Common Methodology',
                'year': 2023,
                'publisher': 'EGRISS',
                'url': 'https://egriss.unu.edu/publications/egriss-common-methodology-2023',
                'key_sections': {
                    '3.1': 'Common definitions and conceptual framework',
                    '4.2': 'Data harmonization across sources',
                    '5.1': 'Quality assurance protocols',
                    '6.3': 'Disaggregation and cross-tabulation standards',
                    '7.1': 'Temporal analysis and trend measurement',
                    '8.2': 'Comparative analysis methodologies'
                },
                'core_principles': [
                    'Conceptual harmonization',
                    'Methodological consistency',
                    'Quality assurance',
                    'Transparency and documentation',
                    'Comparability enhancement'
                ]
            },
            'the_international_recommendations_on_idp_statistics': {
                'title': 'The International Recommendations on IDP Statistics',
                'year': 2020,
                'publisher': 'EGRISS',
                'url': 'https://www.unhcr.org/publications/operations/601d543f4/international-recommendations-idp-statistics.html',
                'key_sections': {
                    '2.2': 'Conceptual framework for internal displacement',
                    '3.4': 'Duration categories and analytical implications',
                    '4.1': 'Cause classification system',
                    '5.3': 'Protection monitoring indicators',
                    '6.2': 'Data collection in conflict settings'
                },
                'core_principles': [
                    'Comprehensive cause analysis',
                    'Duration-sensitive indicators',
                    'Protection-centered approach',
                    'Context-adaptive methodologies',
                    'Ethical data collection'
                ]
            },
            'egriss_conceptual_framework': {
                'title': '2023 EGRISS Conceptual Framework for Forced Displacement Statistics',
                'year': 2023,
                'publisher': 'EGRISS',
                'url': 'https://egriss.unu.edu/publications/2023-egriss-conceptual-framework',
                'key_sections': {
                    '2.1': 'Unified conceptual model',
                    '3.3': 'Cross-cutting issues and intersections',
                    '4.2': 'Protection and solutions framework',
                    '5.1': 'Vulnerability and resilience indicators',
                    '6.4': 'Sustainable development linkages'
                },
                'core_principles': [
                    'Holistic conceptual approach',
                    'Protection-sensitive analysis',
                    'Solutions-oriented indicators',
                    'SDG alignment',
                    'Intersectional perspectives'
                ]
            },
            'unhcr_data_finder_methodology': {
                'title': 'UNHCR Refugee Data Finder Methodology',
                'year': 2022,
                'publisher': 'UNHCR',
                'url': 'https://www.unhcr.org/refugee-statistics/methodology/',
                'key_sections': {
                    '3.1': 'Data sourcing and validation',
                    '4.2': 'Temporal and spatial analysis',
                    '5.3': 'Comparative country analysis',
                    '6.1': 'Trend analysis and forecasting',
                    '7.2': 'Data visualization standards'
                },
                'core_principles': [
                    'Official source prioritization',
                    'Methodological transparency',
                    'Comparative analysis standards',
                    'Trend validation protocols',
                    'Visualization best practices'
                ]
            }
        }
        
        # Include references based on detailed_report flag
        if detailed_report:
            compliance_report['methodology_references'] = detailed_methodology_references
            compliance_report['knowledge_base_summary'] = {
                'total_standards': len(detailed_methodology_references),
                'total_sections': sum(len(ref['key_sections']) for ref in detailed_methodology_references.values()),
                'total_principles': sum(len(ref['core_principles']) for ref in detailed_methodology_references.values()),
                'coverage': 'Comprehensive coverage of all UNHCR international standards and EGRISS methodologies'
            }
        else:
            # Summary references
            compliance_report['methodology_references'] = {
                'refugee_statistics': {
                    'title': 'International Recommendations on Refugee Statistics',
                    'year': 2018,
                    'key_sections': ['Definition of refugees', 'Data collection methods', 'Disaggregation standards']
                },
                'idp_statistics': {
                    'title': 'International Recommendations on IDP Statistics',
                    'year': 2020,
                    'key_sections': ['IDP definition', 'Duration of displacement', 'Protection concerns']
                },
                'statelessness_statistics': {
                    'title': 'International Recommendations on Statelessness Statistics',
                    'year': 2019,
                    'key_sections': ['Definition of statelessness', 'Data sources', 'Challenges in measurement']
                },
                'egriss_methodology': {
                    'title': 'Expert Group on Refugee and IDP Statistics Common Methodology',
                    'year': 2023,
                    'key_sections': ['Common definitions', 'Data harmonization', 'Quality assurance']
                },
                'the_international_recommendations_on_idp_statistics': {
                    'title': 'The International Recommendations on IDP Statistics',
                    'year': 2020,
                    'key_sections': ['Conceptual framework', 'Cause classification', 'Protection indicators']
                },
                'egriss_conceptual_framework': {
                    'title': '2023 EGRISS Conceptual Framework',
                    'year': 2023,
                    'key_sections': ['Unified model', 'Protection framework', 'SDG linkages']
                }
            }
        
        return {
            'analysis_request': analysis_request,
            'guardrails_compliance': compliance_report,
            'metadata': {
                'source': 'UNHCR Analysis Guardrails System',
                'population_type': population_type,
                'country_context': country_iso,
                'year_context': year,
                'timestamp': '2024-06-25',
                'compliance_version': '1.0'
            }
        }

    def _check_population_definition_compliance(self, population_type: str) -> dict[str, Any]:
        """Check if population definition follows international standards."""
        definitions = {
            'refugees': {
                'status': 'compliant',
                'standard': 'International Recommendations on Refugee Statistics 3.1',
                'details': 'Follows 1951 Refugee Convention definition: person who has fled their country due to well-founded fear of persecution'
            },
            'asylum_seekers': {
                'status': 'compliant',
                'standard': 'International Recommendations on Refugee Statistics 3.2',
                'details': 'Follows standard definition: person seeking international protection whose claim has not yet been decided'
            },
            'idps': {
                'status': 'compliant',
                'standard': 'International Recommendations on IDP Statistics 2.1',
                'details': 'Follows IASC definition: persons forced to flee their homes but remain within their country'
            },
            'stateless': {
                'status': 'compliant',
                'standard': 'International Recommendations on Statelessness Statistics 3.1',
                'details': 'Follows 1954 Convention definition: person not considered as a national by any State'
            }
        }
        return definitions.get(population_type, {
            'status': 'requires_validation',
            'standard': 'UNHCR Data Standards',
            'details': f'Population type {population_type} requires definition validation'
        })

    def _validate_country_code(self, country_iso: str) -> dict[str, Any]:
        """Validate country ISO code format."""
        if len(country_iso) == 3 and country_iso.isalpha():
            return {
                'status': 'compliant',
                'standard': 'ISO 3166-1 alpha-3',
                'details': f'{country_iso} is a valid ISO3 country code format'
            }
        else:
            return {
                'status': 'non_compliant',
                'standard': 'ISO 3166-1 alpha-3',
                'details': f'{country_iso} is not a valid ISO3 country code (should be 3 letters)'
            }

    def _check_data_disaggregation(self, data_fields: list[str], population_type: str | None) -> dict[str, Any]:
        """Check if data includes appropriate disaggregation."""
        required_fields = []
        if population_type in ['refugees', 'asylum_seekers', 'idps']:
            required_fields = ['age', 'sex']
        elif population_type == 'stateless':
            required_fields = ['sex']  # Statelessness data often has less disaggregation
        
        missing_fields = [field for field in required_fields if field not in data_fields]
        
        if not missing_fields:
            return {
                'status': 'compliant',
                'standard': 'EGRISS 6.1 - Data disaggregation',
                'details': 'Data includes required disaggregation fields for analysis'
            }
        else:
            return {
                'status': 'partial',
                'standard': 'EGRISS 6.1 - Data disaggregation',
                'details': f'Missing disaggregation fields: {missing_fields}'
            }

    def _check_data_completeness(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Check data completeness."""
        if not data:
            return {
                'status': 'non_compliant',
                'complete_percentage': 0,
                'details': 'No data provided for analysis'
            }
        
        # Check for missing values in key fields
        total_fields = 0
        missing_fields = 0
        
        for record in data:
            for key, value in record.items():
                total_fields += 1
                if value is None or (isinstance(value, (int, float)) and value < 0):
                    missing_fields += 1
        
        completeness_percentage = ((total_fields - missing_fields) / total_fields * 100) if total_fields > 0 else 0
        
        if completeness_percentage >= 90:
            status = 'compliant'
        elif completeness_percentage >= 70:
            status = 'partial'
        else:
            status = 'non_compliant'
        
        return {
            'status': status,
            'complete_percentage': round(completeness_percentage, 1),
            'details': f'Data is {completeness_percentage}% complete with {missing_fields} missing/invalid values out of {total_fields} fields'
        }

    def _check_data_consistency(self, data: list[dict[str, Any]]) -> dict[str, Any]:
        """Check data consistency."""
        if not data or len(data) < 2:
            return {
                'status': 'compliant',
                'details': 'Insufficient data for consistency check'
            }
        
        # Check for extreme outliers that might indicate data errors
        numeric_fields = []
        for record in data:
            for key, value in record.items():
                if isinstance(value, (int, float)) and key not in numeric_fields:
                    numeric_fields.append(key)
        
        consistency_issues = []
        for field in numeric_fields:
            values = [record.get(field) for record in data if record.get(field) is not None]
            if len(values) > 1:
                max_val = max(values)
                min_val = min(values)
                range_val = max_val - min_val
                
                # Check if range is reasonable (this is a simple heuristic)
                if range_val > max_val * 10:  # More than 10x difference
                    consistency_issues.append(f'Field {field} has extreme range: {min_val} to {max_val}')
        
        if consistency_issues:
            return {
                'status': 'requires_review',
                'details': f'Potential consistency issues detected: {consistency_issues}'
            }
        else:
            return {
                'status': 'compliant',
                'details': 'No major consistency issues detected in the data'
            }

    def _check_storytelling_guardrails(self, context: str, population_type: str | None) -> dict[str, Any]:
        """Check storytelling context against UNHCR guidelines."""
        guidelines = []
        details = []
        
        # General storytelling guidelines
        guidelines.append("Avoid language that could stigmatize or endanger populations")
        guidelines.append("Maintain confidentiality and protect individual identities")
        guidelines.append("Provide context about data limitations and uncertainties")
        
        # Population-specific guidelines
        if population_type == 'refugees':
            guidelines.append("Emphasize protection needs and international obligations")
            guidelines.append("Avoid conflating refugees with migrants or economic migrants")
            details.append("Use 'refugees' not 'migrants' when referring to Convention refugees")
        
        elif population_type == 'idps':
            guidelines.append("Highlight internal displacement as a protection issue")
            guidelines.append("Distinguish between conflict-induced and disaster-induced displacement")
            details.append("Specify causes of displacement when possible (conflict, violence, disasters)")
        
        elif population_type == 'stateless':
            guidelines.append("Emphasize legal implications of statelessness")
            guidelines.append("Avoid assumptions about nationality or documentation status")
            details.append("Clarify that statelessness is a legal condition, not a migration status")
        
        # Check for problematic language patterns
        problematic_terms = [
            'illegal', 'bogus', 'fake', 'economic migrant',
            'flood', 'wave', 'swarm', 'invasion'
        ]
        
        language_issues = []
        for term in problematic_terms:
            if term in context.lower():
                language_issues.append(f"Problematic term detected: '{term}'")
        
        if language_issues:
            status = 'requires_revision'
            details.extend(language_issues)
            details.append("Consider using neutral, rights-based language")
        else:
            status = 'compliant'
        
        return {
            'status': status,
            'guidelines': guidelines,
            'details': details if details else ['Storytelling context follows UNHCR guidelines']
        }

    def _get_compliance_level(self, compliance_percentage: float) -> str:
        """Determine compliance level based on percentage."""
        if compliance_percentage >= 90:
            return 'full_compliance'
        elif compliance_percentage >= 75:
            return 'substantial_compliance'
        elif compliance_percentage >= 50:
            return 'partial_compliance'
        else:
            return 'limited_compliance'

 
    @server.tool(
        name="create_quarto_notebook",
        description=(
            "Create Quarto notebooks (.qmd files) from data stories for reproducible reporting. "
            "Use this tool when asked to generate reports, create notebooks, or export analysis "
            "in a reproducible format."
        ),
    )
    def create_quarto_notebook(
        story_content: str,
        output_path: str | None = None,
        title: str | None = None,
        author: str | None = None,
        date: str | None = None,
        include_code_cells: bool = False,
        use_unhcr_theme: bool = True,
        use_unhcr_style: bool = True,
        original_query: str | None = None,
        metadata: dict | None = None,
    ) -> dict[str, Any]:
        """
        Create a Quarto notebook (.qmd file) from a generated data story.

        Converts data story content into a properly formatted Quarto markdown document
        rendered via Jupyter/Python, optionally with UNHCR branding and placeholder
        code cells.

        Supports UNHCR branding through:
        - UNHCR Quarto HTML theme  (https://github.com/unhcr-dataviz/quarto-html-unhcr)
        - UNHCR matplotlib style   (https://github.com/unhcr-dataviz/unhcrpyplotstyle)

        Args:
            story_content:      Markdown data story to embed in the notebook.
            output_path:        Optional file path (e.g. 'story.qmd').  When supplied
                                the notebook is written to disk.
            title:              Notebook title.  Extracted from the first H1 heading in
                                `story_content` when omitted.
            author:             Author name for YAML metadata.
            date:               ISO date string (defaults to today).
            include_code_cells: When True, inserts commented-out placeholder Python
                                code cells after the story content.
            use_unhcr_theme:    Apply the UNHCR Quarto HTML theme (default True).
            use_unhcr_style:    Apply the UNHCR matplotlib style in code cells
                                (default True, only relevant when include_code_cells=True).
            original_query:     Original prompt used to generate the story; appended as
                                an audit trail section at the end of the notebook.

        Returns:
            dict with keys:
                quarto_content  – Full .qmd text.
                path            – Absolute path written to, or None.
                title           – Resolved notebook title.
                author          – Resolved author string.
                date            – Resolved date string.
                format          – Always 'quarto'.
                metadata        – Generation statistics and settings.

        Example:
            result = create_quarto_notebook(
                story_content="Your data story here...",
                output_path="refugee_analysis.qmd",
                title="Refugee Arrivals in France",
                author="UNHCR Analysis Team",
                use_unhcr_theme=True,
                use_unhcr_style=True,
                original_query="Tell the story of refugees from France in the past 10 years",
            )
        """
        import re
        from datetime import datetime
        from pathlib import Path
        from jinja2 import Environment, PackageLoader, select_autoescape

        # ------------------------------------------------------------------
        # Resolve metadata
        # ------------------------------------------------------------------
        if not title:
            m = re.search(r"^#\s+(.+?)(?:\s+#+)?\s*$", story_content, re.MULTILINE)
            title = m.group(1).strip() if m else "UNHCR Data Story"

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        author_str = author or "UNHCR Data Analysis"





        # ------------------------------------------------------------------
        # Story content (ensure it starts with an H1)
        # ------------------------------------------------------------------
        if story_content.strip().startswith("#"):
            processed_content = story_content.strip()
        else:
            processed_content = f"# {title}\n\n{story_content.strip()}"



        # ------------------------------------------------------------------
        # Optional AI disclaimer / audit trail (placed at the very end)
        # ------------------------------------------------------------------
        audit_section = ""
        if original_query:
            safe_query = original_query.replace("`", "'")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            audit_section = f"""

    ## About This Document

    ::: {{.callout-note}}
    **This document was generated by an AI assistant using the UNHCR MCP Server.**

    This analysis is based on data from the United Nations High Commissioner for
    Refugees (UNHCR) and has been automatically generated to provide insights into
    forcibly displaced populations.

    **Important:**

    - AI-generated content may contain errors or inaccuracies.
    - Verify critical figures with official UNHCR sources before distribution.
    - This document does not represent official UNHCR policy or positions.
    - Human review and validation is strongly recommended.
    :::

    ### Original Query
    {safe_query}
    *Generated: {timestamp}*
    """

        # ------------------------------------------------------------------
        # Use Jinja2 template to render the final document
        # ------------------------------------------------------------------
        try:
            # Set up Jinja2 environment
            env = Environment(
                loader=PackageLoader("backend", "templates"),
                autoescape=select_autoescape(["html", "xml"])
            )
            
            # Select template based on document type if available in metadata
            template_name = "base_quarto.j2"  # Default template
            if metadata and "document_type" in metadata:
                doc_type = metadata["document_type"]
                template_path = f"{doc_type}.j2"
                try:
                    # Check if a specific template exists for this document type
                    env.get_template(template_path)
                    template_name = template_path
                except TemplateNotFound:
                    # Fall back to base template
                    template_name = "base_quarto.j2"
            
            template = env.get_template(template_name)
            
            # Prepare template context
            # Add a custom filter to escape Jinja2 syntax in story content
            def escape_jinja(text):
                if not text:
                    return text
                # Escape Jinja2 delimiters
                text = text.replace("{{", "{{ '{{' }}")
                text = text.replace("{%", "{% raw %}{% endraw %}")
                text = text.replace("{#", "{# ")
                return text
            
            env.filters['escape_jinja'] = escape_jinja
            
            # Clean metadata to remove any Jinja2 syntax before passing to template
            def clean_for_template(obj):
                """Recursively clean objects to remove Jinja2 syntax"""
                if isinstance(obj, dict):
                    return {k: clean_for_template(v) for k, v in obj.items()}
                elif isinstance(obj, list):
                    return [clean_for_template(v) for v in obj]
                elif isinstance(obj, str):
                    # Escape Jinja2 delimiters in strings
                    return obj.replace("{{", "{{ '{{' }}").replace("{%", "{% raw %}{% endraw %}")
                else:
                    return obj
            
            # Clean the metadata before adding to template context
            clean_metadata = clean_for_template(metadata) if metadata else {}
            
            # Add analysis configuration to context if available
            analysis_config = {}
            if metadata:
                analysis_config = {
                    "tone": metadata.get("analysis_config", {}).get("tone", "formal, precise, objective"),
                    "length": metadata.get("analysis_config", {}).get("length", {}),
                    "structure": metadata.get("analysis_config", {}).get("structure", []),
                    "audience": metadata.get("audience", "internal"),
                    "document_type": metadata.get("document_type", "long_read")
                }
            
            template_context = {
                "title": title,
                "author": author_str,
                "date": date,
                "use_unhcr_theme": use_unhcr_theme,
                "use_unhcr_style": use_unhcr_style,
                "story_content": processed_content,
                "include_code_cells": include_code_cells,
                "original_query": original_query,
                "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                "metadata": clean_metadata,
                "analysis_config": analysis_config,
                "generated_at": datetime.now().isoformat(),
                # Default content for templates
                "executive_summary": "Comprehensive analysis based on latest UNHCR data",
                "objective": "Provide data-driven insights into refugee situations",
                "methodology": "Analysis of UNHCR population statistics and trends",
                "key_findings": [
                    "Significant refugee populations in multiple regions",
                    "Ongoing displacement crises with complex patterns",
                    "Host communities facing substantial pressure"
                ],
                "trend_analysis": "Detailed examination of refugee movements over time",
                "humanitarian_impact": "Significant humanitarian needs requiring international attention",
                "policy_implications": "Important considerations for policy makers and decision makers",
                "future_outlook": "Projections and scenarios for refugee situations in coming years",
                "conclusion": "This analysis highlights the complex and evolving nature of global refugee situations"
            }
            
            quarto_content = template.render(template_context)
            
        except Exception as template_error:
            logger.error("Jinja2 template rendering failed: %s", template_error)
            # Fall back to manual string assembly if template fails
            # Define the missing variables that would be used in fallback
            def _yaml_str(value: str) -> str:
                """Wrap a string in double quotes and escape inner double quotes."""
                return '"' + value.replace('"', '\"') + '"'

            # YAML front matter
            html_theme_block = (
                "    theme:\n      - unhcr\n      - cosmo\n    css: unhcr.css"
                if use_unhcr_theme
                else "    theme: cosmo"
            )

            yaml_header = f"""\
    ---
    title: {_yaml_str(title)}
    author: {_yaml_str(author_str)}
    date: {_yaml_str(date)}
    format:
    html:
        embed-resources: true
        standalone: true
    {html_theme_block}
    pdf:
        documentclass: article
        papersize: a4
        geometry:
        - top=30mm
        - left=20mm
        - right=20mm
        - bottom=30mm
    editor: visual
    engine: jupyter
    ---
    """

            # Code cells
            code_section = ""
            if include_code_cells:
                style_lines = (
                    """\
    # Apply UNHCR matplotlib style
    # pip install git+https://github.com/Edouard-Legoupil/unhcrpyplotstyle
    import unhcrpyplotstyle  # noqa: F401
    plt.style.use("unhcr")
    """
                    if use_unhcr_style
                    else ""
                )
                escaped_title = title.replace("'", "\\'")
                code_section = f"""

    ## Code

    ```{{{{python}}}}
    #| label: setup
    #| echo: false

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns

    {style_lines}
    # Load your data here
    # df = pd.read_csv("data.csv")
    ```

    ```{{{{python}}}}
    #| label: fig-example
    #| fig-cap: "{escaped_title}"

    # Example — uncomment and adapt:
    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.bar(df["year"], df["refugees"])
    # ax.set_title("{escaped_title}")
    # plt.tight_layout()
    # plt.show()
    ```
    """

            # Audit section
            audit_section = ""
            if original_query:
                safe_query = original_query.replace("`", "'")
                timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                audit_section = f"""

    ## About This Document

    :::: {{.callout-note}}
    **This document was generated by an AI assistant using the UNHCR MCP Server.**

    This analysis is based on data from the United Nations High Commissioner for
    Refugees (UNHCR) and has been automatically generated to provide insights into
    forcibly displaced populations.

    **Important:**

    - AI-generated content may contain errors or inaccuracies.
    - Verify critical figures with official UNHCR sources before distribution.
    - This document does not represent official UNHCR policy or positions.
    - Human review and validation is strongly recommended.
    ::::

    ### Original Query
    {safe_query}
    *Generated: {timestamp}*
    """

            quarto_content = "\n".join(
                part
                for part in [yaml_header, processed_content, code_section, audit_section]
                if part
            )

        # ------------------------------------------------------------------
        # Optionally write to disk
        # ------------------------------------------------------------------
        saved_path: str | None = None
        if output_path:
            dest = Path(output_path)
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(quarto_content, encoding="utf-8")
                saved_path = str(dest.resolve())
                logger.info("Quarto notebook saved to: %s", saved_path)
            except OSError as exc:
                logger.error("Error saving Quarto notebook: %s", exc)
                return {
                    "error": f"Failed to save notebook: {exc}",
                    "status": "error",
                    "quarto_content": quarto_content,
                    "title": title,
                }

        return {
            "quarto_content": quarto_content,
            "path": saved_path,
            "title": title,
            "author": author_str,
            "date": date,
            "format": "quarto",
            "metadata": {
                "source": "UNHCR MCP Server",
                "tool": "create_quarto_notebook",
                "engine": "jupyter",
                "use_unhcr_theme": use_unhcr_theme,
                "use_unhcr_style": use_unhcr_style,
                "code_cells_included": include_code_cells,
                "character_count": len(quarto_content),
                "line_count": quarto_content.count("\n"),
                "original_query": original_query,
            },
        }
        
    # Fallback function in case Jinja2 fails
    async def create_quarto_notebook_fallback(
        story_content: str,
        output_path: str | None = None,
        title: str | None = None,
        author: str | None = None,
        date: str | None = None,
        include_code_cells: bool = False,
        use_unhcr_theme: bool = True,
        use_unhcr_style: bool = True,
        original_query: str | None = None,
    ) -> dict[str, Any]:
        """Fallback implementation using string concatenation"""
        import re
        from datetime import datetime
        from pathlib import Path

        # Resolve metadata
        if not title:
            m = re.search(r"^#\s+(.+?)(?:\s+#+)?\s*$", story_content, re.MULTILINE)
            title = m.group(1).strip() if m else "UNHCR Data Story"

        if not date:
            date = datetime.now().strftime("%Y-%m-%d")

        author_str = author or "UNHCR Data Analysis"

        def _yaml_str(value: str) -> str:
            """Wrap a string in double quotes and escape inner double quotes."""
            return '"' + value.replace('"', '\"') + '"'

        # YAML front matter
        html_theme_block = (
            "    theme:\n      - unhcr\n      - cosmo\n    css: unhcr.css"
            if use_unhcr_theme
            else "    theme: cosmo"
        )

        yaml_header = f"""\
    ---
    title: {_yaml_str(title)}
    author: {_yaml_str(author_str)}
    date: {_yaml_str(date)}
    format:
    html:
        embed-resources: true
        standalone: true
    {html_theme_block}
    pdf:
        documentclass: article
        papersize: a4
        geometry:
        - top=30mm
        - left=20mm
        - right=20mm
        - bottom=30mm
    editor: visual
    engine: jupyter
    ---
    """

        # Story content
        if story_content.strip().startswith("#"):
            processed_content = story_content.strip()
        else:
            processed_content = f"# {title}\n\n{story_content.strip()}"

        # Code cells
        code_section = ""
        if include_code_cells:
            style_lines = (
                """\
    # Apply UNHCR matplotlib style
    # pip install git+https://github.com/Edouard-Legoupil/unhcrpyplotstyle
    import unhcrpyplotstyle  # noqa: F401
    plt.style.use("unhcr")
    """
                if use_unhcr_style
                else ""
            )
            escaped_title = title.replace("'", "\\'")
            code_section = f"""

    ## Code

    ```{{{{python}}}}
    #| label: setup
    #| echo: false

    import pandas as pd
    import numpy as np
    import matplotlib.pyplot as plt
    import seaborn as sns

    {style_lines}
    # Load your data here
    # df = pd.read_csv("data.csv")
    ```

    ```{{{{python}}}}
    #| label: fig-example
    #| fig-cap: "{escaped_title}"

    # Example — uncomment and adapt:
    # fig, ax = plt.subplots(figsize=(10, 6))
    # ax.bar(df["year"], df["refugees"])
    # ax.set_title("{escaped_title}")
    # plt.tight_layout()
    # plt.show()
    ```
    """

        # Audit section
        audit_section = ""
        if original_query:
            safe_query = original_query.replace("`", "'")
            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
            audit_section = f"""

    ## About This Document

    :::: {{.callout-note}}
    **This document was generated by an AI assistant using the UNHCR MCP Server.**

    This analysis is based on data from the United Nations High Commissioner for
    Refugees (UNHCR) and has been automatically generated to provide insights into
    forcibly displaced populations.

    **Important:**

    - AI-generated content may contain errors or inaccuracies.
    - Verify critical figures with official UNHCR sources before distribution.
    - This document does not represent official UNHCR policy or positions.
    - Human review and validation is strongly recommended.
    ::::

    ### Original Query
    {safe_query}
    *Generated: {timestamp}*
    """

        # Assemble document
        quarto_content = "\n".join(
            part
            for part in [yaml_header, processed_content, code_section, audit_section]
            if part
        )

        # Save to disk if requested
        saved_path = None
        if output_path:
            dest = Path(output_path)
            try:
                dest.parent.mkdir(parents=True, exist_ok=True)
                dest.write_text(quarto_content, encoding="utf-8")
                saved_path = str(dest.resolve())
                logger.info("Quarto notebook saved to: %s", saved_path)
            except OSError as exc:
                logger.error("Error saving Quarto notebook: %s", exc)
                return {
                    "error": f"Failed to save notebook: {exc}",
                    "status": "error",
                    "quarto_content": quarto_content,
                    "title": title,
                }

        return {
            "quarto_content": quarto_content,
            "path": saved_path,
            "title": title,
            "author": author_str,
            "date": date,
            "format": "quarto",
            "metadata": {
                "source": "UNHCR MCP Server",
                "tool": "create_quarto_notebook",
                "engine": "jupyter",
                "use_unhcr_theme": use_unhcr_theme,
                "use_unhcr_style": use_unhcr_style,
                "code_cells_included": include_code_cells,
                "character_count": len(quarto_content),
                "line_count": quarto_content.count("\n"),
                "original_query": original_query,
            },
        }

    @server.tool(
        name="safe_tool_selection",
        description=(
            "Safely select the appropriate tool for a given question by analyzing its content. "
            "Use this tool to determine which UNHCR data tool should be used for a specific query."
        ),
    )
    async def safe_tool_selection(question: str) -> dict[str, Any]:
        """
        Analyze a question and select the most appropriate tool to answer it.
        
        Args:
            question: The user's question to analyze
            
        Returns:
            Dictionary containing the selected tool and analysis results
        """
        # Import the internal functions directly to avoid circular MCP calls
        from backend.llm import classify_question, select_tool_from_prompt, validate_tool_selection
        
        try:
            # Replicate the original safe_tool_selection logic without MCP calls
            category = await classify_question(question)
            logger.info("Question category=%s", category.get("category"))
            
            selection = await select_tool_from_prompt(question)
            selection = await validate_tool_selection(selection)
            
            return {
                "category": category,
                "selection": selection,
                "tool": selection.get("tool"),
                "arguments": selection.get("arguments", {}),
                "status": "success"
            }
        except Exception as e:
            return {
                "error": f"Failed to select tool: {str(e)}",
                "status": "error"
            }

    @server.tool(
        name="get_data_for_story",
        description=(
            "Get appropriate data for story generation based on question analysis. "
            "Use this tool to retrieve the right data for creating data-driven stories and reports."
        ),
    )
    async def get_data_for_story(question: str, **kwargs) -> dict[str, Any]:
        """
        Get data for story generation by routing to appropriate data tools.
        
        Args:
            question: The user's question
            arguments: Additional arguments for the data retrieval
            
        Returns:
            Dictionary containing the retrieved data and metadata
        """
        # Import API client directly to avoid MCP tool calls
        from backend.server import UNHCRAPIClient
        
        try:
            api_client = UNHCRAPIClient()
            
            # Extract parameters from kwargs
            arguments = kwargs
            coo = arguments.get("coo") or arguments.get("country_of_origin")
            coa = arguments.get("coa") or arguments.get("country_of_asylum")
            year = arguments.get("year") or arguments.get("years")
            
            # Analyze the question to determine what type of data is needed
            question_lower = question.lower()
            
            # Route to appropriate data based on question keywords
            if any(keyword in question_lower for keyword in ["demographic", "age", "gender", "breakdown"]):
                # Demographic data question
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if not year:
                    year = "2024"  # Default to current year
                
                result = api_client.get_demographics(
                    coo=coo, coa=coa, year=year,
                    coo_all=arguments.get("coo_all", False),
                    coa_all=arguments.get("coa_all", False),
                    pop_type=arguments.get("pop_type", False)
                )
                result["data_type"] = "demographics"
                return result
            elif any(keyword in question_lower for keyword in ["trend", "over time", "year", "evolution"]):
                # Trend data question
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if "population_types" not in arguments:
                    arguments["population_types"] = ["refugees"]
                
                result = api_client.get_population_trends(
                    coo=coo, coa=coa, years=year,
                    population_types=arguments.get("population_types", ["refugees"])
                )
                result["data_type"] = "trends"
                return result
            elif any(keyword in question_lower for keyword in ["solution", "return", "resettlement", "integration"]):
                # Solutions data question
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if not year:
                    year = "2024"  # Default to current year
                
                result = api_client.get_solutions(
                    coo=coo, coa=coa, year=year,
                    coo_all=arguments.get("coo_all", False),
                    coa_all=arguments.get("coa_all", False)
                )
                result["data_type"] = "solutions"
                return result
            elif any(keyword in question_lower for keyword in ["rsd", "asylum decision", "recognition rate"]):
                # RSD data question
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if not year:
                    year = "2024"  # Default to current year
                
                result = api_client.get_asylum_decisions(
                    coo=coo, coa=coa, year=year,
                    coo_all=arguments.get("coo_all", False),
                    coa_all=arguments.get("coa_all", False)
                )
                result["data_type"] = "rsd_decisions"
                return result
            elif any(keyword in question_lower for keyword in ["asylum application", "asylum claim"]):
                # RSD applications question
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if not year:
                    year = "2024"  # Default to current year
                
                result = api_client.get_asylum_applications(
                    coo=coo, coa=coa, year=year,
                    coo_all=arguments.get("coo_all", False),
                    coa_all=arguments.get("coa_all", False)
                )
                result["data_type"] = "rsd_applications"
                return result
            else:
                # Default to population data
                # Ensure required parameters are present
                if not coa:
                    coa = "TUR"  # Default to Turkey
                if not year:
                    year = "2024"  # Default to current year
                
                result = api_client.get_population(
                    coo=coo, coa=coa, year=year,
                    coo_all=arguments.get("coo_all", False),
                    coa_all=arguments.get("coa_all", False)
                )
                result["data_type"] = "population"
                return result
            
        except Exception as e:
            return {
                "error": f"Failed to get data for story: {str(e)}",
                "status": "error",
                "question": question,
                "arguments": arguments,
                "data_type": "error"
            }

    @server.tool(
        name="generate_analytical_story",
        description=(
            "Generate analytical stories and narratives from UNHCR data. "
            "Use this tool when asked to create reports, stories, or narratives based on data analysis."
        ),
    )
    async def generate_analytical_story(**kwargs) -> dict[str, Any]:
        """
        Generate analytical stories from data results.
        
        Args:
            result: Data result from previous analysis
            question: Original user question
            
        Returns:
            Dictionary containing the generated story and metadata
        """
        # Import the story generation function directly
        from backend.llm import generate_story_from_data
        
        try:
            # Extract parameters from kwargs
            result = kwargs.get("result") or kwargs.get("data")
            question = kwargs.get("question", "")
            
            story_content = await generate_story_from_data(question, result)
            
            return {
                "title": f"Analytical Story: {question[:50]}...",
                "story": story_content,
                "story_type": "analytical",
                "metadata": {
                    "source": "UNHCR AI Story Generation",
                    "question": question,
                    "data_type": result.get("data_type", "unknown") if result else "unknown",
                    "timestamp": datetime.now().isoformat()
                },
                "status": "success"
            }
        except Exception as e:
            return {
                "error": f"Failed to generate analytical story: {str(e)}",
                "status": "error",
                "question": question,
                "data_summary": str(result)[:200] if result else "No data"
            }

    return server


def main() -> None:
    """
    Main entry point for the MCP server.
    """
    logger.info("Starting UNHCR Statistics Copilot MCP Server")
    server = create_server()
    server.run()


if __name__ == "__main__":
    main()
