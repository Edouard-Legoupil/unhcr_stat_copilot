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
    # Use the existing safe_tool_selection function from llm.py
    from backend.llm import safe_tool_selection
    
    try:
        result = await safe_tool_selection(question)
        return result
    except Exception as e:
        return {
            'error': f'Failed to select tool: {str(e)}',
            'question': question,
            'status': 'error'
        }
