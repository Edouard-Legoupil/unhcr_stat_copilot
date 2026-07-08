#!/usr/bin/env python3
"""
Build a RAG-optimised DuckDB vector store from converted UNHCR Markdown reports.

Input:
    data/markdown_reports/**/full.md

Output:
    data/vector_store/unhcr_reports.duckdb

Main features:
- Structure-aware Markdown chunking.
- Recursive chunk splitting for long sections.
- Local embeddings with sentence-transformers.
- DuckDB storage with fixed-size FLOAT[n] vectors.
- Optional DuckDB VSS/HNSW index.
- Query mode with filters and optional MMR diversification.
- RAG-optimised metadata and contextual embedding text.

Install:
    uv add duckdb sentence-transformers langchain-text-splitters tqdm pyyaml numpy

Build:
    uv run python scripts/build_reports_vector_index.py build --reset

Query:
    uv run python scripts/build_reports_vector_index.py query \
      "Afghan refugee returns under adverse circumstances in 2025" \
      --top-k 5
"""

from __future__ import annotations

import argparse
import hashlib
import json
import math
import re
import sys
import time
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Any

import duckdb
import numpy as np
import yaml
from sentence_transformers import SentenceTransformer
from tqdm import tqdm


# ---------------------------------------------------------------------
# Defaults
# ---------------------------------------------------------------------

DEFAULT_MARKDOWN_ROOT = Path("/app/data/markdown_reports")
DEFAULT_DB_PATH = Path("/app/data/vector_store/unhcr_reports.duckdb")
DEFAULT_MODEL_NAME = "BAAI/bge-small-en-v1.5"

DEFAULT_CHUNK_SIZE = 1_200
DEFAULT_CHUNK_OVERLAP = 180
DEFAULT_MIN_CHARS = 160
DEFAULT_BATCH_SIZE = 64

TABLE_CHUNKS = "report_chunks"
TABLE_REPORTS = "reports"
TABLE_METADATA = "index_metadata"


# ---------------------------------------------------------------------
# Data models
# ---------------------------------------------------------------------

@dataclass
class SourceReport:
    report_id: str
    markdown_path: str
    report_dir: str
    title: str | None
    year: str | None
    report_type: str | None
    source_pdf: str | None
    source_url: str | None
    figures_detected: int | None
    tables_detected: int | None
    footnotes_detected: int | None


@dataclass
class ChunkRecord:
    chunk_id: str
    content_hash: str
    report_id: str
    markdown_path: str
    report_dir: str
    title: str | None
    year: str | None
    report_type: str | None
    source_pdf: str | None
    source_url: str | None
    header_1: str | None
    header_2: str | None
    header_3: str | None
    header_4: str | None
    section_path: str
    chunk_index: int
    subchunk_index: int
    token_estimate: int
    char_count: int
    is_figure_or_table: bool
    text: str
    embedding_text: str
    metadata_json: str


# ---------------------------------------------------------------------
# Generic helpers
# ---------------------------------------------------------------------

def stable_id(*parts: str) -> str:
    value = "||".join(parts)
    return hashlib.sha256(value.encode("utf-8")).hexdigest()


def content_hash(text: str) -> str:
    normalized = re.sub(r"\s+", " ", text).strip().lower()
    return hashlib.sha256(normalized.encode("utf-8")).hexdigest()


def estimate_tokens(text: str) -> int:
    # Cheap approximation, good enough for metadata/filtering.
    return max(1, int(len(text.split()) * 1.33))


def now_utc() -> str:
    return time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime())


def infer_year(path: Path) -> str | None:
    match = re.search(r"\b(20\d{2})\b", path.as_posix())
    return match.group(1) if match else None


def first_non_empty(*values: Any) -> Any:
    for value in values:
        if value not in (None, "", []):
            return value
    return None


def safe_int(value: Any) -> int | None:
    try:
        if value is None:
            return None
        return int(value)
    except Exception:
        return None


# ---------------------------------------------------------------------
# Markdown discovery/loading
# ---------------------------------------------------------------------

def find_markdown_reports(root: Path) -> list[Path]:
    paths = sorted(root.glob("**/full.md"))
    return [path for path in paths if path.is_file()]


def split_front_matter(markdown: str) -> tuple[dict[str, Any], str]:
    text = markdown.lstrip()

    if not text.startswith("---"):
        return {}, markdown

    parts = text.split("---", 2)

    if len(parts) < 3:
        return {}, markdown

    _, yaml_text, body = parts

    try:
        meta = yaml.safe_load(yaml_text) or {}
        if not isinstance(meta, dict):
            meta = {}
    except Exception:
        meta = {}

    return meta, body.strip()


def load_source_report(md_path: Path) -> tuple[SourceReport, str]:
    markdown = md_path.read_text(encoding="utf-8")
    meta, body = split_front_matter(markdown)

    report_id = stable_id(md_path.as_posix())

    source = SourceReport(
        report_id=report_id,
        markdown_path=md_path.as_posix(),
        report_dir=md_path.parent.as_posix(),
        title=meta.get("title"),
        year=str(first_non_empty(meta.get("year"), infer_year(md_path))),
        report_type=meta.get("report_type"),
        source_pdf=meta.get("source_pdf"),
        source_url=meta.get("source_url"),
        figures_detected=safe_int(meta.get("figures_detected")),
        tables_detected=safe_int(meta.get("tables_detected")),
        footnotes_detected=safe_int(meta.get("footnotes_detected")),
    )

    return source, body


# ---------------------------------------------------------------------
# Markdown/text cleanup for RAG
# ---------------------------------------------------------------------

def remove_global_footnotes_section(markdown: str) -> str:
    """
    Remove global footnote appendix from embedding/chunking body.

    Inline references may remain in the narrative, but the long footnote section
    should not form standalone retrieval chunks.
    """
    return re.split(r"\n## Footnotes\s*\n", markdown, maxsplit=1)[0]


def normalize_markdown_images(text: str) -> str:
    # Remove local image paths from embeddings/chunks.
    text = re.sub(r"!\[[^\]]*\]\([^)]+\)", " ", text)

    # Also remove Docling-style links if they remain.
    text = re.sub(r"\[Image\]\([^)]+\)", " ", text)

    return text


def strip_html_table_tags_keep_text(text: str) -> str:
    # Preserve table cell text but remove HTML tags.
    text = re.sub(
        r"</?(table|thead|tbody|tr|th|td)[^>]*>",
        " ",
        text,
        flags=re.IGNORECASE,
    )
    return text


def strip_markdown_links_keep_label(text: str) -> str:
    return re.sub(r"\[([^\]]+)\]\([^)]+\)", r"\1", text)


def clean_text_for_storage(text: str) -> str:
    """
    Clean text stored in the vector DB.
    This should remain readable to humans.
    """
    text = text.replace("\r\n", "\n").replace("\r", "\n")
    text = re.sub(r"<!--.*?-->", " ", text, flags=re.DOTALL)
    text = normalize_markdown_images(text)
    text = strip_html_table_tags_keep_text(text)
    text = strip_markdown_links_keep_label(text)

    # Remove Markdown heading markers but keep the heading text.
    text = re.sub(r"^\s{0,3}#{1,6}\s+", "", text, flags=re.MULTILINE)

    # Remove Markdown footnote definition lines if any survived.
    text = re.sub(r"^\[\^\d{1,3}\]:.*$", " ", text, flags=re.MULTILINE)

    # Remove inline footnote markers for stored text readability.
    text = re.sub(r"\[\^\d{1,3}\]", "", text)

    # Reduce Markdown emphasis noise.
    text = text.replace("**", "").replace("__", "")

    # Normalize whitespace.
    text = re.sub(r"[ \t]+", " ", text)
    text = re.sub(r"\n{3,}", "\n\n", text)
    text = text.strip()

    return text


def clean_text_for_embedding(text: str) -> str:
    """
    More aggressive cleanup for embedding input.
    """
    text = clean_text_for_storage(text)

    # Remove citation-like standalone source fragments that survived.
    text = re.sub(r"\bSee footnote \d{1,3}\b", " ", text, flags=re.IGNORECASE)
    text = re.sub(r"\s+", " ", text)

    return text.strip()


def is_figure_or_table_chunk(text: str, metadata: dict[str, Any]) -> bool:
    joined = " ".join(str(v) for v in metadata.values() if v)
    probe = f"{joined}\n{text}".lower()

    return bool(
        re.search(r"\bfigure\s+\d+\b", probe)
        or re.search(r"\btable\s+\d+\b", probe)
    )


def section_path_from_metadata(metadata: dict[str, Any]) -> str:
    headers = [
        metadata.get("Header 1"),
        metadata.get("Header 2"),
        metadata.get("Header 3"),
        metadata.get("Header 4"),
    ]
    headers = [h for h in headers if h]
    return " > ".join(headers)


def build_embedding_text(source: SourceReport, chunk_text: str, metadata: dict[str, Any]) -> str:
    """
    RAG optimisation:
    include report-level and section-level context in the text that is embedded.
    This improves retrieval when chunks are small or section titles carry meaning.
    """
    context_parts = []

    if source.title:
        context_parts.append(f"Report title: {source.title}")

    if source.year:
        context_parts.append(f"Year: {source.year}")

    if source.report_type:
        context_parts.append(f"Report type: {source.report_type}")

    section_path = section_path_from_metadata(metadata)
    if section_path:
        context_parts.append(f"Section: {section_path}")

    context = "\n".join(context_parts)

    if context:
        return f"{context}\n\nContent:\n{chunk_text}"

    return chunk_text


# ---------------------------------------------------------------------
# Chunking
# ---------------------------------------------------------------------

def split_markdown_structurally(markdown: str) -> list[dict[str, Any]]:
    """
    Structure-aware splitting by Markdown headers.
    """
    try:
        from langchain_text_splitters import MarkdownHeaderTextSplitter

        headers_to_split_on = [
            ("#", "Header 1"),
            ("##", "Header 2"),
            ("###", "Header 3"),
            ("####", "Header 4"),
        ]

        splitter = MarkdownHeaderTextSplitter(
            headers_to_split_on=headers_to_split_on,
            strip_headers=False,
        )

        docs = splitter.split_text(markdown)

        return [
            {
                "text": doc.page_content,
                "metadata": dict(doc.metadata),
            }
            for doc in docs
        ]

    except Exception as exc:
        print(
            f"[WARN] MarkdownHeaderTextSplitter failed; using fallback heading splitter: {exc}",
            file=sys.stderr,
        )
        return fallback_heading_split(markdown)


def fallback_heading_split(markdown: str) -> list[dict[str, Any]]:
    sections: list[dict[str, Any]] = []
    current_lines: list[str] = []
    heading_stack: dict[int, str] = {}

    def flush() -> None:
        nonlocal current_lines

        text = "\n".join(current_lines).strip()
        if not text:
            return

        metadata = {
            f"Header {level}": heading_stack[level]
            for level in sorted(heading_stack)
            if level <= 4
        }

        sections.append({"text": text, "metadata": metadata})

    for line in markdown.splitlines():
        match = re.match(r"^(#{1,4})\s+(.+?)\s*$", line)

        if match:
            flush()
            current_lines = [line]

            level = len(match.group(1))
            title = match.group(2).strip()

            heading_stack[level] = title

            for deeper in list(heading_stack.keys()):
                if deeper > level:
                    del heading_stack[deeper]

            continue

        current_lines.append(line)

    flush()
    return sections


def split_long_sections(
    sections: list[dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    """
    Split structural sections into retrieval-sized chunks.
    """
    try:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

        splitter = RecursiveCharacterTextSplitter(
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            separators=[
                "\n\n#### ",
                "\n\n### ",
                "\n\n## ",
                "\n\n",
                "\n",
                ". ",
                "; ",
                ", ",
                " ",
                "",
            ],
        )

        final_chunks: list[dict[str, Any]] = []

        for section in sections:
            text = section["text"]
            metadata = section.get("metadata", {})

            if len(text) <= chunk_size:
                item = dict(section)
                item["subchunk_index"] = 0
                final_chunks.append(item)
                continue

            subtexts = splitter.split_text(text)

            for idx, subtext in enumerate(subtexts):
                final_chunks.append(
                    {
                        "text": subtext,
                        "metadata": dict(metadata),
                        "subchunk_index": idx,
                    }
                )

        return final_chunks

    except Exception as exc:
        print(
            f"[WARN] RecursiveCharacterTextSplitter failed; using fallback character splitter: {exc}",
            file=sys.stderr,
        )
        return fallback_character_split(sections, chunk_size, chunk_overlap)


def fallback_character_split(
    sections: list[dict[str, Any]],
    chunk_size: int,
    chunk_overlap: int,
) -> list[dict[str, Any]]:
    chunks: list[dict[str, Any]] = []

    for section in sections:
        text = section["text"]
        metadata = section.get("metadata", {})

        start = 0
        subchunk_index = 0

        while start < len(text):
            end = min(start + chunk_size, len(text))
            subtext = text[start:end]

            chunks.append(
                {
                    "text": subtext,
                    "metadata": dict(metadata),
                    "subchunk_index": subchunk_index,
                }
            )

            if end == len(text):
                break

            start = max(0, end - chunk_overlap)
            subchunk_index += 1

    return chunks


def build_chunks_for_report(
    source: SourceReport,
    markdown_body: str,
    chunk_size: int,
    chunk_overlap: int,
    min_chars: int,
) -> list:
    """
    Build chunk records for one report.
    """
    markdown_body = remove_global_footnotes_section(markdown_body)

    structural_sections = split_markdown_structurally(markdown_body)
    raw_chunks = split_long_sections(
        sections=structural_sections,
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
    )

    records: list[ChunkRecord] = []
    seen_hashes: set[str] = set()
    chunk_index = 0

    for raw_chunk in raw_chunks:
        raw_text = raw_chunk["text"]
        metadata = raw_chunk.get("metadata", {})
        subchunk_index = int(raw_chunk.get("subchunk_index", 0))

        clean_storage = clean_text_for_storage(raw_text)
        clean_embedding_content = clean_text_for_embedding(raw_text)

        if len(clean_embedding_content) < min_chars:
            continue

        hash_value = content_hash(clean_embedding_content)

        # Avoid repeated report headers, repeated captions, or Docling duplication.
        if hash_value in seen_hashes:
            continue

        seen_hashes.add(hash_value)

        embedding_text = build_embedding_text(
            source=source,
            chunk_text=clean_embedding_content,
            metadata=metadata,
        )

        section_path = section_path_from_metadata(metadata)

        chunk_id = stable_id(
            source.markdown_path,
            str(chunk_index),
            hash_value,
        )

        full_metadata = {
            "headers": metadata,
            "section_path": section_path,
            "subchunk_index": subchunk_index,
            "content_hash": hash_value,
        }

        record = ChunkRecord(
            chunk_id=chunk_id,
            content_hash=hash_value,
            report_id=source.report_id,
            markdown_path=source.markdown_path,
            report_dir=source.report_dir,
            title=source.title,
            year=source.year,
            report_type=source.report_type,
            source_pdf=source.source_pdf,
            source_url=source.source_url,
            header_1=metadata.get("Header 1"),
            header_2=metadata.get("Header 2"),
            header_3=metadata.get("Header 3"),
            header_4=metadata.get("Header 4"),
            section_path=section_path,
            chunk_index=chunk_index,
            subchunk_index=subchunk_index,
            token_estimate=estimate_tokens(clean_embedding_content),
            char_count=len(clean_embedding_content),
            is_figure_or_table=is_figure_or_table_chunk(clean_embedding_content, metadata),
            text=clean_storage,
            embedding_text=embedding_text,
            metadata_json=json.dumps(full_metadata, ensure_ascii=False),
        )

        records.append(record)
        chunk_index += 1

    return records


def build_all_chunks(
    markdown_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    min_chars: int,
) -> tuple[list[SourceReport], list[ChunkRecord]]:
    md_paths = find_markdown_reports(markdown_root)

    if not md_paths:
        raise FileNotFoundError(f"No full.md files found under {markdown_root}")

    reports: list[SourceReport] = []
    all_records: list[ChunkRecord] = []

    print(f"[INFO] Found {len(md_paths)} reports")

    for md_path in tqdm(md_paths, desc="Chunking reports"):
        source, body = load_source_report(md_path)
        reports.append(source)

        records = build_chunks_for_report(
            source=source,
            markdown_body=body,
            chunk_size=chunk_size,
            chunk_overlap=chunk_overlap,
            min_chars=min_chars,
        )

        all_records.extend(records)

    print(f"[INFO] Built {len(all_records)} chunks")
    return reports, all_records


# ---------------------------------------------------------------------
# Embedding
# ---------------------------------------------------------------------

def load_embedding_model(model_name: str, device: str | None = None) -> SentenceTransformer:
    kwargs: dict[str, Any] = {}

    if device:
        kwargs["device"] = device

    print(f"[INFO] Loading embedding model: {model_name}")
    return SentenceTransformer(model_name, **kwargs)


def embed_chunks(
    model: SentenceTransformer,
    records: list[ChunkRecord],
    batch_size: int,
    normalize_embeddings: bool = True,
) -> tuple[list[list[float]], int]:
    texts = [record.embedding_text for record in records]

    embeddings = model.encode(
        texts,
        batch_size=batch_size,
        show_progress_bar=True,
        convert_to_numpy=True,
        normalize_embeddings=normalize_embeddings,
    )

    if embeddings.ndim != 2:
        raise ValueError(f"Expected 2D embeddings, got shape={embeddings.shape}")

    dim = int(embeddings.shape[1])
    vectors = embeddings.astype("float32").tolist()

    print(f"[INFO] Embedding dimension: {dim}")
    return vectors, dim


# ---------------------------------------------------------------------
# DuckDB storage
# ---------------------------------------------------------------------

def connect_duckdb(db_path: Path) -> duckdb.DuckDBPyConnection:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    conn = duckdb.connect(str(db_path))
    
    # Install and load VSS extension for vector search
    try:
        conn.execute("INSTALL vss;")
        print("[INFO] Installed VSS extension")
    except Exception as e:
        print(f"[INFO] VSS extension already installed or failed: {e}")
    
    try:
        conn.execute("LOAD vss;")
        print("[INFO] Loaded VSS extension")
    except Exception as e:
        print(f"[INFO] VSS extension already loaded or failed: {e}")
    
    # Enable experimental HNSW persistence for vector search indexes
    try:
        conn.execute("SET hnsw_enable_experimental_persistence=true;")
        print("[INFO] Enabled experimental HNSW persistence for vector search indexes")
    except Exception as e:
        print(f"[WARN] Failed to enable HNSW persistence: {e}")
    
    return conn


def try_load_vss(conn: duckdb.DuckDBPyConnection, install: bool = True) -> bool:
    """
    Try to install/load DuckDB VSS extension.

    If this fails, brute-force vector search still works.
    """
    try:
        if install:
            conn.execute("INSTALL vss;")
        conn.execute("LOAD vss;")
        print("[INFO] DuckDB vss extension loaded")
        return True
    except Exception as exc:
        print(f"[WARN] Could not load DuckDB vss extension: {exc}", file=sys.stderr)
        print("[WARN] Continuing without HNSW index.", file=sys.stderr)
        return False


def create_schema(
    conn: duckdb.DuckDBPyConnection,
    embedding_dim: int,
    reset: bool,
) -> None:
    if reset:
        conn.execute(f"DROP TABLE IF EXISTS {TABLE_CHUNKS};")
        conn.execute(f"DROP TABLE IF EXISTS {TABLE_REPORTS};")
        conn.execute(f"DROP TABLE IF EXISTS {TABLE_METADATA};")

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_REPORTS} (
            report_id TEXT PRIMARY KEY,
            markdown_path TEXT,
            report_dir TEXT,
            title TEXT,
            year TEXT,
            report_type TEXT,
            source_pdf TEXT,
            source_url TEXT,
            figures_detected INTEGER,
            tables_detected INTEGER,
            footnotes_detected INTEGER
        );
        """
    )

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_CHUNKS} (
            chunk_id TEXT PRIMARY KEY,
            content_hash TEXT,
            report_id TEXT,
            markdown_path TEXT,
            report_dir TEXT,
            title TEXT,
            year TEXT,
            report_type TEXT,
            source_pdf TEXT,
            source_url TEXT,
            header_1 TEXT,
            header_2 TEXT,
            header_3 TEXT,
            header_4 TEXT,
            section_path TEXT,
            chunk_index INTEGER,
            subchunk_index INTEGER,
            token_estimate INTEGER,
            char_count INTEGER,
            is_figure_or_table BOOLEAN,
            text TEXT,
            embedding_text TEXT,
            metadata_json TEXT,
            embedding FLOAT[{embedding_dim}]
        );
        """
    )

    conn.execute(
        f"""
        CREATE TABLE IF NOT EXISTS {TABLE_METADATA} (
            key TEXT PRIMARY KEY,
            value TEXT
        );
        """
    )


def insert_reports(
    conn: duckdb.DuckDBPyConnection,
    reports: list[SourceReport],
) -> None:
    rows = []

    for report in reports:
        rows.append(
            [
                report.report_id,
                report.markdown_path,
                report.report_dir,
                report.title,
                report.year,
                report.report_type,
                report.source_pdf,
                report.source_url,
                report.figures_detected,
                report.tables_detected,
                report.footnotes_detected,
            ]
        )

    conn.executemany(
        f"""
        INSERT OR REPLACE INTO {TABLE_REPORTS}
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )


def insert_chunks(
    conn: duckdb.DuckDBPyConnection,
    records: list[ChunkRecord],
    embeddings: list[list[float]],
) -> None:
    if len(records) != len(embeddings):
        raise ValueError("records and embeddings length mismatch")

    rows = []

    for record, vector in zip(records, embeddings):
        d = asdict(record)

        rows.append(
            [
                d["chunk_id"],
                d["content_hash"],
                d["report_id"],
                d["markdown_path"],
                d["report_dir"],
                d["title"],
                d["year"],
                d["report_type"],
                d["source_pdf"],
                d["source_url"],
                d["header_1"],
                d["header_2"],
                d["header_3"],
                d["header_4"],
                d["section_path"],
                d["chunk_index"],
                d["subchunk_index"],
                d["token_estimate"],
                d["char_count"],
                d["is_figure_or_table"],
                d["text"],
                d["embedding_text"],
                d["metadata_json"],
                vector,
            ]
        )

    conn.executemany(
        f"""
        INSERT OR REPLACE INTO {TABLE_CHUNKS}
        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?);
        """,
        rows,
    )

    print(f"[INFO] Inserted {len(rows)} chunks")


def insert_index_metadata(
    conn: duckdb.DuckDBPyConnection,
    model_name: str,
    embedding_dim: int,
    chunk_count: int,
    report_count: int,
    markdown_root: Path,
    chunk_size: int,
    chunk_overlap: int,
    min_chars: int,
    normalize_embeddings: bool,
) -> None:
    metadata = {
        "model_name": model_name,
        "embedding_dim": str(embedding_dim),
        "chunk_count": str(chunk_count),
        "report_count": str(report_count),
        "markdown_root": markdown_root.as_posix(),
        "chunk_size": str(chunk_size),
        "chunk_overlap": str(chunk_overlap),
        "min_chars": str(min_chars),
        "normalize_embeddings": str(normalize_embeddings),
        "built_at": now_utc(),
        "rag_notes": (
            "Chunks are section-aware. Embedding text includes report title, year, "
            "report type, and section path. Global footnote sections are excluded."
        ),
    }

    for key, value in metadata.items():
        conn.execute(
            f"""
            INSERT OR REPLACE INTO {TABLE_METADATA}
            VALUES (?, ?);
            """,
            [key, value],
        )


def create_vss_index(
    conn: duckdb.DuckDBPyConnection,
    metric: str = "cosine",
) -> bool:
    """
    Create HNSW index if DuckDB VSS is available.
    """
    try:
        conn.execute(f"DROP INDEX IF EXISTS idx_{TABLE_CHUNKS}_embedding;")
    except Exception:
        pass

    # Try metric-specific syntax first.
    try:
        conn.execute(
            f"""
            CREATE INDEX idx_{TABLE_CHUNKS}_embedding
            ON {TABLE_CHUNKS}
            USING HNSW (embedding)
            WITH (metric = '{metric}');
            """
        )
        print(f"[INFO] Created HNSW index with metric={metric}")
        return True
    except Exception as exc:
        print(f"[WARN] HNSW index with metric option failed: {exc}", file=sys.stderr)

    # Fallback default HNSW index.
    try:
        conn.execute(
            f"""
            CREATE INDEX idx_{TABLE_CHUNKS}_embedding
            ON {TABLE_CHUNKS}
            USING HNSW (embedding);
            """
        )
        print("[INFO] Created HNSW index with default metric")
        return True
    except Exception as exc:
        print(f"[WARN] Failed to create HNSW index: {exc}", file=sys.stderr)
        return False


def build_index(args: argparse.Namespace) -> None:
    markdown_root = Path(args.markdown_root)
    db_path = Path(args.db)

    reports, records = build_all_chunks(
        markdown_root=markdown_root,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chars=args.min_chars,
    )

    if not records:
        raise RuntimeError("No chunks generated. Check source Markdown and min_chars.")

    model = load_embedding_model(args.model, args.device)

    normalize_embeddings = True

    embeddings, embedding_dim = embed_chunks(
        model=model,
        records=records,
        batch_size=args.batch_size,
        normalize_embeddings=normalize_embeddings,
    )

    conn = connect_duckdb(db_path)

    vss_loaded = False
    if not args.no_vss:
        vss_loaded = try_load_vss(conn, install=not args.no_install_vss)

    create_schema(
        conn=conn,
        embedding_dim=embedding_dim,
        reset=args.reset,
    )

    insert_reports(conn, reports)
    insert_chunks(conn, records, embeddings)
    insert_index_metadata(
        conn=conn,
        model_name=args.model,
        embedding_dim=embedding_dim,
        chunk_count=len(records),
        report_count=len(reports),
        markdown_root=markdown_root,
        chunk_size=args.chunk_size,
        chunk_overlap=args.chunk_overlap,
        min_chars=args.min_chars,
        normalize_embeddings=normalize_embeddings,
    )

    if vss_loaded:
        create_vss_index(conn, metric=args.metric)

    conn.close()

    print("")
    print("[OK] Vector store built")
    print(f"DB: {db_path}")
    print(f"Reports: {len(reports)}")
    print(f"Chunks: {len(records)}")
    print(f"Embedding dimension: {embedding_dim}")


# ---------------------------------------------------------------------
# Querying
# ---------------------------------------------------------------------

def get_index_metadata(conn: duckdb.DuckDBPyConnection) -> dict[str, str]:
    try:
        rows = conn.execute(f"SELECT key, value FROM {TABLE_METADATA};").fetchall()
        return {key: value for key, value in rows}
    except Exception:
        return {}


def vector_literal(vector: list[float], dim: int) -> str:
    values = ", ".join(f"{x:.8f}" for x in vector)
    return f"[{values}]::FLOAT[{dim}]"


def distance_function(metric: str) -> str:
    if metric == "l2sq":
        return "array_distance"
    return "array_cosine_distance"


def build_where_clause(args: argparse.Namespace) -> tuple[str, list[Any]]:
    clauses: list[str] = []
    params: list[Any] = []

    if args.year:
        clauses.append("year = ?")
        params.append(str(args.year))

    if args.report_type:
        clauses.append("lower(report_type) = lower(?)")
        params.append(args.report_type)

    if args.title_contains:
        clauses.append("lower(title) LIKE lower(?)")
        params.append(f"%{args.title_contains}%")

    if args.section_contains:
        clauses.append("lower(section_path) LIKE lower(?)")
        params.append(f"%{args.section_contains}%")

    if args.exclude_figures_tables:
        clauses.append("is_figure_or_table = FALSE")

    if not clauses:
        return "", []

    return "WHERE " + " AND ".join(clauses), params


def cosine_similarity_from_distance(distance: float) -> float:
    return 1.0 - float(distance)


def mmr_select(
    candidates: list[dict[str, Any]],
    query_vector: np.ndarray,
    top_k: int,
    lambda_mult: float = 0.65,
) -> list[dict[str, Any]]:
    """
    Maximal Marginal Relevance reranking.

    Candidates must include:
        embedding_np
        distance

    Since embeddings are normalized, dot product is cosine similarity.
    """
    if len(candidates) <= top_k:
        return candidates

    selected: list[dict[str, Any]] = []
    remaining = candidates.copy()

    for candidate in remaining:
        candidate["query_similarity"] = float(np.dot(query_vector, candidate["embedding_np"]))

    first = max(remaining, key=lambda x: x["query_similarity"])
    selected.append(first)
    remaining.remove(first)

    while remaining and len(selected) < top_k:
        best_candidate = None
        best_score = -math.inf

        for candidate in remaining:
            sim_to_query = candidate["query_similarity"]

            max_sim_to_selected = max(
                float(np.dot(candidate["embedding_np"], selected_item["embedding_np"]))
                for selected_item in selected
            )

            mmr_score = lambda_mult * sim_to_query - (1.0 - lambda_mult) * max_sim_to_selected

            if mmr_score > best_score:
                best_score = mmr_score
                best_candidate = candidate

        selected.append(best_candidate)
        remaining.remove(best_candidate)

    return selected


def query_index(args: argparse.Namespace) -> None:
    db_path = Path(args.db)

    if not db_path.exists():
        raise FileNotFoundError(f"Vector DB not found: {db_path}")

    conn = connect_duckdb(db_path)

    metadata = get_index_metadata(conn)

    model_name = args.model or metadata.get("model_name") or DEFAULT_MODEL_NAME
    embedding_dim = int(metadata.get("embedding_dim", "0"))

    if embedding_dim <= 0:
        raise RuntimeError("Could not determine embedding dimension from index_metadata.")

    if not args.no_vss:
        try_load_vss(conn, install=False)

    model = load_embedding_model(model_name, args.device)

    query_embedding = model.encode(
        [args.query],
        normalize_embeddings=True,
        convert_to_numpy=True,
    ).astype("float32")[0]

    if len(query_embedding) != embedding_dim:
        raise ValueError(
            f"Query embedding dimension {len(query_embedding)} does not match DB dimension {embedding_dim}"
        )

    qvec = vector_literal(query_embedding.tolist(), embedding_dim)
    dist_fn = distance_function(args.metric)
    where_sql, params = build_where_clause(args)

    fetch_k = max(args.fetch_k, args.top_k)

    sql = f"""
        SELECT
            chunk_id,
            content_hash,
            report_id,
            title,
            year,
            report_type,
            source_url,
            markdown_path,
            section_path,
            header_1,
            header_2,
            header_3,
            header_4,
            chunk_index,
            subchunk_index,
            token_estimate,
            char_count,
            is_figure_or_table,
            text,
            embedding,
            {dist_fn}(embedding, {qvec}) AS distance
        FROM {TABLE_CHUNKS}
        {where_sql}
        ORDER BY distance
        LIMIT {int(fetch_k)};
    """

    rows = conn.execute(sql, params).fetchall()

    candidates: list[dict[str, Any]] = []

    for row in rows:
        (
            chunk_id,
            hash_value,
            report_id,
            title,
            year,
            report_type,
            source_url,
            markdown_path,
            section_path,
            header_1,
            header_2,
            header_3,
            header_4,
            chunk_index,
            subchunk_index,
            token_estimate,
            char_count,
            is_figure_or_table,
            text,
            embedding,
            distance,
        ) = row

        emb_np = np.array(embedding, dtype=np.float32)

        candidates.append(
            {
                "chunk_id": chunk_id,
                "content_hash": hash_value,
                "report_id": report_id,
                "title": title,
                "year": year,
                "report_type": report_type,
                "source_url": source_url,
                "markdown_path": markdown_path,
                "section_path": section_path,
                "header_1": header_1,
                "header_2": header_2,
                "header_3": header_3,
                "header_4": header_4,
                "chunk_index": chunk_index,
                "subchunk_index": subchunk_index,
                "token_estimate": token_estimate,
                "char_count": char_count,
                "is_figure_or_table": is_figure_or_table,
                "text": text,
                "embedding_np": emb_np,
                "distance": float(distance),
            }
        )

    if args.mmr:
        selected = mmr_select(
            candidates=candidates,
            query_vector=query_embedding,
            top_k=args.top_k,
            lambda_mult=args.mmr_lambda,
        )
    else:
        selected = candidates[: args.top_k]

    for rank, item in enumerate(selected, start=1):
        print("=" * 110)
        print(f"Rank: {rank}")
        print(f"Distance: {item['distance']:.6f}")
        print(f"Similarity approx.: {cosine_similarity_from_distance(item['distance']):.6f}")
        print(f"Title: {item['title']}")
        print(f"Year: {item['year']}")
        print(f"Report type: {item['report_type']}")
        print(f"Section: {item['section_path']}")
        print(f"Chunk index: {item['chunk_index']} / subchunk {item['subchunk_index']}")
        print(f"Tokens est.: {item['token_estimate']}")
        print(f"Figure/table chunk: {item['is_figure_or_table']}")
        print(f"Source URL: {item['source_url']}")
        print(f"Markdown: {item['markdown_path']}")
        print("-" * 110)
        print(item["text"][: args.preview_chars].strip())
        print()

    conn.close()


# ---------------------------------------------------------------------
# Inspection/export
# ---------------------------------------------------------------------

def inspect_db(args: argparse.Namespace) -> None:
    db_path = Path(args.db)

    if not db_path.exists():
        raise FileNotFoundError(db_path)

    conn = connect_duckdb(db_path)

    metadata = get_index_metadata(conn)

    print("Metadata")
    print(json.dumps(metadata, indent=2))

    print()
    print("Counts by report")
    rows = conn.execute(
        f"""
        SELECT
            year,
            report_type,
            title,
            COUNT(*) AS chunks,
            SUM(token_estimate) AS estimated_tokens,
            SUM(CASE WHEN is_figure_or_table THEN 1 ELSE 0 END) AS figure_table_chunks
        FROM {TABLE_CHUNKS}
        GROUP BY year, report_type, title
        ORDER BY year, report_type, title;
        """
    ).fetchall()

    for row in rows:
        print(row)

    print()
    print("Largest chunks")
    rows = conn.execute(
        f"""
        SELECT
            year,
            title,
            section_path,
            token_estimate,
            LEFT(text, 160)
        FROM {TABLE_CHUNKS}
        ORDER BY token_estimate DESC
        LIMIT 10;
        """
    ).fetchall()

    for row in rows:
        print(row)

    conn.close()


def export_jsonl(args: argparse.Namespace) -> None:
    db_path = Path(args.db)
    output_path = Path(args.output)

    if not db_path.exists():
        raise FileNotFoundError(db_path)

    output_path.parent.mkdir(parents=True, exist_ok=True)

    conn = connect_duckdb(db_path)

    rows = conn.execute(
        f"""
        SELECT
            chunk_id,
            report_id,
            title,
            year,
            report_type,
            source_url,
            markdown_path,
            section_path,
            chunk_index,
            subchunk_index,
            token_estimate,
            text
        FROM {TABLE_CHUNKS}
        ORDER BY year, report_type, title, chunk_index, subchunk_index;
        """
    ).fetchall()

    with output_path.open("w", encoding="utf-8") as f:
        for row in rows:
            item = {
                "chunk_id": row[0],
                "report_id": row[1],
                "title": row[2],
                "year": row[3],
                "report_type": row[4],
                "source_url": row[5],
                "markdown_path": row[6],
                "section_path": row[7],
                "chunk_index": row[8],
                "subchunk_index": row[9],
                "token_estimate": row[10],
                "text": row[11],
            }
            f.write(json.dumps(item, ensure_ascii=False) + "\n")

    conn.close()
    print(f"[OK] Exported {len(rows)} chunks to {output_path}")


# ---------------------------------------------------------------------
# CLI
# ---------------------------------------------------------------------

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        description="Build/query a RAG-optimised DuckDB vector index from UNHCR Markdown reports."
    )

    subparsers = parser.add_subparsers(dest="command", required=True)

    build = subparsers.add_parser("build", help="Build vector index")
    build.add_argument("--markdown-root", default=DEFAULT_MARKDOWN_ROOT.as_posix())
    build.add_argument("--db", default=DEFAULT_DB_PATH.as_posix())
    build.add_argument("--model", default=DEFAULT_MODEL_NAME)
    build.add_argument("--device", default=None, help="Example: cpu, cuda")
    build.add_argument("--chunk-size", type=int, default=DEFAULT_CHUNK_SIZE)
    build.add_argument("--chunk-overlap", type=int, default=DEFAULT_CHUNK_OVERLAP)
    build.add_argument("--min-chars", type=int, default=DEFAULT_MIN_CHARS)
    build.add_argument("--batch-size", type=int, default=DEFAULT_BATCH_SIZE)
    build.add_argument("--metric", choices=["cosine", "l2sq"], default="cosine")
    build.add_argument("--reset", action="store_true")
    build.add_argument("--no-vss", action="store_true")
    build.add_argument("--no-install-vss", action="store_true")
    build.set_defaults(func=build_index)

    query = subparsers.add_parser("query", help="Query vector index")
    query.add_argument("query")
    query.add_argument("--db", default=DEFAULT_DB_PATH.as_posix())
    query.add_argument("--model", default=None)
    query.add_argument("--device", default=None)
    query.add_argument("--top-k", type=int, default=5)
    query.add_argument("--fetch-k", type=int, default=30)
    query.add_argument("--metric", choices=["cosine", "l2sq"], default="cosine")
    query.add_argument("--preview-chars", type=int, default=1_200)
    query.add_argument("--year", default=None)
    query.add_argument("--report-type", default=None)
    query.add_argument("--title-contains", default=None)
    query.add_argument("--section-contains", default=None)
    query.add_argument("--exclude-figures-tables", action="store_true")
    query.add_argument("--mmr", action="store_true")
    query.add_argument("--mmr-lambda", type=float, default=0.65)
    query.add_argument("--no-vss", action="store_true")
    query.set_defaults(func=query_index)

    inspect = subparsers.add_parser("inspect", help="Inspect DB contents")
    inspect.add_argument("--db", default=DEFAULT_DB_PATH.as_posix())
    inspect.set_defaults(func=inspect_db)

    export = subparsers.add_parser("export-jsonl", help="Export chunks as JSONL")
    export.add_argument("--db", default=DEFAULT_DB_PATH.as_posix())
    export.add_argument("--output", default="data/vector_store/report_chunks.jsonl")
    export.set_defaults(func=export_jsonl)

    return parser


def main() -> int:
    parser = build_parser()
    args = parser.parse_args()

    try:
        args.func(args)
        return 0
    except KeyboardInterrupt:
        print("\nInterrupted.", file=sys.stderr)
        return 130
    except Exception as exc:
        print(f"[ERROR] {exc}", file=sys.stderr)
        raise


if __name__ == "__main__":
    raise SystemExit(main())