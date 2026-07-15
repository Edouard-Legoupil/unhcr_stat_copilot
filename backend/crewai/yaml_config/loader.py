"""
YAML Configuration Loader for CrewAI

This module provides functionality to load agent, task, and crew definitions
from a consolidated YAML configuration file (config.yaml).

Usage:
    from backend.crewai.yaml_config.loader import YAMLConfigLoader
    
    loader = YAMLConfigLoader()
    
    # Load all agents
    agents = loader.load_agents()
    
    # Load specific agent
    agent_config = loader.load_agent('statistical_analyzer')
    
    # Load all tasks
    tasks = loader.load_tasks()
    
    # Load specific crew
    crew_config = loader.load_crew('main_analysis_crew')
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
import yaml

from backend.crewai.agents.base import UNHCRBaseAgent

logger = logging.getLogger(__name__)

# Global consolidated configuration
_CONSOLIDATED_CONFIG = None


class YAMLConfigLoader:
    """
    Loader for CrewAI configurations from a consolidated YAML file.
    
    This simplified version loads everything from config.yaml in the yaml_config directory,
    eliminating the need for separate agent, task, and crew subdirectories.
    """
    
    def __init__(
        self,
        config_dir: Optional[str] = None,
        agents_dir: Optional[str] = None,
        tasks_dir: Optional[str] = None,
        crews_dir: Optional[str] = None
    ):
        """
        Initialize the YAML config loader.
        
        Args:
            config_dir: Base configuration directory (default: directory containing this file)
            agents_dir: Unused - kept for backward compatibility
            tasks_dir: Unused - kept for backward compatibility
            crews_dir: Unused - kept for backward compatibility
        """
        global _CONSOLIDATED_CONFIG
        
        # Default paths relative to this module
        base_path = Path(__file__).parent
        
        self.config_dir = Path(config_dir) if config_dir else base_path
        self.agents_dir = Path(agents_dir) if agents_dir else self.config_dir / "agents"
        self.tasks_dir = Path(tasks_dir) if tasks_dir else self.config_dir / "tasks"
        self.crews_dir = Path(crews_dir) if crews_dir else self.config_dir / "crews"
        
        # Load consolidated config
        self._load_consolidated_config()
    
    def _load_consolidated_config(self) -> None:
        """Load the consolidated config.yaml file."""
        global _CONSOLIDATED_CONFIG
        
        config_file = self.config_dir / "config.yaml"
        if not config_file.exists():
            logger.error(f"Consolidated config file not found: {config_file}")
            _CONSOLIDATED_CONFIG = {}
            return
        
        try:
            with open(config_file, 'r') as f:
                _CONSOLIDATED_CONFIG = yaml.safe_load(f) or {}
            logger.info(f"Loaded consolidated configuration from {config_file}")
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {config_file}: {e}")
            _CONSOLIDATED_CONFIG = {}
        except Exception as e:
            logger.error(f"Error loading YAML file {config_file}: {e}")
            _CONSOLIDATED_CONFIG = {}
    
    def _get_consolidated_config(self) -> Dict[str, Any]:
        """Get the consolidated configuration, loading it if necessary."""
        if _CONSOLIDATED_CONFIG is None:
            self._load_consolidated_config()
        return _CONSOLIDATED_CONFIG or {}
    
    def load_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific agent configuration by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            Agent configuration dictionary, or None if not found
        """
        config = self._get_consolidated_config()
        agents = config.get('agents', [])
        
        if isinstance(agents, list):
            for agent_def in agents:
                if isinstance(agent_def, dict) and agent_def.get('name') == agent_name:
                    return agent_def
        
        logger.warning(f"Agent configuration not found: {agent_name}")
        return None
    
    def load_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all agent configurations.
        
        Returns:
            Dictionary mapping agent names to their configurations
        """
        config = self._get_consolidated_config()
        agents_list = config.get('agents', [])
        
        results = {}
        if isinstance(agents_list, list):
            for agent_def in agents_list:
                if isinstance(agent_def, dict):
                    name = agent_def.get('name')
                    if name:
                        results[name] = agent_def
        
        return results
    
    def load_task(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific task configuration by name.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Task configuration dictionary, or None if not found
        """
        config = self._get_consolidated_config()
        tasks = config.get('tasks', [])
        
        if isinstance(tasks, list):
            for task_def in tasks:
                if isinstance(task_def, dict) and task_def.get('name') == task_name:
                    return task_def
        
        logger.warning(f"Task configuration not found: {task_name}")
        return None
    
    def load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all task configurations.
        
        Returns:
            Dictionary mapping task names to their configurations
        """
        config = self._get_consolidated_config()
        tasks_list = config.get('tasks', [])
        
        results = {}
        if isinstance(tasks_list, list):
            for task_def in tasks_list:
                if isinstance(task_def, dict):
                    name = task_def.get('name')
                    if name:
                        results[name] = task_def
        
        return results
    
    def load_crew(self, crew_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific crew configuration by name.
        
        Args:
            crew_name: Name of the crew
            
        Returns:
            Crew configuration dictionary, or None if not found
        """
        config = self._get_consolidated_config()
        crews = config.get('crews', [])
        
        if isinstance(crews, list):
            for crew_def in crews:
                if isinstance(crew_def, dict) and crew_def.get('name') == crew_name:
                    return crew_def
        
        logger.warning(f"Crew configuration not found: {crew_name}")
        return None
    
    def load_crews(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all crew configurations.
        
        Returns:
            Dictionary mapping crew names to their configurations
        """
        config = self._get_consolidated_config()
        crews_list = config.get('crews', [])
        
        results = {}
        if isinstance(crews_list, list):
            for crew_def in crews_list:
                if isinstance(crew_def, dict):
                    name = crew_def.get('name')
                    if name:
                        results[name] = crew_def
        
        return results
    
    def instantiate_agent(
        self,
        agent_config: Dict[str, Any],
        audience: str = "internal",
        document_type: Optional[str] = None,
        **kwargs
    ) -> Optional[UNHCRBaseAgent]:
        """
        Instantiate an agent from its YAML configuration.
        
        Args:
            agent_config: Agent configuration dictionary
            audience: Target audience
            document_type: Document type
            **kwargs: Additional initialization parameters
            
        Returns:
            Instantiated agent, or None if instantiation fails
        """
        try:
            # Get module and class
            module_name = agent_config.get('module', 'backend.crewai.agents')
            class_name = agent_config.get('class_name')
            
            if not class_name:
                logger.error(f"Agent configuration missing class_name: {agent_config.get('name')}")
                return None
            
            # Import the module
            module = importlib.import_module(module_name)
            
            # Get the class
            agent_class = getattr(module, class_name, None)
            if not agent_class:
                logger.error(f"Agent class not found: {class_name} in {module_name}")
                return None
            
            # Prepare initialization kwargs
            init_kwargs = {
                'audience': audience,
                'document_type': document_type,
                **kwargs
            }
            
            # Add role and goal from config if not in kwargs
            if 'role' in agent_config and 'role' not in kwargs:
                init_kwargs['role'] = agent_config['role']
            if 'goal' in agent_config and 'goal' not in kwargs:
                init_kwargs['goal'] = agent_config['goal']
            
            # Instantiate the agent
            agent = agent_class(**init_kwargs)
            
            # Register tools from configuration
            self._register_agent_tools(agent, agent_config)
            
            return agent
            
        except Exception as e:
            logger.error(f"Error instantiating agent {agent_config.get('name')}: {e}")
            return None
    
    def _register_agent_tools(
        self,
        agent: UNHCRBaseAgent,
        agent_config: Dict[str, Any]
    ) -> None:
        """
        Register tools for an agent based on its YAML configuration.
        
        Args:
            agent: Agent instance
            agent_config: Agent configuration
        """
        try:
            from backend.crewai.tools.adapters import MCPToolAdapter
            
            tools_config = agent_config.get('tools', [])
            if not tools_config:
                return
            
            tools = []
            for tool_config in tools_config:
                tool = self._create_tool_from_config(agent, tool_config)
                if tool:
                    tools.append(tool)
                    agent.register_tool(tool_config['name'], tool.function)
            
            agent.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for agent {agent_config.get('name')}: {e}")
    
    def _create_tool_from_config(
        self,
        agent: UNHCRBaseAgent,
        tool_config: Dict[str, Any]
    ) -> Any:
        """
        Create a tool from its YAML configuration.
        
        Args:
            agent: Agent instance (for API client access)
            tool_config: Tool configuration
            
        Returns:
            Adapted tool, or None if creation fails
        """
        try:
            from backend.crewai.tools.adapters import MCPToolAdapter
            
            source = tool_config.get('source')
            if not source:
                logger.warning(f"Tool configuration missing source: {tool_config.get('name')}")
                return None
            
            # Import the source module
            module_path, func_name = source.rsplit('.', 1)
            module = importlib.import_module(module_path)
            tool_func = getattr(module, func_name, None)
            
            if not tool_func:
                logger.warning(f"Tool function not found: {func_name} in {module_path}")
                return None
            
            # Handle special cases (like API client injection)
            if 'get_population_data' in source:
                # For population data, we need to inject the API client
                from backend.mcp.common import UNHCRAPIClient
                api_client = UNHCRAPIClient() if hasattr(agent, 'api_client') and agent.api_client else None
                if api_client:
                    # Create a wrapper that injects the API client
                    def population_data_wrapper(**kwargs):
                        return tool_func(
                            api_client,
                            coo=kwargs.get('coo'),
                            coa=kwargs.get('coa'),
                            year=kwargs.get('year'),
                            coo_all=kwargs.get('coo_all', False),
                            coa_all=kwargs.get('coa_all', False)
                        )
                    tool_func = population_data_wrapper
            
            # Adapt the tool
            tool = MCPToolAdapter.adapt_mcp_tool(
                tool_func,
                name=tool_config.get('name'),
                description=tool_config.get('description', '')
            )
            
            return tool
            
        except Exception as e:
            logger.error(f"Error creating tool {tool_config.get('name')}: {e}")
            return None
    
    def load_and_instantiate_crew(
        self,
        crew_name: str,
        audience: str = "internal",
        document_type: Optional[str] = None,
        **kwargs
    ) -> Optional[Any]:
        """
        Load a crew configuration and instantiate all its agents and tasks.
        
        Args:
            crew_name: Name of the crew
            audience: Target audience
            document_type: Document type
            **kwargs: Additional initialization parameters
            
        Returns:
            Instantiated crew with agents and tasks, or None if loading fails
        """
        try:
            # Load crew configuration
            crew_config = self.load_crew(crew_name)
            if not crew_config:
                logger.error(f"Crew configuration not found: {crew_name}")
                return None
            
            # Load and instantiate agents
            agents = []
            agent_configs = crew_config.get('agents', [])
            
            for agent_ref in agent_configs:
                if isinstance(agent_ref, str):
                    # Agent referenced by name
                    agent_config = self.load_agent(agent_ref)
                    if agent_config:
                        agent = self.instantiate_agent(
                            agent_config,
                            audience=audience,
                            document_type=document_type,
                            **kwargs
                        )
                        if agent:
                            agents.append(agent)
                elif isinstance(agent_ref, dict):
                    # Inline agent configuration
                    agent = self.instantiate_agent(
                        agent_ref,
                        audience=audience,
                        document_type=document_type,
                        **kwargs
                    )
                    if agent:
                        agents.append(agent)
            
            # Import CrewAI
            try:
                from crewai import Crew, Process
                
                # Determine process type
                process_type = crew_config.get('process_type', 'sequential')
                process = Process.sequential if process_type == "sequential" else Process.parallel
                
                # Create crew
                crew = Crew(
                    agents=agents,
                    process=process,
                    verbose=crew_config.get('verbose', 2),
                    memory=crew_config.get('memory', True),
                    cache=crew_config.get('cache', True),
                    max_rpm=crew_config.get('max_rpm'),
                    share_crew=crew_config.get('share_crew', True),
                    crew_name=crew_config.get('name', crew_name),
                    manager_llm=crew_config.get('manager_llm')
                )
                
                return crew
                
            except ImportError:
                logger.warning("CrewAI not available. Using mock crew.")
                # Return a mock crew
                class MockCrew:
                    def __init__(self, **kw):
                        self.agents = kw.get('agents', [])
                        self.process = kw.get('process', 'sequential')
                        self.verbose = kw.get('verbose', 2)
                    
                    async def kickoff(self, inputs: Dict) -> Dict:
                        return {"status": "mocked", "result": f"Crew {crew_name} executed"}
                
                return MockCrew(
                    agents=agents,
                    process=crew_config.get('process_type', 'sequential')
                )
                
        except Exception as e:
            logger.error(f"Error loading and instantiating crew {crew_name}: {e}")
            return None


# Singleton instance for convenience
config_loader = YAMLConfigLoader()


# Convenience functions
def load_agent(agent_name: str) -> Optional[Dict[str, Any]]:
    """Load a specific agent configuration."""
    return config_loader.load_agent(agent_name)


def load_agents() -> Dict[str, Dict[str, Any]]:
    """Load all agent configurations."""
    return config_loader.load_agents()


def load_task(task_name: str) -> Optional[Dict[str, Any]]:
    """Load a specific task configuration."""
    return config_loader.load_task(task_name)


def load_tasks() -> Dict[str, Dict[str, Any]]:
    """Load all task configurations."""
    return config_loader.load_tasks()


def load_crew(crew_name: str) -> Optional[Dict[str, Any]]:
    """Load a specific crew configuration."""
    return config_loader.load_crew(crew_name)


def load_crews() -> Dict[str, Dict[str, Any]]:
    """Load all crew configurations."""
    return config_loader.load_crews()
