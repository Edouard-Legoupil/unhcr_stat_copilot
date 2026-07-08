"""
Tool: apply_analysis_guardrails
Apply UNHCR methodology guardrails to ensure analyses follow international standards.
"""

from typing import Any, Optional

# Import semantic constants for centralized validation
from backend.mcp.tools.semantic_constants import (
    VALID_POPULATION_TYPES,
    VALID_POPULATION_TYPES_SET,
    POPULATION_TYPE_DEFINITIONS,
    FORBIDDEN_IDENTIFIER_FIELDS,
    is_valid_population_type,
    is_identifier_field,
    validate_population_type,
)


def apply_analysis_guardrails_tool(
    analysis_request: dict[str, Any],
    population_type: Optional[str] = None,
    country_iso: Optional[str] = None,
    year: Optional[str | int] = None,
    detailed_report: bool = False
) -> dict[str, Any]:
    """
    Apply UNHCR analysis guardrails to ensure compliance with international standards.
    
    Args:
        analysis_request: The analysis request to validate
        population_type: Specific population type being analyzed
        country_iso: Country ISO code
        year: Year of analysis
        detailed_report: Whether to generate a detailed compliance report
    
    Returns:
        Compliance validation results and recommendations
    """
    # Extract data for validation - handle nested data structures
    raw_data = analysis_request.get('data', [])
    # If data is a dict with a nested 'data' field, use that
    if isinstance(raw_data, dict) and 'data' in raw_data:
        data_items = raw_data.get('data', [])
        if isinstance(data_items, dict) and 'items' in data_items:
            data_items = data_items.get('items', [])
        elif not isinstance(data_items, list):
            data_items = []
    elif isinstance(raw_data, dict):
        # If data is a dict but not nested, treat it as a single item
        data_items = [raw_data] if raw_data else []
    else:
        data_items = raw_data if isinstance(raw_data, list) else []
    
    # Check population definition compliance
    compliance_results = {
        'population_definition': _check_population_definition_compliance(population_type or ''),
        'country_code': _check_valid_country_code(country_iso or ''),
        'data_disaggregation': _check_data_disaggregation(
            analysis_request.get('data_fields', []),
            population_type
        ),
        'data_completeness': _check_data_completeness(data_items),
        'data_consistency': _check_data_consistency(data_items),
        'storytelling_guardrails': _check_storytelling_guardrails(
            analysis_request.get('context', analysis_request.get('storytelling_context', '')),
            population_type
        )
    }
    
    all_compliant = all(
        result.get('compliant', False) for result in compliance_results.values()
    )
    
    overall_compliance = {
        'overall_compliant': all_compliant,
        'compliance_percentage': sum(
            1 for r in compliance_results.values() if r.get('compliant', False)
        ) / len(compliance_results) * 100 if compliance_results else 0,
        'compliance_level': _get_compliance_level(
            sum(1 for r in compliance_results.values() if r.get('compliant', False)) / len(compliance_results) * 100 if compliance_results else 0
        ),
        'detailed_report': compliance_results if detailed_report else None
    }
    
    return overall_compliance


def _check_population_definition_compliance(population_type: str) -> dict[str, Any]:
    """
    Check if population type definitions comply with UNHCR standards.
    
    This function now includes semantic safeguards to prevent identifier fields
    (like coo_id) from being misclassified as population types.
    """
    # First, check if it's a forbidden identifier field
    if is_identifier_field(population_type):
        return {
            'compliant': False,
            'population_type': population_type,
            'message': f'Population type "{population_type}" is a database identifier field, not a population type',
            'recommendation': f'Use one of: {VALID_POPULATION_TYPES}',
            'error_type': 'IDENTIFIER_FIELD_MISUSE',
            'severity': 'CRITICAL'
        }
    
    # Check against valid population types
    if population_type and population_type.lower() in VALID_POPULATION_TYPES_SET:
        # Use the canonical lowercase version for lookup
        canonical_type = population_type.lower()
        return {
            'compliant': True,
            'population_type': canonical_type,
            'definition': POPULATION_TYPE_DEFINITIONS.get(canonical_type, 'UNHCR standard population type'),
            'message': f'Population type "{canonical_type}" is compliant with UNHCR standards'
        }
    else:
        return {
            'compliant': False,
            'population_type': population_type,
            'message': f'Population type "{population_type}" is not a standard UNHCR classification',
            'recommendation': f'Use one of: {VALID_POPULATION_TYPES}',
            'error_type': 'INVALID_POPULATION_TYPE',
            'severity': 'HIGH'
        }


def _check_valid_country_code(country_iso: str) -> dict[str, Any]:
    """Check if country code is valid."""
    if not country_iso:
        return {'compliant': True, 'message': 'No country code specified'}
    
    # Check if it's a valid ISO3 code (simplified check)
    if len(country_iso) == 3 and country_iso.isalpha() and country_iso.isupper():
        return {'compliant': True, 'country_iso': country_iso, 'message': 'Valid ISO3 country code'}
    else:
        return {
            'compliant': False,
            'country_iso': country_iso,
            'message': f'Invalid ISO3 country code: {country_iso}',
            'recommendation': 'Use a valid 3-letter uppercase ISO country code'
        }


def _check_data_disaggregation(data_fields: list[str], population_type: Optional[str]) -> dict[str, Any]:
    """
    Check if data is properly disaggregated according to UNHCR standards.
    
    Also validates that data_fields don't contain forbidden identifier fields
    being misused as data fields.
    """
    # Check if any data_fields are forbidden identifier fields
    identifier_fields_in_data = [f for f in data_fields if is_identifier_field(f)]
    
    if identifier_fields_in_data:
        return {
            'compliant': False,
            'message': f'Data fields contain identifier fields that should not be used as data: {identifier_fields_in_data}',
            'error_type': 'IDENTIFIER_FIELD_IN_DATA',
            'severity': 'CRITICAL',
            'recommendation': 'Remove identifier fields (coo_id, coa_id, year, etc.) from data fields'
        }
    
    required_disaggregations = {
        'refugees': ['age', 'sex', 'country_of_origin'],
        'asylum_seekers': ['age', 'sex', 'country_of_origin'],
        'idps': ['age', 'sex'],
        'demographics': ['age', 'sex']
    }
    
    # Use lowercase for comparison
    population_type_lower = population_type.lower() if population_type else None
    
    if population_type and population_type_lower in required_disaggregations:
        required = required_disaggregations[population_type_lower]
        missing = [d for d in required if d not in data_fields]
        
        if not missing:
            return {
                'compliant': True,
                'message': f'Data properly disaggregated for {population_type_lower}',
                'required_fields': required
            }
        else:
            return {
                'compliant': False,
                'message': f'Missing required disaggregation fields: {missing}',
                'required_fields': required,
                'provided_fields': data_fields,
                'recommendation': f'Add missing fields: {missing}'
            }
    else:
        return {
            'compliant': True,
            'message': 'Population type does not require specific disaggregation'
        }


def _check_data_completeness(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Check if data appears to be complete."""
    if not data:
        return {'compliant': False, 'message': 'No data provided', 'recommendation': 'Provide data for analysis'}
    
    # Check for common completeness indicators
    has_values = all('value' in item or 'count' in item for item in data)
    has_metadata = any('year' in item or 'country' in item for item in data)
    
    if has_values and has_metadata:
        return {'compliant': True, 'message': 'Data appears complete with values and metadata'}
    else:
        missing = []
        if not has_values:
            missing.append('numeric values')
        if not has_metadata:
            missing.append('metadata (year, country, etc.)')
        
        return {
            'compliant': False,
            'message': f'Data appears incomplete, missing: {missing}',
            'recommendation': f'Include {missing} in your data'
        }


def _check_data_consistency(data: list[dict[str, Any]]) -> dict[str, Any]:
    """Check if data is internally consistent."""
    if not data or len(data) < 2:
        return {'compliant': True, 'message': 'Not enough data for consistency check'}
    
    # Simple consistency check: all items should have the same structure
    keys_set = {frozenset(item.keys()) for item in data}
    if len(keys_set) == 1:
        return {'compliant': True, 'message': 'Data structure is consistent across all items'}
    else:
        return {
            'compliant': False,
            'message': f'Inconsistent data structure: {len(keys_set)} different structures found',
            'recommendation': 'Ensure all data items have the same fields'
        }


def _check_storytelling_guardrails(context: str, population_type: Optional[str]) -> dict[str, Any]:
    """Check if storytelling context follows UNHCR guidelines."""
    if not context:
        return {'compliant': True, 'message': 'No context provided for storytelling check'}
    
    # Check for problematic language
    problematic_terms = [
        'illegal migrant', 'illegal alien', 'bogus asylum seeker',
        'queue jumper', 'economic migrant'
    ]
    
    found_issues = [term for term in problematic_terms if term.lower() in context.lower()]
    
    if not found_issues:
        return {'compliant': True, 'message': 'Context appears to follow UNHCR terminology guidelines'}
    else:
        return {
            'compliant': False,
            'message': f'Context contains problematic terminology: {found_issues}',
            'recommendation': 'Use person-first language and avoid stigmatizing terms. '
                           'Refer to UNHCR terminology guidelines.'
        }


def _get_compliance_level(compliance_percentage: float) -> str:
    """Determine compliance level based on percentage."""
    if compliance_percentage >= 90:
        return 'FULLY_COMPLIANT'
    elif compliance_percentage >= 75:
        return 'SUBSTANTIALLY_COMPLIANT'
    elif compliance_percentage >= 50:
        return 'PARTIALLY_COMPLIANT'
    else:
        return 'NON_COMPLIANT'
