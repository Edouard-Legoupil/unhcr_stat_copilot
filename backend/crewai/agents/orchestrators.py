"""
Simplified Orchestration Agents for UNHCR Statistics Copilot

This is a streamlined version that minimizes token consumption and complexity
while maintaining the expected workflow: data fetching → story generation → notebook creation.
"""

import logging
from datetime import datetime
from typing import Any, Dict, List, Optional
import jinja2
import os
import json

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.config import CrewAIConfig, AudienceConfigManager

logger = logging.getLogger(__name__)


class AnalysisOrchestrator(UNHCRBaseAgent):
    """
    Simplified master agent that coordinates the analysis workflow.
    
    This streamlined version minimizes steps and token consumption by:
    1. Fetching data directly via MCP tools (no intermediate agents)
    2. Generating story via MCP tools
    3. Creating notebook via MCP tools
    
    This avoids the complexity of coordinating multiple agents and
    the associated token overhead.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Analysis Orchestrator agent."""
        kwargs.setdefault('role', 'Analysis Orchestrator')
        kwargs.setdefault('goal', 'Deliver end-to-end analysis from question to Quarto notebook')
        
        super().__init__(**kwargs)
        
        # Initialize Jinja2 environment for notebook generation
        self._init_jinja2()
        
        # Track metrics
        self.metrics = {
            'total_workflows': 0,
            'successful_workflows': 0,
            'failed_workflows': 0,
            'total_tokens': 0
        }
    
    def _init_jinja2(self):
        """Initialize Jinja2 environment for template rendering."""
        template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
        if os.path.exists(template_dir):
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = jinja2.Environment(autoescape=False)
            logger.warning(f"Template directory not found: {template_dir}")
    
    async def execute_full_workflow(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        use_rag: bool = True,
        include_notebook: bool = True,
        **kwargs
    ) -> Dict[str, Any]:
        """
        Execute the complete simplified analysis workflow.
        
        Simplified steps:
        1. Extract parameters from question
        2. Fetch data using MCP tools
        3. Generate analytical story using MCP tools  
        4. Create Quarto notebook using MCP tools
        
        This minimizes token consumption by avoiding intermediate agent coordination
        and using direct MCP tool calls.
        """
        start_time = datetime.now()
        workflow_steps = []
        
        # Validate inputs
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        result = {
            'status': 'in_progress',
            'question': question,
            'audience': audience,
            'document_type': document_type,
            'workflow': 'full_analysis',
            'start_time': start_time.isoformat(),
            'steps': [],
            'errors': [],
            'notebook': None,
            'story': None,
            'data': None
        }
        
        try:
            # Step 1: Extract parameters from question
            logger.info("Step 1/3: Extracting parameters from question")
            step_start = datetime.now()
            
            from backend.question_parser import extract_question_parameters
            parameters = await extract_question_parameters(question)
            
            workflow_steps.append({
                'step': 1,
                'name': 'parameter_extraction',
                'status': 'success',
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': parameters
            })
            
            # Step 2: Fetch data using MCP tools directly
            logger.info("Step 2/3: Fetching data")
            step_start = datetime.now()
            
            data_result = await self._fetch_data(
                question=question,
                parameters=parameters,
                audience=audience,
                document_type=document_type
            )
            
            workflow_steps.append({
                'step': 2,
                'name': 'data_fetching',
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
                result['total_steps'] = 3
                logger.error(f"Data retrieval failed: {result['error']}")
                return result
            
            # Store data for later use
            result['data'] = data_result.get('data', {})
            
            # Step 3: Generate story and notebook
            logger.info("Step 3/3: Generating story and notebook")
            step_start = datetime.now()
            
            notebook_result = await self._generate_notebook(
                question=question,
                data=data_result,
                parameters=parameters,
                audience=audience,
                document_type=document_type,
                use_rag=use_rag
            )
            
            workflow_steps.append({
                'step': 3,
                'name': 'notebook_generation',
                'status': notebook_result.get('status', 'error'),
                'duration_ms': (datetime.now() - step_start).total_seconds() * 1000,
                'result': notebook_result
            })
            
            # Update result with notebook
            if notebook_result.get('status') == 'success':
                result['notebook'] = notebook_result.get('notebook', {})
                result['story'] = notebook_result.get('story', '')
                result['status'] = 'success'
            else:
                result['status'] = 'partial'
                result['error'] = notebook_result.get('error', 'Notebook generation failed')
            
            # Complete workflow
            result['steps'] = workflow_steps
            result['completed_steps'] = 3
            result['total_steps'] = 3
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            
            # Update metrics
            self.metrics['total_workflows'] += 1
            if result['status'] == 'success':
                self.metrics['successful_workflows'] += 1
            else:
                self.metrics['failed_workflows'] += 1
            
            logger.info(f"Workflow completed in {(datetime.now() - start_time).total_seconds():.2f}s")
            
            return result
            
        except Exception as e:
            logger.exception(f"Workflow failed: {e}")
            
            result['status'] = 'error'
            result['error'] = str(e)
            result['steps'] = workflow_steps
            result['completed_steps'] = len(workflow_steps)
            result['total_steps'] = 3
            result['end_time'] = datetime.now().isoformat()
            result['duration_seconds'] = (datetime.now() - start_time).total_seconds()
            
            self.metrics['total_workflows'] += 1
            self.metrics['failed_workflows'] += 1
            
            logger.error(f"Full analysis workflow failed: {e}")
            return result
    
    async def _fetch_data(self, question: str, parameters: Dict[str, Any], audience: str, document_type: str) -> Dict[str, Any]:
        """Fetch data using MCP tools directly."""
        try:
            from backend.mcp_bridge import call_tool
            
            origin = parameters.get('origin', parameters.get('coo', ''))
            destination = parameters.get('destination', parameters.get('coa', ''))
            topic = parameters.get('topic', '')
            timespan = parameters.get('timespan', '')
            population_type = parameters.get('population_type', '')
            
            # Prepare parameters for get_data_for_story
            # Handle timespan as years if provided
            call_params = {
                'question': question,
                'coo_all': False,
                'coa_all': False,
                'audience': audience,
                'document_type': document_type
            }
            
            # Only add parameters if they are not None and not empty
            if topic:
                call_params['topic'] = topic
            if timespan:
                call_params['timespan'] = timespan
                call_params['years'] = timespan
            if origin:
                call_params['origin'] = origin
            if destination:
                call_params['destination'] = destination
            if population_type:
                call_params['population_type'] = population_type
            
            result = await call_tool('get_data_for_story', call_params)
            
            if not isinstance(result, dict):
                result = {'status': 'error', 'error': f'Unexpected result type: {type(result)}'}
            
            result.setdefault('status', 'success')
            return result
            
        except Exception as e:
            logger.exception(f"Data fetching failed: {e}")
            return {'status': 'error', 'error': str(e), 'data': {}}
    
    async def _generate_notebook(self, question: str, data: Dict[str, Any], parameters: Dict[str, Any], audience: str, document_type: str, use_rag: bool = True) -> Dict[str, Any]:
        """Generate story and Quarto notebook using MCP tools directly."""
        try:
            from backend.mcp_bridge import call_tool
            
            # Generate analytical story
            story_result = await call_tool(
                'generate_analytical_story',
                {
                    'data': data,
                    'question': question,
                    'audience': audience,
                    'document_type': document_type,
                    'use_rag': use_rag,
                    'apply_guardrails': True
                }
            )
            
            if not isinstance(story_result, dict):
                story_result = {'status': 'error', 'error': f'Unexpected story result type: {type(story_result)}'}
            
            story_content = story_result.get('story', '') or story_result.get('response', '')
            
            # Ensure story_content is always a string (LLM responses may return lists or message objects)
            if not isinstance(story_content, str):
                if isinstance(story_content, list):
                    story_content = '\n'.join(str(item) for item in story_content)
                elif isinstance(story_content, dict):
                    # Handle Azure OpenAI message object format
                    # Message object: {'id': '...', 'type': 'message', 'content': [{'type': 'output_text', 'text': '...'}], ...}
                    if 'content' in story_content and isinstance(story_content['content'], list):
                        # Extract text from content array
                        text_parts = []
                        for item in story_content['content']:
                            if isinstance(item, dict) and 'text' in item:
                                text_parts.append(item['text'])
                            elif isinstance(item, str):
                                text_parts.append(item)
                        story_content = '\n'.join(text_parts) if text_parts else json.dumps(story_content)
                    elif 'text' in story_content:
                        story_content = story_content['text']
                    elif 'content' in story_content:
                        story_content = str(story_content['content'])
                    else:
                        # Last resort: convert to JSON string for proper parsing downstream
                        import json
                        story_content = json.dumps(story_content)
                else:
                    story_content = str(story_content)
            
            # Log for debugging
            logger.info(f"Orchestrator: story_content type={type(story_content)}, length={len(story_content) if isinstance(story_content, str) else 'N/A'}")
            
            # Create Quarto notebook
            notebook_result = await call_tool(
                'create_quarto_notebook',
                {
                    'story_content': story_content,
                    'data': data,
                    'question': question,
                    'audience': audience,
                    'document_type': document_type,
                    'origin': parameters.get('origin', ''),
                    'destination': parameters.get('destination', ''),
                    'topic': parameters.get('topic', ''),
                    'timespan': parameters.get('timespan', '')
                }
            )
            
            if not isinstance(notebook_result, dict):
                notebook_result = {'status': 'error', 'error': f'Unexpected notebook result type: {type(notebook_result)}'}
            
            return {
                'status': 'success',
                'story': story_content,
                'notebook': {
                    'content': notebook_result.get('content', ''),
                    'metadata': notebook_result.get('metadata', {})
                }
            }
            
        except Exception as e:
            logger.exception(f"Notebook generation failed: {e}")
            return {'status': 'error', 'error': str(e), 'story': '', 'notebook': {'content': '', 'metadata': {}}}
    
    async def execute_enhanced_workflow(self, question: str, audience: str = "internal", document_type: str = "technical_report", use_rag: bool = True, **kwargs) -> Dict[str, Any]:
        """Execute enhanced workflow - for now just calls full workflow."""
        return await self.execute_full_workflow(question, audience, document_type, use_rag, **kwargs)
    
    def set_agent_references(self, **agents):
        """Set references to other agents (for compatibility with manager)."""
        for key, value in agents.items():
            if hasattr(self, key):
                setattr(self, key, value)


class NotebookGenerator(UNHCRBaseAgent):
    """Agent for generating Quarto notebooks."""
    
    def __init__(self, **kwargs):
        kwargs.setdefault('role', 'Notebook Generator')
        kwargs.setdefault('goal', 'Generate well-documented Quarto notebooks from analysis results')
        super().__init__(**kwargs)
        
        template_dir = os.path.join(os.path.dirname(__file__), '..', '..', 'templates')
        if os.path.exists(template_dir):
            self.jinja_env = jinja2.Environment(
                loader=jinja2.FileSystemLoader(template_dir),
                autoescape=jinja2.select_autoescape(['html', 'xml'])
            )
        else:
            self.jinja_env = jinja2.Environment(autoescape=False)
            logger.warning(f"Template directory not found: {template_dir}")
    
    async def create_notebook(self, story_content: str, data: Dict[str, Any], **kwargs) -> Dict[str, Any]:
        """Create a Quarto notebook from story content."""
        try:
            from backend.mcp_bridge import call_tool
            # Ensure story_content is a string
            if not isinstance(story_content, str):
                if isinstance(story_content, list):
                    story_content = '\n'.join(str(item) for item in story_content)
                elif isinstance(story_content, dict):
                    # Handle Azure OpenAI message object format
                    if 'content' in story_content and isinstance(story_content['content'], list):
                        text_parts = []
                        for item in story_content['content']:
                            if isinstance(item, dict) and 'text' in item:
                                text_parts.append(item['text'])
                            elif isinstance(item, str):
                                text_parts.append(item)
                        story_content = '\n'.join(text_parts) if text_parts else json.dumps(story_content)
                    elif 'text' in story_content:
                        story_content = story_content['text']
                    elif 'content' in story_content:
                        story_content = str(story_content['content'])
                    else:
                        # Last resort: convert to JSON string for proper parsing downstream
                        story_content = json.dumps(story_content)
                else:
                    story_content = str(story_content)
            result = await call_tool('create_quarto_notebook', {'story_content': story_content, 'data': data, **kwargs})
            
            if not isinstance(result, dict):
                result = {'status': 'error', 'error': f'Unexpected result type: {type(result)}'}
            
            return {
                'status': 'success',
                'quarto_content': result.get('content', ''),
                'metadata': result.get('metadata', {})
            }
        except Exception as e:
            logger.exception(f"Notebook creation failed: {e}")
            return {'status': 'error', 'error': str(e), 'quarto_content': '', 'metadata': {}}
