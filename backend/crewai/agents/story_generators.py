"""
Story Generator Agents for UNHCR Statistics Copilot

These agents are responsible for generating narratives and stories from UNHCR data.
"""

import logging
from typing import Any, Dict, Optional

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.config import CrewAIConfig, AudienceConfigManager
from backend.crewai.tools.adapters import MCPToolAdapter

logger = logging.getLogger(__name__)


class StoryGenerator(UNHCRBaseAgent):
    """
    Specialist agent for generating analytical stories from UNHCR data.
    
    This agent creates compelling narratives based on data and analysis results.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Story Generator agent."""
        kwargs.setdefault('role', 'Story Generator')
        kwargs.setdefault('goal', 'Create compelling data stories from UNHCR analysis')
        
        super().__init__(**kwargs)
        
        # Initialize RAG retriever if available
        try:
            from backend.mcp.common import UNHCRVectorRetriever
            self.rag_retriever = UNHCRVectorRetriever()
            logger.info("RAG retriever initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize RAG retriever: {e}")
            self.rag_retriever = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register story generation tools."""
        try:
            from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
            
            tools = []
            
            # Adapt the story generation tool
            # This is async, so we need special handling
            import inspect
            if inspect.iscoroutinefunction(generate_analytical_story_tool):
                async def async_wrapper(*args, **kwargs):
                    # Inject RAG retriever if available and requested
                    if self.rag_retriever and kwargs.get('use_rag', False):
                        kwargs['rag_retriever'] = self.rag_retriever
                    return await generate_analytical_story_tool(*args, **kwargs)
                
                tool = MCPToolAdapter.adapt_mcp_tool(
                    async_wrapper,
                    name="generate_analytical_story",
                    description=(
                        "Generate analytical stories and narratives from UNHCR data. "
                        "Optionally enriched with relevant context retrieved from UNHCR reports."
                    )
                )
            else:
                def sync_wrapper(*args, **kwargs):
                    if self.rag_retriever and kwargs.get('use_rag', False):
                        kwargs['rag_retriever'] = self.rag_retriever
                    return generate_analytical_story_tool(*args, **kwargs)
                
                tool = MCPToolAdapter.adapt_mcp_tool(
                    sync_wrapper,
                    name="generate_analytical_story",
                    description=(
                        "Generate analytical stories and narratives from UNHCR data. "
                        "Optionally enriched with relevant context retrieved from UNHCR reports."
                    )
                )
            
            tools.append(tool)
            self.register_tool("generate_analytical_story", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for StoryGenerator: {e}")
            self.tools = []
    
    def generate_story(
        self,
        data: Dict[str, Any],
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report",
        use_rag: bool = True,
        analysis_config: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """
        Generate a story from data and analysis.
        
        Args:
            data: The data to base the story on
            question: The original user question
            audience: Target audience for the story
            document_type: Document type for the story
            use_rag: Whether to use RAG enrichment
            analysis_config: Optional analysis configuration
            
        Returns:
            Generated story with metadata
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        # Get configuration for audience
        if analysis_config is None:
            analysis_config = AudienceConfigManager.get_config(audience, document_type)
        
        try:
            # Determine RAG usage
            rag_enabled = use_rag and CrewAIConfig.RAG_ENABLED and self.rag_retriever is not None
            
            # Prepare arguments
            args = {
                'data': data,
                'question': question,
                'audience': audience,
                'document_type': document_type,
                'analysis_config': analysis_config,
                'use_rag': rag_enabled
            }
            
            # Execute story generation
            result = self.execute_tool("generate_analytical_story", **args)
            
            # Parse result if it's a string
            if isinstance(result, str):
                try:
                    import json
                    result = json.loads(result)
                except Exception:
                    result = {'story': result}
            
            return {
                'status': 'success',
                'story': result.get('story', result),
                'metadata': result.get('metadata', {}),
                'question': question,
                'audience': audience,
                'document_type': document_type,
                'rag_used': rag_enabled,
                'config': analysis_config
            }
            
        except Exception as e:
            logger.error(f"Failed to generate story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': audience,
                'document_type': document_type
            }
    
    def generate_comparison_story(
        self,
        scenarios: list,
        data_list: list,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        Generate a comparison story from multiple scenarios and data.
        
        Args:
            scenarios: List of comparison scenarios
            data_list: List of data for each scenario
            question: The original comparison question
            audience: Target audience
            document_type: Document type
            
        Returns:
            Generated comparison story with metadata
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        config = AudienceConfigManager.get_config(audience, document_type)
        
        try:
            # Build comparison data structure
            comparison_data = {
                'scenarios': scenarios,
                'data_list': data_list,
                'question': question,
                'type': 'comparison',
                'audience': audience,
                'document_type': document_type,
                'analysis_config': config
            }
            
            # For now, use the regular story generation with comparison data
            # In a full implementation, this would use a specialized comparison template
            result = self.execute_tool("generate_analytical_story", **{
                'data': comparison_data,
                'question': question,
                'audience': audience,
                'document_type': document_type,
                'analysis_config': config,
                'use_rag': False  # Disable RAG for comparison stories
            })
            
            # Parse result if it's a string
            if isinstance(result, str):
                try:
                    import json
                    result = json.loads(result)
                except Exception:
                    result = {'story': result}
            
            return {
                'status': 'success',
                'story': result.get('story', result),
                'metadata': result.get('metadata', {}),
                'scenarios': scenarios,
                'question': question,
                'audience': audience,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Failed to generate comparison story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'scenarios': scenarios,
                'question': question,
                'audience': audience,
                'document_type': document_type
            }


class RAGResearcher(UNHCRBaseAgent):
    """
    Specialist agent for Retrieval-Augmented Generation (RAG) research.
    
    This agent retrieves relevant context from UNHCR reports to enrich stories.
    """
    
    def __init__(self, **kwargs):
        """Initialize the RAG Researcher agent."""
        kwargs.setdefault('role', 'RAG Researcher')
        kwargs.setdefault('goal', 'Retrieve relevant context from UNHCR reports')
        
        super().__init__(**kwargs)
        
        # Initialize RAG retriever
        try:
            from backend.mcp.common import UNHCRVectorRetriever
            self.rag_retriever = UNHCRVectorRetriever()
            logger.info("RAG retriever initialized for RAGResearcher")
        except Exception as e:
            logger.warning(f"Could not initialize RAG retriever for RAGResearcher: {e}")
            self.rag_retriever = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register RAG tools."""
        try:
            from backend.mcp.tools.retrieve_report_context import retrieve_report_context_tool
            
            tools = []
            
            # Adapt the RAG tool
            import inspect
            if inspect.iscoroutinefunction(retrieve_report_context_tool):
                async def async_wrapper(*args, **kwargs):
                    if self.rag_retriever:
                        # Inject retriever if not provided
                        if 'rag_retriever' not in kwargs:
                            kwargs['rag_retriever'] = self.rag_retriever
                    return await retrieve_report_context_tool(*args, **kwargs)
                
                tool = MCPToolAdapter.adapt_mcp_tool(
                    async_wrapper,
                    name="retrieve_report_context",
                    description=(
                        "Retrieve relevant contextual excerpts from UNHCR reports. "
                        "Use to support data stories, methodology explanations, and source-grounded analysis."
                    )
                )
            else:
                def sync_wrapper(*args, **kwargs):
                    if self.rag_retriever:
                        if 'rag_retriever' not in kwargs:
                            kwargs['rag_retriever'] = self.rag_retriever
                    return retrieve_report_context_tool(*args, **kwargs)
                
                tool = MCPToolAdapter.adapt_mcp_tool(
                    sync_wrapper,
                    name="retrieve_report_context",
                    description=(
                        "Retrieve relevant contextual excerpts from UNHCR reports. "
                        "Use to support data stories, methodology explanations, and source-grounded analysis."
                    )
                )
            
            tools.append(tool)
            self.register_tool("retrieve_report_context", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for RAGResearcher: {e}")
            self.tools = []
    
    def retrieve_context(
        self,
        request: str,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report",
        top_k: int = 5,
        fetch_k: int = 20,
        year: Optional[str] = None,
        report_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Retrieve relevant context for a request.
        
        Args:
            request: The context request
            question: The original user question
            audience: Target audience
            document_type: Document type
            top_k: Number of top results
            fetch_k: Number of results to fetch
            year: Optional year filter
            report_type: Optional report type filter
            
        Returns:
            Retrieved context with metadata
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        try:
            # Use RAG retriever if available
            if self.rag_retriever:
                context = self.rag_retriever.retrieve(
                    request=request,
                    top_k=top_k,
                    fetch_k=fetch_k,
                    year=year,
                    report_type=report_type
                )
            else:
                # Use the tool as fallback
                context = self.execute_tool(
                    "retrieve_report_context",
                    request=request,
                    top_k=top_k,
                    fetch_k=fetch_k,
                    year=year,
                    report_type=report_type
                )
            
            # Parse result if it's a string
            if isinstance(context, str):
                try:
                    import json
                    context = json.loads(context)
                except Exception:
                    context = {'context': context}
            
            return {
                'status': 'success',
                'context': context,
                'request': request,
                'question': question,
                'audience': audience,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Failed to retrieve context: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'request': request,
                'question': question,
                'audience': audience,
                'document_type': document_type
            }


class AudienceAdapter(UNHCRBaseAgent):
    """
    Specialist agent for adapting stories to specific audiences.
    
    This agent ensures stories are tailored to the target audience's
    tone, length, and structure requirements.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Audience Adapter agent."""
        kwargs.setdefault('role', 'Audience Adapter')
        kwargs.setdefault('goal', 'Adapt stories to specific audience requirements')
        
        super().__init__(**kwargs)
        self._register_tools()
    
    def _register_tools(self):
        """Register audience adaptation tools."""
        # This agent doesn't use external tools directly
        # It uses the configuration system
        self.tools = []
    
    def adapt_story(
        self,
        story: str,
        audience: str,
        document_type: str,
        question: str = ""
    ) -> Dict[str, Any]:
        """
        Adapt a story to a specific audience and document type.
        
        Args:
            story: The original story
            audience: Target audience
            document_type: Document type
            question: Original question (optional)
            
        Returns:
            Adapted story with audience-specific formatting
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        # Get configuration
        config = AudienceConfigManager.get_config(audience, document_type)
        audience_config = config.get('config', {})
        
        try:
            # Apply audience-specific adaptations
            adapted_story = self._apply_audience_adaptations(
                story, audience, audience_config, document_type
            )
            
            return {
                'status': 'success',
                'original_story': story,
                'adapted_story': adapted_story,
                'audience': audience,
                'document_type': document_type,
                'tone': audience_config.get('tone', 'formal'),
                'length': audience_config.get('length', {}),
                'structure': audience_config.get('structure', [])
            }
            
        except Exception as e:
            logger.error(f"Failed to adapt story: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'original_story': story,
                'audience': audience,
                'document_type': document_type
            }
    
    def _apply_audience_adaptations(
        self,
        story: str,
        audience: str,
        config: Dict[str, Any],
        document_type: str
    ) -> str:
        """
        Apply audience-specific adaptations to a story.
        
        Args:
            story: The original story
            audience: Target audience
            config: Audience configuration
            document_type: Document type
            
        Returns:
            Adapted story
        """
        # This is a placeholder for the actual adaptation logic
        # In a full implementation, this would use LLM to adapt the story
        
        # For now, we'll just add audience-specific metadata
        tone = config.get('tone', 'formal')
        structure = config.get('structure', [])
        
        # Add header with audience information
        adapted_story = f"""---
Audience: {audience}
Document Type: {document_type}
Tone: {tone}
---

{story}"""
        
        return adapted_story
