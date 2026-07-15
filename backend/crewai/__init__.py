"""
CrewAI Integration for UNHCR Statistics Copilot

This package provides CrewAI-based agent orchestration using MCP tools directly.
Simplified to use YAML-based configuration with a single crew.

Structure:
- agents/: Specialist and orchestration agents
- yaml_config/: YAML configuration files for agents, tasks, and crews
- tools/: Tool adapters
"""

from backend.crewai.manager import CrewAIManager
from backend.crewai.config import AudienceConfigManager
from backend.crewai.yaml_config.loader import config_loader

# Version
__version__ = "1.0.0"

# Initialize global manager (lazy loaded)
_manager: CrewAIManager = None


def get_crewai_manager() -> CrewAIManager:
    """Get the global CrewAI manager instance."""
    global _manager
    if _manager is None:
        _manager = CrewAIManager()
    return _manager


def reset_crewai_manager():
    """Reset the global CrewAI manager instance."""
    global _manager
    if _manager is not None:
        _manager.shutdown()
    _manager = CrewAIManager()


__all__ = [
    'CrewAIManager',
    'AudienceConfigManager',
    'get_crewai_manager',
    'reset_crewai_manager',
    'config_loader'
]
