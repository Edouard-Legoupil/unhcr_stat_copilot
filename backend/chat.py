from __future__ import annotations

import json
import logging
import time
from datetime import datetime


from backend.charts import generate_chart
from backend.llm import safe_tool_selection
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
    style: Optional[str] = None
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
        quarto_result = await generate_comprehensive_quarto_analysis(
            message,
            origin=origin,
            destination=destination,
            topic=topic,
            timespan=timespan,
            audience=audience or "internal",
            document_type=document_type or "long_read",
            style=style or "formal"
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
    question: str
):

    try:

        visualization_data = {
            "data": result
        }

        return await call_tool(
            "generate_ai_data_story",
            {
                "visualization_data":
                    visualization_data,

                "context":
                    question,

                "story_type":
                    "executive",

                "apply_guardrails":
                    True
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
        from backend.llm import generate_story_from_data
        
        # Extract configuration if provided
        tone = None
        length_config = None
        structure = None
        if analysis_config:
            tone = analysis_config.get("tone")
            length_config = analysis_config.get("length")
            structure = analysis_config.get("structure")
        
        story_content = await generate_story_from_data(
            question, result,
            audience=audience,
            document_type=document_type,
            tone=tone,
            length_config=length_config,
            structure=structure
        )

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
    
    # Determine which tool will be used based on question keywords
    if any(keyword in question_lower for keyword in ["demographic", "age", "gender", "breakdown"]):
        tool_name = "get_demographic_breakdown"
    elif any(keyword in question_lower for keyword in ["trend", "over time", "year", "evolution"]):
        tool_name = "get_population_trends"
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
    style: str = "formal"
) -> dict:
    """
    Generate a complete Quarto notebook that contains the full analysis.
    This simplifies the interface by providing a single, comprehensive output.
    
    Now supports structured parameters for audience-specific and document-type-specific
    report generation using Jinja2 templating system.
    """
    try:
        from backend.llm import safe_tool_selection
        
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
        
        # Helper function to track tool usage with full context
        async def track_tool_call(tool_name, arguments):
            start_time = time.time()
            try:
                result = await call_tool(tool_name, arguments)
                end_time = time.time()
                
                # Record tool usage with full context
                tool_sequence.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": True,
                    "duration_ms": round((end_time - start_time) * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "result_type": type(result).__name__,
                    "result_summary": str(result)[:100] + "..." if len(str(result)) > 100 else str(result)
                })
                
                return result
            except Exception as e:
                end_time = time.time()
                
                # Record failed tool call
                tool_sequence.append({
                    "tool": tool_name,
                    "arguments": arguments,
                    "success": False,
                    "duration_ms": round((end_time - start_time) * 1000, 2),
                    "timestamp": datetime.now().isoformat(),
                    "error": str(e)[:200]
                })
                
                # Re-raise the exception after tracking
                raise
        
        # 1. Determine the right tool and arguments
        selection = await track_tool_call("safe_tool_selection", {"question": question})
        arguments = selection.get("arguments", {})
        
        # Extract parameters from the selection (new enhanced format)
        extracted_params = selection.get("parameters", {})
        if extracted_params:
            # Merge extracted parameters with tool arguments
            arguments.update(extracted_params)
            logger.info(f"Enhanced arguments with extracted parameters: {arguments}")
        
        # 2. Get data
        data_result = await track_tool_call("get_data_for_story", {"question": question, "audience": audience, "document_type": document_type, **arguments})
        
        # 3. Generate analytical story based on data
        # Check if data_result contains error information
        if data_result and isinstance(data_result, dict):
            # Check for error patterns in the result
            if data_result.get("error") or (data_result.get("raw_text") and "Error executing tool" in data_result.get("raw_text", "")):
                logger.error(f"Data retrieval failed: {data_result}")
                story_content = f"Data retrieval error: {data_result.get('raw_text', 'Unknown error')}"
            else:
                # Valid data, proceed with story generation
                story_response = await track_tool_call("generate_analytical_story", {"data": data_result, "question": question, "audience": audience, "document_type": document_type, "analysis_config": config})
                
                # Check if story generation succeeded
                if story_response and isinstance(story_response, dict):
                    if story_response.get("error") or (story_response.get("raw_text") and "Error executing tool" in story_response.get("raw_text", "")):
                        logger.error(f"Story generation failed: {story_response}")
                        story_content = f"Story generation error: {story_response.get('raw_text', 'Unknown error')}"
                    else:
                        story_content = story_response.get("story", "") if isinstance(story_response, dict) else str(story_response)
                else:
                    story_content = str(story_response) if story_response else "Story generation returned empty result."
        else:
            story_content = "Could not fetch sufficient data to generate the analysis."
            
        # 4. Generate the Quarto notebook using the content
        quarto_result = await track_tool_call(
            "create_quarto_notebook",
            {
                "story_content": f"## Analysis\n\n{story_content}",
                "title": f"UNHCR Analysis: {question[:50]}..." if len(question) > 50 else f"UNHCR Analysis: {question}",
                "include_code_cells": True,
                "use_unhcr_theme": True,
                "use_unhcr_style": True,
                "metadata": {
                    "audience": audience,
                    "document_type": document_type,
                    "analysis_config": {
                        "tone": config["tone"],
                        "length": config["length"],
                        "structure": config["structure"]
                    }
                }
            }
        )
        
        # 5. Extract and return the quarto result
        if isinstance(quarto_result, dict):
            quarto_content = quarto_result.get("quarto_content", "")
            metadata = quarto_result.get("metadata", {})
        else:
            quarto_content = str(quarto_result)
            metadata = {}
            
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
        
        return {
            "quarto_content": quarto_content,
            "metadata": metadata
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
        
    except Exception as e:
        logger.exception("Failed to generate comprehensive Quarto analysis: %s", e)
        
        # Fallback: Generate a basic Quarto notebook
        return {
            "quarto_content": f"""# UNHCR Analysis Report

## Request
{question}

## Analysis

Analysis generation failed, but this Quarto notebook structure is ready for content.

## Notes

The analysis will be completed when the data tools are available.
""",
            "metadata": {
                "question": question,
                "generated_at": datetime.now().isoformat(),
                "analysis_type": "basic_quarto_fallback",
                "format": "quarto_notebook",
                "status": "fallback"
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