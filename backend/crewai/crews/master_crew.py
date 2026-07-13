"""
Master Crew for UNHCR Statistics Copilot

This is the top-level crew that orchestrates all other crews to provide
complete end-to-end analysis workflows, mirroring the MCP capabilities.
"""

import logging
from typing import Any, Dict, List, Optional, Union

# Import CrewAI (with fallback mock)
try:
    from crewai import Crew, Process, Agent as CrewAIAgent
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. MasterCrew will use mock behavior.")

from backend.crewai.agents import AnalysisOrchestrator, NotebookGenerator
from backend.crewai.crews import DataCrew, AnalysisCrew, StoryCrew, NotebookCrew
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class MasterCrew:
    """
    Master crew that orchestrates all UNHCR Statistics Copilot workflows.
    
    This crew provides the top-level interface for executing complete analysis
    workflows, mirroring the MCP server's full_analysis_workflow and other
    composite tools.
    
    The MasterCrew can:
    - Execute full analysis workflows (data → analysis → story → notebook)
    - Run quick analyses (data → story, no notebook)
    - Perform comparison analyses
    - Execute enhanced analyses with RAG
    - Generate notebooks from existing stories
    
    Sub-crews:
    - DataCrew: Data fetching and validation
    - AnalysisCrew: Statistical analysis and visualization
    - StoryCrew: Story generation and enrichment
    - NotebookCrew: Quarto notebook generation
    """
    
    def __init__(
        self,
        audience: str = "internal",
        document_type: Optional[str] = None,
        process_type: str = "sequential"
    ):
        """
        Initialize the Master Crew.
        
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
        
        # Sub-crew instances (lazy loaded)
        self._crews: Dict[str, Any] = {}
        self._master_crew: Optional[Any] = None
        
        logger.info(f"MasterCrew initialized for audience={self.audience}, "
                   f"document_type={self.document_type}, process={process_type}")
    
    def _get_or_create_crews(self) -> List[Any]:
        """Get or create sub-crew instances."""
        if not self._crews:
            self._crews = {
                'data_crew': DataCrew(
                    audience=self.audience,
                    document_type=self.document_type,
                    process_type=self.process_type
                ),
                'analysis_crew': AnalysisCrew(
                    audience=self.audience,
                    document_type=self.document_type,
                    process_type=self.process_type
                ),
                'story_crew': StoryCrew(
                    audience=self.audience,
                    document_type=self.document_type,
                    process_type=self.process_type
                ),
                'notebook_crew': NotebookCrew(
                    audience=self.audience,
                    document_type=self.document_type,
                    process_type=self.process_type
                )
            }
        
        return list(self._crews.values())
    
    def get_data_crew(self) -> DataCrew:
        """Get the DataCrew instance."""
        if 'data_crew' not in self._crews:
            self._get_or_create_crews()
        return self._crews['data_crew']
    
    def get_analysis_crew(self) -> AnalysisCrew:
        """Get the AnalysisCrew instance."""
        if 'analysis_crew' not in self._crews:
            self._get_or_create_crews()
        return self._crews['analysis_crew']
    
    def get_story_crew(self) -> StoryCrew:
        """Get the StoryCrew instance."""
        if 'story_crew' not in self._crews:
            self._get_or_create_crews()
        return self._crews['story_crew']
    
    def get_notebook_crew(self) -> NotebookCrew:
        """Get the NotebookCrew instance."""
        if 'notebook_crew' not in self._crews:
            self._get_or_create_crews()
        return self._crews['notebook_crew']
    
    def get_master_crew(self) -> Any:
        """
        Get the master CrewAI Crew instance that orchestrates all sub-crews.
        
        Returns:
            Configured Crew instance
        """
        if self._master_crew is None:
            # Get the orchestrator agent
            orchestrator = AnalysisOrchestrator(
                audience=self.audience,
                document_type=self.document_type
            )
            
            # Also include notebook generator for direct access
            notebook_gen = NotebookGenerator(
                audience=self.audience,
                document_type=self.document_type
            )
            
            agents = [orchestrator, notebook_gen]
            
            if CREWAI_AVAILABLE:
                self._master_crew = Crew(
                    agents=agents,
                    process=self.process,
                    verbose=2,
                    memory=True,
                    cache=True,
                    max_rpm=None,
                    share_crew=True,
                    crew_name=f"MasterCrew_{self.audience}_{self.document_type}",
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
                        return {"status": "mocked", "result": "Master workflow mocked"}
                
                self._master_crew = MockCrew(
                    agents=agents,
                    process=self.process_type
                )
        
        return self._master_crew
    
    def execute_full_workflow(
        self,
        question: str,
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the complete analysis workflow.
        
        This mirrors the MCP full_analysis_workflow_tool, executing:
        1. Data fetching (via DataCrew)
        2. Analysis (via AnalysisCrew)
        3. Story generation (via StoryCrew)
        4. Notebook creation (via NotebookCrew, if requested)
        
        Args:
            question: The analysis question
            use_rag: Whether to use RAG enrichment for story generation
            include_notebook: Whether to generate a Quarto notebook
            output_path: Optional path for notebook output
            **kwargs: Additional workflow parameters
            
        Returns:
            Dictionary with complete workflow results
        """
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'steps': [],
            'warnings': [],
            'errors': []
        }
        
        try:
            # Step 1: Data fetching
            data_crew = self.get_data_crew()
            data_result = data_crew.fetch_all_data(
                question=question,
                audience=self.audience,
                document_type=self.document_type
            )
            
            result['steps'].append({
                'step': 1,
                'name': 'data_fetching',
                'status': data_result.get('status', 'error'),
                'result': data_result
            })
            
            if data_result.get('status') != 'success':
                result['status'] = 'partial_success'
                result['warnings'].append("Data fetching encountered errors")
            
            # Extract data from result
            all_data = data_result.get('data', {})
            
            # Step 2: Analysis
            analysis_crew = self.get_analysis_crew()
            analysis_result = analysis_crew.analyze_data(
                data=all_data,
                question=question
            )
            
            result['steps'].append({
                'step': 2,
                'name': 'analysis',
                'status': analysis_result.get('status', 'error'),
                'result': analysis_result
            })
            
            if analysis_result.get('status') != 'success':
                result['status'] = 'partial_success'
                result['warnings'].append("Analysis encountered errors")
            
            # Step 3: Story generation
            story_crew = self.get_story_crew()
            story_result = story_crew.generate_story(
                data=all_data,
                analysis=analysis_result,
                question=question,
                use_rag=use_rag
            )
            
            result['steps'].append({
                'step': 3,
                'name': 'story_generation',
                'status': story_result.get('status', 'error'),
                'result': story_result
            })
            
            if story_result.get('status') != 'success':
                result['status'] = 'partial_success'
                result['warnings'].append("Story generation encountered errors")
            
            result['story'] = story_result.get('story', '')
            result['data'] = all_data
            result['analysis'] = analysis_result
            
            # Step 4: Notebook generation (if requested)
            if include_notebook:
                notebook_crew = self.get_notebook_crew()
                notebook_result = notebook_crew.create_notebook_from_story(
                    story_result=story_result,
                    data=all_data,
                    analysis=analysis_result,
                    question=question,
                    output_path=output_path
                )
                
                result['steps'].append({
                    'step': 4,
                    'name': 'notebook_generation',
                    'status': notebook_result.get('status', 'error'),
                    'result': notebook_result
                })
                
                if notebook_result.get('status') == 'success':
                    result['notebook'] = notebook_result
                else:
                    result['status'] = 'partial_success'
                    result['warnings'].append("Notebook generation encountered errors")
            
            # Mark as completed
            if result['status'] == 'in_progress':
                result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Error in full workflow: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            result['errors'].append(str(e))
        
        return result
    
    def execute_quick_workflow(
        self,
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a quick analysis workflow (data + story, no notebook).
        
        This mirrors the MCP quick_analysis_tool.
        
        Args:
            question: The analysis question
            **kwargs: Additional workflow parameters
            
        Returns:
            Dictionary with quick workflow results
        """
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'steps': []
        }
        
        try:
            # Step 1: Data fetching
            data_crew = self.get_data_crew()
            data_result = data_crew.fetch_all_data(
                question=question
            )
            
            result['steps'].append({
                'step': 1,
                'name': 'data_fetching',
                'status': data_result.get('status', 'error')
            })
            
            all_data = data_result.get('data', {})
            
            # Step 2: Story generation (without full analysis)
            story_crew = self.get_story_crew()
            story_result = story_crew.generate_data_story(
                data=all_data,
                question=question,
                use_rag=kwargs.get('use_rag', True)
            )
            
            result['steps'].append({
                'step': 2,
                'name': 'story_generation',
                'status': story_result.get('status', 'error')
            })
            
            result['story'] = story_result.get('story', '')
            result['data'] = all_data
            result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Error in quick workflow: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def execute_comparison_workflow(
        self,
        question: str,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a comparison analysis workflow.
        
        This mirrors the MCP compare_analysis_tool.
        
        Args:
            question: The comparison question (e.g., "Compare Syria and Ukraine refugee trends")
            **kwargs: Additional workflow parameters
            
        Returns:
            Dictionary with comparison workflow results
        """
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'question': question,
            'audience': self.audience,
            'document_type': self.document_type,
            'comparison': True,
            'scenarios': [],
            'steps': []
        }
        
        try:
            # Parse comparison question to identify scenarios
            # This is a simplified implementation
            scenarios = self._parse_comparison_question(question)
            result['scenarios'] = scenarios
            
            comparison_results = []
            
            # Execute full workflow for each scenario
            for i, scenario in enumerate(scenarios):
                scenario_result = self.execute_full_workflow(
                    question=scenario,
                    include_notebook=False,  # Don't generate notebooks for individual scenarios
                    **kwargs
                )
                comparison_results.append(scenario_result)
            
            result['comparison_results'] = comparison_results
            result['status'] = 'success'
            
        except Exception as e:
            logger.error(f"Error in comparison workflow: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
        
        return result
    
    def _parse_comparison_question(self, question: str) -> List[str]:
        """
        Parse a comparison question to extract individual scenarios.
        
        This is a simple implementation that looks for keywords like
        "compare", "vs", "and", etc.
        
        Args:
            question: The comparison question
            
        Returns:
            List of individual scenario questions
        """
        # Simple parsing - this should be enhanced based on actual use cases
        question_lower = question.lower()
        
        if 'compare' in question_lower or 'vs' in question_lower:
            # Try to split by common comparison keywords
            if ' vs ' in question_lower:
                parts = question.split(' vs ')
                return [f"Analyze {part}" for part in parts]
            elif ' and ' in question_lower:
                parts = question.split(' and ')
                return [f"Analyze {part}" for part in parts]
            elif ' compare ' in question_lower:
                # Remove "compare" and split
                parts = question.replace('compare', '').split(',')
                return [f"Analyze {part.strip()}" for part in parts if part.strip()]
        
        # Default: treat as single scenario
        return [question]
    
    async def execute_async_workflow(
        self,
        question: str,
        workflow_type: str = "full",
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a workflow asynchronously.
        
        Args:
            question: The analysis question
            workflow_type: Type of workflow ('full', 'quick', 'comparison')
            **kwargs: Additional workflow parameters
            
        Returns:
            Dictionary with async execution results
        """
        crew = self.get_master_crew()
        
        try:
            inputs = {
                'question': question,
                'workflow_type': workflow_type,
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
                'crew': 'MasterCrew'
            }
        except Exception as e:
            logger.error(f"Error executing MasterCrew async: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'crew': 'MasterCrew'
            }
    
    def shutdown(self):
        """Shutdown all crews and clean up resources."""
        if self._master_crew and hasattr(self._master_crew, 'shutdown'):
            try:
                self._master_crew.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down master crew: {e}")
        
        # Shutdown all sub-crews
        for crew_name, crew in self._crews.items():
            try:
                if hasattr(crew, 'shutdown'):
                    crew.shutdown()
            except Exception as e:
                logger.error(f"Error shutting down {crew_name}: {e}")
        
        self._master_crew = None
        self._crews.clear()
        logger.info("MasterCrew shutdown complete")
