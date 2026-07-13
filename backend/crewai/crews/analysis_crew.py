"""
Analysis Crew for UNHCR Statistics Copilot

This crew handles statistical analysis, validation, and visualization of UNHCR data.
It coordinates analysis agents to process and interpret data for story generation.
"""

import logging
from typing import Any, Dict, List, Optional

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. AnalysisCrew will use mock behavior.")

from backend.crewai.agents import (
    StatisticalAnalyzer,
    GuardrailsValidator,
    ToolSelector,
    VisualizationExpert
)
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class AnalysisCrew:
    """
    Crew responsible for analyzing UNHCR data.
    
    This crew coordinates analysis agents to perform:
    - Statistical analysis of displacement data
    - Compliance validation against UNHCR guardrails
    - Visualization structure extraction
    - Visualization description generation
    
    Agents:
    - StatisticalAnalyzer: Performs statistical calculations and insights
    - GuardrailsValidator: Ensures analysis complies with UNHCR standards
    - ToolSelector: Selects appropriate analysis tools
    - VisualizationExpert: Creates visualization structures and descriptions
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the Analysis Crew.
        
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
        
        logger.info(f"AnalysisCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_agents(self) -> List[Any]:
        """Get or create agent instances."""
        if not self._agents:
            self._agents = {
                'statistical_analyzer': StatisticalAnalyzer(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'guardrails_validator': GuardrailsValidator(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'tool_selector': ToolSelector(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'visualization_expert': VisualizationExpert(
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
                    crew_name=f"AnalysisCrew_{self.audience}_{self.document_type}",
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
                        return {"status": "mocked", "result": "Analysis mocked"}
                
                self._crew = MockCrew(
                    agents=agents,
                    process=self.process_type
                )
        
        return self._crew
    
    def analyze_data(
        self,
        data: Dict[str, Any],
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Perform complete data analysis.
        
        Args:
            data: The data to analyze
            question: The analysis question
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with analysis results
        """
        # Ensure agents are loaded
        self._get_or_create_agents()
        
        result: Dict[str, Any] = {
            'status': 'success',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'analysis': {},
            'visualizations': [],
            'guardrails': None,
            'warnings': []
        }
        
        try:
            # Step 1: Statistical analysis
            result['analysis'] = self._agents['statistical_analyzer'].analyze_statistics(
                data=data,
                question=question,
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error in statistical analysis: {e}")
            result['analysis'] = {'status': 'error', 'error': str(e)}
            result['warnings'].append(f"Statistical analysis failed: {e}")
        
        try:
            # Step 2: Guardrails validation
            guardrails_result = self._agents['guardrails_validator'].validate_guardrails(
                data=data,
                analysis=result.get('analysis', {}),
                question=question,
                audience=self.audience,
                document_type=self.document_type
            )
            result['guardrails'] = guardrails_result
            
            # Check for guardrails violations
            if guardrails_result.get('status') == 'error' or \
               guardrails_result.get('violations'):
                result['warnings'].append("Guardrails validation found issues")
        except Exception as e:
            logger.error(f"Error in guardrails validation: {e}")
            result['guardrails'] = {'status': 'error', 'error': str(e)}
            result['warnings'].append(f"Guardrails validation failed: {e}")
        
        try:
            # Step 3: Extract visualization structure
            viz_structure = self._agents['visualization_expert'].extract_visualization_structure(
                data=data,
                analysis=result.get('analysis', {}),
                question=question,
                audience=self.audience,
                document_type=self.document_type
            )
            result['visualizations'].append(viz_structure)
        except Exception as e:
            logger.error(f"Error extracting visualization structure: {e}")
            result['warnings'].append(f"Visualization extraction failed: {e}")
        
        try:
            # Step 4: Generate visualization descriptions
            viz_descriptions = self._agents['visualization_expert'].generate_visualization_description(
                data=data,
                analysis=result.get('analysis', {}),
                question=question,
                audience=self.audience,
                document_type=self.document_type
            )
            result['visualization_descriptions'] = viz_descriptions
        except Exception as e:
            logger.error(f"Error generating visualization descriptions: {e}")
            result['warnings'].append(f"Visualization description generation failed: {e}")
        
        # Determine overall status
        if result.get('analysis', {}).get('status') == 'error' or \
           result.get('guardrails', {}).get('status') == 'error':
            result['status'] = 'partial_success'
        
        return result
    
    def apply_analysis_pipeline(
        self,
        data: Dict[str, Any],
        question: str,
        use_rag: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the complete analysis pipeline (mirrors MCP analysis_pipeline.py).
        
        Args:
            data: The data to analyze
            question: The analysis question
            use_rag: Whether to use RAG enrichment
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with complete pipeline results
        """
        result = self.analyze_data(
            data=data,
            question=question,
            **kwargs
        )
        
        # Add RAG context if requested
        if use_rag:
            try:
                from backend.crewai.agents import RAGResearcher
                rag_researcher = RAGResearcher(
                    audience=self.audience,
                    document_type=self.document_type
                )
                rag_context = rag_researcher.retrieve_context(
                    question=question,
                    audience=self.audience,
                    document_type=self.document_type
                )
                result['rag_context'] = rag_context
            except Exception as e:
                logger.error(f"Error retrieving RAG context: {e}")
                result['warnings'].append(f"RAG context retrieval failed: {e}")
        
        return result
    
    async def execute_async(
        self,
        data: Dict[str, Any],
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute analysis asynchronously using CrewAI.
        
        Args:
            data: The data to analyze
            question: The analysis question
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with execution results
        """
        crew = self.get_crew()
        
        try:
            inputs = {
                'data': data,
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
                'crew': 'AnalysisCrew'
            }
        except Exception as e:
            logger.error(f"Error executing AnalysisCrew async: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'AnalysisCrew'
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
        logger.info("AnalysisCrew shutdown complete")
