"""
Observability module for UNHCR MCP Server.

This module provides logging and metrics for monitoring the MCP server.
"""

from backend.mcp.observability.logging import configure_logging, get_logger
from backend.mcp.observability.metrics import (
    tool_requests_total,
    tool_errors_total,
    tool_latency_seconds,
    active_tool_requests,
    chat_requests_total,
    chat_latency_seconds,
    monitor_tool,
    complete_tool,
    tool_error,
    monitor_chat,
    complete_chat,
    prometheus_metrics,
)

__all__ = [
    'configure_logging',
    'get_logger',
    'tool_requests_total',
    'tool_errors_total',
    'tool_latency_seconds',
    'active_tool_requests',
    'chat_requests_total',
    'chat_latency_seconds',
    'monitor_tool',
    'complete_tool',
    'tool_error',
    'monitor_chat',
    'complete_chat',
    'prometheus_metrics',
]
