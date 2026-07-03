"""
Tool: safe_tool_selection
Safely select the appropriate tool for a given question.
"""

from typing import Any


async def safe_tool_selection_tool(question: str) -> dict[str, Any]:
    """
    Safely select the appropriate tool for a given question.
    
    Args:
        question: The user question to analyze
    
    Returns:
        Selected tool with confidence score
    """
    # Import question parser from the parent package
    from backend.question_parser import categorize_question, extract_entities
    
    try:
        # Extract entities and categorize the question
        entities = extract_entities(question)
        category = categorize_question(question)
        
        # Map categories to tools
        category_to_tool = {
            'population': 'get_population_data',
            'demographics': 'get_demographics_data',
            'rsd': 'get_rsd_applications',
            'asylum_decisions': 'get_rsd_decisions',
            'solutions': 'get_solutions',
            'trends': 'get_population_trends',
            'country_profile': 'get_country_key_figures',
            'comparison': 'get_population_data',
            'visualization': 'extract_visualization_structure',
            'analysis': 'analyze_data_statistics',
            'report': 'generate_ai_data_story'
        }
        
        tool_name = category_to_tool.get(category, 'get_population_data')
        
        # Adjust based on entities
        if 'refugee' in question.lower() and 'from' in question.lower():
            if entities.get('coo'):
                tool_name = 'get_population_data'
        
        if 'asylum' in question.lower() and ('application' in question.lower() or 'claim' in question.lower()):
            tool_name = 'get_rsd_applications'
        
        if 'decision' in question.lower() or 'recognition' in question.lower():
            tool_name = 'get_rsd_decisions'
        
        if 'return' in question.lower() or 'resettlement' in question.lower():
            tool_name = 'get_solutions'
        
        return {
            'question': question,
            'selected_tool': tool_name,
            'category': category,
            'entities': entities,
            'confidence': 'high',
            'metadata': {
                'source': 'UNHCR Tool Selector',
                'method': 'content_analysis'
            },
            'status': 'success'
        }
    except Exception as e:
        return {
            'error': f'Failed to select tool: {str(e)}',
            'question': question,
            'status': 'error'
        }
