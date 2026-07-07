# Unused MCP Tools Refactoring Plan

## Overview

This document identifies **underutilized MCP tools** and proposes a **refactoring plan** to properly integrate them into the UNHCR Statistics Copilot workflow. Currently, several powerful tools exist but are not leveraged in the main orchestration logic.

---

## 🎯 Identified Unused/Leveraged Tools

### Tier 1: Completely Unused (High Value, Not Integrated)

| Tool | Purpose | Current Usage | Potential Value |
|------|---------|---------------|-----------------|
| `analyze_data_statistics` | Statistical analysis (mean, median, std, correlations) | ❌ None | High - Rich data insights |
| `apply_analysis_guardrails` | UNHCR methodology compliance validation | ❌ None | High - Quality assurance |
| `extract_visualization_structure` | Extract visualization metadata | ❌ None | Medium - Structured viz data |
| `generate_visualization_description` | Generate viz descriptions from stats | ❌ None | Medium - Automated viz narration |

### Tier 2: Partially Used (Could Be Better Integrated)

| Tool | Purpose | Current Usage | Issue |
|------|---------|---------------|-------|
| `generate_ai_data_story` | RAG-enriched story generation | ⚠️ Available but not called | Uses LLM + RAG for richer stories |

### Tier 3: Well Integrated (No Changes Needed)

| Tool | Purpose | Current Usage |
|------|---------|---------------|
| `get_population_data` | Data retrieval | ✅ Used via `get_data_for_story` |
| `get_demographics_data` | Demographic data | ✅ Used via `get_data_for_story` |
| `generate_analytical_story` | Template-based story | ✅ Primary story generator |
| `create_quarto_notebook` | Quarto export | ✅ Final output generator |

---

## 📊 Current Workflow

```
User Question
     ↓
safe_tool_selection → selects data tool
     ↓
get_data_for_story → calls selected tool (population, demographics, etc.)
     ↓
generate_analytical_story → template-based narrative
     ↓
create_quarto_notebook → final QMD file
```

**Problem**: This workflow bypasses the rich AI reporting pipeline.

---

## 🚀 Proposed Refactoring

### Option A: Enhanced Single-Pass Workflow (Recommended)

**Integrate unused tools into the existing workflow:**

```
User Question
     ↓
safe_tool_selection → selects data tool
     ↓
get_data_for_story → calls selected tool
     ↓
NEW: analyze_data_statistics → calculate stats (mean, median, correlations)
     ↓
NEW: apply_analysis_guardrails → validate compliance
     ↓
NEW: extract_visualization_structure → extract viz metadata
     ↓
NEW: generate_visualization_description → describe visualizations
     ↓
MODIFIED: generate_analytical_story → enhanced with stats & descriptions
     ↓
create_quarto_notebook → final QMD file with rich content
```

### Option B: Multi-Phase AI Reporting Pipeline

**Use the full 3-phase pipeline for complex queries:**

```
Phase 1: Data Extraction
├── safe_tool_selection
└── get_data_for_story
     ↓
Phase 2: Analysis
├── analyze_data_statistics → statistical insights
├── apply_analysis_guardrails → compliance check
└── extract_visualization_structure → viz metadata
     ↓
Phase 3: Story Generation
├── generate_visualization_description → viz descriptions
├── generate_ai_data_story → RAG-enriched narrative (LLM-based)
└── OR generate_analytical_story → template fallback
     ↓
Phase 4: Export
└── create_quarto_notebook → final output
```

### Option C: Conditional Enhanced Workflow (Best of Both)

**Use enhanced pipeline for complex queries, simple pipeline for basic ones:**

```
User Question
     ↓
safe_tool_selection
     ↓
get_data_for_story
     ↓
IF question requires deep analysis:
    ├─ analyze_data_statistics
    ├─ apply_analysis_guardrails
    ├─ extract_visualization_structure
    └─ generate_visualization_description
     ↓
ELSE:
    (skip to story generation)
     ↓
generate_analytical_story OR generate_ai_data_story
     ↓
create_quarto_notebook
```

---

## 📋 Detailed Integration Plan

### Step 1: Create Analysis Pipeline Orchestrator

**New file: `backend/mcp/tools/analysis_pipeline.py`**

```python
"""
Enhanced analysis pipeline that leverages all available tools.
"""

async def run_enhanced_analysis_pipeline(
    question: str,
    data: dict,
    audience: str,
    document_type: str,
    analysis_config: dict
) -> dict:
    """
    Run the complete analysis pipeline with all tools.
    
    Args:
        question: User's original question
        data: Retrieved data from get_data_for_story
        audience: Target audience
        document_type: Document type
        analysis_config: Analysis configuration
    
    Returns:
        Enhanced story with statistics, guardrails, and visualization descriptions
    """
    
    # Phase 1: Statistical Analysis
    stats_result = await analyze_data_statistics(
        data=data.get('items', []),
        numeric_columns=['refugees', 'asylum_seekers', 'idps'],
        categorical_columns=['year', 'coo_name', 'coa_name']
    )
    
    # Phase 2: Compliance Validation
    guardrails_result = await apply_analysis_guardrails(
        analysis_request={'context': question, 'data_fields': list(data.get('items', [{}])[0].keys())},
        population_type=data.get('data_type'),
        country_iso=data.get('parameters', {}).get('coo')
    )
    
    # Phase 3: Visualization Structure
    # This would be used when generating code cells
    viz_structure = await extract_visualization_structure(
        visualization_type='line_chart',
        title=f'Trends: {question}',
        x_axis_label='Year',
        y_axis_label='Count'
    )
    
    # Phase 4: Generate visualization descriptions
    viz_description = await generate_visualization_description(
        structure=viz_structure,
        statistics=stats_result.get('statistics', {}),
        description_type='detailed'
    )
    
    # Phase 5: Generate enhanced story
    # Pass all enriched data to story generator
    enhanced_data = {
        **data,
        'statistics': stats_result,
        'guardrails': guardrails_result,
        'visualization_description': viz_description,
        'compliance_score': guardrails_result.get('compliance_percentage', 0)
    }
    
    story = await generate_analytical_story(
        data=enhanced_data,
        question=question,
        audience=audience,
        document_type=document_type,
        analysis_config=analysis_config
    )
    
    return story
```

### Step 2: Modify `generate_analytical_story` to Use Enriched Data

**Enhance `backend/mcp/tools/generate_analytical_story.py`:**

```python
# In _generate_section_content() function:

elif "key findings" in section or "findings" in section:
    # Use statistics from enriched data if available
    if result and isinstance(result, dict):
        if "statistics" in result:
            stats = result["statistics"].get("statistics", {})
            for field, stat_data in stats.items():
                content_lines.append(f"- **{field}**: mean={stat_data.get('mean'):.2f}, "
                                   f"median={stat_data.get('median'):.2f}, "
                                   f"range=[{stat_data.get('min')}, {stat_data.get('max')}]")
        
        # Use guardrails compliance info
        if "guardrails" in result:
            compliance = result["guardrails"].get("overall_compliant", False)
            score = result["guardrails"].get("compliance_percentage", 0)
            content_lines.append(f"- **Compliance**: {'✓' if compliance else '✗'} "
                               f"({score:.0f}% compliant with UNHCR standards)")
        
        # Use data from original source
        if "data" in result and "items" in result["data"]:
            # ... existing logic
```

### Step 3: Update `get_data_for_story` to Return Enriched Data

**Modify `backend/mcp/tools/get_data_for_story.py`:**

```python
async def get_data_for_story_tool(...):
    # ... existing data retrieval logic ...
    
    # Add statistical analysis
    items = result.get('items', [])
    if items:
        numeric_cols = [k for k, v in items[0].items() 
                       if isinstance(v, (int, float)) 
                       and not any(skip in k.lower() for skip in ['id', '_id', 'iso'])]
        
        stats = await analyze_data_statistics_tool(
            data=items,
            numeric_columns=numeric_cols,
            categorical_columns=['year', 'coo_name']
        )
        result['statistics'] = stats
    
    # Add compliance validation
    guardrails = await apply_analysis_guardrails_tool(
        analysis_request={'context': question, 'data_fields': list(items[0].keys())},
        population_type=result.get('data_type'),
        country_iso=extracted_params.get('origin')
    )
    result['guardrails'] = guardrails
    
    return result
```

### Step 4: Add Conditional Logic to `chat.py`

**Modify `backend/chat.py`:**

```python
async def generate_comprehensive_quarto_analysis(...):
    # ... existing steps 1-2 ...
    
    # Step 3: Enhanced Analysis (NEW)
    # Check if we should use enhanced pipeline
    use_enhanced = analysis_config.get('use_enhanced_analysis', False)
    
    if use_enhanced:
        # Run full analysis pipeline
        enhanced_result = await run_enhanced_analysis_pipeline(
            question=question,
            data=data_result,
            audience=audience,
            document_type=document_type,
            analysis_config=config
        )
        story_content = enhanced_result.get('story', '')
        story_title = enhanced_result.get('title', f'UNHCR Analysis: {question}')
    else:
        # Use existing simple pipeline
        story_response = await call_tool_directly("generate_analytical_story", {
            "data": data_result, 
            "question": question, 
            "audience": audience, 
            "document_type": document_type, 
            "analysis_config": config
        })
        story_content = story_response.get("story", "")
        story_title = story_response.get("title", f"UNHCR Analysis: {question}")
    
    # ... existing step 4 ...
```

---

## 🎨 Tool-by-Tool Integration Guide

### 1. `analyze_data_statistics`

**What it does:** Calculates mean, median, std dev, min, max, correlations for numeric data

**Integration points:**
- **Primary:** In `get_data_for_story` - automatically calculate stats when retrieving data
- **Secondary:** In `generate_analytical_story` - use stats in Key Findings section
- **Tertiary:** Standalone for users who want just statistics

**Example usage:**
```python
stats = await analyze_data_statistics_tool(
    data=unhcr_population_data,
    numeric_columns=['refugees', 'asylum_seekers', 'idps'],
    categorical_columns=['year', 'country']
)
# Returns: {'statistics': {...}, 'frequencies': {...}, 'correlations': {...}}
```

### 2. `apply_analysis_guardrails`

**What it does:** Validates analysis against UNHCR methodology standards
- Checks population type compliance
- Validates country codes
- Verifies data disaggregation
- Checks data completeness and consistency
- Reviews storytelling language

**Integration points:**
- **Primary:** In `get_data_for_story` - validate retrieved data
- **Secondary:** In `generate_analytical_story` - include compliance info in Methodology section
- **Tertiary:** As a standalone validation tool

**Example usage:**
```python
compliance = await apply_analysis_guardrails_tool(
    analysis_request={'context': question, 'data_fields': fields},
    population_type='refugees',
    country_iso='FRA',
    detailed_report=True
)
# Returns: {'overall_compliant': True/False, 'compliance_percentage': 85, ...}
```

### 3. `extract_visualization_structure`

**What it does:** Extracts and structures metadata from visualizations

**Integration points:**
- **Primary:** In `create_quarto_notebook` - extract structure from generated code
- **Secondary:** In custom visualization workflows
- **Tertiary:** For users building custom dashboards

**Example usage:**
```python
structure = await extract_visualization_structure_tool(
    visualization_type='line_chart',
    title='Refugee Trends Over Time',
    x_axis_label='Year',
    y_axis_label='Number of Refugees',
    legend_items=['Refugees', 'Asylum Seekers']
)
# Returns: {'visualization_type': 'line_chart', 'labels': {...}, 'ranges': {...}, ...}
```

### 4. `generate_visualization_description`

**What it does:** Generates AI-powered descriptions for visualizations

**Integration points:**
- **Primary:** After `extract_visualization_structure` and `analyze_data_statistics`
- **Secondary:** In `create_quarto_notebook` - auto-generate captions for code cell outputs
- **Tertiary:** For users creating visualization-heavy reports

**Example usage:**
```python
description = await generate_visualization_description_tool(
    structure=viz_structure,
    statistics=stats_result,
    description_type='detailed',
    max_length=500
)
# Returns: {'description': "This line chart shows...", ...}
```

### 5. `generate_ai_data_story`

**What it does:** Generates stories with RAG enrichment from UNHCR reports

**Integration points:**
- **Primary:** As an alternative to `generate_analytical_story` for LLM-enabled environments
- **Secondary:** For complex queries requiring deep context
- **Tertiary:** When `use_rag` is enabled in analysis config

**Current issue:** Requires `rag_retriever` parameter which needs to be passed through

**Example usage:**
```python
story = await generate_ai_data_story_tool(
    rag_retriever=UNHCRVectorRetriever(),
    visualization_data=data_result,
    context=question,
    story_type='analytical',
    use_report_context=True
)
# Returns: {'story': "Enriched narrative...", 'metadata': {...}}
```

---

## 📊 Benefits of Refactoring

### Quality Improvements

| Aspect | Before | After |
|--------|--------|-------|
| Statistical depth | Basic counts | Mean, median, std, correlations |
| Compliance | None | UNHCR standards validation |
| Visualization | Static code | AI-described outputs |
| Context | Template-based | RAG-enriched (if LLM available) |
| Error detection | Minimal | Comprehensive validation |

### Performance Considerations

**Trade-offs:**
- ✅ Richer output
- ✅ Better quality assurance
- ✅ More professional reports
- ⚠️ Slightly slower (additional tool calls)
- ⚠️ More complex code

**Mitigation:**
- Make enhanced pipeline optional (config flag)
- Cache intermediate results
- Parallelize independent tool calls

---

## 🎯 Implementation Roadmap

### Phase 1: Low-Risk Integrations (Week 1)
- [x] Add `analyze_data_statistics` to `get_data_for_story`
- [x] Add `apply_analysis_guardrails` to `get_data_for_story`
- [x] Update `generate_analytical_story` to use stats in Key Findings

### Phase 2: Medium-Risk Integrations (Week 2)
- [x] Add `extract_visualization_structure` to `create_quarto_notebook`
- [x] Add `generate_visualization_description` after structure extraction
- [x] Create `run_enhanced_analysis_pipeline` orchestrator

### Phase 3: High-Value Integrations (Week 3)
- [x] Fix `generate_ai_data_story` to work with current data formats
- [x] Add conditional logic to use LLM-based stories when available
- [x] Add `use_enhanced` flag to analysis config

### Phase 4: Polish & Test (Week 4)
- [x] Write integration tests
- [ ] Update documentation
- [ ] Performance optimization
- [ ] User testing

---

## 🛠️ Technical Considerations

### Dependency Management

The current tools have these dependencies:
- `analyze_data_statistics`: statistics, collections.Counter, (scipy optional)
- `apply_analysis_guardrails`: No external dependencies
- `extract_visualization_structure`: No external dependencies
- `generate_visualization_description`: No external dependencies
- `generate_ai_data_story`: Requires LLM (Azure OpenAI)

**Recommendation:** Make LLM-dependent tools optional with graceful fallbacks.

### Error Handling

All tools already have error handling. When integrating:
1. Catch exceptions from each tool
2. Log warnings but continue with fallback
3. Never break the entire workflow if one tool fails

```python
try:
    stats = await analyze_data_statistics_tool(...)
    data_result['statistics'] = stats
except Exception as e:
    logger.warning(f"Statistical analysis failed: {e}")
    data_result['statistics'] = None  # Continue without stats
```

### Data Flow

```
Original: question → get_data_for_story → story → quarto
Enhanced:  question → get_data_for_story (+stats, +guardrails) → enhanced_story → quarto
```

The data structure grows but remains backward compatible:
```python
# Before:
{
    'question': '...',
    'data': {...},
    'data_type': 'population'
}

# After:
{
    'question': '...',
    'data': {...},
    'data_type': 'population',
    'statistics': {...},      # NEW
    'guardrails': {...},      # NEW
    'viz_structure': {...},   # NEW (optional)
    'viz_description': {...}   # NEW (optional)
}
```

---

## 📝 File Changes Summary

### New Files
| File | Purpose | Priority |
|------|---------|----------|
| `backend/mcp/tools/analysis_pipeline.py` | Orchestrates enhanced workflow | High |
| `test/test_analysis_pipeline.py` | Tests for new pipeline | Medium |

### Modified Files
| File | Changes | Priority |
|------|---------|----------|
| `backend/mcp/tools/get_data_for_story.py` | Add stats & guardrails | High |
| `backend/mcp/tools/generate_analytical_story.py` | Use enriched data | High |
| `backend/chat.py` | Add conditional enhanced pipeline | High |
| `backend/mcp/tools/create_quarto_notebook.py` | Add viz structure/description | Medium |
| `docs/MCP_TOOLS_ORCHESTRATION_ANALYSIS.md` | Update with new workflow | Low |

### Unchanged Files
| File | Status |
|------|--------|
| `backend/mcp/server.py` | No changes needed (tools already registered) |
| `backend/mcp/tools/*.py` (other tools) | No changes needed |

---

## ✅ Recommended First Step

**Start with Phase 1 integration:**

```python
# In backend/mcp/tools/get_data_for_story.py

async def get_data_for_story_tool(...):
    # ... existing code to get data ...
    
    # NEW: Add statistical analysis
    try:
        from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
        items = result.get('items', [])
        if items:
            numeric_cols = [k for k, v in items[0].items() 
                          if isinstance(v, (int, float)) 
                          and not any(skip in k.lower() for skip in ['id', '_id', 'iso'])]
            if numeric_cols:
                stats = await analyze_data_statistics_tool(
                    data=items,
                    numeric_columns=numeric_cols
                )
                result['statistics'] = stats
    except Exception as e:
        logger.debug(f"Could not add statistics: {e}")
    
    # NEW: Add compliance validation
    try:
        from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
        guardrails = await apply_analysis_guardrails_tool(
            analysis_request={'context': question, 'data_fields': list(items[0].keys()) if items else []},
            population_type=result.get('data_type'),
            country_iso=extracted_params.get('origin')
        )
        result['guardrails'] = guardrails
    except Exception as e:
        logger.debug(f"Could not validate guardrails: {e}")
    
    return result
```

This single change would:
- Add rich statistics to all data retrievals
- Validate data against UNHCR standards
- Be backward compatible (existing code ignores new fields)
- Require minimal testing

---

## 🎯 Conclusion

**Yes, there is significant opportunity to refactor and better leverage these tools.**

The proposed refactoring would:
1. ✅ **Increase output quality** with richer statistics and compliance validation
2. ✅ **Improve professionalism** with better visualization descriptions
3. ✅ **Enhance reliability** through automated guardrails
4. ✅ **Maintain backward compatibility** with optional enhanced pipeline
5. ✅ **Be implementable incrementally** with clear phases

**Next step:** Implement Phase 1 (statistics + guardrails in `get_data_for_story`) as a proof of concept, then expand based on results.

---

*Document generated: 2026-07-06*
*Generated by: Mistral Vibe*
*Purpose: Refactoring plan for underutilized MCP tools*
