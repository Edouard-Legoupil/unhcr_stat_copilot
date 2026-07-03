"""
Tool: retrieve_report_context
Retrieve relevant contextual excerpts from the local UNHCR report vector store.
"""

from typing import Any, Optional

# Import the UNHCRVectorRetriever class
from backend.mcp.common import (
    DEFAULT_RAG_FETCH_K,
    DEFAULT_RAG_TOP_K,
    UNHCRVectorRetriever,
)


def retrieve_report_context_tool(
    rag_retriever: UNHCRVectorRetriever,
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
    
    Args:
        rag_retriever: UNHCRVectorRetriever instance
        request: The retrieval request
        top_k: Number of top results to return
        fetch_k: Number of candidates to fetch
        year: Filter by year
        report_type: Filter by report type
        section_contains: Filter by section path
        exclude_figures_tables: Exclude figures and tables
        rerank: Whether to use cross-encoder reranking
    
    Returns:
        Retrieved context with metadata
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
