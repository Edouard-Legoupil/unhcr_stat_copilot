"""
Tool: get_rsd_decisions
Retrieve Refugee Status Determination (RSD) decision outcomes.
"""

from typing import Any, Optional, Union


def get_rsd_decisions_tool(
    api_client: Any,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
) -> dict[str, Any]:
    """
    Get Refugee Status Determination (RSD) decision data from UNHCR.
    
    Args:
        api_client: UNHCRAPIClient instance
        coo: Country of origin filter
        coa: Country of asylum filter
        year: Year filter
        coo_all: Set to True when analyzing decisions breakdown BY NATIONALITY
        coa_all: Set to True when analyzing decisions breakdown BY COUNTRY
    
    Returns:
        RSD decision data from UNHCR API
    """
    return api_client.get_asylum_decisions(
        coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
    )
