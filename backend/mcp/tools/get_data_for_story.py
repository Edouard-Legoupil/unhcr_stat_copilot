"""
Tool: get_data_for_story
Get appropriate data for story generation.
"""

import logging
import os
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)

# Simple in-memory cache for data with freshness metadata
_data_cache: dict[tuple[Any, ...], tuple[dict[str, Any], float]] = {}
CACHE_TTL = int(os.getenv("MCP_DATA_CACHE_TTL", "300"))  # seconds


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
    
    # Check cache for identical requests
    cache_key = (
        question, coo, coa, year, years,
        tuple(population_types) if population_types else None,
        coo_all, coa_all, audience, document_type, origin, destination, timespan
    )
    if cache_key in _data_cache:
        cached_result, ts = _data_cache[cache_key]
        age = datetime.now().timestamp() - ts
        if age < CACHE_TTL:
            cached_result['cache_timestamp'] = datetime.fromtimestamp(ts).isoformat()
            cached_result['cache_age_seconds'] = int(age)
            return cached_result
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
        # Handle both 'coo'/'coa' and 'origin'/'destination' keys
        if coo is None:
            coo = extracted_params.get('coo') or extracted_params.get('origin')
        if coa is None:
            coa = extracted_params.get('coa') or extracted_params.get('destination')
        
        # Handle list of countries by joining with comma
        if isinstance(coo, list):
            coo = ','.join(coo)
        if isinstance(coa, list):
            coa = ','.join(coa)
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
        stats = None
        try:
            from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
            from backend.mcp.tools.semantic_constants import is_identifier_field
            
            items = data.get('items', []) if isinstance(data, dict) else data if isinstance(data, list) else []
            if items and isinstance(items, list) and len(items) > 0:
                # Extract numeric columns (exclude IDs and codes)
                first_item = items[0]
                if isinstance(first_item, dict):
                    numeric_cols = [
                        k for k, v in first_item.items()
                        if isinstance(v, (int, float))
                        and not (is_identifier_field(k) or any(skip in k.lower() for skip in ['iso', 'hst', 'ooc', 'oip']))
                    ]
                    
                    # Extract categorical columns (exclude identifier fields)
                    # Use semantic validation to exclude fields like coo_id, coa_id, etc.
                    categorical_cols = [
                        k for k, v in first_item.items()
                        if isinstance(v, str) 
                        and any(cat in k.lower() for cat in ['year', 'coo', 'coa', 'name'])
                        and not is_identifier_field(k)  # Exclude identifier fields
                    ]
                    
                    if numeric_cols:
                        # Note: analyze_data_statistics_tool is synchronous, not async
                        stats = analyze_data_statistics_tool(
                            data=items,
                            numeric_columns=numeric_cols,
                            categorical_columns=categorical_cols if categorical_cols else None
                        )
                        data['statistics'] = stats
        except Exception as e:
            logger.debug(f"Could not add statistical analysis: {e}")
            # Continue without statistics - non-blocking
        
        # Enrich data with UNHCR compliance validation (Phase 1 - Enhanced Pipeline)
        guardrails = None
        try:
            from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
            items = data.get('items', []) if isinstance(data, dict) else data if isinstance(data, list) else []
            data_fields = list(items[0].keys()) if items and isinstance(items[0], dict) else []
            
            # Note: apply_analysis_guardrails_tool is synchronous, not async
            guardrails = apply_analysis_guardrails_tool(
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
        
        # Extract visualization structure (Phase 2 - NEW)
        visualization_structure = None
        try:
            from backend.mcp.tools.extract_visualization_structure import extract_visualization_structure_tool
            # Auto-detect visualization type and labels from data
            viz_type = "line_chart"  # Default, can be enhanced
            viz_title = f"Analysis: {question}"
            
            # Try to detect axis labels from data
            x_label = "Year"
            y_label = "Count"
            
            if items and isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                # Look for year/time fields
                for key in items[0].keys():
                    if 'year' in key.lower():
                        x_label = key
                        break
                # Look for numeric value fields (excluding IDs)
                for key in items[0].keys():
                    if isinstance(items[0][key], (int, float)) and 'year' not in key.lower():
                        if not any(skip in key.lower() for skip in ['id', '_id', 'iso', 'hst', 'ooc', 'oip']):
                            y_label = key
                            break
            
            visualization_structure = extract_visualization_structure_tool(
                visualization_type=viz_type,
                title=viz_title,
                x_axis_label=x_label,
                y_axis_label=y_label
            )
            data['visualization_structure'] = visualization_structure
        except Exception as e:
            logger.debug(f"Could not extract visualization structure: {e}")
            # Continue without structure - non-blocking
        
        # Generate visualization description (Phase 3 - NEW)
        visualization_description = None
        try:
            from backend.mcp.tools.generate_visualization_description import generate_visualization_description_tool
            if visualization_structure and stats:
                visualization_description = await generate_visualization_description_tool(
                    structure=visualization_structure,
                    statistics=stats,
                    description_type="detailed",
                    max_length=500,
                    focus_areas=["trends", "comparisons", "outliers"]
                )
                data['visualization_description'] = visualization_description
        except Exception as e:
            logger.debug(f"Could not generate visualization description: {e}")
            # Continue without description - non-blocking
        
        result = {
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
        # Cache result with timestamp
        ts = datetime.now().timestamp()
        result['cache_timestamp'] = datetime.fromtimestamp(ts).isoformat()
        result['cache_age_seconds'] = 0
        _data_cache[cache_key] = (result, ts)
        return result
    except Exception as e:
        return {
            'error': f'Failed to get data for story: {str(e)}',
            'question': question,
            'status': 'error'
        }
