"""
Tool: safe_tool_selection
Safely select the appropriate tool for a given question.

This implementation uses question parsing and keyword matching instead of
calling back to llm.py which would create a circular dependency with the MCP server.
"""

import logging
from typing import Any

logger = logging.getLogger(__name__)


# Tool selection keywords and patterns
TOOL_KEYWORDS = {
    "get_population_data": [
        "population", "refugees", "asylum seekers", "displaced", "total refugees",
        "number of refugees", "how many refugees", "refugee numbers", "population data"
    ],
    "get_population_trends": [
        "trend", "trends", "over time", "over the years", "evolution", 
        "change over time", "historical", "yearly trend", "decade trend",
        "increase", "decrease", "grown", "declined"
    ],
    "get_demographics_data": [
        "demographic", "demographics", "age", "gender", "sex", "breakdown",
        "age distribution", "gender distribution", "age and sex", "population pyramid",
        "age groups", "male", "female", "children", "adults", "elderly"
    ],
    "get_demographic_breakdown": [
        "detailed demographic", "granular demographic", "age breakdown",
        "gender breakdown", "demographic breakdown"
    ],
    "get_country_key_figures": [
        "key figures", "statistics", "overview", "summary", "country profile",
        "country statistics", "total numbers", "combined statistics"
    ],
    "get_rsd_applications": [
        "rsd applications", "asylum applications", "asylum claims", "refugee status",
        "applications for asylum", "asylum requests", "claims", "submitted applications"
    ],
    "get_rsd_decisions": [
        "rsd decisions", "asylum decisions", "recognition rate", "approval rate",
        "rejected asylum", "accepted asylum", "decision outcomes", "status determination"
    ],
    "get_solutions": [
        "solutions", "resettlement", "return", "repatriation", "integration",
        "voluntary return", "durable solutions", "naturalization", "local integration",
        "third country resettlement", "returned refugees", "returned idps"
    ],
    "retrieve_report_context": [
        "report context", "methodology", "source", "explanation", "background",
        "context from reports", "why", "explain", "methodological", "evidence"
    ],
    "get_suggested_questions": [
        "suggested questions", "what to ask", "example questions", "query examples",
        "sample questions", "what can I ask", "help me ask"
    ],
    "get_usage_guidance": [
        "usage guidance", "how to use", "help", "instructions", "guidance",
        "user guide", "documentation", "manual"
    ],
    "apply_analysis_guardrails": [
        "guardrails", "validate analysis", "check compliance", "methodological standards",
        "quality assurance", "validation", "verify analysis"
    ],
}


async def safe_tool_selection_tool(question: str) -> dict[str, Any]:
    """
    Safely select the appropriate tool for a given question.
    
    Uses keyword matching and question parsing to determine the best tool
    without requiring Azure OpenAI or creating circular dependencies.
    
    Args:
        question: The user question to analyze
    
    Returns:
        Dictionary with selected tool and arguments
    """
    try:
        question_lower = question.lower()
        
        # 1. Extract parameters from the question
        from backend.question_parser import extract_question_parameters
        extracted_params = await extract_question_parameters(question)
        
        # 2. Score each tool based on keyword matches
        tool_scores: dict[str, int] = {}
        for tool_name, keywords in TOOL_KEYWORDS.items():
            score = sum(1 for kw in keywords if kw in question_lower)
            if score > 0:
                tool_scores[tool_name] = score
        
        # 3. If no tool matched, use the default based on extracted parameters
        if not tool_scores:
            # Default to population data for most questions
            tool_name = "get_population_data"
            arguments = {}
            
            # Build arguments from extracted parameters
            if extracted_params.get('coo'):
                arguments['coo'] = extracted_params['coo']
            if extracted_params.get('coa'):
                arguments['coa'] = extracted_params['coa']
            if extracted_params.get('year'):
                arguments['year'] = extracted_params['year']
            if extracted_params.get('timespan'):
                arguments['year'] = extracted_params['timespan']
            
            # Add population type if specified
            if extracted_params.get('population_type'):
                # Map population type to API parameters
                pop_type = extracted_params['population_type']
                if pop_type == 'refugees':
                    pass  # Default
                elif pop_type in ['asylum_seekers', 'asylum']:
                    arguments['pop_type'] = True
            
            logger.info(f"Default tool selected: {tool_name} with args: {arguments}")
            return {
                "tool": tool_name,
                "arguments": arguments,
                "parameters": extracted_params,
                "confidence": "medium"
            }
        
        # 4. Select the tool with the highest score
        best_tool = max(tool_scores, key=tool_scores.get)
        
        # 5. Build arguments based on tool type and extracted parameters
        arguments = _build_arguments_for_tool(best_tool, extracted_params, question_lower)
        
        logger.info(f"Selected tool: {best_tool} with args: {arguments}")
        
        return {
            "tool": best_tool,
            "arguments": arguments,
            "parameters": extracted_params,
            "confidence": "high" if tool_scores[best_tool] > 1 else "medium"
        }
    
    except Exception as e:
        logger.exception(f"Failed to select tool: {e}")
        return {
            'error': f'Failed to select tool: {str(e)}',
            'question': question,
            'status': 'error'
        }


def _build_arguments_for_tool(
    tool_name: str,
    extracted_params: dict[str, Any],
    question_lower: str
) -> dict[str, Any]:
    """
    Build appropriate arguments for a specific tool based on extracted parameters.
    
    Args:
        tool_name: The selected tool name
        extracted_params: Extracted parameters from the question
        question_lower: Lowercase version of the question
    
    Returns:
        Dictionary of arguments for the tool
    """
    arguments: dict[str, Any] = {}
    
    # Common arguments for most tools
    if extracted_params.get('coo'):
        arguments['coo'] = extracted_params['coo']
    if extracted_params.get('coa'):
        arguments['coa'] = extracted_params['coa']
    
    # Handle year/timespan
    if extracted_params.get('year'):
        arguments['year'] = extracted_params['year']
    elif extracted_params.get('timespan'):
        # Convert timespan to year format if needed
        timespan = extracted_params['timespan']
        if '-' in timespan:
            # Year range
            arguments['years'] = timespan
        else:
            # Single year or comma-separated years
            arguments['year'] = timespan
    
    # Tool-specific arguments
    if tool_name in ["get_population_data", "get_demographics_data", 
                      "get_rsd_applications", "get_rsd_decisions", "get_solutions"]:
        # Check if we should get all origins or destinations
        if 'all origins' in question_lower or 'all countries of origin' in question_lower:
            arguments['coo_all'] = True
        if 'all destinations' in question_lower or 'all countries of asylum' in question_lower:
            arguments['coa_all'] = True
    
    if tool_name == "get_demographics_data" or tool_name == "get_demographic_breakdown":
        # Enable population type breakdown
        arguments['pop_type'] = True
        if extracted_params.get('population_type'):
            arguments['population_type'] = extracted_params['population_type']
    
    if tool_name == "get_solutions":
        if extracted_params.get('population_type'):
            # Map to specific solution types
            pop_type = extracted_params['population_type']
            if pop_type in ['returned_refugees', 'returned_idps']:
                arguments['population_types'] = [pop_type]
    
    if tool_name == "get_country_key_figures":
        if extracted_params.get('population_types'):
            arguments['population_types'] = extracted_params['population_types']
        else:
            # Default to all main population types
            arguments['population_types'] = ['refugees', 'asylum_seekers', 'idps', 'stateless']
    
    if tool_name == "get_population_trends":
        if extracted_params.get('population_types'):
            arguments['population_types'] = extracted_params['population_types']
        else:
            arguments['population_types'] = ['refugees']
    
    return arguments
