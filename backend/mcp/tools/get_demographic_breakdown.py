"""
Tool: get_demographic_breakdown
Retrieve detailed age and sex distribution for specific population types.
"""

from datetime import datetime
from typing import Any, Optional


def get_demographic_breakdown_tool(
    api_client: Any,
    coa: Optional[str] = None,
    coo: Optional[str] = None,
    year: Optional[int | str] = None,
    population_type: Optional[str] = None
) -> dict[str, Any]:
    """
    Get detailed demographic breakdown by age and sex for a specific population type.
    
    Args:
        api_client: UNHCRAPIClient instance
        coa: Country of asylum (ISO3 code)
        coo: Country of origin (ISO3 code)
        year: Year to filter by
        population_type: Specific population type
    
    Returns:
        Demographic data with age/sex breakdown
    """
    demographics_data = api_client.get_demographics(
        coa=coa, 
        coo=coo,
        year=year, 
        pop_type=True if population_type else False
    )
    
    if demographics_data.get('data'):
        # Process demographic data
        processed_data = []
        
        for item in demographics_data['data']:
            if population_type and item.get('population_type') != population_type:
                continue
                
            processed_data.append({
                'population_type': item.get('population_type', 'unknown'),
                'age_group': item.get('age_group', 'unknown'),
                'sex': item.get('sex', 'unknown'),
                'count': item.get('value', 0),
                'percentage': item.get('percentage', 0)
            })
        
        return {
            'country': demographics_data['data'][0].get('coa_name', 'Unknown'),
            'year': year or datetime.now().year,
            'demographics': processed_data,
            'metadata': {
                'source': 'UNHCR Demographics Statistics'
            }
        }
    
    return {'error': 'No demographic data available', 'status': 'error'}
