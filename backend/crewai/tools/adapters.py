"""
MCP to CrewAI Tool Adapters

This module provides adapters to convert MCP tools to CrewAI-compatible tools,
handling async/sync compatibility and standardizing input/output formats.
"""

import asyncio
import inspect
import json
import logging
from typing import Any, Callable, Dict, List, Optional, Union

logger = logging.getLogger(__name__)

# Import CrewAI Tool (will be mocked if not installed)
try:
    from crewai import Tool as CrewAITool
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logger.warning("CrewAI not installed. Using mock Tool class.")
    
    class CrewAITool:
        """Mock CrewAI Tool for development without CrewAI installed."""
        def __init__(self, name: str = "", description: str = "", function: Callable = None):
            self.name = name
            self.description = description
            self.function = function or (lambda *args, **kwargs: {"status": "mocked"})


class MCPToolAdapter:
    """
    Adapter to convert MCP tools to CrewAI-compatible tools.
    
    This class handles:
    - Async to sync conversion for CrewAI compatibility
    - Standardized input/output formatting
    - Error handling and logging
    - Tool metadata preservation
    """
    
    @staticmethod
    def adapt_mcp_tool(
        mcp_tool: Callable,
        name: str,
        description: str = "",
        tool_kwargs: Optional[Dict[str, Any]] = None
    ) -> CrewAITool:
        """
        Convert an MCP tool function to a CrewAI Tool.
        
        Args:
            mcp_tool: The MCP tool function to adapt
            name: Name of the tool
            description: Description of the tool
            tool_kwargs: Additional kwargs for the CrewAI Tool
            
        Returns:
            CrewAI Tool instance
        """
        # Validate inputs
        if not callable(mcp_tool):
            raise ValueError(f"mcp_tool must be callable, got {type(mcp_tool)}")
        
        if not name:
            name = getattr(mcp_tool, '__name__', 'unnamed_tool')
        
        # Check if tool is async
        is_async = inspect.iscoroutinefunction(mcp_tool)
        
        if is_async:
            # Create async wrapper
            async def async_wrapper(*args, **kwargs) -> str:
                try:
                    # Handle both direct calls and keyword arguments
                    if len(args) == 1 and isinstance(args[0], dict):
                        # Single dict argument (common MCP pattern)
                        result = await mcp_tool(**args[0])
                    else:
                        # Multiple arguments
                        result = await mcp_tool(*args, **kwargs)
                    
                    # Convert result to string if needed
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Async tool {name} failed: {e}")
                    raise
            
            wrapper = async_wrapper
            
        else:
            # Create sync wrapper
            def sync_wrapper(*args, **kwargs) -> str:
                try:
                    # Handle both direct calls and keyword arguments
                    if len(args) == 1 and isinstance(args[0], dict):
                        # Single dict argument (common MCP pattern)
                        result = mcp_tool(**args[0])
                    else:
                        # Multiple arguments
                        result = mcp_tool(*args, **kwargs)
                    
                    # Convert result to string if needed
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Sync tool {name} failed: {e}")
                    raise
            
            wrapper = sync_wrapper
        
        # Additional tool kwargs
        kwargs = tool_kwargs or {}
        
        return CrewAITool(
            name=name,
            description=description,
            function=wrapper,
            **kwargs
        )
    
    @staticmethod
    def adapt_mcp_tool_with_context(
        mcp_tool: Callable,
        name: str,
        description: str = "",
        context_provider: Optional[Callable] = None
    ) -> CrewAITool:
        """
        Adapt an MCP tool with additional context.
        
        Args:
            mcp_tool: The MCP tool function to adapt
            name: Name of the tool
            description: Description of the tool
            context_provider: Function to provide additional context
            
        Returns:
            CrewAI Tool instance with context
        """
        original_tool = mcp_tool
        is_async = inspect.iscoroutinefunction(mcp_tool)
        
        if is_async:
            async def async_wrapper(*args, **kwargs) -> str:
                # Get context if provider exists
                context = {}
                if context_provider:
                    try:
                        context = await context_provider() if inspect.iscoroutinefunction(context_provider) else context_provider()
                    except Exception as e:
                        logger.warning(f"Context provider failed: {e}")
                
                # Merge context with kwargs
                merged_kwargs = {**context, **kwargs}
                
                try:
                    if len(args) == 1 and isinstance(args[0], dict):
                        result = await original_tool(**{**args[0], **merged_kwargs})
                    else:
                        result = await original_tool(*args, **merged_kwargs)
                    
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Async tool {name} with context failed: {e}")
                    raise
            
            wrapper = async_wrapper
            
        else:
            def sync_wrapper(*args, **kwargs) -> str:
                # Get context if provider exists
                context = {}
                if context_provider:
                    try:
                        context = context_provider()
                    except Exception as e:
                        logger.warning(f"Context provider failed: {e}")
                
                # Merge context with kwargs
                merged_kwargs = {**context, **kwargs}
                
                try:
                    if len(args) == 1 and isinstance(args[0], dict):
                        result = original_tool(**{**args[0], **merged_kwargs})
                    else:
                        result = original_tool(*args, **merged_kwargs)
                    
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Sync tool {name} with context failed: {e}")
                    raise
            
            wrapper = sync_wrapper
        
        return CrewAITool(
            name=name,
            description=description,
            function=wrapper
        )
    
    @staticmethod
    def adapt_all_from_module(
        module,
        tool_prefix: str = "",
        tool_suffix: str = "_tool"
    ) -> List[CrewAITool]:
        """
        Adapt all tools from a module that match a naming pattern.
        
        Args:
            module: The Python module containing tool functions
            tool_prefix: Prefix for tool function names
            tool_suffix: Suffix for tool function names (default: '_tool')
            
        Returns:
            List of adapted CrewAI Tools
        """
        from backend.mcp import server as mcp_server_module
        import sys
        
        tools = []
        
        # Get all attributes from the module
        for attr_name in dir(module):
            if attr_name.endswith(tool_suffix) and attr_name.startswith(tool_prefix):
                attr = getattr(module, attr_name)
                
                # Skip if not callable or if it's a class
                if not callable(attr) or inspect.isclass(attr):
                    continue
                
                # Get tool name without suffix
                tool_name = attr_name[:-len(tool_suffix)] if tool_suffix else attr_name
                tool_name = tool_name[len(tool_prefix):] if tool_prefix else tool_name
                
                # Try to get description from docstring
                description = getattr(attr, '__doc__', '')
                if description:
                    # Get first line of docstring
                    description = description.strip().split('\n')[0]
                
                try:
                    adapted_tool = MCPToolAdapter.adapt_mcp_tool(
                        attr,
                        name=tool_name,
                        description=description
                    )
                    tools.append(adapted_tool)
                    logger.info(f"Adapted tool: {tool_name}")
                except Exception as e:
                    logger.error(f"Failed to adapt tool {attr_name}: {e}")
        
        return tools
    
    @staticmethod
    def adapt_mcp_server_tools(server=None) -> List[CrewAITool]:
        """
        Adapt all tools from an MCP server to CrewAI tools.
        
        Args:
            server: The MCP server instance (if None, creates a new one)
            
        Returns:
            List of adapted CrewAI Tools
        """
        if server is None:
            from backend.mcp.server import create_server
            server = create_server()
        
        tools = []
        
        # Get all registered tools from the server
        try:
            # Try to access the tool manager
            if hasattr(server, '_tool_manager'):
                tool_manager = server._tool_manager
                if hasattr(tool_manager, 'tools'):
                    for tool_name, tool_info in tool_manager.tools.items():
                        # Get the actual tool function
                        tool_func = None
                        
                        # Try to find the tool function in the server
                        if hasattr(server, tool_name):
                            tool_func = getattr(server, tool_name)
                        
                        if tool_func and callable(tool_func):
                            try:
                                adapted_tool = MCPToolAdapter.adapt_mcp_tool(
                                    tool_func,
                                    name=tool_name,
                                    description=tool_info.description if hasattr(tool_info, 'description') else str(tool_info)
                                )
                                tools.append(adapted_tool)
                                logger.info(f"Adapted MCP server tool: {tool_name}")
                            except Exception as e:
                                logger.error(f"Failed to adapt MCP server tool {tool_name}: {e}")
        except Exception as e:
            logger.error(f"Error accessing MCP server tools: {e}")
        
        return tools
    
    @staticmethod
    def create_dict_tool(
        name: str,
        description: str,
        function: Callable,
        schema: Optional[Dict[str, Any]] = None
    ) -> CrewAITool:
        """
        Create a CrewAI tool that accepts a dictionary argument.
        
        This is useful for tools that expect structured input.
        
        Args:
            name: Name of the tool
            description: Description of the tool
            function: The function to call (will receive the dict as first argument)
            schema: Optional schema for input validation
            
        Returns:
            CrewAI Tool instance
        """
        is_async = inspect.iscoroutinefunction(function)
        
        if is_async:
            async def async_wrapper(input_dict: Dict[str, Any] = None, **kwargs) -> str:
                if input_dict is None:
                    input_dict = kwargs
                else:
                    input_dict = {**input_dict, **kwargs}
                
                try:
                    result = await function(input_dict)
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Dict tool {name} failed: {e}")
                    raise
            
            wrapper = async_wrapper
            
        else:
            def sync_wrapper(input_dict: Dict[str, Any] = None, **kwargs) -> str:
                if input_dict is None:
                    input_dict = kwargs
                else:
                    input_dict = {**input_dict, **kwargs}
                
                try:
                    result = function(input_dict)
                    if isinstance(result, (dict, list)):
                        return json.dumps(result, default=str)
                    return str(result) if result is not None else ""
                except Exception as e:
                    logger.error(f"Dict tool {name} failed: {e}")
                    raise
            
            wrapper = sync_wrapper
        
        return CrewAITool(
            name=name,
            description=description,
            function=wrapper
        )


class ToolRegistry:
    """
    Registry for managing CrewAI tools across agents.
    
    This provides a centralized way to register, retrieve, and manage tools.
    """
    
    def __init__(self):
        self._tools: Dict[str, CrewAITool] = {}
        self._adapters: Dict[str, MCPToolAdapter] = {}
    
    def register(self, tool: CrewAITool, category: str = "general") -> str:
        """
        Register a tool in the registry.
        
        Args:
            tool: The CrewAI Tool to register
            category: Category for the tool
            
        Returns:
            Tool ID
        """
        tool_id = f"{category}_{tool.name}_{len(self._tools)}"
        self._tools[tool_id] = tool
        logger.info(f"Registered tool: {tool.name} (ID: {tool_id})")
        return tool_id
    
    def get(self, tool_id: str) -> Optional[CrewAITool]:
        """Get a tool by ID."""
        return self._tools.get(tool_id)
    
    def get_by_name(self, name: str) -> Optional[CrewAITool]:
        """Get a tool by name."""
        for tool in self._tools.values():
            if tool.name == name:
                return tool
        return None
    
    def list_tools(self, category: str = None) -> List[CrewAITool]:
        """List all tools, optionally filtered by category."""
        if category is None:
            return list(self._tools.values())
        return [t for t in self._tools.values() if t.name.startswith(f"{category}_")]
    
    def register_adapter(self, name: str, adapter: MCPToolAdapter) -> str:
        """Register an MCP tool adapter."""
        adapter_id = f"adapter_{name}"
        self._adapters[adapter_id] = adapter
        return adapter_id
    
    def get_adapter(self, adapter_id: str) -> Optional[MCPToolAdapter]:
        """Get an adapter by ID."""
        return self._adapters.get(adapter_id)


# Global tool registry
tool_registry = ToolRegistry()
