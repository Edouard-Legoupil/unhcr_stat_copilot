"""
Analysis Task Definitions for UNHCR Statistics Copilot CrewAI

This module contains CrewAI task definitions for statistical analysis and validation.
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

from backend.crewai.agents import (
    StatisticalAnalyzer,
    GuardrailsValidator,
    VisualizationExpert
)

logger = logging.getLogger(__name__)


def create_analysis_task(
    name: str,
    description: str,
    agent: Any,
    expected_output: str,
    context: Optional[List] = None,
    tools: Optional[List] = None,
    async_execution: bool = False
) -> CrewAITask:
    """Factory function to create an analysis task."""
    return CrewAITask(
        name=name,
        description=description,
        agent=agent,
        expected_output=expected_output,
        context=context or [],
        tools=tools or [],
        async_execution=async_execution
    )


class AnalyzeStatisticsTask:
    """Task to perform statistical analysis on UNHCR data."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = StatisticalAnalyzer(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_analysis_task(
            name="analyze_statistics",
            description=f"Perform statistical analysis on data for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with statistical analysis: "
                "{'status': str, 'statistics': dict, 'insights': list, 'warnings': list}"
            ),
            context=[self.data, self.question, self.audience, self.document_type]
        )
    
    def execute(self, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        agent = StatisticalAnalyzer(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return agent.analyze_statistics(
                data=data or self.data,
                question=self.question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in AnalyzeStatisticsTask: {e}")
            return {'status': 'error', 'error': str(e)}


class ValidateGuardrailsTask:
    """Task to validate analysis against UNHCR guardrails."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        analysis: Dict[str, Any] = None,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.analysis = analysis or {}
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = GuardrailsValidator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_analysis_task(
            name="validate_guardrails",
            description=f"Validate analysis against UNHCR guardrails for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with guardrails validation: "
                "{'status': str, 'valid': bool, 'violations': list, 'warnings': list}"
            ),
            context=[self.data, self.analysis, self.question, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        agent = GuardrailsValidator(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return agent.validate_guardrails(
                data=self.data,
                analysis=self.analysis,
                question=self.question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in ValidateGuardrailsTask: {e}")
            return {'status': 'error', 'error': str(e)}


class ExtractVisualizationTask:
    """Task to extract visualization structure from data."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        analysis: Dict[str, Any] = None,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.analysis = analysis or {}
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = VisualizationExpert(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_analysis_task(
            name="extract_visualization",
            description=f"Extract visualization structure for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with visualization structure: "
                "{'status': str, 'structure': dict, 'recommendations': list}"
            ),
            context=[self.data, self.analysis, self.question, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        agent = VisualizationExpert(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return agent.extract_visualization_structure(
                data=self.data,
                analysis=self.analysis,
                question=self.question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in ExtractVisualizationTask: {e}")
            return {'status': 'error', 'error': str(e)}


class GenerateVisualizationDescriptionTask:
    """Task to generate visualization descriptions."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        analysis: Dict[str, Any] = None,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.analysis = analysis or {}
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = VisualizationExpert(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_analysis_task(
            name="generate_visualization_description",
            description=f"Generate visualization descriptions for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with visualization descriptions: "
                "{'status': str, 'descriptions': list, 'metadata': dict}"
            ),
            context=[self.data, self.analysis, self.question, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        agent = VisualizationExpert(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return agent.generate_visualization_description(
                data=self.data,
                analysis=self.analysis,
                question=self.question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in GenerateVisualizationDescriptionTask: {e}")
            return {'status': 'error', 'error': str(e)}


class ApplyAnalysisPipelineTask:
    """Task to apply the complete analysis pipeline."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        question: str = "",
        use_rag: bool = True,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.question = question
        self.use_rag = use_rag
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = StatisticalAnalyzer(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_analysis_task(
            name="apply_analysis_pipeline",
            description=f"Apply complete analysis pipeline for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with complete analysis: "
                "{'status': str, 'analysis': dict, 'guardrails': dict, "
                "'visualizations': list, 'rag_context': dict}"
            ),
            context=[self.data, self.question, self.use_rag, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import AnalysisCrew
        
        crew = AnalysisCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.apply_analysis_pipeline(
                data=self.data,
                question=self.question,
                use_rag=self.use_rag,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in ApplyAnalysisPipelineTask: {e}")
            return {'status': 'error', 'error': str(e)}
