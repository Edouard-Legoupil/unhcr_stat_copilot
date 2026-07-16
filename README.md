# UNHCR Statistics Copilot: LLM+ MCP + Stat API + Quarto

**AI-Powered Data Analysis Platform for UNHCR Population Statistics**

For non technical person, you may review the [Terms of Reference and Standard Operating Procedure for UNHCR Statistics Copilot Virtual Assistant](terms_of_reference_and_sop_unhcr.md).

The below documentation is for technical person. This app app offer a single Azure App Service deployment hosting FastAPI, MCP server, React UI, Azure OpenAI integration hooks, Charts and Quarto export with audience-specific document type configuration.

## Quick Start

```bash
# Fill env variables in .env file within backend/ folder

# Start the development server
./start.sh

# Access the application at http://localhost:5173/
```

## Architecture Overview

```mermaid
graph TD
    A[React Frontend] --> B[FastAPI Backend]
    B --> C[MCP Server]
    C --> D[UNHCR Data Tools]
    C --> E[Analysis Tools]
    C --> F[Visualization Tools]
    D --> G[UNHCR Population API]
    E --> H[Azure OpenAI]
    F --> I[Matplotlib Charts]
    B --> J[Quarto Export]
    B --> K[Audience Config API]
    C --> L[Jinja Templates]
```

## Agentic Orchestration

```mermaid


flowchart TD

%% ==========================================
%% STYLES
%% ==========================================

classDef task fill:#DCFCE7,stroke:#16A34A,stroke-width:2px;
classDef tool fill:#FED7AA,stroke:#EA580C,stroke-width:2px;
classDef io fill:#E5E7EB,stroke:#6B7280,stroke-width:2px;
classDef shared fill:#C7D2FE,stroke:#4338CA,stroke-width:2px,color:#111827;

%% ==========================================
%% SHARED ARTIFACTS (CONNECTING ELEMENTS)
%% These are outputs of one task and inputs to another
%% ==========================================

artifact_population_data(["population_data"])
artifact_rsd_data(["rsd_data"])
artifact_solutions_data(["solutions_data"])
artifact_statistics(["statistics"])
artifact_guardrails(["guardrails_validation"])
artifact_visualization_structure(["visualization_structure"])
artifact_visualization_description(["visualization_description"])
artifact_story(["story"])
artifact_enriched_story(["enriched_story"])
artifact_adapted_story(["adapted_story"])
artifact_notebook(["quarto_notebook"])

class artifact_population_data,artifact_rsd_data,artifact_solutions_data,artifact_statistics,artifact_guardrails,artifact_visualization_structure,artifact_visualization_description,artifact_story,artifact_enriched_story,artifact_adapted_story,artifact_notebook shared

%% ==========================================
%% data_manager AGENT
%% ==========================================

subgraph unhcr_data_fetcher["data_manager"]
    task_fetch_population["fetch_population_data"]
    tool_get_population{{get_population_data}}
    task_fetch_population --> tool_get_population
    tool_get_population --> artifact_population_data

    task_fetch_rsd["fetch_rsd_data"]
    tool_get_rsd{{get_rsd_applications<br/>get_rsd_decisions}}
    task_fetch_rsd --> tool_get_rsd
    tool_get_rsd --> artifact_rsd_data

    task_fetch_solutions["fetch_solutions_data"]
    tool_get_solutions{{get_solutions}}
    task_fetch_solutions --> tool_get_solutions
    tool_get_solutions --> artifact_solutions_data
end

input_question --> task_safe_tool
task_safe_tool --> task_fetch_rsd
task_safe_tool --> task_fetch_population
task_safe_tool --> task_fetch_solutions
artifact_population_data --> input_data
artifact_rsd_data --> input_data
artifact_solutions_data --> input_data

%% ==========================================
%% statistical_analyst AGENT
%% ==========================================

subgraph statistical_analyzer["statistical_analyst"]
    task_analyze_statistics["analyze_statistics"]
    tool_analyze_statistics{{analyze_data_statistics}}
    task_analyze_statistics --> tool_analyze_statistics
    tool_analyze_statistics --> artifact_statistics
    task_validate_guardrails["validate_guardrails"]
    tool_apply_guardrails{{apply_analysis_guardrails}}
    task_validate_guardrails --> tool_apply_guardrails
    tool_apply_guardrails --> artifact_guardrails
end

input_data --> task_analyze_statistics
input_question --> task_analyze_statistics
input_story_structure --> task_analyze_statistics


task_analyze_statistics -. compute .-> artifact_statistics
task_validate_guardrails -. assess .-> artifact_guardrails

%% ==========================================
%% visualization_expert AGENTS
%% ==========================================

subgraph visualization_expert["visualization_expert"]
    task_extract_visualization["extract_visualization"]
    tool_extract_visualization{{extract_visualization_structure}}
    task_extract_visualization --> tool_extract_visualization
    tool_extract_visualization --> artifact_visualization_structure

    task_generate_visualization["generate_visualization"]
    tool_generate_visualization{{generate_visualization}}
    task_generate_visualization --> tool_generate_visualization
    tool_generate_visualization --> artifact_visualization_description
end


input_data --> task_extract_visualization
artifact_statistics --> task_extract_visualization
artifact_guardrails --> task_extract_visualization
input_story_structure --> task_extract_visualization

artifact_visualization_structure --> task_generate_visualization
input_data --> task_generate_visualization

artifact_statistics --> task_validate_guardrails
input_story_structure --> task_validate_guardrails

%% ==========================================
%% Story teller AGENTS
%% ==========================================

subgraph story_generator["story_teller"]
    task_generate_story["generate_story"]
    tool_generate_story{{generate_analytical_story}}
    task_generate_story --> tool_generate_story
    tool_generate_story --> artifact_story
    task_enrich_story["enrich_story_with_rag"]
    tool_get_data_for_story{{get_data_for_story}}
    task_enrich_story --> tool_get_data_for_story
    tool_get_data_for_story --> artifact_enriched_story
    task_adapt_story["adapt_story_for_audience"]
    task_adapt_story --> artifact_adapted_story
end


input_data --> task_generate_story
input_story_structure --> task_generate_story
artifact_statistics --> task_generate_story
artifact_guardrails --> task_generate_story
input_question --> task_generate_story

artifact_story --> task_enrich_story
artifact_enriched_story --> task_adapt_story


task_generate_story -. draft .-> artifact_story
task_enrich_story -. augment .-> artifact_enriched_story
task_adapt_story -. adjust .-> artifact_adapted_story

%% ==========================================
%% NOTEBOOK AGENT
%% ==========================================

subgraph notebook_generator["notebook_encoder"]
    task_create_notebook["create_notebook"]
    tool_create_quarto{{create_quarto_notebook}}
    task_create_notebook --> tool_create_quarto
    tool_create_quarto --> artifact_notebook
end

input_data --> task_create_notebook
input_story_structure --> task_create_notebook
artifact_adapted_story --> task_create_notebook
artifact_visualization_description --> task_create_notebook
task_create_notebook -. weave .-> artifact_notebook

%% ==========================================
%% TASK INPUTS (ALL OUTSIDE SUBGRAPHS)
%% ==========================================

input_question(["question"])
input_data(["data"])
input_story_structure(["story_structure_audience_tone_lenght"])

class input_question,input_story_structure,input_data io

```


## Typical Analysis Request Flow

```mermaid
sequenceDiagram
    User->>Frontend: Submits question + audience + document type
    Frontend->>Backend: POST /chat with request data
    Backend->>MCP Server: Processes request
    MCP Server->>UNHCR API: Fetches population data
    MCP Server->>Analysis Tools: Generates insights
    MCP Server->>Jinja Templates: Renders document
    Backend->>Frontend: Returns quarto content + metadata
    Frontend->>User: Displays IntegratedAnalysisViewer
    User->>Frontend: Clicks debug triangle (▶)
    Frontend->>User: Expands debug panel (▼)
```

## Core Features

### 1. **Audience-Specific Document Type Configuration**

The system supports different audience types with specific document type mappings:

For up-to-date audience-specific document type mappings and defaults, use the `/analysis-config` API endpoint:

```bash
# GET /analysis-config
# GET /analysis-config/{audience}
```

Each document type has specific configuration including:
- **Tone and Style**: Formal, engaging, strategic, etc.
- **Length Specifications**: Word range, reading time, content density
- **Recommended Structure**: Section breakdown for the document

### 2. **Jinja Template System**

Document-specific Jinja templates for consistent formatting:

- **Base Template**: `base_quarto.j2` - Common structure and metadata
- **Technical Report**: `technical_report.j2` - Formal, structured reports
- **Executive Summary**: `executive_summary.j2` - Concise, action-oriented
- **Long Read**: `long_read.j2` - Comprehensive analytical reports
- **Social Media**: `social_media.j2` - Short, engaging posts
- **LinkedIn Post**: `linkedin_post.j2` - Professional content

### 3. **Data Analysis Workflow**

- **Natural Language Queries**: Ask questions like "Show refugee trends in France"
- **Automatic Tool Selection**: AI chooses the right data tools
- **Multi-Stage Analysis**: Data fetching → Statistical analysis → Visualization → Narrative generation
- **Methodology Guardrails**: Ensures UNHCR compliance
- **Audience-Specific Output**: Results tailored to selected audience type

### 4. **Available MCP Tools**

#### Data Fetching Tools
- `get_country_key_figures(coa, year, population_types)` - Key statistics for a country
- `get_population_trends(coa, years, population_types)` - Time series data
- `get_demographic_breakdown(coa, year)` - Age/gender distribution

#### Analysis Tools  
- `analyze_data_statistics(data)` - Statistical analysis
- `extract_visualization_structure(data)` - Chart recommendations
- `generate_ai_data_story(visualization_data)` - Narrative generation

#### Export Tools
- `create_quarto_notebook(story_content)` - Reproducible reports with Jinja templates
- `generate_visualization(chart_data)` - Accessible descriptions



## 🔧 API Endpoints

### Core Endpoints

| Endpoint | Method | Description | Response Format |
|----------|--------|-------------|----------------|
| `/chat` | POST | Process natural language queries | Analysis result with metadata |
| `/tool` | POST | Execute specific tools | Tool execution result |
| `/story` | POST | Generate data stories | Narrative story content |
| `/chart` | POST | Generate visualizations | Chart data and metadata |
| `/analysis-config` | GET | Get complete configuration | Full ANALYSIS_CONFIG |
| `/analysis-config/{audience}` | GET | Get audience-specific config | Audience-specific config |
| `/health` | GET | Health check | `{"status": "ok"}` |

### Configuration Endpoints

| Endpoint | Method | Description | Example Response |
|----------|--------|-------------|----------------|
| `/analysis-config` | GET | Get complete configuration | `{"config": {...all audiences and types...}}` |
| `/analysis-config/{audience}` | GET | Get audience-specific config | `{"available_document_types": [...], "default_document_type": "..."}` |




## Error Handling

The system includes comprehensive error handling:

- **Input Validation**: All endpoints validate required parameters
- **Tool Error Handling**: Graceful degradation when tools fail
- **Guardrails**: Methodology compliance checking
- **Fallback Mechanisms**: Alternative approaches when primary methods fail
- **Template Fallbacks**: Base template used when specific template not found
- **Audience Validation**: Automatic fallback to "internal" for unknown audiences
- **Document Type Validation**: Automatic switch to default when invalid type selected



## Contributing

For issues and questions, please use the GitHub issue tracker.

For Development:

1. Fork the repository
2. Create a feature branch: `git checkout -b feature/your-feature`
3. Commit changes: `git commit -m 'Add some feature'`
4. Push to branch: `git push origin feature/your-feature`
5. Open a pull request

Contribution Guidelines:

- Follow existing code style and patterns
- Add tests for new features
- Update documentation as needed
- Ensure backward compatibility
- Consider all audience types in changes


Features Ideas:

- **Additional Audience Types**: NGO, academic, general public
- **More Document Types**: Infographics, presentations, video scripts
- **Template Editor**: UI for creating/customizing templates
- **Configuration UI**: Admin interface for managing settings
- **Usage Analytics**: Dashboard for monitoring and insights

Potential Integrations:

- **Additional Data Sources**: World Bank, UNHCR reports, etc.
- **Export Formats**: PDF, PowerPoint, Word
- **Collaboration Tools**: Microsoft 365
- **Translation Services**: Multilingual support
- **Accessibility Tools**: Screen reader optimization

Research Directions:

- **Audience Analysis**: Impact of different configurations
- **Template Effectiveness**: Which structures work best
- **User Behavior**: How different audiences interact
- **Performance Optimization**: Faster rendering and processing
- **AI Improvements**: Better tool selection and content generation

## License

[MIT License](LICENSE) - Copyright (c) 2024 UNHCR

