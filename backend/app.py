from __future__ import annotations

import json
import logging
import os
import time
from datetime import datetime
from typing import Any, Optional

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from backend.crewai.crew import UNHCRCrew

# Load environment variables from .env file
load_dotenv()

# Observability - imported lazily to avoid circular imports
# from backend.mcp.observability import (
#     prometheus_metrics,
#     monitor_chat,
#     complete_chat,
#     monitor_tool,
#     complete_tool,
#     tool_error,
#     configure_logging,
# )
# configure_logging(level=os.getenv("LOG_LEVEL", "INFO"))

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.mcp.server import create_server
from backend.chat import process_chat_message
from backend.charts import generate_chart   
from backend.mcp_bridge import call_tool, MCPConnectionError, MCPValidationError, MCP_TOOL_SCHEMAS
from backend.history import save_analysis, get_all_analyses, get_analysis, save_quarto_analysis, get_quarto_analyses, save_rating
from backend.chat import analysis_config_model, AudienceEnum

# CrewAI integration (lazy import to avoid circular dependencies)
# Will be imported when first CrewAI endpoint is called
CREWAI_ENABLED = os.getenv("CREWAI_ENABLED", "false").lower() == "true"
from backend.auth import (
    UserInfo,
    verify_azure_auth,
    get_optional_user,
    get_azure_config,
    extract_user_from_azure_headers
)
from typing import TypedDict, Optional

logger = logging.getLogger(__name__)

# Initialize rate limiter
# Configure rate limits from environment or use defaults
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED
)

# Configure rate limit storage (in-memory for now, can be Redis in production)
from slowapi import _rate_limit_exceeded_handler
from slowapi.middleware import SlowAPIMiddleware

# ---------------------------------------------------------------------
# Helper Functions
# ---------------------------------------------------------------------

def create_visualization_data(
    data: Any,
    visualization_type: str = "chart",
    title: str = "Data Visualization",
    x_label: str = "X Axis",
    y_label: str = "Y Axis"
) -> dict[str, Any]:
    """
    Helper function to create properly formatted data
    for the generate_analytical_story tool.
    
    Args:
        data: The actual data to visualize
        visualization_type: Type of visualization (chart, table, etc.)
        title: Title for the visualization
        x_label: Label for X axis
        y_label: Label for Y axis
        
    Returns:
        Properly formatted visualization_data dictionary
    """
    return {
        "data": data,
        "structure": {
            "visualization_type": visualization_type,
            "labels": {
                "title": title,
                "x": x_label,
                "y": y_label
            }
        }
    }

# ---------------------------------------------------------------------
# MCP & FastAPI Setup
# ---------------------------------------------------------------------
from contextlib import asynccontextmanager

mcp_server = create_server()
# Set streamable_http_path to "/" so it works when mounted at /mcp
mcp_server.settings.streamable_http_path = "/"
mcp_app = mcp_server.streamable_http_app()

# Get the session manager AFTER creating the streamable HTTP app
mcp_session_manager = mcp_server.session_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_session_manager.run():
        yield

app = FastAPI(
    title="UNHCR Stat Copilot",
    description="UNHCR MCP-powered analytics assistant",
    version="1.0.0",
    lifespan=lifespan
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Add rate limiter middleware
app.state.limiter = limiter
app.add_middleware(SlowAPIMiddleware)
app.add_exception_handler(429, _rate_limit_exceeded_handler)


# -------------------------------------------------------------------------
# CrewAI Integration
# -------------------------------------------------------------------------

# Register CrewAI endpoints if enabled
if CREWAI_ENABLED:
    try:
        from backend.crewai.app_integration import register_crewai_endpoints
        register_crewai_endpoints(app)
        logger.info("CrewAI endpoints registered and enabled")
    except Exception as e:
        logger.warning(f"Could not register CrewAI endpoints: {e}")
        CREWAI_ENABLED = False
else:
    logger.info("CrewAI endpoints disabled (set CREWAI_ENABLED=true to enable)")


# -------------------------------------------------------------------------

try:
    # FastMCP HTTP transport
    # Mount at /mcp - the mcp_app has streamable_http_path="/" so it handles /mcp requests
    from starlette.routing import Mount
    app.routes.append(Mount("/mcp", mcp_app))
except Exception as e:
    logger.warning(
        "Could not mount MCP endpoint: %s",
        e
    )

# NOTE: /mcp health check endpoints removed to avoid conflict with FastMCP.
# FastMCP handles /mcp directly. Azure health checks should use /health instead.
# See: https://github.com/modelcontextprotocol/python-sdk/issues/XXX
# The Mount at /mcp takes precedence for MCP protocol requests.


# ---------------------------------------------------------------------
# Helper Functions for Documentation
# ---------------------------------------------------------------------

def generate_example_usage(tool_name: str, schema: dict) -> str:
    """
    Generate example usage for a tool.
    
    Args:
        tool_name: Name of the MCP tool
        schema: Tool schema containing required and optional parameters
        
    Returns:
        String with example usage
    """
    required = schema.get("required", [])
    optional = schema.get("optional", [])[:3]  # Show first 3 optional params
    types_map = schema.get("types", {})
    
    params = []
    # Add required parameters
    for p in required:
        param_type = types_map.get(p, str)
        if param_type == str:
            params.append(f"'{p}': 'example_value'")
        elif param_type == int:
            params.append(f"'{p}': 2024")
        elif param_type == bool:
            params.append(f"'{p}': True")
        elif param_type == list:
            params.append(f"'{p}': ['item1', 'item2']")
        elif param_type == dict:
            params.append(f"'{p}': {{'key': 'value'}}")
        else:
            params.append(f"'{p}': 'value'")
    
    # Add optional parameters
    for p in optional:
        param_type = types_map.get(p, str)
        if param_type == str:
            params.append(f"'{p}': 'optional_value'")
        elif param_type == int:
            params.append(f"'{p}': 100")
        elif param_type == bool:
            params.append(f"'{p}': False")
        elif param_type == list:
            params.append(f"'{p}': []")
        elif param_type == dict:
            params.append(f"'{p}': {{}}")
        else:
            params.append(f"'{p}': None")
    
    params_str = ", \n        ".join(params)
    return f"""call_tool('{tool_name}', {{
        {params_str}
    }})"""


def get_tool_description_from_server(tool_name: str) -> str:
    """
    Get tool description from the MCP server if available.
    
    Args:
        tool_name: Name of the MCP tool
        
    Returns:
        Tool description or fallback message
    """
    try:
        if hasattr(mcp_server, '_tool_manager'):
            tool_info = mcp_server._tool_manager.get_tool(tool_name)
            if tool_info and hasattr(tool_info, 'description'):
                return tool_info.description
    except Exception:
        pass
    return "No description available"


def convert_types_to_strings(types_dict: dict) -> dict:
    """
    Convert Python type objects to string representations for JSON serialization.
    
    Args:
        types_dict: Dictionary with type objects as values
        
    Returns:
        Dictionary with type names as strings
    """
    result = {}
    for key, value in types_dict.items():
        if isinstance(value, tuple):
            # Handle union types like (str, int)
            type_names = [t.__name__ if hasattr(t, '__name__') else str(t) for t in value]
            result[key] = type_names
        elif hasattr(value, '__name__'):
            result[key] = value.__name__
        else:
            result[key] = str(value)
    return result


def generate_html_documentation(data: dict, title: str = "MCP Documentation") -> str:
    """
    Generate HTML documentation from a dictionary.
    
    Args:
        data: Dictionary containing documentation data
        title: HTML page title
        
    Returns:
        HTML string
    """
    import json
    
    # Generate JSON for the data
    json_data = json.dumps(data, indent=2, default=str)
    
    html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>{title}</title>
    <style>
        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Oxygen, Ubuntu, sans-serif;
            margin: 0;
            padding: 20px;
            background-color: #f5f5f5;
            color: #333;
        }}
        .container {{
            max-width: 1200px;
            margin: 0 auto;
        }}
        h1 {{
            color: #2c3e50;
            border-bottom: 2px solid #3498db;
            padding-bottom: 10px;
        }}
        h2 {{
            color: #2c3e50;
            margin-top: 25px;
        }}
        h3 {{
            color: #7f8c8d;
            margin-top: 20px;
        }}
        .tool-card {{
            background: white;
            border-radius: 8px;
            padding: 15px;
            margin: 10px 0;
            box-shadow: 0 2px 4px rgba(0,0,0,0.1);
        }}
        .tool-name {{
            font-weight: bold;
            color: #3498db;
            font-size: 1.1em;
        }}
        .param-list {{
            background: #f8f9fa;
            padding: 10px;
            border-radius: 4px;
            margin: 5px 0;
        }}
        .code-block {{
            background: #2d3436;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.9em;
        }}
        .json-section {{
            background: #2d3436;
            color: #ecf0f1;
            padding: 15px;
            border-radius: 4px;
            overflow-x: auto;
            font-family: 'Courier New', monospace;
            font-size: 0.85em;
        }}
        a {{
            color: #3498db;
            text-decoration: none;
        }}
        a:hover {{
            text-decoration: underline;
        }}
        .endpoints {{
            background: #e8f4fc;
            padding: 15px;
            border-radius: 4px;
            margin: 20px 0;
        }}
        .endpoints a {{
            display: block;
            margin: 5px 0;
        }}
        .copy-btn {{
            background: #3498db;
            color: white;
            border: none;
            padding: 5px 10px;
            border-radius: 4px;
            cursor: pointer;
            margin-left: 10px;
        }}
        .copy-btn:hover {{
            background: #2980b9;
        }}
    </style>
</head>
<body>
    <div class="container">
        <h1>{title}</h1>
        <p>MCP (Model Context Protocol) Server Documentation</p>
        
        <div class="endpoints">
            <h3>📚 Endpoints</h3>
            <a href="/api/mcp/docs">/api/mcp/docs - Full Documentation (JSON)</a>
            <a href="/api/mcp/info">/api/mcp/info - Server Info (JSON)</a>
            <a href="/tools">/tools - Tool List (JSON)</a>
            <a href="/mcp">/mcp - MCP Protocol Endpoint</a>
            <a href="/docs">/docs - Swagger UI</a>
            <a href="/redoc">/redoc - ReDoc</a>
        </div>
        
        <div class="json-section">
            <h3>📄 JSON Documentation</h3>
            <p>Full documentation in JSON format:</p>
            <pre id="json-data">{json_data}</pre>
            <button class="copy-btn" onclick="copyToClipboard()">Copy JSON</button>
        </div>
        
        <script>
            function copyToClipboard() {{
                const json = document.getElementById('json-data').textContent;
                navigator.clipboard.writeText(json).then(() => {{
                    alert('Copied to clipboard!');
                }});
            }}
        </script>
    </div>
</body>
</html>"""
    return html


# ---------------------------------------------------------------------
# MCP Documentation Endpoints
# ---------------------------------------------------------------------

@app.get("/api/mcp/docs",
         summary="MCP Server Documentation",
         description="Get complete documentation for the MCP server including all tools, descriptions, and parameters.",
         response_description="MCP server documentation",
         tags=["MCP", "Documentation"],
         responses={
             200: {
                 "description": "MCP server documentation",
                 "content": {
                     "application/json": {
                         "example": {
                             "server": {"name": "...", "description": "...", "version": "1.0.0"},
                             "tools": {},
                             "endpoints": {},
                             "total_tools": 0
                         }
                     },
                     "text/html": {
                         "example": "<html>...</html>"
                     }
                 }
             }
         })
async def mcp_docs(request: Request):
    """
    Returns comprehensive documentation for the MCP server.
    
    This endpoint provides:
    - Server metadata (name, description, version)
    - All registered tools with their descriptions
    - Tool parameter schemas
    - Usage examples
    
    Returns:
        JSON or HTML: Documentation containing server info, tools, and endpoints.
        Returns HTML when Accept header includes text/html, JSON otherwise.
    """
    # Get server info
    server_info = {
        "name": mcp_server.name,
        "description": mcp_server.instructions,
        "version": "1.0.0"
    }
    
    # Build tool documentation
    tools_docs = {}
    for tool_name, schema in MCP_TOOL_SCHEMAS.items():
        tool_desc = get_tool_description_from_server(tool_name)
        
        tools_docs[tool_name] = {
            "description": tool_desc,
            "required_params": schema.get("required", []),
            "optional_params": schema.get("optional", []),
            "param_types": convert_types_to_strings(schema.get("types", {})),
            "example": generate_example_usage(tool_name, schema)
        }
    
    data = {
        "server": server_info,
        "tools": tools_docs,
        "endpoints": {
            "mcp_base": "/mcp",
            "mcp_docs": "/api/mcp/docs",
            "mcp_info": "/api/mcp/info",
            "tools_list": "/tools",
            "execute_tool": "/tool",
            "chat": "/chat",
            "health": "/health"
        },
        "total_tools": len(tools_docs),
        "documentation": {
            "format": "JSON",
            "generated_at": datetime.now().isoformat(),
            "fastapi_docs": "/docs",
            "redoc": "/redoc"
        }
    }
    
    # Return HTML if the client accepts it, otherwise JSON
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=generate_html_documentation(data, "MCP Documentation"))
    return data


@app.get("/api/mcp/info",
         summary="MCP Server Info",
         description="Get metadata and basic information about the MCP server.",
         response_description="MCP server metadata",
         tags=["MCP", "Info"],
         responses={
             200: {
                 "description": "MCP server metadata",
                 "content": {
                     "application/json": {
                         "example": {
                             "server": {"name": "...", "description": "...", "version": "1.0.0"},
                             "endpoint": "/mcp",
                             "tools_count": 0,
                             "tool_names": [],
                             "status": "running"
                         }
                     },
                     "text/html": {
                         "example": "<html>...</html>"
                     }
                 }
             }
         })
async def mcp_info(request: Request):
    """
    Get basic information about the MCP server.
    
    This provides a lightweight overview of the MCP server without
    the full tool documentation.
    
    Returns:
        JSON or HTML: Server metadata and summary information.
        Returns HTML when Accept header includes text/html, JSON otherwise.
    """
    tool_names = list(MCP_TOOL_SCHEMAS.keys())
    
    data = {
        "server": {
            "name": mcp_server.name,
            "description": mcp_server.instructions,
            "version": "1.0.0"
        },
        "endpoint": "/mcp",
        "tools_count": len(tool_names),
        "tool_names": tool_names,
        "status": "running",
        "documentation_endpoints": {
            "full_docs": "/api/mcp/docs",
            "tool_list": "/tools"
        },
        "timestamp": datetime.now().isoformat()
    }
    
    # Return HTML if the client accepts it, otherwise JSON
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=generate_html_documentation(data, "MCP Server Info"))
    return data


# ---------------------------------------------------------------------
# Models
# ---------------------------------------------------------------------

class ChatRequest(BaseModel):
    message: str
    origin: Optional[str] = None
    destination: Optional[str] = None
    topic: Optional[str] = None
    timespan: Optional[str] = None
    audience: Optional[str] = None
    document_type: Optional[str] = None
    style: Optional[str] = None
    use_rag: bool = True
    include_notebook: bool = True
    output_path: Optional[str] = None


class ToolRequest(BaseModel):
    tool: str
    arguments: dict[str, Any]


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health", 
         summary="Health Check",
         description="Check the health status of the UNHCR Stat Copilot service.",
         response_description="Service health status",
         responses={
             200: {
                 "description": "Service is healthy",
                 "content": {
                     "application/json": {
                         "example": {"status": "ok", "service": "unhcr-copilot"}
                     }
                 }
             }
         })
async def health():
    """
    Health check endpoint for the UNHCR Stat Copilot service.
    
    Returns a simple status response to verify the service is running.
    This endpoint does not require authentication and is available to all users.
    
    Returns:
        dict: A dictionary containing:
            - status (str): "ok" if service is healthy
            - service (str): The service name ("unhcr-copilot")
    """
    return {
        "status": "ok",
        "service": "unhcr-copilot"
    }


# ---------------------------------------------------------------------
# Observability - Prometheus Metrics
# ---------------------------------------------------------------------

@app.get("/metrics",
         summary="Prometheus Metrics",
         description="Expose Prometheus metrics for monitoring server health and performance.",
         response_description="Prometheus-formatted metrics",
         responses={
             200: {
                 "description": "Prometheus metrics in text format",
                 "content": {
                     "text/plain": {}
                 }
             }
         })
async def metrics():
    """
    Prometheus metrics endpoint for monitoring the UNHCR Stat Copilot service.
    
    Returns Prometheus-formatted metrics for monitoring:
    - Request counts and error rates
    - Latency histograms
    - Active request gauges
    
    This endpoint does not require authentication and is available to all users.
    
    Returns:
        Response: Plain text response with Prometheus metrics
    """
    from fastapi.responses import Response
    from backend.mcp.observability import prometheus_metrics
    return Response(content=prometheus_metrics(), media_type="text/plain")


# ---------------------------------------------------------------------
# MCP Tool Discovery
# ---------------------------------------------------------------------

@app.get("/tools",
         summary="List Available Tools",
         description="Retrieve detailed information about all available MCP tools including descriptions and parameters.",
         response_description="List of available MCP tools with metadata",
         tags=["MCP", "Tools"],
         responses={
             200: {
                 "description": "Successful response with tool list and metadata",
                 "content": {
                     "application/json": {
                         "example": {
                             "tools": [
                                 {
                                     "name": "get_population_data",
                                     "description": "Retrieve forcibly displaced population statistics from UNHCR",
                                     "required_params": [],
                                     "optional_params": ["coo", "coa", "year"],
                                     "endpoint": "/tool"
                                 }
                             ],
                             "total": 1,
                             "server": "UNHCR Forcibly Displaced Populations MCP Server"
                         }
                     },
                     "text/html": {
                         "example": "<html>...</html>"
                     }
                 }
             }
         })
async def tools(request: Request):
    """
    List all available MCP tools with detailed metadata.
    
    This endpoint returns comprehensive information about all available tools
    in the MCP server, including descriptions, required/optional parameters,
    and usage examples.
    
    This endpoint does not require authentication.
    
    Returns:
        JSON or HTML: Dictionary containing tool list with metadata.
        Returns HTML when Accept header includes text/html, JSON otherwise.
    """
    tool_list = []
    
    for tool_name, schema in MCP_TOOL_SCHEMAS.items():
        tool_desc = get_tool_description_from_server(tool_name)
        
        tool_list.append({
            "name": tool_name,
            "description": tool_desc,
            "required_params": schema.get("required", []),
            "optional_params": schema.get("optional", []),
            "param_types": convert_types_to_strings(schema.get("types", {})),
            "example_usage": generate_example_usage(tool_name, schema),
            "execution_endpoint": "/tool"
        })
    
    data = {
        "tools": tool_list,
        "total": len(tool_list),
        "server": mcp_server.name,
        "mcp_endpoint": "/mcp",
        "full_documentation": "/api/mcp/docs",
        "server_info": "/api/mcp/info"
    }
    
    # Return HTML if the client accepts it, otherwise JSON
    if "text/html" in request.headers.get("accept", ""):
        return HTMLResponse(content=generate_html_documentation(data, "Available Tools"))
    return data


# ---------------------------------------------------------------------
# Direct Tool Execution
# ---------------------------------------------------------------------

@app.post("/tool",
          summary="Execute MCP Tool",
          description="Execute a specific MCP tool with provided arguments.",
          response_description="Tool execution result",
          responses={
              200: {
                  "description": "Tool executed successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "tool": "get_population_data",
                              "result": {"data": [], "metadata": {}},
                              "user": {"name": "user@example.com"}
                          }
                      }
                  }
              },
              400: {"description": "Invalid tool request or validation error"},
              401: {"description": "Authentication required"},
              503: {"description": "MCP server unavailable"}
          })
@limiter.limit("10/minute")
async def execute_tool(
    request: Request,
    tool_request: ToolRequest,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Execute a specific MCP tool directly.
    
    This endpoint allows direct execution of any available MCP tool with custom arguments.
    It requires Azure AD authentication. Rate limited to 10 requests per minute per IP.
    
    Args:
        tool_request (ToolRequest): The tool execution request containing:
            - tool (str): Name of the tool to execute (must be in /tools list)
            - arguments (dict): Dictionary of arguments to pass to the tool
        user (UserInfo): Authenticated user information (injected by dependency)
    
    Returns:
        dict: A dictionary containing:
            - tool (str): The name of the tool that was executed
            - result (Any): The result returned by the tool
            - user (dict): Information about the authenticated user
    
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 400: If tool arguments are invalid
        HTTPException 503: If MCP server is unavailable
        HTTPException 500: For any other unexpected errors
    
    Example:
        Request body:
        {
            "tool": "get_population_data",
            "arguments": {
                "country": "France",
                "year": 2023,
                "data_type": "refugees"
            }
        }
    """
    tool_name = tool_request.tool
    start_time = time.time()
    
    # Lazy import to avoid circular imports
    from backend.mcp.observability import monitor_tool, complete_tool, tool_error
    monitor_tool(tool_name)
    
    try:

        result = await call_tool(
            tool_request.tool,
            tool_request.arguments
        )
        
        complete_tool(tool_name, 'success')
        
        return {
            "tool": tool_request.tool,
            "result": result,
            "user": user.to_dict()
        }

    except MCPConnectionError as e:
        logger.error(f"MCP connection error: {e}")
        tool_error(tool_name, 'connection_error')
        complete_tool(tool_name, 'error')
        raise HTTPException(
            status_code=503,
            detail=f"MCP server unavailable: {str(e)}"
        )
    except MCPValidationError as e:
        logger.error(f"Validation error: {e}")
        tool_error(tool_name, 'validation_error')
        complete_tool(tool_name, 'error')
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:

        logger.exception(e)
        tool_error(tool_name, 'internal_error')
        complete_tool(tool_name, 'error')

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# Chat Endpoint
# ---------------------------------------------------------------------

@app.post("/chat",
          summary="Process Chat via CrewAI",
          description="Delegate chat processing to the CrewAI orchestrator.",
          response_description="Analysis result from CrewAI workflow")
@limiter.limit("5/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Delegate chat message processing to the CrewAI orchestrator,
    streamlining the full-analysis workflow through UNHCRCrew.
    """
    crew = UNHCRCrew(
        audience=chat_request.audience or "internal",
        document_type=chat_request.document_type,
        process_type="sequential"
    )
    try:
        result = await crew.execute_full_workflow(
            question=chat_request.message,
            origin=chat_request.origin,
            destination=chat_request.destination,
            topic=chat_request.topic,
            timespan=chat_request.timespan,
            use_rag=chat_request.use_rag,
            include_notebook=chat_request.include_notebook,
            output_path=chat_request.output_path,
            style=chat_request.style
        )
        # Expose step names as tool_sequence for frontend observability
        if 'steps' in result and isinstance(result['steps'], list):
            result['tool_sequence'] = [
                { 'name': step.get('name'), 'status': step.get('status'), 'duration_ms': step.get('duration_ms') }
                for step in result['steps']
            ]
        # Persist JSON entry and optionally save Quarto notebook if included
        save_analysis(result)
        nb = result.get("notebook") or {}
        if chat_request.include_notebook and nb.get("content"):
            metadata_for_save = result.get("metadata", {}).copy()
            metadata_for_save["steps"] = result.get("steps", [])
            metadata_for_save["workflow_sequence"] = result.get("workflow_sequence", [])
            save_result = save_quarto_analysis(nb.get("content", ""), metadata_for_save)
            result.update({
                "id": save_result.get("id"),
                "filepath": save_result.get("filepath"),
                "quarto_filename": save_result.get("filename"),
                "quarto_metadata": save_result.get("metadata"),
            })
        return {**result, "user": user.to_dict()}
    except Exception as e:
        logger.exception(f"CrewAI chat failed: {e}")
        raise HTTPException(status_code=500, detail=str(e))


# ---------------------------------------------------------------------
# Analysis History Endpoints
# ---------------------------------------------------------------------

@app.get("/history",
         summary="Get Analysis History",
         description="Retrieve all previous analyses including both JSON and Quarto-based analyses.",
         response_description="List of all analyses with metadata",
         responses={
             200: {
                 "description": "Successful response with analysis history",
                 "content": {
                     "application/json": {
                         "example": {
                             "status": "success",
                             "analyses": [
                                 {
                                     "id": "abc123",
                                     "timestamp": "2026-07-02T12:00:00",
                                     "analysis_type": "quarto_notebook",
                                     "unique_id": "quarto_abc123"
                                 }
                             ]
                         }
                     }
                 }
             },
             500: {"description": "Internal server error"}
         })
async def get_history():
    """
    Get all previous analyses (both JSON and Quarto)
    """
    try:
        # Get JSON analyses
        json_analyses = get_all_analyses()
        
        # Get Quarto analyses
        quarto_analyses = get_quarto_analyses()
        
        # Add type prefix to IDs to ensure uniqueness when combining
        # This prevents React key conflicts between JSON and Quarto analyses
        for analysis in json_analyses:
            analysis["unique_id"] = f"json_{analysis['id']}"
            analysis["analysis_type"] = "json"
            
        for analysis in quarto_analyses:
            analysis["unique_id"] = f"quarto_{analysis['id']}"
            analysis["analysis_type"] = "quarto"
        
        # Combine both types
        all_analyses = json_analyses + quarto_analyses
        
        # Sort by timestamp (newest first)
        all_analyses.sort(key=lambda x: x["timestamp"], reverse=True)
        
        return {
            "status": "success",
            "analyses": all_analyses
        }
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/history/{analysis_id}",
          summary="Get Specific Analysis",
          description="Retrieve a specific analysis by its unique ID.",
          response_description="Analysis details",
          responses={
              200: {
                  "description": "Analysis found and returned",
                  "content": {
                      "application/json": {
                          "example": {
                              "id": "abc123",
                              "analysis_type": "comprehensive_quarto",
                              "response": "Full analysis content...",
                              "timestamp": "2026-07-02T12:00:00"
                          }
                      }
                  }
              },
              404: {"description": "Analysis not found"},
              500: {"description": "Internal server error"}
          })
async def get_single_analysis(analysis_id: str):
    """
    Get a specific analysis by ID.
    
    Retrieves the full details of a previously completed analysis. The analysis
    can be either a JSON-based analysis or a Quarto notebook analysis.
    
    Args:
        analysis_id (str): The unique identifier of the analysis to retrieve
    
    Returns:
        dict: The complete analysis object with all its fields. The exact structure
              depends on the analysis type but typically includes:
            - id (str): Analysis identifier
            - analysis_type (str): Type of analysis (e.g., "quarto_notebook")
            - response (str): The analysis response/content
            - timestamp (str): When the analysis was created
            - Additional fields specific to the analysis type
    
    Raises:
        HTTPException 404: If the analysis with the given ID is not found
        HTTPException 500: For any other errors
    """
    try:
        # First try to get as JSON analysis
        analysis = get_analysis(analysis_id)
        
        if analysis is None:
            raise HTTPException(
                status_code=404,
                detail="Analysis not found"
            )
        
        return analysis
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/quarto/{analysis_id}",
          summary="Download Quarto Analysis",
          description="Download the raw Quarto markdown file (.qmd) for a specific analysis.",
          response_description="Quarto markdown file content",
          responses={
              200: {
                  "description": "Quarto file content",
                  "content": {
                      "text/plain": {
                          "example": "---\ntitle: Analysis\nauthor: UNHCR\n---\n# Analysis Content..."
                      }
                  },
                  "headers": {
                      "Content-Disposition": {
                          "description": "Attachment with filename"
                      }
                  }
              },
              404: {"description": "Quarto analysis or file not found"},
              500: {"description": "Internal server error"}
          })
async def download_quarto_analysis(analysis_id: str):
    """
    Download a Quarto analysis file by ID.
    
    Retrieves the raw Quarto markdown (.qmd) file for a specific analysis. This is the
    source file that can be rendered using the Quarto CLI (quarto render command).
    
    The returned file includes YAML front matter with metadata such as title, author,
    date, and the UNHCR theme configuration.
    
    Args:
        analysis_id (str): The unique identifier of the Quarto analysis
    
    Returns:
        Response: A Response object containing:
            - content (str): The raw Quarto markdown content
            - media_type (str): "text/plain"
            - headers (dict): Content-Disposition header with filename
    
    Raises:
        HTTPException 404: If the analysis or Quarto file is not found
        HTTPException 500: For any other errors
    
    Note:
        This endpoint returns the raw .qmd file. To get a pre-rendered HTML version,
        the file should be processed with the Quarto CLI: `quarto render file.qmd`
    """
    try:
        # Find the metadata file for this analysis
        metadata_file = os.path.join("./data/analysis_history", f"{analysis_id}.json")
        
        if not os.path.exists(metadata_file):
            raise HTTPException(
                status_code=404,
                detail="Quarto analysis not found"
            )
        
        # Read metadata to find the Quarto file
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        quarto_filepath = metadata.get("filepath")
        
        if not quarto_filepath or not os.path.exists(quarto_filepath):
            raise HTTPException(
                status_code=404,
                detail="Quarto file not found"
            )
        
        # Read and return the Quarto file
        with open(quarto_filepath, "r", encoding="utf-8") as f:
            quarto_content = f.read()
        
        # Determine filename from metadata
        filename = metadata.get("quarto_filename", f"analysis_{analysis_id}.qmd")
        
        return Response(
            content=quarto_content,
            media_type="text/plain",
            headers={
                "Content-Disposition": f"attachment; filename={filename}"
            }
        )
        
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# Quarto Rendering Endpoint
# ---------------------------------------------------------------------

@app.get("/quarto/{analysis_id}/rendered",
         summary="Get Rendered Quarto Analysis",
         description="Get the pre-rendered HTML version of a Quarto analysis using the quarto render CLI.",
         response_description="Rendered HTML content",
         responses={
             200: {
                 "description": "Successfully rendered HTML",
                 "content": {
                     "text/html": {
                         "example": "<!DOCTYPE html><html>...</html>"
                     }
                 }
             },
             404: {"description": "Quarto analysis or file not found"},
             500: {"description": "Internal server error during rendering"}
         })
async def get_rendered_quarto_analysis(analysis_id: str):
    """
    Get the pre-rendered HTML version of a Quarto analysis.
    
    This endpoint first tries to serve pre-rendered HTML files (if available),
    falling back to on-demand rendering using the Quarto CLI if necessary.
    
    This is the recommended way to display Quarto analyses, as it properly handles:
    - YAML front matter (title, author, theme, etc.)
    - All markdown features (tables, lists, blockquotes, etc.)
    - Quarto-specific extensions
    - Code cells and outputs (if present)
    - LaTeX/math rendering
    - UNHCR theme application
    
    This endpoint does not require authentication.
    
    Args:
        analysis_id (str): The unique identifier of the Quarto analysis
    
    Returns:
        Response: A Response object containing:
            - content (str): The fully rendered HTML content
            - media_type (str): "text/html"
    
    Raises:
        HTTPException 404: If the analysis or Quarto file is not found
        HTTPException 500: If the Quarto CLI is not available or rendering fails
    
    Note:
        This endpoint first checks for pre-rendered HTML files in data/quarto_analyses/.
        If not found, it falls back to on-demand rendering using Quarto CLI.
    """
    import subprocess
    import tempfile
    import shutil
    from pathlib import Path
    
    try:
        # First, check if we have pre-rendered HTML in the quarto_analyses directory
        from backend.history import QUARTO_DIR
        
        # Try to find the analysis metadata to get the HTML path
        metadata_file = os.path.join("./data/analysis_history", f"{analysis_id}.json")
        
        if os.path.exists(metadata_file):
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Check if we have a pre-rendered HTML path
            html_path = metadata.get("html_path")
            if html_path and os.path.exists(html_path):
                # Serve the pre-rendered HTML directly
                with open(html_path, "r", encoding="utf-8") as f:
                    html_content = f.read()
                return Response(content=html_content, media_type="text/html")
        
        # Fallback: on-demand rendering
        if not os.path.exists(metadata_file):
            raise HTTPException(
                status_code=404,
                detail="Quarto analysis not found"
            )
        
        # Read metadata to find the Quarto file
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        quarto_filepath = metadata.get("filepath")
        
        if not quarto_filepath or not os.path.exists(quarto_filepath):
            raise HTTPException(
                status_code=404,
                detail="Quarto file not found"
            )
        
        # Create a temporary directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the .qmd file to temp dir with a simple filename
            temp_qmd = os.path.join(temp_dir, "analysis.qmd")
            with open(temp_qmd, "w", encoding="utf-8") as f:
                with open(quarto_filepath, "r", encoding="utf-8") as src:
                    f.write(src.read())
            
            # Run quarto render command
            # Quarto will create the HTML file in the same directory with the same name
            # Note: --output flag doesn't work with paths, so we let Quarto generate it automatically
            result = subprocess.run(
                ["quarto", "render", temp_qmd, "--to", "html"],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                logger.error(f"Quarto render failed for {analysis_id}: {result.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Quarto rendering failed: {result.stderr}"
                )
            
            # Find the generated HTML file
            # Quarto creates: analysis.html (same name as qmd but with .html extension)
            temp_html = os.path.join(temp_dir, "analysis.html")
            
            if not os.path.exists(temp_html):
                # List all files in temp dir to find the HTML
                files = os.listdir(temp_dir)
                html_files = [f for f in files if f.endswith('.html')]
                if html_files:
                    temp_html = os.path.join(temp_dir, html_files[0])
                else:
                    logger.error(f"No HTML files found in temp dir. Files: {files}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Quarto did not produce HTML output. Files created: {files}"
                    )
            
            # Read and return the rendered HTML
            with open(temp_html, "r", encoding="utf-8") as f:
                html_content = f.read()
            
            # Update metadata with the rendered HTML path for future requests
            html_filename = f"{Path(quarto_filepath).stem}.html"
            html_save_path = os.path.join(QUARTO_DIR, html_filename)
            with open(html_save_path, "w", encoding="utf-8") as f:
                f.write(html_content)
            
            # Update metadata
            metadata["html_path"] = html_save_path
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f)
            
            return Response(content=html_content, media_type="text/html")
        
    except subprocess.CalledProcessError as e:
        logger.exception(f"Quarto CLI error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quarto CLI error: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.exception(f"Quarto CLI not found: {e}")
        raise HTTPException(
            status_code=500,
            detail="Quarto CLI is not installed on the server. Please install Quarto to use this feature."
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# Quarto PDF Rendering Endpoint
# ---------------------------------------------------------------------

@app.get("/quarto/{analysis_id}/pdf",
         summary="Get Rendered Quarto Analysis as PDF",
         description="Get the pre-rendered PDF version of a Quarto analysis using the quarto render CLI.",
         response_description="Rendered PDF file",
         responses={
             200: {
                 "description": "Successfully rendered PDF",
                 "content": {
                     "application/pdf": {
                         "example": "PDF binary data"
                     }
                 }
             },
             404: {"description": "Quarto analysis or file not found"},
             500: {"description": "Internal server error during rendering"}
         })
async def get_rendered_quarto_analysis_pdf(analysis_id: str):
    """
    Get the pre-rendered PDF version of a Quarto analysis.
    
    This endpoint first tries to serve pre-rendered PDF files (if available),
    falling back to on-demand rendering using the Quarto CLI if necessary.
    
    This is the recommended way to get PDF versions of Quarto analyses, as it properly handles:
    - YAML front matter (title, author, theme, etc.)
    - All markdown features (tables, lists, blockquotes, etc.)
    - Quarto-specific extensions
    - Code cells and outputs (if present)
    - LaTeX/math rendering
    - UNHCR theme application
    
    This endpoint does not require authentication.
    
    Args:
        analysis_id (str): The unique identifier of the Quarto analysis
    
    Returns:
        Response: A Response object containing:
            - PDF binary content
            - media_type: "application/pdf"
            - headers with filename for download
    
    Raises:
        HTTPException 404: If the analysis or Quarto file is not found
        HTTPException 500: If the Quarto CLI is not available or rendering fails
    
    Note:
        This endpoint first checks for pre-rendered PDF files in data/quarto_analyses/.
        If not found, it falls back to on-demand rendering using Quarto CLI.
        
        The PDF will be rendered with the format settings from the Quarto file's
        YAML header (pdf: documentclass, papersize, geometry, etc.).
    """
    import subprocess
    import tempfile
    from pathlib import Path
    
    try:
        # First, check if we have pre-rendered PDF in the quarto_analyses directory
        from backend.history import QUARTO_DIR
        
        # Try to find the analysis metadata to get the PDF path
        metadata_file = os.path.join("./data/analysis_history", f"{analysis_id}.json")
        
        if os.path.exists(metadata_file):
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Check if we have a pre-rendered PDF path
            pdf_path = metadata.get("pdf_path")
            if pdf_path and os.path.exists(pdf_path):
                # Serve the pre-rendered PDF directly
                with open(pdf_path, "rb") as f:
                    rendered_pdf = f.read()
                
                # Get a nice filename for the download
                qmd_filename = os.path.basename(metadata.get("filepath", "analysis.qmd"))
                pdf_filename = qmd_filename.replace('.qmd', '.pdf')
                
                return Response(
                    content=rendered_pdf,
                    media_type="application/pdf",
                    headers={
                        "Content-Disposition": f"attachment; filename={pdf_filename}"
                    }
                )
        
        # Fallback: on-demand rendering
        if not os.path.exists(metadata_file):
            raise HTTPException(
                status_code=404,
                detail="Quarto analysis not found"
            )
        
        # Read metadata to find the Quarto file
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        quarto_filepath = metadata.get("filepath")
        
        if not quarto_filepath or not os.path.exists(quarto_filepath):
            raise HTTPException(
                status_code=404,
                detail="Quarto file not found"
            )
        
        # Create a temporary directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the .qmd file to temp dir with a simple filename
            temp_qmd = os.path.join(temp_dir, "analysis.qmd")
            with open(temp_qmd, "w", encoding="utf-8") as f:
                with open(quarto_filepath, "r", encoding="utf-8") as src:
                    f.write(src.read())
            
            # Run quarto render command for PDF
            # Quarto will create the PDF file in the same directory with the same name
            result = subprocess.run(
                ["quarto", "render", temp_qmd, "--to", "pdf"],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                logger.error(f"Quarto PDF render failed for {analysis_id}: {result.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Quarto PDF rendering failed: {result.stderr}"
                )
            
            # Find the generated PDF file
            # Quarto creates: analysis.pdf (same name as qmd but with .pdf extension)
            temp_pdf = os.path.join(temp_dir, "analysis.pdf")
            
            if not os.path.exists(temp_pdf):
                # List all files in temp dir to find the PDF
                files = os.listdir(temp_dir)
                pdf_files = [f for f in files if f.lower().endswith('.pdf')]
                if pdf_files:
                    temp_pdf = os.path.join(temp_dir, pdf_files[0])
                else:
                    logger.error(f"No PDF files found in temp dir. Files: {files}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Quarto did not produce PDF output. Files created: {files}"
                    )
            
            # Read and return the rendered PDF
            with open(temp_pdf, "rb") as f:
                rendered_pdf = f.read()
            
            # Save the PDF for future requests
            pdf_filename = f"{Path(quarto_filepath).stem}.pdf"
            pdf_save_path = os.path.join(QUARTO_DIR, pdf_filename)
            with open(pdf_save_path, "wb") as f:
                f.write(rendered_pdf)
            
            # Update metadata
            metadata["pdf_path"] = pdf_save_path
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f)
            
            # Get a nice filename for the download
            qmd_filename = os.path.basename(quarto_filepath)
            pdf_filename = qmd_filename.replace('.qmd', '.pdf')
            
            return Response(
                content=rendered_pdf,
                media_type="application/pdf",
                headers={
                    "Content-Disposition": f"attachment; filename={pdf_filename}"
                }
            )
        
    except subprocess.CalledProcessError as e:
        logger.exception(f"Quarto CLI error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quarto CLI error: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.exception(f"Quarto CLI not found: {e}")
        raise HTTPException(
            status_code=500,
            detail="Quarto CLI is not installed on the server. Please install Quarto to use this feature."
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@app.get("/quarto/{analysis_id}/word",
         summary="Get Rendered Quarto Analysis as Word",
         description="Get the pre-rendered Word document version of a Quarto analysis using the quarto render CLI.",
         response_description="Rendered Word document file",
         responses={
             200: {
                 "description": "Successfully rendered Word document",
                 "content": {
                     "application/vnd.openxmlformats-officedocument.wordprocessingml.document": {
                         "example": "Word document binary data"
                     }
                 }
             },
             404: {"description": "Quarto analysis or file not found"},
             500: {"description": "Internal server error during rendering"}
         })
async def get_rendered_quarto_analysis_word(analysis_id: str):
    """
    Get the pre-rendered Word document version of a Quarto analysis.
    
    This endpoint first tries to serve pre-rendered Word files (if available),
    falling back to on-demand rendering using the Quarto CLI if necessary.
    
    This is the recommended way to get Word versions of Quarto analyses, as it properly handles:
    - YAML front matter (title, author, theme, etc.)
    - All markdown features (tables, lists, blockquotes, etc.)
    - Quarto-specific extensions
    - Code cells and outputs (if present)
    - LaTeX/math rendering
    - UNHCR theme application
    
    This endpoint does not require authentication.
    
    Args:
        analysis_id (str): The unique identifier of the Quarto analysis
    
    Returns:
        Response: A Response object containing:
            - Word document binary content
            - media_type: "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
            - headers with filename for download
    
    Raises:
        HTTPException 404: If the analysis or Quarto file is not found
        HTTPException 500: If the Quarto CLI is not available or rendering fails
    
    Note:
        This endpoint first checks for pre-rendered Word files in data/quarto_analyses/.
        If not found, it falls back to on-demand rendering using Quarto CLI.
        
        The Word document will be rendered with the format settings from the Quarto file's
        YAML header (docx: options).
    """
    import subprocess
    import tempfile
    from pathlib import Path
    
    try:
        # First, check if we have pre-rendered Word in the quarto_analyses directory
        from backend.history import QUARTO_DIR
        
        # Try to find the analysis metadata to get the Word path
        metadata_file = os.path.join("./data/analysis_history", f"{analysis_id}.json")
        
        if os.path.exists(metadata_file):
            with open(metadata_file, "r", encoding="utf-8") as f:
                metadata = json.load(f)
            
            # Check if we have a pre-rendered Word path
            word_path = metadata.get("word_path")
            if word_path and os.path.exists(word_path):
                # Serve the pre-rendered Word directly
                with open(word_path, "rb") as f:
                    rendered_word = f.read()
                
                # Get a nice filename for the download
                qmd_filename = os.path.basename(metadata.get("filepath", "analysis.qmd"))
                word_filename = qmd_filename.replace('.qmd', '.docx')
                
                return Response(
                    content=rendered_word,
                    media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                    headers={
                        "Content-Disposition": f"attachment; filename={word_filename}"
                    }
                )
        
        # Fallback: on-demand rendering
        if not os.path.exists(metadata_file):
            raise HTTPException(
                status_code=404,
                detail="Quarto analysis not found"
            )
        
        # Read metadata to find the Quarto file
        with open(metadata_file, "r", encoding="utf-8") as f:
            metadata = json.load(f)
        
        quarto_filepath = metadata.get("filepath")
        
        if not quarto_filepath or not os.path.exists(quarto_filepath):
            raise HTTPException(
                status_code=404,
                detail="Quarto file not found"
            )
        
        # Create a temporary directory for rendering
        with tempfile.TemporaryDirectory() as temp_dir:
            # Copy the .qmd file to temp dir with a simple filename
            temp_qmd = os.path.join(temp_dir, "analysis.qmd")
            with open(temp_qmd, "w", encoding="utf-8") as f:
                with open(quarto_filepath, "r", encoding="utf-8") as src:
                    f.write(src.read())
            
            # Run quarto render command for Word
            # Quarto will create the Word file in the same directory with the same name
            result = subprocess.run(
                ["quarto", "render", temp_qmd, "--to", "docx"],
                capture_output=True,
                text=True,
                cwd=temp_dir
            )
            
            if result.returncode != 0:
                logger.error(f"Quarto Word render failed for {analysis_id}: {result.stderr}")
                raise HTTPException(
                    status_code=500,
                    detail=f"Quarto Word rendering failed: {result.stderr}"
                )
            
            # Find the generated Word file
            # Quarto creates: analysis.docx (same name as qmd but with .docx extension)
            temp_word = os.path.join(temp_dir, "analysis.docx")
            
            if not os.path.exists(temp_word):
                # List all files in temp dir to find the Word file
                files = os.listdir(temp_dir)
                word_files = [f for f in files if f.lower().endswith('.docx')]
                if word_files:
                    temp_word = os.path.join(temp_dir, word_files[0])
                else:
                    logger.error(f"No Word files found in temp dir. Files: {files}")
                    raise HTTPException(
                        status_code=500,
                        detail=f"Quarto did not produce Word output. Files created: {files}"
                    )
            
            # Read and return the rendered Word document
            with open(temp_word, "rb") as f:
                rendered_word = f.read()
            
            # Save the Word file for future requests
            word_filename = f"{Path(quarto_filepath).stem}.docx"
            word_save_path = os.path.join(QUARTO_DIR, word_filename)
            with open(word_save_path, "wb") as f:
                f.write(rendered_word)
            
            # Update metadata
            metadata["word_path"] = word_save_path
            with open(metadata_file, "w", encoding="utf-8") as f:
                json.dump(metadata, f)
            
            # Get a nice filename for the download
            qmd_filename = os.path.basename(quarto_filepath)
            word_filename = qmd_filename.replace('.qmd', '.docx')
            
            return Response(
                content=rendered_word,
                media_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
                headers={
                    "Content-Disposition": f"attachment; filename={word_filename}"
                }
            )
        
    except subprocess.CalledProcessError as e:
        logger.exception(f"Quarto CLI error: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Quarto CLI error: {str(e)}"
        )
    except FileNotFoundError as e:
        logger.exception(f"Quarto CLI not found: {e}")
        raise HTTPException(
            status_code=500,
            detail="Quarto CLI is not installed on the server. Please install Quarto to use this feature."
        )
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# AI Story Endpoint
# ---------------------------------------------------------------------

@app.post("/story",
          summary="Generate AI Data Story",
          description="Generate an AI-powered data story from visualization data.",
          response_description="Generated data story with analysis",
          responses={
              200: {
                  "description": "Data story generated successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "story": "Comprehensive analysis of refugee data...",
                              "visualization_data": {},
                              "metadata": {},
                              "user": {"name": "user@example.com"}
                          }
                      }
                  }
              },
              400: {"description": "Invalid payload or missing required fields"},
              401: {"description": "Authentication required"},
              503: {"description": "MCP server unavailable"}
          })
@limiter.limit("5/minute")
async def create_story(
    request: Request,
    payload: dict,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Generate an AI data story from visualization data.
    
    This endpoint creates a narrative data story based on provided visualization data.
    It uses the generate_ai_data_story MCP tool to transform raw data into a compelling,
    human-readable story suitable for reports and presentations.
    
    Requires Azure AD authentication. Rate limited to 5 requests per minute per IP.
    
    Args:
        payload (dict): Request payload containing:
            - visualization_data (dict, required): Data to visualize, must contain:
                - data: The actual data to visualize
                - structure: Visualization structure and labels
            - title (str, optional): Title for the story
            - context (str, optional): Additional context for the analysis
            - Any other parameters accepted by generate_ai_data_story tool
        user (UserInfo): Authenticated user information (injected by dependency)
    
    Returns:
        dict: A dictionary containing:
            - All fields from the generate_ai_data_story tool result
            - user (dict): Information about the authenticated user
            
        Typical response fields:
            - story (str): The generated narrative story
            - visualization_data (dict): The processed visualization data
            - metadata (dict): Analysis metadata
            - recommendations (list): Suggested actions or insights
    
    Raises:
        HTTPException 400: If visualization_data is missing or invalid
        HTTPException 401: If user is not authenticated
        HTTPException 503: If MCP server is unavailable
        HTTPException 500: For any other errors
    
    Example:
        Request body:
        {
            "visualization_data": {
                "data": [{"year": 2020, "count": 1000}, {"year": 2021, "count": 1500}],
                "structure": {
                    "visualization_type": "line_chart",
                    "labels": {"title": "Refugee Population Over Time"}
                }
            },
            "title": "Refugee Population Trends",
            "context": "Analysis of UNHCR data for policy makers"
        }
    """
    try:
        # Ensure visualization_data is present in the payload
        if "visualization_data" not in payload:
            raise HTTPException(
                status_code=400,
                detail="visualization_data is required"
            )
        
        # If visualization_data exists but doesn't have the required structure
        if not isinstance(payload["visualization_data"], dict):
            raise HTTPException(
                status_code=400,
                detail="visualization_data must be a dictionary"
            )
        
        # Ensure visualization_data has at least a 'data' field
        if "data" not in payload["visualization_data"]:
            raise HTTPException(
                status_code=400,
                detail="visualization_data.data is required"
            )

        result = await call_tool(
            "generate_ai_data_story",
            payload
        )

        return {
            **result,
            "user": user.to_dict()
        }

    except MCPConnectionError as e:
        logger.error(f"MCP connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"MCP server unavailable: {str(e)}"
        )
    except MCPValidationError as e:
        logger.error(f"Validation error: {e}")
        raise HTTPException(
            status_code=400,
            detail=str(e)
        )
    except Exception as e:

        logger.exception(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# Quarto Export
# ---------------------------------------------------------------------

@app.post("/report",
          summary="Create Quarto Report",
          description="Create a Quarto notebook report from a data story.",
          response_description="Created Quarto notebook with UNHCR theme",
          responses={
              200: {
                  "description": "Quarto report created successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "quarto_content": "---\ntitle: Report\n...",
                              "path": "/path/to/report.qmd",
                              "title": "UNHCR Report",
                              "format": "quarto",
                              "metadata": {},
                              "user": {"name": "user@example.com"}
                          }
                      }
                  }
              },
              400: {"description": "Invalid payload"},
              401: {"description": "Authentication required"},
              503: {"description": "MCP server unavailable"}
          })
@limiter.limit("3/minute")
async def create_report(
    request: Request,
    payload: dict,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Create a Quarto notebook report from a data story.
    
    This endpoint generates a Quarto (.qmd) notebook file from a provided story.
    The notebook is configured with UNHCR branding and theme by default, and can
    include optional Python code cells for reproducibility.
    
    Requires Azure AD authentication. Rate limited to 3 requests per minute per IP.
    
    Args:
        payload (dict): Request payload containing:
            - story (str, optional): The data story content to include in the notebook
            - title (str, optional): Title for the report (defaults to "UNHCR Report")
            - Any other parameters accepted by create_quarto_notebook tool
        user (UserInfo): Authenticated user information (injected by dependency)
    
    Returns:
        dict: A dictionary containing:
            - All fields from the create_quarto_notebook tool result
            - user (dict): Information about the authenticated user
            
        Typical response fields:
            - quarto_content (str): The full Quarto markdown content
            - path (str): File path where the notebook was saved (or None)
            - title (str): The resolved notebook title
            - author (str): The resolved author
            - date (str): The resolved date
            - format (str): Always "quarto"
            - metadata (dict): Generation metadata and statistics
    
    Raises:
        HTTPException 401: If user is not authenticated
        HTTPException 503: If MCP server is unavailable
        HTTPException 500: For any other errors
    
    Example:
        Request body:
        {
            "story": "In 2023, the number of refugees from Ukraine reached 1 million...",
            "title": "Ukraine Refugee Crisis Analysis"
        }
    """
    # Prepare inputs for notebook generation
    story = payload.get("story")
    data = payload.get("data")
    title = payload.get("title", "UNHCR Report")
    # Include metadata for template front matter
    from backend.chat import get_analysis_config
    audience = payload.get("audience", "internal")
    document_type = payload.get("document_type", "technical_report")
    analysis_config = get_analysis_config(audience, document_type)
    metadata = {
        "audience": audience,
        "document_type": document_type,
        "analysis_config": analysis_config
    }
    # Call the create_quarto_notebook tool with metadata
    result = await call_tool(
        "create_quarto_notebook",
        {
            "story_content": story,
            "title": title,
            "include_code_cells": True,
            "use_unhcr_theme": True,
            "use_unhcr_style": True,
            "data": data,
            "metadata": metadata
        }
    )
    return {
        **result,
        "user": user.to_dict()
    }


# ---------------------------------------------------------------------
# Suggested Questions
# ---------------------------------------------------------------------

@app.get("/suggestions",
         summary="Get Suggested Questions",
         description="Retrieve a list of suggested analysis questions for users.",
         response_description="List of suggested questions",
         responses={
             200: {
                 "description": "Suggested questions retrieved successfully",
                 "content": {
                     "application/json": {
                         "example": {
                             "suggestions": [
                                 "What are the latest refugee population trends?",
                                 "Show me demographic breakdown by country",
                                 "Analyze RSD decision patterns"
                             ],
                             "user": {"name": "user@example.com"}
                         }
                     }
                 }
             },
             503: {"description": "MCP server unavailable"}
         })
async def suggestions(
    user: UserInfo = Depends(get_optional_user)
):
    """
    Get suggested analysis questions.
    
    This endpoint returns a list of suggested questions that users can ask the
    UNHCR Stat Copilot. These questions are designed to help users discover the types
    of analyses that can be performed with the available data and tools.
    
    This endpoint supports optional authentication. If the user is authenticated,
    their information will be included in the response.
    
    Returns:
        dict: A dictionary containing:
            - All fields from the get_suggested_questions tool result
            - user (dict or None): Information about the authenticated user, or None if not authenticated
            
        Typical response fields:
            - suggestions (list[str]): List of suggested question strings
            - categories (list): Categorized suggestions (if available)
            - user (dict or None): User information
    
    Raises:
        HTTPException 503: If MCP server is unavailable
    
    Note:
        This endpoint does not require authentication but will include user
        information in the response if the user is authenticated.
    """
    try:
        result = await call_tool(
            "get_suggested_questions",
            {}
        )
        return {
            **result,
            "user": user.to_dict() if user.is_authenticated else None
        }
    except MCPConnectionError as e:
        logger.error(f"MCP connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"MCP server unavailable: {str(e)}"
        )


# ---------------------------------------------------------------------
# Guidance
# ---------------------------------------------------------------------

@app.get("/guidance",
         summary="Get Usage Guidance",
         description="Retrieve usage instructions and guidance for the UNHCR Stat Copilot.",
         response_description="Usage guidance and instructions",
         responses={
             200: {
                 "description": "Guidance retrieved successfully",
                 "content": {
                     "application/json": {
                         "example": {
                             "guidance": "Welcome to UNHCR Stat Copilot...",
                             "features": [],
                             "examples": [],
                             "user": {"name": "user@example.com"}
                         }
                     }
                 }
             },
             503: {"description": "MCP server unavailable"}
         })
async def guidance(
    user: UserInfo = Depends(get_optional_user)
):
    """
    Get usage guidance for the UNHCR Stat Copilot.
    
    This endpoint returns comprehensive usage instructions, feature descriptions,
    and examples to help users understand how to effectively use the UNHCR Stat Copilot
    for data analysis and reporting.
    
    This endpoint supports optional authentication. If the user is authenticated,
    their information will be included in the response.
    
    Returns:
        dict: A dictionary containing:
            - All fields from the get_usage_guidance tool result
            - user (dict or None): Information about the authenticated user, or None if not authenticated
            
        Typical response fields:
            - guidance (str): General usage instructions
            - features (list): List of available features and their descriptions
            - examples (list): Example queries and use cases
            - best_practices (list): Recommended practices for optimal results
            - limitations (list): Known limitations and workarounds
            - user (dict or None): User information
    
    Raises:
        HTTPException 503: If MCP server is unavailable
    
    Note:
        This endpoint does not require authentication but will include user
        information in the response if the user is authenticated.
    """
    try:
        result = await call_tool(
            "get_usage_guidance",
            {}
        )
        return {
            **result,
            "user": user.to_dict() if user.is_authenticated else None
        }
    except MCPConnectionError as e:
        logger.error(f"MCP connection error: {e}")
        raise HTTPException(
            status_code=503,
            detail=f"MCP server unavailable: {str(e)}"
        )


@app.get("/analysis-config",
          summary="Get Analysis Configuration",
          description="Retrieve the complete analysis configuration including audience-specific document types.",
          response_description="Complete analysis configuration",
          responses={
              200: {
                  "description": "Analysis configuration retrieved successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "status": "success",
                              "config": {
                                  "audiences": {
                                      "policy_makers": {"document_types": [], "default": ""}
                                  }
                              }
                          }
                      }
                  }
              }
          })
async def get_analysis_config():
    """
    Get the complete analysis configuration for audience-specific document types.
    
    This endpoint returns the full ANALYSIS_CONFIG dictionary which contains
    configuration for all supported audiences and their corresponding document types.
    This is useful for frontend applications to discover available options.
    
    This endpoint does not require authentication.
    
    Returns:
        dict: A dictionary containing:
            - status (str): "success"
            - config (dict): The complete analysis configuration with:
                - audiences: Dictionary mapping audience names to their configurations
                - Each audience configuration includes document_types and default settings
    
    Example:
        The config structure includes:
        {
            "audiences": {
                "policy_makers": {
                    "document_types": ["executive_summary", "briefing_note", "policy_report"],
                    "default": "executive_summary",
                    "style": "concise",
                    "length": "short"
                },
                "technical_experts": {
                    "document_types": ["technical_report", "data_analysis", "methodology_note"],
                    "default": "technical_report",
                    "style": "detailed",
                    "length": "long"
                }
            }
        }
    """
    from backend.models.analysis_config import analysis_config_model, AudienceEnum

    return {"status": "success", "config": analysis_config_model.config}


@app.get("/analysis-config/{audience}",
          summary="Get Audience Configuration",
          description="Retrieve analysis configuration for a specific audience.",
          response_description="Audience-specific analysis configuration",
          responses={
              200: {
                  "description": "Audience configuration retrieved successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "status": "success",
                              "audience": "policy_makers",
                              "default_document_type": "executive_summary",
                              "available_document_types": ["executive_summary", "briefing_note", "policy_report"]
                          }
                      }
                  }
              },
              400: {"description": "Invalid audience specified"},
              404: {"description": "Audience not found"}
          })
async def get_audience_config(audience: AudienceEnum):
    """
    Get the analysis configuration for a specific audience.
    
    This endpoint returns the configuration for a specific audience, including
    the available document types and the default document type for that audience.
    This is useful for frontend applications to populate dropdown menus and
    provide intelligent defaults based on the selected audience.
    
    This endpoint does not require authentication.
    
    Args:
        audience (str): The audience name to get configuration for. Valid values include:
            - policy_makers
            - technical_experts
            - field_offices
            - donors
            - general_public
            - academic_researchers
    
    Returns:
        dict: A dictionary containing:
            - status (str): "success"
            - audience (str): The requested audience name
            - default_document_type (str): The default document type for this audience
            - available_document_types (list[str]): List of all available document types
              for this audience
    
    Raises:
        HTTPException 400: If the audience name is invalid or not recognized
    
    Example:
        Request: GET /analysis-config/policy_makers
        
        Response:
        {
            "status": "success",
            "audience": "policy_makers",
            "default_document_type": "executive_summary",
            "available_document_types": [
                "executive_summary",
                "briefing_note", 
                "policy_report",
                "decision_brief"
            ]
        }
    """
    # Return audience-specific configuration using the central model
    config = analysis_config_model.get_config(audience, None)
    return {
        "status": "success",
        "audience": config["audience"],
        "default_document_type": config["default_type"],
        "available_document_types": list(config["config"].keys()),
    }


# ---------------------------------------------------------------------
# Analysis Rating
# ---------------------------------------------------------------------

class RatingRequest(BaseModel):
    analysis_id: str
    rating: int
    feedback: Optional[str] = None


@app.post("/analysis/rate",
          summary="Rate an Analysis",
          description="Submit a rating and optional feedback for a specific analysis. Users can rate analyses with 1-5 stars. For ratings less than 4 stars, users are encouraged to provide feedback.",
          response_description="Confirmation of rating submission",
          responses={
              200: {
                  "description": "Rating submitted successfully",
                  "content": {
                      "application/json": {
                          "example": {
                              "status": "success",
                              "message": "Rating saved successfully",
                              "analysis_id": "abc123",
                              "rating": 4,
                              "feedback": "Great analysis!"
                          }
                      }
                  }
              },
              400: {"description": "Invalid rating value or missing analysis_id"},
              404: {"description": "Analysis not found"},
              500: {"description": "Internal server error"}
          })
async def rate_analysis(rating_data: RatingRequest):
    """
    Submit a rating for an analysis.
    
    This endpoint allows users to rate analyses with a 1-5 star rating.
    When users give less than 4 stars, they should provide feedback explaining
    why the rating is low. The rating and feedback are automatically saved
    in the analysis log for quality improvement.
    
    Args:
        rating_data (RatingRequest): The rating data containing:
            - analysis_id (str, required): The unique identifier of the analysis being rated
            - rating (int, required): The rating score (1-5)
            - feedback (str, optional): Feedback text for ratings less than 4 stars
    
    Returns:
        dict: A confirmation message with the submitted rating details
    
    Raises:
        HTTPException 400: If rating is not between 1 and 5, or analysis_id is missing
        HTTPException 404: If the analysis with the given ID is not found
        HTTPException 500: If there's an internal server error saving the rating
    """
    try:
        # Validate the rating data
        if not rating_data.analysis_id:
            raise HTTPException(
                status_code=400,
                detail="analysis_id is required"
            )
        
        if rating_data.rating < 1 or rating_data.rating > 5:
            raise HTTPException(
                status_code=400,
                detail="Rating must be between 1 and 5 stars"
            )
        
        # Save the rating to the analysis log
        success = save_rating(
            rating_data.analysis_id,
            rating_data.rating,
            rating_data.feedback
        )
        
        if not success:
            raise HTTPException(
                status_code=404,
                detail=f"Analysis with ID {rating_data.analysis_id} not found"
            )
        
        return {
            "status": "success",
            "message": "Rating saved successfully",
            "analysis_id": rating_data.analysis_id,
            "rating": rating_data.rating,
            "feedback": rating_data.feedback,
            "timestamp": datetime.now().isoformat()
        }
        
    except HTTPException:
        raise
    except Exception as e:
        logger.exception(f"Failed to save rating: {e}")
        raise HTTPException(
            status_code=500,
            detail=f"Internal server error: {str(e)}"
        )


# ---------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------

@app.get("/",
         summary="API Root",
         description="Root endpoint providing an overview of the UNHCR Stat Copilot API.",
         response_description="API overview and available endpoints",
         responses={
             200: {
                 "description": "API root information",
                 "content": {
                     "application/json": {
                         "example": {
                             "application": "UNHCR Stat Copilot ",
                             "version": "1.0.0",
                             "mcp": "/mcp",
                             "chat": "/chat",
                             "docs": "/docs"
                         }
                     }
                 }
             }
         })
async def root():
    """
    API root endpoint.
    
    This is the base endpoint for the UNHCR Stat Copilot  API. It provides a simple overview
    of the application and links to the main endpoints and documentation.
    
    This endpoint does not require authentication and is available to all users.
    
    Returns:
        dict: A dictionary containing:
            - application (str): The application name ("UNHCR Stat Copilot ")
            - version (str): The current API version
            - mcp (str): Path to the MCP endpoint for Model Context Protocol access
            - chat (str): Path to the chat endpoint for natural language queries
            - docs (str): Path to the API documentation (OpenAPI/Swagger)
    
    Note:
        For full API documentation, navigate to /docs (Swagger UI) or /openapi.json
        for the OpenAPI specification.
    """
    result = {
        "application": "UNHCR Stat Copilot ",
        "version": "1.0.0",
        "mcp": "/mcp",
        "chat": "/chat",
        "docs": "/docs"
    }
    
    # Add CrewAI info if enabled
    if CREWAI_ENABLED:
        result["crewai"] = "/crewai"
        result["crewai_enabled"] = True
    else:
        result["crewai_enabled"] = False
    
    return result
