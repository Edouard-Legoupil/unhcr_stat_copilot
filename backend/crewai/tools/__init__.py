"""
Tool Adapters and Implementations for CrewAI

This package provides:
- Adapters to convert MCP tools to CrewAI tools
- Custom tool implementations for CrewAI agents
- Tool utilities and helpers
"""

from backend.crewai.tools.adapters import MCPToolAdapter, CrewAITool, tool_registry

# Note: Individual tool modules (data_tools, analysis_tools, etc.) are not yet implemented.
# For now, we only expose the adapter classes and the tool registry.
# The actual MCP tools should be imported from backend.mcp.tools.* modules as needed.

__all__ = [
    # Adapters
    'MCPToolAdapter',
    'CrewAITool',
    # Registry
    'tool_registry'
]
