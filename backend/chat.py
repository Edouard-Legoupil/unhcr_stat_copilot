"""
Chat Processing Module for UNHCR Statistics Copilot

This module provides chat message processing using MCP-based workflow.
The dual-run (MCP vs CrewAI) processor switching has been removed.
All processing now uses the MCP workflow directly.

Usage:
    from backend.chat import process_chat_message
    
    result = await process_chat_message(
        message="Show me refugee trends",
        audience="policy_makers"
    )
"""

import logging
from typing import Optional, Any, Dict

from backend.mcp_bridge import call_tool
from backend.models.analysis_config import AnalysisConfigModel
from enum import Enum

logger = logging.getLogger(__name__)


# =============================================================================
# Analysis Configuration
# =============================================================================

ANALYSIS_CONFIG = {
    "internal": {
        "defaultType": "technical_report",
        "documentTypes": {
            "technical_report": {
                "tone": "formal, precise, objective",
                "length": {
                    "wordRange": "2000-5000",
                    "readingTime": "10-25 min",
                    "density": "high"
                },
                "structure": [
                    "objective",
                    "methodology",
                    "data analysis",
                    "results",
                    "limitations",
                    "annex (optional)"
                ]
            },
            "long_read": {
                "tone": "analytical, narrative, engaging",
                "length": {
                    "wordRange": "1200-3000",
                    "readingTime": "6-15 min",
                    "density": "medium-high"
                },
                "structure": [
                    "introduction",
                    "context",
                    "key findings",
                    "deep dive analysis",
                    "implications",
                    "conclusion"
                ]
            },
            "executive_summary": {
                "tone": "concise, strategic, actionable",
                "length": {
                    "wordRange": "300-800",
                    "readingTime": "2-4 min",
                    "density": "high"
                },
                "structure": [
                    "key messages",
                    "main findings",
                    "implications",
                    "recommended actions"
                ]
            }
        }
    },
    "public_donors": {
        "defaultType": "executive_summary",
        "documentTypes": {
            "executive_summary": {
                "tone": "clear, impactful, accessible",
                "length": {
                    "wordRange": "300-700",
                    "readingTime": "2-3 min",
                    "density": "medium"
                },
                "structure": [
                    "headline insight",
                    "key statistics",
                    "impact highlights",
                    "call to action"
                ]
            },
            "long_read": {
                "tone": "engaging, narrative, transparent",
                "length": {
                    "wordRange": "800-2000",
                    "readingTime": "4-10 min",
                    "density": "medium"
                },
                "structure": [
                    "introduction",
                    "context",
                    "key findings",
                    "stories or examples",
                    "visualizations",
                    "call to action"
                ]
            },
            "social_media": {
                "tone": "engaging, punchy, shareable",
                "length": {
                    "wordRange": "50-200",
                    "readingTime": "30 sec - 1 min",
                    "density": "low"
                },
                "structure": [
                    "hook",
                    "key fact",
                    "visual",
                    "call to action"
                ]
            },
            "linkedin_post": {
                "tone": "professional, networked, insightful",
                "length": {
                    "wordRange": "100-300",
                    "readingTime": "1-2 min",
                    "density": "medium-low"
                },
                "structure": [
                    "attention grabber",
                    "insight",
                    "relevance",
                    "engagement question"
                ]
            }
        }
    },
    "private_donors": {
        "defaultType": "long_read",
        "documentTypes": {
            "technical_report": {
                "tone": "detailed, data-driven, persuasive",
                "length": {
                    "wordRange": "3000-6000",
                    "readingTime": "15-30 min",
                    "density": "high"
                },
                "structure": [
                    "executive summary",
                    "problem statement",
                    "methodology",
                    "detailed findings",
                    "investment opportunities",
                    "ROI analysis",
                    "appendices"
                ]
            },
            "long_read": {
                "tone": "compelling, values-aligned, visionary",
                "length": {
                    "wordRange": "1500-3500",
                    "readingTime": "8-18 min",
                    "density": "medium"
                },
                "structure": [
                    "human story",
                    "the challenge",
                    "our approach",
                    "impact achieved",
                    "why invest",
                    "testimonials"
                ]
            },
            "executive_summary": {
                "tone": "high-impact, ROI-focused, strategic",
                "length": {
                    "wordRange": "500-1000",
                    "readingTime": "3-5 min",
                    "density": "medium-high"
                },
                "structure": [
                    "investment thesis",
                    "key metrics",
                    "impact highlights",
                    "ask",
                    "expected returns"
                ]
            }
        }
    },
    "government": {
        "defaultType": "executive_summary",
        "documentTypes": {
            "policy_brief": {
                "tone": "authoritative, evidence-based, actionable",
                "length": {
                    "wordRange": "800-1500",
                    "readingTime": "4-8 min",
                    "density": "high"
                },
                "structure": [
                    "policy issue",
                    "current situation",
                    "data analysis",
                    "policy recommendations",
                    "implementation roadmap",
                    "references"
                ]
            },
            "executive_summary": {
                "tone": "diplomatic, concise, solution-oriented",
                "length": {
                    "wordRange": "400-800",
                    "readingTime": "2-4 min",
                    "density": "high"
                },
                "structure": [
                    "key findings",
                    "policy implications",
                    "recommendations",
                    "next steps"
                ]
            },
            "technical_report": {
                "tone": "comprehensive, detailed, rigorous",
                "length": {
                    "wordRange": "4000-8000",
                    "readingTime": "20-40 min",
                    "density": "very high"
                },
                "structure": [
                    "executive summary",
                    "introduction",
                    "methodology",
                    "detailed analysis",
                    "findings",
                    "conclusion",
                    "appendices"
                ]
            }
        }
    },
    "media": {
        "defaultType": "social_media",
        "documentTypes": {
            "press_release": {
                "tone": "newsworthy, factual, urgent",
                "length": {
                    "wordRange": "300-600",
                    "readingTime": "2-3 min",
                    "density": "medium"
                },
                "structure": [
                    "headline",
                    "dateline",
                    "lead paragraph",
                    "key facts",
                    "quotes",
                    "background",
                    "contact information"
                ]
            },
            "feature_article": {
                "tone": "human interest, narrative, compelling",
                "length": {
                    "wordRange": "1500-3000",
                    "readingTime": "8-15 min",
                    "density": "medium"
                },
                "structure": [
                    "lead",
                    "human story",
                    "the problem",
                    "the solution",
                    "the impact",
                    "call to action"
                ]
            },
            "social_media": {
                "tone": "engaging, shareable, visually appealing",
                "length": {
                    "wordRange": "50-200",
                    "readingTime": "30 sec - 1 min",
                    "density": "low"
                },
                "structure": [
                    "hook",
                    "visual",
                    "key message",
                    "hashtags",
                    "link"
                ]
            },
            "linkedin_post": {
                "tone": "thought leadership, professional, networked",
                "length": {
                    "wordRange": "100-300",
                    "readingTime": "1-2 min",
                    "density": "medium-low"
                },
                "structure": [
                    "attention grabber",
                    "insight",
                    "personal connection",
                    "engagement question"
                ]
            }
        }
    }
}

analysis_config_model = AnalysisConfigModel(config=ANALYSIS_CONFIG)
AudienceEnum = Enum(
    "AudienceEnum",
    {aud: aud for aud in ANALYSIS_CONFIG.keys()},
    type=str,
)

def get_available_document_types(audience: str = "internal") -> list:
    """Get available document types for a given audience."""
    return analysis_config_model.available_document_types(audience)


def get_default_document_type(audience: str = "internal") -> str:
    """Get the default document type for a given audience."""
    return analysis_config_model.default_document_type(audience)


def get_analysis_config(audience: str, document_type: str) -> dict:
    """Get the full analysis configuration for a given audience and document type."""
    return analysis_config_model.get_config(audience, document_type)


async def process_chat_message(
    message: str,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    topic: Optional[str] = None,
    timespan: Optional[str] = None,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    style: Optional[str] = None,
    use_enhanced: Optional[bool] = None,
    use_rag: Optional[bool] = None,
    include_notebook: Optional[bool] = True,
    output_path: Optional[str] = None,
    **kwargs
) -> dict:
    """
    Process a chat message using MCP workflow.
    
    This is the main entry point for chat message processing. It uses
    the MCP bridge to call tools directly.
    
    Args:
        message: The user's query or analysis request
        origin: Origin context for the analysis
        destination: Destination context
        topic: Specific topic to focus on
        timespan: Time period for the analysis
        audience: Target audience for the output
        document_type: Type of document to generate
        style: Writing style for the response
        use_enhanced: Whether to use enhanced analysis
        use_rag: Whether to use RAG enrichment
        include_notebook: Whether to generate a Quarto notebook
        output_path: Path to save the notebook
        **kwargs: Additional parameters
    
    Returns:
        Dictionary containing analysis results, including:
        - question: The original question
        - analysis_type: Type of analysis performed
        - story: Generated story content
        - notebook: Generated notebook content (if requested)
        - quarto_content: Notebook content
        - quarto_metadata: Notebook metadata
        - status: "success" or "error"
        - execution_source: "mcp" (indicating MCP workflow was used)
    """
    # Set defaults
    if audience is None:
        audience = "internal"
    if document_type is None:
        document_type = get_default_document_type(audience)
    if use_enhanced is None:
        use_enhanced = True
    if use_rag is None:
        use_rag = True
    if include_notebook is None:
        include_notebook = True
    
    # Get analysis config
    analysis_config = get_analysis_config(audience, document_type)
    
    result: Dict[str, Any] = {
        'status': 'in_progress',
        'question': message,
        'audience': audience,
        'document_type': document_type,
        'analysis_config': analysis_config,
        'origin': origin,
        'destination': destination,
        'topic': topic,
        'timespan': timespan,
        'style': style,
        'execution_source': 'mcp',
        'steps': [],
        'errors': []
    }
    
    try:
        # Step 1: Get data for the story
        logger.info(f"Step 1/3: Fetching data for question: {message}")
        
        data_params = {
            'question': message,
            'audience': audience,
            'document_type': document_type,
            'use_enhanced': use_enhanced,
            'use_rag': use_rag
        }
        
        # Add optional parameters if provided
        if origin:
            data_params['origin'] = origin
        if destination:
            data_params['destination'] = destination
        if topic:
            data_params['topic'] = topic
        if timespan:
            data_params['timespan'] = timespan
            data_params['years'] = timespan
        
        # Add any extra kwargs
        data_params.update(kwargs)
        
        data_result = await call_tool('get_data_for_story', data_params)
        
        if not isinstance(data_result, dict):
            data_result = {'status': 'error', 'error': f'Unexpected result type: {type(data_result)}'}
        
        result['steps'].append({
            'step': 1,
            'name': 'data_fetching',
            'tool': 'get_data_for_story',
            'params': data_params,
            'status': data_result.get('status', 'error'),
            'result': data_result
        })
        
        if data_result.get('status') != 'success':
            result['status'] = 'partial_success'
            result['warnings'] = ["Data fetching encountered errors"]
        
        all_data = data_result.get('data', {})
        
        # Step 2: Generate analytical story
        logger.info("Step 2/3: Generating analytical story")
        
        story_params = {
            'question': message,
            'data': all_data,
            'audience': audience,
            'document_type': document_type,
            'use_rag': use_rag,
            'analysis_config': analysis_config
        }
        
        if origin:
            story_params['origin'] = origin
        if destination:
            story_params['destination'] = destination
        if topic:
            story_params['topic'] = topic
        if timespan:
            story_params['timespan'] = timespan
        if style:
            story_params['style'] = style
        
        story_result = await call_tool('generate_analytical_story', story_params)
        
        if not isinstance(story_result, dict):
            story_result = {'status': 'error', 'error': f'Unexpected result type: {type(story_result)}'}
        
        # Override story_result to include cleaned text only
        story_content = story_result.get('story', '')
        if not isinstance(story_content, str):
            from backend.crewai.agents.orchestrators import _extract_text_from_message_impl
            story_content = _extract_text_from_message_impl(story_content)
        if isinstance(story_content, str) and story_content.strip().startswith(('{', '[')):
            try:
                import json
                parsed = json.loads(story_content)
                story_content = _extract_text_from_message_impl(parsed)
            except Exception:
                pass
        story_content = story_content.lstrip('\n').strip()
        story_result['story'] = story_content
        result['steps'].append({
            'step': 2,
            'name': 'story_generation',
            'tool': 'generate_analytical_story',
            'params': story_params,
            'status': story_result.get('status', 'error'),
            'result': story_result
        })
        if not isinstance(story_content, str):
            # Try to extract text from various message formats
            from backend.crewai.agents.orchestrators import _extract_text_from_message_impl
            story_content = _extract_text_from_message_impl(story_content)
        
        # If the story appears as JSON or dict-string, parse then extract text
        if isinstance(story_content, str) and story_content.strip().startswith(('{', '[')):
            try:
                import json
                parsed = json.loads(story_content)
                extracted = _extract_text_from_message_impl(parsed)
                if extracted:
                    story_content = extracted
            except Exception:
                pass
        # Strip leading newlines/spaces to avoid stray formatting
        result['story'] = story_content.lstrip('\n').strip()
        result['data'] = all_data
        result['extracted_params'] = data_result.get('extracted_params', {})
        result['analysis'] = story_result.get('analysis', {})
        
        if story_result.get('status') != 'success':
            result['status'] = 'partial_success'
            if 'warnings' not in result:
                result['warnings'] = []
            result['warnings'].append("Story generation encountered errors")
        
        # Step 3: Create Quarto notebook (if requested)
        if include_notebook:
            logger.info("Step 3/3: Creating Quarto notebook")
            notebook_params = {
                'story_content': story_content,
                'data': all_data,
                'question': message,
                'audience': audience,
                'document_type': document_type,
                'use_unhcr_theme': True,
                'use_unhcr_style': True,
                'include_code_cells': False
            }
            if origin:
                notebook_params['origin'] = origin
            if destination:
                notebook_params['destination'] = destination
            if topic:
                notebook_params['topic'] = topic
            if timespan:
                notebook_params['timespan'] = timespan
            if output_path:
                notebook_params['output_path'] = output_path
            if style:
                notebook_params['style'] = style

            notebook_result = await call_tool('create_quarto_notebook', notebook_params)
            if not isinstance(notebook_result, dict):
                notebook_result = {'status': 'error', 'error': f'Unexpected result type: {type(notebook_result)}'}

            result['steps'].append({
                'step': 3,
                'name': 'notebook_generation',
                'tool': 'create_quarto_notebook',
                'params': notebook_params,
                'status': notebook_result.get('status', 'error'),
                'result': notebook_result
            })
            if notebook_result.get('status') == 'success':
                result['notebook'] = notebook_result
                result['quarto_content'] = notebook_result.get('content', '')
                result['quarto_metadata'] = notebook_result.get('metadata', {})
            else:
                if result.get('status') != 'error':
                    result['status'] = 'partial_success'
                if 'warnings' not in result:
                    result['warnings'] = []
                result['warnings'].append("Notebook generation encountered errors")
        
        # Mark as completed and set analysis_type for saving Quarto notebooks
        if result['status'] == 'in_progress':
            result['status'] = 'success'
        # Use 'comprehensive_quarto' when notebook is included, else generic 'full'
        result['analysis_type'] = (
            'comprehensive_quarto' if include_notebook else 'full'
        )
        
    except Exception as e:
        logger.error(f"Error in chat processing: {e}")
        result['status'] = 'error'
        result['error'] = str(e)
        result['errors'].append(str(e))
    
    return result


async def run_tool_directly(tool_name: str, arguments: dict) -> dict:
    """
    Execute a tool directly via MCP bridge.
    
    Args:
        tool_name: Name of the MCP tool to call
        arguments: Dictionary of arguments for the tool
    
    Returns:
        Dictionary with tool execution results
    """
    try:
        result = await call_tool(tool_name, arguments)
        if not isinstance(result, dict):
            result = {'status': 'error', 'error': f'Unexpected result type: {type(result)}'}
        return result
    except Exception as e:
        logger.error(f"Error running tool {tool_name}: {e}")
        return {'status': 'error', 'error': str(e), 'tool': tool_name}


async def execute_full_workflow(
    question: str,
    audience: str = "internal",
    document_type: str = None,
    use_rag: bool = True,
    include_notebook: bool = True,
    output_path: str = None,
    **kwargs
) -> dict:
    """
    Execute the complete analysis workflow.
    
    This is a convenience wrapper around process_chat_message for
    executing full end-to-end analysis workflows.
    
    Args:
        question: The analysis question
        audience: Target audience for the output
        document_type: Type of document to generate
        use_rag: Whether to use RAG enrichment
        include_notebook: Whether to generate a Quarto notebook
        output_path: Path to save the notebook
        **kwargs: Additional parameters
    
    Returns:
        Dictionary with complete workflow results
    """
    if document_type is None:
        document_type = get_default_document_type(audience)
    
    return await process_chat_message(
        message=question,
        audience=audience,
        document_type=document_type,
        use_rag=use_rag,
        include_notebook=include_notebook,
        output_path=output_path,
        **kwargs
    )
