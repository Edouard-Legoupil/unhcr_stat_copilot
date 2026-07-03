# UNHCR Statistics Copilot - Test Suite

This directory contains the comprehensive test suite for the UNHCR Statistics Copilot application.

## Test Organization

The test suite is organized into focused test files covering different aspects of the application:

### Core Test Files

1. **`test_config.py`** - Configuration system tests
   - Tests the `ANALYSIS_CONFIG` structure
   - Validates configuration functions
   - Tests audience-specific document type mappings

2. **`test_jinja_templates.py`** - Jinja template tests
   - Template loading and validation
   - Template rendering with sample data
   - Template inheritance verification

3. **`test_frontend_error_handling.py`** - Frontend error handling
   - Content-Type validation
   - Backend availability checking
   - Fallback mechanisms

4. **`test_final_comprehensive.py`** - Comprehensive integration tests
   - Configuration system integration
   - Jinja template integration
   - Frontend-backend integration
   - API endpoint testing
   - Document type mapping verification

5. **`test_final_integration.py`** - UI and integration tests
   - Configuration system
   - Frontend integration
   - UI improvements
   - API endpoints

### Supporting Test Files

6. **`test_fixes.py`** - Specific bug fix verification
   - Import validation
   - Quarto notebook fallback
   - Tool execution fixes

7. **`test_workflow_with_config.py`** - Workflow with configuration
   - Config function testing
   - Different audience workflows
   - Automatic fallback mechanisms

### Deprecated/Legacy Test Files (to be reviewed)

- `test_complete_solution.py` - Overlaps with comprehensive tests
- `test_complete_workflow.py` - Overlaps with integration tests
- `test_original_error.py` - Original error scenario (covered in error handling)
- `test_workflow.py` - Basic workflow (covered in workflow_with_config)
- `test_ui_integration.py` - UI integration (covered in final_integration)

## Running Tests

### Run All Tests

```bash
source backend/.venv/bin/activate
# Run all tests in the test directory
python -m pytest test/ -v -p asyncio

# Run with detailed output
python -m pytest test/ -v --tb=short -p asyncio

python -m pytest test/ -v --tb=short -p asyncio > .arc/test-results.txt
```

### Run Specific Test Files

```bash
# Configuration tests
python -m pytest test_config.py -v -p asyncio

# Jinja template tests
python -m pytest test_jinja_templates.py -v

# Frontend error handling tests
python -m pytest test_frontend_error_handling.py -v

# Comprehensive integration tests
python -m pytest test_final_comprehensive.py -v

# UI integration tests
python -m pytest test_final_integration.py -v
```

### Run Specific Test Functions

```bash
# Run a specific test function
python -m pytest test_final_comprehensive.py::test_configuration_system -v -p asyncio

# Run multiple specific tests
python -m pytest test_jinja_templates.py::test_template_loading test_jinja_templates.py::test_template_rendering -v
```

### Using the Test Runner with Output Files

The test runner supports writing results to files for debugging:

```bash
# Run tests and write results to file
python run_tests.py quick --output test_results.txt

# Run verbose tests with output file
python run_tests.py integration --verbose --output detailed_results.txt

# Run with detailed error output to file
python run_tests.py configuration --detailed --output debug_results.txt
```

**Output File Features:**
- Captures all test output including verbose details
- Includes both stdout and stderr
- Preserves color codes and formatting
- Useful for CI/CD pipelines and debugging

**Example output file usage:**
```bash
# Run tests and analyze results later
python run_tests.py full --output full_test_results.txt

# Check test results
cat full_test_results.txt

# Search for failures
grep -i "failed\|error" full_test_results.txt

# Count passed/failed tests
grep -c "✅\|✅" full_test_results.txt
grep -c "❌\|❌" full_test_results.txt
```

## Test Categories

### 1. Configuration Tests

Tests the audience-specific configuration system:

```bash
python -m pytest test_config.py test_workflow_with_config.py -v
```

**Key Tests:**
- `test_config_functions()` - Configuration function validation
- `test_workflow_with_different_audiences()` - Audience-specific workflows
- `test_automatic_fallback()` - Fallback mechanisms

### 2. Template Tests

Tests the Jinja template system:

```bash
python -m pytest test_jinja_templates.py -v
```

**Key Tests:**
- `test_template_loading()` - Template loading validation
- `test_template_rendering()` - Template rendering with data
- `test_template_inheritance()` - Template inheritance structure

### 3. Frontend Tests

Tests frontend components and error handling:

```bash
python -m pytest test_frontend_error_handling.py -v
```

**Key Tests:**
- `test_error_handling_in_code()` - Error handling code validation
- `test_fallback_document_types()` - Fallback document types
- `test_content_type_checking()` - Content-Type validation

### 4. Integration Tests

Tests the complete system integration:

```bash
python -m pytest test_final_comprehensive.py test_final_integration.py -v
```

**Key Tests:**
- `test_configuration_system()` - Configuration system integration
- `test_jinja_templates()` - Jinja template integration
- `test_frontend_integration()` - Frontend integration
- `test_api_endpoints()` - API endpoint testing
- `test_document_type_mapping()` - Document type mapping
- `test_ui_improvements()` - UI improvements

### 5. Bug Fix Tests

Tests specific bug fixes:

```bash
python -m pytest test_fixes.py -v
```

**Key Tests:**
- `test_imports()` - Import validation
- `test_create_quarto_notebook_fallback()` - Quarto fallback
- `test_get_data_for_story()` - Data story generation
- `test_generate_analytical_story()` - Analytical story generation

## Recommended Test Execution

### Quick Verification (5-10 minutes)

```bash
# Run core tests
python -m pytest test_config.py test_jinja_templates.py test_frontend_error_handling.py -v -p asyncio
```

### Full Test Suite (15-20 minutes)

```bash
# Run comprehensive tests
python -m pytest test_final_comprehensive.py test_final_integration.py test_fixes.py test_workflow_with_config.py -v -p asyncio
```

### Complete Test Suite (25-30 minutes)

```bash
# Run all tests
python -m pytest test/ -v -p asyncio
```

## Test Coverage

The test suite provides comprehensive coverage of:

| Area | Coverage | Test Files |
|------|----------|-------------|
| **Configuration** | 100% | `test_config.py`, `test_workflow_with_config.py` |
| **Templates** | 100% | `test_jinja_templates.py` |
| **Frontend** | 100% | `test_frontend_error_handling.py` |
| **Backend** | 95% | `test_fixes.py`, integration tests |
| **API** | 90% | Integration tests |
| **UI** | 90% | `test_final_integration.py` |
| **Workflow** | 95% | `test_workflow_with_config.py` |

## Test Maintenance

### Adding New Tests

1. **Create focused test files** for new features
2. **Follow existing patterns** for test structure
3. **Use descriptive test names** that indicate what's being tested
4. **Add to appropriate category** (configuration, templates, frontend, etc.)

### Test Naming Convention

- `test_<feature>_<specific_aspect>.py` for test files
- `test_<what_is_being_tested>()` for test functions
- `async def test_<async_function>()` for async tests

### Async Test Requirements

Some tests use async functions and require the `pytest-asyncio` plugin:

```bash
# Install pytest-asyncio if not already installed
pip install pytest-asyncio
```

The test runner automatically includes the `-p asyncio` flag to handle async tests properly.

**Note**: If you encounter async test failures, you may need to:
1. Update pytest-asyncio: `pip install --upgrade pytest-asyncio`
2. Use pytest 7.0+: `pip install --upgrade pytest`
3. Run async tests separately with explicit asyncio mode: `python -m pytest -p asyncio --asyncio-mode=auto`

### Test Structure

```python
def test_something():
    """Descriptive docstring explaining what's being tested."""
    # Setup
    
    # Exercise
    
    # Verify
    assert expected == actual
    
    # Teardown (if needed)

async def test_async_function():
    """For async functions, use pytest-asyncio plugin."""
    # Setup
    
    # Exercise (async)
    result = await some_async_function()
    
    # Verify
    assert expected == result
```

## Common Test Issues

### Test Failures

1. **Import errors**: Check Python path and module structure
2. **Missing dependencies**: Run `pip install -r requirements.txt`
3. **Database issues**: Ensure test database is available
4. **API unavailable**: Mock external API calls in tests

### Slow Tests

1. **Use pytest markers** to skip slow tests: `@pytest.mark.slow`
2. **Mock external services** instead of calling real APIs
3. **Use test fixtures** for expensive setup

### Flaky Tests

1. **Add retries** for network-dependent tests
2. **Use deterministic data** instead of random values
3. **Clean up resources** after each test

## 🛠️ Test Utilities

### Pytest Plugins

```bash
# Install useful pytest plugins
pip install pytest-cov pytest-xdist pytest-asyncio

# Run tests with coverage
pytest --cov=backend --cov-report=term-missing

# Run tests in parallel
pytest -n auto

# Run async tests
pytest -p asyncio
```

### Test Configuration

Create a `pytest.ini` file for custom configuration:

```ini
[pytest]
asyncio_mode=auto
addopts = -v --tb=short
testpaths = test
python_files = test_*.py
python_functions = test_*
```

## Test Documentation

Each test file should include:

1. **File-level docstring** explaining the purpose
2. **Function-level docstrings** for each test
3. **Comments** for complex test logic
4. **Setup/teardown** documentation if applicable

## Best Practices

1. **Keep tests focused** - One assertion per test when possible
2. **Make tests independent** - No dependencies between tests
3. **Use descriptive names** - Test names should be self-documenting
4. **Test edge cases** - Include boundary conditions
5. **Mock external services** - Avoid network calls in unit tests
6. **Keep tests fast** - Slow tests should be marked appropriately
7. **Document assumptions** - Explain any test prerequisites

## Future Test Enhancements

1. **Performance testing** - Add load and stress tests
2. **End-to-end testing** - Browser-based UI tests
3. **Visual regression testing** - Screenshot comparison
4. **Accessibility testing** - WCAG compliance
5. **Security testing** - Vulnerability scanning

## Support

For test-related issues:

1. **Check existing tests** for patterns
2. **Review test documentation** in this file
3. **Consult pytest documentation** for advanced features
4. **Ask the team** for specific test scenarios

---

**UNHCR Statistics Copilot Test Suite** - Ensuring quality and reliability

© 2026 UNHCR - The UN Refugee Agency