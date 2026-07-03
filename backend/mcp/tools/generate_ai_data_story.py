"""
Tool: generate_ai_data_story
Generate a complete AI data story from visualization data.
"""

from typing import Any, Optional
from backend.mcp.common import DEFAULT_RAG_FETCH_K, DEFAULT_RAG_TOP_K


async def generate_ai_data_story_tool(
    rag_retriever: Any,
    visualization_data: dict[str, Any],
    context: Optional[str] = None,
    story_type: str = "analytical",
    max_tokens: int = 500,
    apply_guardrails: bool = True,
    use_report_context: bool = True,
    rag_top_k: int = DEFAULT_RAG_TOP_K,
    rag_fetch_k: int = DEFAULT_RAG_FETCH_K,
    rag_rerank: bool = False,
    rag_year: Optional[str] = None,
    rag_report_type: Optional[str] = None,
    rag_section_contains: Optional[str] = None,
    rag_exclude_figures_tables: bool = False
) -> dict[str, Any]:
    """
    Generate AI data stories from visualization data with RAG enrichment.
    
    Args:
        rag_retriever: UNHCRVectorRetriever instance
        visualization_data: Data to generate story from
        context: Additional context for story generation
        story_type: Type of story
        max_tokens: Maximum tokens for story generation
        apply_guardrails: Whether to apply UNHCR methodology guardrails
        use_report_context: Whether to enrich with RAG context
        rag_*: RAG retrieval parameters
    
    Returns:
        Generated data story with metadata
    """
    from backend.llm import generate_data_story_with_rag
    
    try:
        story = await generate_data_story_with_rag(
            visualization_data=visualization_data,
            context=context,
            story_type=story_type,
            max_tokens=max_tokens,
            apply_guardrails=apply_guardrails,
            use_report_context=use_report_context,
            rag_top_k=rag_top_k,
            rag_fetch_k=rag_fetch_k,
            rag_rerank=rag_rerank,
            rag_year=rag_year,
            rag_report_type=rag_report_type,
            rag_section_contains=rag_section_contains,
            rag_exclude_figures_tables=rag_exclude_figures_tables
        )
        
        return {
            'story': story,
            'story_type': story_type,
            'metadata': {
                'source': 'UNHCR AI Data Story Generator',
                'phase': 'story_generation'
            },
            'status': 'success'
        }
    except Exception as e:
        return {
            'error': f'Failed to generate AI data story: {str(e)}',
            'status': 'error'
        }
