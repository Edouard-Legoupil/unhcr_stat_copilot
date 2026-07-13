"""
Workflow Task Definitions for UNHCR Statistics Copilot CrewAI

This module contains CrewAI task definitions for complete end-to-end workflows.
"""

import logging
from typing import Any, Dict, List, Optional

try:
    from crewai import Task as CrewAITask
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. Using mock Task class.")
    
    class CrewAITask:
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'Mock Task')
            self.description = kwargs.get('description', '')
            self.expected_output = kwargs.get('expected_output', '')
            self.agent = kwargs.get('agent')
            self.context = kwargs.get('context', [])
            self.tools = kwargs.get('tools', [])
            self.async_execution = kwargs.get('async_execution', False)

from backend.crewai.agents import AnalysisOrchestrator, NotebookGenerator

logger = logging.getLogger(__name__)


def create_workflow_task(
    name: str,
    description: str,
    agent: Any,
    expected_output: str,
    context: Optional[List] = None,
    tools: Optional[List] = None,
    async_execution: bool = False
) -> CrewAITask:
    """Factory function to create a workflow task."""
    return CrewAITask(
        name=name,
        description=description,
        agent=agent,
        expected_output=expected_output,
        context=context or [],
        tools=tools or [],
        async_execution=async_execution
    )


class FullAnalysisWorkflowTask:
    """Task to execute the complete analysis workflow."""
    
    def __init__(
        self,
        question: str = "",
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.question = question
        self.use_rag = use_rag
        self.include_notebook = include_notebook
        self.output_path = output_path
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = AnalysisOrchestrator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_workflow_task(
            name="full_analysis_workflow",
            description=f"Execute complete analysis workflow for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with complete analysis: "
                "{'status': str, 'story': str, 'data': dict, 'analysis': dict, "
                "'notebook': dict, 'steps': list, 'warnings': list}"
            ),
            context=[self.question, self.use_rag, self.include_notebook,
                    self.output_path, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import MasterCrew
        
        crew = MasterCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.execute_full_workflow(
                question=self.question,
                use_rag=self.use_rag,
                include_notebook=self.include_notebook,
                output_path=self.output_path,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in FullAnalysisWorkflowTask: {e}")
            return {'status': 'error', 'error': str(e)}


class QuickAnalysisWorkflowTask:
    """Task to execute a quick analysis workflow (data + story, no notebook)."""
    
    def __init__(
        self,
        question: str = "",
        use_rag: bool = True,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.question = question
        self.use_rag = use_rag
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = AnalysisOrchestrator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_workflow_task(
            name="quick_analysis_workflow",
            description=f"Execute quick analysis workflow for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with quick analysis: "
                "{'status': str, 'story': str, 'data': dict, 'steps': list}"
            ),
            context=[self.question, self.use_rag, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import MasterCrew
        
        crew = MasterCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.execute_quick_workflow(
                question=self.question,
                use_rag=self.use_rag,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in QuickAnalysisWorkflowTask: {e}")
            return {'status': 'error', 'error': str(e)}


class ComparisonAnalysisWorkflowTask:
    """Task to execute a comparison analysis workflow."""
    
    def __init__(
        self,
        question: str = "",
        use_rag: bool = True,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.question = question
        self.use_rag = use_rag
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = AnalysisOrchestrator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_workflow_task(
            name="comparison_analysis_workflow",
            description=f"Execute comparison analysis workflow for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with comparison analysis: "
                "{'status': str, 'comparison_results': list, 'scenarios': list, 'steps': list}"
            ),
            context=[self.question, self.use_rag, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import MasterCrew
        
        crew = MasterCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.execute_comparison_workflow(
                question=self.question,
                use_rag=self.use_rag,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in ComparisonAnalysisWorkflowTask: {e}")
            return {'status': 'error', 'error': str(e)}


class EnhancedAnalysisWorkflowTask:
    """Task to execute an enhanced analysis workflow with full pipeline."""
    
    def __init__(
        self,
        question: str = "",
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.question = question
        self.use_rag = use_rag
        self.include_notebook = include_notebook
        self.output_path = output_path
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = AnalysisOrchestrator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_workflow_task(
            name="enhanced_analysis_workflow",
            description=f"Execute enhanced analysis workflow for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with enhanced analysis: "
                "{'status': str, 'story': str, 'analysis': dict, 'rag_context': dict, "
                "'notebook': dict, 'steps': list}"
            ),
            context=[self.question, self.use_rag, self.include_notebook,
                    self.output_path, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import MasterCrew
        
        crew = MasterCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.execute_full_workflow(
                question=self.question,
                use_rag=self.use_rag,
                include_notebook=self.include_notebook,
                output_path=self.output_path,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in EnhancedAnalysisWorkflowTask: {e}")
            return {'status': 'error', 'error': str(e)}
