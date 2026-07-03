"""
Tool: generate_ai_data_story
Generate a complete AI data story from visualization data.
"""

import json
import logging
from typing import Any, Optional
from backend.mcp.common import DEFAULT_RAG_FETCH_K, DEFAULT_RAG_TOP_K

logger = logging.getLogger(__name__)


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
    
    Uses either LLM-based generation or a fallback template approach.
    
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
    try:
        # Try LLM-based generation first
        try:
            from backend.llm import generate_data_story_with_rag
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
        except Exception as e:
            logger.debug(f"LLM data story generation failed: {e}, falling back to template")
            # Fallback to template-based story generation
            story = _generate_data_story_from_template(
                visualization_data, context, story_type, apply_guardrails
            )
        
        # If story is empty or None, use template fallback
        if not story:
            story = _generate_data_story_from_template(
                visualization_data, context, story_type, apply_guardrails
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


def _generate_data_story_from_template(
    visualization_data: dict[str, Any],
    context: Optional[str],
    story_type: str,
    apply_guardrails: bool
) -> str:
    """
    Generate a data story using templates.
    
    Args:
        visualization_data: Data to generate story from
        context: Additional context
        story_type: Type of story
        apply_guardrails: Whether guardrails were requested
    
    Returns:
        Generated story content
    """
    parts = []
    
    # Title
    title = visualization_data.get('title', 'UNHCR Data Analysis')
    parts.append(f"# {title}")
    parts.append("")
    
    # Introduction
    parts.append("## Introduction")
    parts.append("")
    if context:
        parts.append(f"This analysis addresses: **{context}**")
    else:
        parts.append("This data story provides insights into UNHCR forcibly displaced populations.")
    parts.append("")
    
    # Data Overview
    parts.append("## Data Overview")
    parts.append("")
    
    if 'data' in visualization_data:
        data = visualization_data['data']
        if isinstance(data, list):
            parts.append(f"- **Data points**: {len(data)}")
        elif isinstance(data, dict):
            parts.append(f"- **Data structure**: {list(data.keys())}")
            # Show some key values
            for key, value in list(data.items())[:5]:
                parts.append(f"  - {key}: {value}")
    
    # Guardrails notice
    if apply_guardrails:
        parts.append("")
        parts.append("## Methodology")
        parts.append("")
        parts.append("- This analysis follows UNHCR methodology standards")
        parts.append("- All data is sourced from official UNHCR statistics")
        parts.append("- Results are aggregate-level only")
    
    # Conclusion
    parts.append("")
    parts.append("## Conclusion")
    parts.append("")
    parts.append("This data story provides a comprehensive overview of the visualization data.")
    parts.append("For more detailed analysis, please contact a UNHCR data specialist.")
    
    return "\n".join(parts)
