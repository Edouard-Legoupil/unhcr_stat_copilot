"""
MCP Tools Package for UNHCR Statistics Copilot

This package contains all the tool implementations for the UNHCR MCP server.
Each tool is implemented in a separate module and exported here.
"""

# Import semantic constants (for validation across tools)
from backend.mcp.tools.semantic_constants import (
    VALID_POPULATION_TYPES,
    VALID_POPULATION_TYPES_SET,
    POPULATION_TYPE_DEFINITIONS,
    FORBIDDEN_IDENTIFIER_FIELDS,
    FIELD_LABEL_MAPPING,
    is_valid_population_type,
    is_identifier_field,
    validate_population_type,
    get_field_label,
    semantic_safeguard,
)

# Import all tool functions
from backend.mcp.tools.retrieve_report_context import retrieve_report_context_tool
from backend.mcp.tools.safe_tool_selection import safe_tool_selection_tool
from backend.mcp.tools.get_data_for_story import get_data_for_story_tool

from backend.mcp.tools.get_population_data import get_population_data_tool
from backend.mcp.tools.get_demographics_data import get_demographics_data_tool
from backend.mcp.tools.get_rsd_applications import get_rsd_applications_tool
from backend.mcp.tools.get_rsd_decisions import get_rsd_decisions_tool
from backend.mcp.tools.get_solutions import get_solutions_tool
from backend.mcp.tools.get_country_key_figures import get_country_key_figures_tool
from backend.mcp.tools.get_population_trends import get_population_trends_tool
from backend.mcp.tools.get_demographic_breakdown import get_demographic_breakdown_tool

from backend.mcp.tools.extract_visualization_structure import extract_visualization_structure_tool
from backend.mcp.tools.get_suggested_questions import get_suggested_questions_tool

from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
from backend.mcp.tools.get_usage_guidance import get_usage_guidance_tool
from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool

from backend.mcp.tools.generate_visualization import generate_visualization_tool
from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool

from backend.mcp.tools.analysis_pipeline import run_enhanced_analysis_pipeline, run_conditional_analysis_pipeline

__all__ = [
    # Semantic constants for validation
    'VALID_POPULATION_TYPES',
    'VALID_POPULATION_TYPES_SET',
    'POPULATION_TYPE_DEFINITIONS',
    'FORBIDDEN_IDENTIFIER_FIELDS',
    'FIELD_LABEL_MAPPING',
    'is_valid_population_type',
    'is_identifier_field',
    'validate_population_type',
    'get_field_label',
    'semantic_safeguard',
    # Tool functions
    'retrieve_report_context_tool',
    'get_population_data_tool',
    'get_demographics_data_tool',
    'get_rsd_applications_tool',
    'get_rsd_decisions_tool',
    'get_solutions_tool',
    'get_country_key_figures_tool',
    'get_population_trends_tool',
    'get_demographic_breakdown_tool',
    'extract_visualization_structure_tool',
    'analyze_data_statistics_tool',
    'generate_visualization_tool',
    'get_usage_guidance_tool',
    'get_suggested_questions_tool',
    'apply_analysis_guardrails_tool',
    'create_quarto_notebook_tool',
    'safe_tool_selection_tool',
    'get_data_for_story_tool',
    'generate_analytical_story_tool',
]
