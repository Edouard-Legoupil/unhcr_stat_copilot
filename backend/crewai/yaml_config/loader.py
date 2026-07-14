"""
YAML Configuration Loader for CrewAI

This module provides functionality to load agent, task, and crew definitions
from YAML files instead of having them hardcoded in Python.

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
    crew_config = loader.load_crew('analysis_crew')
"""

import importlib
import logging
from pathlib import Path
from typing import Any, Dict, List, Optional, Type, Union
import yaml

from backend.crewai.agents.base import UNHCRBaseAgent

logger = logging.getLogger(__name__)


class YAMLConfigLoader:
    """
    Loader for CrewAI configurations from YAML files.
    
    This class provides methods to load agent, task, and crew definitions
    from YAML configuration files, enabling cleaner separation of configuration
    from code.
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
            config_dir: Base configuration directory
            agents_dir: Directory for agent configurations
            tasks_dir: Directory for task configurations
            crews_dir: Directory for crew configurations
        """
        # Default paths relative to this module
        base_path = Path(__file__).parent
        
        self.config_dir = Path(config_dir) if config_dir else base_path
        self.agents_dir = Path(agents_dir) if agents_dir else self.config_dir / "agents"
        self.tasks_dir = Path(tasks_dir) if tasks_dir else self.config_dir / "tasks"
        self.crews_dir = Path(crews_dir) if crews_dir else self.config_dir / "crews"
        
        # Ensure directories exist
        self._ensure_directories()
    
    def _ensure_directories(self):
        """Ensure required directories exist."""
        for directory in [self.config_dir, self.agents_dir, self.tasks_dir, self.crews_dir]:
            if not directory.exists():
                logger.warning(f"Configuration directory not found: {directory}")
    
    def _load_yaml_file(self, file_path: Union[str, Path]) -> Optional[Dict[str, Any]]:
        """
        Load a YAML file from disk.
        
        Args:
            file_path: Path to the YAML file
            
        Returns:
            Parsed YAML content as dictionary, or None if file not found
        """
        path = Path(file_path)
        if not path.exists():
            logger.warning(f"YAML file not found: {path}")
            return None
        
        try:
            with open(path, 'r') as f:
                content = yaml.safe_load(f)
            return content if content else {}
        except yaml.YAMLError as e:
            logger.error(f"Error parsing YAML file {path}: {e}")
            return None
        except Exception as e:
            logger.error(f"Error loading YAML file {path}: {e}")
            return None
    
    def _load_all_yaml_files(self, directory: Path) -> List[Dict[str, Any]]:
        """
        Load all YAML files from a directory.
        
        Args:
            directory: Directory to search for YAML files
            
        Returns:
            List of parsed YAML contents
        """
        if not directory.exists():
            logger.warning(f"Directory not found: {directory}")
            return []
        
        yaml_files = list(directory.glob("*.yaml")) + list(directory.glob("*.yml"))
        
        results = []
        for yaml_file in yaml_files:
            content = self._load_yaml_file(yaml_file)
            if content:
                # Add source file info for debugging
                content['_source_file'] = str(yaml_file)
                results.append(content)
        
        return results
    
    def load_agent(self, agent_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific agent configuration by name.
        
        Args:
            agent_name: Name of the agent (without .yaml extension)
            
        Returns:
            Agent configuration dictionary, or None if not found
        """
        # Try to find in agents directory
        yaml_file = self.agents_dir / f"{agent_name}.yaml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        yaml_file = self.agents_dir / f"{agent_name}.yml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        # Try to find in subdirectories
        for yaml_path in self.agents_dir.rglob(f"{agent_name}.yaml"):
            return self._load_yaml_file(yaml_path)
        
        for yaml_path in self.agents_dir.rglob(f"{agent_name}.yml"):
            return self._load_yaml_file(yaml_path)
        
        logger.warning(f"Agent configuration not found: {agent_name}")
        return None
    
    def load_agents(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all agent configurations.
        
        Returns:
            Dictionary mapping agent names to their configurations
        """
        results = {}
        
        # Load all YAML files from agents directory
        yaml_contents = self._load_all_yaml_files(self.agents_dir)
        
        for content in yaml_contents:
            # Handle different YAML structures
            if isinstance(content, dict):
                # Could be a single agent definition or a collection
                if 'analysts' in content:
                    for agent_def in content['analysts']:
                        name = agent_def.get('name')
                        if name:
                            results[name] = agent_def
                elif 'data_fetchers' in content:
                    for agent_def in content['data_fetchers']:
                        name = agent_def.get('name')
                        if name:
                            results[name] = agent_def
                elif 'story_generators' in content:
                    for agent_def in content['story_generators']:
                        name = agent_def.get('name')
                        if name:
                            results[name] = agent_def
                elif 'orchestrators' in content:
                    for agent_def in content['orchestrators']:
                        name = agent_def.get('name')
                        if name:
                            results[name] = agent_def
                else:
                    # Assume it's a single agent definition
                    name = content.get('name')
                    if name:
                        results[name] = content
            
        return results
    
    def load_task(self, task_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific task configuration by name.
        
        Args:
            task_name: Name of the task
            
        Returns:
            Task configuration dictionary, or None if not found
        """
        # Try to find in tasks directory
        yaml_file = self.tasks_dir / f"{task_name}.yaml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        yaml_file = self.tasks_dir / f"{task_name}.yml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        # Try to find in subdirectories
        for yaml_path in self.tasks_dir.rglob(f"{task_name}.yaml"):
            return self._load_yaml_file(yaml_path)
        
        for yaml_path in self.tasks_dir.rglob(f"{task_name}.yml"):
            return self._load_yaml_file(yaml_path)
        
        logger.warning(f"Task configuration not found: {task_name}")
        return None
    
    def load_tasks(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all task configurations.
        
        Returns:
            Dictionary mapping task names to their configurations
        """
        results = {}
        
        # Load all YAML files from tasks directory
        yaml_contents = self._load_all_yaml_files(self.tasks_dir)
        
        for content in yaml_contents:
            if isinstance(content, dict):
                # Handle collection of tasks
                if 'tasks' in content:
                    for task_def in content['tasks']:
                        name = task_def.get('name')
                        if name:
                            results[name] = task_def
                else:
                    # Assume it's a single task definition
                    name = content.get('name')
                    if name:
                        results[name] = content
        
        return results
    
    def load_crew(self, crew_name: str) -> Optional[Dict[str, Any]]:
        """
        Load a specific crew configuration by name.
        
        Args:
            crew_name: Name of the crew
            
        Returns:
            Crew configuration dictionary, or None if not found
        """
        # Try to find in crews directory
        yaml_file = self.crews_dir / f"{crew_name}.yaml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        yaml_file = self.crews_dir / f"{crew_name}.yml"
        if yaml_file.exists():
            return self._load_yaml_file(yaml_file)
        
        # Try to find in subdirectories
        for yaml_path in self.crews_dir.rglob(f"{crew_name}.yaml"):
            return self._load_yaml_file(yaml_path)
        
        for yaml_path in self.crews_dir.rglob(f"{crew_name}.yml"):
            return self._load_yaml_file(yaml_path)
        
        logger.warning(f"Crew configuration not found: {crew_name}")
        return None
    
    def load_crews(self) -> Dict[str, Dict[str, Any]]:
        """
        Load all crew configurations.
        
        Returns:
            Dictionary mapping crew names to their configurations
        """
        results = {}
        
        # Load all YAML files from crews directory
        yaml_contents = self._load_all_yaml_files(self.crews_dir)
        
        for content in yaml_contents:
            if isinstance(content, dict):
                # Could be a collection or single definition
                if 'crews' in content:
                    for crew_def in content['crews']:
                        name = crew_def.get('name')
                        if name:
                            results[name] = crew_def
                else:
                    # Assume it's a single crew definition
                    name = content.get('name')
                    if name:
                        results[name] = content
        
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
