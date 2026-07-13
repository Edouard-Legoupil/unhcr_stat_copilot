"""
CrewAI Integration for UNHCR Statistics Copilot

This package provides CrewAI-based agent orchestration that mirrors the MCP capabilities
while retaining the ability to generate well-documented Quarto notebooks with analysis logs.

Structure:
- agents/: Specialist and orchestration agents
- crews/: Crew definitions for different workflows
- tasks/: Task definitions for crews
- tools/: Tool adapters and implementations
"""

from backend.crewai.manager import CrewAIManager
from backend.crewai.config import AudienceConfigManager

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
