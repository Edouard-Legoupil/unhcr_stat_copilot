"""
Task Definitions for UNHCR Statistics Copilot CrewAI

This package contains all CrewAI task definitions for different analysis workflows.

Tasks are organized by workflow type:
- Data tasks: Fetching and validating UNHCR data
- Analysis tasks: Statistical analysis and visualization
- Story tasks: Generating analytical stories
- Notebook tasks: Creating Quarto notebooks
- Workflow tasks: Complete end-to-end workflows
"""

from backend.crewai.tasks.data_tasks import (
    FetchPopulationDataTask,
    FetchAllDataTask,
    ValidateDataTask
)
from backend.crewai.tasks.analysis_tasks import (
    AnalyzeStatisticsTask,
    ValidateGuardrailsTask,
    ExtractVisualizationTask,
    GenerateVisualizationDescriptionTask,
    ApplyAnalysisPipelineTask
)
from backend.crewai.tasks.story_tasks import (
    GenerateStoryTask,
    EnrichStoryWithRAGTask,
    AdaptStoryToAudienceTask,
    GenerateDataStoryTask
)
from backend.crewai.tasks.notebook_tasks import (
    CreateNotebookTask,
    CreateQuartoNotebookTask
)
from backend.crewai.tasks.workflow_tasks import (
    FullAnalysisWorkflowTask,
    QuickAnalysisWorkflowTask,
    ComparisonAnalysisWorkflowTask,
    EnhancedAnalysisWorkflowTask
)

__all__ = [
    # Data tasks
    'FetchPopulationDataTask',
    'FetchAllDataTask',
    'ValidateDataTask',
    # Analysis tasks
    'AnalyzeStatisticsTask',
    'ValidateGuardrailsTask',
    'ExtractVisualizationTask',
    'GenerateVisualizationDescriptionTask',
    'ApplyAnalysisPipelineTask',
    # Story tasks
    'GenerateStoryTask',
    'EnrichStoryWithRAGTask',
    'AdaptStoryToAudienceTask',
    'GenerateDataStoryTask',
    # Notebook tasks
    'CreateNotebookTask',
    'CreateQuartoNotebookTask',
    # Workflow tasks
    'FullAnalysisWorkflowTask',
    'QuickAnalysisWorkflowTask',
    'ComparisonAnalysisWorkflowTask',
    'EnhancedAnalysisWorkflowTask'
]
