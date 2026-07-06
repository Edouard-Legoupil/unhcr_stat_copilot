"""
Prometheus metrics for UNHCR MCP Server.

This module provides Prometheus metrics for monitoring server health,
performance, and error rates.
"""

import os
from pathlib import Path
from typing import Optional

from prometheus_client import Counter, Histogram, Gauge, generate_latest

# Configuration for file-based metrics storage
METRICS_FILE_ENABLED = os.getenv("METRICS_FILE_ENABLED", "false").lower() == "true"
METRICS_FILE_PATH = Path(os.getenv("METRICS_FILE_PATH", "metrics/prometheus.metrics"))

# Ensure metrics directory exists if file storage is enabled
if METRICS_FILE_ENABLED:
    METRICS_FILE_PATH.parent.mkdir(parents=True, exist_ok=True)

# Request counters
tool_requests_total = Counter(
    'unhcr_mcp_tool_requests_total',
    'Total number of MCP tool requests',
    ['tool_name', 'status']
)

tool_errors_total = Counter(
    'unhcr_mcp_tool_errors_total',
    'Total number of MCP tool errors',
    ['tool_name', 'error_type']
)

# Latency tracking
tool_latency_seconds = Histogram(
    'unhcr_mcp_tool_latency_seconds',
    'Latency of MCP tool requests in seconds',
    ['tool_name'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10, 30, 60, 120]
)

# Active requests gauge (use Gauge for values that can go up and down)
active_tool_requests = Gauge(
    'unhcr_mcp_active_tool_requests',
    'Number of active tool requests',
    ['tool_name']
)

# Chat/API request counters
chat_requests_total = Counter(
    'unhcr_mcp_chat_requests_total',
    'Total number of chat/API requests',
    ['endpoint', 'status']
)

chat_latency_seconds = Histogram(
    'unhcr_mcp_chat_latency_seconds',
    'Latency of chat/API requests in seconds',
    ['endpoint'],
    buckets=[0.01, 0.05, 0.1, 0.5, 1, 2, 5, 10]
)


def monitor_tool(tool_name: str):
    """
    Called when a tool request starts.
    
    Args:
        tool_name: The name of the tool being called
    """
    tool_requests_total.labels(tool_name=tool_name, status='started').inc()
    active_tool_requests.labels(tool_name=tool_name).inc()


def complete_tool(tool_name: str, status: str = 'success'):
    """
    Called when a tool request completes.
    
    Args:
        tool_name: The name of the tool that was called
        status: The completion status (success, timeout, error, etc.)
    """
    tool_requests_total.labels(tool_name=tool_name, status=status).inc()
    active_tool_requests.labels(tool_name=tool_name).dec()


def tool_error(tool_name: str, error_type: str):
    """
    Called when a tool request fails.
    
    Args:
        tool_name: The name of the tool that was called
        error_type: The type of error that occurred
    """
    tool_errors_total.labels(tool_name=tool_name, error_type=error_type).inc()


def monitor_chat(endpoint: str):
    """
    Called when a chat/API request starts.
    
    Args:
        endpoint: The endpoint being called
    """
    chat_requests_total.labels(endpoint=endpoint, status='started').inc()


def complete_chat(endpoint: str, status: str = 'success'):
    """
    Called when a chat/API request completes.
    
    Args:
        endpoint: The endpoint that was called
        status: The completion status (success, error, etc.)
    """
    chat_requests_total.labels(endpoint=endpoint, status=status).inc()


def prometheus_metrics() -> bytes:
    """
    Generate Prometheus metrics in the standard format.
    
    If METRICS_FILE_ENABLED is True, also saves metrics to the configured file path.
    
    Returns:
        Bytes containing Prometheus-formatted metrics
    """
    metrics_bytes = generate_latest()
    
    # Save to file if enabled
    if METRICS_FILE_ENABLED:
        try:
            METRICS_FILE_PATH.write_bytes(metrics_bytes)
        except Exception as e:
            # Don't fail if we can't write to file
            pass
    
    return metrics_bytes
