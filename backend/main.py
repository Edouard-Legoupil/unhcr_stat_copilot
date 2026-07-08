#!/usr/bin/env python3
"""
UNHCR Statistics Copilot - Main Application Entry Point

This module serves as the main entry point for the FastAPI application,
serving both the API endpoints and static frontend files.
"""

from fastapi import FastAPI
from fastapi.staticfiles import StaticFiles
import os
import logging
from dotenv import load_dotenv
from backend.app import app as backend_app
from backend.mcp.server import create_server

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)

# Configure file-based logging for persistence
from backend.mcp.observability.logging import configure_logging
configure_logging(
    level=os.getenv("LOG_LEVEL", "INFO"),
    log_file="logs/unhcr_stat_copilot.log"
)

logger = logging.getLogger(__name__)

# Use the existing backend app as the main application
app = backend_app

# CORS is already configured in backend_app, no need to add again

# Mount static frontend files at the root
frontend_dist_path = "/app/frontend/dist"
if os.path.exists(frontend_dist_path):
    logger.info(f"Mounting frontend static files from {frontend_dist_path}")
    # Mount frontend at root, but let API routes take precedence
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
else:
    logger.warning(f"Frontend static files not found at {frontend_dist_path}")

# Add health check endpoint
@app.get("/health",
         include_in_schema=False,
         summary="Health Check",
         description="Check the health status of the UNHCR Statistics Copilot service including frontend and API availability.")
async def health():
    """
    Health check endpoint for the UNHCR Statistics Copilot service.
    
    This endpoint is excluded from the OpenAPI schema (include_in_schema=False)
    but provides a comprehensive health check that verifies:
    - Overall service health
    - Frontend static files availability
    - API availability
    
    This endpoint does not require authentication and is available to all users.
    
    Returns:
        dict: A dictionary containing:
            - status (str): "healthy" if service is running properly
            - service (str): The service name ("unhcr-statistics-copilot")
            - frontend (bool): True if frontend static files are mounted
            - api (str): API status ("available")
    """
    return {
        "status": "healthy",
        "service": "unhcr-statistics-copilot",
        "frontend": os.path.exists(frontend_dist_path),
        "api": "available"
    }

# Update root endpoint to mention frontend
original_root = app.routes[-1]  # Get the original root endpoint

@app.get("/",
         summary="API Root with Frontend Info",
         description="Root endpoint providing an overview of the UNHCR Stat Copilot  API with frontend availability information.")
async def read_root():
    """
    API root endpoint with frontend information.
    
    This endpoint extends the original root endpoint from backend.app to include
    information about frontend static files availability. It provides a comprehensive
    overview of the application including API endpoints and frontend serving status.
    
    This endpoint does not require authentication and is available to all users.
    
    Returns:
        dict: A dictionary containing:
            - application (str): The application name ("UNHCR Stat Copilot ")
            - version (str): The current API version
            - mcp (str): Path to the MCP endpoint
            - chat (str): Path to the chat endpoint
            - docs (str): Path to the API documentation
            - frontend (str): Path to frontend or "Not mounted"
            - health (str): Path to health check endpoint
    """
    original_response = await original_root.endpoint()
    original_response["frontend"] = "/" if os.path.exists(frontend_dist_path) else "Not mounted"
    original_response["health"] = "/health"
    return original_response

if __name__ == "__main__":
    import uvicorn
    logger.info("Starting UNHCR Statistics Copilot server...")
    uvicorn.run(
        "backend.main:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )