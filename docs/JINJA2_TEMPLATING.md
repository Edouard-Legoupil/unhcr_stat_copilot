# Jinja2 Templating System Documentation

**UNHCR Statistics Copilot - Template Engine Reference**

*Last Updated: July 2025*
*Version: 1.0*

---

## 📋 Table of Contents

1. [Overview](#-overview)
2. [Template Architecture](#-template-architecture)
3. [Available Templates](#-available-templates)
4. [Template Features](#-template-features)
5. [Template Syntax Guide](#-template-syntax-guide)
6. [Custom Filters](#-custom-filters)
7. [Usage Patterns](#-usage-patterns)
8. [Best Practices](#-best-practices)
9. [Recent Changes](#-recent-changes)
10. [Troubleshooting](#-troubleshooting)

---

## 🎯 Overview

The UNHCR Statistics Copilot uses **Jinja2** as its templating engine to generate structured, reproducible documents from data analysis. This system powers the generation of:

- **Quarto Notebooks** (.qmd files) for data stories and reports
- **Markdown documents** for various audiences
- **Executive summaries** with formatted statistics
- **Technical reports** with embedded code and visualizations
- **Social media content** with optimized formatting

### Why Jinja2?

Jinja2 was selected for its:

1. **Flexibility** - Supports complex conditional logic and loops
2. **Extensibility** - Custom filters and functions can be added
3. **Safety** - Auto-escaping for HTML/XML content
4. **Performance** - Compiled templates for fast rendering
5. **Familiarity** - Widely used in Python ecosystem

### Template Location

All templates are stored in:
```
backend/templates/
```

This directory contains both base templates and specialized templates for different document types.

---

## 🏗️ Template Architecture

### Directory Structure

```
backend/templates/
├── base_quarto.j2              # Base template (extended by others)
├── quarto_notebook.j2           # Standard Quarto notebook template
├── quarto_notebook_interleaved.j2  # NEW: Template with auto-inserted charts
├── executive_summary.j2         # Executive summary format
├── technical_report.j2          # Technical report format
├── long_read.j2                 # Long-form analysis format
├── social_media.j2              # Social media post format
└── linkedin_post.j2             # LinkedIn-specific format
```

### Template Hierarchy

```
base_quarto.j2 (Base)
    │
    ├── executive_summary.j2 (Extends base)
    ├── technical_report.j2 (Extends base)
    ├── long_read.j2 (Extends base)
    └── ... (other specialized templates)

quarto_notebook.j2 (Standalone)
quarto_notebook_interleaved.j2 (Standalone, NEW)
```

### Initialization

The Jinja2 environment is initialized in the `AnalysisOrchestrator` class:

```python
# backend/crewai/agents/orchestrators.py

def _init_jinja2(self):
    """Initialize Jinja2 environment for template rendering."""
    template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
    if os.path.exists(template_dir):
        self.jinja_env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(template_dir),
            autoescape=jinja2.select_autoescape(['html', 'xml'])
        )
    else:
        self.jinja_env = jinja2.Environment(autoescape=False)
        logger.warning(f"Template directory not found: {template_dir}")
```

### Template Loading

Templates are loaded dynamically based on the document type:

```python
# In create_quarto_notebook.py
def _load_template(template_name: str = "quarto_notebook.j2") -> Optional[jinja2.Template]:
    """Load a Jinja2 template from the templates directory."""
    templates_dir = Path(__file__).parent.parent.parent / "templates"
    if not templates_dir.exists():
        logger.warning(f"Templates directory not found at {templates_dir}")
        return None
    
    env = jinja2.Environment(
        loader=jinja2.FileSystemLoader(templates_dir),
        autoescape=False
    )
    return env.get_template(template_name)
```

---

## 📄 Available Templates

### 1. quarto_notebook.j2

**Purpose**: Standard Quarto notebook generation

**Key Features**:
- YAML metadata header with UNHCR-specific fields
- Conditional theme application (UNHCR theme or default)
- PDF and HTML output support
- Hidden code cells in rendered output
- Metadata storage in YAML header

**Use Case**: Default notebook generation for most data stories

### 2. quarto_notebook_interleaved.j2 ⭐ NEW

**Purpose**: Advanced Quarto notebook with automatically inserted charts

**Key Features**:
- **Automatic chart insertion** at key points in the story
- **Intelligent section detection** - inserts visualizations after introductions/overviews
- **Dynamic visualization generation** based on data structure
- **Time series detection** - automatically creates line charts for temporal data
- **Multi-population support** - plots different population types
- **Detailed analysis charts** from visualization structure metadata

**Added**: Commit `8b49833` (July 2025)

**Use Case**: Rich data stories with embedded visualizations

**Example Insertion Logic**:
```jinja2
{# Insert chart after introduction/overview sections #}
{%- if i == 0 and ('introduction' in section.lower() or 'overview' in section.lower() or 'executive' in section.lower() or 'summary' in section.lower()) %}

{# Generate main visualization if data is available #}
{%- if data and data.get('items') %}

## Data Visualization

```{python}
#| label: "Main Visualization"
#| echo: false
#| fold: false
#| fig-height: 8
#| fig-width: 12

import pandas as pd
import matplotlib.pyplot as plt

items = {{ data.items|tojson }}
df = pd.DataFrame(items)

# Auto-detect time series and create appropriate visualization
...
```

{%- endif %}
{%- endif %}
```

### 3. base_quarto.j2

**Purpose**: Base template for extended templates

**Blocks**:
- `content` - Main document content

**Variables**:
- `title` - Document title
- `generated_at` - Generation timestamp
- `audience` - Target audience
- `document_type` - Type of document
- `story_content` - Main narrative content
- `analysis_config` - Analysis configuration
- `metadata` - Complete metadata object

### 4. executive_summary.j2

**Purpose**: Executive summary format

**Extends**: base_quarto.j2

**Features**:
- Key insights section
- Statistics table
- Impact highlights
- Default fallback content

**Variables**:
- `headline` - Main headline
- `insight` - Key insight text
- `statistics` - List of statistic objects
- `impacts` - List of impact objects
- Various fallback variables (total_refugees, trend, etc.)

### 5. technical_report.j2

**Purpose**: Technical report format

**Features**:
- Methodology section
- Data sources
- Detailed findings
- Recommendations

### 6. long_read.j2

**Purpose**: Long-form analysis (1200-3000 words)

**Features**:
- Narrative structure
- Data-driven insights
- Contextual analysis

### 7. social_media.j2

**Purpose**: Social media post format

**Features**:
- Concise formatting
- Hashtag support
- Platform-optimized length

### 8. linkedin_post.j2

**Purpose**: LinkedIn-specific format

**Features**:
- Professional tone
- LinkedIn-specific formatting
- Tag support

---

## ✨ Template Features

### YAML Metadata Generation

All Quarto templates generate comprehensive YAML headers with:

```yaml
---
title: {{ title|quote_yaml }}
author: {{ author|quote_yaml }}
date: {{ date|quote_yaml }}
format:
  html:
    embed-resources: true
    standalone: true
  pdf:
    documentclass: article
    papersize: a4
...
```

### UNHCR-Specific Metadata

Templates embed UNHCR-specific metadata in the YAML header:

```yaml
unhcr_metadata:
  audience: {{ metadata.audience|quote_yaml }}
  document_type: {{ metadata.document_type|quote_yaml }}
  analysis_config: |
    {{ metadata.analysis_config|tojson|indent(4, first=false) }}
  tool_sequence: |
    {{ metadata.tool_sequence|tojson|indent(4, first=false) }}
  statistics: |
    {{ metadata.statistics|tojson|indent(4, first=false) }}
  guardrails: |
    {{ metadata.guardrails|tojson|indent(4, first=false) }}
  visualization_structure: |
    {{ metadata.visualization_structure|tojson|indent(4, first=false) }}
```

### Conditional Theme Support

Templates support both UNHCR-branded and default themes:

```jinja2
{%- if use_unhcr_theme %}
    theme:
      - unhcr
      - cosmo
    css: unhcr.css
{%- else %}
    theme: cosmo
{%- endif %}
```

### Safe Content Handling

All story content is rendered with the `safe` filter to preserve markdown formatting:

```jinja2
{{ story_content | safe }}
```

### Automatic Title Handling

Templates intelligently handle title insertion:

```jinja2
{% if story_content.strip() and not story_content.strip().startswith('#') %}
# {{ title }}

{% endif %}
```

### Code Cell Support

Templates support optional code cell insertion:

```jinja2
{%- if include_code_cells and python_code %}
```{python}
#| echo: false
#| fold: true
#| title: "Data Analysis Code"
{{ python_code | safe }}
```
{% endif %}
```

---

## 🔧 Template Syntax Guide

### Variables

Access variables using double curly braces:

```jinja2
{{ title }}
{{ author }}
{{ story_content | safe }}
```

### Filters

Apply filters with the pipe character:

```jinja2
{{ title | upper }}          # Convert to uppercase
{{ value | int }}            # Convert to integer
{{ text | truncate(100) }}    # Truncate to 100 chars
{{ data | tojson }}          # Convert to JSON
{{ data | tojson | indent(2) }}  # Pretty-print JSON
```

### Conditionals

```jinja2
{% if metadata %}
  {# Content when metadata exists #}
{% endif %}

{% if metadata and metadata.get('audience') %}
  Audience: {{ metadata.audience }}
{% endif %}

{% if use_unhcr_theme %}
  Theme: unhcr
{% else %}
  Theme: cosmo
{% endif %}
```

### Loops

```jinja2
{% for stat in statistics %}
| {{ stat.metric }} | {{ stat.value }} | {{ stat.trend }} |
{% endfor %}
```

### Template Inheritance

```jinja2
{# In child template #}
{% extends "base_quarto.j2" %}

{% block content %}
  {# Custom content here #}
{% endblock %}
```

### Comments

```jinja2
{# This is a comment, not rendered in output #}
```

---

## 🧩 Custom Filters

### YAML Quoting Filter

The `quote_yaml` filter properly quotes strings for YAML output:

```jinja2
{{ title | quote_yaml }}  {# Outputs: "My Title" #}
```

### JSON Conversion

The `tojson` filter converts Python objects to JSON:

```jinja2
{{ data | tojson }}
```

### Indentation

The `indent` filter adds indentation to multi-line strings:

```jinja2
{{ data | tojson | indent(4, first=false) }}
```

### Safe Markdown

The `safe` filter prevents HTML escaping of markdown:

```jinja2
{{ story_content | safe }}
```

---

## 📝 Usage Patterns

### 1. Basic Template Rendering

```python
from jinja2 import Environment, FileSystemLoader

env = Environment(loader=FileSystemLoader('backend/templates'))
template = env.get_template('quarto_notebook.j2')

result = template.render(
    title="Syrian Refugee Trends 2024",
    author="UNHCR Statistics Copilot",
    date="2024-07-07",
    story_content="## Introduction\n\nThis report analyzes...",
    use_unhcr_theme=True,
    include_code_cells=True,
    python_code="import pandas as pd..."
)
```

### 2. Using Helper Functions

The `create_quarto_notebook.py` module provides helper functions:

```python
from backend.mcp.tools.create_quarto_notebook import _load_template, _escape_jinja

template = _load_template("quarto_notebook_interleaved.j2")
if template:
    content = template.render(
        title=title,
        story_content=_escape_jinja(story_content),  # Escape special chars
        data=data,
        metadata=metadata
    )
```

### 3. Escaping Jinja2 Special Characters

To prevent template errors when story content contains Jinja2-like syntax:

```python
def _escape_jinja(text: str) -> str:
    """Escape Jinja2 special characters in text."""
    if not isinstance(text, str):
        return text
    return text.replace('{', '{{ ').replace('}', ' }}').replace('%', '%%')
```

**Note**: The `quarto_notebook_interleaved.j2` template does NOT escape content by default to allow dynamic chart insertion.

---

## ✅ Best Practices

### 1. Always Use `safe` Filter for Markdown

```jinja2
{# Good #}
{{ story_content | safe }}

{# Bad (escapes HTML/markdown) #}
{{ story_content }}
```

### 2. Quote YAML Values

```jinja2
{# Good #}
title: {{ title | quote_yaml }}

{# Bad (may break YAML syntax) #}
title: {{ title }}
```

### 3. Check for None Values

```jinja2
{# Good #}
{%- if metadata.get('audience') and metadata.audience is not none %}
audience: {{ metadata.audience | quote_yaml }}
{%- endif %}

{# Bad (may cause errors) #}
audience: {{ metadata.audience | quote_yaml }}
```

### 4. Use Block Scalar for Multi-line JSON

```jinja2
{# Good - preserves formatting #}
analysis_config: |
  {{ metadata.analysis_config | tojson | indent(4, first=false) }}

{# Less readable #}
analysis_config: {{ metadata.analysis_config | tojson }}
```

### 5. Handle Missing Data Gracefully

```jinja2
{# Good #}
{{ total_refugees | default("N/A", true) }}

{# May show "None" #}
{{ total_refugees }}
```

### 6. Template Naming Convention

- Use lowercase with underscores: `template_name.j2`
- End with `.j2` extension to distinguish from regular files
- Prefix with purpose: `quarto_`, `executive_`, `technical_`, etc.

---

## 🆕 Recent Changes

### Version 1.1 (July 2025)

#### Added: quarto_notebook_interleaved.j2

**Commit**: `8b49833` - "fix: Update CrewAI workflow step counts and add defensive result handling"

**Changes**:
- Added new template with automatic chart insertion
- Intelligent section detection for visualization placement
- Dynamic Python code generation based on data structure
- Support for interleaved charts and narrative

**Purpose**: Enable richer data stories with automatically generated visualizations at appropriate points in the narrative.

**Example**:
```jinja2
{# Split story into sections #}
{% set story_sections = story_content.split('## ') if '## ' in story_content else [story_content] %}

{# Insert charts after introduction sections #}
{%- if i == 0 and ('introduction' in section.lower() or 'overview' in section.lower()) %}
  {# Auto-generate visualization here #}
{%- endif %}
```

### Version 1.0 (June-July 2025)

**Previous Enhancements**:

1. **ba2baa3** - "refactor: update YAML metadata formatting in Quarto notebook template to use block scalar style with proper indentation"
   - Changed from inline JSON to block scalar for better readability
   - Added proper indentation for nested JSON structures

2. **8c61c93** - "fix: prevent error messages from appearing in Quarto notebook YAML metadata"
   - Added None checks for metadata fields
   - Improved error handling in template rendering

3. **0526e1a** - "fix: Remove indent filter from Python code in Quarto template and add original_query parameter"
   - Added support for `original_query` in YAML header
   - Fixed Python code formatting issues

4. **d5706a2, 1c4acb6** - "Fix YAML indentation error in Quarto notebook template"
   - Corrected indentation issues in template structure

---

## 🐛 Troubleshooting

### Common Issues and Solutions

#### 1. Template Not Found Error

**Error**: `TemplateNotFound: quarto_notebook.j2`

**Solution**:
- Verify the template exists in `backend/templates/`
- Check the template name is spelled correctly
- Ensure the Jinja2 environment is initialized with the correct path

```python
# Verify template directory
template_dir = Path(__file__).parent.parent.parent / "templates"
assert template_dir.exists(), f"Templates directory not found: {template_dir}"
```

#### 2. Undefined Variable Error

**Error**: `UndefinedError: 'metadata' is undefined`

**Solution**:
- Always pass all required variables to the template
- Use default values for optional variables
- Check for None values before accessing nested properties

```jinja2
{# Use this pattern #}
{%- if metadata and metadata.get('audience') and metadata.audience is not none %}
  {{ metadata.audience }}
{%- endif %}
```

#### 3. Jinja2 Syntax in Content

**Error**: Template rendering fails because story content contains `{{` or `{%`

**Solution**:
- Use the `_escape_jinja()` function to escape special characters
- Or use a template that doesn't process the content (with `safe` filter)

```python
from backend.mcp.tools.create_quarto_notebook import _escape_jinja

safe_content = _escape_jinja(user_content)
template.render(story_content=safe_content)
```

#### 4. YAML Formatting Issues

**Error**: Invalid YAML generated

**Solution**:
- Use `quote_yaml` filter for string values
- Use block scalar (`|`) for multi-line content
- Validate generated YAML before use

```jinja2
{# Good pattern for multi-line #}
metadata: |
  {{ metadata | tojson | indent(2, first=false) }}
```

#### 5. Jinja2 Not Available

**Error**: `ImportError: jinja2`

**Solution**:
- Install Jinja2: `pip install jinja2`
- The system has fallback to manual string formatting, but templates won't work

---

## 📊 Template Comparison

| Feature | quarto_notebook.j2 | quarto_notebook_interleaved.j2 | executive_summary.j2 |
|---------|-------------------|-------------------------------|-------------------|
| YAML Header | ✅ | ✅ | ✅ (extends base) |
| Code Cells | ✅ | ✅ | ❌ |
| Auto Charts | ❌ | ✅ | ❌ |
| Section Detection | ❌ | ✅ | ❌ |
| Time Series Support | ❌ | ✅ | ❌ |
| Theme Support | ✅ | ✅ | ✅ |
| PDF Output | ✅ | ✅ | ✅ |
| Extends Base | ❌ | ❌ | ✅ |
| Best For | Standard stories | Rich data stories | Executive summaries |

---

## 🎓 Learning Resources

### Jinja2 Documentation

- [Official Jinja2 Documentation](https://jinja.palletsprojects.com/)
- [Template Designer Documentation](https://jinja.palletsprojects.com/en/3.1.x/templates/)

### UNHCR-Specific Examples

See the actual template files in `backend/templates/` for:
- Real-world usage patterns
- UNHCR-specific formatting
- Metadata handling
- Visualization integration

---

## 📞 Support

For issues with the templating system:

1. **Check this documentation** first
2. **Review recent commits** for template-related changes
3. **Examine the template files** directly
4. **Consult the Jinja2 documentation** for syntax questions
5. **Create an issue** with reproducible steps

---

*Documentation maintained by: UNHCR Statistics Copilot Development Team*
*Location: `/docs/JINJA2_TEMPLATING.md`*
*Template Directory: `/backend/templates/`*
