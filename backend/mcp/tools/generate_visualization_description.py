"""
Tool: generate_visualization_description
Generate AI-powered descriptions and interpretations for visualizations.
"""

from typing import Any, Optional


async def generate_visualization_description_tool(
    structure: dict[str, Any],
    statistics: dict[str, Any],
    description_type: str = "both",
    max_length: int = 300,
    focus_areas: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Generate AI descriptions for visualizations (Phase 3 of AI reporting).
    
    Args:
        structure: Visualization structure metadata
        statistics: Statistical analysis results
        description_type: Type of description
        max_length: Maximum length of generated description
        focus_areas: Specific areas to focus on
    
    Returns:
        Generated description with metadata
    """
    from backend.llm import generate_visualization_narrative
    
    try:
        description = await generate_visualization_narrative(
            structure=structure,
            statistics=statistics,
            description_type=description_type,
            max_length=max_length,
            focus_areas=focus_areas
        )
        
        return {
            'description': description,
            'description_type': description_type,
            'length': len(description),
            'metadata': {
                'source': 'UNHCR AI Visualization Analysis',
                'phase': 'description_generation'
            },
            'status': 'success'
        }
    except Exception as e:
        return {
            'error': f'Failed to generate visualization description: {str(e)}',
            'status': 'error'
        }
