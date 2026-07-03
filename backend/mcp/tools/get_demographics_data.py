"""
Tool: get_demographics_data
Retrieve age and sex breakdown data for forcibly displaced populations.
"""

from typing import Any, Optional, Union


def get_demographics_data_tool(
    api_client: Any,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
    pop_type: bool = False,
) -> dict[str, Any]:
    """
    Get forcibly displaced populations demographics data from UNHCR.
    
    Args:
        api_client: UNHCRAPIClient instance
        coo: Country of origin (ISO3 code)
        coa: Country of asylum (ISO3 code)
        year: Year to filter by
        coo_all: Set to True when breaking down results by ORIGIN country
        coa_all: Set to True when breaking down results by ASYLUM country
        pop_type: Set to True when asked about specific population types
    
    Returns:
        Demographics data from UNHCR API
    """
    return api_client.get_demographics(
        coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all, pop_type=pop_type
    )
