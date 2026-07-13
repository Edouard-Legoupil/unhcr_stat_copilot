"""
Notebook Crew for UNHCR Statistics Copilot

This crew handles Quarto notebook generation from analysis results.
It coordinates the notebook generator agent to create well-documented notebooks.
"""

import logging
from typing import Any, Dict, List, Optional

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. NotebookCrew will use mock behavior.")

from backend.crewai.agents import NotebookGenerator
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class NotebookCrew:
    """
    Crew responsible for generating Quarto notebooks from analysis results.
    
    This crew coordinates the notebook generator agent to:
    - Select appropriate templates based on document type
    - Render Jinja2 templates with story content and analysis logs
    - Generate complete Quarto markdown files
    - Preserve all analysis metadata and observability information
    
    Agents:
    - NotebookGenerator: Creates Quarto notebooks from analysis results
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the Notebook Crew.
        
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
        
        logger.info(f"NotebookCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_agents(self) -> List[Any]:
        """Get or create agent instances."""
        if not self._agents:
            self._agents = {
                'notebook_generator': NotebookGenerator(
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
                    crew_name=f"NotebookCrew_{self.audience}_{self.document_type}",
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
                        return {"status": "mocked", "result": "Notebook generation mocked"}
                
                self._crew = MockCrew(
                    agents=agents,
                    process=self.process_type
                )
        
        return self._crew
    
    def create_notebook(
        self,
        story_content: str,
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str,
        output_path: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Quarto notebook from analysis results.
        
        Args:
            story_content: The main story/narrative content
            data: The source data used in the analysis
            analysis: The analysis results
            question: The original analysis question
            output_path: Optional path to save the notebook
            metadata: Additional metadata to include
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with notebook generation results
        """
        # Ensure agents are loaded
        self._get_or_create_agents()
        
        try:
            result = self._agents['notebook_generator'].generate_notebook(
                story_content=story_content,
                data=data,
                analysis=analysis,
                question=question,
                audience=self.audience,
                document_type=self.document_type,
                output_path=output_path,
                metadata=metadata or {},
                **kwargs
            )
            
            return result
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type
            }
    
    def create_notebook_from_story(
        self,
        story_result: Dict[str, Any],
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a notebook from a story generation result.
        
        This is a convenience method that extracts the story content from
        a story_result dictionary and creates a notebook.
        
        Args:
            story_result: Result from story generation
            data: The source data
            analysis: The analysis results
            question: The original question
            output_path: Optional path to save the notebook
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with notebook generation results
        """
        story_content = story_result.get('story', '')
        
        # Extract metadata from story result
        metadata = {
            'enriched': story_result.get('enriched', False),
            'adapted': story_result.get('adapted', False),
            'rag_context': story_result.get('rag_context', {}),
            'adaptation_notes': story_result.get('adaptation_notes', '')
        }
        
        return self.create_notebook(
            story_content=story_content,
            data=data,
            analysis=analysis,
            question=question,
            output_path=output_path,
            metadata=metadata,
            **kwargs
        )
    
    def create_quarto_notebook(
        self,
        story_content: str,
        audience: str,
        document_type: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Quarto notebook (mirrors MCP create_quarto_notebook_tool).
        
        This method provides compatibility with the existing MCP tool interface.
        
        Args:
            story_content: The story content
            audience: Target audience
            document_type: Document type
            output_path: Optional path to save the notebook
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with notebook generation results
        """
        # For backward compatibility, we can accept audience and document_type
        # that differ from the crew's configured values
        use_audience = audience or self.audience
        use_document_type = document_type or self.document_type
        
        try:
            result = self._agents['notebook_generator'].create_quarto_notebook(
                story_content=story_content,
                audience=use_audience,
                document_type=use_document_type,
                output_path=output_path,
                **kwargs
            )
            
            return result
        except Exception as e:
            logger.error(f"Error creating Quarto notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'story_content_preview': story_content[:200] + '...' if len(story_content) > 200 else story_content
            }
    
    async def execute_async(
        self,
        story_content: str,
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute notebook generation asynchronously using CrewAI.
        
        Args:
            story_content: The main story content
            data: The source data
            analysis: The analysis results
            question: The original question
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with execution results
        """
        crew = self.get_crew()
        
        try:
            inputs = {
                'story_content': story_content,
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
                'crew': 'NotebookCrew'
            }
        except Exception as e:
            logger.error(f"Error executing NotebookCrew async: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'NotebookCrew'
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
        logger.info("NotebookCrew shutdown complete")
