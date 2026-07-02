from __future__ import annotations

import json
import logging
import os
from typing import Any

from dotenv import load_dotenv
from fastapi import Depends, FastAPI, HTTPException, Request, Response
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel

# Load environment variables from .env file
load_dotenv()

# Rate limiting
from slowapi import Limiter
from slowapi.util import get_remote_address

from backend.server import create_server
from backend.chat import process_chat_message
from backend.llm import safe_tool_selection
from backend.charts import generate_chart   
from backend.mcp_bridge import call_tool, MCPConnectionError, MCPValidationError
from backend.history import save_analysis, get_all_analyses, get_analysis, save_quarto_analysis, get_quarto_analyses
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

app.add_exception_handler(429, _rate_limit_exceeded_handler)

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
    Helper function to create properly formatted visualization_data
    for the generate_ai_data_story tool.
    
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
mcp_server.settings.streamable_http_path = "/"
mcp_app = mcp_server.streamable_http_app()

@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_server.session_manager.run():
        yield

app = FastAPI(
    title="UNHCR Copilot",
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

try:
    # FastMCP HTTP transport
    app.mount(
        "/mcp",
        mcp_app
    )
except Exception as e:
    logger.warning(
        "Could not mount MCP endpoint: %s",
        e
    )

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


class ToolRequest(BaseModel):
    tool: str
    arguments: dict[str, Any]


# ---------------------------------------------------------------------
# Health
# ---------------------------------------------------------------------

@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "unhcr-copilot"
    }


# ---------------------------------------------------------------------
# MCP Tool Discovery
# ---------------------------------------------------------------------

@app.get("/tools")
async def tools():

    return {
        "tools": [
            "get_population_data",
            "get_demographics_data",
            "get_rsd_applications",
            "get_rsd_decisions",
            "get_solutions",
            "get_country_key_figures",
            "get_population_trends",
            "get_demographic_breakdown",
            "extract_visualization_structure",
            "analyze_data_statistics",
            "generate_visualization_description",
            "generate_ai_data_story",
            "get_usage_guidance",
            "get_suggested_questions",
            "apply_analysis_guardrails",
            "create_quarto_notebook",
        ]
    }


# ---------------------------------------------------------------------
# Direct Tool Execution
# ---------------------------------------------------------------------

@app.post("/tool")
@limiter.limit("10/minute")
async def execute_tool(
    request: Request,
    tool_request: ToolRequest,
    user: UserInfo = Depends(verify_azure_auth)
):

    try:

        result = await call_tool(
            tool_request.tool,
            tool_request.arguments
        )

        return {
            "tool": tool_request.tool,
            "result": result,
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
# Chat Endpoint
# ---------------------------------------------------------------------

@app.post("/chat")
@limiter.limit("5/minute")
async def chat(
    request: Request,
    chat_request: ChatRequest,
    user: UserInfo = Depends(verify_azure_auth)
):

    try:

        result = await process_chat_message(
            chat_request.message,
            origin=chat_request.origin,
            destination=chat_request.destination,
            topic=chat_request.topic,
            timespan=chat_request.timespan,
            audience=chat_request.audience,
            document_type=chat_request.document_type,
            style=chat_request.style
        )

        # Save both the analysis metadata and the Quarto file
        quarto_types = ["quarto_notebook", "comprehensive_quarto", "basic_quarto_fallback"]
        if result.get("analysis_type") in quarto_types:
            # Save the Quarto file directly
            save_quarto_analysis(
                result["quarto_content"],
                result["quarto_metadata"]
            )
        else:
            # Fallback to the original JSON saving for compatibility
            save_analysis(result)

        return {
            **result,
            "user": user.to_dict()
        }

    except Exception as e:

        logger.exception(e)

        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# ---------------------------------------------------------------------
# Analysis History Endpoints
# ---------------------------------------------------------------------

@app.get("/history")
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


@app.get("/history/{analysis_id}")
async def get_single_analysis(analysis_id: str):
    """
    Get a specific analysis by ID
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


@app.get("/quarto/{analysis_id}")
async def download_quarto_analysis(analysis_id: str):
    """
    Download a Quarto analysis file by ID
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
# AI Story Endpoint
# ---------------------------------------------------------------------

@app.post("/story")
@limiter.limit("5/minute")
async def create_story(
    request: Request,
    payload: dict,
    user: UserInfo = Depends(verify_azure_auth)
):

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

@app.post("/report")
@limiter.limit("3/minute")
async def create_report(
    request: Request,
    payload: dict,
    user: UserInfo = Depends(verify_azure_auth)
):

    story = payload.get("story")

    title = payload.get(
        "title",
        "UNHCR Report"
    )

    result = await call_tool(
        "create_quarto_notebook",
        {
            "story_content": story,
            "title": title,
            "include_code_cells": True,
            "use_unhcr_theme": True,
            "use_unhcr_style": True,
        }
    )

    return {
        **result,
        "user": user.to_dict()
    }


# ---------------------------------------------------------------------
# Suggested Questions
# ---------------------------------------------------------------------

@app.get("/suggestions")
async def suggestions(
    user: UserInfo = Depends(get_optional_user)
):

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

@app.get("/guidance")
async def guidance(
    user: UserInfo = Depends(get_optional_user)
):

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


@app.get("/analysis-config")
async def get_analysis_config():
    """
    Get the complete analysis configuration for audience-specific document types.
    """
    from backend.chat import ANALYSIS_CONFIG
    return {"status": "success", "config": ANALYSIS_CONFIG}


@app.get("/analysis-config/{audience}")
async def get_audience_config(audience: str):
    """
    Get the analysis configuration for a specific audience.
    """
    from backend.chat import get_analysis_config, get_available_document_types, get_default_document_type
    
    try:
        available_types = get_available_document_types(audience)
        default_type = get_default_document_type(audience)
        
        return {
            "status": "success",
            "audience": audience,
            "default_document_type": default_type,
            "available_document_types": available_types
        }
    except Exception as e:
        logger.exception(e)
        raise HTTPException(
            status_code=400,
            detail=f"Invalid audience: {audience}"
        )


# ---------------------------------------------------------------------
# Root
# ---------------------------------------------------------------------

@app.get("/")
async def root():

    return {
        "application": "UNHCR Copilot",
        "version": "1.0.0",
        "mcp": "/mcp",
        "chat": "/chat",
        "docs": "/docs"
    }