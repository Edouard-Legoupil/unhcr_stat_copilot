"""
CrewAI Crew for UNHCR Statistics Copilot

This is the crew that orchestrates analysis workflows.
It uses MCP tools directly via the AnalysisOrchestrator agent.
"""

import logging
from typing import Any, Dict, List, Optional

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. UNHCRCrew will use mock behavior.")
    
    # Mock Process enum
    from enum import Enum
    class Process(Enum):
        sequential = "sequential"
        parallel = "parallel"

from backend.crewai.agents.orchestrators import AnalysisOrchestrator
from backend.crewai.config import AudienceConfigManager
from backend.chat import ANALYSIS_CONFIG, get_analysis_config

logger = logging.getLogger(__name__)


class UNHCRCrew:
    """
    Simplified single crew for UNHCR Statistics Copilot.
    
    This crew orchestrates the complete analysis workflow using MCP tools directly.
    It replaces the previous multi-crew structure (DataCrew, AnalysisCrew, StoryCrew,
    NotebookCrew, MasterCrew) with a single, streamlined crew.
    
    The crew uses the AnalysisOrchestrator agent which:
    1. Fetches data using MCP tools directly
    2. Generates stories using MCP tools
    3. Creates notebooks using MCP tools
    
    This approach minimizes token consumption by avoiding intermediate agent
    coordination and using direct MCP tool calls.
    
    Usage:
        crew = UNHCRCrew(audience="internal", document_type="technical_report")
        
        # Execute full workflow
        result = await crew.execute_full_workflow(
            question="Analyze refugee trends from Syria",
            use_rag=True,
            include_notebook=True
        )
        
        # Or execute individual steps
        data = await crew.fetch_data(question="Syria refugee data")
        story = await crew.generate_story(data=data, question="Syria refugee trends")
        notebook = await crew.create_notebook(story=story, data=data)
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the UNHCR Crew.
        
        Args:
            audience: Target audience for the analysis (default: "internal")
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
        
        # Get analysis config from chat module
        self.analysis_config = ANALYSIS_CONFIG
        
        logger.info(f"UNHCRCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_agent(self) -> AnalysisOrchestrator:
        """Get or create the main orchestrator agent."""
        if 'orchestrator' not in self._agents:
            self._agents['orchestrator'] = AnalysisOrchestrator(
                audience=self.audience,
                document_type=self.document_type
            )
        return self._agents['orchestrator']
    
    def get_crew(self) -> Any:
        """
        Get the CrewAI Crew instance.
        
        Returns:
            Configured Crew instance
        """
        if self._crew is None:
            orchestrator = self._get_or_create_agent()
            
            if CREWAI_AVAILABLE:
                self._crew = Crew(
                    agents=[orchestrator],
                    process=self.process,
                    verbose=2,
                    memory=True,
                    cache=True,
                    max_rpm=None,
                    share_crew=True,
                    crew_name=f"UNHCRCrew_{self.audience}_{self.document_type}",
                    manager_llm=None
                )
            else:
                # Mock crew behavior
                class MockCrew:
                    def __init__(self, **kwargs):
                        self.agents = kwargs.get('agents', [])
                        self.process = kwargs.get('process', 'sequential')
                        self.verbose = kwargs.get('verbose', 2)
                    
                    async def kickoff(self, inputs: Dict) -> Dict:
                        """Mock kickoff."""
                        return {"status": "mocked", "result": "Workflow mocked"}
                
                self._crew = MockCrew(
                    agents=[orchestrator],
                    process=self.process_type
                )
        
        return self._crew
    
    async def execute_full_workflow(
        self,
        question: str,
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        topic: Optional[str] = None,
        timespan: Optional[str] = None,
        style: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the complete analysis workflow.
        
        This is the main entry point for end-to-end analysis. It performs:
        1. Data fetching using MCP tools
        2. Story generation using MCP tools
        3. Notebook creation using MCP tools (if requested)
        
        Args:
            question: The analysis question
            use_rag: Whether to use RAG enrichment
            include_notebook: Whether to generate a Quarto notebook
            output_path: Optional path to save the notebook
            origin: Origin context
            destination: Destination context
            topic: Specific topic
            timespan: Time period
            style: Writing style
            **kwargs: Additional parameters
        
        Returns:
            Dictionary with complete workflow results
        """
        orchestrator = self._get_or_create_agent()
        
        # Prepare parameters
        params = {
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'use_rag': use_rag,
            'include_notebook': include_notebook,
            'output_path': output_path
        }
        
        # Add optional parameters
        if origin:
            params['origin'] = origin
        if destination:
            params['destination'] = destination
        if topic:
            params['topic'] = topic
        if timespan:
            params['timespan'] = timespan
        if style:
            params['style'] = style
        
        # Add extra kwargs
        params.update(kwargs)
        
        try:
            # Use the orchestrator's full workflow
            result = await orchestrator.execute_full_workflow(**params)
            
            # Ensure result has crew metadata
            result['crew'] = 'UNHCRCrew'
            result['crew_type'] = 'simplified'
            
            return result
            
        except Exception as e:
            logger.error(f"Error executing full workflow: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                'crew': 'UNHCRCrew'
            }
    
    async def execute_async_workflow(
        self,
        question: str,
        workflow_type: str = "full",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a workflow asynchronously using CrewAI kickoff.
        
        Args:
            question: The analysis question
            workflow_type: Type of workflow ('full', 'quick', 'comparison')
            **kwargs: Additional workflow parameters
        
        Returns:
            Dictionary with async execution results
        """
        crew = self.get_crew()
        
        try:
            inputs = {
                'question': question,
                'workflow_type': workflow_type,
                'audience': self.audience,
                'document_type': self.document_type,
                **kwargs
            }
            
            result = await crew.kickoff(inputs=inputs)
            
            return {
                'status': 'success',
                'result': result,
                'crew': 'UNHCRCrew'
            }
        except Exception as e:
            logger.error(f"Error executing async workflow: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'UNHCRCrew'
            }
    
    async def fetch_data(
        self,
        question: str,
        parameters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch data for analysis using MCP tools.
        
        Args:
            question: The analysis question
            parameters: Additional parameters for data retrieval
            **kwargs: Additional keyword arguments
        
        Returns:
            Dictionary with data retrieval results
        """
        orchestrator = self._get_or_create_agent()
        
        params = {
            'question': question,
            'parameters': parameters or {},
            'audience': self.audience,
            'document_type': self.document_type
        }
        params.update(kwargs)
        
        try:
            # Use the internal _fetch_data method from orchestrator
            result = await orchestrator._fetch_data(
                question=question,
                parameters=params,
                audience=self.audience,
                document_type=self.document_type
            )
            
            result['crew'] = 'UNHCRCrew'
            result['audience'] = self.audience
            result['document_type'] = self.document_type
            
            return result
        except Exception as e:
            logger.error(f"Error fetching data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                'crew': 'UNHCRCrew'
            }
    
    async def generate_story(
        self,
        data: Dict[str, Any],
        question: str,
        use_rag: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Generate a story from data using MCP tools.
        
        Args:
            data: The source data
            question: The analysis question
            use_rag: Whether to use RAG enrichment
            **kwargs: Additional keyword arguments
        
        Returns:
            Dictionary with story generation results
        """
        orchestrator = self._get_or_create_agent()
        
        # Get analysis config for this audience/document type
        analysis_config = get_analysis_config(self.audience, self.document_type)
        
        params = {
            'data': data,
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'use_rag': use_rag,
            'analysis_config': analysis_config
        }
        params.update(kwargs)
        
        try:
            # Use the internal _generate_notebook method which also generates story
            # Actually, we need to call generate_analytical_story directly
            from backend.mcp_bridge import call_tool
            
            story_result = await call_tool('generate_analytical_story', {
                'data': data,
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                'use_rag': use_rag,
                'analysis_config': analysis_config
            })
            
            if not isinstance(story_result, dict):
                story_result = {'status': 'error', 'error': f'Unexpected result type: {type(story_result)}'}
            
            story_result['crew'] = 'UNHCRCrew'
            story_result['audience'] = self.audience
            story_result['document_type'] = self.document_type
            
            return story_result
            
        except Exception as e:
            logger.error(f"Error generating story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                'crew': 'UNHCRCrew'
            }
    
    async def create_notebook(
        self,
        story_content: str,
        data: Dict[str, Any],
        question: str,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Create a Quarto notebook from story and data using MCP tools.
        
        Args:
            story_content: The story content
            data: The source data
            question: The original question
            output_path: Optional path to save the notebook
            **kwargs: Additional keyword arguments
        
        Returns:
            Dictionary with notebook generation results
        """
        orchestrator = self._get_or_create_agent()
        
        params = {
            'story_content': story_content,
            'data': data,
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'output_path': output_path
        }
        params.update(kwargs)
        
        try:
            # Use the internal _generate_notebook method from orchestrator
            result = await orchestrator._generate_notebook(
                question=question,
                data={'data': data, 'status': 'success'},
                parameters={},
                audience=self.audience,
                document_type=self.document_type,
                use_rag=True
            )
            
            if not isinstance(result, dict):
                result = {'status': 'error', 'error': f'Unexpected result type: {type(result)}'}
            
            result['crew'] = 'UNHCRCrew'
            result['audience'] = self.audience
            result['document_type'] = self.document_type
            
            return result
            
        except Exception as e:
            logger.error(f"Error creating notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': self.audience,
                'document_type': self.document_type,
                'crew': 'UNHCRCrew'
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
        logger.info("UNHCRCrew shutdown complete")


# Convenience function for quick access
def get_crew(
    audience: str = "internal",
    document_type: Optional[str] = None,
    process_type: str = "sequential"
) -> UNHCRCrew:
    """
    Get a configured UNHCRCrew instance.
    
    Args:
        audience: Target audience for the analysis
        document_type: Document type (defaults to audience default)
        process_type: Crew process type ('sequential' or 'parallel')
    
    Returns:
        Configured UNHCRCrew instance
    """
    return UNHCRCrew(
        audience=audience,
        document_type=document_type,
        process_type=process_type
    )
