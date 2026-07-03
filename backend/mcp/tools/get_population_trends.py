"""
Tool: get_population_trends
Retrieve time series data showing population changes over multiple years.
"""

from datetime import datetime
from typing import Any, Optional


def get_population_trends_tool(
    api_client: Any,
    coa: Optional[str] = None,
    coo: Optional[str] = None,
    years: Optional[str] = None,
    population_types: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Get population trends over multiple years for time series analysis.
    
    Args:
        api_client: UNHCRAPIClient instance
        coa: Country of asylum (ISO3 code)
        coo: Country of origin (ISO3 code)
        years: Comma-separated years or year range
        population_types: List of population types to track over time
    
    Returns:
        Time series data for population trends
    """
    if not years:
        # Default to last 5 years including current year
        current_year = datetime.now().year
        start_year = current_year - 4
        years = ','.join(str(y) for y in range(start_year, current_year + 1))
        
    # Get population data for multiple years
    population_data = api_client.get_population(coa=coa, coo=coo, year=years)
    
    if population_data.get('data'):
        # Process into time series format
        time_series = {}
        
        for item in population_data['data']:
            year = item.get('year', 'unknown')
            pop_type = item.get('population_type', 'unknown')
            value = item.get('value', 0)
            
            # Filter by population types if specified
            if population_types and pop_type not in population_types:
                continue
                
            if year not in time_series:
                time_series[year] = {}
                
            time_series[year][pop_type] = value
        
        return {
            'country': population_data['data'][0].get('coa_name', 'Unknown'),
            'time_series': time_series,
            'metadata': {
                'source': 'UNHCR Population Statistics',
                'time_range': years
            }
        }
    
    return {'error': 'No trend data available', 'status': 'error'}
