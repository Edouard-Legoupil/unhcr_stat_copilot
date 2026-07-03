"""
Tool: get_rsd_applications
Retrieve Refugee Status Determination (RSD) application statistics.
"""

from typing import Any, Optional, Union


def get_rsd_applications_tool(
    api_client: Any,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
) -> dict[str, Any]:
    """
    Get RSD application data from UNHCR.
    
    Args:
        api_client: UNHCRAPIClient instance
        coo: Country of origin filter
        coa: Country of asylum filter
        year: Year filter
        coo_all: Set to True when analyzing the ORIGIN COUNTRIES of asylum seekers
        coa_all: Set to True when analyzing the ASYLUM COUNTRIES where applications were filed
    
    Returns:
        RSD application data from UNHCR API
    """
    return api_client.get_asylum_applications(
        coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
    )
