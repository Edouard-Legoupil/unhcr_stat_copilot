"""
Chat Processing Module

This module provides chat message processing for the UNHCR Statistics Copilot.

It delegates to either MCP-based or CrewAI-based processors based on the
CHAT_PROCESSOR environment variable.

Environment Variables:
    CHAT_PROCESSOR: "mcp" (default) or "crewai"

Usage:
    from backend.chat import process_chat_message
    
    result = await process_chat_message(
        message="Show me refugee trends",
        audience="policy_makers"
    )
"""

# Import the processors
from backend.chat_processors.mcp_processor import MCPChatProcessor
from backend.chat_processors.crewai_processor import CrewAIChatProcessor

import os
import logging
from typing import Optional, Any
from enum import Enum

logger = logging.getLogger(__name__)


class ChatProcessorType(Enum):
    """Available chat processor types."""
    MCP = "mcp"           # Use MCP-based processing (default)
    CREWAI = "crewai"     # Use CrewAI-based processing


# Global processor instance (lazy initialized)
_processor: Optional[Any] = None


def get_chat_processor():
    """
    Get the appropriate chat processor based on CHAT_PROCESSOR environment variable.
    
    Returns:
        A processor instance (MCPChatProcessor or CrewAIChatProcessor)
    """
    global _processor
    
    if _processor is None:
        processor_type = os.getenv("CHAT_PROCESSOR", "mcp").lower()
        
        try:
            processor_type = ChatProcessorType(processor_type)
        except ValueError:
            logger.warning(f"Invalid CHAT_PROCESSOR: {processor_type}, defaulting to MCP")
            processor_type = ChatProcessorType.MCP
        
        if processor_type == ChatProcessorType.CREWAI:
            _processor = CrewAIChatProcessor()
            logger.info("Using CrewAI chat processor")
        else:
            _processor = MCPChatProcessor()
            logger.info("Using MCP chat processor")
    
    return _processor


def reset_chat_processor():
    """Reset the chat processor instance (useful for testing)."""
    global _processor
    _processor = None


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
    """
    Process a chat message using the configured processor.
    
    This is the main entry point for chat message processing. It delegates
    to either MCP or CrewAI processor based on CHAT_PROCESSOR environment variable.
    
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
        rag_retriever: RAG retriever instance (optional)
    
    Returns:
        Dictionary containing analysis results, including:
        - question: The original question
        - analysis_type: Type of analysis performed
        - quarto_content: Generated Quarto notebook content
        - quarto_metadata: Notebook metadata
        - status: "success" or "error"
        - execution_source: "mcp" or "crewai" (indicating which processor was used)
    """
    processor = get_chat_processor()
    
    result = await processor.process(
        message=message,
        origin=origin,
        destination=destination,
        topic=topic,
        timespan=timespan,
        audience=audience,
        document_type=document_type,
        style=style,
        use_enhanced=use_enhanced,
        use_rag=use_rag,
        rag_retriever=rag_retriever
    )
    
    return result


async def run_tool_directly(tool_name: str, arguments: dict) -> dict:
    """
    Execute a tool directly.
    
    This will use the appropriate processor (MCP or CrewAI) based on configuration.
    """
    processor = get_chat_processor()
    if hasattr(processor, 'run_tool_directly'):
        return await processor.run_tool_directly(tool_name, arguments)
    else:
        # Fallback to MCP implementation
        mcp_processor = MCPChatProcessor()
        return await mcp_processor.run_tool_directly(tool_name, arguments)


# =============================================================================
# Analysis Configuration (for backward compatibility)
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


def get_available_document_types(audience: str = "internal") -> list:
    """Get available document types for a given audience."""
    if audience not in ANALYSIS_CONFIG:
        audience = "internal"
    
    return list(ANALYSIS_CONFIG[audience]["documentTypes"].keys())


def get_default_document_type(audience: str = "internal") -> str:
    """Get the default document type for a given audience."""
    if audience not in ANALYSIS_CONFIG:
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
