"""
Notebook Task Definitions for UNHCR Statistics Copilot CrewAI

This module contains CrewAI task definitions for Quarto notebook generation.
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

from backend.crewai.agents import NotebookGenerator

logger = logging.getLogger(__name__)


def create_notebook_task(
    name: str,
    description: str,
    agent: Any,
    expected_output: str,
    context: Optional[List] = None,
    tools: Optional[List] = None,
    async_execution: bool = False
) -> CrewAITask:
    """Factory function to create a notebook task."""
    return CrewAITask(
        name=name,
        description=description,
        agent=agent,
        expected_output=expected_output,
        context=context or [],
        tools=tools or [],
        async_execution=async_execution
    )


class CreateNotebookTask:
    """Task to create a Quarto notebook from analysis results."""
    
    def __init__(
        self,
        story_content: str = "",
        data: Dict[str, Any] = None,
        analysis: Dict[str, Any] = None,
        question: str = "",
        output_path: Optional[str] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.story_content = story_content
        self.data = data or {}
        self.analysis = analysis or {}
        self.question = question
        self.output_path = output_path
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = NotebookGenerator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_notebook_task(
            name="create_notebook",
            description=f"Create Quarto notebook for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with notebook: "
                "{'status': str, 'notebook_content': str, 'metadata': dict, 'path': str}"
            ),
            context=[self.story_content, self.data, self.analysis, self.question,
                    self.output_path, self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import NotebookCrew
        
        crew = NotebookCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.create_notebook(
                story_content=self.story_content,
                data=self.data,
                analysis=self.analysis,
                question=self.question,
                output_path=self.output_path,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in CreateNotebookTask: {e}")
            return {'status': 'error', 'error': str(e)}


class CreateQuartoNotebookTask:
    """Task to create a Quarto notebook (MCP compatible)."""
    
    def __init__(
        self,
        story_content: str = "",
        audience: str = "internal",
        document_type: str = "technical_report",
        output_path: Optional[str] = None
    ):
        self.story_content = story_content
        self.audience = audience
        self.document_type = document_type
        self.output_path = output_path
    
    def get_task(self) -> CrewAITask:
        agent = NotebookGenerator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_notebook_task(
            name="create_quarto_notebook",
            description=f"Create Quarto notebook for {self.audience}/{self.document_type}",
            agent=agent,
            expected_output=(
                "Dictionary with Quarto notebook: "
                "{'status': str, 'content': str, 'path': str, 'metadata': dict}"
            ),
            context=[self.story_content, self.audience, self.document_type, self.output_path]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import NotebookCrew
        
        crew = NotebookCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.create_quarto_notebook(
                story_content=self.story_content,
                audience=self.audience,
                document_type=self.document_type,
                output_path=self.output_path,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in CreateQuartoNotebookTask: {e}")
            return {'status': 'error', 'error': str(e)}
