# UNHCR Statistics Copilot: Migration Plan to CrewAI

## Executive Summary

This document outlines the migration of the UNHCR Statistics Copilot backend from its current client-side tool orchestration to a **CrewAI-based agent system** that mirrors MCP (Model Context Protocol) capabilities. The migration will retain the app's core functionality: generating well-documented Quarto notebooks with comprehensive analysis logs.

## Current Architecture Analysis

### 1. Existing Components

#### MCP Server (`backend/mcp/server.py`)
- **Framework**: FastMCP (Python MCP implementation)
- **Tools**: 25+ registered tools covering:
  - **Data Fetching**: `get_population_data`, `get_demographics_data`, `get_rsd_applications`, `get_rsd_decisions`, `get_solutions`, `get_country_key_figures`, `get_population_trends`, `get_demographic_breakdown`
  - **Analysis**: `analyze_data_statistics`, `apply_analysis_guardrails`, `safe_tool_selection`
  - **Visualization**: `extract_visualization_structure`, `generate_visualization_description`
  - **Story Generation**: `get_data_for_story`, `generate_analytical_story`
  - **Export**: `create_quarto_notebook`
  - **Workflow Orchestration**: `full_analysis_workflow`, `quick_analysis`, `compare_analysis`, `run_enhanced_analysis`, `run_conditional_analysis`
  - **Meta**: `get_usage_guidance`, `get_suggested_questions`, `retrieve_report_context`

#### Backend Orchestration (`backend/app.py`, `backend/chat.py`)
- **FastAPI endpoints** that call MCP tools directly
- **Chat processing** with audience-specific configuration
- **Parameter extraction** from natural language questions
- **Tool chaining** logic embedded in Python functions

#### Workflow System (`backend/mcp/tools/workflows.py`)
- **`full_analysis_workflow_tool`**: 4-step process (question classification → data retrieval → story generation → notebook creation)
- **`quick_analysis_tool`**: Lightweight analysis without notebook
- **`compare_analysis_tool`**: Multi-scenario comparative analysis

#### Analysis Pipeline (`backend/mcp/tools/analysis_pipeline.py`)
- **5-phase pipeline**: Statistical analysis → Compliance validation → Visualization structure → Visualization description → Enhanced story generation
- **Non-blocking errors**: Each phase continues even if previous fails
- **RAG integration**: Optional Retrieval-Augmented Generation for enriched stories

#### Template System (`backend/templates/`)
- **6 Jinja2 templates**: base_quarto.j2, technical_report.j2, executive_summary.j2, long_read.j2, social_media.j2, linkedin_post.j2
- **Audience-aware**: Each template incorporates audience-specific configuration
- **Dynamic content**: Placeholders for data, charts, and narrative

#### Audience Configuration (`backend/chat.py`)
- **5 audience types**: internal, public_donors, private_donors, government, media
- **3 document types each**: technical_report, long_read, executive_summary, social_media, linkedin_post
- **Configuration includes**: tone, length (word range, reading time, density), structure (section breakdown)

### 2. Current Tool Orchestration Flow

```
User Question → FastAPI Endpoint → MCP Bridge → Tool Selection → Data Fetching → 
Analysis → Visualization → Story Generation → Quarto Notebook → Response
```

The orchestration is currently:
- **Imperative**: Python functions call tools sequentially
- **Hardcoded**: Tool chains are defined in code
- **Client-side**: Orchestration logic lives in the backend, not in the MCP server
- **Synchronous/Async Mix**: Some tools are sync, some are async

## Migration Goals

### Primary Objectives
1. **Replace imperative orchestration** with declarative CrewAI agent teams
2. **Mirror MCP capabilities** in CrewAI tools
3. **Retain Quarto notebook generation** with well-documented analysis logs
4. **Maintain audience-specific configuration** system
5. **Preserve all existing functionality** during and after migration

### Success Criteria
- ✅ All 25+ MCP tools available as CrewAI tools
- ✅ CrewAI agents can perform end-to-end analysis workflows
- ✅ Quarto notebooks generated with same quality and structure
- ✅ Analysis logs maintained with full observability
- ✅ Audience-specific configuration respected
- ✅ Zero downtime during migration (gradual rollout)

## CrewAI Architecture Design

### 1. Agent Hierarchy

#### Level 1: Specialist Agents (Tool-level)
Each MCP tool becomes a CrewAI agent with the tool as its primary capability.

```python
class UNHCRDataFetcher(Agent):
    """Specialist agent for fetching UNHCR population data"""
    role = "UNHCR Data Fetcher"
    goal = "Retrieve accurate population statistics from UNHCR API"
    backstory = "Expert in UNHCR data structures and API endpoints..."
    tools = [get_population_data, get_demographics_data, ...]
    verbose = True
```

#### Level 2: Analysis Agents (Pipeline-level)
Agents that orchestrate multiple tools for specific analysis types.

```python
class StatisticalAnalyzer(Agent):
    """Agent for statistical analysis of UNHCR data"""
    role = "Statistical Analyst"
    goal = "Perform comprehensive statistical analysis on displacement data"
    backstory = "Expert statistician with UNHCR methodology knowledge..."
    tools = [analyze_data_statistics, apply_analysis_guardrails, ...]
```

#### Level 3: Orchestration Agents (Workflow-level)
High-level agents that manage complete analysis workflows.

```python
class AnalysisOrchestrator(Agent):
    """Master agent that coordinates complete analysis workflows"""
    role = "Analysis Orchestrator"
    goal = "Deliver end-to-end analysis from question to Quarto notebook"
    backstory = "Senior analyst coordinating all aspects of UNHCR data analysis..."
    tools = [all MCP tools + delegation to specialist agents]
```

### 2. Crew Structure

```python
# Data Fetching Crew
DataFetchingCrew = Crew(
    agents=[UNHCRDataFetcher, GeographyExpert, TemporalAnalyzer],
    tasks=[fetch_population_data_task, validate_data_task],
    process=Sequential()
)

# Analysis Crew
AnalysisCrew = Crew(
    agents=[StatisticalAnalyzer, VisualizationExpert, GuardrailsValidator],
    tasks=[analyze_statistics_task, generate_visualizations_task, apply_guardrails_task],
    process=Sequential()
)

# Story Generation Crew
StoryCrew = Crew(
    agents=[StoryGenerator, RAGResearcher, AudienceAdapter],
    tasks=[generate_story_task, enrich_with_rag_task, adapt_to_audience_task],
    process=Sequential()
)

# Master Analysis Crew (orchestrates all crews)
MasterAnalysisCrew = Crew(
    agents=[AnalysisOrchestrator],
    tasks=[full_workflow_task],
    process=Sequential()
)
```

### 3. Tool Mapping

#### Direct Tool Mapping (1:1)
MCP tools that can be directly mapped to CrewAI tools:

| MCP Tool | CrewAI Tool | Agent | Category |
|----------|-------------|--------|----------|
| `get_population_data` | `fetch_population_data` | UNHCRDataFetcher | Data |
| `get_demographics_data` | `fetch_demographics` | UNHCRDataFetcher | Data |
| `get_rsd_applications` | `fetch_rsd_applications` | RSDExpert | Data |
| `get_rsd_decisions` | `fetch_rsd_decisions` | RSDExpert | Data |
| `get_solutions` | `fetch_solutions` | SolutionsExpert | Data |
| `get_country_key_figures` | `fetch_key_figures` | UNHCRDataFetcher | Data |
| `get_population_trends` | `fetch_trends` | TemporalAnalyzer | Data |
| `get_demographic_breakdown` | `fetch_breakdown` | DemographicsExpert | Data |
| `analyze_data_statistics` | `analyze_statistics` | StatisticalAnalyzer | Analysis |
| `apply_analysis_guardrails` | `validate_guardrails` | GuardrailsValidator | Analysis |
| `extract_visualization_structure` | `extract_viz_structure` | VisualizationExpert | Visualization |
| `generate_visualization_description` | `describe_visualization` | VisualizationExpert | Visualization |
| `retrieve_report_context` | `retrieve_context` | RAGResearcher | RAG |
| `get_usage_guidance` | `get_guidance` | SystemAdvisor | Meta |
| `get_suggested_questions` | `suggest_questions` | QueryAssistant | Meta |
| `safe_tool_selection` | `select_tool` | ToolSelector | Meta |

#### Composite Tools (Orchestrated)
MCP tools that orchestrate multiple underlying tools:

| MCP Tool | CrewAI Implementation | Agents Involved |
|----------|----------------------|-----------------|
| `get_data_for_story` | Crew task combining data fetchers | UNHCRDataFetcher, ToolSelector |
| `generate_analytical_story` | Crew task with RAG option | StoryGenerator, RAGResearcher |
| `create_quarto_notebook` | Crew task with template rendering | NotebookGenerator |
| `full_analysis_workflow` | Master crew orchestration | All agents |
| `run_enhanced_analysis` | Analysis crew execution | StatisticalAnalyzer, GuardrailsValidator, VisualizationExpert |
| `run_conditional_analysis` | Conditional crew execution | AnalysisOrchestrator |
| `quick_analysis` | Simplified crew execution | UNHCRDataFetcher, StoryGenerator |
| `compare_analysis` | Parallel crew execution | AnalysisOrchestrator (manages multiple) |

### 4. Quarto Notebook Generation

#### Current Flow:
```python
# In create_quarto_notebook.py
async def create_quarto_notebook_tool(story_content, output_path, ...):
    # 1. Extract data from story_content
    # 2. Select Jinja2 template based on document_type
    # 3. Render template with story data
    # 4. Generate Quarto markdown
    # 5. Save to file
    # 6. Return notebook content and metadata
```

#### New CrewAI Flow:
```python
class NotebookGenerator(Agent):
    role = "Quarto Notebook Generator"
    goal = "Create well-documented Quarto notebooks from analysis results"
    backstory = "Expert in Quarto format and UNHCR documentation standards..."
    
    def generate_notebook(self, story_content, audience, document_type, metadata):
        # 1. Validate inputs
        # 2. Select appropriate template
        # 3. Enrich with analysis logs
        # 4. Render using Jinja2
        # 5. Add observability metadata
        # 6. Return complete notebook
```

## Implementation Phases

### Phase 1: Foundation (Week 1-2)
**Objective**: Set up CrewAI infrastructure and mirror MCP tools

#### Tasks:
1. **Install CrewAI**
   ```bash
   pip install crewai crewai-tools
   ```

2. **Create Agent Base Classes** (`backend/crewai/agents/`)
   - Base agent with common configuration
   - UNHCR-specific agent traits
   - Error handling and logging standards

3. **Create Tool Adapters** (`backend/crewai/tools/`)
   - Adapt MCP tools to CrewAI tool format
   - Handle async/sync compatibility
   - Standardize input/output formats

4. **Build Specialist Agents**
   - Data fetchers (UNHCR, RSD, Solutions)
   - Analysts (Statistical, Guardrails)
   - Visualization experts
   - Story generators

#### Deliverables:
- ✅ CrewAI installed and configured
- ✅ `backend/crewai/` directory structure
- ✅ All MCP tools available as CrewAI tools
- ✅ Specialist agents implemented and tested

### Phase 2: Orchestration (Week 3-4)
**Objective**: Build CrewAI crews that replace current orchestration

#### Tasks:
1. **Create Crew Definitions** (`backend/crewai/crews/`)
   - DataFetchingCrew
   - AnalysisCrew
   - StoryCrew
   - NotebookCrew
   - MasterAnalysisCrew

2. **Implement Crew Tasks**
   - Map existing workflows to crew tasks
   - Handle tool dependencies
   - Manage async execution

3. **Build Audience Configuration Bridge**
   - Integrate ANALYSIS_CONFIG into CrewAI context
   - Pass audience/document_type to crews
   - Maintain configuration consistency

4. **Implement Error Handling**
   - Crew-level error recovery
   - Tool fallback mechanisms
   - Graceful degradation

#### Deliverables:
- ✅ All crews defined and functional
- ✅ End-to-end workflows working via crews
- ✅ Audience configuration integrated
- ✅ Error handling implemented

### Phase 3: Integration (Week 5-6)
**Objective**: Integrate CrewAI with existing backend

#### Tasks:
1. **Create CrewAI Manager** (`backend/crewai/manager.py`)
   - Single entry point for crew execution
   - Crew lifecycle management
   - Result aggregation and formatting

2. **Update MCP Server** (`backend/mcp/server.py`)
   - Add CrewAI-based tool implementations
   - Maintain backward compatibility
   - Gradual migration path

3. **Update Backend Endpoints** (`backend/app.py`)
   - Route requests to CrewAI manager
   - Maintain existing API contracts
   - Add crew execution metrics

4. **Build Migration Utilities**
   - A/B testing framework
   - Rollback mechanisms
   - Performance comparison tools

#### Deliverables:
- ✅ CrewAI manager operational
- ✅ MCP server with CrewAI tools
- ✅ Backend endpoints updated
- ✅ Migration utilities ready

### Phase 4: Migration & Testing (Week 7-8)
**Objective**: Migrate production traffic to CrewAI

#### Tasks:
1. **A/B Testing**
   - Route 10% of traffic to CrewAI
   - Compare results with existing system
   - Monitor performance and errors

2. **Gradual Rollout**
   - Increase traffic to CrewAI incrementally
   - Monitor key metrics:
     - Response time
     - Success rate
     - Quarto notebook quality
     - Analysis log completeness

3. **Bug Fixes**
   - Address issues from A/B testing
   - Optimize crew configurations
   - Tune agent parameters

4. **Performance Optimization**
   - Optimize crew task execution
   - Tune agent parallelism
   - Improve tool caching

#### Deliverables:
- ✅ CrewAI handling 100% of production traffic
- ✅ All tests passing
- ✅ Performance metrics acceptable
- ✅ Rollback plan documented

### Phase 5: Cleanup & Documentation (Week 9-10)
**Objective**: Finalize migration and document the new architecture

#### Tasks:
1. **Remove Legacy Code**
   - Deprecate old orchestration logic
   - Clean up unused dependencies
   - Update imports

2. **Update Documentation**
   - Update README.md
   - Add CrewAI architecture documentation
   - Create developer guide for CrewAI integration

3. **Add Observability**
   - Crew execution metrics
   - Agent performance dashboards
   - Tool usage analytics

4. **Final Testing**
   - End-to-end integration tests
   - Load testing
   - Edge case validation

#### Deliverables:
- ✅ Clean codebase with CrewAI as primary orchestration
- ✅ Complete documentation
- ✅ Full observability
- ✅ All tests passing

## Detailed Implementation

### Directory Structure

```
backend/
├── crewai/
│   ├── __init__.py
│   ├── config.py              # CrewAI configuration
│   ├── agents/
│   │   ├── __init__.py
│   │   ├── base.py            # Base agent class
│   │   ├── data_fetchers.py   # Data fetching agents
│   │   ├── analysts.py        # Analysis agents
│   │   ├── visualizers.py     # Visualization agents
│   │   ├── story_generators.py # Story generation agents
│   │   └── orchestrators.py   # Orchestration agents
│   ├── tools/
│   │   ├── __init__.py
│   │   ├── adapters.py        # MCP to CrewAI adapters
│   │   ├── data_tools.py      # Data fetching tools
│   │   ├── analysis_tools.py  # Analysis tools
│   │   ├── viz_tools.py       # Visualization tools
│   │   └── notebook_tools.py  # Notebook generation tools
│   ├── crews/
│   │   ├── __init__.py
│   │   ├── data_crew.py       # Data fetching crew
│   │   ├── analysis_crew.py    # Analysis crew
│   │   ├── story_crew.py      # Story generation crew
│   │   ├── notebook_crew.py    # Notebook generation crew
│   │   └── master_crew.py     # Master orchestration crew
│   ├── tasks/
│   │   ├── __init__.py
│   │   ├── data_tasks.py      # Data fetching tasks
│   │   ├── analysis_tasks.py  # Analysis tasks
│   │   ├── story_tasks.py     # Story generation tasks
│   │   └── notebook_tasks.py  # Notebook generation tasks
│   └── manager.py            # CrewAI manager
├── mcp/
│   └── server.py             # Updated with CrewAI tools
└── app.py                   # Updated to use CrewAI manager
```

### Key Code Examples

#### 1. Base Agent (`backend/crewai/agents/base.py`)

```python
from crewai import Agent
from typing import Any, Dict, Optional
import logging

logger = logging.getLogger(__name__)

class UNHCRBaseAgent(Agent):
    """Base agent for UNHCR Statistics Copilot with common configuration."""
    
    def __init__(self, **kwargs):
        # Set common UNHCR configuration
        kwargs.setdefault('verbose', True)
        kwargs.setdefault('allow_delegation', True)
        kwargs.setdefault('max_iter', 10)
        kwargs.setdefault('memory', True)
        
        # Add UNHCR-specific context
        kwargs.setdefault('backstory', self._get_unhcr_backstory(kwargs.get('role', '')))
        
        super().__init__(**kwargs)
        
        # Configure logging
        self._configure_logging()
    
    def _get_unhcr_backstory(self, role: str) -> str:
        """Generate UNHCR-specific backstory based on role."""
        base = (
            "You are an AI assistant working for the United Nations High Commissioner for Refugees (UNHCR). "
            "Your responses must adhere to UNHCR standards, methodology, and ethical guidelines. "
            "Always ensure data accuracy and respect for persons of concern."
        )
        
        role_specific = {
            'UNHCR Data Fetcher': "Expert in UNHCR population data structures and API endpoints.",
            'Statistical Analyst': "Expert statistician with deep knowledge of UNHCR methodology and standards.",
            'Analysis Orchestrator': "Senior analyst coordinating comprehensive UNHCR data analysis workflows.",
        }
        
        return f"{base} {role_specific.get(role, '')}"
    
    def _configure_logging(self):
        """Configure agent-specific logging."""
        self.logger = logging.getLogger(f"crewai.{self.role}")
    
    def execute_tool(self, tool_name: str, *args, **kwargs) -> Any:
        """Execute a tool with standardized error handling."""
        try:
            result = self._execute_tool(tool_name, *args, **kwargs)
            logger.info(f"Agent {self.role}: Tool {tool_name} executed successfully")
            return result
        except Exception as e:
            logger.error(f"Agent {self.role}: Tool {tool_name} failed: {e}")
            raise
```

#### 2. Tool Adapter (`backend/crewai/tools/adapters.py`)

```python
from crewai import Tool
from typing import Any, Callable, Optional
import asyncio
import inspect

class MCPToolAdapter:
    """Adapter to convert MCP tools to CrewAI tools."""
    
    @staticmethod
    def adapt_mcp_tool(mcp_tool: Callable, name: str, description: str) -> Tool:
        """
        Convert an MCP tool function to a CrewAI Tool.
        
        Args:
            mcp_tool: The MCP tool function to adapt
            name: Name of the tool
            description: Description of the tool
            
        Returns:
            CrewAI Tool instance
        """
        # Check if tool is async
        is_async = inspect.iscoroutinefunction(mcp_tool)
        
        if is_async:
            async def async_wrapper(*args, **kwargs) -> str:
                result = await mcp_tool(*args, **kwargs)
                return str(result) if result is not None else ""
            
            return Tool(
                name=name,
                description=description,
                function=async_wrapper
            )
        else:
            def sync_wrapper(*args, **kwargs) -> str:
                result = mcp_tool(*args, **kwargs)
                return str(result) if result is not None else ""
            
            return Tool(
                name=name,
                description=description,
                function=sync_wrapper
            )
    
    @staticmethod
    def adapt_all_mcp_tools(tools_module) -> list[Tool]:
        """
        Adapt all tools from an MCP tools module.
        
        Args:
            tools_module: Module containing MCP tool functions
            
        Returns:
            List of CrewAI Tools
        """
        from backend.mcp.server import create_server
        import inspect
        
        server = create_server()
        crewai_tools = []
        
        # Get all registered tools from the server
        for tool_name, tool_info in server._tool_manager.tools.items():
            if hasattr(tools_module, f"{tool_name}_tool"):
                mcp_tool_func = getattr(tools_module, f"{tool_name}_tool")
                crewai_tool = MCPToolAdapter.adapt_mcp_tool(
                    mcp_tool_func,
                    name=tool_name,
                    description=tool_info.description
                )
                crewai_tools.append(crewai_tool)
        
        return crewai_tools
```

#### 3. Specialist Agent Example (`backend/crewai/agents/data_fetchers.py`)

```python
from backend.crewai.agents.base import UNHCRBaseAgent
from backend.mcp.tools.get_population_data import get_population_data_tool
from backend.mcp.tools.get_demographics_data import get_demographics_data_tool
from backend.mcp.tools.get_country_key_figures import get_country_key_figures_tool
from backend.crewai.tools.adapters import MCPToolAdapter

class UNHCRDataFetcher(UNHCRBaseAgent):
    """Specialist agent for fetching UNHCR population data."""
    
    def __init__(self):
        super().__init__(
            role="UNHCR Data Fetcher",
            goal="Retrieve accurate and timely population statistics from UNHCR API",
            backstory=(
                "You are an expert in UNHCR data structures with deep knowledge of "
                "the UNHCR Population API (https://api.unhcr.org/population/v1/). "
                "You understand all population types (refugees, asylum_seekers, idps, stateless, etc.) "
                "and can efficiently retrieve data by country of origin (coo), country of asylum (coa), "
                "and year. Always validate input parameters and handle API errors gracefully."
            ),
            allow_delegation=False
        )
        
        # Initialize API client
        from backend.mcp.common import UNHCRAPIClient
        self.api_client = UNHCRAPIClient()
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all data fetching tools."""
        # Adapt MCP tools to CrewAI format
        self.tools = [
            MCPToolAdapter.adapt_mcp_tool(
                lambda coo, coa, year, coo_all, coa_all: 
                    get_population_data_tool(self.api_client, coo, coa, year, coo_all, coa_all),
                name="get_population_data",
                description=(
                    "Retrieve forcibly displaced population statistics from UNHCR. "
                    "Use when asked about refugee numbers, asylum seekers, stateless persons, "
                    "or other populations of concern by country and year."
                )
            ),
            MCPToolAdapter.adapt_mcp_tool(
                lambda coa, coo, year, population_types: 
                    get_country_key_figures_tool(self.api_client, coa, coo, year, population_types),
                name="get_country_key_figures",
                description=(
                    "Retrieve formatted key statistics and summaries for specific countries. "
                    "Use when asked for country profiles, overview statistics, or formatted summaries."
                )
            ),
            # Add more tools...
        ]
    
    def fetch_population_data(self, question: str, parameters: dict) -> dict:
        """
        High-level method to fetch population data based on a question.
        
        Args:
            question: The user's question
            parameters: Extracted parameters (coo, coa, year, etc.)
            
        Returns:
            Population data with metadata
        """
        # Extract parameters
        coo = parameters.get('coo')
        coa = parameters.get('coa')
        year = parameters.get('year')
        
        # Call the tool
        result = self.execute_tool(
            'get_population_data',
            coo=coo,
            coa=coa,
            year=year
        )
        
        return {
            'data': result,
            'question': question,
            'parameters': parameters,
            'tool': 'get_population_data'
        }
```

#### 4. Crew Definition Example (`backend/crewai/crews/data_crew.py`)

```python
from crewai import Crew, Process
from backend.crewai.agents.data_fetchers import UNHCRDataFetcher
from backend.crewai.agents.analysts import ToolSelector
from backend.crewai.tasks.data_tasks import (
    FetchPopulationDataTask,
    ValidateDataTask,
    EnrichDataTask
)

class DataFetchingCrew:
    """Crew responsible for data fetching and initial processing."""
    
    def __init__(self):
        self.agents = [
            UNHCRDataFetcher(),
            ToolSelector()
        ]
        
        self.crew = Crew(
            agents=self.agents,
            tasks=[
                FetchPopulationDataTask(),
                ValidateDataTask(),
                EnrichDataTask()
            ],
            process=Process.sequential,
            memory=True,
            cache=True
        )
    
    def fetch_data_for_question(self, question: str, audience: str = "internal") -> dict:
        """
        Fetch data for a given question.
        
        Args:
            question: The user's question
            audience: Target audience for the analysis
            
        Returns:
            Data result with metadata
        """
        # Set up task inputs
        inputs = {
            'question': question,
            'audience': audience
        }
        
        # Execute the crew
        result = self.crew.kickoff(inputs=inputs)
        
        return {
            'status': 'success',
            'data': result,
            'crew': 'data_fetching',
            'steps': len(self.crew.tasks)
        }
```

#### 5. CrewAI Manager (`backend/crewai/manager.py`)

```python
from typing import Any, Dict, Optional
from backend.crewai.crews.data_crew import DataFetchingCrew
from backend.crewai.crews.analysis_crew import AnalysisCrew
from backend.crewai.crews.story_crew import StoryCrew
from backend.crewai.crews.notebook_crew import NotebookCrew
from backend.crewai.crews.master_crew import MasterAnalysisCrew
import logging

logger = logging.getLogger(__name__)

class CrewAIManager:
    """
    Manager for all CrewAI operations in UNHCR Statistics Copilot.
    
    Provides a single entry point for crew execution and maintains
    crew instances for reuse.
    """
    
    def __init__(self):
        self.crews = {
            'data': DataFetchingCrew(),
            'analysis': AnalysisCrew(),
            'story': StoryCrew(),
            'notebook': NotebookCrew(),
            'master': MasterAnalysisCrew()
        }
        
        self.metrics = {
            'executions': 0,
            'successes': 0,
            'failures': 0,
            'average_time': 0
        }
    
    def execute_workflow(
        self,
        workflow_type: str,
        question: str,
        audience: str = "internal",
        document_type: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a complete analysis workflow using CrewAI.
        
        Args:
            workflow_type: Type of workflow ('full', 'quick', 'compare', etc.)
            question: The user's question
            audience: Target audience
            document_type: Document type (optional)
            **kwargs: Additional workflow parameters
            
        Returns:
            Complete analysis result
        """
        import time
        start_time = time.time()
        
        self.metrics['executions'] += 1
        
        try:
            # Select the appropriate crew based on workflow type
            if workflow_type == 'full':
                result = self._execute_full_workflow(question, audience, document_type, **kwargs)
            elif workflow_type == 'quick':
                result = self._execute_quick_workflow(question, audience, **kwargs)
            elif workflow_type == 'compare':
                result = self._execute_compare_workflow(question, audience, **kwargs)
            else:
                # Default to master crew for unknown workflow types
                result = self.crews['master'].execute(question, audience, document_type, **kwargs)
            
            self.metrics['successes'] += 1
            duration = time.time() - start_time
            self.metrics['average_time'] = (
                (self.metrics['average_time'] * (self.metrics['successes'] - 1)) + duration
            ) / self.metrics['successes']
            
            # Add observability data
            result['crewai_metrics'] = {
                'execution_time': duration,
                'crew': workflow_type,
                'status': 'success'
            }
            
            return result
            
        except Exception as e:
            self.metrics['failures'] += 1
            logger.error(f"CrewAI workflow {workflow_type} failed: {e}")
            
            return {
                'status': 'error',
                'error': str(e),
                'workflow': workflow_type,
                'crewai_metrics': {
                    'execution_time': time.time() - start_time,
                    'crew': workflow_type,
                    'status': 'failure'
                }
            }
    
    def _execute_full_workflow(
        self,
        question: str,
        audience: str,
        document_type: Optional[str],
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the full analysis workflow."""
        # Use master crew for full workflow
        return self.crews['master'].execute(
            question=question,
            audience=audience,
            document_type=document_type,
            workflow_type='full',
            **kwargs
        )
    
    def _execute_quick_workflow(
        self,
        question: str,
        audience: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the quick analysis workflow."""
        # Fetch data
        data_result = self.crews['data'].fetch_data_for_question(question, audience)
        
        # Generate story (without notebook)
        story_result = self.crews['story'].generate_story(
            data=data_result['data'],
            question=question,
            audience=audience,
            include_notebook=False
        )
        
        return story_result
    
    def _execute_compare_workflow(
        self,
        question: str,
        audience: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the comparative analysis workflow."""
        # This would use the master crew with compare configuration
        return self.crews['master'].execute(
            question=question,
            audience=audience,
            workflow_type='compare',
            **kwargs
        )
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get CrewAI execution metrics."""
        return self.metrics
    
    def reset_metrics(self):
        """Reset CrewAI execution metrics."""
        self.metrics = {
            'executions': 0,
            'successes': 0,
            'failures': 0,
            'average_time': 0
        }
```

#### 6. Updated MCP Server with CrewAI (`backend/mcp/server.py` - additions)

```python
# Add CrewAI imports
from backend.crewai.manager import CrewAIManager

# Initialize CrewAI manager
crewai_manager = CrewAIManager()

# Add CrewAI-based tools to the server
@server.tool(
    name="crewai_full_analysis",
    description=(
        "Complete end-to-end analysis using CrewAI agents. "
        "This tool uses CrewAI to orchestrate the full analysis workflow: "
        "question → data → analysis → story → notebook."
    ),
)
async def crewai_full_analysis_wrapper(
    question: str,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    **kwargs
) -> dict[str, Any]:
    """CrewAI-based full analysis workflow."""
    return crewai_manager.execute_workflow(
        workflow_type='full',
        question=question,
        audience=audience or "internal",
        document_type=document_type,
        **kwargs
    )

@server.tool(
    name="crewai_quick_analysis",
    description=(
        "Quick analysis using CrewAI agents without notebook generation. "
        "Use this for lightweight, fast analysis requests."
    ),
)
async def crewai_quick_analysis_wrapper(
    question: str,
    audience: Optional[str] = None,
    **kwargs
) -> dict[str, Any]:
    """CrewAI-based quick analysis workflow."""
    return crewai_manager.execute_workflow(
        workflow_type='quick',
        question=question,
        audience=audience or "internal",
        **kwargs
    )
```

#### 7. Updated Backend App (`backend/app.py` - key changes)

```python
# Add CrewAI imports
from backend.crewai.manager import CrewAIManager

# Initialize CrewAI manager
crewai_manager = CrewAIManager()

# Update chat endpoint to use CrewAI
@app.post("/chat")
async def chat(
    request: Request,
    user: UserInfo = Depends(get_optional_user)
) -> Response:
    """Process chat message using CrewAI."""
    data = await request.json()
    
    question = data.get("message", "")
    audience = data.get("audience", "internal")
    document_type = data.get("document_type")
    
    # Use CrewAI for processing
    result = crewai_manager.execute_workflow(
        workflow_type='full',
        question=question,
        audience=audience,
        document_type=document_type
    )
    
    # Format response
    return JSONResponse(content=result)

# Add CrewAI metrics endpoint
@app.get("/crewai/metrics")
async def get_crewai_metrics():
    """Get CrewAI execution metrics."""
    return crewai_manager.get_metrics()

@app.post("/crewai/reset")
async def reset_crewai_metrics():
    """Reset CrewAI execution metrics."""
    crewai_manager.reset_metrics()
    return {"status": "reset"}
```

## Audience Configuration Integration

### Current System
The ANALYSIS_CONFIG dictionary in `backend/chat.py` defines:
- 5 audience types
- 3 document types per audience
- Tone, length, structure for each combination

### New CrewAI Integration

```python
# In backend/crewai/config.py

ANALYSIS_CONFIG = {
    # ... (existing config from chat.py)
}

class AudienceConfigManager:
    """Manages audience-specific configuration for CrewAI agents."""
    
    @staticmethod
    def get_config(audience: str, document_type: Optional[str] = None) -> dict:
        """Get configuration for a specific audience and document type."""
        from backend.chat import ANALYSIS_CONFIG, get_analysis_config
        return get_analysis_config(audience, document_type or "")
    
    @staticmethod
    def get_available_types(audience: str) -> list:
        """Get available document types for an audience."""
        from backend.chat import get_available_document_types
        return get_available_document_types(audience)
    
    @staticmethod
    def get_default_type(audience: str) -> str:
        """Get default document type for an audience."""
        from backend.chat import get_default_document_type
        return get_default_document_type(audience)

# Update agents to use audience config
class StoryGenerator(UNHCRBaseAgent):
    def __init__(self):
        super().__init__(
            role="Story Generator",
            goal="Generate compelling data stories from UNHCR analysis",
            backstory=(
                "You are an expert storyteller who can transform data and analysis "
                "into compelling narratives. You understand different audience types "
                "and adapt your writing style accordingly."
            )
        )
        self.config_manager = AudienceConfigManager()
    
    def generate_story(self, data: dict, question: str, audience: str, document_type: str) -> dict:
        # Get audience-specific configuration
        config = self.config_manager.get_config(audience, document_type)
        
        # Use configuration in story generation
        tone = config.get('tone', 'formal')
        structure = config.get('structure', [])
        
        # Generate story based on configuration
        story = self._generate_with_config(data, question, tone, structure)
        
        return {
            'story': story,
            'config': config,
            'audience': audience,
            'document_type': document_type
        }
```

## Quarto Notebook Generation Preservation

### Current Flow
1. Story content is generated
2. Jinja2 template is selected based on document_type
3. Template is rendered with story data
4. Quarto markdown is generated
5. Metadata and observability data are added

### New CrewAI Flow

```python
class NotebookGenerator(UNHCRBaseAgent):
    """Agent responsible for generating Quarto notebooks."""
    
    def __init__(self):
        super().__init__(
            role="Quarto Notebook Generator",
            goal="Create well-documented Quarto notebooks from analysis results",
            backstory=(
                "You are an expert in Quarto format and UNHCR documentation standards. "
                "You can generate reproducible notebooks with proper structure, "
                "metadata, and observability data."
            )
        )
        
        # Load Jinja2 environment
        from jinja2 import Environment, FileSystemLoader
        import os
        
        template_dir = os.path.join(os.path.dirname(__file__), '../templates')
        self.env = Environment(loader=FileSystemLoader(template_dir))
    
    def generate_notebook(
        self,
        story_content: str,
        data: dict,
        question: str,
        audience: str,
        document_type: str,
        metadata: Optional[dict] = None,
        **kwargs
    ) -> dict:
        """
        Generate a Quarto notebook from analysis results.
        
        Args:
            story_content: The generated story/narrative
            data: The analysis data
            question: Original user question
            audience: Target audience
            document_type: Document type
            metadata: Additional metadata
            **kwargs: Additional parameters
            
        Returns:
            Complete notebook content with metadata
        """
        # Select template
        template_name = self._select_template(document_type)
        template = self.env.get_template(template_name)
        
        # Prepare context
        context = self._prepare_context(
            story_content, data, question, audience, document_type, metadata, **kwargs
        )
        
        # Render template
        notebook_content = template.render(**context)
        
        # Add observability data
        observability = self._generate_observability_data(
            story_content, data, question, audience, document_type
        )
        
        return {
            'notebook': notebook_content,
            'metadata': {
                'audience': audience,
                'document_type': document_type,
                'question': question,
                'template': template_name,
                **observability
            }
        }
    
    def _select_template(self, document_type: str) -> str:
        """Select the appropriate Jinja2 template."""
        # Map document types to template files
        template_map = {
            'technical_report': 'technical_report.j2',
            'executive_summary': 'executive_summary.j2',
            'long_read': 'long_read.j2',
            'social_media': 'social_media.j2',
            'linkedin_post': 'linkedin_post.j2'
        }
        return template_map.get(document_type, 'base_quarto.j2')
    
    def _prepare_context(self, **kwargs) -> dict:
        """Prepare context for template rendering."""
        # Convert all data to template-friendly format
        context = {}
        
        for key, value in kwargs.items():
            if isinstance(value, dict):
                context[key] = self._convert_dict(value)
            elif isinstance(value, list):
                context[key] = self._convert_list(value)
            else:
                context[key] = value
        
        # Add default context
        context.update({
            'generated_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'source': 'UNHCR Statistics Copilot'
        })
        
        return context
    
    def _generate_observability_data(self, **kwargs) -> dict:
        """Generate observability data for the notebook."""
        return {
            'analysis_log': self._generate_analysis_log(**kwargs),
            'tool_execution': self._get_tool_execution_log(),
            'performance_metrics': self._get_performance_metrics()
        }
    
    def _generate_analysis_log(self, **kwargs) -> str:
        """Generate a detailed analysis log."""
        # Create a structured log of the analysis process
        log_entries = []
        
        # Add question and parameters
        log_entries.append(f"## Analysis Log\n\n")
        log_entries.append(f"**Question:** {kwargs.get('question', 'N/A')}\n\n")
        log_entries.append(f"**Audience:** {kwargs.get('audience', 'N/A')}\n\n")
        log_entries.append(f"**Document Type:** {kwargs.get('document_type', 'N/A')}\n\n")
        
        # Add data summary
        data = kwargs.get('data', {})
        if data:
            log_entries.append(f"### Data Summary\n\n")
            log_entries.append(f"**Data Type:** {data.get('data_type', 'unknown')}\n\n")
            log_entries.append(f"**Items:** {len(data.get('items', []))}\n\n")
        
        # Add story summary
        story = kwargs.get('story_content', '')
        if story:
            log_entries.append(f"### Story Summary\n\n")
            log_entries.append(f"**Length:** {len(story)} characters\n\n")
            log_entries.append(f"**Sections:** {self._count_sections(story)}\n\n")
        
        return '\n'.join(log_entries)
```

## Migration Strategy

### 1. Dual-Run Mode
During migration, run both systems in parallel:

```python
class DualRunManager:
    """Manages dual execution of legacy and CrewAI systems for comparison."""
    
    def __init__(self):
        self.legacy_enabled = True
        self.crewai_enabled = True
        self.comparison_mode = True
    
    async def process_question(self, question: str, audience: str, **kwargs) -> dict:
        """Process a question using both systems."""
        results = {}
        
        # Legacy system
        if self.legacy_enabled:
            results['legacy'] = await self._run_legacy(question, audience, **kwargs)
        
        # CrewAI system
        if self.crewai_enabled:
            results['crewai'] = await self._run_crewai(question, audience, **kwargs)
        
        # Compare if both ran
        if self.comparison_mode and 'legacy' in results and 'crewai' in results:
            results['comparison'] = self._compare_results(results['legacy'], results['crewai'])
        
        # Return primary result (CrewAI if available, otherwise legacy)
        return results.get('crewai', results.get('legacy', {}))
    
    def _compare_results(self, legacy: dict, crewai: dict) -> dict:
        """Compare results from both systems."""
        comparison = {
            'fields_match': {},
            'fields_differ': {},
            'missing_in_legacy': [],
            'missing_in_crewai': []
        }
        
        # Compare top-level fields
        legacy_keys = set(legacy.keys())
        crewai_keys = set(crewai.keys())
        
        comparison['missing_in_legacy'] = list(crewai_keys - legacy_keys)
        comparison['missing_in_crewai'] = list(legacy_keys - crewai_keys)
        
        # Compare common fields
        common_keys = legacy_keys & crewai_keys
        for key in common_keys:
            if legacy[key] == crewai[key]:
                comparison['fields_match'][key] = True
            else:
                comparison['fields_differ'][key] = {
                    'legacy': legacy[key],
                    'crewai': crewai[key]
                }
        
        return comparison
```

### 2. Traffic Routing

```python
import random

class TrafficRouter:
    """Routes traffic between legacy and CrewAI systems."""
    
    def __init__(self, crewai_percentage: float = 0.0):
        self.crewai_percentage = crewai_percentage
    
    def should_use_crewai(self, request_id: str = None) -> bool:
        """Determine if this request should use CrewAI."""
        if request_id is None:
            request_id = str(random.randint(0, 999999))
        
        # Use consistent hashing for the same request
        hash_val = hash(request_id) % 100
        return hash_val < (self.crewai_percentage * 100)
    
    def set_crewai_percentage(self, percentage: float):
        """Set the percentage of traffic to route to CrewAI."""
        self.crewai_percentage = max(0.0, min(1.0, percentage))
    
    def get_crewai_percentage(self) -> float:
        """Get the current CrewAI traffic percentage."""
        return self.crewai_percentage
```

### 3. Rollback Mechanism

```python
class RollbackManager:
    """Manages rollback from CrewAI to legacy system."""
    
    def __init__(self):
        self.error_threshold = 0.1  # 10% error rate
        self latency_threshold = 2.0  # 2x latency
        self.error_count = 0
        self.total_count = 0
        self.rolled_back = False
    
    def record_execution(self, success: bool, latency: float, crewai_latency: float):
        """Record an execution result."""
        self.total_count += 1
        if not success:
            self.error_count += 1
        
        # Check thresholds
        error_rate = self.error_count / self.total_count if self.total_count > 0 else 0
        latency_ratio = crewai_latency / latency if latency > 0 else 1
        
        if error_rate > self.error_threshold or latency_ratio > self.latency_threshold:
            self.rollback()
    
    def rollback(self):
        """Initiate rollback to legacy system."""
        self.rolled_back = True
        logger.warning(
            f"Rolling back to legacy system. "
            f"Error rate: {self.error_count / self.total_count if self.total_count > 0 else 0}"
        )
    
    def recover(self):
        """Recover CrewAI system after fixing issues."""
        self.rolled_back = False
        self.error_count = 0
        self.total_count = 0
        logger.info("CrewAI system recovered and ready for traffic")
    
    def is_rolled_back(self) -> bool:
        """Check if system is in rollback mode."""
        return self.rolled_back
```

## Testing Strategy

### 1. Unit Tests

```python
# test/crewai/test_agents.py

import pytest
from backend.crewai.agents.data_fetchers import UNHCRDataFetcher
from backend.crewai.tools.adapters import MCPToolAdapter

class TestUNHCRDataFetcher:
    """Tests for UNHCR Data Fetcher agent."""
    
    @pytest.fixture
    def data_fetcher(self):
        return UNHCRDataFetcher()
    
    def test_agent_initialization(self, data_fetcher):
        """Test that agent initializes correctly."""
        assert data_fetcher.role == "UNHCR Data Fetcher"
        assert len(data_fetcher.tools) > 0
        assert hasattr(data_fetcher, 'api_client')
    
    def test_fetch_population_data(self, data_fetcher):
        """Test population data fetching."""
        result = data_fetcher.fetch_population_data(
            question="Show refugee trends in France",
            parameters={'coo': 'FRA', 'year': '2023'}
        )
        
        assert 'data' in result
        assert 'question' in result
        assert 'tool' in result
        assert result['tool'] == 'get_population_data'

class TestMCPToolAdapter:
    """Tests for MCP to CrewAI tool adapter."""
    
    def test_adapt_sync_tool(self):
        """Test adapting a synchronous MCP tool."""
        def sync_tool(param1: str) -> dict:
            return {'result': param1}
        
        tool = MCPToolAdapter.adapt_mcp_tool(
            sync_tool,
            name='test_sync_tool',
            description='Test sync tool'
        )
        
        assert tool.name == 'test_sync_tool'
        assert tool.description == 'Test sync tool'
        assert callable(tool.function)
    
    @pytest.mark.asyncio
    async def test_adapt_async_tool(self):
        """Test adapting an asynchronous MCP tool."""
        async def async_tool(param1: str) -> dict:
            return {'result': param1}
        
        tool = MCPToolAdapter.adapt_mcp_tool(
            async_tool,
            name='test_async_tool',
            description='Test async tool'
        )
        
        assert tool.name == 'test_async_tool'
        assert tool.description == 'Test async tool'
        assert callable(tool.function)
```

### 2. Integration Tests

```python
# test/crewai/test_crews.py

import pytest
from backend.crewai.crews.data_crew import DataFetchingCrew

class TestDataFetchingCrew:
    """Tests for Data Fetching Crew."""
    
    @pytest.fixture
    def data_crew(self):
        return DataFetchingCrew()
    
    def test_crew_initialization(self, data_crew):
        """Test that crew initializes correctly."""
        assert len(data_crew.agents) > 0
        assert len(data_crew.crew.tasks) > 0
    
    def test_fetch_data_for_question(self, data_crew):
        """Test data fetching for a question."""
        result = data_crew.fetch_data_for_question(
            question="Show refugee data for France 2023",
            audience="internal"
        )
        
        assert 'status' in result
        assert 'data' in result
        assert result['status'] == 'success'
```

### 3. End-to-End Tests

```python
# test/crewai/test_end_to_end.py

import pytest
from backend.crewai.manager import CrewAIManager

class TestCrewAIEndToEnd:
    """End-to-end tests for CrewAI integration."""
    
    @pytest.fixture
    def crewai_manager(self):
        return CrewAIManager()
    
    def test_full_workflow(self, crewai_manager):
        """Test complete analysis workflow."""
        result = crewai_manager.execute_workflow(
            workflow_type='full',
            question="Show refugee trends in France from 2020 to 2023",
            audience='internal',
            document_type='technical_report'
        )
        
        assert 'status' in result
        assert result['status'] == 'success'
        assert 'notebook' in result or 'story' in result
        assert 'crewai_metrics' in result
    
    def test_quick_workflow(self, crewai_manager):
        """Test quick analysis workflow."""
        result = crewai_manager.execute_workflow(
            workflow_type='quick',
            question="What are the latest refugee numbers for Germany?",
            audience='public_donors'
        )
        
        assert 'status' in result
        assert result['status'] == 'success'
        assert 'story' in result
    
    def test_metrics_tracking(self, crewai_manager):
        """Test that metrics are tracked correctly."""
        initial_metrics = crewai_manager.get_metrics()
        
        # Execute a workflow
        crewai_manager.execute_workflow(
            workflow_type='quick',
            question="Test question",
            audience='internal'
        )
        
        updated_metrics = crewai_manager.get_metrics()
        
        assert updated_metrics['executions'] == initial_metrics['executions'] + 1
        assert updated_metrics['successes'] >= initial_metrics['successes']
```

### 4. Comparison Tests

```python
# test/crewai/test_comparison.py

import pytest
from backend.crewai.manager import CrewAIManager
from backend.chat import process_chat_message
from backend.crewai.comparison import ResultComparator

class TestComparison:
    """Tests comparing CrewAI and legacy system results."""
    
    @pytest.fixture
    def comparator(self):
        return ResultComparator()
    
    @pytest.mark.asyncio
    async def test_notebook_structure_comparison(self, comparator):
        """Test that notebook structures are equivalent."""
        question = "Show refugee trends in France"
        audience = "internal"
        
        # Get legacy result
        legacy_result = await process_chat_message(
            message=question,
            audience=audience
        )
        
        # Get CrewAI result
        crewai_manager = CrewAIManager()
        crewai_result = crewai_manager.execute_workflow(
            workflow_type='full',
            question=question,
            audience=audience
        )
        
        # Compare
        comparison = comparator.compare(
            legacy_result.get('notebook', ''),
            crewai_result.get('notebook', '')
        )
        
        # Should have similar structure
        assert comparison['structure_match'] > 0.8  # 80% similarity
    
    @pytest.mark.asyncio
    async def test_data_accuracy_comparison(self, comparator):
        """Test that data accuracy is maintained."""
        question = "What are the refugee numbers for Syria in 2023?"
        audience = "internal"
        
        # Get both results
        legacy_result = await process_chat_message(
            message=question,
            audience=audience
        )
        
        crewai_manager = CrewAIManager()
        crewai_result = crewai_manager.execute_workflow(
            workflow_type='full',
            question=question,
            audience=audience
        )
        
        # Compare data
        data_comparison = comparator.compare_data(
            legacy_result.get('data', {}),
            crewai_result.get('data', {})
        )
        
        # Should have same or better data accuracy
        assert data_comparison['accuracy_match'] >= 0.95  # 95% accuracy
```

## Deployment Plan

### 1. Staging Deployment
1. Deploy CrewAI infrastructure to staging environment
2. Run comparison tests against production data
3. Validate all workflows work correctly
4. Test rollback mechanisms

### 2. Canary Deployment
1. Deploy to 5% of production traffic
2. Monitor error rates and performance
3. Compare results with legacy system
4. Gradually increase to 25%

### 3. Full Deployment
1. Deploy to 50% of production traffic
2. Monitor for 24-48 hours
3. Address any issues
4. Deploy to 100%

### 4. Cleanup
1. Remove dual-run mode after 1 week of stable operation
2. Archive legacy orchestration code
3. Update all documentation
4. Celebrate! 🎉

## Monitoring and Observability

### Key Metrics to Track

1. **Performance Metrics**
   - Crew execution time (average, p95, p99)
   - Tool execution time per type
   - End-to-end workflow latency

2. **Quality Metrics**
   - Notebook generation success rate
   - Data accuracy (compared to legacy)
   - Story quality scores
   - Template rendering success

3. **Error Metrics**
   - Crew execution failures
   - Tool execution failures
   - Fallback rates
   - Rollback events

4. **Usage Metrics**
   - Most used agents
   - Most used tools
   - Most used workflows
   - Audience distribution
   - Document type distribution

### Dashboard Components

```python
# Example Prometheus metrics for CrewAI

from prometheus_client import Counter, Histogram, Gauge

# Crew execution metrics
CREWAI_EXECUTIONS = Counter(
    'crewai_executions_total',
    'Total CrewAI executions',
    ['crew', 'workflow_type', 'status']
)

CREWAI_EXECUTION_TIME = Histogram(
    'crewai_execution_time_seconds',
    'CrewAI execution time in seconds',
    ['crew', 'workflow_type']
)

CREWAI_TOOL_EXECUTIONS = Counter(
    'crewai_tool_executions_total',
    'Total CrewAI tool executions',
    ['tool', 'agent', 'status']
)

CREWAI_TOOL_TIME = Histogram(
    'crewai_tool_execution_time_seconds',
    'CrewAI tool execution time in seconds',
    ['tool', 'agent']
)

# Agent metrics
CREWAI_AGENT_MESSAGES = Counter(
    'crewai_agent_messages_total',
    'Total messages processed by agents',
    ['agent', 'type']
)

# Error metrics
CREWAI_ERRORS = Counter(
    'crewai_errors_total',
    'Total CrewAI errors',
    ['crew', 'agent', 'tool', 'error_type']
)

# Traffic metrics
CREWAI_TRAFFIC_PERCENTAGE = Gauge(
    'crewai_traffic_percentage',
    'Percentage of traffic routed to CrewAI'
)
```

## Risk Assessment

### Potential Risks and Mitigations

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Performance degradation | Medium | High | Load testing, optimization, rollback mechanism |
| Data accuracy issues | Low | High | Comparison testing, validation checks |
| Template rendering issues | Low | Medium | Template testing, fallback to base template |
| Agent hallucinations | Medium | Medium | Guardrails, validation, human review for critical outputs |
| Tool compatibility issues | Medium | Medium | Comprehensive adapter testing, fallback to legacy tools |
| Memory leaks | Low | Medium | Monitoring, limits, regular restarts |
| Cost overruns | Medium | Medium | Usage limits, cost monitoring, budget alerts |

### Contingency Plans

1. **Performance Issues**
   - Implement caching for frequent queries
   - Optimize crew configurations
   - Add more resources if needed
   - Rollback to legacy if performance degrades significantly

2. **Data Accuracy Issues**
   - Implement validation checks
   - Add human review for critical outputs
   - Maintain dual-run mode for comparison
   - Rollback to legacy if accuracy drops

3. **System Failures**
   - Implement circuit breakers
   - Add comprehensive error handling
   - Maintain fallback mechanisms
   - Quick rollback capability

## Success Measurement

### Quantitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| CrewAI adoption | 100% | Traffic percentage |
| Response time | < 2s p95 | Prometheus metrics |
| Success rate | > 99% | Error tracking |
| Data accuracy | > 99% | Comparison testing |
| Notebook quality | > 4.5/5 | User feedback |
| Cost | < 1.5x current | Cost monitoring |

### Qualitative Metrics

| Metric | Target | Measurement Method |
|--------|--------|-------------------|
| Developer satisfaction | High | Surveys, feedback |
| Maintainability | Improved | Code reviews, complexity metrics |
| Extensibility | Improved | Time to add new features |
| User satisfaction | High | User feedback, NPS |

## Timeline

| Phase | Duration | Key Activities | Success Criteria |
|-------|----------|----------------|------------------|
| Foundation | 2 weeks | Setup CrewAI, implement agents, adapt tools | All MCP tools available as CrewAI tools |
| Orchestration | 2 weeks | Build crews, implement workflows, integrate config | End-to-end workflows working via crews |
| Integration | 2 weeks | Integrate with backend, add endpoints, migration utilities | CrewAI integrated with existing system |
| Migration | 2 weeks | A/B testing, gradual rollout, bug fixes | CrewAI handling 100% of production traffic |
| Cleanup | 2 weeks | Remove legacy, update docs, final testing | Clean codebase, complete documentation |

**Total Estimated Duration: 10 weeks**

## Team Responsibilities

### Core Team
- **Project Lead**: Overall coordination, decision making
- **Backend Developers**: CrewAI implementation, integration
- **QA Engineers**: Testing, validation
- **DevOps Engineers**: Deployment, monitoring

### Extended Team
- **UNHCR Domain Experts**: Validation of analysis results
- **Product Manager**: Requirements, priorities
- **Technical Writers**: Documentation

## Budget Estimate

| Category | Estimated Cost |
|----------|----------------|
| Development Time | 10 weeks × 5 developers × $100/hr = $200,000 |
| CrewAI Licensing | $5,000 (if using enterprise features) |
| Cloud Resources | $2,000 (additional for testing) |
| Contingency (20%) | $41,400 |
| **Total** | **$248,400** |

*Note: Costs are estimates and may vary based on team size, rates, and actual requirements.*

## Conclusion

This migration plan outlines a comprehensive approach to replacing the current client-side tool orchestration with a CrewAI-based agent system. The migration:

1. **Preserves all existing functionality** including Quarto notebook generation with well-documented analysis logs
2. **Improves maintainability** through declarative crew definitions
3. **Enhances extensibility** making it easier to add new tools and workflows
4. **Provides better observability** with crew-level metrics and logging
5. **Enables advanced orchestration** with agent collaboration and delegation

The phased approach ensures minimal risk and allows for gradual adoption, with rollback capabilities at each stage.

**Next Steps:**
1. Review and approve this migration plan
2. Set up CrewAI infrastructure
3. Begin Phase 1: Foundation implementation

---

*Generated by Mistral Vibe*
*Co-Authored-By: Mistral Vibe <vibe@mistral.ai>*
