"""
Tool: generate_analytical_story
Generate analytical stories and narratives from UNHCR data.
"""

from datetime import datetime
from typing import Any, Optional


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
    # Import the story generation function directly
    from backend.llm import generate_story_from_data
    
    try:
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
        
        story_content = await generate_story_from_data(
            question, result, 
            audience=audience, 
            document_type=document_type,
            tone=tone,
            length_config=length_config,
            structure=structure
        )
        
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
