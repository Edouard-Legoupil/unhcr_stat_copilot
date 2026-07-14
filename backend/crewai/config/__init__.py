"""
CrewAI Configuration Module

This module provides YAML-based configuration for CrewAI agents, tasks, and crews.

Structure:
    config/
    ├── __init__.py          # This file
    ├── loader.py            # YAML configuration loader
    ├── agents/              # Agent configurations
    │   ├── analysts.yaml
    │   ├── data_fetchers.yaml
    │   ├── story_generators.yaml
    │   └── orchestrators.yaml
    ├── tasks/               # Task configurations
    │   ├── analysis_tasks.yaml
    │   ├── data_tasks.yaml
    │   └── notebook_tasks.yaml
    └── crews/               # Crew configurations
        ├── analysis_crew.yaml
        ├── data_crew.yaml
        ├── story_crew.yaml
        └── notebook_crew.yaml

Usage:
    # Load configurations
    from backend.crewai.config import (
        load_agent, load_agents,
        load_task, load_tasks,
        load_crew, load_crews,
        YAMLConfigLoader
    )
    
    # Or use the loader directly
    from backend.crewai.config.loader import YAMLConfigLoader
    loader = YAMLConfigLoader()
    agents = loader.load_agents()
"""

from backend.crewai.config.loader import (
    YAMLConfigLoader,
    config_loader,
    load_agent,
    load_agents,
    load_task,
    load_tasks,
    load_crew,
    load_crews
)

__all__ = [
    'YAMLConfigLoader',
    'config_loader',
    'load_agent',
    'load_agents',
    'load_task',
    'load_tasks',
    'load_crew',
    'load_crews'
]
