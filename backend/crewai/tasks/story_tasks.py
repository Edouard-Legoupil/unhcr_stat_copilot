"""
Story Task Definitions for UNHCR Statistics Copilot CrewAI

This module contains CrewAI task definitions for story generation and enrichment.
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
    StoryGenerator,
    RAGResearcher,
    AudienceAdapter
)

logger = logging.getLogger(__name__)


def create_story_task(
    name: str,
    description: str,
    agent: Any,
    expected_output: str,
    context: Optional[List] = None,
    tools: Optional[List] = None,
    async_execution: bool = False
) -> CrewAITask:
    """Factory function to create a story task."""
    return CrewAITask(
        name=name,
        description=description,
        agent=agent,
        expected_output=expected_output,
        context=context or [],
        tools=tools or [],
        async_execution=async_execution
    )


class GenerateStoryTask:
    """Task to generate an analytical story from data and analysis."""
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        analysis: Dict[str, Any] = None,
        question: str = "",
        use_rag: bool = True,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.data = data or {}
        self.analysis = analysis or {}
        self.question = question
        self.use_rag = use_rag
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = StoryGenerator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_story_task(
            name="generate_story",
            description=f"Generate analytical story for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with story: "
                "{'status': str, 'story': str, 'metadata': dict, 'warnings': list}"
            ),
            context=[self.data, self.analysis, self.question, self.use_rag,
                    self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import StoryCrew
        
        crew = StoryCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.generate_story(
                data=self.data,
                analysis=self.analysis,
                question=self.question,
                use_rag=self.use_rag,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in GenerateStoryTask: {e}")
            return {'status': 'error', 'error': str(e)}


class EnrichStoryWithRAGTask:
    """Task to enrich a story with RAG context."""
    
    def __init__(
        self,
        story: str = "",
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.story = story
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = RAGResearcher(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_story_task(
            name="enrich_story_with_rag",
            description=f"Enrich story with RAG context for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with enriched story: "
                "{'status': str, 'enriched_story': str, 'context_used': dict}"
            ),
            context=[self.story, self.question, self.audience, self.document_type]
        )
    
    def execute(self, story: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        agent = RAGResearcher(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            # Retrieve context first
            context = agent.retrieve_context(
                question=self.question,
                audience=self.audience,
                document_type=self.document_type
            )
            
            # Enrich the story
            return agent.enrich_story(
                story=story or self.story,
                context=context,
                question=self.question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in EnrichStoryWithRAGTask: {e}")
            return {'status': 'error', 'error': str(e)}


class AdaptStoryToAudienceTask:
    """Task to adapt a story to a specific audience."""
    
    def __init__(
        self,
        story: str = "",
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        self.story = story
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        agent = AudienceAdapter(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_story_task(
            name="adapt_story_to_audience",
            description=f"Adapt story to audience: {self.audience}",
            agent=agent,
            expected_output=(
                "Dictionary with adapted story: "
                "{'status': str, 'adapted_story': str, 'notes': str}"
            ),
            context=[self.story, self.question, self.audience, self.document_type]
        )
    
    def execute(self, story: Optional[str] = None, **kwargs) -> Dict[str, Any]:
        agent = AudienceAdapter(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return agent.adapt_story(
                story=story or self.story,
                audience=self.audience,
                document_type=self.document_type,
                question=self.question,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in AdaptStoryToAudienceTask: {e}")
            return {'status': 'error', 'error': str(e)}


class GenerateDataStoryTask:
    """Task to generate a story directly from data (with auto-analysis)."""
    
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
        agent = StoryGenerator(
            audience=self.audience,
            document_type=self.document_type
        )
        return create_story_task(
            name="generate_data_story",
            description=f"Generate story from data for: {self.question}",
            agent=agent,
            expected_output=(
                "Dictionary with story from data: "
                "{'status': str, 'story': str, 'enriched': bool, 'adapted': bool}"
            ),
            context=[self.data, self.question, self.use_rag,
                    self.audience, self.document_type]
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        from backend.crewai.crews import StoryCrew
        
        crew = StoryCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        try:
            return crew.generate_data_story(
                data=self.data,
                question=self.question,
                use_rag=self.use_rag,
                **kwargs
            )
        except Exception as e:
            logger.error(f"Error in GenerateDataStoryTask: {e}")
            return {'status': 'error', 'error': str(e)}
