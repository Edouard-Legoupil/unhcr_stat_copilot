"""
Semantic Constants for UNHCR MCP Tools

This module provides centralized constants for semantic validation across all MCP tools.
It ensures consistent validation of population types, country codes, and other parameters.
"""

from typing import Set, List, Dict, Any

# ============================================================================
# VALID UNHCR POPULATION TYPES
# ============================================================================
# These are the ONLY valid population types that should be accepted
# for plotting, analysis, and data retrieval

VALID_POPULATION_TYPES: List[str] = [
    'refugees',
    'asylum_seekers',
    'idps',                    # Internally Displaced Persons
    'stateless',
    'returned_refugees',
    'returned_idps',
    'oip',                     # Other people in need of international protection
    'ooc',                     # Other persons of concern
    'returnees',               # Generic returnees (refugees + IDPs)
    'venezuelans_displaced_abroad',
    'other_people_in_need',
]

# Set for fast lookup
VALID_POPULATION_TYPES_SET: Set[str] = set(VALID_POPULATION_TYPES)

# Population type definitions for documentation
POPULATION_TYPE_DEFINITIONS: Dict[str, str] = {
    'refugees': 'Persons recognized as refugees under the 1951 Convention relating to the Status of Refugees',
    'asylum_seekers': 'Persons whose applications for asylum or refugee status are pending at any stage',
    'idps': 'Persons or groups of persons who have been forced or obliged to flee or to leave their homes or places of habitual residence, in particular as a result of or in order to avoid the effects of armed conflict, situations of generalized violence, violations of human rights or natural or human-made disasters, and who have not crossed an internationally recognized State border',
    'stateless': 'Persons who are not considered as nationals by any State under the operation of its law',
    'returned_refugees': 'Refugees who have voluntarily returned to their country of origin',
    'returned_idps': 'Internally displaced persons who have returned to their areas of origin or habitual residence',
    'oip': 'Other people in need of international protection',
    'ooc': 'Other persons of concern to UNHCR',
    'returnees': 'Persons who have returned (includes both returned refugees and returned IDPs)',
    'venezuelans_displaced_abroad': 'Venezuelans displaced abroad (specific to the Venezuela situation)',
    'other_people_in_need': 'Other people in need of international protection or assistance',
}


# ============================================================================
# FORBIDDEN IDENTIFIER FIELDS
# ============================================================================
# These fields are database identifiers/foreign keys and should NEVER be treated
# as population types, country codes, or any other semantic entity for plotting

FORBIDDEN_IDENTIFIER_FIELDS: Set[str] = {
    # Country/location identifiers
    'coo_id',
    'coa_id',
    'id',
    '_id',
    
    # Year/time identifiers
    'year',
    'years',
    'timespan',
    
    # ISO codes (these are country identifiers, not population types)
    'iso',
    'iso3',
    'iso2',
    'country_code',
    'country_iso',
    
    # Other technical identifiers
    'hst',
    'ooc_id',
    'oip_id',
    'population_type_id',
    'type_id',
    'code',
    
    # Metadata fields
    'name',
    'label',
    'description',
    'source',
    'reference',
    
    # Numeric identifiers
    'value',
    'count',
    'total',
    'sum',
}

# Extended set including common variations
FORBIDDEN_IDENTIFIER_PATTERNS: Set[str] = FORBIDDEN_IDENTIFIER_FIELDS | {
    'coo_id_',
    'coa_id_',
    '_coo_id',
    '_coa_id',
}


# ============================================================================
# VALIDATION HELPER FUNCTIONS
# ============================================================================

def is_valid_population_type(population_type: str | None) -> bool:
    """
    Check if a string is a valid UNHCR population type.
    
    Args:
        population_type: The string to validate
        
    Returns:
        True if valid, False otherwise (including None)
    """
    if population_type is None:
        return False
    
    population_type_lower = population_type.lower().strip()
    
    # Check if it's a forbidden identifier field
    if is_identifier_field(population_type_lower):
        return False
    
    # Check if it's in the valid population types
    return population_type_lower in VALID_POPULATION_TYPES_SET


def is_identifier_field(field_name: str | None) -> bool:
    """
    Check if a field name is a forbidden identifier field.
    
    Args:
        field_name: The field name to check
        
    Returns:
        True if it's an identifier field, False otherwise
    """
    if field_name is None:
        return False
    
    field_name_lower = field_name.lower().strip()
    
    # Direct match
    if field_name_lower in FORBIDDEN_IDENTIFIER_FIELDS:
        return True
    
    # Check for patterns (e.g., ends with _id, starts with id_)
    if field_name_lower.endswith('_id'):
        return True
    if field_name_lower.startswith('id_'):
        return True
    
    return False


def validate_population_type(population_type: str | None) -> tuple[bool, str]:
    """
    Validate a population type and return a detailed result.
    
    Args:
        population_type: The population type to validate
        
    Returns:
        Tuple of (is_valid, message)
    """
    if population_type is None:
        return False, "Population type cannot be None"
    
    population_type_lower = population_type.lower().strip()
    
    # Check if it's an identifier field
    if is_identifier_field(population_type_lower):
        return False, f"'{population_type}' is a database identifier, not a population type. Valid types: {VALID_POPULATION_TYPES}"
    
    # Check if it's valid
    if population_type_lower in VALID_POPULATION_TYPES_SET:
        return True, f"'{population_type}' is a valid UNHCR population type"
    
    # Unknown type
    return False, f"'{population_type}' is not a standard UNHCR population type. Valid types: {VALID_POPULATION_TYPES}"


def get_valid_population_types_list() -> List[str]:
    """Return the list of valid UNHCR population types."""
    return VALID_POPULATION_TYPES.copy()


def get_forbidden_identifier_fields() -> Set[str]:
    """Return the set of forbidden identifier fields."""
    return FORBIDDEN_IDENTIFIER_FIELDS.copy()


# ============================================================================
# COUNTRY CODE VALIDATION
# ============================================================================

def is_valid_iso3_country_code(code: str | None) -> bool:
    """
    Check if a string is a valid ISO3 country code.
    
    Args:
        code: The code to validate
        
    Returns:
        True if valid, False otherwise
    """
    if code is None:
        return False
    
    # ISO3 codes are 3 uppercase letters
    if len(code) == 3 and code.isalpha() and code.isupper():
        # Additional check: not a forbidden identifier
        if code.lower() in {f.lower() for f in FORBIDDEN_IDENTIFIER_FIELDS}:
            return False
        return True
    
    return False


# ============================================================================
# SEMANTIC SAFEGUARD DECORATOR
# ============================================================================

def semantic_safeguard(func):
    """
    Decorator to add semantic validation to MCP tool functions.
    
    Validates population_type parameters to prevent identifier fields
    from being used as population types.
    """
    def wrapper(*args, **kwargs):
        # Check for population_type in kwargs
        population_type = kwargs.get('population_type')
        if population_type:
            is_valid, message = validate_population_type(population_type)
            if not is_valid:
                return {
                    'error': message,
                    'status': 'error',
                    'validation_failed': True,
                    'invalid_parameter': 'population_type',
                    'invalid_value': population_type
                }
        
        # Check for population_types (list) in kwargs
        population_types = kwargs.get('population_types')
        if population_types:
            if isinstance(population_types, list):
                for pop_type in population_types:
                    is_valid, message = validate_population_type(pop_type)
                    if not is_valid:
                        return {
                            'error': message,
                            'status': 'error',
                            'validation_failed': True,
                            'invalid_parameter': 'population_types',
                            'invalid_value': pop_type
                        }
        
        # Call the original function
        return func(*args, **kwargs)
    
    return wrapper
