# MCP Tools Orchestration Audit

## Executive Summary

This document provides a comprehensive audit of the MCP tool orchestration within the UNHCR Statistics Copilot system. The audit identifies critical issues with Quarto notebook generation, unused tools, and proposes a refactored architecture for proper tool integration.

**Audit Date:** 2025-01-08  
**Version:** 1.0  
**Status:** Draft  

---

## Table of Contents

1. [Current Architecture Overview](#current-architecture-overview)
2. [Identified Issues](#identified-issues)
3. [Unused Tools Analysis](#unused-tools-analysis)
4. [Quarto Generation Problems](#quarto-generation-problems)
5. [Orchestration Workflow Analysis](#orchestration-workflow-analysis)
6. [Refactored Architecture](#refactored-architecture)
7. [Implementation Recommendations](#implementation-recommendations)
8. [Verification Checklist](#verification-checklist)

---

## Current Architecture Overview

### Tool Inventory

The system currently has **25 MCP tools** registered in the server:

#### Data Retrieval Tools (8)
- `retrieve_report_context` - RAG-based context retrieval
- `get_population_data` - Core population statistics
- `get_demographics_data` - Age/sex breakdowns
- `get_rsd_applications` - Refugee Status Determination applications
- `get_rsd_decisions` - RSD decision outcomes
- `get_solutions` - Durable solutions data
- `get_country_key_figures` - Country-specific statistics
- `get_population_trends` - Time-series population data
- `get_demographic_breakdown` - Detailed demographic analysis

#### Analysis Pipeline Tools (5)
- `extract_visualization_structure` - Phase 1: Structure extraction
- `analyze_data_statistics` - Phase 2: Statistical analysis
- `generate_visualization_description` - Phase 3: Description generation
- `generate_ai_data_story` - Phase 4: Story generation
- `apply_analysis_guardrails` - Compliance validation

#### Utility Tools (7)
- `get_usage_guidance` - System documentation
- `get_suggested_questions` - Query suggestion
- `safe_tool_selection` - Intelligent tool routing
- `create_quarto_notebook` - Report generation
- `get_data_for_story` - Data orchestration
- `generate_analytical_story` - Comprehensive analysis
- `generate_analytical_story_tool` - Alternative story generation

### Current Workflow

```
┌─────────────────────┐
│   User Query         │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│   process_chat_message│
│   (backend/chat.py)   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ safe_tool_selection  │◄─── UNUSED TOOLS NOT INTEGRATED
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ get_data_for_story   │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ generate_analytical_ │
│      story          │
└──────────┬──────────┘
           │
           ▼
┌─────────────────────┐
│ create_quarto_notebook│◄─── RENDERING ISSUES
└─────────────────────┘
```

---

## Identified Issues

### Critical Issues (Blocking)

#### Issue #1: Quarto Indentation Error
**Location:** `backend/mcp/tools/create_quarto_notebook.py`, line 366  
**Severity:** HIGH  
**Status:** ACTIVE  

```python
# Line 366 in _generate_data_visualization_code()
code_lines.append("import matplotlib.pyplot as plt")
```

**Root Cause:** The `_generate_data_visualization_code()` function generates Python code that may have indentation issues when inserted into Quarto code cells. The function doesn't properly handle the indentation context.

**Evidence:** 
- Error: `IndentationError: unexpected indent`
- File: `data/quarto_analyses/20260706_120928_Generate_an_analysis_of_Refugees_from_France_in_th_a4685e71-f46f-4ddf-ac86-8e258937beb4.qmd`

**Impact:** Generated Quarto notebooks fail to render or execute.

---

#### Issue #2: Missing Narrative in Quarto Output
**Location:** `backend/mcp/tools/create_quarto_notebook.py`, line 524-539  
**Severity:** HIGH  
**Status:** ACTIVE  

**Root Cause:** The `_extract_text_from_message()` function fails to properly extract narrative content from complex message structures. When the story content is passed as a nested dictionary or list, the extraction logic doesn't handle all edge cases.

**Evidence:** 
- User reports: "generated document do not follows the requested structure"
- User reports: "it seems the narrative are not pushed in the quarto"

**Impact:** Generated reports lack the analytical narrative, making them incomplete.

---

#### Issue #3: Code Cells Visible in Rendered Output
**Location:** `backend/templates/quarto_notebook.j2`, lines 69-78  
**Severity:** HIGH  
**Status:** ACTIVE  

**Root Cause:** The template uses `#| echo: false` to hide code output, but this is not working correctly. The code cells are still displaying the code itself in the rendered HTML.

**Current Template:**
```jinja2
:::: {.cell}
```{python}
#| echo: false
#| fold: true
# This cell loads and validates metadata
print("UNHCR Analysis Notebook")
```
::::
```

**Impact:** End users see raw Python code instead of clean output.

---

#### Issue #4: Metadata Visible in Rendered HTML
**Location:** `backend/templates/quarto_notebook.j2`, lines 28-59  
**Severity:** MEDIUM  
**Status:** ACTIVE  

**Root Cause:** All metadata is stored in the YAML header, which is visible in the source `.qmd` file. However, the user requirement is that metadata should ONLY be visible in the source file, not in the rendered HTML version.

**Current State:** YAML header metadata is properly hidden from rendered HTML by Quarto's default behavior, but the HTML comments (lines 101-106) are visible in the source.

**Impact:** Sensitive metadata could be exposed in rendered output.

---

### Major Issues (Non-Blocking)

#### Issue #5: Unused MCP Tools
**Severity:** HIGH  
**Status:** ACTIVE  

The following tools are **registered but never called** in the orchestration workflow:

1. **`analyze_data_statistics_tool`** - Statistical analysis (Phase 2)
   - Location: `backend/mcp/tools/analyze_data_statistics.py`
   - Never called by: `generate_comprehensive_quarto_analysis`

2. **`apply_analysis_guardrails_tool`** - Compliance validation
   - Location: `backend/mcp/tools/apply_analysis_guardrails.py`
   - Never called by: `generate_comprehensive_quarto_analysis`

3. **`extract_visualization_structure_tool`** - Structure extraction (Phase 1)
   - Location: `backend/mcp/tools/extract_visualization_structure.py`
   - Never called by: `generate_comprehensive_quarto_analysis`

4. **`generate_visualization_description_tool`** - Description generation (Phase 3)
   - Location: `backend/mcp/tools/generate_visualization_description.py`
   - Never called by: `generate_comprehensive_quarto_analysis`

**Impact:** Rich analysis features (statistics, guardrails, visualization descriptions) are completely unavailable to users.

---

#### Issue #6: Quarto Not Pre-Rendered
**Location:** `backend/history.py`, line 231-233  
**Severity:** MEDIUM  
**Status:** ACTIVE  

**Root Cause:** Quarto files are saved but not automatically pre-rendered to HTML and PDF. The user requirement is that rendering should be done "directly and saved so that it load automatically from the frontend - and not generated per demand".

**Current Behavior:** 
- Files are saved to `./data/quarto_analyses/` as `.qmd`
- Rendering is attempted in `create_quarto_notebook_tool()` but only when `render_html=True` or `render_pdf=True`
- Frontend must request rendering on-demand

**Evidence:** User report: "quarto rendering to both html and pdf should be done directly and saved so that it load automatically from the frontend"

**Impact:** Performance degradation, user waits for rendering on each request.

---

## Unused Tools Analysis

### Tool: `analyze_data_statistics_tool`

**Purpose:** Perform statistical analysis on datasets including descriptive statistics, correlations, and distributions.

**Current Usage:** 0 calls in codebase

**Recommended Integration Point:** 
```python
# In generate_comprehensive_quarto_analysis(), after data retrieval:
statistics_result = await analyze_data_statistics_tool(
    data=data_result.get('items', []),
    numeric_columns=['value', 'year'],
    categorical_columns=['population_type', 'country']
)
```

**Expected Output:**
- Mean, median, min, max, std_dev for numeric columns
- Frequency distributions for categorical columns
- Correlation analysis between numeric columns

**Use Cases:**
- Automated statistical insights in reports
- Data quality validation
- Trend analysis

---

### Tool: `apply_analysis_guardrails_tool`

**Purpose:** Apply UNHCR methodology guardrails to ensure analyses follow international standards.

**Current Usage:** 0 calls in codebase

**Recommended Integration Point:**
```python
# In generate_comprehensive_quarto_analysis(), before story generation:
guardrails_result = await apply_analysis_guardrails_tool(
    analysis_request={
        'data_fields': list(data_result.get('items', [{}])[0].keys()),
        'storytelling_context': question,
        'data': data_result
    },
    population_type=extracted_params.get('population_type'),
    country_iso=extracted_params.get('coo') or extracted_params.get('coa'),
    detailed_report=True
)
```

**Expected Output:**
- Population definition compliance
- Country code validation
- Data disaggregation validation
- Data completeness checks
- Storytelling guardrails validation

**Use Cases:**
- Ensure all analyses comply with UNHCR standards
- Validate user queries before processing
- Generate compliance reports

---

### Tool: `extract_visualization_structure_tool`

**Purpose:** Extract and structure visualization metadata for AI-generated reports.

**Current Usage:** 0 calls in codebase

**Recommended Integration Point:**
```python
# In generate_comprehensive_quarto_analysis(), after data retrieval:
viz_structure = await extract_visualization_structure_tool(
    visualization_type='line_chart',
    title=f'{topic} Trends',
    x_axis_label='Year',
    y_axis_label='Population Count',
    legend_items=list(set(item.get('population_type', 'Unknown') 
                       for item in data_result.get('items', [])))
)
```

**Expected Output:**
- Structured visualization metadata
- Labels for axes, title, subtitle
- Legend items
- Geometric layers

**Use Cases:**
- Automatic chart configuration
- Visualization metadata storage
- Template-based chart generation

---

### Tool: `generate_visualization_description_tool`

**Purpose:** Generate AI-powered descriptions and interpretations for visualizations.

**Current Usage:** 0 calls in codebase

**Recommended Integration Point:**
```python
# In generate_comprehensive_quarto_analysis(), after statistics:
# Assuming viz_structure and statistics_result are available
viz_description = await generate_visualization_description_tool(
    structure=viz_structure,
    statistics=statistics_result,
    description_type='both',
    focus_areas=['trends', 'comparisons', 'outliers']
)
```

**Expected Output:**
- Natural language description of visualization
- Statistical insights
- Focus area highlights

**Use Cases:**
- Chart captions
- Visualization explanations
- Automated report text

---

## Quarto Generation Problems

### Root Cause Analysis

#### Problem 1: Indentation Error

The `_generate_data_visualization_code()` function in `create_quarto_notebook.py` generates Python code with proper indentation, but when this code is inserted into a Quarto code cell, the indentation context is wrong.

**Current Code (lines 364-368):**
```python
code_lines.append("import pandas as pd")
code_lines.append("import matplotlib.pyplot as plt")
code_lines.append("import seaborn as sns")
```

**Problem:** These lines are at the top level, but when inserted into a Quarto code cell with `#| echo: false`, they need consistent indentation.

**Solution:** Ensure all generated code is properly indented for Quarto code cells:
```python
# In Quarto code cell, code should be at consistent indentation level
# Don't add extra indentation beyond what's needed for Python syntax
```

#### Problem 2: Narrative Extraction Failure

The `_extract_text_from_message()` function has gaps in handling complex message formats.

**Current Logic (lines 63-88):**
```python
if isinstance(content, list):
    texts = []
    for item in content:
        if isinstance(item, dict):
            if 'text' in item:
                texts.append(item['text'])
            elif 'content' in item:
                text = _extract_text_from_message(item['content'])
                if text:
                    texts.append(text)
```

**Problem:** Doesn't handle cases where content is a dict with nested 'raw_text' or 'message' fields that are common in LLM responses.

**Solution:** Expand extraction logic to handle more message formats.

#### Problem 3: Code Visibility in Rendered Output

The template uses `#| echo: false` but this isn't working correctly.

**Root Cause:** The `#|` syntax is Jupyter cell metadata, but Quarto may not be processing it correctly, OR the code is being inserted at the wrong indentation level.

**Solution:** Use Quarto-native cell options:
```jinja2
:::: {.cell echo="false"}
```

---

## Orchestration Workflow Analysis

### Current Flow (Simplified)

```
User Query
    │
    ▼
process_chat_message()
    │
    ▼
generate_comprehensive_quarto_analysis()
    │
    ├── safe_tool_selection() - OK
    │
    ├── get_data_for_story() - OK
    │
    ├── generate_analytical_story() - OK
    │
    └── create_quarto_notebook() - PROBLEMS
```

### Missing from Flow

```
X analyze_data_statistics() - NOT CALLED
X apply_analysis_guardrails() - NOT CALLED
X extract_visualization_structure() - NOT CALLED
X generate_visualization_description() - NOT CALLED
```

### Complete Pipeline (Proposed)

```
User Query
    │
    ▼
process_chat_message()
    │
    ▼
generate_comprehensive_quarto_analysis()
    │
    ├── safe_tool_selection() - Determine tool chain
    │
    ├── get_data_for_story() - Get raw data
    │
    ├── extract_visualization_structure() - Define viz metadata ← NEW
    │
    ├── analyze_data_statistics() - Calculate statistics ← NEW
    │
    ├── apply_analysis_guardrails() - Validate compliance ← NEW
    │
    ├── generate_visualization_description() - Describe viz ← NEW
    │
    ├── generate_analytical_story() - Create narrative - ENHANCED
    │
    └── create_quarto_notebook() - Generate .qmd + pre-render HTML/PDF - FIXED
```

---

## Refactored Architecture

### Phase 1: Data Acquisition

```python
async def acquire_data(question, params):
    """Retrieve and validate data for analysis."""
    
    # Step 1: Select appropriate tool
    selection = await safe_tool_selection(question)
    
    # Step 2: Get data
    data = await get_data_for_story(
        question=question,
        **params
    )
    
    # Step 3: Validate with guardrails
    guardrails = await apply_analysis_guardrails(
        analysis_request={
            'data_fields': extract_fields(data),
            'storytelling_context': question,
            'data': data
        },
        **params
    )
    
    return {
        'data': data,
        'guardrails': guardrails,
        'selection': selection
    }
```

### Phase 2: Statistical Analysis

```python
async def analyze_data(data, numeric_columns, categorical_columns):
    """Perform comprehensive statistical analysis."""
    
    statistics = await analyze_data_statistics_tool(
        data=data.get('items', []),
        numeric_columns=numeric_columns,
        categorical_columns=categorical_columns,
        correlation_columns=numeric_columns[:2] if len(numeric_columns) >= 2 else None
    )
    
    return statistics
```

### Phase 3: Visualization Pipeline

```python
async def create_visualization_pipeline(data, question, audience, document_type):
    """Complete visualization creation pipeline."""
    
    # Step 1: Extract structure
    viz_structure = await extract_visualization_structure_tool(
        visualization_type=determine_viz_type(data),
        title=f"{question} Analysis",
        x_axis_label=determine_x_axis(data),
        y_axis_label=determine_y_axis(data),
        legend_items=extract_legend_items(data)
    )
    
    # Step 2: Analyze statistics
    statistics = await analyze_data(data)
    
    # Step 3: Generate description
    description = await generate_visualization_description_tool(
        structure=viz_structure,
        statistics=statistics,
        description_type='both',
        focus_areas=['trends', 'patterns', 'outliers']
    )
    
    return {
        'structure': viz_structure,
        'statistics': statistics,
        'description': description
    }
```

### Phase 4: Story Generation (Enhanced)

```python
async def generate_comprehensive_story(
    data,
    visualization_pipeline,
    question,
    audience,
    document_type,
    config
):
    """Generate story with full pipeline integration."""
    
    story = await generate_ai_data_story_tool(
        visualization_data={
            'data': data,
            'structure': visualization_pipeline['structure'],
            'statistics': visualization_pipeline['statistics'],
            'description': visualization_pipeline['description']
        },
        context=question,
        story_type=determine_story_type(audience, document_type),
        apply_guardrails=True,
        use_report_context=True,
        max_tokens=1000
    )
    
    return story
```

### Phase 5: Quarto Generation (Fixed)

```python
async def generate_quarto_notebook_fixed(
    story,
    visualization_pipeline,
    data,
    question,
    audience,
    document_type,
    config
):
    """Generate Quarto notebook with proper formatting."""
    
    # Ensure story content is properly extracted
    story_content = extract_narrative(story)  # Enhanced extraction
    
    # Generate visualization code (properly indented)
    viz_code = generate_viz_code(data, visualization_pipeline)
    
    # Create notebook with proper metadata
    notebook = await create_quarto_notebook_tool(
        story_content=story_content,
        title=story.get('title', question),
        author="UNHCR Statistics Copilot",
        include_code_cells=True,
        use_unhcr_theme=True,
        use_unhcr_style=True,
        metadata={
            'audience': audience,
            'document_type': document_type,
            'analysis_config': config,
            'tool_sequence': track_tool_sequence(),
            'statistics': visualization_pipeline['statistics'],
            'guardrails': validation_results,
            'visualization_structure': visualization_pipeline['structure'],
            'visualization_description': visualization_pipeline['description']
        },
        data=data,
        original_query=question,
        render_html=True,  # Pre-render
        render_pdf=True   # Pre-render
    )
    
    return notebook
```

---

## Implementation Recommendations

### Priority 1: Fix Quarto Generation (Immediate)

#### Fix 1.1: Indentation in Code Generation

**File:** `backend/mcp/tools/create_quarto_notebook.py`  
**Function:** `_generate_data_visualization_code()`  

**Changes:**
```python
# Remove the indentation issue by ensuring code starts at column 0
# The template will handle indentation within the code cell

def _generate_data_visualization_code(data: Any, data_name: str = "data") -> str:
    """
    Generate Python code for data visualization.
    
    Returns code with NO leading indentation - template handles this.
    """
    code_lines = []
    
    # Import statements - no indentation
    code_lines.append("import pandas as pd")
    code_lines.append("import matplotlib.pyplot as plt")
    code_lines.append("import seaborn as sns")
    code_lines.append("")
    
    # Rest of code... all at same indentation level
    
    return "\n".join(code_lines)
```

#### Fix 1.2: Enhanced Text Extraction

**File:** `backend/mcp/tools/create_quarto_notebook.py`  
**Function:** `_extract_text_from_message()`  

**Changes:**
```python
def _extract_text_from_message(content: Any) -> str:
    """Extract text content from various message formats."""
    
    if content is None:
        return ""
    
    if isinstance(content, str):
        # Clean JSON artifacts
        cleaned = content.strip()
        if cleaned.startswith('[') and cleaned.endswith(']'):
            try:
                parsed = json.loads(cleaned)
                return _extract_text_from_message(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        if cleaned.startswith('{') and cleaned.endswith('}'):
            try:
                parsed = json.loads(cleaned)
                return _extract_text_from_message(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        return cleaned
    
    if isinstance(content, list):
        texts = []
        for item in content:
            if isinstance(item, dict):
                # Enhanced: Check multiple possible text fields
                for key in ['text', 'content', 'raw_text', 'message', 'story']:
                    if key in item:
                        text = _extract_text_from_message(item[key])
                        if text:
                            texts.append(text)
                            break  # Take first match
                # If no specific field, try all values
                if not texts or not texts[-1]:
                    for key, value in item.items():
                        if key not in ['type', 'role', 'name']:  # Skip metadata
                            text = _extract_text_from_message(value)
                            if text:
                                texts.append(text)
                                break
            elif isinstance(item, str):
                texts.append(item)
        return "\n\n".join(texts)
    
    if isinstance(content, dict):
        # Check for story content in various locations
        for key in ['story', 'content', 'text', 'raw_text', 'message', 'narrative']:
            if key in content:
                return _extract_text_from_message(content[key])
        
        # Azure OpenAI format
        if 'content' in content and isinstance(content['content'], list):
            return _extract_text_from_message(content['content'])
        
        # Try all values
        for key, value in content.items():
            if key not in ['type', 'role', 'name', 'usage']:
                text = _extract_text_from_message(value)
                if text:
                    return text
    
    return str(content) if content else ""
```

#### Fix 1.3: Template for Hidden Code Cells

**File:** `backend/templates/quarto_notebook.j2`  

**Changes:**
```jinja2
{# Code cells - only output displayed, code hidden #}
{%- if include_code_cells and python_code %}
::: {.cell echo="false" fold="true"}
```{python}
# Data Analysis Code - click to expand
{{ python_code | indent(4, first=false) | safe }}
```
:::
{% endif %}

{%- if include_code_cells and python_code %}
::: {.cell}
```{python}
#| echo: false
#| fold: true
# Data Analysis Code - click to expand
{{ python_code | safe }}
```
:::
{% endif %}
```

**Better Solution:** Use proper Quarto cell options:
```jinja2
{# Code cells with proper Quarto syntax for hidden code #}
{%- if include_code_cells and python_code %}
```{python}
#| echo: false
#| fold: true
#| title: "Data Analysis Code"
{{ python_code | safe }}
```
{% endif %}
```

#### Fix 1.4: Ensure Metadata Only in Source

**File:** `backend/templates/quarto_notebook.j2`  

**Changes:** Move all metadata to YAML header only, remove HTML comments that might be rendered:
```jinja2
---
title: {{ title|quote_yaml }}
author: {{ author|quote_yaml }}
date: {{ date|quote_yaml }}
format:
  html:
    embed-resources: true
    standalone: true
    {% if use_unhcr_theme %}
    theme:
      - unhcr
      - cosmo
    css: unhcr.css
    {% else %}
    theme: cosmo
    {% endif %}
  pdf:
    documentclass: article
    papersize: a4
    geometry:
      - top=30mm
      - left=20mm
      - right=20mm
      - bottom=30mm

# Store metadata in YAML - only visible in source
unhcr_metadata:
  {% if metadata.get('audience') %}
  audience: {{ metadata.audience|quote_yaml }}
  {% endif %}
  {% if metadata.get('document_type') %}
  document_type: {{ metadata.document_type|quote_yaml }}
  {% endif %}
  analysis_id: {{ metadata.get('analysis_id', '')|quote_yaml }}
  generated: {{ timestamp|quote_yaml }}
  tool_sequence: {{ metadata.get('tool_sequence', [])|tojson|quote_yaml }}
  
original_query: {{ original_query|quote_yaml }}
source: UNHCR Statistics Copilot

error: visual
engine: jupyter
---

# Title
# {{ title }}

{{ story_content | safe }}

{# Code cells - hidden in rendered output #}
{%- if include_code_cells and python_code %}
```{python}
#| echo: false
#| fold: true
{{ python_code | safe }}
```
{% endif %}
```

### Priority 2: Integrate Unused Tools (High)

#### Integration 2.1: Update `generate_comprehensive_quarto_analysis`

**File:** `backend/chat.py`  
**Function:** `generate_comprehensive_quarto_analysis()`  

**Add the following integration points:**

```python
async def generate_comprehensive_quarto_analysis(
    question: str,
    origin: str = None,
    destination: str = None,
    topic: str = None,
    timespan: str = None,
    audience: str = "internal",
    document_type: str = "long_read",
    style: str = "formal"
) -> dict:
    """Generate a complete Quarto notebook with full tool pipeline."""
    
    try:
        # Enhanced tool tracking
        tool_sequence = []
        
        # Helper for direct tool calls
        async def call_tool_directly(tool_name, arguments):
            # ... existing code ...
        
        # 1. Tool selection
        selection = await call_tool_directly(
            "safe_tool_selection", 
            {"question": question}
        )
        
        # 2. Get data
        arguments = selection.get("arguments", {})
        extracted_params = selection.get("parameters", {})
        arguments.update(extracted_params)
        
        valid_data_params = {
            'coo', 'coa', 'year', 'years', 'population_types', 'population_type',
            'coo_all', 'coa_all', 'audience', 'document_type', 'origin', 
            'destination', 'timespan'
        }
        filtered_arguments = {k: v for k, v in arguments.items() if k in valid_data_params}
        filtered_arguments['question'] = question
        filtered_arguments['audience'] = audience
        filtered_arguments['document_type'] = document_type
        
        data_result = await call_tool_directly("get_data_for_story", filtered_arguments)
        
        # 3. NEW: Apply guardrails
        guardrails_result = None
        if data_result and isinstance(data_result, dict):
            if not (data_result.get("error") or 
                   (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                guardrails_result = await call_tool_directly(
                    "apply_analysis_guardrails",
                    {
                        "analysis_request": {
                            "data_source": "UNHCR MCP",
                            "data_fields": list(data_result.get('items', [{}])[0].keys()) 
                                       if data_result.get('items') else [],
                            "storytelling_context": question,
                            "data": data_result
                        },
                        "detailed_report": True
                    }
                )
        
        # 4. NEW: Extract visualization structure
        viz_structure = None
        if data_result and isinstance(data_result, dict):
            if not (data_result.get("error") or 
                   (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                # Determine visualization type based on data
                viz_type = determine_visualization_type(data_result)
                numeric_cols = detect_numeric_columns(data_result)
                
                viz_structure = await call_tool_directly(
                    "extract_visualization_structure",
                    {
                        "visualization_type": viz_type,
                        "title": f"{question}",
                        "x_axis_label": "Year",  # Default, can be improved
                        "y_axis_label": numeric_cols[0] if numeric_cols else "Count"
                    }
                )
        
        # 5. NEW: Analyze statistics
        statistics_result = None
        if data_result and isinstance(data_result, dict):
            if not (data_result.get("error") or 
                   (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                items = data_result.get('items', [])
                if items:
                    numeric_cols = [k for k, v in items[0].items() 
                                   if isinstance(v, (int, float)) and 
                                   not any(skip in k.lower() for skip in ['id', '_id', 'iso'])]
                    categorical_cols = [k for k, v in items[0].items() 
                                      if isinstance(v, str) and k.lower() not in ['year', 'value', 'count']]
                    
                    statistics_result = await call_tool_directly(
                        "analyze_data_statistics",
                        {
                            "data": items,
                            "numeric_columns": numeric_cols[:5],  # Top 5 numeric
                            "categorical_columns": categorical_cols[:3]  # Top 3 categorical
                        }
                    )
        
        # 6. NEW: Generate visualization description
        viz_description = None
        if viz_structure and statistics_result:
            viz_description = await call_tool_directly(
                "generate_visualization_description",
                {
                    "structure": viz_structure,
                    "statistics": statistics_result,
                    "description_type": "both",
                    "focus_areas": ["trends", "comparisons", "outliers"]
                }
            )
        
        # 7. Generate analytical story (enhanced with pipeline data)
        story_response = None
        if data_result and isinstance(data_result, dict):
            if not (data_result.get("error") or 
                   (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                story_response = await call_tool_directly(
                    "generate_analytical_story",
                    {
                        "data": data_result,
                        "question": question,
                        "audience": audience,
                        "document_type": document_type,
                        "analysis_config": config,
                        # NEW: Include pipeline results
                        "statistics": statistics_result,
                        "guardrails": guardrails_result,
                        "visualization": viz_structure,
                        "description": viz_description
                    }
                )
        
        # 8. Generate Quarto notebook with all pipeline results
        metadata = {
            'audience': audience,
            'document_type': document_type,
            'analysis_config': config,
            'tool_sequence': tool_sequence,
            'statistics': statistics_result,
            'guardrails': guardrails_result,
            'visualization_structure': viz_structure,
            'visualization_description': viz_description
        }
        
        # Extract data for code generation
        notebook_data = extract_data_for_code(data_result)
        
        # Generate unique ID
        analysis_id = str(uuid.uuid4())
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = "_".join(story_title.split()[:10]) if story_title else "analysis"
        quarto_filename = f"{timestamp}_{safe_title}_{analysis_id}.qmd"
        quarto_path = os.path.join(QUARTO_DIR, quarto_filename)
        
        quarto_result = await call_tool_directly(
            "create_quarto_notebook",
            {
                "story_content": story_content,
                "output_path": quarto_path,
                "title": story_title,
                "author": "UNHCR Statistics Copilot",
                "include_code_cells": True,
                "use_unhcr_theme": True,
                "use_unhcr_style": True,
                "metadata": metadata,
                "data": notebook_data,
                "original_query": question,
                "render_html": True,  # Pre-render
                "render_pdf": True   # Pre-render
            }
        )
        
        return {
            'quarto_content': quarto_result.get('content', ''),
            'metadata': metadata,
            'path': quarto_path,
            'html_path': quarto_result.get('html_path'),
            'pdf_path': quarto_result.get('pdf_path'),
            'status': 'success'
        }
    
    except Exception as e:
        logger.exception(f"Error in generate_comprehensive_quarto_analysis: {e}")
        return {
            'error': str(e),
            'status': 'error'
        }
```

### Priority 3: Pre-Rendering Implementation (High)

#### Fix 3.1: Always Pre-Render in create_quarto_notebook_tool

**File:** `backend/mcp/tools/create_quarto_notebook.py`  
**Function:** `create_quarto_notebook_tool()`  

**Changes:**
```python
async def create_quarto_notebook_tool(
    story_content: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    date: Optional[str] = None,
    include_code_cells: bool = False,
    use_unhcr_theme: bool = True,
    use_unhcr_style: bool = True,
    original_query: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    data: Optional[Any] = None,
    render_html: bool = True,  # DEFAULT TO TRUE
    render_pdf: bool = True,   # DEFAULT TO TRUE
) -> dict[str, Any]:
    """
    Create a Quarto notebook from story content.
    
    By default, always pre-renders to HTML and PDF for performance.
    """
    # ... existing code ...
    
    # Always save to file
    if output_path:
        output_dir = Path(output_path).parent
        output_dir.mkdir(parents=True, exist_ok=True)
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(quarto_content)
        
        # Always pre-render if Quarto is available
        render_results = {'html_path': None, 'pdf_path': None, 'errors': []}
        render_results = _render_quarto_file(
            qmd_path=output_path,
            output_dir=output_dir,
            render_html=render_html,
            render_pdf=render_pdf
        )
        
        # Also save render results to history
        if render_results.get('html_path'):
            metadata['html_path'] = render_results['html_path']
        if render_results.get('pdf_path'):
            metadata['pdf_path'] = render_results['pdf_path']
    
    # ... rest of function ...
```

#### Fix 3.2: Save Rendered Files Alongside QMD

**File:** `backend/history.py`  
**Function:** `save_quarto_analysis()`  

**Changes:**
```python
def save_quarto_analysis(quarto_content: str, metadata: dict) -> dict:
    """Save analysis as Quarto file with pre-rendered HTML and PDF."""
    
    # ... existing code ...
    
    # Save metadata with render paths
    if metadata.get('html_path'):
        metadata['rendered_html_path'] = metadata['html_path']
    if metadata.get('pdf_path'):
        metadata['rendered_pdf_path'] = metadata['pdf_path']
    
    # Save to history
    history_filepath = os.path.join(HISTORY_DIR, f"{analysis_id}.json")
    serializable_metadata = _make_serializable(metadata)
    with open(history_filepath, "w", encoding="utf-8") as f:
        json.dump(serializable_metadata, f, indent=2, ensure_ascii=False)
    
    # Return with render paths
    return {
        "filename": filename,
        "filepath": filepath,
        "id": analysis_id,
        "metadata": metadata,
        "html_path": metadata.get('html_path'),
        "pdf_path": metadata.get('pdf_path'),
        "rendered": {
            "html": metadata.get('html_path') is not None,
            "pdf": metadata.get('pdf_path') is not None
        }
    }
```

### Priority 4: Frontend Updates (Medium)

#### Frontend Integration

**Changes:** Update frontend to:
1. Check for pre-rendered HTML/PDF files
2. Serve pre-rendered files directly
3. Fallback to on-demand rendering if pre-rendered files don't exist
4. Display loading state while rendering (if needed)

**API Response Enhancement:**
```json
{
  "id": "analysis_id",
  "question": "...",
  "quarto_path": "/data/quarto_analyses/filename.qmd",
  "html_path": "/data/quarto_analyses/filename.html",
  "pdf_path": "/data/quarto_analyses/filename.pdf",
  "rendered": {
    "html": true,
    "pdf": true
  },
  "status": "success"
}
```

---

## Verification Checklist

### Code Review Verification

- [ ] **Quarto Indentation:** Verify `_generate_data_visualization_code()` generates properly formatted Python code
- [ ] **Text Extraction:** Verify `_extract_text_from_message()` handles all message formats from LLM
- [ ] **Template Syntax:** Verify Quarto template uses correct syntax for hidden code cells
- [ ] **Metadata Storage:** Verify all metadata is stored only in YAML header

### Integration Verification

- [ ] **Tool Registration:** Verify all 5 unused tools are properly registered in MCP server
- [ ] **Tool Calling:** Verify all 5 unused tools are called in the orchestration pipeline
- [ ] **Data Flow:** Verify data flows correctly through all pipeline stages
- [ ] **Error Handling:** Verify errors in any tool don't break the entire pipeline

### Rendering Verification

- [ ] **Pre-Rendering:** Verify Quarto files are automatically rendered to HTML and PDF
- [ ] **File Storage:** Verify rendered files are saved alongside .qmd files
- [ ] **Metadata:** Verify render paths are stored in history metadata
- [ ] **Frontend Integration:** Verify frontend can access pre-rendered files

### Performance Verification

- [ ] **Rendering Time:** Measure time to generate Quarto notebook (should be < 30 seconds)
- [ ] **File Size:** Verify generated files are reasonable size (< 10MB)
- [ ] **Memory Usage:** Verify memory usage is stable during generation
- [ ] **Concurrent Requests:** Verify system can handle multiple concurrent generation requests

---

## Success Criteria

1. **Quarto Generation:** No indentation errors, all narrative included, code hidden in rendered output
2. **Tool Integration:** All 25 MCP tools are called in appropriate contexts
3. **Pre-Rendering:** HTML and PDF files are generated automatically and accessible
4. **Performance:** End-to-end generation time < 30 seconds
5. **Quality:** Generated reports meet UNHCR standards (validated by guardrails)

---

## Files to Modify

### High Priority
1. `/home/edouard/python/unhcr_stat_copilot/backend/mcp/tools/create_quarto_notebook.py`
   - Fix code generation indentation
   - Enhance text extraction
   - Ensure pre-rendering by default

2. `/home/edouard/python/unhcr_stat_copilot/backend/templates/quarto_notebook.j2`
   - Fix code cell visibility
   - Ensure metadata only in YAML header

3. `/home/edouard/python/unhcr_stat_copilot/backend/chat.py`
   - Integrate unused MCP tools
   - Update orchestration pipeline

### Medium Priority
4. `/home/edouard/python/unhcr_stat_copilot/backend/history.py`
   - Save render paths in metadata

5. `/home/edouard/python/unhcr_stat_copilot/frontend/**/*.js` (or relevant frontend files)
   - Use pre-rendered files
   - Update display logic

---

## Dependencies

### Python Packages Required
- `quarto` - For rendering (already used)
- `jinja2` - For templating (already used)
- `pandas` - For data manipulation (already used)
- `matplotlib` - For visualization (already used)
- `seaborn` - For visualization (already used)

### External Tools Required
- Quarto CLI - Must be installed and in PATH

---

## Testing Strategy

1. **Unit Tests:** Test each tool individually with known inputs
2. **Integration Tests:** Test tool pipeline with sample data
3. **End-to-End Tests:** Test complete analysis generation
4. **Regression Tests:** Ensure existing functionality still works
5. **Performance Tests:** Measure generation time and resource usage

---

## Rollout Plan

### Phase 1: Critical Fixes (Day 1-2)
1. Fix Quarto indentation errors
2. Fix narrative extraction
3. Fix code cell visibility
4. Deploy to staging
5. Verify basic functionality

### Phase 2: Tool Integration (Day 3-4)
1. Integrate `analyze_data_statistics`
2. Integrate `apply_analysis_guardrails`
3. Integrate `extract_visualization_structure`
4. Integrate `generate_visualization_description`
5. Deploy to staging
6. Verify pipeline works

### Phase 3: Pre-Rendering (Day 5-6)
1. Implement automatic pre-rendering
2. Update history storage
3. Update frontend integration
4. Deploy to staging
5. Performance testing

### Phase 4: Production (Day 7)
1. Final testing
2. Documentation update
3. Production deployment
4. Monitoring

---

## Monitoring and Metrics

### Key Metrics to Track
1. **Generation Success Rate:** % of analysis requests that succeed
2. **Generation Time:** Average time to generate complete analysis
3. **Tool Usage:** Count of each tool called
4. **Error Rates:** Errors per tool and overall
5. **User Satisfaction:** Feedback on generated reports

### Logging Enhancements
1. Add detailed logging for each pipeline stage
2. Track timing for each tool call
3. Log errors with full context
4. Monitor resource usage

---

## Risks and Mitigation

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Breaking existing functionality | Medium | High | Comprehensive regression testing |
| Performance degradation | Medium | Medium | Performance testing, optimization |
| Tool integration bugs | High | Medium | Incremental integration, unit tests |
| Quarto rendering issues | Medium | High | Test rendering with various data types |
| Memory leaks | Low | Medium | Resource monitoring, stress testing |

---

## Conclusion

This audit identifies critical issues with the current MCP tool orchestration and Quarto generation system. The proposed refactoring addresses:

1. **Immediate bugs:** Indentation errors, missing narrative, visible code cells
2. **Missing features:** 4 unused tools not integrated
3. **Performance:** On-demand rendering instead of pre-rendering
4. **Quality:** Missing statistical analysis and guardrails validation

The refactored architecture provides a complete analysis pipeline that leverages all available tools, produces high-quality reports, and delivers better performance through pre-rendering.

**Recommendation:** Proceed with implementation in phases, starting with critical bug fixes, then tool integration, then performance optimizations.

---

*Document generated by: Mistral Vibe*  
*Co-Authored-By: Mistral Vibe <vibe@mistral.ai>*
