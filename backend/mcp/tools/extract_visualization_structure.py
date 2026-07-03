"""
Tool: extract_visualization_structure
Extract and structure visualization metadata for AI-generated reports.
"""

from typing import Any, Optional


def extract_visualization_structure_tool(
    visualization_type: str,
    title: Optional[str] = None,
    subtitle: Optional[str] = None,
    x_axis_label: Optional[str] = None,
    y_axis_label: Optional[str] = None,
    x_axis_range: Optional[list[float]] = None,
    y_axis_range: Optional[list[float]] = None,
    legend_items: Optional[list[str]] = None,
    geometric_layers: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Extract and structure visualization metadata (Phase 1 of AI reporting).
    
    Args:
        visualization_type: Type of visualization
        title: Main title of the visualization
        subtitle: Subtitle or secondary title
        x_axis_label: Label for X-axis
        y_axis_label: Label for Y-axis
        x_axis_range: Range of X-axis as [min, max]
        y_axis_range: Range of Y-axis as [min, max]
        legend_items: List of items in the legend
        geometric_layers: List of geometric layers used
    
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
