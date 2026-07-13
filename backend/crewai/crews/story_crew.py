"""
Story Crew for UNHCR Statistics Copilot

This crew handles story generation from analysis results.
It coordinates story generation agents to create compelling narratives from data.
"""

import logging
from typing import Any, Dict, List, Optional

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. StoryCrew will use mock behavior.")

from backend.crewai.agents import (
    StoryGenerator,
    RAGResearcher,
    AudienceAdapter
)
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class StoryCrew:
    """
    Crew responsible for generating analytical stories from UNHCR data.
    
    This crew coordinates story generation agents to:
    - Generate data-driven narratives
    - Enrich stories with RAG context
    - Adapt stories to specific audiences
    
    Agents:
    - StoryGenerator: Creates analytical stories from data
    - RAGResearcher: Retrieves additional context for enrichment
    - AudienceAdapter: Adapts stories to target audience
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the Story Crew.
        
        Args:
            audience: Target audience for the analysis
            document_type: Document type (defaults to audience default)
            process_type: Crew process type ('sequential' or 'parallel')
        """
        self.audience = AudienceConfigManager.validate_audience(audience)
        self.document_type = document_type or AudienceConfigManager.get_default_type(self.audience)
        self.process_type = process_type
        
        # Determine process
        self.process = Process.sequential if process_type == "sequential" else Process.parallel
        
        # Agent instances (lazy loaded)
        self._agents: Dict[str, Any] = {}
        self._crew: Optional[Any] = None
        
        logger.info(f"StoryCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_agents(self) -> List[Any]:
        """Get or create agent instances."""
        if not self._agents:
            self._agents = {
                'story_generator': StoryGenerator(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'rag_researcher': RAGResearcher(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'audience_adapter': AudienceAdapter(
                    audience=self.audience,
                    document_type=self.document_type
                )
            }
        
        return list(self._agents.values())
    
    def get_crew(self) -> Any:
        """
        Get the CrewAI Crew instance.
        
        Returns:
            Configured Crew instance
        """
        if self._crew is None:
            agents = self._get_or_create_agents()
            
            if CREWAI_AVAILABLE:
                self._crew = Crew(
                    agents=agents,
                    process=self.process,
                    verbose=2,
                    memory=True,
                    cache=True,
                    max_rpm=None,
                    share_crew=True,
                    crew_name=f"StoryCrew_{self.audience}_{self.document_type}",
                    manager_llm=None
                )
            else:
                # Mock crew behavior
                class MockCrew:
                    def __init__(self, **kwargs):
                        self.agents = agents
                        self.process = self.process_type
                        self.verbose = kwargs.get('verbose', 2)
                    
                    async def kickoff(self, inputs: Dict) -> Dict:
                        """Mock kickoff."""
                        return {"status": "mocked", "result": "Story generation mocked"}
                
                self._crew = MockCrew(
                    agents=agents,
                    process=self.process_type
                )
        
        return self._crew
    
    def generate_story(
        self,
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str,
        use_rag: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a complete analytical story.
        
        Args:
            data: The source data
            analysis: The analysis results
            question: The analysis question
            use_rag: Whether to use RAG enrichment
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with story generation results
        """
        # Ensure agents are loaded
        self._get_or_create_agents()
        
        result: Dict[str, Any] = {
            'status': 'success',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'story': '',
            'enriched': False,
            'adapted': False,
            'warnings': []
        }
        
        try:
            # Step 1: Generate base story
            story_result = self._agents['story_generator'].generate_story(
                data=data,
                analysis=analysis,
                question=question,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
            result['story'] = story_result.get('story', '')
            result['story_metadata'] = story_result.get('metadata', {})
            
            # Step 2: Enrich with RAG if requested
            if use_rag:
                try:
                    rag_context = self._agents['rag_researcher'].retrieve_context(
                        question=question,
                        audience=self.audience,
                        document_type=self.document_type
                    )
                    
                    enriched_story = self._agents['rag_researcher'].enrich_story(
                        story=result['story'],
                        context=rag_context,
                        question=question,
                        audience=self.audience,
                        document_type=self.document_type
                    )
                    result['story'] = enriched_story.get('enriched_story', result['story'])
                    result['enriched'] = True
                    result['rag_context'] = rag_context
                except Exception as e:
                    logger.error(f"Error enriching story with RAG: {e}")
                    result['warnings'].append(f"RAG enrichment failed: {e}")
            
            # Step 3: Adapt to audience
            try:
                adapted_story = self._agents['audience_adapter'].adapt_story(
                    story=result['story'],
                    audience=self.audience,
                    document_type=self.document_type,
                    question=question
                )
                result['story'] = adapted_story.get('adapted_story', result['story'])
                result['adapted'] = True
                result['adaptation_notes'] = adapted_story.get('notes', '')
            except Exception as e:
                logger.error(f"Error adapting story to audience: {e}")
                result['warnings'].append(f"Audience adaptation failed: {e}")
        
        except Exception as e:
            logger.error(f"Error generating story: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def generate_data_story(
        self,
        data: Dict[str, Any],
        question: str,
        use_rag: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a story directly from data (auto-analysis + story).
        
        Args:
            data: The source data
            question: The analysis question
            use_rag: Whether to use RAG enrichment
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with story generation results
        """
        # First get data for story (which may include auto-analysis)
        try:
            from backend.crewai.agents import AnalysisOrchestrator
            orchestrator = AnalysisOrchestrator(
                audience=self.audience,
                document_type=self.document_type
            )
            
            story_data = orchestrator.get_data_for_story(
                question=question,
                data=data,
                audience=self.audience,
                document_type=self.document_type
            )
            
            # Then generate story from the prepared data
            result = self.generate_story(
                data=story_data.get('data', data),
                analysis=story_data.get('analysis', {}),
                question=question,
                use_rag=use_rag,
                **kwargs
            )
            
            return result
        except Exception as e:
            logger.error(f"Error in data-to-story pipeline: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question
            }
    
    async def execute_async(
        self,
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute story generation asynchronously using CrewAI.
        
        Args:
            data: The source data
            analysis: The analysis results
            question: The analysis question
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with execution results
        """
        crew = self.get_crew()
        
        try:
            inputs = {
                'data': data,
                'analysis': analysis,
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                **kwargs
            }
            
            if CREWAI_AVAILABLE:
                result = await crew.kickoff(inputs=inputs)
            else:
                result = await crew.kickoff(inputs=inputs)
            
            return {
                'status': 'success',
                'result': result,
                'crew': 'StoryCrew'
            }
        except Exception as e:
            logger.error(f"Error executing StoryCrew async: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'StoryCrew'
            }
    
    def shutdown(self):
        """Shutdown the crew and clean up resources."""
        if self._crew and hasattr(self._crew, 'shutdown'):
            try:
                self._crew.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down crew: {e}")
        
        self._crew = None
        self._agents.clear()
        logger.info("StoryCrew shutdown complete")
