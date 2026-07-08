"""
Unit tests for Semantic Constants Module

These tests verify the core semantic validation functionality without
requiring integration with other modules that may have circular imports.
"""

import pytest
import sys
import os

# Add the paths for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools'))

# Import directly from the module file
import semantic_constants

# Re-export for cleaner access
VALID_POPULATION_TYPES = semantic_constants.VALID_POPULATION_TYPES
FORBIDDEN_IDENTIFIER_FIELDS = semantic_constants.FORBIDDEN_IDENTIFIER_FIELDS
is_valid_population_type = semantic_constants.is_valid_population_type
is_identifier_field = semantic_constants.is_identifier_field
validate_population_type = semantic_constants.validate_population_type


class TestValidPopulationTypes:
    """Test validation of valid UNHCR population types."""
    
    def test_all_valid_types_are_recognized(self):
        """All standard UNHCR population types should be recognized as valid."""
        for pop_type in VALID_POPULATION_TYPES:
            assert is_valid_population_type(pop_type), f"{pop_type} should be valid"
    
    def test_case_insensitive_validation(self):
        """Population type validation should be case-insensitive."""
        assert is_valid_population_type('Refugees')
        assert is_valid_population_type('REFUGEES')
        assert is_valid_population_type('refugees')


class TestForbiddenIdentifierFields:
    """Test that identifier fields are properly rejected."""
    
    def test_coo_id_is_rejected(self):
        """coo_id should be rejected as a population type."""
        assert not is_valid_population_type('coo_id')
        assert is_identifier_field('coo_id')
    
    def test_coa_id_is_rejected(self):
        """coa_id should be rejected as a population type."""
        assert not is_valid_population_type('coa_id')
        assert is_identifier_field('coa_id')
    
    def test_year_is_rejected(self):
        """year should be rejected as a population type."""
        assert not is_valid_population_type('year')
        assert is_identifier_field('year')
    
    def test_id_is_rejected(self):
        """id should be rejected as a population type."""
        assert not is_valid_population_type('id')
        assert is_identifier_field('id')
    
    def test_pattern_matching_ends_with_id(self):
        """Fields ending with _id should be detected."""
        assert is_identifier_field('some_id')
        assert is_identifier_field('population_id')
        assert not is_valid_population_type('some_id')
    
    def test_pattern_matching_starts_with_id(self):
        """Fields starting with id_ should be detected."""
        assert is_identifier_field('id_field')
        assert is_identifier_field('id_value')
        assert not is_valid_population_type('id_field')


class TestValidatePopulationTypeFunction:
    """Test the validate_population_type function."""
    
    def test_valid_types_return_true(self):
        """Valid population types should return (True, message)."""
        for pop_type in VALID_POPULATION_TYPES:
            is_valid, message = validate_population_type(pop_type)
            assert is_valid
            assert pop_type in message
    
    def test_identifier_fields_return_false_with_specific_message(self):
        """Identifier fields should return (False, message) with specific error."""
        is_valid, message = validate_population_type('coo_id')
        assert not is_valid
        assert 'database identifier' in message.lower()
    
    def test_unknown_types_return_false(self):
        """Unknown types should return (False, message)."""
        is_valid, message = validate_population_type('unknown_type')
        assert not is_valid
        assert 'not a standard' in message.lower()
    
    def test_none_returns_false(self):
        """None should return (False, message)."""
        is_valid, message = validate_population_type(None)
        assert not is_valid


class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string(self):
        """Empty string should not be valid."""
        assert not is_valid_population_type('')
        assert not is_identifier_field('')
    
    def test_whitespace_only(self):
        """Whitespace-only strings should not be valid."""
        assert not is_valid_population_type('   ')
    
    def test_mixed_case_identifier(self):
        """Mixed case identifier fields should still be detected."""
        assert is_identifier_field('COO_ID')
        assert is_identifier_field('Coo_Id')
    
    def test_population_type_with_spaces(self):
        """Population types with spaces should be handled."""
        assert is_valid_population_type('  refugees  ')


class TestSemanticSafeguardDecorator:
    """Test the semantic_safeguard decorator."""
    
    def test_decorator_rejects_invalid_population_type(self):
        """Decorator should reject invalid population_type parameter."""
        @semantic_constants.semantic_safeguard
        def dummy_tool(population_type=None):
            return {'success': True}
        
        result = dummy_tool(population_type='coo_id')
        
        assert result['status'] == 'error'
        assert result['validation_failed'] is True
        assert result['invalid_parameter'] == 'population_type'
        assert result['invalid_value'] == 'coo_id'
    
    def test_decorator_accepts_valid_population_type(self):
        """Decorator should accept valid population_type parameter."""
        @semantic_constants.semantic_safeguard
        def dummy_tool(population_type=None):
            return {'success': True, 'population_type': population_type}
        
        result = dummy_tool(population_type='refugees')
        
        assert result['success'] is True
        assert result['population_type'] == 'refugees'
    
    def test_decorator_rejects_invalid_population_types_list(self):
        """Decorator should reject invalid types in population_types list."""
        @semantic_constants.semantic_safeguard
        def dummy_tool(population_types=None):
            return {'success': True}
        
        result = dummy_tool(population_types=['refugees', 'coo_id'])
        
        assert result['status'] == 'error'
        assert result['validation_failed'] is True
        assert result['invalid_parameter'] == 'population_types'
        assert result['invalid_value'] == 'coo_id'


if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
