"""
Tool: get_country_key_figures
Retrieve formatted key statistics and summaries for specific countries.
"""

from datetime import datetime
from typing import Any, Callable, Optional, Union


def get_country_key_figures_tool(
    api_client: Any,
    coa: Optional[str] = None,
    coo: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    population_types: Optional[list[str]] = None,
    get_color: Callable[[str], str] = lambda x: '#333333',
) -> dict[str, Any]:
    """
    Get key figures for a specific country with formatted summary statistics.
    
    Args:
        api_client: UNHCRAPIClient instance
        coa: Country of asylum (ISO3 code)
        coo: Country of origin (ISO3 code)
        year: Year to filter by
        population_types: List of population types to include
        get_color: Function to get color for population type
    
    Returns:
        Formatted key figures data including totals, percentages, and metadata
    """
    # Get raw population data
    population_data = api_client.get_population(coa=coa, coo=coo, year=year)
    
    # Process data to extract key figures
    if population_data.get('data'):
        data = population_data['data']
        
        # Filter by population types if specified
        if population_types:
            data = [item for item in data if item.get('population_type') in population_types]
        
        # Calculate totals and percentages
        total_poc = sum(item.get('value', 0) for item in data)
        
        # Format results
        result = {
            'country': data[0].get('coa_name', 'Unknown'),
            'year': year or datetime.now().year,
            'total_population_of_concern': total_poc,
            'breakdown': [],
            'metadata': {
                'source': 'UNHCR Population Statistics',
                'api_version': 'v1'
            }
        }
        
        # Add breakdown by population type
        for item in data:
            pop_type = item.get('population_type', 'unknown')
            value = item.get('value', 0)
            percentage = (value / total_poc * 100) if total_poc > 0 else 0
            
            result['breakdown'].append({
                'population_type': pop_type,
                'count': value,
                'percentage': round(percentage, 2),
                'color': get_color(pop_type)
            })
        
        return result
    
    return {'error': 'No data available', 'status': 'error'}
