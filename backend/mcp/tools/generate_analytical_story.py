"""
Tool: generate_analytical_story
Generate analytical stories and narratives from UNHCR data.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def generate_analytical_story_tool(
    result: Optional[dict] = None,
    data: Optional[dict] = None,
    question: str = "",
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    analysis_config: Optional[dict] = None,
) -> dict[str, Any]:
    """
    Generate analytical stories from data results.
    
    Uses either LLM-based story generation (if Azure OpenAI is configured)
    or a fallback template-based approach.
    
    Args:
        result: Data result from previous analysis
        data: Alternative name for result
        question: Original user question
        audience: Target audience for the analysis
        document_type: Type of document being generated
        analysis_config: Analysis configuration
    
    Returns:
        Dictionary containing the generated story and metadata
    """
    # Extract parameters - use result if provided, otherwise data
    if result is None:
        result = data
    
    # Extract analysis configuration if available
    tone = None
    length_config = None
    structure = None
    if analysis_config and isinstance(analysis_config, dict):
        tone = analysis_config.get("tone")
        length_config = analysis_config.get("length")
        structure = analysis_config.get("structure")
    
    try:
        # Try LLM-based story generation first
        story_content = None
        try:
            # Import inside try block to handle import-time errors
            from backend.llm import generate_story_from_data
            story_content = await generate_story_from_data(
                question, result, 
                audience=audience, 
                document_type=document_type,
                tone=tone,
                length_config=length_config,
                structure=structure
            )
        except Exception as e:
            logger.debug(f"LLM story generation failed: {e}, falling back to template-based approach")
            # Fallback to template-based story generation
            story_content = _generate_story_from_template(question, result, audience, document_type, analysis_config)
        
        if story_content is None:
            # If somehow we still don't have content, use template
            story_content = _generate_story_from_template(question, result, audience, document_type, analysis_config)
        
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
        logger.exception(f"Failed to generate analytical story: {e}")
        return {
            "error": f"Failed to generate analytical story: {str(e)}",
            "status": "error",
            "question": question,
            "data_summary": str(result)[:200] if result else "No data"
        }


def _generate_story_from_template(
    question: str,
    result: Optional[dict],
    audience: Optional[str],
    document_type: Optional[str],
    analysis_config: Optional[dict]
) -> str:
    """
    Generate a story using templates instead of LLM.
    
    Args:
        question: The original question
        result: Data result
        audience: Target audience
        document_type: Document type
        analysis_config: Analysis configuration
    
    Returns:
        Generated story content
    """
    # Build story components
    story_parts = []
    
    # Title
    story_parts.append(f"# Analysis: {question}")
    story_parts.append("")
    
    # Introduction
    story_parts.append("## Introduction")
    story_parts.append("")
    story_parts.append(f"This analysis addresses the question: **{question}**")
    story_parts.append("")
    
    # Data Overview
    story_parts.append("## Data Overview")
    story_parts.append("")
    
    if result and isinstance(result, dict):
        # Extract key information from result
        if "data" in result and isinstance(result["data"], list):
            story_parts.append(f"- **Records**: {len(result['data'])}")
        elif "data" in result and isinstance(result["data"], dict):
            story_parts.append(f"- **Data fields**: {list(result['data'].keys())}")
        
        if "data_type" in result:
            story_parts.append(f"- **Data type**: {result['data_type']}")
        
        if "question" in result:
            story_parts.append(f"- **Original question**: {result['question']}")
    else:
        story_parts.append("- No data available for detailed analysis")
    
    story_parts.append("")
    
    # Key Findings
    story_parts.append("## Key Findings")
    story_parts.append("")
    
    if result and isinstance(result, dict):
        # Try to extract numerical data
        if "data" in result:
            data = result["data"]
            if isinstance(data, list) and len(data) > 0:
                story_parts.append("- Data retrieved successfully")
                story_parts.append(f"- Total entries: {len(data)}")
                
                # Show sample of first few items
                if len(data) > 0:
                    sample = data[0]
                    if isinstance(sample, dict):
                        story_parts.append("- Sample data structure:")
                        for key, value in list(sample.items())[:5]:
                            story_parts.append(f"  - {key}: {value}")
            elif isinstance(data, dict):
                story_parts.append("- Data structure:")
                for key, value in list(data.items())[:10]:
                    story_parts.append(f"  - {key}: {value}")
    
    story_parts.append("")
    
    # Methodology
    story_parts.append("## Methodology")
    story_parts.append("")
    story_parts.append("- Data sourced from UNHCR official statistics")
    story_parts.append("- Analysis follows UNHCR methodological guidelines")
    story_parts.append("- All data is aggregate-level only")
    story_parts.append("")
    
    # Conclusion
    story_parts.append("## Conclusion")
    story_parts.append("")
    story_parts.append(f"This analysis provides insights into {question.lower()}. For more detailed")
    story_parts.append("analysis, please refine your query or contact a data specialist.")
    
    return "\n".join(story_parts)
