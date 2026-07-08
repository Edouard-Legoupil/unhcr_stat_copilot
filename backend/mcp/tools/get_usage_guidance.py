"""
Tool: get_usage_guidance
Get usage guidance, examples, and best practices for UNHCR MCP tools.
"""

from typing import Any, Optional


def get_usage_guidance_tool(
    tool_category: Optional[str] = None,
    specific_tool: Optional[str] = None
) -> dict[str, Any]:
    """
    Get usage guidance for UNHCR MCP tools.
    
    Args:
        tool_category: Category of tools
        specific_tool: Specific tool name for detailed guidance
    
    Returns:
        Usage guidance and examples
    """
    guidance = {
        'available_tools': [
            {'name': 'get_population_data', 'category': 'data_retrieval', 'description': 'Retrieve population statistics'},
            {'name': 'get_demographics_data', 'category': 'data_retrieval', 'description': 'Get demographic breakdowns'},
            {'name': 'get_rsd_applications', 'category': 'data_retrieval', 'description': 'Get asylum application data'},
            {'name': 'get_rsd_decisions', 'category': 'data_retrieval', 'description': 'Get RSD decision data'},
            {'name': 'get_solutions', 'category': 'data_retrieval', 'description': 'Get durable solutions data'},
            {'name': 'retrieve_report_context', 'category': 'rag', 'description': 'Retrieve context from UNHCR reports'},
            {'name': 'extract_visualization_structure', 'category': 'reporting', 'description': 'Extract visualization metadata'},
            {'name': 'analyze_data_statistics', 'category': 'analysis', 'description': 'Perform statistical analysis'},
            {'name': 'generate_visualization_description', 'category': 'reporting', 'description': 'Generate visualization descriptions'},
            {'name': 'generate_analytical_story', 'category': 'reporting', 'description': 'Generate analytical stories and data stories with optional RAG enrichment'},
            {'name': 'get_country_key_figures', 'category': 'data_retrieval', 'description': 'Get country-specific key figures'},
            {'name': 'get_population_trends', 'category': 'analysis', 'description': 'Get population trends over time'},
            {'name': 'get_demographic_breakdown', 'category': 'analysis', 'description': 'Get demographic breakdowns'},
            {'name': 'apply_analysis_guardrails', 'category': 'compliance', 'description': 'Apply UNHCR analysis guardrails'},
            {'name': 'get_suggested_questions', 'category': 'guidance', 'description': 'Get suggested questions'},
            {'name': 'safe_tool_selection', 'category': 'guidance', 'description': 'Safe tool selection'},
            {'name': 'get_data_for_story', 'category': 'reporting', 'description': 'Get data for story generation'},
            {'name': 'generate_analytical_story', 'category': 'reporting', 'description': 'Generate analytical stories'},
            {'name': 'create_quarto_notebook', 'category': 'export', 'description': 'Create Quarto notebooks'},
        ],
        'categories': {
            'data_retrieval': 'Tools for retrieving raw data from UNHCR APIs',
            'analysis': 'Tools for statistical and demographic analysis',
            'reporting': 'Tools for generating reports and visualizations',
            'rag': 'Tools for retrieving and enriching with report context',
            'compliance': 'Tools for ensuring compliance with UNHCR standards',
            'guidance': 'Tools for getting help and suggestions'
        },
        'metadata': {
            'source': 'UNHCR MCP Server',
            'version': '1.0'
        }
    }
    
    # Filter by category or tool if specified
    if tool_category:
        guidance['available_tools'] = [
            t for t in guidance['available_tools'] if t.get('category') == tool_category
        ]
    
    if specific_tool:
        guidance['specific_tool'] = next(
            (t for t in guidance['available_tools'] if t.get('name') == specific_tool),
            None
        )
    
    return guidance
