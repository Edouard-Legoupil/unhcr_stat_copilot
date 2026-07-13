# CrewAI Test Suite

This directory contains comprehensive tests for the CrewAI integration in UNHCR Statistics Copilot.

## Test Modules

### 1. `test_agents.py`
Tests for all CrewAI agent classes:
- `UNHCRBaseAgent` - Base agent class
- `UNHCRDataFetcher` - Data fetching agent
- `RSDExpert` - RSD data agent
- `SolutionsExpert` - Solutions data agent
- `DemographicsExpert` - Demographics agent
- `TemporalAnalyzer` - Time-series analysis agent
- `GeographyExpert` - Geographic analysis agent
- `StatisticalAnalyzer` - Statistical analysis agent
- `GuardrailsValidator` - Guardrails validation agent
- `ToolSelector` - Tool selection agent
- `VisualizationExpert` - Visualization agent
- `StoryGenerator` - Story generation agent
- `RAGResearcher` - RAG research agent
- `AudienceAdapter` - Audience adaptation agent
- `AnalysisOrchestrator` - Workflow orchestration agent
- `NotebookGenerator` - Notebook generation agent

### 2. `test_crews.py`
Tests for all CrewAI crew classes:
- `DataCrew` - Data fetching crew
- `AnalysisCrew` - Analysis crew
- `StoryCrew` - Story generation crew
- `NotebookCrew` - Notebook generation crew
- `MasterCrew` - Master orchestration crew

### 3. `test_manager.py`
Tests for the CrewAIManager class:
- Initialization and configuration
- Agent management
- Workflow execution
- Metrics tracking
- Shutdown and cleanup

### 4. `test_migration.py`
Tests for migration utilities:
- `MigrationConfig` - Configuration loading
- `MigrationMetrics` - Metrics tracking
- `MigrationRouter` - Request routing
- Multiple migration modes (MCP_ONLY, CREWAI_ONLY, DUAL_RUN, HYBRID, FALLBACK)
- Multiple routing strategies (RANDOM, ROUND_ROBIN, PERCENTAGE, TOOL_BASED, AUDIENCE_BASED)

### 5. `test_integration.py`
Tests for integration between components:
- CrewAI and MCP server
- CrewAI and FastAPI app
- CrewAI tool adapter
- All CrewAI-based tool implementations

## Running Tests

### Run all tests
```bash
cd /home/edouard/python/unhcr_stat_copilot
python -m pytest test/crewai/ -v
```

### Run specific test module
```bash
python -m pytest test/crewai/test_agents.py -v
python -m pytest test/crewai/test_crews.py -v
python -m pytest test/crewai/test_manager.py -v
python -m pytest test/crewai/test_migration.py -v
python -m pytest test/crewai/test_integration.py -v
```

### Run with coverage
```bash
python -m pytest test/crewai/ --cov=backend/crewai --cov-report=html
```

### Run with specific markers
```bash
# Run only unit tests
python -m pytest test/crewai/ -m unit -v

# Run only integration tests
python -m pytest test/crewai/ -m integration -v
```

## Test Configuration

Tests can be configured using environment variables:

- `CREWAI_ENABLED`: Enable/disable CrewAI features (default: false)
- `CREWAI_MIGRATION_MODE`: Migration mode for tests (default: mcp_only)
- `CREWAI_ROUTING_STRATEGY`: Routing strategy for tests
- `CREWAI_MCP_PERCENTAGE`: Percentage for MCP routing
- `CREWAI_CREWAI_PERCENTAGE`: Percentage for CrewAI routing

## Mocking CrewAI

Since CrewAI might not be installed in all test environments, all tests are designed to work with mocked CrewAI components. The mocks are provided in the `backend/crewai/tools/adapters.py` file.

## Test Structure

Each test module follows this structure:

1. **Test Classes**: Grouped by the component being tested
2. **Test Methods**: Each method tests a specific behavior
3. **Assertions**: Verify expected outcomes
4. **Setup/Teardown**: Configure test environment

## Best Practices

1. **Isolate tests**: Each test should be independent
2. **Use mocks**: For external dependencies
3. **Test edge cases**: Include error handling tests
4. **Keep tests fast**: Avoid slow operations in unit tests
5. **Clear assertions**: Make assertions descriptive

## Contributing

When adding new tests:
1. Follow the existing structure
2. Add tests to the appropriate module
3. Ensure tests pass with mocked CrewAI
4. Add both success and error case tests
5. Keep test files under 500 lines when possible
