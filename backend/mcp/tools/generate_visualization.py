"""
Tool: generate_visualization
Generate UNHCR-compliant, AI-powered descriptions and interpretations for visualizations.

This MCP tool is intentionally strict about the UNHCR Data Visualization Guidelines
(June 2025) and uses the ``unhcrpyplotstyle`` Matplotlib style package for
chart-branding guidance.
"""

from __future__ import annotations

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)

# -----------------------------------------------------------------------------
# UNHCR Data Visualization Guidelines — June 2025 constants
# -----------------------------------------------------------------------------

UNHCR_PRIMARY_BLUE = "#0072BC"
UNHCR_COPYRIGHT = "© UNHCR, The UN Refugee Agency"

UNHCR_DATA_COLOURS: dict[str, str] = {
    "blue": "#0072BC",
    "yellow": "#FFC740",
    "green": "#32C189",
    "cyan": "#6CD8FD",
    "red": "#D25A45",
    "purple": "#A097E3",
    "brown": "#7C3C36",
    "grey": "#BFBFBF",
    "black": "#000000",
    "white": "#FFFFFF",
}

UNHCR_TEXT_AAA_COLOURS: dict[str, str] = {
    "blue": "#05568B",
    "yellow": "#684D0B",
    "green": "#1F5741",
    "cyan": "#0B5269",
    "red": "#683229",
    "purple": "#403C5D",
    "brown": "#7C3C36",
    "grey": "#4D4D4D",
}

UNHCR_SEQUENTIAL_RAMPS: dict[str, list[str]] = {
    "blue": ["#CDE3F1", "#8FC1E1", "#4F9ED0", "#0072BC", "#05568B", "#0B3754"],
    "red": ["#FCE2DE", "#F9B3A7", "#F67F6A", "#D25A45", "#9C4637", "#683229"],
    "yellow": ["#FEF1D1", "#FFC740", "#E4A202", "#B98405", "#8F6808", "#684D0B"],
    "green": ["#DAF6EB", "#7DE0B9", "#32C189", "#2B9C70", "#257958", "#1F5741"],
    "cyan": ["#D4F3FE", "#6CD8FD", "#01B6F2", "#0493C2", "#087295", "#0B5269"],
    "purple": ["#E7E5F7", "#C3BEED", "#A097E3", "#7E74C2", "#5E578E", "#403C5D"],
    "brown": ["#EAD9D8", "#D3AFAB", "#BC8580", "#A65B54", "#7C3C36", "#482724"],
    "grey": ["#E5E5E5", "#BFBFBF", "#999999", "#737373", "#4D4D4D", "#262626"],
}

UNHCR_CATEGORICAL_PALETTES: dict[int, list[str]] = {
    1: ["#0072BC"],
    2: ["#0072BC", "#D25A45"],
    3: ["#0072BC", "#FFC740", "#32C189"],
    4: ["#0072BC", "#FFC740", "#32C189", "#6CD8FD"],
    5: ["#0072BC", "#FFC740", "#32C189", "#6CD8FD", "#D25A45"],
    6: ["#0072BC", "#FFC740", "#32C189", "#D25A45", "#A097E3", "#7C3C36"],
}

UNHCR_REGION_COLOURS: dict[str, str] = {
    "Asia and the Pacific": "#32C189",
    "East and Horn of Africa and the Great Lakes": "#0072BC",
    "The Americas": "#6CD8FD",
    "West and Central Africa": "#D25A45",
    "Middle East and North Africa": "#FFC740",
    "Europe": "#A097E3",
}

UNHCR_POPULATION_TYPE_COLOURS: dict[str, str] = {
    "Refugees": "#0072BC",
    "Internally Displaced People": "#32C189",
    "IDPs": "#32C189",
    "Asylum-seekers": "#6CD8FD",
    "Other people in need of international protection": "#D25A45",
    "UNRWA Refugees": "#A097E3",
    "Palestine refugees under UNRWA’s mandate": "#A097E3",
    "Forcibly Displaced People": "#FFC740",
    "Stateless People": "#0072BC",
    "Returned Refugees and IDPs": "#A097E3",
    "Others of Concern": "#BFBFBF",
}

UNHCR_GENDER_COLOURS: dict[str, str] = {
    "Male": "#0072BC",
    "Female": "#6CD8FD",
    "Non-binary": "#32C189",
    "Neutral": "#32C189",
}

UNHCR_APPROVED_FONTS = ["Lato", "Proxima Nova", "Arial"]

# ``unhcrpyplotstyle`` style names are chart-specific Matplotlib stylesheets.
UNHCR_STYLE_BY_CHART_TYPE: dict[str, str] = {
    "area": "area",
    "area chart": "area",
    "bar": "bar",
    "bar chart": "bar",
    "bubble": "bubble",
    "bubble chart": "bubble",
    "column": "column",
    "column chart": "column",
    "connected scatterplot": "connected_scatterplot",
    "donut": "donut",
    "donut chart": "donut",
    "dot plot": "dotplot",
    "dotplot": "dotplot",
    "heatmap": "heatmap",
    "histogram": "histogram",
    "line": "line",
    "line chart": "line",
    "line column": "linecolumn",
    "line column chart": "linecolumn",
    "lollipop": "lollipop",
    "lollipop chart": "lollipop",
    "map": "map",
    "pie": "pie",
    "pie chart": "pie",
    "population pyramid": "population_pyramid",
    "scatterplot": "scatterplot",
    "scatter plot": "scatterplot",
    "slope": "slope",
    "slope chart": "slope",
    "stream graph": "streamgraph",
    "streamgraph": "streamgraph",
    "treemap": "treemap",
}

UNHCR_RECOMMENDED_CHART_TYPES = {
    "change_over_time": ["line chart", "area chart", "stacked area chart", "stream graph", "line column chart", "slope chart", "dot plot"],
    "comparison": ["bar chart", "column chart", "grouped bar chart", "grouped column chart", "stacked bar chart", "stacked column chart"],
    "correlation": ["bubble chart", "connected scatterplot", "heatmap", "scatterplot", "tree diagram", "venn diagram"],
    "distribution": ["histogram", "population pyramid", "boxplot"],
    "part_to_a_whole": ["100% stacked column chart", "donut chart", "grid plot", "pie chart", "treemap", "waterfall"],
    "ranking": ["ordered column chart", "lollipop chart", "slope chart", "ordered bar chart"],
    "flow": ["sankey diagram", "chord diagram", "flow map", "arc diagram", "flow diagram"],
    "geospatial": ["choropleth map", "bubble map", "flow map", "icon map", "dot density map", "pie chart map"],
}


def _normalise_chart_type(value: Any) -> str:
    return str(value or "").strip().lower().replace("_", " ")


def get_unhcrpyplotstyle_names(visualization_type: str) -> list[str]:
    """Return the Matplotlib styles that must be applied for a UNHCR chart."""
    chart_style = UNHCR_STYLE_BY_CHART_TYPE.get(_normalise_chart_type(visualization_type))
    return ["unhcrpyplotstyle", chart_style] if chart_style else ["unhcrpyplotstyle"]


def apply_unhcrpyplotstyle(plt: Any, visualization_type: str) -> list[str]:
    """
    Apply UNHCR Matplotlib styles using the ``unhcrpyplotstyle`` package.

    This helper is safe for MCP runtimes: it imports the package to register the
    style sheets, applies the base style plus the chart-specific style when
    available, and returns the exact style names applied.
    """
    import unhcrpyplotstyle  # noqa: F401  # imported for Matplotlib style registration

    styles = get_unhcrpyplotstyle_names(visualization_type)
    plt.style.use(styles)
    return styles


def _recommended_palette(structure: dict[str, Any]) -> dict[str, Any]:
    variable_type = str(structure.get("variable_type", "categorical")).lower()
    categories = structure.get("categories") or structure.get("series") or []
    category_count = len(categories) if isinstance(categories, list) else int(structure.get("category_count", 0) or 0)
    grouping = str(structure.get("special_category", "")).lower()

    if grouping in {"unhcr regions", "regions", "region"}:
        return {"type": "special_unhcr_regions", "colours": UNHCR_REGION_COLOURS}
    if grouping in {"population type", "population_type", "population"}:
        return {"type": "special_population_type", "colours": UNHCR_POPULATION_TYPE_COLOURS}
    if grouping in {"gender", "sex"}:
        return {"type": "special_gender", "colours": UNHCR_GENDER_COLOURS}
    if variable_type in {"numeric", "ordered", "ordinal", "continuous", "sequential"}:
        ramp_name = str(structure.get("colour_ramp", "blue")).lower()
        return {"type": "sequential", "ramp": ramp_name, "colours": UNHCR_SEQUENTIAL_RAMPS.get(ramp_name, UNHCR_SEQUENTIAL_RAMPS["blue"])}
    if variable_type == "diverging":
        return {"type": "diverging", "colours": ["#0072BC", "#4F9ED0", "#8FC1E1", "#CDE3F1", "#F5F5F5", "#FEF1D1", "#FFC740", "#E4A202", "#B98405"]}

    palette_size = min(max(category_count, 1), 6)
    return {
        "type": "categorical",
        "max_recommended_categories": 6,
        "category_count": category_count,
        "colours": UNHCR_CATEGORICAL_PALETTES[palette_size],
    }


def _sentence_case_title(text: str) -> bool:
    """Heuristic: the first alphabetic character should be uppercase."""
    stripped = text.strip()
    return bool(stripped) and stripped[0].isupper()


def _validate_guideline_compliance(structure: dict[str, Any]) -> dict[str, Any]:
    issues: list[str] = []
    warnings: list[str] = []
    recommendations: list[str] = []

    title = str(structure.get("title", "")).strip()
    subtitle = str(structure.get("subtitle", "")).strip()
    viz_type = _normalise_chart_type(structure.get("visualization_type", ""))
    font = str(structure.get("font", "Lato")).strip()
    source = str(structure.get("source", "")).strip()
    copyright_text = str(structure.get("copyright", UNHCR_COPYRIGHT)).strip()
    has_data_labels = bool(structure.get("has_data_labels", structure.get("data_labels", False)))
    has_gridlines = bool(structure.get("has_gridlines", structure.get("gridlines", False)))
    has_axis_labels = bool(structure.get("has_axis_labels", structure.get("axis_labels", False)))

    if not title:
        issues.append("Add a short chart title with the first word capitalized.")
    elif not _sentence_case_title(title):
        issues.append("Capitalize the first word of the chart title.")

    if subtitle and not _sentence_case_title(subtitle):
        issues.append("Capitalize the first word of the subtitle.")

    if font not in UNHCR_APPROVED_FONTS:
        issues.append("Use Lato as the primary chart font; Proxima Nova or Arial are acceptable fallbacks.")
    elif font != "Lato":
        warnings.append("Lato is recommended for chart numerals and readability; accepted fallback detected.")

    if not source:
        issues.append("Add a source line, e.g. 'Source: UNHCR Refugee Data Finder'.")

    if copyright_text != UNHCR_COPYRIGHT:
        warnings.append(f"Use the standard copyright wording: '{UNHCR_COPYRIGHT}'.")

    if has_data_labels and (has_gridlines or has_axis_labels):
        issues.append("Do not combine data labels with axis labels/gridlines; use one approach to avoid congestion.")

    category_count = int(structure.get("category_count", 0) or 0)
    categories = structure.get("categories") or structure.get("series") or []
    if isinstance(categories, list):
        category_count = max(category_count, len(categories))
    special_category = str(structure.get("special_category", "")).lower()
    variable_type = str(structure.get("variable_type", "categorical")).lower()
    if variable_type == "categorical" and category_count > 6 and special_category not in {"unhcr regions", "regions", "region", "population type", "population", "gender", "sex"}:
        warnings.append("Use no more than six categorical colours; consolidate groups or split into multiple charts unless this is a UNHCR special category.")

    if viz_type and viz_type not in UNHCR_STYLE_BY_CHART_TYPE:
        # Some recommended chart types do not have a package style, e.g. Sankey.
        all_recommended = {chart for charts in UNHCR_RECOMMENDED_CHART_TYPES.values() for chart in charts}
        if viz_type not in all_recommended:
            recommendations.append("Select a chart type listed in the UNHCR chart-type taxonomy when possible.")
        else:
            warnings.append("This chart type is guideline-recognised but may not have a dedicated unhcrpyplotstyle stylesheet; use the base style and guideline colours.")

    if not structure.get("top_bar", True):
        recommendations.append("Consider using the optional UNHCR blue top bar for branded outputs.")

    palette = _recommended_palette(structure)
    style_names = get_unhcrpyplotstyle_names(viz_type)

    return {
        "compliant": not issues,
        "issues": issues,
        "warnings": warnings,
        "recommendations": recommendations,
        "required_font": "Lato",
        "approved_font_fallbacks": UNHCR_APPROVED_FONTS[1:],
        "primary_colour": UNHCR_PRIMARY_BLUE,
        "recommended_palette": palette,
        "matplotlib_styles": style_names,
        "required_source": bool(source),
        "required_copyright": UNHCR_COPYRIGHT,
        "chart_element_rule": "Use data labels OR axis labels/gridlines, not both.",
    }


def _build_style_code_snippet(structure: dict[str, Any]) -> str:
    viz_type = structure.get("visualization_type", "")
    styles = get_unhcrpyplotstyle_names(viz_type)
    return (
        "import matplotlib.pyplot as plt\n"
        "import unhcrpyplotstyle  # registers UNHCR Matplotlib style sheets\n"
        f"plt.style.use({styles!r})\n"
        "# Then draw the chart and add Source + © UNHCR, The UN Refugee Agency."
    )


async def generate_visualization_tool(
    structure: dict[str, Any],
    statistics: Optional[dict[str, Any]] = None,
    description_type: str = "both",
    max_length: int = 300,
    focus_areas: Optional[list[str]] = None,
) -> dict[str, Any]:
    """
    Generate UNHCR-compliant descriptions for visualizations.

    The response includes:
      - a concise narrative description;
      - strict guideline-compliance checks;
      - the exact ``unhcrpyplotstyle`` Matplotlib styles to apply;
      - approved UNHCR palettes and chart-element recommendations.
    """
    try:
        # Handle None statistics by using empty dict
        if statistics is None:
            statistics = {}
        
        compliance = _validate_guideline_compliance(structure)

        try:
            from backend.llm import generate_visualization_narrative

            description = await generate_visualization_narrative(
                structure=structure,
                statistics=statistics,
                description_type=description_type,
                max_length=max_length,
                focus_areas=focus_areas,
            )
        except Exception as e:
            logger.debug("LLM visualization description failed: %s; falling back to template", e)
            description = _generate_description_from_template(
                structure, statistics, description_type, max_length, focus_areas, compliance
            )

        if not description:
            description = _generate_description_from_template(
                structure, statistics, description_type, max_length, focus_areas, compliance
            )

        return {
            "description": description,
            "description_type": description_type,
            "length": len(description),
            "guideline_compliance": compliance,
            "unhcrpyplotstyle": {
                "required": True,
                "styles": compliance["matplotlib_styles"],
                "code_snippet": _build_style_code_snippet(structure),
            },
            "metadata": {
                "source": "UNHCR AI Visualization Analysis",
                "phase": "description_generation",
                "guidelines": "UNHCR Data Visualization Guidelines, June 2025",
                "brand_copyright": UNHCR_COPYRIGHT,
            },
            "status": "success" if compliance["compliant"] else "needs_revision",
        }
    except Exception as e:
        logger.exception("Failed to generate visualization description")
        return {
            "error": f"Failed to generate visualization description: {str(e)}",
            "status": "error",
        }


def _generate_description_from_template(
    structure: dict[str, Any],
    statistics: dict[str, Any],
    description_type: str,
    max_length: int,
    focus_areas: Optional[list[str]],
    compliance: Optional[dict[str, Any]] = None,
) -> str:
    """Generate a UNHCR-compliant visualization description using templates."""
    parts: list[str] = []

    title = structure.get("title")
    subtitle = structure.get("subtitle")
    viz_type = structure.get("visualization_type", "chart")
    source = structure.get("source")

    if title:
        parts.append(f"**{title}**")
    if subtitle:
        parts.append(str(subtitle))

    styles = get_unhcrpyplotstyle_names(str(viz_type))
    parts.append(
        f"This {viz_type} should use the UNHCR Matplotlib style {' + '.join(styles)} "
        "with Lato typography and the approved UNHCR data-colour palette."
    )

    if statistics:
        insights: list[str] = []
        if "mean" in statistics:
            insights.append(f"average {statistics['mean']}")
        if "median" in statistics:
            insights.append(f"median {statistics['median']}")
        if "min" in statistics and "max" in statistics:
            insights.append(f"range {statistics['min']}–{statistics['max']}")
        elif "min" in statistics:
            insights.append(f"minimum {statistics['min']}")
        elif "max" in statistics:
            insights.append(f"maximum {statistics['max']}")
        if "std" in statistics:
            insights.append(f"standard deviation {statistics['std']}")
        if insights:
            parts.append("Key statistical insights: " + "; ".join(insights) + ".")

    if focus_areas:
        parts.append("Focus areas: " + ", ".join(focus_areas) + ".")

    if source:
        parts.append(f"Source: {source}.")
    parts.append(UNHCR_COPYRIGHT)

    if compliance and not compliance.get("compliant"):
        parts.append("Revision needed: " + " ".join(compliance.get("issues", [])))

    description = " ".join(parts)
    if len(description) > max_length:
        description = description[: max(0, max_length - 3)].rstrip() + "..."
    return description
