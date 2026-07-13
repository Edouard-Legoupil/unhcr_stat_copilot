"""
CrewAI Agents for UNHCR Statistics Copilot

This package contains all CrewAI agents used in the UNHCR Statistics Copilot.

Agent Hierarchy:
- Level 1: Specialist Agents (tool-level operations)
- Level 2: Analysis Agents (pipeline-level orchestration)
- Level 3: Orchestration Agents (workflow-level coordination)
"""

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.agents.data_fetchers import (
    UNHCRDataFetcher,
    RSDExpert,
    SolutionsExpert,
    DemographicsExpert,
    TemporalAnalyzer,
    GeographyExpert
)
from backend.crewai.agents.analysts import (
    StatisticalAnalyzer,
    GuardrailsValidator,
    ToolSelector,
    VisualizationExpert
)
from backend.crewai.agents.story_generators import (
    StoryGenerator,
    RAGResearcher,
    AudienceAdapter
)
from backend.crewai.agents.orchestrators import (
    AnalysisOrchestrator,
    NotebookGenerator
)

__all__ = [
    # Base
    'UNHCRBaseAgent',
    # Data Fetchers
    'UNHCRDataFetcher',
    'RSDExpert',
    'SolutionsExpert',
    'DemographicsExpert',
    'TemporalAnalyzer',
    'GeographyExpert',
    # Analysts
    'StatisticalAnalyzer',
    'GuardrailsValidator',
    'ToolSelector',
    'VisualizationExpert',
    # Story Generators
    'StoryGenerator',
    'RAGResearcher',
    'AudienceAdapter',
    # Orchestrators
    'AnalysisOrchestrator',
    'NotebookGenerator'
]
