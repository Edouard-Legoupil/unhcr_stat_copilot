"""
Tool: get_data_for_story
Get appropriate data for story generation.
"""

import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


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
        
        # Enrich data with statistical analysis (Phase 1 - Enhanced Pipeline)
        try:
            from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
            items = data.get('items', []) if isinstance(data, dict) else data if isinstance(data, list) else []
            if items and isinstance(items, list) and len(items) > 0:
                # Extract numeric columns (exclude IDs and codes)
                first_item = items[0]
                if isinstance(first_item, dict):
                    numeric_cols = [
                        k for k, v in first_item.items()
                        if isinstance(v, (int, float))
                        and not any(skip in k.lower() for skip in ['id', '_id', 'iso', 'hst', 'ooc', 'oip'])
                    ]
                    categorical_cols = [
                        k for k, v in first_item.items()
                        if isinstance(v, str) and any(cat in k.lower() for cat in ['year', 'coo', 'coa', 'name'])
                    ]
                    
                    if numeric_cols:
                        stats = await analyze_data_statistics_tool(
                            data=items,
                            numeric_columns=numeric_cols,
                            categorical_columns=categorical_cols if categorical_cols else None
                        )
                        data['statistics'] = stats
        except Exception as e:
            logger.debug(f"Could not add statistical analysis: {e}")
            # Continue without statistics - non-blocking
        
        # Enrich data with UNHCR compliance validation (Phase 1 - Enhanced Pipeline)
        try:
            from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
            items = data.get('items', []) if isinstance(data, dict) else data if isinstance(data, list) else []
            data_fields = list(items[0].keys()) if items and isinstance(items[0], dict) else []
            
            guardrails = await apply_analysis_guardrails_tool(
                analysis_request={
                    'context': question,
                    'data_fields': data_fields
                },
                population_type=data_type,
                country_iso=coo
            )
            data['guardrails'] = guardrails
        except Exception as e:
            logger.debug(f"Could not validate analysis guardrails: {e}")
            # Continue without guardrails - non-blocking
        
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
