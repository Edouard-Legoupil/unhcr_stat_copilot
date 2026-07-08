"""
Unit tests for Semantic Safeguards in UNHCR MCP Tools

These tests ensure that identifier fields like 'coo_id' are never misclassified
as population types, and that only valid UNHCR population types are accepted.
"""

import pytest
import sys
import os

# Add the paths for direct imports
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend'))
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools'))

# Import directly from the module file to avoid circular imports
import semantic_constants

# Re-export for cleaner access
VALID_POPULATION_TYPES = semantic_constants.VALID_POPULATION_TYPES
VALID_POPULATION_TYPES_SET = semantic_constants.VALID_POPULATION_TYPES_SET
FORBIDDEN_IDENTIFIER_FIELDS = semantic_constants.FORBIDDEN_IDENTIFIER_FIELDS
POPULATION_TYPE_DEFINITIONS = semantic_constants.POPULATION_TYPE_DEFINITIONS
is_valid_population_type = semantic_constants.is_valid_population_type
is_identifier_field = semantic_constants.is_identifier_field
validate_population_type = semantic_constants.validate_population_type
semantic_safeguard = semantic_constants.semantic_safeguard


# ============================================================================
# Test Valid Population Types
# ============================================================================

class TestValidPopulationTypes:
    """Test validation of valid UNHCR population types."""
    
    def test_valid_population_types_are_recognized(self):
        """All standard UNHCR population types should be recognized as valid."""
        for pop_type in VALID_POPULATION_TYPES:
            assert is_valid_population_type(pop_type), f"{pop_type} should be valid"
    
    def test_valid_population_types_case_insensitive(self):
        """Population type validation should be case-insensitive."""
        assert is_valid_population_type('Refugees')
        assert is_valid_population_type('REFUGEES')
        assert is_valid_population_type('refugees')
        assert is_valid_population_type('Asylum_Seekers')
    
    def test_valid_population_types_in_set(self):
        """All valid population types should be in the lookup set."""
        for pop_type in VALID_POPULATION_TYPES:
            assert pop_type in VALID_POPULATION_TYPES_SET
    
    def test_population_type_definitions_exist(self):
        """All valid population types should have definitions."""
        for pop_type in VALID_POPULATION_TYPES:
            assert pop_type in POPULATION_TYPE_DEFINITIONS
            assert POPULATION_TYPE_DEFINITIONS[pop_type]


# ============================================================================
# Test Forbidden Identifier Fields
# ============================================================================

class TestForbiddenIdentifierFields:
    """Test that identifier fields are properly rejected."""
    
    def test_identifier_fields_are_rejected(self):
        """Fields like coo_id, coa_id should be rejected as population types."""
        for field in FORBIDDEN_IDENTIFIER_FIELDS:
            assert not is_valid_population_type(field), f"{field} should be rejected"
    
    def test_is_identifier_field_detection(self):
        """is_identifier_field should correctly identify forbidden fields."""
        # Direct matches
        assert is_identifier_field('coo_id')
        assert is_identifier_field('coa_id')
        assert is_identifier_field('id')
        assert is_identifier_field('year')
        assert is_identifier_field('iso')
        assert is_identifier_field('country_code')
        
        # Pattern matches (ends with _id)
        assert is_identifier_field('some_id')
        assert is_identifier_field('population_id')
        assert is_identifier_field('user_id')
        
        # Pattern matches (starts with id_)
        assert is_identifier_field('id_field')
        assert is_identifier_field('id_value')
        
        # Not identifier fields
        assert not is_identifier_field('refugees')
        assert not is_identifier_field('asylum_seekers')
        assert not is_identifier_field('country')
        # Note: 'name' is in FORBIDDEN_IDENTIFIER_FIELDS as a metadata field
        # so it will be detected as an identifier field
    
    def test_coo_id_specific_rejection(self):
        """Specifically test that coo_id is rejected as a population type."""
        assert not is_valid_population_type('coo_id')
        assert is_identifier_field('coo_id')
        
        is_valid, message = validate_population_type('coo_id')
        assert not is_valid
        assert 'coo_id' in message
        assert 'database identifier' in message.lower()
    
    def test_coa_id_specific_rejection(self):
        """Specifically test that coa_id is rejected as a population type."""
        assert not is_valid_population_type('coa_id')
        assert is_identifier_field('coa_id')
        
        is_valid, message = validate_population_type('coa_id')
        assert not is_valid
        assert 'coa_id' in message


# ============================================================================
# Test validate_population_type Function
# ============================================================================

class TestValidatePopulationType:
    """Test the validate_population_type function."""
    
    def test_valid_types_return_true(self):
        """Valid population types should return (True, message)."""
        for pop_type in VALID_POPULATION_TYPES:
            is_valid, message = validate_population_type(pop_type)
            assert is_valid
            assert pop_type in message
    
    def test_invalid_types_return_false(self):
        """Invalid population types should return (False, message)."""
        invalid_types = ['coo_id', 'coa_id', 'year', 'invalid_type', '']
        for pop_type in invalid_types:
            is_valid, message = validate_population_type(pop_type)
            assert not is_valid
    
    def test_none_returns_false(self):
        """None should return (False, message)."""
        is_valid, message = validate_population_type(None)
        assert not is_valid
        assert 'cannot be none' in message.lower() or 'none' in message.lower()
    
    def test_identifier_fields_have_specific_error(self):
        """Identifier fields should have specific error messages."""
        is_valid, message = validate_population_type('coo_id')
        assert not is_valid
        assert 'database identifier' in message.lower()
        assert 'Valid types:' in message
    
    def test_unknown_types_have_specific_error(self):
        """Unknown (non-identifier) types should have appropriate error messages."""
        is_valid, message = validate_population_type('unknown_type')
        assert not is_valid
        assert 'not a standard unhcr' in message.lower() or 'not a standard' in message.lower()


# ============================================================================
# Test Edge Cases
# ============================================================================

class TestEdgeCases:
    """Test edge cases and boundary conditions."""
    
    def test_empty_string(self):
        """Empty string should not be valid."""
        assert not is_valid_population_type('')
        assert not is_identifier_field('')
    
    def test_whitespace_only(self):
        """Whitespace-only strings should not be valid."""
        assert not is_valid_population_type('   ')
        assert not is_identifier_field('   ')
    
    def test_mixed_case_identifier(self):
        """Mixed case identifier fields should still be detected."""
        assert is_identifier_field('COO_ID')
        assert is_identifier_field('Coo_Id')
        assert not is_valid_population_type('COO_ID')
    
    def test_population_type_with_spaces(self):
        """Population types with leading/trailing spaces should be handled."""
        assert is_valid_population_type('  refugees  ')
        assert is_valid_population_type(' asylum_seekers ')


# ============================================================================
# Test Integration with Question Parser
# ============================================================================

class TestQuestionParserIntegration:
    """Test integration with the question parser."""
    
    @pytest.mark.asyncio
    async def test_question_parser_rejects_coo_id(self):
        """Question parser should not extract coo_id as a population type."""
        # Import here to avoid circular import at module level
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "question_parser",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'question_parser.py')
        )
        question_parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(question_parser_module)
        extract_question_parameters = question_parser_module.extract_question_parameters
        
        # This should NOT extract coo_id as population_type
        question = "Show me data for coo_id in 2023"
        params = await extract_question_parameters(question)
        
        # coo_id should not be set as population_type
        assert params.get('population_type') != 'coo_id'
        assert params.get('population_type') is None
    
    @pytest.mark.asyncio
    async def test_question_parser_accepts_valid_types(self):
        """Question parser should accept valid population types."""
        # Import here to avoid circular import at module level
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "question_parser",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'question_parser.py')
        )
        question_parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(question_parser_module)
        extract_question_parameters = question_parser_module.extract_question_parameters
        
        question = "Show me data for refugees in 2023"
        params = await extract_question_parameters(question)
        
        assert params.get('population_type') == 'refugees'
    
    @pytest.mark.asyncio
    async def test_question_parser_case_insensitive(self):
        """Question parser should be case-insensitive for population types."""
        # Import here to avoid circular import at module level
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "question_parser",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'question_parser.py')
        )
        question_parser_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(question_parser_module)
        extract_question_parameters = question_parser_module.extract_question_parameters
        
        question = "Show me data for REFUGEES in 2023"
        params = await extract_question_parameters(question)
        
        assert params.get('population_type') == 'refugees'


# ============================================================================
# Test Integration with Apply Analysis Guardrails
# ============================================================================

class TestApplyAnalysisGuardrailsIntegration:
    """Test integration with the apply_analysis_guardrails tool."""
    
    def test_guardrails_rejects_coo_id(self):
        """Guardrails should reject coo_id as a population type."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        _check_population_definition_compliance = guardrails_module._check_population_definition_compliance
        
        result = _check_population_definition_compliance('coo_id')
        
        assert not result['compliant']
        assert 'IDENTIFIER_FIELD_MISUSE' in result.get('error_type', '')
        assert result.get('severity') == 'CRITICAL'
    
    def test_guardrails_accepts_valid_types(self):
        """Guardrails should accept valid population types."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        _check_population_definition_compliance = guardrails_module._check_population_definition_compliance
        
        for pop_type in VALID_POPULATION_TYPES:
            result = _check_population_definition_compliance(pop_type)
            assert result['compliant']
            assert result['population_type'] == pop_type
    
    def test_guardrails_rejects_unknown_types(self):
        """Guardrails should reject unknown (non-identifier) types."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        _check_population_definition_compliance = guardrails_module._check_population_definition_compliance
        
        result = _check_population_definition_compliance('unknown_type')
        
        assert not result['compliant']
        assert 'INVALID_POPULATION_TYPE' in result.get('error_type', '')
        assert result.get('severity') == 'HIGH'
    
    def test_guardrails_data_disaggregation_rejects_identifiers(self):
        """Guardrails should reject identifier fields in data fields."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        _check_data_disaggregation = guardrails_module._check_data_disaggregation
        
        result = _check_data_disaggregation(
            data_fields=['age', 'sex', 'coo_id'],
            population_type='refugees'
        )
        
        assert not result['compliant']
        assert 'IDENTIFIER_FIELD_IN_DATA' in result.get('error_type', '')
        assert 'coo_id' in result['message']


# ============================================================================
# Test Semantic Safeguard Decorator
# ============================================================================

class TestSemanticSafeguardDecorator:
    """Test the semantic_safeguard decorator."""
    
    def test_decorator_rejects_invalid_population_type(self):
        """Decorator should reject invalid population_type parameter."""
        @semantic_safeguard
        def dummy_tool(population_type=None):
            return {'success': True}
        
        result = dummy_tool(population_type='coo_id')
        
        assert result['status'] == 'error'
        assert 'validation_failed' in result
        assert result['invalid_parameter'] == 'population_type'
        assert result['invalid_value'] == 'coo_id'
    
    def test_decorator_accepts_valid_population_type(self):
        """Decorator should accept valid population_type parameter."""
        @semantic_safeguard
        def dummy_tool(population_type=None):
            return {'success': True, 'population_type': population_type}
        
        result = dummy_tool(population_type='refugees')
        
        assert result['success'] is True
        assert result['population_type'] == 'refugees'
    
    def test_decorator_rejects_invalid_population_types_list(self):
        """Decorator should reject invalid types in population_types list."""
        @semantic_safeguard
        def dummy_tool(population_types=None):
            return {'success': True}
        
        result = dummy_tool(population_types=['refugees', 'coo_id'])
        
        assert result['status'] == 'error'
        assert 'validation_failed' in result
        assert result['invalid_parameter'] == 'population_types'
        assert result['invalid_value'] == 'coo_id'


# ============================================================================
# Test Real-World Scenarios
# ============================================================================

class TestRealWorldScenarios:
    """Test real-world scenarios where coo_id might be misused."""
    
    def test_scenario_chart_creation_with_coo_id(self):
        """Simulate the original issue: coo_id being used in chart creation."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        apply_analysis_guardrails_tool = guardrails_module.apply_analysis_guardrails_tool
        
        # This simulates what might happen in chart creation
        result = apply_analysis_guardrails_tool(
            analysis_request={'context': 'Create chart with coo_id'},
            population_type='coo_id',
            detailed_report=True
        )
        
        # Should not be compliant
        assert not result['overall_compliant']
        
        # Should have population definition error
        pop_check = result['detailed_report']['population_definition']
        assert not pop_check['compliant']
        assert 'coo_id' in pop_check['message']
        assert 'database identifier' in pop_check['message'].lower()
    
    def test_scenario_valid_chart_creation(self):
        """Test that valid chart creation still works."""
        import importlib.util
        spec = importlib.util.spec_from_file_location(
            "apply_analysis_guardrails",
            os.path.join(os.path.dirname(__file__), '..', 'backend', 'mcp', 'tools', 'apply_analysis_guardrails.py')
        )
        guardrails_module = importlib.util.module_from_spec(spec)
        spec.loader.exec_module(guardrails_module)
        apply_analysis_guardrails_tool = guardrails_module.apply_analysis_guardrails_tool
        
        result = apply_analysis_guardrails_tool(
            analysis_request={'context': 'Create chart with refugees'},
            population_type='refugees',
            detailed_report=True
        )
        
        # Should be compliant for population definition
        pop_check = result['detailed_report']['population_definition']
        assert pop_check['compliant']
        assert pop_check['population_type'] == 'refugees'


# ============================================================================
# Run Tests
# ============================================================================

if __name__ == '__main__':
    pytest.main([__file__, '-v', '--tb=short'])
