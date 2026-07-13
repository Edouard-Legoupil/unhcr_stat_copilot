"""
Base Agent Class for UNHCR Statistics Copilot

This module provides the foundation for all CrewAI agents in the UNHCR Statistics Copilot,
including common configuration, error handling, and UNHCR-specific context.
"""

import logging
import time
from typing import Any, Callable, Dict, List, Optional, Union
from datetime import datetime
import inspect

# Import CrewAI Agent (will be mocked if not installed)
try:
    from crewai import Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logger = logging.getLogger(__name__)
    logger.warning("CrewAI not installed. Using mock Agent class.")
    
    class CrewAIAgent:
        """Mock CrewAI Agent for development without CrewAI installed."""
        def __init__(self, **kwargs):
            self.role = kwargs.get('role', 'Mock Agent')
            self.goal = kwargs.get('goal', 'Mock goal')
            self.backstory = kwargs.get('backstory', 'Mock backstory')
            self.tools = kwargs.get('tools', [])
            self.verbose = kwargs.get('verbose', False)
            self.allow_delegation = kwargs.get('allow_delegation', False)
            self.memory = kwargs.get('memory', False)
            self.max_iter = kwargs.get('max_iter', 10)
            self.logger = logging.getLogger(f"mock_crewai.{self.role}")
        
        def execute_task(self, task: Any) -> Any:
            """Mock task execution."""
            return {"status": "mocked", "result": "Mock result"}

from backend.crewai.config import CrewAIConfig, AudienceConfigManager

logger = logging.getLogger(__name__)


# Get the CrewAI Agent's field names to allow setting custom attributes
try:
    from crewai import Agent as CrewAIAgent
    CREWAI_AGENT_FIELDS = set(CrewAIAgent.__fields__.keys())
except (ImportError, AttributeError):
    CREWAI_AGENT_FIELDS = set()


class UNHCRBaseAgent(CrewAIAgent):
    """
    Base agent for UNHCR Statistics Copilot with common configuration.
    
    This class extends CrewAI's Agent with UNHCR-specific enhancements:
    - Standardized configuration from CrewAIConfig
    - UNHCR-specific backstory generation
    - Enhanced error handling and logging
    - Tool execution tracking
    - Observability metrics
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the UNHCR base agent.
        
        Args:
            role: The agent's role/title
            goal: The agent's primary goal
            backstory: The agent's backstory/context (optional, auto-generated if not provided)
            tools: List of tools available to the agent
            audience: Target audience for context (optional)
            document_type: Document type for context (optional)
            **kwargs: Additional CrewAI Agent parameters
        """
        # Store original role for logging
        self._original_role = kwargs.get('role', 'UNHCR Agent')
        
        # Apply CrewAI configuration defaults
        kwargs.setdefault('verbose', CrewAIConfig.VERBOSE)
        kwargs.setdefault('allow_delegation', CrewAIConfig.ALLOW_DELEGATION)
        kwargs.setdefault('memory', CrewAIConfig.MEMORY_ENABLED)
        kwargs.setdefault('max_iter', CrewAIConfig.MAX_ITER)
        
        # Set LLM to None to avoid provider errors (OpenAI API key not required)
        # CrewAI will use the default mock/fallback behavior
        kwargs.setdefault('llm', None)
        
        # Generate UNHCR-specific backstory if not provided
        if 'backstory' not in kwargs or not kwargs['backstory']:
            audience = kwargs.get('audience', 'internal')
            document_type = kwargs.get('document_type')
            kwargs['backstory'] = self._generate_unhcr_backstory(
                kwargs.get('role', ''),
                audience,
                document_type
            )
        
        # Initialize the parent CrewAI Agent
        super().__init__(**kwargs)
        
        # Store UNHCR-specific data in a private dict to avoid Pydantic validation
        # We use object.__setattr__ to bypass Pydantic's strict mode
        object.__setattr__(self, '_unhcr_data', {
            'agent_id': f"{self.role.replace(' ', '_').lower()}_{int(time.time())}",
            'start_time': datetime.now(),
            'execution_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_execution_time': 0.0
        })
        
        # Initialize tool registry
        object.__setattr__(self, '_tool_registry', {})
        object.__setattr__(self, '_tool_execution_log', [])
        
        # Initialize observability
        self._init_observability()
        
        # Configure agent-specific logging
        self._configure_logging()
        
        # Log initialization
        self._unhcr_data['logger'].info(f"Initialized {self.role} agent")
    
    def __setattr__(self, name, value):
        """
        Override __setattr__ to allow setting custom attributes on Pydantic models.
        
        This is necessary because CrewAI's Agent class is a Pydantic model that doesn't
        allow extra attributes by default. We use object.__setattr__ to bypass this.
        """
        if name not in CREWAI_AGENT_FIELDS or name.startswith('_'):
            # For custom attributes or private attributes, use object.__setattr__
            object.__setattr__(self, name, value)
        else:
            # For CrewAI Agent fields, use normal setattr
            super().__setattr__(name, value)
    
    def _generate_unhcr_backstory(
        self,
        role: str,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> str:
        """
        Generate a UNHCR-specific backstory for the agent.
        
        Args:
            role: The agent's role
            audience: The target audience
            document_type: The document type
            
        Returns:
            UNHCR-specific backstory string
        """
        # Base UNHCR context
        base_context = (
            "You are an AI assistant working for the United Nations High Commissioner for Refugees (UNHCR). "
            "Your responses must adhere to UNHCR standards, methodology, and ethical guidelines. "
            "Always ensure data accuracy, respect for persons of concern, and compliance with international standards. "
            "You have access to UNHCR population data and analysis tools."
        )
        
        # Role-specific context
        role_contexts = {
            'UNHCR Data Fetcher': (
                "As a Data Fetcher, your primary responsibility is retrieving accurate and timely "
                "population statistics from the UNHCR API. You understand all population types "
                "(refugees, asylum_seekers, idps, stateless, returned_refugees, etc.) and can "
                "efficiently query data by country of origin (coo), country of asylum (coa), and year."
            ),
            'RSD Expert': (
                "As an RSD (Refugee Status Determination) Expert, you specialize in retrieving and "
                "analyzing data about asylum applications, decisions, and outcomes. You understand "
                "the complexities of refugee status determination processes."
            ),
            'Solutions Expert': (
                "As a Solutions Expert, you focus on durable solutions data including refugee returnees, "
                "resettlement, naturalization, and IDP returns. You understand the pathways to lasting solutions."
            ),
            'Demographics Expert': (
                "As a Demographics Expert, you specialize in age and gender breakdown data for forcibly "
                "displaced populations. You can analyze demographic composition and trends."
            ),
            'Statistical Analyst': (
                "As a Statistical Analyst, you perform comprehensive statistical analysis on displacement "
                "data. You calculate descriptive statistics, correlations, and distributions, and ensure "
                "compliance with UNHCR methodology standards."
            ),
            'Guardrails Validator': (
                "As a Guardrails Validator, you ensure all analyses follow UNHCR methodology standards "
                "and international guidelines. You validate data interpretation and methodology compliance."
            ),
            'Tool Selector': (
                "As a Tool Selector, you determine the appropriate UNHCR data tools for specific queries. "
                "You analyze questions to identify the best tools and parameters for data retrieval."
            ),
            'Visualization Expert': (
                "As a Visualization Expert, you extract visualization metadata and generate descriptions "
                "for charts and graphs. You understand data visualization best practices."
            ),
            'Story Generator': (
                "As a Story Generator, you create compelling narratives from UNHCR data and analysis. "
                "You adapt your writing style based on the target audience and document type."
            ),
            'RAG Researcher': (
                "As a RAG Researcher, you enrich stories with relevant context from UNHCR reports "
                "and documents. You retrieve and incorporate supporting evidence."
            ),
            'Audience Adapter': (
                "As an Audience Adapter, you ensure stories are tailored to specific audiences. "
                "You understand the tone, length, and structure requirements for each audience type."
            ),
            'Analysis Orchestrator': (
                "As an Analysis Orchestrator, you coordinate complete analysis workflows from "
                "question to Quarto notebook. You manage all aspects of the analysis process."
            ),
            'Notebook Generator': (
                "As a Notebook Generator, you create well-documented Quarto notebooks from analysis "
                "results. You ensure proper structure, metadata, and reproducibility."
            )
        }
        
        # Get role-specific context
        role_context = role_contexts.get(role, f"As a {role}, you perform specialized tasks for UNHCR data analysis.")
        
        # Audience-specific context
        audience_metadata = AudienceConfigManager.get_audience_metadata(audience)
        audience_context = (
            f"Your analysis is targeted at {audience_metadata.get('description', audience)}. "
            f"Follow these guidelines: {audience_metadata.get('tone_guidelines', 'formal and accurate')}. "
            f"Typical use cases include: {', '.join(audience_metadata.get('typical_use_cases', []))}."
        )
        
        # Document type context
        doc_type_context = ""
        if document_type:
            doc_type_context = f"The output should be formatted as a {document_type.replace('_', ' ')}. "
        
        # Combine all contexts
        return f"{base_context} {role_context} {audience_context} {doc_type_context}".strip()
    
    def _configure_logging(self):
        """Configure agent-specific logging."""
        logger_name = f"crewai.agents.{self.role.replace(' ', '_')}"
        agent_logger = logging.getLogger(logger_name)
        
        # Create a handler for this agent
        handler = logging.StreamHandler()
        handler.setFormatter(logging.Formatter(CrewAIConfig.LOG_FORMAT))
        handler.setLevel(getattr(logging, CrewAIConfig.LOG_LEVEL, logging.INFO))
        
        # Add handler if it doesn't exist
        if not any(isinstance(h, logging.StreamHandler) for h in agent_logger.handlers):
            agent_logger.addHandler(handler)
        
        agent_logger.setLevel(getattr(logging, CrewAIConfig.LOG_LEVEL, logging.INFO))
        
        # Store logger in UNHCR data
        self._unhcr_data['logger'] = agent_logger
    
    def _init_observability(self):
        """Initialize observability tracking for the agent."""
        self._unhcr_data['metrics'] = {
            'tool_executions': 0,
            'tool_successes': 0,
            'tool_failures': 0,
            'average_tool_time': 0.0,
            'last_execution': None
        }
    
    def register_tool(self, name: str, tool: Callable, description: str = "") -> str:
        """
        Register a tool with the agent.
        
        Args:
            name: Name of the tool
            tool: The tool function
            description: Description of the tool
            
        Returns:
            Tool ID
        """
        tool_id = f"{self.role}_{name}_{int(time.time())}"[::30]  # Ensure unique ID
        
        # Adapt async tools if needed
        if inspect.iscoroutinefunction(tool):
            original_tool = tool
            async def async_tool_wrapper(*args, **kwargs):
                return await self._execute_with_tracking(original_tool, *args, **kwargs)
            tool = async_tool_wrapper
        else:
            original_tool = tool
            def sync_tool_wrapper(*args, **kwargs):
                return self._execute_with_tracking(original_tool, *args, **kwargs)
            tool = sync_tool_wrapper
        
        self._tool_registry[tool_id] = {
            'name': name,
            'original': original_tool,
            'wrapper': tool,
            'description': description,
            'execution_count': 0,
            'success_count': 0,
            'failure_count': 0,
            'total_time': 0.0
        }
        
        logger.debug(f"Registered tool '{name}' with agent '{self.role}'")
        return tool_id
    
    async def _execute_with_tracking(
        self,
        tool: Callable,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a tool with tracking and error handling.
        
        Args:
            tool: The tool function to execute
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Result of the tool execution
        """
        start_time = time.time()
        tool_name = getattr(tool, '__name__', str(tool))
        
        try:
            if inspect.iscoroutinefunction(tool):
                result = await tool(*args, **kwargs)
            else:
                result = tool(*args, **kwargs)
            
            # Update success metrics
            execution_time = time.time() - start_time
            self._update_metrics(tool_name, True, execution_time)
            
            logger.info(f"Agent {self.role}: Tool {tool_name} executed in {execution_time:.2f}s")
            
            return result
            
        except Exception as e:
            # Update failure metrics
            execution_time = time.time() - start_time
            self._update_metrics(tool_name, False, execution_time)
            
            logger.error(f"Agent {self.role}: Tool {tool_name} failed after {execution_time:.2f}s: {e}")
            raise
    
    def _update_metrics(self, tool_name: str, success: bool, execution_time: float):
        """Update agent metrics after tool execution."""
        data = self._unhcr_data
        data['execution_count'] += 1
        data['total_execution_time'] += execution_time
        
        if success:
            data['success_count'] += 1
        else:
            data['failure_count'] += 1
        
        # Update tool-specific metrics
        for tool_id, tool_info in self._tool_registry.items():
            if tool_info['name'] == tool_name or str(tool_info['original']) == tool_name:
                tool_info['execution_count'] += 1
                tool_info['total_time'] += execution_time
                if success:
                    tool_info['success_count'] += 1
                else:
                    tool_info['failure_count'] += 1
        
        # Update average
        if data['success_count'] > 0:
            data['metrics']['average_tool_time'] = data['total_execution_time'] / data['execution_count']
        
        data['metrics']['last_execution'] = datetime.now()
    
    def execute_tool(
        self,
        tool_name: str,
        *args,
        **kwargs
    ) -> Any:
        """
        Execute a registered tool by name.
        
        Args:
            tool_name: Name of the registered tool
            *args: Positional arguments for the tool
            **kwargs: Keyword arguments for the tool
            
        Returns:
            Result of the tool execution
        """
        # Find the tool
        for tool_id, tool_info in self._tool_registry.items():
            if tool_info['name'] == tool_name:
                wrapper = tool_info['wrapper']
                
                # Check if tool is async
                if inspect.iscoroutinefunction(tool_info['original']):
                    import asyncio
                    loop = asyncio.get_event_loop()
                    return loop.run_until_complete(wrapper(*args, **kwargs))
                else:
                    return wrapper(*args, **kwargs)
        
        # Tool not found, try executing directly
        logger.warning(f"Tool '{tool_name}' not found in registry, attempting direct execution")
        
        # Look for tool in the agent's tools list
        for tool in self.tools:
            if hasattr(tool, 'name') and tool.name == tool_name:
                if hasattr(tool, 'function'):
                    func = tool.function
                    if inspect.iscoroutinefunction(func):
                        import asyncio
                        loop = asyncio.get_event_loop()
                        return loop.run_until_complete(func(*args, **kwargs))
                    else:
                        return func(*args, **kwargs)
        
        raise ValueError(f"Tool '{tool_name}' not found and cannot be executed directly")
    
    def get_metrics(self) -> Dict[str, Any]:
        """
        Get the agent's execution metrics.
        
        Returns:
            Dictionary with execution metrics
        """
        data = self._unhcr_data
        return {
            **data['metrics'],
            'agent_id': data['agent_id'],
            'role': self.role,
            'start_time': data['start_time'].isoformat(),
            'execution_count': data['execution_count'],
            'success_count': data['success_count'],
            'failure_count': data['failure_count'],
            'success_rate': data['success_count'] / data['execution_count'] if data['execution_count'] > 0 else 0.0,
            'tool_registry': {
                name: {
                    'executions': info['execution_count'],
                    'successes': info['success_count'],
                    'failures': info['failure_count'],
                    'avg_time': info['total_time'] / info['execution_count'] if info['execution_count'] > 0 else 0.0
                }
                for name, info in self._tool_registry.items()
            }
        }
    
    def reset_metrics(self):
        """Reset the agent's execution metrics."""
        self._unhcr_data['execution_count'] = 0
        self._unhcr_data['success_count'] = 0
        self._unhcr_data['failure_count'] = 0
        self._unhcr_data['total_execution_time'] = 0.0
        self._unhcr_data['metrics'] = {
            'tool_executions': 0,
            'tool_successes': 0,
            'tool_failures': 0,
            'average_tool_time': 0.0,
            'last_execution': None
        }
        
        for tool_info in self._tool_registry.values():
            tool_info['execution_count'] = 0
            tool_info['success_count'] = 0
            tool_info['failure_count'] = 0
            tool_info['total_time'] = 0.0
    
    def shutdown(self):
        """Clean up agent resources."""
        logger.info(f"Shutting down {self.role} agent")
        # Clean up any resources
        self._tool_execution_log.clear()
        self.reset_metrics()
    
    def __del__(self):
        """Destructor to clean up resources."""
        self.shutdown()


# Mock agent for development without CrewAI
if not CREWAI_AVAILABLE:
    class MockUNHCRBaseAgent(UNHCRBaseAgent):
        """Mock version of UNHCRBaseAgent for development."""
        
        def __init__(self, **kwargs):
            # Call parent init without CrewAI
            self.role = kwargs.get('role', 'Mock Agent')
            self.goal = kwargs.get('goal', 'Mock goal')
            self.backstory = kwargs.get('backstory', 'Mock backstory')
            self.tools = kwargs.get('tools', [])
            self.verbose = kwargs.get('verbose', False)
            self.allow_delegation = kwargs.get('allow_delegation', False)
            self.memory = kwargs.get('memory', False)
            self.max_iter = kwargs.get('max_iter', 10)
            self.logger = logging.getLogger(f"mock_crewai.{self.role}")
            
            # Initialize UNHCR-specific attributes
            self.agent_id = f"{self.role.replace(' ', '_').lower()}_{int(time.time())}"
            self.start_time = datetime.now()
            self.execution_count = 0
            self.success_count = 0
            self.failure_count = 0
            self.total_execution_time = 0.0
            self._tool_registry = {}
            self._tool_execution_log = []
            self._init_observability()
            self._configure_logging()
