# CrewAI YAML Configuration

This directory contains YAML-based configuration files for CrewAI agents, tasks, and crews.

## 📁 Directory Structure

```
yaml_config/
├── README.md              # This file
├── __init__.py            # Module exports
├── loader.py              # YAML configuration loader
├── agents/                # Agent configurations
│   ├── analysts.yaml      # Analyst agents (StatisticalAnalyzer, GuardrailsValidator, etc.)
│   ├── data_fetchers.yaml # Data fetcher agents (UNHCRDataFetcher, RSDExpert, etc.)
│   ├── story_generators.yaml # Story generator agents (StoryGenerator, RAGResearcher, etc.)
│   └── orchestrators.yaml  # Orchestrator agents (AnalysisOrchestrator, NotebookGenerator, etc.)
├── tasks/                # Task configurations
│   ├── analysis_tasks.yaml
│   ├── data_tasks.yaml
│   ├── notebook_tasks.yaml
│   ├── story_tasks.yaml
│   └── workflow_tasks.yaml
└── crews/                # Crew configurations
    ├── analysis_crew.yaml
    ├── data_crew.yaml
    ├── notebook_crew.yaml
    ├── story_crew.yaml
    └── master_crew.yaml
```

## 🎯 Purpose

This configuration system allows you to define CrewAI agents, tasks, and crews using **YAML files** instead of hardcoding them in Python. This provides:

### Benefits

1. **Improved Readability** - YAML is more human-readable than Python dictionaries
2. **Easier Maintenance** - Change configurations without modifying code
3. **Better Organization** - Configurations are separated from implementation
4. **Version Control Friendly** - Easier to track changes to configurations
5. **Reusability** - Same agent can be referenced by multiple crews
6. **Documentation** - YAML files serve as living documentation

## 🚀 Usage

### Basic Usage

```python
# Import the loader
from backend.crewai.yaml_config.loader import load_agent, load_crew, YAMLConfigLoader

# Load a specific agent configuration
agent_config = load_agent('statistical_analyzer')

# Load all agents
all_agents = load_agents()

# Load a crew configuration
crew_config = load_crew('analysis_crew')

# Load all crews
all_crews = load_crews()
```

### Instantiating from YAML

```python
from backend.crewai.yaml_config.loader import config_loader

# Instantiate an agent from YAML
loader = YAMLConfigLoader()
agent = loader.instantiate_agent(
    agent_config={'name': 'statistical_analyzer'},
    audience='internal',
    document_type='technical_report'
)

# Load and instantiate an entire crew
crew = loader.load_and_instantiate_crew(
    crew_name='analysis_crew',
    audience='policy_makers',
    document_type='executive_summary'
)
```

## 📝 File Format

### Agent Configuration

Each agent YAML file contains a list of agent definitions:

```yaml
analysts:
  - name: statistical_analyzer
    class_name: StatisticalAnalyzer
    module: backend.crewai.agents.analysts
    role: Statistical Analyst
    goal: Perform comprehensive statistical analysis on displacement data
    description: |
      Multi-line description of the agent...
    
    tools:
      - name: analyze_data_statistics
        source: backend.mcp.tools.analyze_data_statistics
        adapter: MCPToolAdapter.adapt_mcp_tool
        description: Tool description
        parameters:
          - param1
          - param2
    
    capabilities:
      - statistical_analysis
      - data_insights
    
    methods:
      - analyze_data
      - analyze_statistics
```

### Task Configuration

Each task YAML file contains a list of task definitions:

```yaml
tasks:
  - name: fetch_population_data
    description: Task description
    agent: unhcr_data_fetcher  # References an agent by name
    expected_output: |
      Description of expected output format...
    
    context:
      - question
      - parameters
      - audience
    
    async_execution: false
    
    parameters:
      - name: question
        type: str
        required: true
        description: The user's question
```

### Crew Configuration

Each crew YAML file defines a crew with its agents and workflow:

```yaml
name: analysis_crew

# Crew-level settings
process_type: sequential
verbose: 2
memory: true
cache: true

description: Crew description

# Agent references (loaded from agents/ directory)
agents:
  - statistical_analyzer
  - guardrails_validator
  - tool_selector
  - visualization_expert

# Workflow definition
workflow:
  - name: analyze_data
    description: Perform data analysis
    agent: statistical_analyzer
    expected_output: Analysis results
    context:
      - question
      - data
    
  - name: validate_guardrails
    description: Validate analysis
    agent: guardrails_validator
    depends_on: analyze_data
```

## 🔄 Migration Guide

### For Existing Code

If you have existing code that creates agents and crews directly, you can migrate to YAML:

**Before (Hardcoded):**
```python
# In your Python file
agent = StatisticalAnalyzer(
    role='Statistical Analyst',
    goal='Perform analysis',
    audience=audience,
    document_type=document_type
)
```

**After (YAML-based):**
```python
# Load from YAML
from backend.crewai.yaml_config.loader import config_loader

agent = config_loader.instantiate_agent(
    agent_config={'name': 'statistical_analyzer'},
    audience=audience,
    document_type=document_type
)
```

### Gradual Migration

You don't need to migrate everything at once. The YAML loader coexists with existing code:

1. Start by creating YAML files for new agents/tasks/crews
2. Gradually migrate existing definitions to YAML
3. Update your code to use the loader where appropriate
4. Keep backward compatibility by maintaining both systems

## ✅ Best Practices

### 1. Naming Conventions

- Use **snake_case** for agent, task, and crew names
- Use **lowercase** for YAML files
- Keep names descriptive but concise

### 2. Organization

- Group related agents in the same YAML file
- Keep each file focused on a specific domain (analysis, data, stories, etc.)
- Use comments liberally to explain configurations

### 3. Documentation

- Always include a `description` field for agents, tasks, and crews
- Use multi-line strings (`|`) for longer descriptions
- Document all parameters and their purposes

### 4. Version Control

- Commit YAML files alongside code changes
- Use meaningful commit messages (e.g., "feat: add RSD expert agent")
- Review YAML changes as carefully as code changes

## 🐛 Troubleshooting

### Common Issues

1. **YAML file not found**
   - Check that the file exists in the correct directory
   - Verify the file has a `.yaml` or `.yml` extension
   - Check for typos in the file name

2. **Agent class not found**
   - Verify the `module` and `class_name` are correct
   - Ensure the module can be imported
   - Check that the class exists in the module

3. **Tool source not found**
   - Verify the `source` path is correct
   - Ensure the source module is importable
   - Check that the tool function exists

4. **Missing required fields**
   - Check that all required fields are present in the YAML
   - Use `default` values for optional fields

### Debugging

Enable debug logging to see what's happening:

```python
import logging
logging.basicConfig(level=logging.DEBUG)

from backend.crewai.yaml_config.loader import config_loader
config = config_loader.load_agent('my_agent')
```

## 📚 Examples

See the existing YAML files in this directory for complete, working examples of:

- [Agent configurations](agents/)
- [Task configurations](tasks/)
- [Crew configurations](crews/)

## 🎓 Learning Resources

- [YAML Specification](https://yaml.org/spec/)
- [PyYAML Documentation](https://pyyaml.org/wiki/PyYAMLDocumentation)
- [CrewAI Documentation](https://docs.crewai.com/)

## 💬 Support

For issues with the YAML configuration system:

1. Check this README first
2. Review the existing YAML files for examples
3. Check the logs for error messages
4. Create an issue with reproduction steps

## 📝 Contributing

When adding new agents, tasks, or crews:

1. Create a new YAML file or add to an existing one
2. Follow the existing format and conventions
3. Add appropriate descriptions and documentation
4. Test that the configuration loads correctly
5. Commit with a descriptive message

---

*Maintained by: UNHCR Statistics Copilot Development Team*
*Location: `/backend/crewai/yaml_config/`*
