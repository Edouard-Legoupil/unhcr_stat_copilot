"""
Crew Definitions for UNHCR Statistics Copilot

This package contains all CrewAI crew definitions for different analysis workflows.

Crews:
- DataCrew: Fetches and validates UNHCR data
- AnalysisCrew: Performs statistical analysis and validation
- StoryCrew: Generates analytical stories with RAG enrichment
- NotebookCrew: Creates Quarto notebooks from analysis results
- MasterCrew: Orchestrates all crews for complete workflows
"""

from backend.crewai.crews.data_crew import DataCrew
from backend.crewai.crews.analysis_crew import AnalysisCrew
from backend.crewai.crews.story_crew import StoryCrew
from backend.crewai.crews.notebook_crew import NotebookCrew
from backend.crewai.crews.master_crew import MasterCrew

__all__ = [
    'DataCrew',
    'AnalysisCrew',
    'StoryCrew',
    'NotebookCrew',
    'MasterCrew'
]
