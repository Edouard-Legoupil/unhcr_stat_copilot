"""
Orchestration Agents for UNHCR Statistics Copilot

These agents manage complete analysis workflows and coordinate
multiple specialist agents to achieve complex tasks.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import jinja2
import os

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.config import CrewAIConfig, AudienceConfigManager

logger = logging.getLogger(__name__)


class AnalysisOrchestrator(UNHCRBaseAgent):
    """
    Master agent that coordinates complete analysis workflows.
    
    This agent manages the end-to-end analysis process from question
    to Quarto notebook, orchestrating all other agents as needed.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Analysis Orchestrator agent."""
        kwargs.setdefault('role', 'Analysis Orchestrator')
        kwargs.setdefault('goal', 'Deliver end-to-end analysis from question to Quarto notebook')
        
        super().__init__(**kwargs)
        
        # Initialize agent references (will be set by the manager)
        self.data_fetcher = None
        self.statistical_analyzer = None
        self.guardrails_validator = None
        self.tool_selector = None
        self.visualization_expert = None
        self.story_generator = None
        self.rag_researcher = None
        self.audience_adapter = None
        
        # Initialize Jinja2 environment for notebook generation
        self._init_jinja2()
        
        # Initialize tool registry
        self._register_tools()
    
    def _init_jinja2(self):
        """Initialize Jinja2 environment for template rendering."""
        try:
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'templates'
            )
            
            if os.path.exists(template_dir):
                self.jinja_env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(template_dir),
                    autoescape=True
                )
                logger.info(f"Jinja2 environment initialized with template directory: {template_dir}")
            else:
                logger.warning(f"Template directory not found: {template_dir}")
                self.jinja_env = jinja2.Environment(autoescape=True)
                
        except Exception as e:
            logger.error(f"Error initializing Jinja2: {e}")
            self.jinja_env = jinja2.Environment(autoescape=True)
    
    def _register_tools(self):
        """Register orchestration tools."""
        # This agent uses other agents as tools rather than external tools
        self.tools = []
    
    def set_agents(
        self,
        data_fetcher: Any = None,
        statistical_analyzer: Any = None,
        guardrails_validator: Any = None,
        tool_selector: Any = None,
        visualization_expert: Any = None,
        story_generator: Any = None,
        rag_researcher: Any = None,
        audience_adapter: Any = None
    ):
        """
        Set references to other agents for orchestration.
        
        Args:
            data_fetcher: UNHCRDataFetcher instance
            statistical_analyzer: StatisticalAnalyzer instance
            guardrails_validator: GuardrailsValidator instance
            tool_selector: ToolSelector instance
            visualization_expert: VisualizationExpert instance
            story_generator: StoryGenerator instance
            rag_researcher: RAGResearcher instance
            audience_adapter: AudienceAdapter instance
        """
        self.data_fetcher = data_fetcher
        self.statistical_analyzer = statistical_analyzer
        self.guardrails_validator = guardrails_validator
        self.tool_selector = tool_selector
        self.visualization_expert = visualization_expert
        self.story_generator = story_generator
        self.rag_researcher = rag_researcher
        self.audience_adapter = audience_adapter
        
        logger.info("Analysis Orchestrator: Agent references set")
    
    def execute_full_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        use_rag: bool = True,
        include_notebook: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the complete analysis workflow.
        
        This method coordinates all steps:
        1. Question analysis and tool selection
        2. Data retrieval
        3. Statistical analysis
        4. Guardrails validation
        5. Visualization extraction
        6. Story generation
        7. Audience adaptation
        8. Quarto notebook generation (optional)
        
        Args:
            question: The user's question
            audience: Target audience
            document_type: Document type
            use_rag: Whether to use RAG enrichment
            include_notebook: Whether to generate a Quarto notebook
            **kwargs: Additional workflow parameters
            
        Returns:
            Complete analysis result
        """
        # Start timing
        start_time = datetime.now()
        workflow_steps = []
        
        # Validate inputs
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        # Get configuration
        config = AudienceConfigManager.get_config(audience, document_type)
        
        result = {
            'status': 'in_progress',
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'workflow': 'full_analysis',
            'start_time': start_time.isoformat(),
            'steps': [],
            'errors': []
        }
        
        try:
            # Step 1: Tool selection
            logger.info("Step 1/7: Selecting tools for question")
            step_start = datetime.now()
            
            if self.tool_selector:
                tool_selection = self.tool_selector.select_tools(
                    question=question,
                    audience=audience,
                    document_type=document_type
                )
                workflow_steps.append({
                    'step': 1,
                    'name': 'tool_selection',
                    'status': tool_selection.get('status', 'success'),
                    'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                    'result': tool_selection
                })
                
                # Extract parameters from tool selection
                parameters = tool_selection.get('selection', {}).get('parameters', {})
            else:
                # Fallback: extract parameters from question
                from backend.question_parser import extract_question_parameters
                parameters = extract_question_parameters(question)
                tool_selection = {'status': 'fallback', 'selection': {'tool': 'auto'}}
                workflow_steps.append({
                    'step': 1,
                    'name': 'tool_selection',
                    'status': 'fallback',
                    'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                    'result': tool_selection
                })
            
            # Step 2: Data retrieval
            logger.info("Step 2/7: Retrieving data")
            step_start = datetime.now()
            
            if self.data_fetcher:
                data_result = self.data_fetcher.fetch_population_data(
                    question=question,
                    parameters=parameters,
                    audience=audience,
                    document_type=document_type
                )
            else:
                data_result = {'status': 'error', 'error': 'Data fetcher not available'}
            
            workflow_steps.append({
                'step': 2,
                'name': 'data_retrieval',
                'status': data_result.get('status', 'error'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': data_result
            })
            
            # Check for data retrieval errors
            if data_result.get('status') != 'success':
                result['status'] = 'error'
                result['error'] = data_result.get('error', 'Data retrieval failed')
                result['steps'] = workflow_steps
                result['completed_steps'] = 2
                result['total_steps'] = 7
                return result
            
            # Step 3: Statistical analysis
            logger.info("Step 3/7: Performing statistical analysis")
            step_start = datetime.now()
            
            if self.statistical_analyzer:
                # Handle data that might be a JSON string from MCPToolAdapter
                data_value = data_result.get('data', {})
                if isinstance(data_value, str):
                    import json
                    data_value = json.loads(data_value)
                
                data_items = data_value.get('items', []) if isinstance(data_value, dict) else []
                if isinstance(data_items, dict):
                    # Handle nested data structure
                    data_items = list(data_items.values()) if isinstance(data_items, dict) else []
                
                analysis_result = self.statistical_analyzer.analyze_data(
                    data=data_items,
                    audience=audience,
                    document_type=document_type
                )
            else:
                analysis_result = {'status': 'skipped', 'error': 'Statistical analyzer not available'}
            
            workflow_steps.append({
                'step': 3,
                'name': 'statistical_analysis',
                'status': analysis_result.get('status', 'skipped'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': analysis_result
            })
            
            # Step 4: Guardrails validation
            logger.info("Step 4/7: Validating with guardrails")
            step_start = datetime.now()
            
            if self.guardrails_validator:
                # Handle data that might be a JSON string
                data_value = data_result.get('data', {})
                if isinstance(data_value, str):
                    import json
                    data_value = json.loads(data_value)
                
                validation_result = self.guardrails_validator.validate_analysis(
                    analysis_request={'context': question, 'data_fields': list(parameters.keys())},
                    data=data_value,
                    audience=audience,
                    document_type=document_type
                )
            else:
                validation_result = {'status': 'skipped', 'compliance_score': 0}
            
            workflow_steps.append({
                'step': 4,
                'name': 'guardrails_validation',
                'status': validation_result.get('status', 'skipped'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': validation_result
            })
            
            # Step 5: Visualization extraction
            logger.info("Step 5/7: Extracting visualization")
            step_start = datetime.now()
            
            if self.visualization_expert:
                # Handle data that might be a JSON string
                data_value = data_result.get('data', {})
                if isinstance(data_value, str):
                    import json
                    data_value = json.loads(data_value)
                
                viz_result = self.visualization_expert.extract_visualization(
                    data=data_value,
                    audience=audience,
                    document_type=document_type
                )
            else:
                viz_result = {'status': 'skipped'}
            
            workflow_steps.append({
                'step': 5,
                'name': 'visualization_extraction',
                'status': viz_result.get('status', 'skipped'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': viz_result
            })
            
            # Step 6: Story generation
            logger.info("Step 6/7: Generating story")
            step_start = datetime.now()
            
            # Build enriched data for story generation
            enriched_data = {
                **data_result.get('data', {}),
                'statistics': analysis_result.get('analysis') if analysis_result.get('status') == 'success' else None,
                'guardrails': validation_result if validation_result.get('status') == 'success' else None,
                'visualization': viz_result if viz_result.get('status') == 'success' else None
            }
            
            if self.story_generator:
                story_result = self.story_generator.generate_story(
                    data=enriched_data,
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    use_rag=use_rag,
                    analysis_config=config
                )
            else:
                story_result = {'status': 'error', 'error': 'Story generator not available'}
            
            workflow_steps.append({
                'step': 6,
                'name': 'story_generation',
                'status': story_result.get('status', 'error'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': story_result
            })
            
            # Check for story generation errors
            if story_result.get('status') != 'success':
                result['status'] = 'error'
                result['error'] = story_result.get('error', 'Story generation failed')
                result['steps'] = workflow_steps
                result['completed_steps'] = 6
                result['total_steps'] = 7
                return result
            
            # Step 7: Audience adaptation
            logger.info("Step 7/7: Adapting to audience")
            step_start = datetime.now()
            
            if self.audience_adapter:
                adapted_story = self.audience_adapter.adapt_story(
                    story=story_result.get('story', ''),
                    audience=audience,
                    document_type=document_type,
                    question=question
                )
            else:
                adapted_story = story_result
            
            workflow_steps.append({
                'step': 7,
                'name': 'audience_adaptation',
                'status': adapted_story.get('status', 'success'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': adapted_story
            })
            
            # Generate Quarto notebook if requested
            notebook = None
            notebook_metadata = None
            
            if include_notebook:
                logger.info("Generating Quarto notebook")
                notebook_start = datetime.now()
                
                notebook_result = self.generate_notebook(
                    story_content=adapted_story.get('adapted_story', story_result.get('story', '')),
                    data=enriched_data,
                    question=question,
                    audience=audience,
                    document_type=document_type,
                    analysis_log=workflow_steps,
                    metadata={
                        'workflow': 'full_analysis',
                        'compliance_score': validation_result.get('compliance_score', 0),
                        'analysis_config': config
                    }
                )
                
                notebook = notebook_result.get('notebook')
                notebook_metadata = notebook_result.get('metadata')
                
                workflow_steps.append({
                    'step': 8,
                    'name': 'notebook_generation',
                    'status': notebook_result.get('status', 'success'),
                    'duration_ms': (datetime.now() - notebook_start).total_seconds() * 1000,
                    'result': {'notebook_length': len(notebook) if notebook else 0}
                })
            
            # Build final result
            result = {
                'status': 'success',
                'question': question,
                'audience': audience,
                'document_type': document_type,
                'workflow': 'full_analysis',
                'start_time': start_time.isoformat(),
                'end_time': datetime.now().isoformat(),
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'steps': workflow_steps,
                'completed_steps': 7 + (1 if include_notebook else 0),
                'total_steps': 7 + (1 if include_notebook else 0),
                'data': data_result.get('data', {}),
                'analysis': analysis_result.get('analysis') if analysis_result.get('status') == 'success' else None,
                'validation': validation_result if validation_result.get('status') == 'success' else None,
                'visualization': viz_result if viz_result.get('status') == 'success' else None,
                'story': story_result.get('story', ''),
                'adapted_story': adapted_story.get('adapted_story', story_result.get('story', '')),
                'notebook': notebook,
                'notebook_metadata': notebook_metadata,
                'compliance_score': validation_result.get('compliance_score', 0),
                'config': config,
                'rag_used': use_rag and CrewAIConfig.RAG_ENABLED,
                'errors': [s for s in workflow_steps if s.get('status') == 'error']
            }
            
            logger.info("Full analysis workflow completed successfully")
            return result
            
        except Exception as e:
            logger.error(f"Full analysis workflow failed: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            result['steps'] = workflow_steps
            result['completed_steps'] = len(workflow_steps)
            result['total_steps'] = 7 + (1 if include_notebook else 0)
            return result
    
    def generate_notebook(
        self,
        story_content: str,
        data: Dict[str, Any],
        question: str,
        audience: str,
        document_type: str,
        analysis_log: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a Quarto notebook from analysis results.
        
        Args:
            story_content: The generated story/narrative
            data: The analysis data
            question: Original user question
            audience: Target audience
            document_type: Document type
            analysis_log: Workflow execution log
            metadata: Additional metadata
            
        Returns:
            Quarto notebook content with metadata
        """
        try:
            # Select template based on document type
            template_name = self._select_template(document_type)
            
            # Get the template
            template = self.jinja_env.get_template(template_name)
            
            # Prepare context
            context = self._prepare_context(
                story_content=story_content,
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                analysis_log=analysis_log,
                metadata=metadata or {}
            )
            
            # Render the template
            notebook_content = template.render(**context)
            
            # Generate observability data
            observability = self._generate_observability_data(
                story_content=story_content,
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                analysis_log=analysis_log
            )
            
            return {
                'status': 'success',
                'notebook': notebook_content,
                'template': template_name,
                'metadata': {
                    **observability,
                    'audience': audience,
                    'document_type': document_type,
                    'question': question,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'template': None,
                'metadata': {
                    'audience': audience,
                    'document_type': document_type
                }
            }
    
    def _select_template(self, document_type: str) -> str:
        """Select the appropriate Jinja2 template."""
        template_map = {
            'technical_report': 'technical_report.j2',
            'executive_summary': 'executive_summary.j2',
            'long_read': 'long_read.j2',
            'social_media': 'social_media.j2',
            'linkedin_post': 'linkedin_post.j2'
        }
        return template_map.get(document_type, 'base_quarto.j2')
    
    def _prepare_context(self, **kwargs) -> Dict[str, Any]:
        """Prepare context for template rendering."""
        context = {}
        
        for key, value in kwargs.items():
            if isinstance(value, dict):
                context[key] = self._convert_dict(value)
            elif isinstance(value, list):
                context[key] = self._convert_list(value)
            else:
                context[key] = value
        
        # Add default context
        context.update({
            'generated_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'source': 'UNHCR Statistics Copilot - CrewAI'
        })
        
        return context
    
    def _convert_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary to template-friendly format."""
        return {k: self._convert_value(v) for k, v in d.items()}
    
    def _convert_list(self, lst: List[Any]) -> List[Any]:
        """Convert list to template-friendly format."""
        return [self._convert_value(v) for v in lst]
    
    def _convert_value(self, value: Any) -> Any:
        """Convert a value to template-friendly format."""
        if isinstance(value, dict):
            return self._convert_dict(value)
        elif isinstance(value, list):
            return self._convert_list(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return value
    
    def _generate_observability_data(self, **kwargs) -> Dict[str, Any]:
        """Generate observability data for the notebook."""
        analysis_log = kwargs.get('analysis_log', [])
        
        # Generate analysis log markdown
        log_markdown = self._generate_analysis_log_markdown(analysis_log)
        
        return {
            'analysis_log': log_markdown,
            'tool_execution_summary': self._get_tool_execution_summary(analysis_log),
            'performance_metrics': self._get_performance_metrics(analysis_log)
        }
    
    def _generate_analysis_log_markdown(self, steps: List[Dict[str, Any]]) -> str:
        """Generate a markdown analysis log from workflow steps."""
        if not steps:
            return "No analysis log available"
        
        lines = ["## Analysis Log\n"]
        lines.append(f"**Workflow:** {steps[0].get('question', 'N/A')}\n\n")
        lines.append("### Execution Steps\n")
        lines.append("| Step | Name | Status | Duration (ms) |\n")
        lines.append("|------|------|--------|---------------|\n")
        
        for step in steps:
            step_num = step.get('step', 0)
            name = step.get('name', 'unknown')
            status = step.get('status', 'unknown')
            duration = step.get('duration_ms', 0)
            
            lines.append(f"| {step_num} | {name} | {status} | {duration:.2f} |\n")
        
        lines.append(f"\n**Total Duration:** {sum(s.get('duration_ms', 0) for s in steps):.2f} ms\n")
        
        # Add error details if any
        errors = [s for s in steps if s.get('status') == 'error']
        if errors:
            lines.append("\n### Errors\n")
            for error in errors:
                lines.append(f"- **Step {error.get('step')}: {error.get('name')}**: {error.get('result', {}).get('error', 'Unknown error')}\n")
        
        return '\n'.join(lines)
    
    def _get_tool_execution_summary(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get a summary of tool executions."""
        summary = {
            'total_steps': len(steps),
            'success_count': 0,
            'error_count': 0,
            'skipped_count': 0,
            'total_duration_ms': 0
        }
        
        for step in steps:
            status = step.get('status', '')
            duration = step.get('duration_ms', 0)
            
            summary['total_duration_ms'] += duration
            
            if status == 'success':
                summary['success_count'] += 1
            elif status == 'error':
                summary['error_count'] += 1
            elif status == 'skipped':
                summary['skipped_count'] += 1
        
        return summary
    
    def _get_performance_metrics(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get performance metrics from workflow steps."""
        durations = [s.get('duration_ms', 0) for s in steps if s.get('duration_ms', 0) > 0]
        
        if not durations:
            return {
                'average_duration_ms': 0,
                'min_duration_ms': 0,
                'max_duration_ms': 0,
                'total_duration_ms': 0
            }
        
        return {
            'average_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations),
            'total_duration_ms': sum(durations)
        }
    
    def execute_comparison_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a comparison analysis workflow for multi-scenario analysis."""
        logger.info("Executing comparison workflow")
        start_time = datetime.now()
        
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'workflow': 'compare_analysis',
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'start_time': start_time.isoformat(),
            'steps': [],
            'comparisons': []
        }
        
        try:
            # Extract comparison scenarios from question
            scenarios = self._extract_comparison_scenarios(question)
            
            comparison_data = []
            if self.data_fetcher:
                for scenario in scenarios:
                    scenario_data = self.data_fetcher.fetch_population_data(
                        question=question,
                        parameters=scenario,
                        audience=audience,
                        document_type=document_type
                    )
                    if scenario_data.get('status') == 'success':
                        comparison_data.append({
                            'scenario': scenario,
                            'data': scenario_data.get('data', {})
                        })
            
            # Generate comparison story
            if self.story_generator:
                comparison_story = self.story_generator.generate_comparison_story(
                    scenarios=scenarios,
                    data_list=[d.get('data', {}) for d in comparison_data],
                    question=question,
                    audience=audience,
                    document_type=document_type
                )
            else:
                comparison_story = {'status': 'error', 'error': 'Story generator not available'}
            
            # Audience adaptation
            if self.audience_adapter and comparison_story.get('status') == 'success':
                adapted_story = self.audience_adapter.adapt_story(
                    story=comparison_story.get('story', ''),
                    audience=audience,
                    document_type=document_type,
                    question=question
                )
            else:
                adapted_story = comparison_story
            
            result.update({
                'status': 'success',
                'end_time': datetime.now().isoformat(),
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'completed_steps': 3,
                'total_steps': 3,
                'comparisons': comparison_data,
                'story': comparison_story.get('story', ''),
                'adapted_story': adapted_story.get('adapted_story', comparison_story.get('story', '')),
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Comparison workflow failed: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            return result
    
    def execute_enhanced_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        use_rag: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute an enhanced analysis workflow with full pipeline."""
        logger.info("Executing enhanced workflow")
        start_time = datetime.now()
        
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        config = AudienceConfigManager.get_config(audience, document_type)
        
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'workflow': 'enhanced_analysis',
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'start_time': start_time.isoformat(),
            'steps': []
        }
        
        try:
            # Tool selection
            parameters = {}
            if self.tool_selector:
                tool_selection = self.tool_selector.select_tools(
                    question=question,
                    audience=audience,
                    document_type=document_type
                )
                parameters = tool_selection.get('selection', {}).get('parameters', {})
            
            # Data retrieval
            data_result = self.data_fetcher.fetch_population_data(
                question=question,
                parameters=parameters,
                audience=audience,
                document_type=document_type
            )
            
            # Enhanced analysis pipeline
            enhanced_result = self._execute_analysis_pipeline(
                data=data_result.get('data', {}),
                question=question,
                audience=audience,
                document_type=document_type
            )
            
            # Story generation with RAG
            enriched_data = {
                **data_result.get('data', {}),
                'statistics': enhanced_result.get('statistical_analysis', {}).get('result', {}).get('analysis'),
                'guardrails': enhanced_result.get('guardrails_validation', {}).get('result'),
                'visualization': enhanced_result.get('visualization_extraction', {}).get('result')
            }
            
            story_result = self.story_generator.generate_story(
                data=enriched_data,
                question=question,
                audience=audience,
                document_type=document_type,
                use_rag=use_rag and CrewAIConfig.RAG_ENABLED,
                analysis_config=config
            )
            
            # Audience adaptation
            if self.audience_adapter:
                adapted_story = self.audience_adapter.adapt_story(
                    story=story_result.get('story', ''),
                    audience=audience,
                    document_type=document_type,
                    question=question
                )
            else:
                adapted_story = story_result
            
            result.update({
                'status': 'success',
                'end_time': datetime.now().isoformat(),
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'completed_steps': 4,
                'total_steps': 4,
                'data': data_result.get('data', {}),
                'analysis': enhanced_result.get('statistical_analysis', {}).get('result', {}).get('analysis'),
                'validation': enhanced_result.get('guardrails_validation', {}).get('result'),
                'visualization': enhanced_result.get('visualization_extraction', {}).get('result'),
                'story': story_result.get('story', ''),
                'adapted_story': adapted_story.get('adapted_story', story_result.get('story', '')),
                'compliance_score': enhanced_result.get('guardrails_validation', {}).get('result', {}).get('compliance_score', 0),
                'rag_used': use_rag and CrewAIConfig.RAG_ENABLED
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Enhanced workflow failed: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            return result
    
    def execute_conditional_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        **kwargs
    ) -> Dict[str, Any]:
        """Execute a conditional analysis workflow based on question type."""
        logger.info("Executing conditional workflow")
        start_time = datetime.now()
        
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        config = AudienceConfigManager.get_config(audience, document_type)
        
        result: Dict[str, Any] = {
            'status': 'in_progress',
            'workflow': 'conditional_analysis',
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'start_time': start_time.isoformat(),
            'steps': []
        }
        
        try:
            # Analyze question type and execute appropriate path
            question_type = self._analyze_question_type(question)
            
            path_result = self._execute_question_path(
                question=question,
                question_type=question_type,
                audience=audience,
                document_type=document_type,
                **kwargs
            )
            
            # Story generation
            data = path_result.get('data', {})
            story_result = self.story_generator.generate_story(
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                use_rag=kwargs.get('use_rag', False) and CrewAIConfig.RAG_ENABLED,
                analysis_config=config
            )
            
            # Audience adaptation
            if self.audience_adapter:
                adapted_story = self.audience_adapter.adapt_story(
                    story=story_result.get('story', ''),
                    audience=audience,
                    document_type=document_type,
                    question=question
                )
            else:
                adapted_story = story_result
            
            result.update({
                'status': 'success',
                'end_time': datetime.now().isoformat(),
                'duration_ms': (datetime.now() - start_time).total_seconds() * 1000,
                'completed_steps': 3,
                'total_steps': 3,
                'data': data,
                'story': story_result.get('story', ''),
                'adapted_story': adapted_story.get('adapted_story', story_result.get('story', '')),
                'question_type': question_type,
                'path_result': path_result
            })
            
            return result
            
        except Exception as e:
            logger.error(f"Conditional workflow failed: {e}")
            result['status'] = 'error'
            result['error'] = str(e)
            result['end_time'] = datetime.now().isoformat()
            return result
    
    def _analyze_question_type(self, question: str) -> str:
        """Analyze the type of question being asked."""
        question_lower = question.lower()
        
        if any(word in question_lower for word in ['compare', 'comparison', 'vs', 'versus']):
            return 'comparison'
        elif any(word in question_lower for word in ['trend', 'over time', 'change']):
            return 'trend'
        elif any(word in question_lower for word in ['demographic', 'age', 'gender', 'sex']):
            return 'demographic'
        elif any(word in question_lower for word in ['solution', 'return', 'resettlement']):
            return 'solutions'
        elif any(word in question_lower for word in ['rsd', 'asylum', 'status']):
            return 'rsd'
        else:
            return 'standard'
    
    def _execute_question_path(
        self,
        question: str,
        question_type: str,
        audience: str,
        document_type: str,
        **kwargs
    ) -> Dict[str, Any]:
        """Execute the appropriate analysis path based on question type."""
        # Simplified implementation
        if question_type in ['comparison', 'trend', 'demographic', 'solutions', 'rsd']:
            return self.data_fetcher.fetch_population_data(
                question=question,
                parameters={},
                audience=audience,
                document_type=document_type
            )
        else:
            return self.data_fetcher.fetch_population_data(
                question=question,
                parameters={},
                audience=audience,
                document_type=document_type
            )
    
    def _extract_comparison_scenarios(self, question: str) -> List[Dict[str, Any]]:
        """Extract comparison scenarios from a question."""
        scenarios = []
        question_lower = question.lower()
        
        if ' vs ' in question_lower or ' versus ' in question_lower:
            parts = question_lower.split(' vs ') if ' vs ' in question_lower else question_lower.split(' versus ')
            for part in parts:
                scenarios.append({'coo': part.strip(), 'coa': None, 'year': None})
        elif ' compare ' in question_lower:
            compare_idx = question_lower.find(' compare ')
            if compare_idx > 0:
                entities = question_lower[compare_idx + 9:].split(' and ')
                for entity in entities:
                    scenarios.append({'coo': entity.strip(), 'coa': None, 'year': None})
        
        if not scenarios:
            scenarios.append({})
        
        return scenarios
    
    def _execute_analysis_pipeline(
        self,
        data: Dict[str, Any],
        question: str,
        audience: str,
        document_type: str
    ) -> Dict[str, Any]:
        """Execute the complete analysis pipeline."""
        pipeline_result = {}
        
        # Statistical analysis
        if self.statistical_analyzer:
            data_items = data.get('items', [])
            if isinstance(data_items, dict):
                data_items = list(data_items.values()) if isinstance(data_items, dict) else []
            
            analysis_result = self.statistical_analyzer.analyze_data(
                data=data_items,
                audience=audience,
                document_type=document_type
            )
            pipeline_result['statistical_analysis'] = {
                'result': analysis_result,
                'status': analysis_result.get('status', 'skipped')
            }
        
        # Guardrails validation
        if self.guardrails_validator:
            validation_result = self.guardrails_validator.validate_analysis(
                analysis_request={'context': question, 'data_fields': list(data.get('items', {}).keys()) if isinstance(data.get('items'), dict) else []},
                data=data,
                audience=audience,
                document_type=document_type
            )
            pipeline_result['guardrails_validation'] = {
                'result': validation_result,
                'status': validation_result.get('status', 'skipped')
            }
        
        # Visualization extraction
        if self.visualization_expert:
            viz_result = self.visualization_expert.extract_visualization(
                data=data,
                audience=audience,
                document_type=document_type
            )
            pipeline_result['visualization_extraction'] = {
                'result': viz_result,
                'status': viz_result.get('status', 'skipped')
            }
        
        return pipeline_result


class NotebookGenerator(UNHCRBaseAgent):
    """
    Specialist agent for generating Quarto notebooks.
    
    This agent creates well-documented Quarto notebooks from analysis results.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Notebook Generator agent."""
        kwargs.setdefault('role', 'Notebook Generator')
        kwargs.setdefault('goal', 'Create well-documented Quarto notebooks')
        
        super().__init__(**kwargs)
        
        # Initialize Jinja2 environment
        self._init_jinja2()
        
        # Initialize agent references
        self.analysis_orchestrator = None
        self.story_generator = None
        self.audience_adapter = None
    
    def set_agents(
        self,
        analysis_orchestrator: Any = None,
        story_generator: Any = None,
        audience_adapter: Any = None
    ):
        """Set references to other agents for notebook generation."""
        self.analysis_orchestrator = analysis_orchestrator
        self.story_generator = story_generator
        self.audience_adapter = audience_adapter
        logger.info("NotebookGenerator: Agent references set")
    
    def _init_jinja2(self):
        """Initialize Jinja2 environment."""
        try:
            template_dir = os.path.join(
                os.path.dirname(os.path.dirname(os.path.dirname(__file__))),
                'templates'
            )
            
            if os.path.exists(template_dir):
                self.jinja_env = jinja2.Environment(
                    loader=jinja2.FileSystemLoader(template_dir),
                    autoescape=True
                )
            else:
                self.jinja_env = jinja2.Environment(autoescape=True)
                
        except Exception as e:
            logger.error(f"Error initializing Jinja2 for NotebookGenerator: {e}")
            self.jinja_env = jinja2.Environment(autoescape=True)
    
    def generate_notebook(
        self,
        story_content: str,
        data: Dict[str, Any],
        question: str,
        audience: str,
        document_type: str,
        analysis_log: List[Dict[str, Any]] = None,
        metadata: Dict[str, Any] = None
    ) -> Dict[str, Any]:
        """
        Generate a Quarto notebook from analysis results.
        
        Args:
            story_content: The generated story/narrative
            data: The analysis data
            question: Original user question
            audience: Target audience
            document_type: Document type
            analysis_log: Workflow execution log
            metadata: Additional metadata
            
        Returns:
            Quarto notebook content with metadata
        """
        # Validate inputs
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        try:
            # Select template
            template_name = self._select_template(document_type)
            template = self.jinja_env.get_template(template_name)
            
            # Prepare context
            context = self._prepare_context(
                story_content=story_content,
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                analysis_log=analysis_log,
                metadata=metadata or {}
            )
            
            # Render template
            notebook_content = template.render(**context)
            
            # Generate observability data
            observability = self._generate_observability_data(
                story_content=story_content,
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                analysis_log=analysis_log
            )
            
            return {
                'status': 'success',
                'notebook': notebook_content,
                'template': template_name,
                'metadata': {
                    **observability,
                    'audience': audience,
                    'document_type': document_type,
                    'question': question,
                    'generated_at': datetime.now().isoformat()
                }
            }
            
        except Exception as e:
            logger.error(f"Failed to generate notebook: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'template': None,
                'metadata': {
                    'audience': audience,
                    'document_type': document_type
                }
            }
    
    def _select_template(self, document_type: str) -> str:
        """Select the appropriate Jinja2 template."""
        template_map = {
            'technical_report': 'technical_report.j2',
            'executive_summary': 'executive_summary.j2',
            'long_read': 'long_read.j2',
            'social_media': 'social_media.j2',
            'linkedin_post': 'linkedin_post.j2'
        }
        return template_map.get(document_type, 'base_quarto.j2')
    
    def _prepare_context(self, **kwargs) -> Dict[str, Any]:
        """Prepare context for template rendering."""
        context = {}
        
        for key, value in kwargs.items():
            if isinstance(value, dict):
                context[key] = self._convert_dict(value)
            elif isinstance(value, list):
                context[key] = self._convert_list(value)
            else:
                context[key] = value
        
        # Add default context
        context.update({
            'generated_at': datetime.now().isoformat(),
            'version': '1.0.0',
            'source': 'UNHCR Statistics Copilot - CrewAI'
        })
        
        return context
    
    def _convert_dict(self, d: Dict[str, Any]) -> Dict[str, Any]:
        """Convert dictionary to template-friendly format."""
        return {k: self._convert_value(v) for k, v in d.items()}
    
    def _convert_list(self, lst: List[Any]) -> List[Any]:
        """Convert list to template-friendly format."""
        return [self._convert_value(v) for v in lst]
    
    def _convert_value(self, value: Any) -> Any:
        """Convert a value to template-friendly format."""
        if isinstance(value, dict):
            return self._convert_dict(value)
        elif isinstance(value, list):
            return self._convert_list(value)
        elif isinstance(value, datetime):
            return value.isoformat()
        else:
            return value
    
    def _generate_observability_data(self, **kwargs) -> Dict[str, Any]:
        """Generate observability data for the notebook."""
        analysis_log = kwargs.get('analysis_log', [])
        data = kwargs.get('data', {})
        
        # Generate analysis log markdown
        log_markdown = self._generate_analysis_log_markdown(analysis_log)
        
        # Generate data summary
        data_summary = self._generate_data_summary(data)
        
        return {
            'analysis_log': log_markdown,
            'data_summary': data_summary,
            'tool_execution_summary': self._get_tool_execution_summary(analysis_log),
            'performance_metrics': self._get_performance_metrics(analysis_log)
        }
    
    def _generate_analysis_log_markdown(self, steps: List[Dict[str, Any]]) -> str:
        """Generate a markdown analysis log from workflow steps."""
        if not steps:
            return "No analysis log available"
        
        lines = ["## Analysis Log\n"]
        lines.append(f"**Question:** {steps[0].get('question', 'N/A')}\n\n")
        lines.append("### Execution Steps\n")
        lines.append("| Step | Name | Status | Duration (ms) |\n")
        lines.append("|------|------|--------|---------------|\n")
        
        for step in steps:
            step_num = step.get('step', 0)
            name = step.get('name', 'unknown')
            status = step.get('status', 'unknown')
            duration = step.get('duration_ms', 0)
            
            lines.append(f"| {step_num} | {name} | {status} | {duration:.2f} |\n")
        
        lines.append(f"\n**Total Duration:** {sum(s.get('duration_ms', 0) for s in steps):.2f} ms\n")
        
        return '\n'.join(lines)
    
    def _generate_data_summary(self, data: Dict[str, Any]) -> str:
        """Generate a markdown data summary."""
        lines = ["## Data Summary\n\n"]
        
        if not data:
            lines.append("No data available\n")
            return '\n'.join(lines)
        
        # Add basic info
        if 'data_type' in data:
            lines.append(f"**Data Type:** {data['data_type']}\n\n")
        
        # Count items
        items = data.get('items', [])
        if isinstance(items, dict):
            lines.append(f"**Data Items:** {len(items)}\n\n")
        elif isinstance(items, list):
            lines.append(f"**Data Items:** {len(items)}\n\n")
        
        # Add field information
        if items and len(items) > 0:
            if isinstance(items, list) and isinstance(items[0], dict):
                lines.append("**Fields:**\n\n")
                for key in items[0].keys():
                    lines.append(f"- {key}\n")
                lines.append("\n")
            elif isinstance(items, dict):
                lines.append("**Fields:**\n\n")
                for key in items.keys():
                    lines.append(f"- {key}\n")
                lines.append("\n")
        
        return '\n'.join(lines)
    
    def _get_tool_execution_summary(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get a summary of tool executions."""
        summary = {
            'total_steps': len(steps),
            'success_count': 0,
            'error_count': 0,
            'skipped_count': 0
        }
        
        for step in steps:
            status = step.get('status', '')
            if status == 'success':
                summary['success_count'] += 1
            elif status == 'error':
                summary['error_count'] += 1
            elif status == 'skipped':
                summary['skipped_count'] += 1
        
        return summary
    
    def _get_performance_metrics(self, steps: List[Dict[str, Any]]) -> Dict[str, Any]:
        """Get performance metrics from workflow steps."""
        durations = [s.get('duration_ms', 0) for s in steps if s.get('duration_ms', 0) > 0]
        
        if not durations:
            return {
                'average_duration_ms': 0,
                'min_duration_ms': 0,
                'max_duration_ms': 0
            }
        
        return {
            'average_duration_ms': sum(durations) / len(durations),
            'min_duration_ms': min(durations),
            'max_duration_ms': max(durations)
        }
