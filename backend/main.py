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
from backend.server import create_server

# Load environment variables from .env file
load_dotenv()

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
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
@app.get("/health", include_in_schema=False)
async def health():
    return {
        "status": "healthy",
        "service": "unhcr-statistics-copilot",
        "frontend": os.path.exists(frontend_dist_path),
        "api": "available"
    }

# Update root endpoint to mention frontend
original_root = app.routes[-1]  # Get the original root endpoint
@app.get("/")
async def read_root():
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
        port=8080,
        reload=True,
        log_level="info"
    )