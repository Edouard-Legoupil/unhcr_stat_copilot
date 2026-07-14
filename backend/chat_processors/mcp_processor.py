"""
MCP-based Chat Processor

This module contains the MCP-based implementation of chat message processing.
It uses direct MCP tool calls for orchestration.
"""

import logging
from typing import Optional, Any
from dataclasses import dataclass

from backend.charts import generate_chart
from backend.mcp_bridge import call_tool
from backend.question_parser import (
    extract_question_parameters, 
    auto_complete_parameters,
    get_required_params_for_tool
)

logger = logging.getLogger(__name__)


@dataclass
class MCPChatProcessor:
    """
    Processor that uses MCP tools directly for chat message processing.
    
    This is the original implementation that calls MCP tools sequentially.
    """
    
    name: str = "mcp_processor"
    execution_source: str = "mcp"
    
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
        Process a chat message using MCP tools.
        
        This is the original implementation that was in backend/chat.py.
        """
        try:
            # Extract parameters from message if not provided
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

            # Generate a comprehensive Quarto notebook with the analysis
            # Determine RAG availability
            effective_rag = use_rag if use_rag is not None else False
            
            quarto_result = await self._generate_comprehensive_quarto_analysis(
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

            # Build response
            result = {
                "question": message,
                "analysis_type": "quarto_notebook",
                "quarto_content": quarto_result.get("quarto_content", ""),
                "quarto_metadata": quarto_result.get("metadata", {}),
                "status": "success",
                "execution_source": self.execution_source
            }
            
            # Add optional fields if present
            for key in ["data", "visualization", "response", "story"]:
                if key in quarto_result:
                    result[key] = quarto_result[key]
            
            return result

        except Exception as e:
            logger.exception(e)
            return {
                "status": "error",
                "message": str(e),
                "execution_source": self.execution_source
            }
    
    async def _generate_comprehensive_quarto_analysis(
        self,
        question: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        topic: Optional[str] = None,
        timespan: Optional[str] = None,
        audience: str = "internal",
        document_type: str = "long_read",
        style: str = "formal",
        use_enhanced: bool = True,
        use_rag: bool = True,
        rag_retriever: Any = None
    ) -> dict:
        """Generate a comprehensive Quarto notebook analysis."""
        from backend.mcp_bridge import call_tool
        from backend.crewai.mcp_integration import full_analysis_workflow_tool
        
        try:
            # Prepare the analysis data
            analysis_data = {
                "question": question,
                "origin": origin,
                "destination": destination,
                "topic": topic,
                "timespan": timespan,
                "audience": audience,
                "document_type": document_type,
                "style": style,
                "use_enhanced": use_enhanced,
                "use_rag": use_rag
            }
            
            # Use the full analysis workflow tool
            result = await full_analysis_workflow_tool(
                question=question,
                origin=origin or "",
                destination=destination or "",
                topic=topic or "",
                timespan=timespan or "",
                audience=audience,
                document_type=document_type,
                style=style,
                use_enhanced=use_enhanced,
                use_rag=use_rag,
                rag_retriever=rag_retriever
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error in comprehensive Quarto analysis: {e}")
            # Fallback to basic analysis
            return await self._basic_quarto_analysis(
                question,
                origin=origin,
                destination=destination,
                topic=topic,
                timespan=timespan,
                audience=audience,
                document_type=document_type,
                style=style
            )
    
    async def _basic_quarto_analysis(
        self,
        question: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        topic: Optional[str] = None,
        timespan: Optional[str] = None,
        audience: str = "internal",
        document_type: str = "long_read",
        style: str = "formal"
    ) -> dict:
        """Generate a basic Quarto notebook analysis."""
        try:
            # Extract data based on question parameters
            data_result = await self._extract_data(
                question,
                origin=origin,
                destination=destination,
                topic=topic,
                timespan=timespan
            )
            
            if data_result.get("status") == "error":
                return data_result
            
            # Generate story from data
            story_result = await self._generate_story(
                data_result,
                question,
                audience=audience,
                document_type=document_type
            )
            
            if story_result.get("status") == "error":
                return story_result
            
            # Create Quarto notebook
            # Ensure story_content is a string
            story_content = story_result.get("story", "")
            if not isinstance(story_content, str):
                if isinstance(story_content, list):
                    story_content = '\n'.join(str(item) for item in story_content)
                else:
                    story_content = str(story_content)
            
            notebook_result = await call_tool(
                "create_quarto_notebook",
                {
                    "story_content": story_content,
                    "data": data_result,
                    "question": question,
                    "audience": audience,
                    "document_type": document_type,
                    "origin": origin or "",
                    "destination": destination or "",
                    "topic": topic or "",
                    "timespan": timespan or ""
                }
            )
            
            return {
                "quarto_content": notebook_result.get("quarto_content", ""),
                "quarto_metadata": notebook_result.get("metadata", {}),
                "data": data_result,
                "story": story_content,
                "analysis_type": "quarto_notebook"
            }
            
        except Exception as e:
            logger.exception(f"Error in basic Quarto analysis: {e}")
            return {
                "status": "error",
                "message": str(e),
                "quarto_content": "",
                "quarto_metadata": {}
            }
    
    async def _extract_data(
        self,
        question: str,
        origin: Optional[str] = None,
        destination: Optional[str] = None,
        topic: Optional[str] = None,
        timespan: Optional[str] = None
    ) -> dict:
        """Extract data based on question parameters."""
        try:
            from backend.crewai.mcp_integration import get_data_for_story_tool
            
            result = await get_data_for_story_tool(
                question=question,
                origin=origin or "",
                destination=destination or "",
                topic=topic or "",
                timespan=timespan or "",
                population_types=None,
                year=None,
                years=None,
                coo_all=False,
                coa_all=False,
                audience=None,
                document_type=None
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error extracting data: {e}")
            return {
                "status": "error",
                "message": str(e),
                "data": {}
            }
    
    async def _generate_story(
        self,
        data: dict,
        question: str,
        audience: str = "internal",
        document_type: str = "long_read"
    ) -> dict:
        """Generate a story from data."""
        try:
            result = await call_tool(
                "generate_analytical_story",
                {
                    "data": data,
                    "question": question,
                    "audience": audience,
                    "document_type": document_type,
                    "use_rag": True,
                    "apply_guardrails": True
                }
            )
            
            return result
            
        except Exception as e:
            logger.exception(f"Error generating story: {e}")
            return {
                "status": "error",
                "message": str(e),
                "story": ""
            }
    
    async def run_tool_directly(self, tool_name: str, arguments: dict) -> dict:
        """Execute a tool directly."""
        try:
            result = await call_tool(tool_name, arguments)
            chart = generate_chart(tool_name, result)
            
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
