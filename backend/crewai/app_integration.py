"""
CrewAI FastAPI Endpoint Integration for UNHCR Statistics Copilot

This module provides FastAPI endpoints for CrewAI-based analysis workflows.
These endpoints can be used alongside or instead of the MCP-based endpoints.

To integrate with the main app, import and call register_crewai_endpoints(app).
"""

import logging
import time
from datetime import datetime
from typing import Any, Dict, Optional

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from backend.crewai.manager import CrewAIManager, WorkflowType, get_manager
from backend.crewai.crews import DataCrew, AnalysisCrew, StoryCrew, NotebookCrew, MasterCrew
from backend.crewai.migration import get_migration_router, MigrationMode, MigrationRouter
from backend.crewai.config import AudienceConfigManager
from backend.auth import UserInfo, verify_azure_auth, get_optional_user

logger = logging.getLogger(__name__)

# Create a router for CrewAI endpoints
crewai_router = APIRouter(prefix="/crewai", tags=["CrewAI"])


# -------------------------------------------------------------------------
# Request Models
# -------------------------------------------------------------------------

class CrewAIChatRequest(BaseModel):
    """Request model for CrewAI chat endpoint."""
    message: str = Field(..., description="The user's query or analysis request")
    audience: str = Field(default="internal", description="Target audience for the analysis")
    document_type: Optional[str] = Field(default=None, description="Type of document to generate")
    workflow_type: str = Field(default="full_analysis", description="Type of workflow to execute")
    use_rag: bool = Field(default=True, description="Whether to use RAG enrichment")
    include_notebook: bool = Field(default=True, description="Whether to generate a Quarto notebook")
    output_path: Optional[str] = Field(default=None, description="Output path for the notebook")
    
    class Config:
        json_schema_extra = {
            "example": {
                "message": "Show me refugee population trends in France over the past 10 years",
                "audience": "policy_makers",
                "document_type": "executive_summary",
                "workflow_type": "full_analysis",
                "use_rag": True,
                "include_notebook": True
            }
        }


class CrewAIAnalysisRequest(BaseModel):
    """Request model for CrewAI analysis endpoint."""
    question: str = Field(..., description="The analysis question")
    audience: str = Field(default="internal", description="Target audience")
    document_type: Optional[str] = Field(default=None, description="Document type")
    use_rag: bool = Field(default=True, description="Use RAG enrichment")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "What are the refugee trends in Syria?",
                "audience": "internal",
                "document_type": "technical_report",
                "use_rag": True
            }
        }


class CrewAIDataRequest(BaseModel):
    """Request model for CrewAI data fetching endpoint."""
    question: str = Field(..., description="The data query")
    audience: str = Field(default="internal", description="Target audience")
    document_type: Optional[str] = Field(default=None, description="Document type")
    parameters: Optional[Dict[str, Any]] = Field(default=None, description="Additional parameters")
    
    class Config:
        json_schema_extra = {
            "example": {
                "question": "Get population data for Syria in 2023",
                "audience": "internal",
                "parameters": {"year": 2023, "coo": "SYR"}
            }
        }


class MigrationConfigRequest(BaseModel):
    """Request model for updating migration configuration."""
    mode: Optional[str] = Field(default=None, description="Migration mode: mcp_only, crewai_only, dual_run, hybrid, fallback")
    strategy: Optional[str] = Field(default=None, description="Routing strategy")
    mcp_percentage: Optional[float] = Field(default=None, description="Percentage of traffic to route to MCP")
    crewai_percentage: Optional[float] = Field(default=None, description="Percentage of traffic to route to CrewAI")
    
    class Config:
        json_schema_extra = {
            "example": {
                "mode": "hybrid",
                "strategy": "percentage",
                "mcp_percentage": 50.0,
                "crewai_percentage": 50.0
            }
        }


# -------------------------------------------------------------------------
# CrewAI Endpoints
# -------------------------------------------------------------------------

@crewai_router.post("/chat",
                  summary="CrewAI Chat",
                  description="Process a chat message using CrewAI agents for analysis and response generation.",
                  response_description="Chat response with analysis results from CrewAI")
async def crewai_chat(
    request: Request,
    chat_request: CrewAIChatRequest,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Process a chat message using CrewAI agents.
    
    This endpoint provides an alternative to the MCP-based /chat endpoint,
    using CrewAI agents for tool orchestration and analysis.
    
    The CrewAI approach provides:
    - Multi-agent coordination for complex workflows
    - Better error handling and recovery
    - Built-in observability and metrics
    - Easier extension and customization
    
    Args:
        chat_request: The chat message request
        user: Authenticated user information
        
    Returns:
        Analysis result from CrewAI workflow
    """
    start_time = time.time()
    
    try:
        # Get CrewAI manager
        manager = get_manager()
        
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(chat_request.audience)
        document_type = chat_request.document_type
        if document_type:
            document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        else:
            document_type = AudienceConfigManager.get_default_type(audience)
        
        # Convert workflow_type to enum
        try:
            workflow_type = WorkflowType(chat_request.workflow_type)
        except ValueError:
            workflow_type = WorkflowType.FULL_ANALYSIS
        
        # Execute workflow
        result = manager.execute_workflow(
            question=chat_request.message,
            audience=audience,
            document_type=document_type,
            workflow_type=workflow_type,
            use_rag=chat_request.use_rag,
            include_notebook=chat_request.include_notebook,
            output_path=chat_request.output_path
        )
        
        duration = time.time() - start_time
        result['crewai_duration'] = duration
        result['execution_source'] = 'crewai'
        
        # Save analysis (similar to MCP chat endpoint)
        from backend.history import save_analysis, save_quarto_analysis
        
        quarto_types = ["quarto_notebook", "comprehensive_quarto", "basic_quarto_fallback"]
        if result.get("analysis_type") in quarto_types or result.get("notebook"):
            quarto_metadata = result.get("quarto_metadata", result.get("metadata", {}))
            save_result = save_quarto_analysis(
                result.get("quarto_content", result.get("notebook", {}).get("content", "")),
                quarto_metadata
            )
            result["id"] = save_result.get("id")
            result["filepath"] = save_result.get("filepath")
        else:
            save_analysis(result)
        
        return {
            **result,
            "user": user.to_dict()
        }
        
    except Exception as e:
        logger.exception(f"CrewAI chat failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@crewai_router.post("/analyze",
                  summary="CrewAI Analysis",
                  description="Execute a data analysis workflow using CrewAI agents.")
async def crewai_analyze(
    request: CrewAIAnalysisRequest
):
    """
    Execute a data analysis workflow using CrewAI.
    
    This endpoint performs data fetching and statistical analysis using
    CrewAI agents, returning comprehensive analysis results.
    
    Args:
        request: Analysis request with question and parameters
        
    Returns:
        Analysis results including statistics, insights, and visualizations
    """
    start_time = time.time()
    
    try:
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(request.audience)
        document_type = request.document_type
        if document_type:
            document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        else:
            document_type = AudienceConfigManager.get_default_type(audience)
        
        # Use MasterCrew for full workflow
        master_crew = MasterCrew(
            audience=audience,
            document_type=document_type
        )
        
        result = master_crew.execute_full_workflow(
            question=request.question,
            use_rag=request.use_rag,
            include_notebook=False
        )
        
        duration = time.time() - start_time
        result['crewai_duration'] = duration
        result['execution_source'] = 'crewai'
        
        return result
        
    except Exception as e:
        logger.exception(f"CrewAI analysis failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@crewai_router.post("/data",
                  summary="CrewAI Data Fetching",
                  description="Fetch UNHCR data using CrewAI data agents.")
async def crewai_fetch_data(
    request: CrewAIDataRequest
):
    """
    Fetch UNHCR data using CrewAI agents.
    
    This endpoint uses CrewAI data specialist agents to retrieve
    population, demographic, RSD, and other UNHCR data.
    
    Args:
        request: Data request with query and parameters
        
    Returns:
        Fetched data from various UNHCR sources
    """
    start_time = time.time()
    
    try:
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(request.audience)
        document_type = request.document_type
        if document_type:
            document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        else:
            document_type = AudienceConfigManager.get_default_type(audience)
        
        # Use DataCrew to fetch data
        data_crew = DataCrew(
            audience=audience,
            document_type=document_type
        )
        
        result = data_crew.fetch_all_data(
            question=request.question,
            parameters=request.parameters or {}
        )
        
        duration = time.time() - start_time
        result['crewai_duration'] = duration
        result['execution_source'] = 'crewai'
        
        return result
        
    except Exception as e:
        logger.exception(f"CrewAI data fetching failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


@crewai_router.post("/notebook",
                  summary="CrewAI Notebook Generation",
                  description="Generate a Quarto notebook from story content using CrewAI.")
async def crewai_generate_notebook(
    story_content: str,
    audience: str = "internal",
    document_type: Optional[str] = None,
    output_path: Optional[str] = None
):
    """
    Generate a Quarto notebook using CrewAI.
    
    This endpoint uses the CrewAI NotebookCrew to create
    well-documented Quarto notebooks from analysis results.
    
    Args:
        story_content: The story/narrative content
        audience: Target audience
        document_type: Document type
        output_path: Optional output path
        
    Returns:
        Generated Quarto notebook content and metadata
    """
    start_time = time.time()
    
    try:
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        if document_type:
            document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        else:
            document_type = AudienceConfigManager.get_default_type(audience)
        
        # Use NotebookCrew
        notebook_crew = NotebookCrew(
            audience=audience,
            document_type=document_type
        )
        
        result = notebook_crew.create_quarto_notebook(
            story_content=story_content,
            audience=audience,
            document_type=document_type,
            output_path=output_path
        )
        
        duration = time.time() - start_time
        result['crewai_duration'] = duration
        result['execution_source'] = 'crewai'
        
        return result
        
    except Exception as e:
        logger.exception(f"CrewAI notebook generation failed: {e}")
        raise HTTPException(
            status_code=500,
            detail=str(e)
        )


# -------------------------------------------------------------------------
# Migration Endpoints
# -------------------------------------------------------------------------

@crewai_router.get("/migration/metrics",
                 summary="Migration Metrics",
                 description="Get metrics for the CrewAI migration.")
async def get_migration_metrics():
    """
    Get current migration metrics.
    
    Returns metrics about:
    - Request counts for MCP and CrewAI
    - Success/failure rates
    - Execution times
    - Comparison results (for dual-run mode)
    """
    router = get_migration_router()
    return router.get_metrics()


@crewai_router.post("/migration/config",
                  summary="Update Migration Configuration",
                  description="Update the CrewAI migration configuration.")
async def update_migration_config(
    config: MigrationConfigRequest
):
    """
    Update migration configuration.
    
    This endpoint allows dynamic configuration of the migration mode
    and routing strategy without restarting the application.
    
    Args:
        config: Migration configuration updates
        
    Returns:
        Updated configuration and confirmation message
    """
    router = get_migration_router()
    
    if config.mode:
        router.set_mode(config.mode)
    
    if config.strategy:
        router.set_strategy(config.strategy)
    
    # Update percentages if provided
    if config.mcp_percentage is not None:
        router.config.mcp_percentage = config.mcp_percentage
    
    if config.crewai_percentage is not None:
        router.config.crewai_percentage = config.crewai_percentage
    
    return {
        "status": "success",
        "message": "Migration configuration updated",
        "config": {
            "mode": router.config.mode.value,
            "strategy": router.config.strategy.value,
            "mcp_percentage": router.config.mcp_percentage,
            "crewai_percentage": router.config.crewai_percentage
        }
    }


@crewai_router.post("/migration/reset",
                  summary="Reset Migration Metrics",
                  description="Reset all migration metrics.")
async def reset_migration_metrics():
    """
    Reset all migration metrics.
    
    This clears all tracked metrics and starts fresh.
    """
    router = get_migration_router()
    router.reset_metrics()
    
    return {
        "status": "success",
        "message": "Migration metrics reset"
    }


@crewai_router.get("/migration/mode",
                 summary="Get Current Migration Mode",
                 description="Get the current migration mode and configuration.")
async def get_migration_mode():
    """
    Get the current migration mode.
    
    Returns:
        Current migration mode and configuration
    """
    router = get_migration_router()
    return {
        "mode": router.config.mode.value,
        "strategy": router.config.strategy.value,
        "mcp_percentage": router.config.mcp_percentage,
        "crewai_percentage": router.config.crewai_percentage,
        "crewai_tools": router.config.crewai_tools,
        "mcp_tools": router.config.mcp_tools,
        "crewai_audiences": router.config.crewai_audiences,
        "mcp_audiences": router.config.mcp_audiences
    }


# -------------------------------------------------------------------------
# Manager Endpoints
# -------------------------------------------------------------------------

@crewai_router.get("/manager/metrics",
                 summary="Manager Metrics",
                 description="Get CrewAI manager metrics.")
async def get_manager_metrics():
    """
    Get CrewAI manager metrics.
    
    Returns metrics about:
    - Total workflows executed
    - Completed/failed workflows
    - Agent execution metrics
    - Workflow execution times
    """
    manager = get_manager()
    return manager.get_metrics()


@crewai_router.post("/manager/reset",
                  summary="Reset Manager Metrics",
                  description="Reset CrewAI manager metrics.")
async def reset_manager_metrics():
    """
    Reset CrewAI manager metrics.
    """
    manager = get_manager()
    manager.reset_metrics()
    
    return {
        "status": "success",
        "message": "Manager metrics reset"
    }


@crewai_router.get("/manager/agents",
                 summary="List Agents",
                 description="List all initialized CrewAI agents.")
async def list_agents():
    """
    List all initialized CrewAI agents.
    
    Returns:
        List of agent names and their status
    """
    manager = get_manager()
    return {
        "agents": manager.list_agents(),
        "count": len(manager.list_agents())
    }


@crewai_router.get("/manager/health",
                 summary="Manager Health Check",
                 description="Check the health of the CrewAI manager.")
async def manager_health():
    """
    Check CrewAI manager health.
    
    Returns:
        Health status and initialization info
    """
    manager = get_manager()
    return {
        "status": "healthy",
        "initialized": manager._initialized,
        "agent_count": len(manager.list_agents()),
        "uptime_seconds": (datetime.now() - manager.start_time).total_seconds()
    }


# -------------------------------------------------------------------------
# Integration Function
# -------------------------------------------------------------------------

def register_crewai_endpoints(app):
    """
    Register CrewAI endpoints with a FastAPI app.
    
    This function should be called from the main app.py to integrate
    CrewAI endpoints.
    
    Args:
        app: FastAPI application instance
    """
    app.include_router(crewai_router)
    logger.info("CrewAI endpoints registered")


def get_crewai_router():
    """
    Get the CrewAI router for manual registration.
    
    Returns:
        APIRouter instance with all CrewAI endpoints
    """
    return crewai_router
