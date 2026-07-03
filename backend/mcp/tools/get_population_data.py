"""
Tool: get_population_data
Retrieve forcibly displaced population statistics from UNHCR.
"""

from typing import Any, Optional, Union


def get_population_data_tool(
    api_client: Any,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
) -> dict[str, Any]:
    """
    Get forcibly displaced populations like refugees, asylum seekers, stateless persons data from UNHCR.
    
    Args:
        api_client: UNHCRAPIClient instance
        coo: Country of origin (ISO3 code)
        coa: Country of asylum (ISO3 code)
        year: Year to filter by
        coo_all: Set to True when breaking down results by ORIGIN country
        coa_all: Set to True when breaking down results by ASYLUM country
    
    Returns:
        Population data from UNHCR API
    """
    return api_client.get_population(
        coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
    )
