# UNHCR MCP Tools Architecture

## Overview

This document provides a comprehensive architecture overview of the UNHCR Statistics Copilot MCP server tools, including their relationships, workflows, and usage patterns.

---

## 🎯 Tool Taxonomy

The MCP tools are organized into **4 tiers** based on their role in the analysis workflow:

### Tier 1: Entry Point Tools (Highest Level)
These are the primary tools that external consumers (AI agents, APIs, users) should call directly.

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `full_analysis_workflow` | Complete end-to-end analysis: question → data → story → notebook | For comprehensive analysis requests |
| `quick_analysis` | Lightweight analysis: question → data → story (no notebook) | For fast, simple queries |
| `compare_analysis` | Run same analysis across multiple scenarios | For comparative questions |

### Tier 2: Workflow Orchestration Tools
These tools orchestrate multiple underlying tools to provide complete workflows.

| Tool | Purpose | When to Use |
|------|---------|-------------|
| `run_enhanced_analysis` | Full pipeline with statistics, guardrails, visualization | When rich insights are needed |
| `run_conditional_analysis` | Auto-detects enhanced vs simple pipeline | For adaptive workflows |
| `get_data_for_story` | Orchestrates data retrieval with enrichment | Internal use |
| `safe_tool_selection` | Selects appropriate data tool based on question | Step 1 of any workflow |

### Tier 3: Core Functionality Tools
These are the primary data and analysis tools.

#### Data Retrieval
| Tool | Purpose | Data Source |
|------|---------|-------------|
| `get_population_data` | Population statistics | UNHCR API |
| `get_demographics_data` | Age/sex breakdown | UNHCR API |
| `get_rsd_applications` | Asylum applications | UNHCR API |
| `get_rsd_decisions` | RSD decision outcomes | UNHCR API |
| `get_solutions` | Durable solutions (return, resettlement, etc.) | UNHCR API |
| `get_country_key_figures` | Country-level summaries | UNHCR API |
| `get_population_trends` | Time series data | UNHCR API |
| `get_demographic_breakdown` | Detailed demographics | UNHCR API |

#### Analysis & Enrichment
| Tool | Purpose | Output |
|------|---------|--------|
| `analyze_data_statistics` | Statistical analysis (mean, median, correlations) | Statistics dict |
| `apply_analysis_guardrails` | UNHCR methodology compliance validation | Compliance report |
| `extract_visualization_structure` | Extract metadata from visualizations | Viz structure |
| `generate_visualization_description` | Generate AI descriptions for visualizations | Text description |

#### Story Generation
| Tool | Purpose | Method |
|------|---------|--------|
| `generate_analytical_story` | Template-based story generation | Jinja2 templates |
| `generate_ai_data_story` | LLM-based story with RAG enrichment | Azure OpenAI + RAG |

#### Output Formatting
| Tool | Purpose | Format |
|------|---------|--------|
| `create_quarto_notebook` | Generate reproducible Quarto notebook | .qmd file |

### Tier 4: Utility & Support Tools
These tools provide supporting functionality.

| Tool | Purpose | Usage |
|------|---------|-------|
| `retrieve_report_context` | RAG retrieval from UNHCR reports | Used by `generate_ai_data_story` |
| `get_usage_guidance` | Get tool usage help | User assistance |
| `get_suggested_questions` | Get question suggestions | User assistance |

---

## 🔄 Workflow Diagrams

### Main Workflow: Full Analysis

```
┌─────────────────────────────────────────────────────────────────────┐
│                        USER REQUEST                                   │
│              (e.g., "Analyze refugee trends from Syria")             │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TIER 1: ENTRY POINT                                │
│                  full_analysis_workflow                               │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                    TIER 2: WORKFLOW ORCHESTRATION                     │
│                  ┌─────────────────┐ ┌─────────────────┐              │
│                  │ Step 1:         │ │ Step 2:         │              │
│                  │ safe_tool_      │ │ get_data_for_   │              │
│                  │ selection       │ │ story           │              │
│                  │                 │ │                 │              │
│                  │ Selects data    │ │ Retrieves data  │              │
│                  │ tool based on   │ │ + enrichment    │              │
│                  │ question        │ │ (stats, guard-   │              │
│                  │                 │ │  rails, viz)     │              │
│                  └────────┬────────┘ └────────┬────────┘              │
│                           │                 │                             │
│                           ▼                 ▼                             │
│                  ┌───────────────────────────────────┐              │
│                  │         Step 3: Story              │              │
│                  │   generate_analytical_story        │              │
│                  │   (or generate_ai_data_story)      │              │
│                  └────────────────┬──────────────────┘              │
│                                   │                                    │
│                                   ▼                                    │
│                  ┌───────────────────────────────────┐              │
│                  │         Step 4: Output             │              │
│                  │   create_quarto_notebook           │              │
│                  └───────────────────────────────────┘              │
└─────────────────────────────────────────────────────────────────────┘
                                │
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│                        RESULT                                        │
│  {                                                                   │
│    "status": "success",                                              │
│    "question": "Analyze refugee trends from Syria",                 │
│    "data": {...},                                                    │
│    "story": {...},                                                   │
│    "notebook": {...},                                                │
│    "metadata": { "workflow": "full_analysis", ... }                │
│  }                                                                   │
└─────────────────────────────────────────────────────────────────────┘
```

### Simplified Workflow: Quick Analysis

```
┌─────────────────────────┐
│   USER REQUEST           │
└─────────────────────────┘
          │
          ▼
┌─────────────────────────┐
│   quick_analysis          │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   get_data_for_story     │
│   (includes enrichment)  │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   generate_analytical_   │
│   story                 │
└────────────┬────────────┘
             │
             ▼
┌─────────────────────────┐
│   RESULT                 │
│   { status, question,     │
│     data, story }         │
└─────────────────────────┘
```

### Data Enrichment Pipeline (Inside get_data_for_story)

```
┌─────────────────────────────────────────┐
│         get_data_for_story                │
├─────────────────────────────────────────┤
│  1. Extract parameters from question      │
│  2. Call appropriate data tool:           │
│     - get_population_data                 │
│     - get_demographics_data               │
│     - get_rsd_applications                 │
│     - etc.                                │
│  3. Enrich with:                          │
│     ┌─────────────────────────────────┐  │
│     │ analyze_data_statistics          │  │
│     │ - Calculates mean, median, std    │  │
│     │ - Calculates correlations         │  │
│     └─────────────────────────────────┘  │
│     ┌─────────────────────────────────┐  │
│     │ apply_analysis_guardrails         │  │
│     │ - Validates UNHCR compliance      │  │
│     │ - Checks data quality             │  │
│     └─────────────────────────────────┘  │
│     ┌─────────────────────────────────┐  │
│     │ extract_visualization_structure  │  │
│     │ - Detects viz type and labels     │  │
│     └─────────────────────────────────┘  │
│     ┌─────────────────────────────────┐  │
│     │ generate_visualization_description│  │
│     │ - AI-powered viz narration        │  │
│     └─────────────────────────────────┘  │
└─────────────────────────────────────────┘
                              │
                              ▼
                    Enriched Data Dict
```

---

## 🎨 Tool Relationships

### Dependency Graph

```
                                    ┌─────────────────────┐
                                    │   Entry Points       │
                                    ├─────────────────────┤
                                    │ full_analysis_      │
                                    │ workflow            │
                                    │ quick_analysis       │
                                    │ compare_analysis     │
                                    └─────────┬───────────┘
                                              │
              ┌───────────────────────────────┼───────────────────────────────┐
              │                               │                       │           │
              ▼                               ▼                       ▼           │
┌─────────────────┐              ┌─────────────────┐         ┌─────────────┐
│ run_enhanced_   │              │ run_conditional  │         │ Direct Data │
│ analysis        │              │ _analysis        │         │ Tools       │
└────────┬────────┘              └─────────────────┘         └──────┬──────┘
         │                                                                        │
         ▼                                                                        │
┌─────────────────────────────────────────────────────────────────────────────┐
│                           get_data_for_story                                   │
│                                                                               │
│  ┌─────────────────┐    ┌─────────────────┐    ┌─────────────────┐            │
│  │ Data Tools      │    │ Enrichment      │    │ Orchestration   │            │
│  │                 │    │ Tools           │    │ Tools           │            │
│  │ - get_population_│    │ - analyze_data_ │    │ - safe_tool_    │            │
│  │   data          │    │   statistics    │    │   selection     │            │
│  │ - get_demographics│   │ - apply_analysis│    │                 │            │
│  │   _data         │    │   _guardrails   │    │                 │            │
│  │ - get_rsd_      │    │ - extract_viz_  │    │                 │            │
│  │   applications  │    │   _structure    │    │                 │            │
│  │ - ...           │    │ - generate_viz_ │    │                 │            │
│  └─────────────────┘    │   _description   │    │                 │            │
│                      └─────────────────┘    └─────────────────┘            │
└─────────────────────────────────────────────────────────────────────────────┘
         │                               │                               │
         ▼                               ▼                               ▼
┌─────────────────┐              ┌─────────────────┐               ┌─────────────────┐
│ Story Generation │              │ RAG Enrichment  │               │ Output          │
│                 │              │                 │               │                 │
│ - generate_     │              │ - retrieve_     │               │ - create_       │
│   analytical_   │              │   report_       │               │   quarto_       │
│   story         │              │   context       │               │   notebook      │
│ - generate_ai_  │              │                 │               │                 │
│   data_story    │              └─────────────────┘               └─────────────────┘
└─────────────────┘
```

---

## 📊 Tool Usage Statistics

### Registration Status
- **Total Tools**: 23 (20 original + 3 new workflow tools)
- **MCP Registered**: 23/23 ✅
- **Actively Used in chat.py**: 17/20 original + 3/3 new = 20/23
- **Used in Workflows**: 15/20 original + 3/3 new = 18/23

### Usage Frequency (Estimated)
| Tool | Usage Level | Notes |
|------|-------------|-------|
| `full_analysis_workflow` | ★★★★★ | Primary entry point |
| `get_data_for_story` | ★★★★★ | Called by all workflows |
| `generate_analytical_story` | ★★★★★ | Default story generator |
| `safe_tool_selection` | ★★★★★ | Step 1 of all workflows |
| `analyze_data_statistics` | ★★★★☆ | In enhanced pipeline |
| `apply_analysis_guardrails` | ★★★★☆ | In enhanced pipeline |
| `extract_visualization_structure` | ★★★★☆ | In enhanced pipeline |
| `generate_visualization_description` | ★★★★☆ | In enhanced pipeline |
| `create_quarto_notebook` | ★★★★☆ | Final output step |
| Data retrieval tools | ★★★★☆ | Called by get_data_for_story |
| `run_enhanced_analysis` | ★★★☆☆ | MCP-accessible pipeline |
| `run_conditional_analysis` | ★★★☆☆ | MCP-accessible pipeline |
| `quick_analysis` | ★★☆☆☆ | Lightweight workflow |
| `compare_analysis` | ★★☆☆☆ | Comparative workflow |
| `generate_ai_data_story` | ★☆☆☆☆ | Requires RAG/LLM |
| `retrieve_report_context` | ★☆☆☆☆ | Used by generate_ai_data_story |
| `get_usage_guidance` | ☆☆☆☆☆ | User assistance only |
| `get_suggested_questions` | ☆☆☆☆☆ | User assistance only |

---

## 🎯 Tool Selection Guidelines

### When to Use Which Entry Point

| Scenario | Recommended Tool | Rationale |
|----------|-----------------|-----------|
| Comprehensive analysis needed | `full_analysis_workflow` | All steps included |
| Quick answer needed | `quick_analysis` | Fast, no notebook |
| Compare multiple scenarios | `compare_analysis` | Run same query multiple times |
| Custom workflow needed | `run_conditional_analysis` or `run_enhanced_analysis` | Flexible pipeline |
| Just need data | Direct data tools (e.g., `get_population_data`) | Simple requests |
| Just need help | `get_usage_guidance` or `get_suggested_questions` | Assistance |

### When to Use Enhanced vs Simple Pipeline

**Use Enhanced Pipeline (`use_enhanced=True`) when:**
- Question contains: "analyze", "trends", "comparison", "correlation", "relationship", "pattern", "insight", "deep dive", "comprehensive"
- Need statistical analysis (mean, median, correlations)
- Need UNHCR compliance validation
- Need visualization descriptions
- Generating reports for external stakeholders

**Use Simple Pipeline (`use_enhanced=False`) when:**
- Quick fact-checking
- Simple data retrieval
- Internal use with familiar data
- Performance-sensitive scenarios
- Real-time or interactive use

---

## 🔧 Configuration Options

### Analysis Configuration

```python
analysis_config = {
    # Audience-specific settings
    "audience": "internal",  # or "public_donors", "private_donors", "government", "media"
    
    # Document type
    "document_type": "long_read",  # or "executive_summary", "technical_report", "social_media"
    
    # Tone and style
    "tone": "formal",
    "length": {
        "wordRange": "2000-5000",
        "readingTime": "10-25 min"
    },
    
    # Structure (sections to include)
    "structure": [
        "introduction",
        "context",
        "key findings",
        "deep dive analysis",
        "implications",
        "conclusion"
    ],
    
    # Pipeline options
    "use_enhanced": True,  # Enable enhanced pipeline
    "apply_guardrails": True,  # Validate against UNHCR standards
    "use_report_context": True,  # Use RAG enrichment (if available)
    
    # Output options
    "include_code_cells": True,  # Include Python code in notebook
    "use_unhcr_theme": True,  # Use UNHCR branding
    "render_html": True,  # Render HTML output
    "render_pdf": True  # Render PDF output
}
```

---

## 💡 Best Practices

### 1. Always Start with Question Classification
```python
# Good: Let the system determine the right tool
selection = await safe_tool_selection_tool(question)
data = await get_data_for_story_tool(api_client, question, **selection.parameters)

# Bad: Hardcode tool selection
# data = await get_population_data_tool(api_client, ...)  # May not be the right tool!
```

### 2. Use Workflow Tools for Complex Requests
```python
# Good: Use high-level workflow
result = await full_analysis_workflow_tool(
    question="Analyze refugee trends from Syria to Germany 2020-2023",
    audience="government"
)

# Bad: Manual orchestration (error-prone, harder to maintain)
# selection = await safe_tool_selection_tool(question)
# data = await get_data_for_story_tool(...)
# story = await generate_analytical_story_tool(...)
# notebook = await create_quarto_notebook_tool(...)
```

### 3. Use Enhanced Pipeline for Reports
```python
# Good: Enhanced pipeline for external reports
result = await full_analysis_workflow_tool(
    question="...",
    use_enhanced=True,  # Enables stats, guardrails, viz
    include_notebook=True
)

# Good: Simple pipeline for internal checks
result = await quick_analysis_tool(
    question="What's the refugee count?",
    use_enhanced=False  # Fast, lightweight
)
```

### 4. Handle Errors Gracefully
```python
# All tools return dicts with "status" field
result = await some_tool(...)
if result.get("status") == "error":
    # Handle error appropriately
    logger.error(f"Tool failed: {result.get('error')}")
    # Fallback to simpler approach
```

### 5. Use RAG When Available
```python
# Check if RAG/LLM is configured
if llm_available and rag_retriever:
    story = await generate_ai_data_story_tool(
        visualization_data=data,
        context=question,
        rag_retriever=rag_retriever,
        use_report_context=True
    )
else:
    # Fallback to template-based
    story = await generate_analytical_story_tool(...)
```

---

## 📚 Tool Reference by Category

### Entry Point Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `full_analysis_workflow` | Complete end-to-end analysis | question, origin, destination, topic, timespan, year, years, population_types, coo_all, coa_all, audience, document_type, style, use_enhanced, include_notebook, include_html, include_pdf, output_path | Full analysis result with data, story, notebook |
| `quick_analysis` | Lightweight analysis (no notebook) | question, audience, document_type | Quick analysis result with data, story |
| `compare_analysis` | Run same analysis for multiple scenarios | question_template, comparisons, audience | Comparative analysis with results for each scenario |

### Workflow Orchestration Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `run_enhanced_analysis` | Full pipeline with all enrichments | question, data, audience, document_type, analysis_config, use_rag | Enhanced story with statistics, guardrails, visualization |
| `run_conditional_analysis` | Auto-detects enhanced vs simple | question, data, audience, document_type, analysis_config, use_enhanced | Story (enhanced or simple) |
| `get_data_for_story` | Data retrieval with enrichment | question, coo, coa, year, years, population_types, coo_all, coa_all, audience, document_type, origin, destination, population_type, timespan | Enriched data with statistics, guardrails, visualization |
| `safe_tool_selection` | Select appropriate data tool | question | Selected tool name and parameters |

### Data Retrieval Tools
All these tools are called internally by `get_data_for_story`:

| Name | Description | Key Parameters |
|------|-------------|----------------|
| `get_population_data` | Forcibly displaced population statistics | coo, coa, year, coo_all, coa_all |
| `get_demographics_data` | Age and sex breakdown | coo, coa, year, pop_type |
| `get_rsd_applications` | Asylum applications | coo, coa, year, coo_all, coa_all |
| `get_rsd_decisions` | RSD decision outcomes | coo, coa, year, coo_all, coa_all |
| `get_solutions` | Durable solutions data | coo, coa, year, coo_all, coa_all |
| `get_country_key_figures` | Country-level statistics | coa, coo, year, population_types |
| `get_population_trends` | Time series data | coa, coo, years, population_types |
| `get_demographic_breakdown` | Detailed demographics | coa, coo, year, population_type |

### Analysis & Enrichment Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `analyze_data_statistics` | Statistical analysis | data, numeric_columns, categorical_columns, correlation_columns | Statistics dict with mean, median, std, correlations |
| `apply_analysis_guardrails` | Compliance validation | analysis_request, population_type, country_iso, year, detailed_report | Compliance report with overall_compliant, compliance_percentage |
| `extract_visualization_structure` | Extract viz metadata | visualization_type, title, subtitle, x_axis_label, y_axis_label, ... | Visualization structure dict |
| `generate_visualization_description` | Generate viz descriptions | structure, statistics, description_type, max_length, focus_areas | Description text |

### Story Generation Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `generate_analytical_story` | Template-based story | result, data, question, audience, document_type, analysis_config | Story with title, content, metadata |
| `generate_ai_data_story` | LLM-based story with RAG | visualization_data, context, story_type, max_tokens, apply_guardrails, use_report_context, rag_retriever, ... | AI-generated story with RAG enrichment |

### Output Formatting Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `create_quarto_notebook` | Generate Quarto notebook | story_content, output_path, title, author, date, include_code_cells, use_unhcr_theme, use_unhcr_style, original_query, metadata, data, render_html, render_pdf | Quarto content, paths to rendered files |

### Utility Tools
| Name | Description | Parameters | Returns |
|------|-------------|------------|---------|
| `retrieve_report_context` | RAG retrieval from reports | request, top_k, fetch_k, year, report_type, section_contains, exclude_figures_tables, rerank | Retrieved context chunks |
| `get_usage_guidance` | Get tool usage help | tool_category, specific_tool | Usage guidance dict |
| `get_suggested_questions` | Get question suggestions | topic, data_type, limit | List of suggested questions |

---

## 🚀 Migration Guide

### From Direct Tool Calls to Workflows

**Before:**
```python
# Manual orchestration
selection = await call_tool("safe_tool_selection", {"question": question})
data = await call_tool("get_data_for_story", {**selection.arguments, "question": question})
story = await call_tool("generate_analytical_story", {"data": data, "question": question})
notebook = await call_tool("create_quarto_notebook", {"story_content": story["story"]})
```

**After:**
```python
# Single workflow call
result = await call_tool("full_analysis_workflow", {
    "question": question,
    "audience": "internal"
})
```

### From Simple to Enhanced Pipeline

**Before:**
```python
data = await call_tool("get_data_for_story", {"question": question})
story = await call_tool("generate_analytical_story", {"data": data, "question": question})
```

**After:**
```python
# Enhanced pipeline with statistics, guardrails, visualization
data = await call_tool("get_data_for_story", {"question": question})
result = await call_tool("run_enhanced_analysis", {
    "question": question,
    "data": data,
    "use_rag": False  # Set to True if RAG is available
})
```

---

## 🔄 Tool Naming Recommendations

For better clarity and to avoid confusion, the following tool name improvements are recommended:

### Current Names vs Recommended Names

| Current Name | Issue | Recommended Name | Rationale |
|--------------|-------|------------------|-----------|
| `get_data_for_story` | Too generic, doesn't convey enrichment | `fetch_and_enrich_data` or `prepare_story_data` | Better describes that it both fetches AND enriches data |
| `generate_analytical_story` | Confusing vs `generate_ai_data_story` | `generate_template_story` | Clarifies it's template-based, not AI-based |
| `generate_ai_data_story` | Name suggests it's the main/preferred one | `generate_rag_enriched_story` | Clarifies it uses RAG enrichment |
| `get_population_data` | Sounds like it's the only population tool | `get_basic_population_stats` or `get_population_statistics` | More specific about what it returns |
| `get_country_key_figures` | "Key figures" is unclear | `get_country_summary` or `get_country_profile` | More intuitive for non-technical users |
| `apply_analysis_guardrails` | Long and verbose | `validate_analysis` or `check_compliance` | Shorter and clearer |
| `extract_visualization_structure` | Very long | `extract_viz_metadata` | Shorter while still clear |
| `generate_visualization_description` | Very long | `describe_visualization` | Shorter and more active |

### Migration Strategy

To implement these renames **without breaking existing code**:

1. **Keep old names as aliases** (recommended for backward compatibility):
   ```python
   # In server.py
   @server.tool(name="get_data_for_story")  # Old name (kept)
   async def get_data_for_story_wrapper(...): ...
   
   @server.tool(name="fetch_and_enrich_data")  # New name (alias)
   async def fetch_and_enrich_data_wrapper(...):
       return await get_data_for_story_wrapper(...)
   ```

2. **Update documentation** to use new names primarily

3. **Deprecate old names** over time with warnings

4. **Eventually remove old names** in a future major version

### Priority Order for Renaming

1. **High Priority** (Most confusing):
   - `generate_analytical_story` → `generate_template_story`
   - `generate_ai_data_story` → `generate_rag_enriched_story`

2. **Medium Priority** (Long names):
   - `apply_analysis_guardrails` → `validate_analysis`
   - `extract_visualization_structure` → `extract_viz_metadata`
   - `generate_visualization_description` → `describe_visualization`

3. **Low Priority** (Minor clarity issues):
   - `get_data_for_story` → `prepare_story_data`
   - `get_population_data` → `get_population_statistics`
   - `get_country_key_figures` → `get_country_summary`

---

## 📝 Version History

- **v1.0** (Initial): Basic tool set with data retrieval and simple story generation
- **v2.0** (Current): Enhanced pipeline with statistics, guardrails, visualization
- **v3.0** (This document): Added workflow tools, comprehensive documentation

---

## 🎯 Conclusion

The UNHCR MCP tools are now organized into a **4-tier architecture** with clear entry points, workflow orchestration, core functionality, and utilities. This structure provides:

1. **Simplicity** for external consumers (use Tier 1 entry points)
2. **Flexibility** for advanced use cases (use Tier 2-4 tools directly)
3. **Consistency** through standardized workflows
4. **Maintainability** through clear dependencies and relationships

For most use cases, **start with `full_analysis_workflow`** and only drop down to lower-level tools when you need specific customization.
