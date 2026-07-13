"""
Data Crew for UNHCR Statistics Copilot

This crew handles data fetching and validation from various UNHCR data sources.
It coordinates data fetchers to retrieve population, demographic, RSD, and solutions data.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. DataCrew will use mock behavior.")

from backend.crewai.agents import (
    UNHCRDataFetcher,
    RSDExpert,
    SolutionsExpert,
    DemographicsExpert,
    TemporalAnalyzer,
    GeographyExpert
)
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class DataCrew:
    """
    Crew responsible for fetching and validating UNHCR data.
    
    This crew coordinates multiple data specialist agents to retrieve
    comprehensive data for analysis workflows.
    
    Agents:
    - UNHCRDataFetcher: Primary population data retrieval
    - RSDExpert: Refugee Status Determination data
    - SolutionsExpert: Durable solutions data
    - DemographicsExpert: Demographic breakdowns
    - TemporalAnalyzer: Time-series and trend data
    - GeographyExpert: Geographic context and relationships
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the Data Crew.
        
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
        
        logger.info(f"DataCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_agents(self) -> List[Any]:
        """Get or create agent instances."""
        if not self._agents:
            self._agents = {
                'data_fetcher': UNHCRDataFetcher(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'rsd_expert': RSDExpert(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'solutions_expert': SolutionsExpert(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'demographics_expert': DemographicsExpert(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'temporal_analyzer': TemporalAnalyzer(
                    audience=self.audience,
                    document_type=self.document_type
                ),
                'geography_expert': GeographyExpert(
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
                    crew_name=f"DataCrew_{self.audience}_{self.document_type}",
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
                        return {"status": "mocked", "result": "Data fetching mocked"}
                
                self._crew = MockCrew(
                    agents=agents,
                    process=self.process_type
                )
        
        return self._crew
    
    def fetch_population_data(
        self,
        question: str,
        parameters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch population data using the data fetcher agent.
        
        Args:
            question: The analysis question
            parameters: Additional parameters for data retrieval
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with data retrieval results
        """
        agent = self._agents.get('data_fetcher')
        if not agent:
            agent = UNHCRDataFetcher(
                audience=self.audience,
                document_type=self.document_type
            )
            self._agents['data_fetcher'] = agent
        
        try:
            result = agent.fetch_population_data(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"Error fetching population data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question
            }
    
    def fetch_all_data(
        self,
        question: str,
        parameters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Fetch all types of data (population, RSD, solutions, demographics).
        
        Args:
            question: The analysis question
            parameters: Additional parameters
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with all data types
        """
        results = {}
        
        # Ensure agents are loaded
        self._get_or_create_agents()
        
        try:
            # Fetch population data
            results['population'] = self._agents['data_fetcher'].fetch_population_data(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching population data: {e}")
            results['population'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch RSD applications
            results['rsd_applications'] = self._agents['rsd_expert'].fetch_rsd_applications(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching RSD applications: {e}")
            results['rsd_applications'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch RSD decisions
            results['rsd_decisions'] = self._agents['rsd_expert'].fetch_rsd_decisions(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching RSD decisions: {e}")
            results['rsd_decisions'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch solutions data
            results['solutions'] = self._agents['solutions_expert'].fetch_solutions(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching solutions data: {e}")
            results['solutions'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch demographics
            results['demographics'] = self._agents['demographics_expert'].fetch_demographics(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching demographics: {e}")
            results['demographics'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch trends
            results['trends'] = self._agents['temporal_analyzer'].fetch_trends(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching trends: {e}")
            results['trends'] = {'status': 'error', 'error': str(e)}
        
        try:
            # Fetch geographic context
            results['geography'] = self._agents['geography_expert'].fetch_geography_data(
                question=question,
                parameters=parameters or {},
                audience=self.audience,
                document_type=self.document_type
            )
        except Exception as e:
            logger.error(f"Error fetching geography data: {e}")
            results['geography'] = {'status': 'error', 'error': str(e)}
        
        return {
            'status': 'success',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'data': results
        }
    
    async def execute_async(
        self,
        question: str,
        parameters: Optional[Dict] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute data fetching asynchronously using CrewAI.
        
        Args:
            question: The analysis question
            parameters: Additional parameters
            **kwargs: Additional keyword arguments
            
        Returns:
            Dictionary with execution results
        """
        crew = self.get_crew()
        
        try:
            inputs = {
                'question': question,
                'parameters': parameters or {},
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
                'crew': 'DataCrew'
            }
        except Exception as e:
            logger.error(f"Error executing DataCrew async: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'DataCrew'
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
        logger.info("DataCrew shutdown complete")
