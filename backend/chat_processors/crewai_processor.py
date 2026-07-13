"""
CrewAI-based Chat Processor

This module contains the CrewAI-based implementation of chat message processing.
It uses CrewAI agents and crews for orchestration with proper LLM initialization.

Note: The CrewAI LLM is initialized lazily only when the processor is actually used,
to avoid errors when Azure OpenAI credentials are not set but MCP processor is being used.
"""

import os
import logging
from typing import Optional, Any
from dataclasses import dataclass, field

logger = logging.getLogger(__name__)


# LLM is initialized lazily in the _get_llm() method to avoid errors when
# Azure OpenAI credentials are not set (e.g., when using MCP processor)

# Global LLM instance (lazy initialized)
_llm: Optional[Any] = None


def _get_llm():
    """
    Lazy initialization of CrewAI LLM for Azure OpenAI.
    
    Returns the LLM instance, initializing it on first call if credentials are available.
    
    Raises:
        ImportError: If Azure OpenAI credentials are not set
    """
    global _llm
    
    if _llm is None:
        from crewai import LLM
        
        azure_endpoint = os.getenv("AZURE_OPENAI_ENDPOINT")
        azure_api_key = os.getenv("AZURE_OPENAI_API_KEY")
        
        if not azure_endpoint or not azure_api_key:
            raise ImportError(
                "Azure OpenAI credentials are required for CrewAI processor. "
                "Please set AZURE_OPENAI_ENDPOINT and AZURE_OPENAI_API_KEY environment variables. "
                "If you want to use MCP processor, set CHAT_PROCESSOR=mcp."
            )
        
        _llm = LLM(
            model=f"azure/{os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4.1')}",
            api_base=azure_endpoint,
            api_key=azure_api_key,
            api_version=os.getenv("OPENAI_API_VERSION", "2024-10-21"),
            timeout=float(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "120"))
        )
        
        logger.info("CrewAI LLM initialized successfully")
    
    return _llm


@dataclass
class CrewAIChatProcessor:
    """
    Processor that uses CrewAI agents for chat message processing.
    
    This implementation uses CrewAI's multi-agent orchestration framework
    to process chat messages with proper LLM initialization.
    """
    
    name: str = "crewai_processor"
    execution_source: str = "crewai"
    
    # Lazy-loaded components
    _manager: Any = field(default=None, init=False)
    _master_crew: Any = field(default=None, init=False)
    
    def _get_manager(self):
        """Lazy load the CrewAI manager."""
        if self._manager is None:
            from backend.crewai.manager import get_manager
            self._manager = get_manager()
        return self._manager
    
    def _get_master_crew(self, audience: str, document_type: str):
        """Lazy load the Master Crew for the given audience and document type."""
        from backend.crewai.crews.master_crew import MasterCrew
        # Create a new instance for each request to avoid state issues
        return MasterCrew(
            audience=audience,
            document_type=document_type
        )
    
    async def process(
        self,
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
        Process a chat message using CrewAI agents.
        
        This uses CrewAI's multi-agent orchestration to:
        1. Initialize LLM (lazy, on first use)
        2. Extract parameters from the question (if not provided)
        3. Use CrewAI Manager to execute the full workflow
        4. Generate comprehensive analysis with Quarto notebook
        """
        try:
            # Initialize LLM (lazy, only when CrewAI is actually used)
            llm = _get_llm()
            
            from backend.crewai.config import AudienceConfigManager
            from backend.crewai.manager import WorkflowType
            
            # Validate and set defaults
            effective_audience = AudienceConfigManager.validate_audience(audience or "internal")
            effective_document_type = document_type
            if effective_document_type:
                effective_document_type = AudienceConfigManager.validate_document_type(
                    effective_audience, effective_document_type
                )
            else:
                effective_document_type = AudienceConfigManager.get_default_type(effective_audience)
            
            # Extract parameters from message if not provided
            if not origin or not destination or not topic or not timespan:
                from backend.question_parser import extract_question_parameters
                extracted_params = await extract_question_parameters(message)
                logger.info(f"Extracted parameters: {extracted_params}")
                
                if not origin:
                    origin = extracted_params.get("origin")
                if not destination:
                    destination = extracted_params.get("destination")
                if not topic:
                    topic = extracted_params.get("topic")
                if not timespan:
                    timespan = extracted_params.get("timespan")
            
            # Use CrewAI Manager to execute workflow
            manager = self._get_manager()
            
            # Determine RAG usage
            effective_rag = use_rag if use_rag is not None else True
            effective_enhanced = use_enhanced if use_enhanced is not None else True
            
            result = await manager.execute_workflow(
                question=message,
                audience=effective_audience,
                document_type=effective_document_type,
                workflow_type=WorkflowType.FULL_ANALYSIS,
                use_rag=effective_rag,
                include_notebook=True,
                output_path=None
            )
            
            # Handle case where result is None or not a dict
            if result is None:
                result = {}
            if not isinstance(result, dict):
                result = {"status": "error", "error": f"Unexpected result type: {type(result)}"}
            
            # Ensure notebook is always a dict
            if "notebook" in result and result["notebook"] is None:
                result["notebook"] = {}
            if "notebook" not in result:
                result["notebook"] = {}
            
            # Adapt result to match expected format
            adapted_result = {
                "question": message,
                "analysis_type": "quarto_notebook",
                "quarto_content": result.get("notebook", {}).get("content", result.get("quarto_content", "")),
                "quarto_metadata": result.get("metadata", {}),
                "status": result.get("status", "error"),
                "execution_source": self.execution_source
            }
            
            # Copy additional fields if present
            for key in ["data", "visualization", "response", "story", "error"]:
                if key in result:
                    adapted_result[key] = result[key]
            
            # Add origin, destination, topic, timespan to metadata if available
            if origin or destination or topic or timespan:
                adapted_result["quarto_metadata"]["context"] = {
                    "origin": origin or "",
                    "destination": destination or "",
                    "topic": topic or "",
                    "timespan": timespan or ""
                }
            
            return adapted_result
            
        except Exception as e:
            logger.exception(f"CrewAI chat processing failed: {e}")
            # Check if it's a workflow execution error
            error_msg = str(e)
            if "workflow" in error_msg.lower() or "orchestrator" in error_msg.lower():
                error_msg = f"CrewAI workflow execution failed: {error_msg}"
            
            # Optionally fall back to MCP if CrewAI fails
            # For now, just return error - fallback can be added later
            return {
                "status": "error",
                "message": error_msg,
                "execution_source": self.execution_source,
                "question": message,
                "error": error_msg
            }
    
    async def run_tool_directly(self, tool_name: str, arguments: dict) -> dict:
        """
        Execute a tool directly using CrewAI agents.
        
        This will use the appropriate CrewAI agent to execute the tool.
        """
        try:
            from backend.crewai.manager import get_manager
            
            manager = get_manager()
            
            # For now, fall back to MCP bridge
            # In future, this can be implemented with direct CrewAI agent calls
            from backend.mcp_bridge import call_tool
            from backend.charts import generate_chart
            
            result = await call_tool(tool_name, arguments)
            chart = generate_chart(tool_name, result)
            
            return {
                "tool": tool_name,
                "arguments": arguments,
                "result": result,
                "chart": chart,
                "execution_source": self.execution_source
            }
            
        except Exception as e:
            logger.exception(e)
            return {
                "status": "error",
                "message": str(e),
                "execution_source": self.execution_source
            }
