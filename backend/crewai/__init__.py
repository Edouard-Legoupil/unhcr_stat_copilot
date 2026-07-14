"""
CrewAI Integration for UNHCR Statistics Copilot

This package provides CrewAI-based agent orchestration that uses MCP tools directly.
The structure has been simplified to use a single UNHCRCrew class instead of multiple
separate crews (DataCrew, AnalysisCrew, StoryCrew, NotebookCrew, MasterCrew).

Structure:
- agents/: Specialist and orchestration agents
- crews/: Simplified single crew definition (UNHCRCrew)
- tasks/: Task definitions for crews
- tools/: Tool adapters and implementations
- yaml_config/: YAML configuration files for agents and crews
"""

from backend.crewai.manager import CrewAIManager
from backend.crewai.config import AudienceConfigManager
from backend.crewai.crew import UNHCRCrew, get_crew

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


# Export the simplified crew for convenience
__all__ = [
    'CrewAIManager',
    'AudienceConfigManager',
    'get_crewai_manager',
    'reset_crewai_manager',
    'UNHCRCrew',
    'get_crew'
]
