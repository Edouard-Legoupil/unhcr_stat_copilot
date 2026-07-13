"""
CrewAI MCP Integration for UNHCR Statistics Copilot

This module provides integration between CrewAI agents/crews and the MCP server.
It allows CrewAI workflows to be exposed as MCP tools, enabling AI clients to
use CrewAI agents through the MCP protocol.

The integration provides:
- CrewAI-based tool implementations that mirror MCP capabilities
- Adaptors to convert between MCP and CrewAI formats
- A unified interface for both MCP and CrewAI execution
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union
from functools import wraps

from backend.crewai.manager import CrewAIManager, WorkflowType
from backend.crewai.crews import DataCrew, AnalysisCrew, StoryCrew, NotebookCrew, MasterCrew
from backend.crewai.config import AudienceConfigManager

logger = logging.getLogger(__name__)


class CrewAIToolAdapter:
    """
    Adapter to expose CrewAI workflows as MCP-compatible tools.
    
    This class provides wrapper functions that can be registered as MCP tools,
    allowing AI clients to trigger CrewAI workflows through the MCP protocol.
    """
    
    def __init__(self, manager: Optional[CrewAIManager] = None):
        """
        Initialize the CrewAI Tool Adapter.
        
        Args:
            manager: Optional CrewAIManager instance (created if not provided)
        """
        self.manager = manager or CrewAIManager(initialize_agents=False)
        self._initialization_count = 0
    
    def _ensure_initialized(self):
        """Ensure the manager and agents are initialized."""
        if not hasattr(self.manager, '_initialized') or not self.manager._initialized:
            if self._initialization_count == 0:
                self.manager.initialize_agents()
                self.manager._initialized = True
            self._initialization_count += 1
    
    def get_manager(self) -> CrewAIManager:
        """Get the CrewAI manager, ensuring it's initialized."""
        self._ensure_initialized()
        return self.manager
    
    # -------------------------------------------------------------------------
    # Data Tools (mirror MCP data tools)
    # -------------------------------------------------------------------------
    
    def crewai_get_population_data_tool(
        self,
        coo: Optional[str] = None,
        coa: Optional[str] = None,
        year: Optional[Union[str, int]] = None,
        coo_all: bool = False,
        coa_all: bool = False,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of get_population_data.
        Uses the DataCrew to fetch population data.
        """
        self._ensure_initialized()
        
        try:
            # Create a DataCrew for this request
            data_crew = DataCrew(
                audience=audience,
                document_type=document_type
            )
            
            # Build parameters from MCP format
            parameters = {
                'coo': coo,
                'coa': coa,
                'year': year,
                'coo_all': coo_all,
                'coa_all': coa_all
            }
            
            # Build a question from parameters
            question_parts = []
            if coo:
                question_parts.append(f"country of origin: {coo}")
            if coa:
                question_parts.append(f"country of asylum: {coa}")
            if year:
                question_parts.append(f"year: {year}")
            
            question = f"Get population data for {', '.join(question_parts)}" if question_parts else "Get population data"
            
            result = data_crew.fetch_population_data(
                question=question,
                parameters=parameters
            )
            
            return result
            
        except Exception as e:
            logger.error(f"Error in crewai_get_population_data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_get_population_data'
            }
    
    def crewai_fetch_all_data_tool(
        self,
        question: str,
        audience: str = "internal",
        document_type: Optional[str] = None,
        parameters: Optional[Dict] = None
    ) -> Dict[str, Any]:
        """
        Fetch all types of UNHCR data using CrewAI.
        """
        self._ensure_initialized()
        
        try:
            data_crew = DataCrew(
                audience=audience,
                document_type=document_type
            )
            
            return data_crew.fetch_all_data(
                question=question,
                parameters=parameters or {}
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_fetch_all_data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_fetch_all_data'
            }
    
    # -------------------------------------------------------------------------
    # Analysis Tools (mirror MCP analysis tools)
    # -------------------------------------------------------------------------
    
    def crewai_analyze_data_statistics_tool(
        self,
        data: Dict[str, Any],
        question: str = "",
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of analyze_data_statistics.
        """
        self._ensure_initialized()
        
        try:
            analysis_crew = AnalysisCrew(
                audience=audience,
                document_type=document_type
            )
            
            return analysis_crew.analyze_data(
                data=data,
                question=question
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_analyze_data_statistics: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_analyze_data_statistics'
            }
    
    def crewai_apply_analysis_guardrails_tool(
        self,
        data: Dict[str, Any],
        analysis: Dict[str, Any],
        question: str = "",
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of apply_analysis_guardrails.
        """
        self._ensure_initialized()
        
        try:
            analysis_crew = AnalysisCrew(
                audience=audience,
                document_type=document_type
            )
            
            return analysis_crew.analyze_data(
                data=data,
                question=question
            ).get('guardrails', {})
            
        except Exception as e:
            logger.error(f"Error in crewai_apply_analysis_guardrails: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_apply_analysis_guardrails'
            }
    
    def crewai_extract_visualization_structure_tool(
        self,
        data: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None,
        question: str = "",
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of extract_visualization_structure.
        """
        self._ensure_initialized()
        
        try:
            from backend.crewai.agents import VisualizationExpert
            
            viz_expert = VisualizationExpert(
                audience=audience,
                document_type=document_type
            )
            
            return viz_expert.extract_visualization_structure(
                data=data,
                analysis=analysis or {},
                question=question
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_extract_visualization_structure: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_extract_visualization_structure'
            }
    
    def crewai_generate_visualization_description_tool(
        self,
        data: Dict[str, Any],
        analysis: Optional[Dict[str, Any]] = None,
        question: str = "",
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of generate_visualization_description.
        """
        self._ensure_initialized()
        
        try:
            from backend.crewai.agents import VisualizationExpert
            
            viz_expert = VisualizationExpert(
                audience=audience,
                document_type=document_type
            )
            
            return viz_expert.generate_visualization_description(
                data=data,
                analysis=analysis or {},
                question=question
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_generate_visualization_description: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_generate_visualization_description'
            }
    
    # -------------------------------------------------------------------------
    # Story Tools (mirror MCP story tools)
    # -------------------------------------------------------------------------
    
    def crewai_generate_analytical_story_tool(
        self,
        data: Dict[str, Any],
        question: str = "",
        use_rag: bool = True,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of generate_analytical_story.
        """
        self._ensure_initialized()
        
        try:
            story_crew = StoryCrew(
                audience=audience,
                document_type=document_type
            )
            
            # First analyze the data
            analysis_crew = AnalysisCrew(
                audience=audience,
                document_type=document_type
            )
            analysis = analysis_crew.analyze_data(
                data=data,
                question=question
            )
            
            return story_crew.generate_story(
                data=data,
                analysis=analysis,
                question=question,
                use_rag=use_rag
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_generate_analytical_story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_generate_analytical_story'
            }
    
    def crewai_get_data_for_story_tool(
        self,
        question: str,
        data: Optional[Dict[str, Any]] = None,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of get_data_for_story.
        """
        self._ensure_initialized()
        
        try:
            from backend.crewai.agents import AnalysisOrchestrator
            
            orchestrator = AnalysisOrchestrator(
                audience=audience,
                document_type=document_type
            )
            
            return orchestrator.get_data_for_story(
                question=question,
                data=data or {},
                audience=audience,
                document_type=document_type
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_get_data_for_story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_get_data_for_story'
            }
    
    # -------------------------------------------------------------------------
    # Notebook Tools (mirror MCP notebook tools)
    # -------------------------------------------------------------------------
    
    def crewai_create_quarto_notebook_tool(
        self,
        story_content: str,
        audience: str = "internal",
        document_type: Optional[str] = None,
        output_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of create_quarto_notebook.
        """
        self._ensure_initialized()
        
        try:
            notebook_crew = NotebookCrew(
                audience=audience,
                document_type=document_type
            )
            
            return notebook_crew.create_quarto_notebook(
                story_content=story_content,
                audience=audience,
                document_type=document_type,
                output_path=output_path
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_create_quarto_notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_create_quarto_notebook'
            }
    
    # -------------------------------------------------------------------------
    # Workflow Tools (mirror MCP workflow tools)
    # -------------------------------------------------------------------------
    
    def crewai_full_analysis_workflow_tool(
        self,
        question: str,
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of full_analysis_workflow.
        Executes the complete workflow using CrewAI crews.
        """
        self._ensure_initialized()
        
        try:
            master_crew = MasterCrew(
                audience=audience,
                document_type=document_type
            )
            
            return master_crew.execute_full_workflow(
                question=question,
                use_rag=use_rag,
                include_notebook=include_notebook,
                output_path=output_path
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_full_analysis_workflow: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_full_analysis_workflow'
            }
    
    def crewai_quick_analysis_tool(
        self,
        question: str,
        use_rag: bool = True,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of quick_analysis.
        """
        self._ensure_initialized()
        
        try:
            master_crew = MasterCrew(
                audience=audience,
                document_type=document_type
            )
            
            return master_crew.execute_quick_workflow(
                question=question,
                use_rag=use_rag
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_quick_analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_quick_analysis'
            }
    
    def crewai_compare_analysis_tool(
        self,
        question: str,
        use_rag: bool = True,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        CrewAI-based implementation of compare_analysis.
        """
        self._ensure_initialized()
        
        try:
            master_crew = MasterCrew(
                audience=audience,
                document_type=document_type
            )
            
            return master_crew.execute_comparison_workflow(
                question=question,
                use_rag=use_rag
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_compare_analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_compare_analysis'
            }
    
    # -------------------------------------------------------------------------
    # Manager-based workflow execution
    # -------------------------------------------------------------------------
    
    def crewai_execute_workflow_tool(
        self,
        question: str,
        workflow_type: str = "full_analysis",
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        audience: str = "internal",
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Execute any CrewAI workflow type through the manager.
        
        Args:
            question: The analysis question
            workflow_type: Type of workflow (full_analysis, quick_analysis, compare_analysis, etc.)
            use_rag: Whether to use RAG enrichment
            include_notebook: Whether to generate a notebook
            output_path: Output path for the notebook
            audience: Target audience
            document_type: Document type
            
        Returns:
            Workflow execution result
        """
        self._ensure_initialized()
        
        try:
            # Convert string workflow_type to WorkflowType enum if needed
            if isinstance(workflow_type, str):
                try:
                    workflow_type_enum = WorkflowType(workflow_type)
                except ValueError:
                    workflow_type_enum = WorkflowType.FULL_ANALYSIS
            else:
                workflow_type_enum = workflow_type
            
            return self.manager.execute_workflow(
                question=question,
                workflow_type=workflow_type_enum,
                use_rag=use_rag,
                include_notebook=include_notebook,
                output_path=output_path,
                audience=audience,
                document_type=document_type
            )
            
        except Exception as e:
            logger.error(f"Error in crewai_execute_workflow: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_execute_workflow'
            }
    
    def crewai_get_metrics_tool(self) -> Dict[str, Any]:
        """
        Get CrewAI manager metrics and observability data.
        """
        self._ensure_initialized()
        
        try:
            return self.manager.get_metrics()
            
        except Exception as e:
            logger.error(f"Error in crewai_get_metrics: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_get_metrics'
            }
    
    def crewai_reset_metrics_tool(self) -> Dict[str, Any]:
        """
        Reset CrewAI manager metrics.
        """
        self._ensure_initialized()
        
        try:
            self.manager.reset_metrics()
            return {'status': 'success', 'message': 'Metrics reset'}
            
        except Exception as e:
            logger.error(f"Error in crewai_reset_metrics: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'tool': 'crewai_reset_metrics'
            }
    
    # -------------------------------------------------------------------------
    # Utility methods
    # -------------------------------------------------------------------------
    
    def get_tool_registry(self) -> Dict[str, Callable]:
        """
        Get a registry of all CrewAI tools that can be registered with MCP.
        
        Returns:
            Dictionary mapping tool names to callable functions
        """
        return {
            # Data tools
            'crewai_get_population_data': self.crewai_get_population_data_tool,
            'crewai_fetch_all_data': self.crewai_fetch_all_data_tool,
            
            # Analysis tools
            'crewai_analyze_data_statistics': self.crewai_analyze_data_statistics_tool,
            'crewai_apply_analysis_guardrails': self.crewai_apply_analysis_guardrails_tool,
            'crewai_extract_visualization_structure': self.crewai_extract_visualization_structure_tool,
            'crewai_generate_visualization_description': self.crewai_generate_visualization_description_tool,
            
            # Story tools
            'crewai_generate_analytical_story': self.crewai_generate_analytical_story_tool,
            'crewai_get_data_for_story': self.crewai_get_data_for_story_tool,
            
            # Notebook tools
            'crewai_create_quarto_notebook': self.crewai_create_quarto_notebook_tool,
            
            # Workflow tools
            'crewai_full_analysis_workflow': self.crewai_full_analysis_workflow_tool,
            'crewai_quick_analysis': self.crewai_quick_analysis_tool,
            'crewai_compare_analysis': self.crewai_compare_analysis_tool,
            
            # Manager tools
            'crewai_execute_workflow': self.crewai_execute_workflow_tool,
            'crewai_get_metrics': self.crewai_get_metrics_tool,
            'crewai_reset_metrics': self.crewai_reset_metrics_tool,
        }


# Global adapter instance
crewai_adapter = CrewAIToolAdapter()


def get_crewai_tools() -> Dict[str, Callable]:
    """
    Get all CrewAI tools for MCP registration.
    
    Returns:
        Dictionary of CrewAI tool functions
    """
    return crewai_adapter.get_tool_registry()
