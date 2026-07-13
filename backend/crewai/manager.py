"""
CrewAI Manager for UNHCR Statistics Copilot

This module provides the main CrewAI manager that orchestrates all agents,
crews, and tools for the UNHCR Statistics Copilot. It serves as the central
entry point for executing analysis workflows using CrewAI agents.

The manager:
- Initializes and manages all CrewAI agents
- Provides workflow execution methods
- Maintains observability and metrics
- Handles agent coordination and delegation
- Preserves the Quarto notebook generation capability
"""

import asyncio
import logging
import time
from contextlib import asynccontextmanager
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

from backend.crewai.config import CrewAIConfig, AudienceConfigManager
from backend.crewai.agents import (
    UNHCRDataFetcher,
    RSDExpert,
    SolutionsExpert,
    DemographicsExpert,
    TemporalAnalyzer,
    GeographyExpert,
    StatisticalAnalyzer,
    GuardrailsValidator,
    ToolSelector,
    VisualizationExpert,
    StoryGenerator,
    RAGResearcher,
    AudienceAdapter,
    AnalysisOrchestrator,
    NotebookGenerator
)
from backend.crewai.tools.adapters import MCPToolAdapter, tool_registry

logger = logging.getLogger(__name__)


class WorkflowType(Enum):
    """Enumeration of supported workflow types."""
    FULL_ANALYSIS = "full_analysis"
    QUICK_ANALYSIS = "quick_analysis"
    COMPARE_ANALYSIS = "compare_analysis"
    ENHANCED_ANALYSIS = "enhanced_analysis"
    CONDITIONAL_ANALYSIS = "conditional_analysis"
    NOTEBOOK_ONLY = "notebook_only"
    DATA_ONLY = "data_only"
    STORY_ONLY = "story_only"


class WorkflowStatus(Enum):
    """Enumeration of workflow execution statuses."""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"
    ERROR = "error"
    TIMEOUT = "timeout"
    CANCELLED = "cancelled"


@dataclass
class WorkflowMetrics:
    """Metrics for a single workflow execution."""
    workflow_id: str
    workflow_type: str
    start_time: datetime
    end_time: Optional[datetime] = None
    duration_seconds: float = 0.0
    steps_completed: int = 0
    total_steps: int = 0
    status: str = "pending"
    agent_execution_times: Dict[str, float] = field(default_factory=dict)
    tool_execution_times: Dict[str, float] = field(default_factory=dict)
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'workflow_id': self.workflow_id,
            'workflow_type': self.workflow_type,
            'start_time': self.start_time.isoformat(),
            'end_time': self.end_time.isoformat() if self.end_time else None,
            'duration_seconds': self.duration_seconds,
            'steps_completed': self.steps_completed,
            'total_steps': self.total_steps,
            'status': self.status,
            'agent_execution_times': self.agent_execution_times,
            'tool_execution_times': self.tool_execution_times,
            'errors': self.errors,
            'warnings': self.warnings
        }


@dataclass
class AgentMetrics:
    """Metrics for agent execution."""
    agent_name: str
    execution_count: int = 0
    success_count: int = 0
    failure_count: int = 0
    total_execution_time: float = 0.0
    average_execution_time: float = 0.0
    last_execution: Optional[datetime] = None
    last_error: Optional[str] = None
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'agent_name': self.agent_name,
            'execution_count': self.execution_count,
            'success_count': self.success_count,
            'failure_count': self.failure_count,
            'total_execution_time': self.total_execution_time,
            'average_execution_time': self.average_execution_time,
            'last_execution': self.last_execution.isoformat() if self.last_execution else None,
            'last_error': self.last_error
        }


@dataclass
class ManagerMetrics:
    """Overall metrics for the CrewAI Manager."""
    total_workflows: int = 0
    completed_workflows: int = 0
    failed_workflows: int = 0
    total_execution_time: float = 0.0
    agent_metrics: Dict[str, AgentMetrics] = field(default_factory=dict)
    workflow_metrics: List[WorkflowMetrics] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_workflows': self.total_workflows,
            'completed_workflows': self.completed_workflows,
            'failed_workflows': self.failed_workflows,
            'total_execution_time': self.total_execution_time,
            'agent_metrics': {name: metrics.to_dict() for name, metrics in self.agent_metrics.items()},
            'workflow_metrics': [m.to_dict() for m in self.workflow_metrics]
        }


class CrewAIManager:
    """
    Main manager for CrewAI agents in UNHCR Statistics Copilot.
    
    This class provides:
    - Initialization and management of all CrewAI agents
    - Workflow execution with various modes
    - Comprehensive metrics and observability
    - Agent coordination and delegation
    - Quarto notebook generation preservation
    
    Usage:
        manager = CrewAIManager()
        
        # Execute a full workflow
        result = manager.execute_workflow(
            question="What are the refugee trends in Syria?",
            audience="internal",
            document_type="technical_report",
            workflow_type="full_analysis"
        )
        
        # Get metrics
        metrics = manager.get_metrics()
        
        # Cleanup
        manager.shutdown()
    """
    
    def __init__(self, initialize_agents: bool = True):
        """
        Initialize the CrewAI Manager.
        
        Args:
            initialize_agents: Whether to initialize all agents on startup
        """
        self.start_time = datetime.now()
        self._initialized = False
        self._shutting_down = False
        
        # Agent instances
        self._agents: Dict[str, Any] = {}
        
        # Metrics tracking
        self._metrics = ManagerMetrics()
        self._current_workflow_metrics: Optional[WorkflowMetrics] = None
        
        # Configuration
        self._config = CrewAIConfig
        
        # Workflow state
        self._active_workflows: Dict[str, WorkflowMetrics] = {}
        
        # Initialize agents if requested
        if initialize_agents:
            self.initialize_agents()
            self._initialized = True
            logger.info("CrewAI Manager initialized with all agents")
        else:
            logger.info("CrewAI Manager initialized (agents not loaded yet)")
    
    def initialize_agents(self) -> Dict[str, Any]:
        """
        Initialize all CrewAI agents.
        
        Returns:
            Dictionary of initialized agents
        """
        logger.info("Initializing CrewAI agents...")
        start_time = time.time()
        
        try:
            # Level 1: Specialist Agents (Data Fetchers)
            logger.info("Initializing Level 1 agents (Data Fetchers)...")
            self._agents['data_fetcher'] = UNHCRDataFetcher(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['rsd_expert'] = RSDExpert(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['solutions_expert'] = SolutionsExpert(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['demographics_expert'] = DemographicsExpert(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['temporal_analyzer'] = TemporalAnalyzer(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['geography_expert'] = GeographyExpert(
                audience='internal',
                document_type='technical_report'
            )
            
            logger.info("Level 1 agents initialized")
            
            # Level 2: Analysis Agents
            logger.info("Initializing Level 2 agents (Analysts)...")
            self._agents['statistical_analyzer'] = StatisticalAnalyzer(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['guardrails_validator'] = GuardrailsValidator(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['tool_selector'] = ToolSelector(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['visualization_expert'] = VisualizationExpert(
                audience='internal',
                document_type='technical_report'
            )
            
            logger.info("Level 2 agents initialized")
            
            # Level 3: Story Generation Agents
            logger.info("Initializing Level 3 agents (Story Generators)...")
            self._agents['story_generator'] = StoryGenerator(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['rag_researcher'] = RAGResearcher(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['audience_adapter'] = AudienceAdapter(
                audience='internal',
                document_type='technical_report'
            )
            
            logger.info("Level 3 agents initialized")
            
            # Level 4: Orchestration Agents
            logger.info("Initializing Level 4 agents (Orchestrators)...")
            self._agents['analysis_orchestrator'] = AnalysisOrchestrator(
                audience='internal',
                document_type='technical_report'
            )
            self._agents['notebook_generator'] = NotebookGenerator(
                audience='internal',
                document_type='technical_report'
            )
            
            logger.info("Level 4 agents initialized")
            
            # Set up agent references in orchestrators
            self._setup_agent_references()
            
            # Initialize metrics for all agents
            for agent_name, agent in self._agents.items():
                self._metrics.agent_metrics[agent_name] = AgentMetrics(
                    agent_name=agent_name
                )
            
            initialization_time = time.time() - start_time
            logger.info(f"All agents initialized in {initialization_time:.2f} seconds")
            
            return self._agents
            
        except Exception as e:
            logger.error(f"Error initializing agents: {e}")
            raise
    
    def _setup_agent_references(self):
        """Set up references between agents for orchestration."""
        logger.info("Setting up agent references...")
        
        try:
            # Get the orchestrator
            orchestrator = self._agents.get('analysis_orchestrator')
            if orchestrator:
                # Set all agent references
                orchestrator.set_agents(
                    data_fetcher=self._agents.get('data_fetcher'),
                    statistical_analyzer=self._agents.get('statistical_analyzer'),
                    guardrails_validator=self._agents.get('guardrails_validator'),
                    tool_selector=self._agents.get('tool_selector'),
                    visualization_expert=self._agents.get('visualization_expert'),
                    story_generator=self._agents.get('story_generator'),
                    rag_researcher=self._agents.get('rag_researcher'),
                    audience_adapter=self._agents.get('audience_adapter')
                )
                
                # Also set references for notebook generator
                notebook_gen = self._agents.get('notebook_generator')
                if notebook_gen and hasattr(notebook_gen, 'set_agents'):
                    notebook_gen.set_agents(
                        analysis_orchestrator=orchestrator,
                        story_generator=self._agents.get('story_generator'),
                        audience_adapter=self._agents.get('audience_adapter')
                    )
            
            logger.info("Agent references set up successfully")
            
        except Exception as e:
            logger.error(f"Error setting up agent references: {e}")
            raise
    
    def get_agent(self, agent_name: str) -> Any:
        """
        Get a specific agent by name.
        
        Args:
            agent_name: Name of the agent
            
        Returns:
            The agent instance
            
        Raises:
            ValueError: If agent not found
        """
        if agent_name not in self._agents:
            available = list(self._agents.keys())
            raise ValueError(
                f"Agent '{agent_name}' not found. Available agents: {available}"
            )
        return self._agents[agent_name]
    
    def list_agents(self) -> List[str]:
        """Get list of all initialized agent names."""
        return list(self._agents.keys())
    
    def get_agent_metrics(self, agent_name: str) -> Optional[AgentMetrics]:
        """Get metrics for a specific agent."""
        return self._metrics.agent_metrics.get(agent_name)
    
    def update_agent_metrics(
        self,
        agent_name: str,
        success: bool,
        execution_time: float,
        error: Optional[str] = None
    ):
        """
        Update metrics for a specific agent.
        
        Args:
            agent_name: Name of the agent
            success: Whether the execution was successful
            execution_time: Time taken in seconds
            error: Error message if failed
        """
        if agent_name not in self._metrics.agent_metrics:
            self._metrics.agent_metrics[agent_name] = AgentMetrics(
                agent_name=agent_name
            )
        
        metrics = self._metrics.agent_metrics[agent_name]
        metrics.execution_count += 1
        metrics.total_execution_time += execution_time
        metrics.last_execution = datetime.now()
        
        if success:
            metrics.success_count += 1
        else:
            metrics.failure_count += 1
            metrics.last_error = error
        
        # Update average
        if metrics.execution_count > 0:
            metrics.average_execution_time = (
                metrics.total_execution_time / metrics.execution_count
            )
    
    def execute_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: Optional[str] = None,
        workflow_type: Union[str, WorkflowType] = WorkflowType.FULL_ANALYSIS,
        use_rag: bool = True,
        include_notebook: bool = True,
        output_path: Optional[str] = None,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute a complete analysis workflow.
        
        This is the main entry point for running analysis workflows using
        CrewAI agents. It coordinates all agents and tools to produce
        comprehensive analysis results with Quarto notebook generation.
        
        Args:
            question: The user's question or analysis request
            audience: Target audience (internal, public_donors, private_donors, government, media)
            document_type: Document type (technical_report, long_read, executive_summary, etc.)
            workflow_type: Type of workflow to execute
            use_rag: Whether to use RAG enrichment for story generation
            include_notebook: Whether to generate a Quarto notebook
            output_path: Optional path for notebook output
            **kwargs: Additional workflow-specific parameters
            
        Returns:
            Dictionary containing:
            - status: Workflow status
            - result: Analysis result
            - notebook: Generated notebook content (if requested)
            - metrics: Workflow metrics
            - errors: List of errors encountered
        """
        # Generate workflow ID
        workflow_id = f"workflow_{int(time.time())}_{len(self._metrics.workflow_metrics)}"
        
        # Validate inputs
        audience = AudienceConfigManager.validate_audience(audience)
        if document_type:
            document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        else:
            document_type = AudienceConfigManager.get_default_type(audience)
        
        # Convert workflow_type if string
        if isinstance(workflow_type, str):
            try:
                workflow_type = WorkflowType(workflow_type)
            except ValueError:
                workflow_type = WorkflowType.FULL_ANALYSIS
                logger.warning(f"Invalid workflow_type '{workflow_type}', defaulting to FULL_ANALYSIS")
        
        # Initialize workflow metrics
        workflow_metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            workflow_type=workflow_type.value,
            start_time=datetime.now(),
            total_steps=self._get_total_steps(workflow_type),
            status=WorkflowStatus.IN_PROGRESS.value
        )
        
        self._current_workflow_metrics = workflow_metrics
        self._active_workflows[workflow_id] = workflow_metrics
        self._metrics.total_workflows += 1
        
        # Prepare result structure
        result: Dict[str, Any] = {
            'workflow_id': workflow_id,
            'status': WorkflowStatus.IN_PROGRESS.value,
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'workflow_type': workflow_type.value,
            'start_time': datetime.now().isoformat(),
            'steps': [],
            'errors': [],
            'warnings': [],
            'metrics': None,
            'notebook': None,
            'story': None,
            'data': None,
            'visualizations': None
        }
        
        workflow_start = time.time()
        
        try:
            # Route to appropriate workflow handler
            if workflow_type == WorkflowType.FULL_ANALYSIS:
                result.update(self._execute_full_analysis(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    use_rag=use_rag,
                    include_notebook=include_notebook,
                    output_path=output_path,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.QUICK_ANALYSIS:
                result.update(self._execute_quick_analysis(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.COMPARE_ANALYSIS:
                result.update(self._execute_compare_analysis(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.ENHANCED_ANALYSIS:
                result.update(self._execute_enhanced_analysis(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    use_rag=use_rag,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.CONDITIONAL_ANALYSIS:
                result.update(self._execute_conditional_analysis(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.NOTEBOOK_ONLY:
                result.update(self._execute_notebook_only(
                    story_content=kwargs.get('story_content', ''),
                    audience=audience,
                    document_type=document_type,
                    output_path=output_path,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.DATA_ONLY:
                result.update(self._execute_data_only(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            elif workflow_type == WorkflowType.STORY_ONLY:
                result.update(self._execute_story_only(
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    use_rag=use_rag,
                    workflow_metrics=workflow_metrics,
                    **kwargs
                ))
            
            # Mark workflow as completed
            workflow_metrics.status = WorkflowStatus.COMPLETED.value
            workflow_metrics.end_time = datetime.now()
            workflow_metrics.duration_seconds = time.time() - workflow_start
            workflow_metrics.steps_completed = len(result.get('steps', []))
            
            result['status'] = WorkflowStatus.COMPLETED.value
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = workflow_metrics.duration_seconds
            result['metrics'] = workflow_metrics.to_dict()
            
            self._metrics.completed_workflows += 1
            self._metrics.total_execution_time += workflow_metrics.duration_seconds
            
            logger.info(f"Workflow {workflow_id} completed successfully in {workflow_metrics.duration_seconds:.2f}s")
            
        except Exception as e:
            # Mark workflow as failed
            workflow_metrics.status = WorkflowStatus.ERROR.value
            workflow_metrics.end_time = datetime.now()
            workflow_metrics.duration_seconds = time.time() - workflow_start
            workflow_metrics.errors.append(str(e))
            
            result['status'] = WorkflowStatus.ERROR.value
            result['end_time'] = datetime.now().isoformat()
            result['error'] = str(e)
            result['duration_seconds'] = workflow_metrics.duration_seconds
            result['metrics'] = workflow_metrics.to_dict()
            
            self._metrics.failed_workflows += 1
            
            logger.error(f"Workflow {workflow_id} failed: {e}")
            raise
        
        finally:
            # Clean up current workflow
            self._current_workflow_metrics = None
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
            
            # Store workflow metrics
            self._metrics.workflow_metrics.append(workflow_metrics)
        
        return result
    
    def _get_total_steps(self, workflow_type: WorkflowType) -> int:
        """Get the total number of steps for a workflow type."""
        step_counts = {
            WorkflowType.FULL_ANALYSIS: 8,
            WorkflowType.QUICK_ANALYSIS: 4,
            WorkflowType.COMPARE_ANALYSIS: 6,
            WorkflowType.ENHANCED_ANALYSIS: 7,
            WorkflowType.CONDITIONAL_ANALYSIS: 5,
            WorkflowType.NOTEBOOK_ONLY: 2,
            WorkflowType.DATA_ONLY: 2,
            WorkflowType.STORY_ONLY: 4
        }
        return step_counts.get(workflow_type, 4)
    
    def _execute_full_analysis(
        self,
        question: str,
        audience: str,
        document_type: str,
        use_rag: bool,
        include_notebook: bool,
        output_path: Optional[str],
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the full analysis workflow using the AnalysisOrchestrator."""
        logger.info("Executing full analysis workflow")
        
        orchestrator = self._agents.get('analysis_orchestrator')
        if not orchestrator:
            raise ValueError("AnalysisOrchestrator not initialized")
        
        # Execute the orchestrated workflow
        workflow_result = orchestrator.execute_full_workflow(
            question=question,
            audience=audience,
            document_type=document_type,
            use_rag=use_rag,
            include_notebook=include_notebook,
            **kwargs
        )
        
        # Track metrics
        workflow_metrics.steps_completed = len(workflow_result.get('steps', []))
        
        # Update agent metrics
        self.update_agent_metrics(
            'analysis_orchestrator',
            success=workflow_result.get('status') == 'success',
            execution_time=workflow_metrics.duration_seconds,
            error=workflow_result.get('error')
        )
        
        return workflow_result
    
    def _execute_quick_analysis(
        self,
        question: str,
        audience: str,
        document_type: str,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a quick analysis workflow (data + story, no notebook)."""
        logger.info("Executing quick analysis workflow")
        
        data_fetcher = self._agents.get('data_fetcher')
        story_generator = self._agents.get('story_generator')
        tool_selector = self._agents.get('tool_selector')
        
        if not data_fetcher or not story_generator:
            raise ValueError("Required agents not initialized for quick analysis")
        
        # Step 1: Tool selection
        parameters = {}
        if tool_selector:
            tool_selection = tool_selector.select_tools(
                question=question,
                audience=audience,
                document_type=document_type
            )
            parameters = tool_selection.get('selection', {}).get('parameters', {})
        
        # Step 2: Data retrieval
        data_result = data_fetcher.fetch_population_data(
            question=question,
            parameters=parameters,
            audience=audience,
            document_type=document_type
        )
        
        # Step 3: Story generation
        story_result = story_generator.generate_story(
            data=data_result.get('data', {}),
            question=question,
            audience=audience,
            document_type=document_type,
            use_rag=kwargs.get('use_rag', False)
        )
        
        result = {
            'status': 'success',
            'steps': [
                {'step': 1, 'name': 'tool_selection', 'status': 'success'},
                {'step': 2, 'name': 'data_retrieval', 'status': data_result.get('status', 'error')},
                {'step': 3, 'name': 'story_generation', 'status': story_result.get('status', 'error')}
            ],
            'data': data_result.get('data', {}),
            'story': story_result.get('story', ''),
            'question': question,
            'audience': audience,
            'document_type': document_type
        }
        
        workflow_metrics.steps_completed = 3
        
        return result
    
    def _execute_compare_analysis(
        self,
        question: str,
        audience: str,
        document_type: str,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a comparison analysis workflow."""
        logger.info("Executing compare analysis workflow")
        
        orchestrator = self._agents.get('analysis_orchestrator')
        if not orchestrator:
            raise ValueError("AnalysisOrchestrator not initialized")
        
        # For comparison, we need to parse the question for multiple scenarios
        # This is a simplified implementation
        comparison_result = orchestrator.execute_comparison_workflow(
            question=question,
            audience=audience,
            document_type=document_type,
            **kwargs
        )
        
        workflow_metrics.steps_completed = len(comparison_result.get('steps', []))
        
        return comparison_result
    
    def _execute_enhanced_analysis(
        self,
        question: str,
        audience: str,
        document_type: str,
        use_rag: bool,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute an enhanced analysis with full pipeline."""
        logger.info("Executing enhanced analysis workflow")
        
        orchestrator = self._agents.get('analysis_orchestrator')
        if not orchestrator:
            raise ValueError("AnalysisOrchestrator not initialized")
        
        result = orchestrator.execute_enhanced_workflow(
            question=question,
            audience=audience,
            document_type=document_type,
            use_rag=use_rag,
            **kwargs
        )
        
        workflow_metrics.steps_completed = len(result.get('steps', []))
        
        return result
    
    def _execute_conditional_analysis(
        self,
        question: str,
        audience: str,
        document_type: str,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a conditional analysis workflow."""
        logger.info("Executing conditional analysis workflow")
        
        orchestrator = self._agents.get('analysis_orchestrator')
        if not orchestrator:
            raise ValueError("AnalysisOrchestrator not initialized")
        
        result = orchestrator.execute_conditional_workflow(
            question=question,
            audience=audience,
            document_type=document_type,
            **kwargs
        )
        
        workflow_metrics.steps_completed = len(result.get('steps', []))
        
        return result
    
    def _execute_notebook_only(
        self,
        story_content: str,
        audience: str,
        document_type: str,
        output_path: Optional[str],
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a Quarto notebook from story content."""
        logger.info("Executing notebook-only workflow")
        
        notebook_generator = self._agents.get('notebook_generator')
        if not notebook_generator:
            raise ValueError("NotebookGenerator not initialized")
        
        result = notebook_generator.generate_notebook(
            story_content=story_content,
            audience=audience,
            document_type=document_type,
            output_path=output_path,
            **kwargs
        )
        
        workflow_metrics.steps_completed = 2
        
        return result
    
    def _execute_data_only(
        self,
        question: str,
        audience: str,
        document_type: str,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute data retrieval only."""
        logger.info("Executing data-only workflow")
        
        data_fetcher = self._agents.get('data_fetcher')
        if not data_fetcher:
            raise ValueError("DataFetcher not initialized")
        
        tool_selector = self._agents.get('tool_selector')
        
        # Get parameters
        parameters = {}
        if tool_selector:
            tool_selection = tool_selector.select_tools(
                question=question,
                audience=audience,
                document_type=document_type
            )
            parameters = tool_selection.get('selection', {}).get('parameters', {})
        
        result = data_fetcher.fetch_population_data(
            question=question,
            parameters=parameters,
            audience=audience,
            document_type=document_type
        )
        
        workflow_metrics.steps_completed = 2
        
        return result
    
    def _execute_story_only(
        self,
        question: str,
        audience: str,
        document_type: str,
        use_rag: bool,
        workflow_metrics: WorkflowMetrics,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate a story from data."""
        logger.info("Executing story-only workflow")
        
        story_generator = self._agents.get('story_generator')
        rag_researcher = self._agents.get('rag_researcher')
        audience_adapter = self._agents.get('audience_adapter')
        data_fetcher = self._agents.get('data_fetcher')
        tool_selector = self._agents.get('tool_selector')
        
        if not story_generator or not data_fetcher:
            raise ValueError("Required agents not initialized for story generation")
        
        # Get data first
        parameters = {}
        if tool_selector:
            tool_selection = tool_selector.select_tools(
                question=question,
                audience=audience,
                document_type=document_type
            )
            parameters = tool_selection.get('selection', {}).get('parameters', {})
        
        data_result = data_fetcher.fetch_population_data(
            question=question,
            parameters=parameters,
            audience=audience,
            document_type=document_type
        )
        
        # Generate story
        story_result = story_generator.generate_story(
            data=data_result.get('data', {}),
            question=question,
            audience=audience,
            document_type=document_type,
            use_rag=use_rag
        )
        
        # Optionally enrich with RAG
        if use_rag and rag_researcher:
            enriched_story = rag_researcher.enrich_story(
                story=story_result.get('story', ''),
                question=question,
                audience=audience,
                document_type=document_type
            )
            story_result['story'] = enriched_story.get('enriched_story', story_result.get('story', ''))
        
        # Apply audience adaptation
        if audience_adapter:
            adapted_story = audience_adapter.adapt_story(
                story=story_result.get('story', ''),
                audience=audience,
                document_type=document_type
            )
            story_result['story'] = adapted_story.get('adapted_story', story_result.get('story', ''))
        
        result = {
            'status': 'success',
            'steps': [
                {'step': 1, 'name': 'data_retrieval', 'status': data_result.get('status', 'error')},
                {'step': 2, 'name': 'story_generation', 'status': story_result.get('status', 'error')},
                {'step': 3, 'name': 'rag_enrichment', 'status': 'success' if use_rag else 'skipped'},
                {'step': 4, 'name': 'audience_adaptation', 'status': 'success'}
            ],
            'story': story_result.get('story', ''),
            'data': data_result.get('data', {}),
            'question': question,
            'audience': audience,
            'document_type': document_type
        }
        
        workflow_metrics.steps_completed = 4
        
        return result
    
    @asynccontextmanager
    async def async_workflow_context(self, workflow_id: Optional[str] = None):
        """
        Context manager for async workflow execution.
        
        Args:
            workflow_id: Optional workflow ID (generated if not provided)
            
        Yields:
            Workflow metrics for the current workflow
        """
        if workflow_id is None:
            workflow_id = f"async_workflow_{int(time.time())}"
        
        workflow_metrics = WorkflowMetrics(
            workflow_id=workflow_id,
            workflow_type="async",
            start_time=datetime.now(),
            status=WorkflowStatus.IN_PROGRESS.value
        )
        
        self._current_workflow_metrics = workflow_metrics
        self._active_workflows[workflow_id] = workflow_metrics
        
        try:
            yield workflow_metrics
            workflow_metrics.status = WorkflowStatus.COMPLETED.value
        except Exception as e:
            workflow_metrics.status = WorkflowStatus.ERROR.value
            workflow_metrics.errors.append(str(e))
            raise
        finally:
            workflow_metrics.end_time = datetime.now()
            workflow_metrics.duration_seconds = (
                workflow_metrics.end_time - workflow_metrics.start_time
            ).total_seconds()
            
            self._current_workflow_metrics = None
            if workflow_id in self._active_workflows:
                del self._active_workflows[workflow_id]
            
            self._metrics.workflow_metrics.append(workflow_metrics)
    
    def get_metrics(self, include_history: bool = True) -> Dict[str, Any]:
        """
        Get all metrics for the manager.
        
        Args:
            include_history: Whether to include historical workflow metrics
            
        Returns:
            Dictionary containing all metrics
        """
        metrics_dict = self._metrics.to_dict()
        
        if not include_history:
            metrics_dict['workflow_metrics'] = []
        
        metrics_dict['uptime_seconds'] = (datetime.now() - self.start_time).total_seconds()
        metrics_dict['initialized'] = self._initialized
        metrics_dict['agent_count'] = len(self._agents)
        
        return metrics_dict
    
    def get_active_workflows(self) -> Dict[str, Dict[str, Any]]:
        """Get information about currently active workflows."""
        return {
            workflow_id: metrics.to_dict()
            for workflow_id, metrics in self._active_workflows.items()
        }
    
    def reset_metrics(self):
        """Reset all metrics."""
        self._metrics = ManagerMetrics()
        
        # Reset agent metrics
        for agent in self._agents.values():
            if hasattr(agent, 'reset_metrics'):
                agent.reset_metrics()
        
        logger.info("All metrics reset")
    
    def reload_configuration(self):
        """Reload configuration from environment variables."""
        CrewAIConfig.load_from_env()
        logger.info("Configuration reloaded")
    
    def shutdown(self):
        """Shutdown the manager and all agents."""
        if self._shutting_down:
            return
        
        self._shutting_down = True
        logger.info("Shutting down CrewAI Manager...")
        
        try:
            # Shutdown all agents
            for agent_name, agent in self._agents.items():
                try:
                    if hasattr(agent, 'shutdown'):
                        agent.shutdown()
                    logger.info(f"Shut down agent: {agent_name}")
                except Exception as e:
                    logger.error(f"Error shutting down agent {agent_name}: {e}")
            
            # Clear agent references
            self._agents.clear()
            self._initialized = False
            
            logger.info("CrewAI Manager shutdown complete")
            
        except Exception as e:
            logger.error(f"Error during shutdown: {e}")
            raise
    
    def __del__(self):
        """Destructor to ensure proper cleanup."""
        try:
            self.shutdown()
        except Exception:
            pass
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.shutdown()
        return False


# Global manager instance (lazy loaded)
_manager: Optional[CrewAIManager] = None


def get_manager() -> CrewAIManager:
    """
    Get the global CrewAI manager instance.
    
    Returns:
        The global CrewAIManager instance
    """
    global _manager
    if _manager is None:
        _manager = CrewAIManager()
    return _manager


def reset_manager():
    """Reset the global CrewAI manager instance."""
    global _manager
    if _manager is not None:
        _manager.shutdown()
    _manager = CrewAIManager()
