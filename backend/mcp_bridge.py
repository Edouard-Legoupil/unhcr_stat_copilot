import asyncio
import json
import logging
import os
import re
import time
from typing import Any, Dict, Optional

from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

# Configuration from environment variables
MCP_TIMEOUT = int(os.getenv("MCP_TIMEOUT_SECONDS", "30"))
MCP_MAX_RETRIES = int(os.getenv("MCP_MAX_RETRIES", "3"))


def get_mcp_server_url() -> str:
    """
    Get the MCP server URL, preferring internal container address when in Azure.
    Falls back to MCP_SERVER_URL env var if explicitly set (for external MCP servers).
    """
    # Check if we're in a container with a specific port
    port = os.getenv("WEBSITES_PORT") or os.getenv("PORT", "8000")
    
    # Use explicit MCP_SERVER_URL if set (for external MCP servers or overrides)
    explicit_url = os.getenv("MCP_SERVER_URL")
    if explicit_url:
        return explicit_url
    
    # Default to internal container endpoint
    return f"http://localhost:{port}/mcp/"


MCP_URL = get_mcp_server_url()

logger = logging.getLogger(__name__)


class MCPConnectionError(Exception):
    """Raised when MCP server is unavailable or connection fails."""
    pass


class MCPToolError(Exception):
    """Raised when an MCP tool call fails."""
    pass


class MCPValidationError(Exception):
    """Raised when MCP tool arguments fail validation."""
    pass


# Known MCP tools and their expected parameters
MCP_TOOL_SCHEMAS: Dict[str, Dict[str, Any]] = {
    "get_population_data": {
        "required": [],
        "optional": ["coo", "coa", "year", "coo_all", "coa_all"],
        "types": {
            "coo": str,
            "coa": str,
            "year": (str, int),
            "coo_all": bool,
            "coa_all": bool
        }
    },
    "get_demographics_data": {
        "required": [],
        "optional": ["coo", "coa", "year", "coo_all", "coa_all", "pop_type"],
        "types": {
            "coo": str,
            "coa": str,
            "year": (str, int),
            "coo_all": bool,
            "coa_all": bool,
            "pop_type": bool
        }
    },
    "get_rsd_applications": {
        "required": [],
        "optional": ["coo", "coa", "year", "coo_all", "coa_all"],
        "types": {
            "coo": str,
            "coa": str,
            "year": (str, int),
            "coo_all": bool,
            "coa_all": bool
        }
    },
    "get_rsd_decisions": {
        "required": [],
        "optional": ["coo", "coa", "year", "coo_all", "coa_all"],
        "types": {
            "coo": str,
            "coa": str,
            "year": (str, int),
            "coo_all": bool,
            "coa_all": bool
        }
    },
    "get_solutions": {
        "required": [],
        "optional": ["coo", "coa", "year", "coo_all", "coa_all"],
        "types": {
            "coo": str,
            "coa": str,
            "year": (str, int),
            "coo_all": bool,
            "coa_all": bool
        }
    },
    "get_country_key_figures": {
        "required": [],
        "optional": ["coa", "coo", "year", "population_types"],
        "types": {
            "coa": str,
            "coo": str,
            "year": (str, int),
            "population_types": list
        }
    },
    "get_population_trends": {
        "required": [],
        "optional": ["coa", "coo", "years", "population_types"],
        "types": {
            "coa": str,
            "coo": str,
            "years": str,
            "population_types": list
        }
    },
    "get_demographic_breakdown": {
        "required": [],
        "optional": ["coa", "coo", "year", "population_type"],
        "types": {
            "coa": str,
            "coo": str,
            "year": (str, int),
            "population_type": str
        }
    },
    "retrieve_report_context": {
        "required": ["request"],
        "optional": ["top_k", "fetch_k", "year", "report_type", "section_contains", "exclude_figures_tables", "rerank"],
        "types": {
            "request": str,
            "top_k": int,
            "fetch_k": int,
            "year": str,
            "report_type": str,
            "section_contains": str,
            "exclude_figures_tables": bool,
            "rerank": bool
        }
    },
    "extract_visualization_structure": {
        "required": ["visualization_type"],
        "optional": ["title", "subtitle", "x_axis_label", "y_axis_label", "x_axis_range", "y_axis_range", "legend_items", "geometric_layers"],
        "types": {
            "visualization_type": str,
            "title": str,
            "subtitle": str,
            "x_axis_label": str,
            "y_axis_label": str,
            "x_axis_range": list,
            "y_axis_range": list,
            "legend_items": list,
            "geometric_layers": list
        }
    },
    "analyze_data_statistics": {
        "required": ["data", "numeric_columns"],
        "optional": ["categorical_columns", "correlation_columns"],
        "types": {
            "data": list,
            "numeric_columns": list,
            "categorical_columns": list,
            "correlation_columns": list
        }
    },
    "generate_visualization_description": {
        "required": ["structure", "statistics"],
        "optional": ["description_type", "max_length", "focus_areas"],
        "types": {
            "structure": dict,
            "statistics": dict,
            "description_type": str,
            "max_length": int,
            "focus_areas": list
        }
    },
    "generate_ai_data_story": {
        "required": ["visualization_data"],
        "optional": ["context", "story_type", "max_tokens", "apply_guardrails", "use_report_context", "rag_top_k", "rag_fetch_k", "rag_rerank", "rag_year", "rag_report_type", "rag_section_contains", "rag_exclude_figures_tables"],
        "types": {
            "visualization_data": dict,
            "context": str,
            "story_type": str,
            "max_tokens": int,
            "apply_guardrails": bool,
            "use_report_context": bool,
            "rag_top_k": int,
            "rag_fetch_k": int,
            "rag_rerank": bool,
            "rag_year": str,
            "rag_report_type": str,
            "rag_section_contains": str,
            "rag_exclude_figures_tables": bool
        }
    },
    "get_usage_guidance": {
        "required": [],
        "optional": ["tool_category", "specific_tool"],
        "types": {
            "tool_category": str,
            "specific_tool": str
        }
    },
    "get_suggested_questions": {
        "required": [],
        "optional": ["topic", "data_type", "limit"],
        "types": {
            "topic": str,
            "data_type": str,
            "limit": int
        }
    },
    "apply_analysis_guardrails": {
        "required": ["analysis_request"],
        "optional": ["population_type", "country_iso", "year", "detailed_report"],
        "types": {
            "analysis_request": dict,
            "population_type": str,
            "country_iso": str,
            "year": (str, int),
            "detailed_report": bool
        }
    },
    "create_quarto_notebook": {
        "required": ["story_content"],
        "optional": ["output_path", "title", "author", "date", "include_code_cells", "use_unhcr_theme", "use_unhcr_style", "original_query", "metadata", "data"],
        "types": {
            "story_content": str,
            "output_path": str,
            "title": str,
            "author": str,
            "date": str,
            "include_code_cells": bool,
            "use_unhcr_theme": bool,
            "use_unhcr_style": bool,
            "original_query": str,
            "metadata": dict,
            "data": (dict, list)
        }
    },
    "safe_tool_selection": {
        "required": ["question"],
        "optional": [],
        "types": {
            "question": str
        }
    },
    "get_data_for_story": {
        "required": ["question"],
        "optional": ["coo", "coa", "year", "years", "population_types", "coo_all", "coa_all", "pop_type", "audience", "document_type"],
        "types": {
            "question": str,
            "coo": str,
            "coa": str,
            "year": (str, int),
            "years": str,
            "population_types": list,
            "coo_all": bool,
            "coa_all": bool,
            "pop_type": bool,
            "audience": str,
            "document_type": str
        }
    },
    "generate_analytical_story": {
        "required": [],
        "optional": ["result", "data", "question", "audience", "document_type", "analysis_config"],
        "types": {
            "result": dict,
            "data": dict,
            "question": str,
            "audience": str,
            "document_type": str,
            "analysis_config": dict
        }
    },
}


def validate_tool_arguments(tool_name: str, arguments: Dict[str, Any]) -> None:
    """
    Validate arguments for a specific MCP tool.
    
    Args:
        tool_name: Name of the MCP tool
        arguments: Dictionary of arguments to validate
        
    Raises:
        MCPValidationError: If validation fails
    """
    if tool_name not in MCP_TOOL_SCHEMAS:
        # Unknown tool - fail strictly
        raise MCPValidationError(f"Unknown MCP tool: '{tool_name}'. Available tools: {list(MCP_TOOL_SCHEMAS.keys())}")
    
    schema = MCP_TOOL_SCHEMAS[tool_name]
    
    # Check required arguments
    for required_arg in schema.get("required", []):
        if required_arg not in arguments:
            raise MCPValidationError(
                f"Missing required argument '{required_arg}' for tool '{tool_name}'"
            )
    
    # Check argument types
    types = schema.get("types", {})
    for arg_name, arg_value in arguments.items():
        if arg_name in types:
            expected_type = types[arg_name]
            if isinstance(expected_type, tuple):
                # Multiple allowed types
                if not isinstance(arg_value, expected_type):
                    raise MCPValidationError(
                        f"Argument '{arg_name}' for tool '{tool_name}' must be one of {expected_type}, got {type(arg_value)}"
                    )
            else:
                # Single expected type
                if not isinstance(arg_value, expected_type):
                    # Special handling for None
                    if arg_value is None:
                        continue
                    raise MCPValidationError(
                        f"Argument '{arg_name}' for tool '{tool_name}' must be {expected_type}, got {type(arg_value)}"
                    )
    
    # Additional validation for specific arguments
    if tool_name == "get_population_data":
        if "coo" in arguments and arguments["coo"]:
            if not isinstance(arguments["coo"], str) or len(arguments["coo"]) != 3:
                raise MCPValidationError(
                    f"Argument 'coo' must be a 3-letter ISO country code, got '{arguments['coo']}'"
                )
        if "coa" in arguments and arguments["coa"]:
            if not isinstance(arguments["coa"], str) or len(arguments["coa"]) != 3:
                raise MCPValidationError(
                    f"Argument 'coa' must be a 3-letter ISO country code, got '{arguments['coa']}'"
                )
    
    # Validate year format if present
    if "year" in arguments and arguments["year"]:
        year = arguments["year"]
        if isinstance(year, str):
            # Can be comma-separated years or single year
            if "," in year:
                years = [y.strip() for y in year.split(",")]
                for y in years:
                    if not y.isdigit() or len(y) != 4:
                        raise MCPValidationError(
                            f"Year '{y}' is not a valid 4-digit year"
                        )
            else:
                if not year.isdigit() or len(year) != 4:
                    raise MCPValidationError(
                        f"Year '{year}' is not a valid 4-digit year"
                    )



async def call_tool(
    tool_name: str,
    arguments: dict,
    timeout: Optional[int] = None,
    max_retries: Optional[int] = None,
    validate: bool = True
) -> Any:
    """
    Call an MCP tool with retry logic and proper error handling.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Dictionary of arguments for the tool
        timeout: Override default timeout in seconds
        max_retries: Override default max retries
        validate: Whether to validate arguments before calling (default: True)
        
    Returns:
        Tool result as parsed JSON, or raw text if not JSON
        
    Raises:
        MCPConnectionError: If connection to MCP server fails after all retries
        MCPToolError: If tool execution fails
        MCPValidationError: If argument validation fails
    """
    actual_timeout = timeout if timeout is not None else MCP_TIMEOUT
    actual_retries = max_retries if max_retries is not None else MCP_MAX_RETRIES
    
    # Validate arguments if requested
    if validate:
        try:
            validate_tool_arguments(tool_name, arguments)
        except MCPValidationError as e:
            logger.error(f"Argument validation failed for tool {tool_name}: {e}")
            raise
    
    last_exception = None
    
    for attempt in range(actual_retries):
        try:
            async with streamablehttp_client(
                MCP_URL,
                timeout=actual_timeout
            ) as (
                read_stream,
                write_stream,
                _
            ):

                async with ClientSession(
                    read_stream,
                    write_stream
                ) as session:

                    await session.initialize()

                    result = await session.call_tool(
                        tool_name,
                        arguments
                    )

                    # MCP SDK returns result.content as a list of
                    # TextContent objects: [{type:"text", text:"..."}]
                    # Parse the JSON inside .text to return a plain dict.
                    content = result.content

                    if not content:
                        return {}

                    # Take the first text content block
                    first = content[0]
                    text = getattr(first, "text", None)
                    if text is None and isinstance(first, dict):
                        text = first.get("text")

                    if text:
                        try:
                            return json.loads(text)
                        except (json.JSONDecodeError, TypeError):
                            # Return raw text if not JSON - some tools return plain text
                            logger.debug(
                                "MCP tool %s returned non-JSON text",
                                tool_name,
                            )
                            return text

                    return {"raw_content": str(content)}
                    
        except Exception as e:
            last_exception = e
            if attempt < actual_retries - 1:
                # Exponential backoff
                wait_time = (2 ** attempt) * 0.5
                logger.warning(
                    "MCP call to %s failed (attempt %d/%d), retrying in %.1fs: %s",
                    tool_name,
                    attempt + 1,
                    actual_retries,
                    wait_time,
                    str(e)
                )
                await asyncio.sleep(wait_time)
            else:
                logger.error(
                    "MCP call to %s failed after %d attempts",
                    tool_name,
                    actual_retries,
                    exc_info=True
                )
    
    # All retries exhausted
    raise MCPConnectionError(
        f"Failed to call MCP tool '{tool_name}' after {actual_retries} attempts: {last_exception}"
    )