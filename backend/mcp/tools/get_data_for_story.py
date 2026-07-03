"""
Tool: get_data_for_story
Get appropriate data for story generation.
"""

from typing import Any, Optional


async def get_data_for_story_tool(
    api_client: Any,
    question: str,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[str | int] = None,
    years: Optional[str] = None,
    population_types: Optional[list[str]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    population_type: Optional[str] = None,
    timespan: Optional[str] = None
) -> dict[str, Any]:
    """
    Get appropriate data for story generation based on question analysis.
    
    Args:
        api_client: UNHCRAPIClient instance
        question: The user question
        coo: Country of origin
        coa: Country of asylum
        year: Specific year
        years: Multiple years
        population_types: List of population types
        coo_all: Get all origin countries
        coa_all: Get all asylum countries
        audience: Target audience
        document_type: Type of document
        origin: Origin country
        destination: Destination country
        population_type: Population type
        timespan: Time span
    
    Returns:
        Data for story generation
    """
    from backend.question_parser import categorize_question, extract_entities
    
    try:
        entities = extract_entities(question)
        category = categorize_question(question)
        
        # Use provided parameters or extract from question
        coo = coo or entities.get('coo')
        coa = coa or entities.get('coa')
        year = year or entities.get('year')
        
        # Determine what data to fetch based on question type
        if 'population' in category:
            data = api_client.get_population(coo=coo, coa=coa, year=year or years)
        elif 'demographics' in category:
            data = api_client.get_demographics(coo=coo, coa=coa, year=year or years, pop_type=True)
        elif 'rsd' in category or 'asylum' in category:
            if 'decision' in question.lower():
                data = api_client.get_asylum_decisions(coo=coo, coa=coa, year=year or years)
            else:
                data = api_client.get_asylum_applications(coo=coo, coa=coa, year=year or years)
        elif 'solution' in category:
            data = api_client.get_solutions(coo=coo, coa=coa, year=year or years)
        else:
            # Default to population data
            data = api_client.get_population(coo=coo, coa=coa, year=year or years)
        
        return {
            'question': question,
            'category': category,
            'entities': entities,
            'data': data,
            'data_type': category,
            'parameters': {
                'coo': coo,
                'coa': coa,
                'year': year,
                'years': years
            },
            'metadata': {
                'source': 'UNHCR Data for Story',
                'audience': audience,
                'document_type': document_type
            },
            'status': 'success'
        }
    except Exception as e:
        return {
            'error': f'Failed to get data for story: {str(e)}',
            'question': question,
            'status': 'error'
        }
