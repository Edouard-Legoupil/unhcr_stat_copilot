"""
Tool: get_solutions
Retrieve durable solutions data.
"""

from typing import Any, Optional, Union


def get_solutions_tool(
    api_client: Any,
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[Union[str, int]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
) -> dict[str, Any]:
    """
    Get figures on durable solutions from UNHCR.
    
    Args:
        api_client: UNHCRAPIClient instance
        coo: Country of origin filter
        coa: Country of asylum filter
        year: Year filter
        coo_all: Set to True when analyzing decisions breakdown BY NATIONALITY
        coa_all: Set to True when analyzing decisions breakdown BY COUNTRY
    
    Returns:
        Solutions data from UNHCR API
    """
    return api_client.get_solutions(
        coo=coo, coa=coa, year=year, coo_all=coo_all, coa_all=coa_all
    )
