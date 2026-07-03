"""
Tool: generate_visualization_description
Generate AI-powered descriptions and interpretations for visualizations.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def generate_visualization_description_tool(
    structure: dict[str, Any],
    statistics: dict[str, Any],
    description_type: str = "both",
    max_length: int = 300,
    focus_areas: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Generate AI descriptions for visualizations (Phase 3 of AI reporting).
    
    Uses either LLM-based generation or a fallback template approach.
    
    Args:
        structure: Visualization structure metadata
        statistics: Statistical analysis results
        description_type: Type of description
        max_length: Maximum length of generated description
        focus_areas: Specific areas to focus on
    
    Returns:
        Generated description with metadata
    """
    try:
        # Try LLM-based generation first
        try:
            from backend.llm import generate_visualization_narrative
            description = await generate_visualization_narrative(
                structure=structure,
                statistics=statistics,
                description_type=description_type,
                max_length=max_length,
                focus_areas=focus_areas
            )
        except Exception as e:
            logger.debug(f"LLM visualization description failed: {e}, falling back to template")
            # Fallback to template-based description
            description = _generate_description_from_template(
                structure, statistics, description_type, max_length, focus_areas
            )
        
        # If description is empty or None, use template fallback
        if not description:
            description = _generate_description_from_template(
                structure, statistics, description_type, max_length, focus_areas
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


def _generate_description_from_template(
    structure: dict[str, Any],
    statistics: dict[str, Any],
    description_type: str,
    max_length: int,
    focus_areas: Optional[list[str]]
) -> str:
    """
    Generate a visualization description using templates.
    
    Args:
        structure: Visualization structure
        statistics: Statistical data
        description_type: Type of description to generate
        max_length: Maximum length
        focus_areas: Areas to focus on
    
    Returns:
        Generated description
    """
    parts = []
    
    # Title from structure
    if structure.get('title'):
        parts.append(f"**{structure['title']}**")
    
    # Subtitle if available
    if structure.get('subtitle'):
        parts.append(f"\n{structure['subtitle']}")
    
    # Description based on visualization type
    viz_type = structure.get('visualization_type', 'unknown')
    parts.append(f"\nThis {viz_type} visualization displays data about UNHCR forcibly displaced populations.")
    
    # Add statistical insights
    if statistics:
        parts.append("\n\nKey statistical insights:")
        if 'mean' in statistics:
            parts.append(f"- Average: {statistics['mean']}")
        if 'median' in statistics:
            parts.append(f"- Median: {statistics['median']}")
        if 'min' in statistics:
            parts.append(f"- Minimum: {statistics['min']}")
        if 'max' in statistics:
            parts.append(f"- Maximum: {statistics['max']}")
        if 'std' in statistics:
            parts.append(f"- Standard deviation: {statistics['std']}")
    
    # Focus areas
    if focus_areas:
        parts.append(f"\n\nFocus areas: {', '.join(focus_areas)}")
    
    # Truncate to max_length
    description = ' '.join(parts)
    if len(description) > max_length:
        description = description[:max_length] + "..."
    
    return description
