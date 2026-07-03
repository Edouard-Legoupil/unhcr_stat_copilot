"""
Tool: get_data_for_story
Get appropriate data for story generation.
"""

from datetime import datetime
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
    from backend.question_parser import extract_question_parameters
    
    try:
        # Extract parameters from the question
        extracted_params = await extract_question_parameters(question)
        
        # Handle parameter aliases
        if origin and coo is None:
            coo = origin
        if destination and coa is None:
            coa = destination
        if population_type and population_types is None:
            population_types = [population_type]
        
        # Use extracted parameters if not provided
        if coo is None:
            coo = extracted_params.get('coo')
        if coa is None:
            coa = extracted_params.get('coa')
        if year is None:
            year = extracted_params.get('year')
        if timespan and year is None and years is None:
            years = timespan
        
        # If years is provided but year is not, use years
        if year is None and years is not None:
            if "-" in str(years):
                try:
                    start, end = years.split("-")
                    years_list = list(range(int(start), int(end) + 1))
                    year = ",".join(str(y) for y in years_list)
                except (ValueError, TypeError):
                    year = years
            else:
                year = years
        
        # Determine what data to fetch based on question content
        question_lower = question.lower()
        
        # Default to population data
        data = api_client.get_population(coo=coo, coa=coa, year=year or years)
        
        # Check for specific data types in the question
        if any(keyword in question_lower for keyword in ["demographic", "age", "gender", "breakdown"]):
            data = api_client.get_demographics(coo=coo, coa=coa, year=year or years, pop_type=True)
            data_type = "demographics"
        elif any(keyword in question_lower for keyword in ["solution", "return", "resettlement", "integration"]):
            data = api_client.get_solutions(coo=coo, coa=coa, year=year or years)
            data_type = "solutions"
        elif any(keyword in question_lower for keyword in ["application", "asylum", "claim"]):
            data = api_client.get_asylum_applications(coo=coo, coa=coa, year=year or years)
            data_type = "rsd_applications"
        elif any(keyword in question_lower for keyword in ["decision", "recognition", "approval"]):
            data = api_client.get_asylum_decisions(coo=coo, coa=coa, year=year or years)
            data_type = "rsd_decisions"
        else:
            data_type = "population"
        
        return {
            'question': question,
            'extracted_params': extracted_params,
            'data': data,
            'data_type': data_type,
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
