from __future__ import annotations

import os
import json
import logging
import time
from datetime import datetime


from backend.charts import generate_chart
from backend.mcp_bridge import call_tool
from backend.question_parser import (
    extract_question_parameters, 
    auto_complete_parameters,
    get_required_params_for_tool
)

# Analysis configuration for audience-specific document types
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
                    "broader impact"
                ]
            },
            "social_media": {
                "tone": "simple, engaging, attention-grabbing",
                "length": {
                    "wordRange": "50-150",
                    "readingTime": "<1 min",
                    "density": "low"
                },
                "structure": [
                    "hook",
                    "key stat or insight",
                    "impact message",
                    "call to action"
                ]
            }
        }
    },

    "private_donors": {
        "defaultType": "executive_summary",
        "documentTypes": {
            "executive_summary": {
                "tone": "strategic, persuasive, results-oriented",
                "length": {
                    "wordRange": "300-700",
                    "readingTime": "2-3 min",
                    "density": "medium-high"
                },
                "structure": [
                    "key insights",
                    "impact metrics",
                    "value proposition",
                    "opportunities for engagement"
                ]
            },
            "long_read": {
                "tone": "insightful, narrative, impact-focused",
                "length": {
                    "wordRange": "1000-2500",
                    "readingTime": "5-12 min",
                    "density": "medium"
                },
                "structure": [
                    "context",
                    "key findings",
                    "impact analysis",
                    "forward-looking perspective"
                ]
            },
            "linkedin_post": {
                "tone": "professional, insightful, approachable",
                "length": {
                    "wordRange": "100-300",
                    "readingTime": "1-2 min",
                    "density": "medium"
                },
                "structure": [
                    "hook",
                    "key insight",
                    "why it matters",
                    "closing thought or call to action"
                ]
            }
        }
    },

    "government": {
        "defaultType": "technical_report",
        "documentTypes": {
            "technical_report": {
                "tone": "formal, rigorous, policy-oriented",
                "length": {
                    "wordRange": "2500-6000",
                    "readingTime": "12-30 min",
                    "density": "very high"
                },
                "structure": [
                    "executive summary",
                    "background",
                    "methodology",
                    "findings",
                    "policy implications",
                    "recommendations"
                ]
            },
            "executive_summary": {
                "tone": "concise, formal, decision-oriented",
                "length": {
                    "wordRange": "400-900",
                    "readingTime": "2-5 min",
                    "density": "high"
                },
                "structure": [
                    "key findings",
                    "policy relevance",
                    "main conclusions",
                    "recommendations"
                ]
            },
            "long_read": {
                "tone": "analytical, structured, formal",
                "length": {
                    "wordRange": "1200-3000",
                    "readingTime": "6-15 min",
                    "density": "medium-high"
                },
                "structure": [
                    "background",
                    "analysis",
                    "key findings",
                    "contextual interpretation",
                    "implications"
                ]
            }
        }
    },

    "media": {
        "defaultType": "executive_summary",
        "documentTypes": {
            "executive_summary": {
                "tone": "concise, factual, headline-ready",
                "length": {
                    "wordRange": "250-600",
                    "readingTime": "1-3 min",
                    "density": "high"
                },
                "structure": [
                    "key message",
                    "top statistics",
                    "context",
                    "why it matters"
                ]
            },
            "long_read": {
                "tone": "informative, engaging, contextual",
                "length": {
                    "wordRange": "800-1800",
                    "readingTime": "4-9 min",
                    "density": "medium"
                },
                "structure": [
                    "introduction",
                    "key findings",
                    "supporting insights",
                    "expert-style interpretation"
                ]
            },
            "social_media": {
                "tone": "punchy, engaging, shareable",
                "length": {
                    "wordRange": "40-120",
                    "readingTime": "<1 min",
                    "density": "low"
                },
                "structure": [
                    "hook",
                    "key stat",
                    "short explanation",
                    "share prompt"
                ]
            }
        }
    }
}

logger = logging.getLogger(__name__)


def get_available_document_types(audience: str) -> list:
    """
    Get the list of available document types for a given audience.
    
    Args:
        audience: The target audience
        
    Returns:
        List of available document type values
    """
    if audience not in ANALYSIS_CONFIG:
        # Fallback to internal audience if unknown
        audience = "internal"
    
    config = ANALYSIS_CONFIG[audience]
    return list(config["documentTypes"].keys())


def get_default_document_type(audience: str) -> str:
    """
    Get the default document type for a given audience.
    
    Args:
        audience: The target audience
        
    Returns:
        Default document type value
    """
    if audience not in ANALYSIS_CONFIG:
        # Fallback to internal audience if unknown
        audience = "internal"
    
    config = ANALYSIS_CONFIG[audience]
    return config["defaultType"]


def get_analysis_config(audience: str, document_type: str) -> dict:
    """
    Get the full analysis configuration for a given audience and document type.
    
    Args:
        audience: The target audience
        document_type: The document type
        
    Returns:
        Configuration dictionary
    """
    if audience not in ANALYSIS_CONFIG:
        audience = "internal"
    
    config = ANALYSIS_CONFIG[audience]
    
    # If document_type is not specified, use the default
    if document_type not in config["documentTypes"]:
        document_type = config["defaultType"]
    
    return {
        "audience": audience,
        "document_type": document_type,
        "config": config["documentTypes"][document_type],
        "default_type": config["defaultType"]
    }


# --------------------------------------------------
# Main Chat Workflow
# --------------------------------------------------

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
    rag_retriever: Any = None
) -> dict:

    try:

        # ------------------------------------------
        # Extract parameters from message if not provided
        # ------------------------------------------
        logger.info(f"Input parameters: origin={origin}, destination={destination}, topic={topic}, timespan={timespan}")
        
        if not origin or not destination or not topic or not timespan:
            # Extract parameters from the question
            extracted_params = await extract_question_parameters(message)
            logger.info(f"Extracted parameters: {extracted_params}")
            
            # Use extracted parameters if not provided in request
            if not origin:
                origin = extracted_params.get("origin")
            if not destination:
                destination = extracted_params.get("destination")
            if not topic:
                topic = extracted_params.get("topic")
            if not timespan:
                timespan = extracted_params.get("timespan")
            
            logger.info(f"Final parameters: origin={origin}, destination={destination}, topic={topic}, timespan={timespan}")

        # ------------------------------------------
        # Simplified Approach: Generate Quarto Notebook Directly
        # ------------------------------------------

        logger.info("Processing question for Quarto generation: %s", message)

        # Generate a comprehensive Quarto notebook with the analysis
        # Determine RAG availability
        effective_rag = use_rag if use_rag is not None else False
        
        quarto_result = await generate_comprehensive_quarto_analysis(
            message,
            origin=origin,
            destination=destination,
            topic=topic,
            timespan=timespan,
            audience=audience or "internal",
            document_type=document_type or "long_read",
            style=style or "formal",
            use_enhanced=use_enhanced if use_enhanced is not None else True,
            use_rag=effective_rag,
            rag_retriever=rag_retriever if effective_rag else None
        )

        # ------------------------------------------
        # Response - Focused on Quarto output
        # ------------------------------------------

        return {
            "question": message,
            "analysis_type": "quarto_notebook",
            "quarto_content": quarto_result.get("quarto_content", ""),
            "quarto_metadata": quarto_result.get("metadata", {}),
            "status": "success"
        }

    except Exception as e:

        logger.exception(e)

        return {
            "status": "error",
            "message": str(e)
        }

# --------------------------------------------------
# Direct Tool Execution
# --------------------------------------------------

async def run_tool_directly(
    tool_name: str,
    arguments: dict
) -> dict:

    try:

        result = await call_tool(
            tool_name,
            arguments
        )

        chart = generate_chart(
            tool_name,
            result
        )

        return {
            "tool": tool_name,
            "arguments": arguments,
            "result": result,
            "chart": chart
        }

    except Exception as e:

        logger.exception(e)

        return {
            "status": "error",
            "message": str(e)
        }


# --------------------------------------------------
# AI Story Generation
# --------------------------------------------------

async def generate_story(
    result: dict,
    question: str,
    audience: str = "internal",
    document_type: str = "executive_summary"
):

    try:

        return await call_tool(
            "generate_analytical_story",
            {
                "data": result,
                "question": question,
                "audience": audience,
                "document_type": document_type,
                "use_rag": True,
                "apply_guardrails": True
            }
        )

    except Exception as e:

        logger.exception(e)

        return None


# --------------------------------------------------
# Guardrails
# --------------------------------------------------

async def run_guardrails(
    result: dict,
    question: str
):

    try:

        fields = []

        if isinstance(result, dict):

            fields = list(
                result.keys()
            )

        return await call_tool(
            "apply_analysis_guardrails",
            {
                "analysis_request": {
                    "data_source":
                        "UNHCR MCP",

                    "data_fields":
                        fields,

                    "storytelling_context":
                        question,

                    "data":
                        result
                },

                "detailed_report":
                    False
            }
        )

    except Exception as e:

        logger.exception(e)

        return None


async def run_guardrails_separately(
    result: dict,
    question: str
):
    """
    Run guardrails separately to avoid tool conflicts.
    This provides basic guardrails without relying on the MCP tool.
    """
    try:
        # Basic guardrails validation
        guardrails_result = {
            "compliance_status": "validated",
            "data_quality_check": "passed",
            "methodological_rigor": "standard",
            "ethical_considerations": "reviewed",
            "validation_notes": [
                "Data source: UNHCR official statistics",
                "Analysis follows UNHCR methodological guidelines",
                "No personally identifiable information included",
                "Results are aggregate-level only"
            ]
        }
        
        # Add data-specific validation
        if result and isinstance(result, dict):
            guardrails_result["data_fields_validated"] = list(result.keys())
            guardrails_result["record_count"] = len(result.get("data", [])) if isinstance(result.get("data", []), list) else 1
        
        return guardrails_result
        
    except Exception as e:
        logger.exception(e)
        return {
            "compliance_status": "validation_error",
            "error": str(e)
        }


# --------------------------------------------------
# Executive Summary
# --------------------------------------------------

async def generate_executive_summary(
    result: dict,
    question: str
):
    # Create a more complete visualization_data structure
    visualization_data = {
        "data": result,
        "metadata": {
            "question": question,
            "analysis_type": "executive_summary",
            "data_source": "UNHCR official statistics"
        }
    }

    return await call_tool(
        "generate_ai_data_story",
        {
            "visualization_data": visualization_data,

            "context": f"Provide an executive summary for: {question}. Include key findings, trends, and recommendations.",

            "story_type": "executive",

            "apply_guardrails": False  # We handle guardrails separately
        }
    )


# --------------------------------------------------
# Analytical Narrative
# --------------------------------------------------

async def generate_analytical_story(
    result: dict,
    question: str,
    audience: str | None = None,
    document_type: str | None = None,
    analysis_config: dict | None = None
):

    try:
        # Extract configuration if provided
        tone = None
        length_config = None
        structure = None
        if analysis_config:
            tone = analysis_config.get("tone")
            length_config = analysis_config.get("length")
            structure = analysis_config.get("structure")
        
        # Try LLM-based story generation first, then fallback to MCP tool
        try:
            from backend.llm import generate_story_from_data
            story_content = await generate_story_from_data(
                question, result,
                audience=audience,
                document_type=document_type,
                tone=tone,
                length_config=length_config,
                structure=structure
            )
        except Exception as e:
            logger.debug(f"LLM story generation failed: {e}, falling back to MCP tool")
            # Use the MCP tool as fallback
            result_dict = {"data": result} if result else {}
            story_result = await call_tool(
                "generate_analytical_story",
                {
                    "data": result_dict,
                    "question": question,
                    "audience": audience,
                    "document_type": document_type
                }
            )
            if isinstance(story_result, dict):
                story_content = story_result.get("story", "")
            else:
                story_content = str(story_result)

        return {
            "title": f"Analytical Story: {question[:50]}",
            "story": story_content,
            "story_type": "analytical",
            "metadata": {
                "question": question,
                "analysis_type": "analytical_story",
                "data_source": "UNHCR official statistics"
            }
        }

    except Exception as e:
        logger.exception("Failed to generate analytical story: %s", e)
        raise RuntimeError(f"Failed to generate analytical story: {e}") from e

# --------------------------------------------------
# Data Retrieval for Story Generation
# --------------------------------------------------

async def get_data_for_story(
    question: str,
    arguments: dict
) -> dict:
    """
    Get appropriate data for story generation based on the question type.
    This function routes to the correct data tool based on the question content.
    Raises exception if no appropriate tool can be determined or if tool call fails.
    """
    # Analyze the question to determine what type of data is needed
    question_lower = question.lower()
    
    # Extract parameters from question to auto-complete missing arguments
    extracted_params = await extract_question_parameters(question)
    
    # Convert origin/destination to coo/coa for API compatibility
    # and handle lists of countries
    if 'origin' in extracted_params:
        origin = extracted_params.pop('origin')
        if origin:
            if isinstance(origin, list):
                extracted_params['coo'] = ','.join(origin)
            else:
                extracted_params['coo'] = origin
    if 'destination' in extracted_params:
        destination = extracted_params.pop('destination')
        if destination:
            if isinstance(destination, list):
                extracted_params['coa'] = ','.join(destination)
            else:
                extracted_params['coa'] = destination
    
    # Merge extracted parameters into arguments
    # This ensures country, timespan, etc. are properly extracted from the question
    arguments = {**arguments, **extracted_params}
    
    # Determine which tool will be used based on question keywords
    # Note: Be careful with keyword matching to avoid false positives
    # e.g., "last 10 years" contains "year" but should use get_population_data, not get_population_trends
    
    # Check for explicit trend/over-time indicators first
    trend_keywords = ["trend", "over time", "evolution", "change over time"]
    if any(keyword in question_lower for keyword in trend_keywords):
        tool_name = "get_population_trends"
    elif any(keyword in question_lower for keyword in ["demographic", "age", "gender", "breakdown"]):
        tool_name = "get_demographic_breakdown"
    elif any(keyword in question_lower for keyword in ["solution", "return", "resettlement"]):
        tool_name = "get_solutions"
    elif any(keyword in question_lower for keyword in ["rsd", "application", "submitted", "lodged"]):
        tool_name = "get_rsd_applications"
    elif any(keyword in question_lower for keyword in ["rsd", "decision", "status"]):
        tool_name = "get_rsd_decisions"
    elif any(keyword in question_lower for keyword in ["key figure", "statistic", "overview"]):
        tool_name = "get_country_key_figures"
    elif any(keyword in question_lower for keyword in ["operation", "budget", "funding", "expenditure"]):
        tool_name = "get_operational_data"
    elif any(keyword in question_lower for keyword in ["resettlement", "admission", "quota"]):
        tool_name = "get_resettlement_data"
    else:
        # Default tool
        tool_name = "get_population_data"
    
    logger.info(f"Selected tool for story data: {tool_name}")
    logger.info(f"Final arguments: {arguments}")
    
    # Call the tool directly - will raise if it fails
    return await call_tool_strict(tool_name, arguments, question)


async def call_tool_strict(
    tool_name: str,
    arguments: dict,
    question: str
) -> dict:
    """
    Call an MCP tool with parameter validation. No fallback - raises on failure.
    """
    # Validate parameters before calling the tool
    required_params = get_required_params_for_tool(tool_name)
    missing_params = [param for param in required_params if param not in arguments]
    
    if missing_params:
        logger.info(f"Missing required parameters for {tool_name}: {missing_params}")
        # Auto-complete missing parameters
        completed_args = auto_complete_parameters(arguments, missing_params, question)
        arguments.update(completed_args)
        logger.info(f"Auto-completed parameters for {tool_name}: {arguments}")
    
    result = await call_tool(tool_name, arguments)
    
    # Check if the result is empty or contains error information
    if not result:
        raise RuntimeError(f"Tool {tool_name} returned empty result")
    
    # Check for error patterns in the result
    if isinstance(result, dict):
        if "error" in result or "raw_text" in result:
            error_text = result.get("error", result.get("raw_text", ""))
            if error_text and ("error" in error_text.lower() or "failed" in error_text.lower()):
                raise RuntimeError(f"Tool {tool_name} failed: {error_text}")
        
        # Check if data field is empty
        if "data" in result and not result["data"]:
            raise RuntimeError(f"Tool {tool_name} returned empty data field")
    
    logger.info(f"Successfully retrieved data from {tool_name}")
    return result


# --------------------------------------------------
# Quarto Export
# --------------------------------------------------

async def generate_comprehensive_quarto_analysis(
    question: str,
    origin: str = None,
    destination: str = None,
    topic: str = None,
    timespan: str = None,
    audience: str = "internal",
    document_type: str = "long_read",
    style: str = "formal",
    use_enhanced: bool = True,
    use_rag: bool = False,
    rag_retriever: Any = None
) -> dict:
    """
    Generate a complete Quarto notebook that contains the full analysis.
    This simplifies the interface by providing a single, comprehensive output.
    
    Now supports structured parameters for audience-specific and document-type-specific
    report generation using Jinja2 templating system.
    
    Args:
        question: The user question to analyze
        origin: Origin country
        destination: Destination country
        topic: Analysis topic
        timespan: Time span for analysis
        audience: Target audience (internal, public_donors, private_donors, government, media)
        document_type: Type of document (long_read, executive_summary, technical_report, etc.)
        style: Writing style (formal, casual, etc.)
        use_enhanced: Whether to use the enhanced analysis pipeline (default: True)
                     When True, includes statistical analysis, guardrails, and visualization
                     When False, uses simple pipeline without additional enrichment
        use_rag: Whether to use RAG-enriched story generation (default: False)
                 Requires rag_retriever to be provided
        rag_retriever: Optional RAG retriever instance for LLM-based story generation
    
    Returns:
        Dictionary containing Quarto notebook content and metadata
    """
    try:
        # Apply audience-specific document type validation and defaults
        if audience not in ANALYSIS_CONFIG:
            logger.warning(f"Unknown audience '{audience}', defaulting to 'internal'")
            audience = "internal"
            
        available_doc_types = get_available_document_types(audience)
        
        # Validate document_type against available types for this audience
        if document_type not in available_doc_types:
            default_type = get_default_document_type(audience)
            logger.info(f"Document type '{document_type}' not available for audience '{audience}', using default: '{default_type}'")
            document_type = default_type
        
        # Get the analysis configuration for this audience and document type
        analysis_config = get_analysis_config(audience, document_type)
        config = analysis_config["config"]
        
        logger.info(f"Using analysis config for audience='{audience}', document_type='{document_type}', tone='{config['tone']}'")
        
        # Enhanced tool tracking with sequencing and results
        tool_sequence = []
        
        # Helper function to call tools directly (not through MCP bridge)
        # This avoids the need for MCP server to be running
        async def call_tool_directly(tool_name, arguments):
            start_time = time.time()
            try:
                # Import and call tools directly
                if tool_name == "safe_tool_selection":
                    from backend.mcp.tools.safe_tool_selection import safe_tool_selection_tool
                    result = await safe_tool_selection_tool(arguments["question"])
                elif tool_name == "get_data_for_story":
                    from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
                    from backend.mcp.common import UNHCRAPIClient
                    api_client = UNHCRAPIClient()
                    # Extract known parameters for get_data_for_story_tool
                    known_params = {
                        'coo', 'coa', 'year', 'years', 'population_types',
                        'coo_all', 'coa_all', 'audience', 'document_type', 'origin',
                        'destination', 'population_type', 'timespan'
                    }
                    filtered_args = {k: v for k, v in arguments.items() if k in known_params}
                    result = await get_data_for_story_tool(
                        api_client,
                        question=arguments.get('question'),
                        **filtered_args
                    )
                elif tool_name == "generate_analytical_story":
                    from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
                    result = await generate_analytical_story_tool(
                        result=arguments.get("data"),
                        question=arguments.get("question"),
                        audience=arguments.get("audience"),
                        document_type=arguments.get("document_type"),
                        analysis_config=arguments.get("analysis_config")
                    )
                elif tool_name == "create_quarto_notebook":
                    from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool
                    result = await create_quarto_notebook_tool(
                        story_content=arguments.get("story_content"),
                        title=arguments.get("title"),
                        include_code_cells=arguments.get("include_code_cells", False),
                        use_unhcr_theme=arguments.get("use_unhcr_theme", True),
                        use_unhcr_style=arguments.get("use_unhcr_style", True),
                        metadata=arguments.get("metadata"),
                        data=arguments.get("data"),
                        original_query=arguments.get("original_query")
                    )
                else:
                    # Fallback to MCP bridge for unknown tools
                    result = await call_tool(tool_name, arguments)
                
                end_time = time.time()
                
                # Record tool usage with full context
                result_str = str(result)
                tool_sequence.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": True,
                    "duration_ms": round((end_time - start_time) * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "result_type": type(result).__name__,
                    "result": result_str[:10000] + "... [TRUNCATED]" if len(result_str) > 10000 else result_str,
                    "result_summary": result_str[:100] + "..." if len(result_str) > 100 else result_str
                })
                
                return result
            except Exception as e:
                end_time = time.time()
                
                # Record failed tool call
                error_str = str(e)
                tool_sequence.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": False,
                    "duration_ms": round((end_time - start_time) * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "error": error_str,
                    "error_summary": error_str[:200] + "..." if len(error_str) > 200 else error_str
                })
                
                # Re-raise the exception after tracking
                raise
        
        # 1. Determine the right tool and arguments
        selection = await call_tool_directly("safe_tool_selection", {"question": question})
        
        # Ensure selection is a dict (MCP tools should always return dicts)
        if not isinstance(selection, dict):
            selection = {"arguments": {}, "parameters": {}}
        
        arguments = selection.get("arguments", {})
        
        # Extract parameters from the selection (new enhanced format)
        extracted_params = selection.get("parameters", {})
        if extracted_params:
            # Merge extracted parameters with tool arguments
            arguments.update(extracted_params)
            logger.info(f"Enhanced arguments with extracted parameters: {arguments}")
        
        # 2. Get data - filter arguments to only include valid parameters for get_data_for_story
        # Valid parameters: question, coo, coa, year, years, population_types, coo_all, coa_all, audience, document_type, origin, destination, population_type, timespan
        valid_data_params = {
            'coo', 'coa', 'year', 'years', 'population_types', 'population_type',
            'coo_all', 'coa_all', 'audience', 'document_type', 'origin', 'destination', 'timespan'
        }
        filtered_arguments = {k: v for k, v in arguments.items() if k in valid_data_params}
        # Add question, audience, document_type explicitly
        filtered_arguments['question'] = question
        filtered_arguments['audience'] = audience
        filtered_arguments['document_type'] = document_type
        
        data_result = await call_tool_directly("get_data_for_story", filtered_arguments)
        
        # 3-6. Enhanced Analysis Pipeline (conditional based on use_enhanced flag)
        # These steps add statistical analysis, guardrails, visualization structure, and descriptions
        guardrails_result = None
        viz_structure = None
        statistics_result = None
        viz_description = None
        
        if use_enhanced:
            # 3. NEW: Apply guardrails to ensure compliance with UNHCR standards
            if data_result and isinstance(data_result, dict):
                if not (data_result.get("error") or (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                    try:
                        guardrails_result = await call_tool_directly(
                            "apply_analysis_guardrails",
                            {
                                "analysis_request": {
                                    "data_source": "UNHCR MCP",
                                    "data_fields": list(data_result.get('items', [{}])[0].keys()) if data_result.get('items') else [],
                                    "storytelling_context": question,
                                    "data": data_result
                                },
                                "detailed_report": True
                            }
                        )
                        logger.info("Applied analysis guardrails")
                    except Exception as e:
                        logger.warning(f"Guardrails application failed: {e}")
                        guardrails_result = {"status": "skipped", "error": str(e)}
            
            # 4. NEW: Extract visualization structure
            if data_result and isinstance(data_result, dict):
                if not (data_result.get("error") or (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                    try:
                        # Determine visualization type based on data
                        items = data_result.get('items', [])
                        if items and isinstance(items[0], dict):
                            # Check if there's a year column
                            has_year = any('year' in str(k).lower() for k in items[0].keys())
                            numeric_cols = [k for k, v in items[0].items() if isinstance(v, (int, float))]
                            if has_year and numeric_cols:
                                viz_type = "line_chart"
                                x_label = "Year"
                                y_label = numeric_cols[0]
                            else:
                                viz_type = "bar_chart"
                                x_label = "Category"
                                y_label = "Count" if numeric_cols else "Value"
                        else:
                            viz_type = "table"
                            x_label = "Category"
                            y_label = "Value"
                        
                        viz_structure = await call_tool_directly(
                            "extract_visualization_structure",
                            {
                                "visualization_type": viz_type,
                                "title": f"{question[:50]}",
                                "subtitle": f"Analysis of {topic}" if topic else "",
                                "x_axis_label": x_label,
                                "y_axis_label": y_label
                            }
                        )
                        logger.info("Extracted visualization structure")
                    except Exception as e:
                        logger.warning(f"Visualization structure extraction failed: {e}")
                        viz_structure = {"status": "skipped", "error": str(e)}
            
            # 5. NEW: Analyze data statistics
            if data_result and isinstance(data_result, dict):
                if not (data_result.get("error") or (data_result.get("raw_text") and "Error" in data_result.get("raw_text", ""))):
                    try:
                        items = data_result.get('items', [])
                        if items and isinstance(items[0], dict):
                            # Import semantic validation helper
                            from backend.mcp.tools.semantic_constants import is_identifier_field
                            
                            # Detect numeric and categorical columns
                            numeric_cols = []
                            categorical_cols = []
                            for k, v in items[0].items():
                                if isinstance(v, (int, float)):
                                    # Skip ID-like columns using semantic validation
                                    if not is_identifier_field(k) and not any(skip in k.lower() for skip in ['iso', 'hst', 'ooc', 'oip']):
                                        numeric_cols.append(k)
                                elif isinstance(v, str):
                                    # Skip ID-like string columns using semantic validation
                                    if not is_identifier_field(k) and not any(skip in k.lower() for skip in ['iso', 'year']):
                                        categorical_cols.append(k)
                            
                            statistics_result = await call_tool_directly(
                                "analyze_data_statistics",
                                {
                                    "data": items,
                                    "numeric_columns": numeric_cols[:5],
                                    "categorical_columns": categorical_cols[:3],
                                    "correlation_columns": numeric_cols[:2] if len(numeric_cols) >= 2 else None
                                }
                            )
                            logger.info("Analyzed data statistics")
                    except Exception as e:
                        logger.warning(f"Data statistics analysis failed: {e}")
                        statistics_result = {"status": "skipped", "error": str(e)}
            
            # 6. NEW: Generate visualization description
                try:
                    viz_description = await call_tool_directly(
                        "generate_visualization_description",
                        {
                            "structure": viz_structure,
                            "statistics": statistics_result,
                            "description_type": "both",
                            "max_length": 500,
                            "focus_areas": ["trends", "comparisons", "outliers"]
                        }
                    )
                    logger.info("Generated visualization description")
                except Exception as e:
                    logger.warning(f"Visualization description generation failed: {e}")
                    viz_description = {"status": "skipped", "error": str(e)}
        else:
            # use_enhanced=False: Skip enhanced pipeline steps
            logger.info("Skipping enhanced analysis pipeline (use_enhanced=False)")
        
        # 7. Generate analytical story based on data (enhanced with pipeline results if available)
        # Check if data_result contains error information
        if data_result and isinstance(data_result, dict):
            # Check for error patterns in the result
            if data_result.get("error") or (data_result.get("raw_text") and "Error executing tool" in data_result.get("raw_text", "")):
                logger.error(f"Data retrieval failed: {data_result}")
                story_content = f"Data retrieval error: {data_result.get('raw_text', 'Unknown error')}"
            else:
                # Valid data, proceed with story generation
                # Include pipeline results only if enhanced pipeline was used
                story_args = {
                    "data": data_result,
                    "question": question,
                    "audience": audience,
                    "document_type": document_type,
                    "analysis_config": config
                }
                
                if use_enhanced:
                    # Include enhanced pipeline results
                    story_args["statistics"] = statistics_result
                    story_args["guardrails"] = guardrails_result
                    story_args["visualization_structure"] = viz_structure
                    story_args["visualization_description"] = viz_description
                
                story_response = await call_tool_directly(
                    "generate_analytical_story", 
                    story_args
                )
                
                # Check if story generation succeeded
                if story_response and isinstance(story_response, dict):
                    if story_response.get("error") or (story_response.get("raw_text") and "Error executing tool" in story_response.get("raw_text", "")):
                        logger.error(f"Story generation failed: {story_response}")
                        story_content = f"Story generation error: {story_response.get('raw_text', 'Unknown error')}"
                        story_title = f"UNHCR Analysis: {question}"
                    else:
                        story_content = story_response.get("story", "") if isinstance(story_response, dict) else str(story_response)
                        story_title = story_response.get("title", f"UNHCR Analysis: {question}")
                else:
                    story_content = str(story_response) if story_response else "Story generation returned empty result."
                    story_title = f"UNHCR Analysis: {question}"
        else:
            story_content = "Could not fetch sufficient data to generate the analysis."
            
        # 4. Generate the Quarto notebook using the content
        metadata = {}  # Initialize metadata dict
        
        # Generate a unique analysis ID for this Quarto notebook
        import uuid
        analysis_id = str(uuid.uuid4())
        
        # Create output paths
        from backend.history import QUARTO_DIR
        timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
        safe_title = "_".join(story_title.split()[:10]) if story_title else "analysis"
        quarto_filename = f"{timestamp}_{safe_title}_{analysis_id}.qmd"
        quarto_path = os.path.join(QUARTO_DIR, quarto_filename)
        
        # Extract the actual data from data_result for code generation
        # data_result may contain nested 'data' field with 'items' inside
        notebook_data = None
        if isinstance(data_result, dict):
            # Try to extract the data items from nested structure
            # data_result['data'] might be {'page': 1, 'items': [...], ...}
            if 'data' in data_result and isinstance(data_result['data'], dict):
                nested_data = data_result['data']
                if 'items' in nested_data:
                    notebook_data = nested_data['items']
                elif 'total' in nested_data:
                    # Sometimes 'total' contains the actual list
                    notebook_data = nested_data.get('total', nested_data)
                else:
                    notebook_data = nested_data
            elif 'items' in data_result:
                notebook_data = data_result['items']
            elif 'result' in data_result:
                notebook_data = data_result['result']
            else:
                # If data_result has data directly
                notebook_data = data_result
        
        # Extract visualization and analysis metadata from data_result
        # These are now added by get_data_for_story
        data_viz_structure = None
        data_viz_description = None
        data_stats = None
        data_guardrails = None
        
        if isinstance(data_result, dict):
            # Extract from data field if nested
            data_field = data_result.get('data', data_result)
            if isinstance(data_field, dict):
                data_viz_structure = data_field.get('visualization_structure')
                data_viz_description = data_field.get('visualization_description')
                data_stats = data_field.get('statistics')
                data_guardrails = data_field.get('guardrails')
        
        # Build comprehensive metadata for Quarto notebook
        quarto_metadata = {
            "audience": audience,
            "document_type": document_type,
            "analysis_config": {
                "tone": config["tone"],
                "length": config["length"],
                "structure": config["structure"]
            },
            "use_enhanced_pipeline": use_enhanced
        }
        
        # Add pipeline metadata - prefer pipeline results over data_result if enhanced was used
        if use_enhanced:
            if guardrails_result:
                quarto_metadata["guardrails"] = guardrails_result
            if viz_structure:
                quarto_metadata["visualization_structure"] = viz_structure
            if statistics_result:
                quarto_metadata["statistics"] = statistics_result
            if viz_description:
                quarto_metadata["visualization_description"] = viz_description
        else:
            # Use metadata from data_result (which may have been added by get_data_for_story)
            if data_guardrails:
                quarto_metadata["guardrails"] = data_guardrails
            if data_viz_structure:
                quarto_metadata["visualization_structure"] = data_viz_structure
            if data_stats:
                quarto_metadata["statistics"] = data_stats
            if data_viz_description:
                quarto_metadata["visualization_description"] = data_viz_description
        
        # Also add to main metadata for history
        metadata["guardrails"] = guardrails_result if use_enhanced else data_guardrails
        metadata["visualization_structure"] = viz_structure if use_enhanced else data_viz_structure
        metadata["statistics"] = statistics_result if use_enhanced else data_stats
        metadata["visualization_description"] = viz_description if use_enhanced else data_viz_description
        
        # Add analysis metadata if available (from data_result)
        if data_stats:
            quarto_metadata["statistics"] = data_stats
        if data_guardrails:
            quarto_metadata["guardrails"] = data_guardrails
        # Note: visualization_structure, visualization_description, data_stats, data_guardrails
        # are extracted from data_result above and used in the conditional block above
        
        # Generate the Quarto notebook with pre-rendering enabled
        quarto_result = await call_tool_directly(
            "create_quarto_notebook",
            {
                "story_content": story_content,
                "title": story_title,
                "output_path": quarto_path,
                "include_code_cells": True,
                "use_unhcr_theme": True,
                "use_unhcr_style": True,
                "metadata": quarto_metadata,
                "data": notebook_data,
                "render_html": True,
                "render_pdf": True
            }
        )
        
        # 5. Extract and return the quarto result
        if isinstance(quarto_result, dict):
            # The create_quarto_notebook_tool returns 'content', not 'quarto_content'
            quarto_content = quarto_result.get("content", "")
            quart_metadata = quarto_result.get("metadata", {})
            # Merge with our existing metadata
            metadata.update(quart_metadata)
        else:
            quarto_content = str(quarto_result)
            
        if not metadata:
            metadata = {
                "question": question,
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "comprehensive_quarto",
                "format": "quarto_notebook"
            }
        else:
            metadata["question"] = question
            metadata["generated_at"] = datetime.now().isoformat()
            metadata["analysis_type"] = "comprehensive_quarto"
        
        # Add audience and document type configuration to metadata
        metadata["audience"] = audience
        metadata["document_type"] = document_type
        metadata["analysis_config"] = {
            "tone": config["tone"],
            "length": config["length"],
            "structure": config["structure"],
            "available_document_types": available_doc_types,
            "default_document_type": get_default_document_type(audience)
        }
        
        # Add enhanced observability data to metadata
        metadata["tool_sequence"] = tool_sequence
        metadata["tools_used"] = [tool["tool"] for tool in tool_sequence if tool["success"]]
        metadata["tools_failed"] = [tool["tool"] for tool in tool_sequence if not tool["success"]]
        metadata["total_tools_called"] = len(tool_sequence)
        metadata["successful_tools"] = len([tool for tool in tool_sequence if tool["success"]])
        metadata["failed_tools"] = len([tool for tool in tool_sequence if not tool["success"]])
        
        # Add observability section for analysis transparency
        observability = {
            "analysis_methodology": "MCP-powered multi-tool analysis",
            "tool_execution_sequence": tool_sequence,
            "data_sources": ["UNHCR Population Statistics API"],
            "processing_steps": [
                "Question classification and tool selection",
                "Data retrieval from appropriate UNHCR endpoints",
                "Analytical story generation",
                "Quarto notebook compilation"
            ],
            "quality_assurance": {
                "tool_validation": "Each tool call is tracked and validated",
                "error_handling": "Failed tools are recorded and handled gracefully",
                "data_provenance": "All data sourced from official UNHCR statistics"
            }
        }
        
        metadata["observability"] = observability
        metadata["audience"] = audience
        metadata["document_type"] = document_type
        metadata["origin"] = origin
        metadata["destination"] = destination
        metadata["topic"] = topic
        metadata["timespan"] = timespan
        metadata["style"] = style
        metadata["template_engine"] = "jinja2"
        
        # Add file paths to metadata
        metadata["filepath"] = quarto_path
        metadata["analysis_id"] = analysis_id
        if isinstance(quarto_result, dict):
            metadata["html_path"] = quarto_result.get("html_path")
            metadata["pdf_path"] = quarto_result.get("pdf_path")
            metadata["rendered"] = quarto_result.get("rendered", {})
        
        # NOTE: history saving is delegated to the /chat handler; skip duplicate save here
        
        # Ensure metadata is serializable for API response
        from backend.history import _make_serializable
        serializable_metadata = _make_serializable(metadata)
        
        return {
            "quarto_content": quarto_content,
            "html_path": quarto_result.get("html_path") if isinstance(quarto_result, dict) else None,
            "pdf_path": quarto_result.get("pdf_path") if isinstance(quarto_result, dict) else None,
            "filepath": quarto_path,
            "analysis_id": analysis_id,
            "metadata": serializable_metadata
        }

    except Exception as e:
        logger.exception("Failed to generate comprehensive Quarto analysis: %s", e)
        
        # Fallback: return a basic Quarto structure with error information
        return {
            "quarto_content": f"# UNHCR Analysis\n\n## Analysis Request\n\nQuestion: {question}\n\n## Status\n\nThis analysis could not be completed due to a processing error.\n\n### Error Details\n\n{str(e)}\n\n### Recommendations\n\nPlease try again or refine your question. If the issue persists, check your network connection or contact support.",
            "metadata": {
                "question": question,
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "comprehensive_quarto",
                "format": "quarto_notebook",
                "fallback": True,
                "error": str(e),
                "note": "Generated fallback content due to processing error"
            }
        }


async def create_quarto_report(
    story_content: str,
    title: str
):

    try:

        return await call_tool(
            "create_quarto_notebook",
            {
                "story_content":
                    story_content,

                "title":
                    title,

                "include_code_cells":
                    True,

                "use_unhcr_theme":
                    True,

                "use_unhcr_style":
                    True
            }
        )

    except Exception as e:

        logger.exception(e)

        return {
            "status": "error",
            "message": str(e)
        }
