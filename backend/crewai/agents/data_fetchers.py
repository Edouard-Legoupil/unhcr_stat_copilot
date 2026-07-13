"""
Data Fetcher Agents for UNHCR Statistics Copilot

These agents are responsible for fetching data from various UNHCR sources
and provide the foundation for all data-driven analysis.
"""

import logging
from typing import Any, Dict, List, Optional, Union

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.config import CrewAIConfig, AudienceConfigManager
from backend.crewai.tools.adapters import MCPToolAdapter

logger = logging.getLogger(__name__)


class UNHCRDataFetcher(UNHCRBaseAgent):
    """
    Specialist agent for fetching UNHCR population data.
    
    This agent handles all data retrieval operations from the UNHCR API,
    including population statistics, demographics, and key figures.
    """
    
    def __init__(self, **kwargs):
        """
        Initialize the UNHCR Data Fetcher agent.
        
        Args:
            **kwargs: Additional agent parameters
        """
        # Set default role if not provided
        kwargs.setdefault('role', 'UNHCR Data Fetcher')
        kwargs.setdefault('goal', 'Retrieve accurate population statistics from UNHCR API')
        
        super().__init__(**kwargs)
        
        # Initialize API client
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
            logger.info("UNHCRAPIClient initialized successfully")
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient: {e}")
            self.api_client = None
        
        # Register tools
        self._register_tools()
    
    def _register_tools(self):
        """Register all data fetching tools with the agent."""
        try:
            # Import MCP tools
            from backend.mcp.tools.get_population_data import get_population_data_tool
            from backend.mcp.tools.get_demographics_data import get_demographics_data_tool
            from backend.mcp.tools.get_country_key_figures import get_country_key_figures_tool
            from backend.mcp.tools.get_population_trends import get_population_trends_tool
            from backend.mcp.tools.get_demographic_breakdown import get_demographic_breakdown_tool
            
            # Adapt and register tools
            tools = []
            
            # get_population_data
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda **kwargs: 
                        get_population_data_tool(
                            self.api_client,
                            coo=kwargs.get('coo'),
                            coa=kwargs.get('coa'),
                            year=kwargs.get('year'),
                            coo_all=kwargs.get('coo_all', False),
                            coa_all=kwargs.get('coa_all', False)
                        ),
                    name="get_population_data",
                    description=(
                        "Retrieve forcibly displaced population statistics from UNHCR. "
                        "Use when asked about refugee numbers, asylum seekers, stateless persons, "
                        "or other populations of concern by country and year."
                    )
                )
                tools.append(tool)
                self.register_tool("get_population_data", tool.function)
            
            # get_demographics_data
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coo, coa, year, coo_all, coa_all, pop_type: 
                        get_demographics_data_tool(self.api_client, coo, coa, year, coo_all, coa_all, pop_type),
                    name="get_demographics_data",
                    description=(
                        "Retrieve age and sex breakdown data for forcibly displaced populations. "
                        "Use when asked about demographic composition, gender distribution, "
                        "or age groups of refugees and other populations of concern."
                    )
                )
                tools.append(tool)
                self.register_tool("get_demographics_data", tool.function)
            
            # get_country_key_figures
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coa, coo, year, population_types: 
                        get_country_key_figures_tool(self.api_client, coa, coo, year, population_types),
                    name="get_country_key_figures",
                    description=(
                        "Retrieve formatted key statistics and summaries for specific countries. "
                        "Use when asked for country profiles, overview statistics, "
                        "or formatted summaries of displacement situations."
                    )
                )
                tools.append(tool)
                self.register_tool("get_country_key_figures", tool.function)
            
            # get_population_trends
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda **kwargs: 
                        get_population_trends_tool(
                            self.api_client,
                            coa=kwargs.get('coa'),
                            coo=kwargs.get('coo'),
                            years=kwargs.get('years'),
                            population_types=kwargs.get('population_types')
                        ),
                    name="get_population_trends",
                    description=(
                        "Retrieve time series data showing population changes over multiple years. "
                        "Use when asked about trends, historical changes, or comparisons "
                        "across different time periods."
                    )
                )
                tools.append(tool)
                self.register_tool("get_population_trends", tool.function)
            
            # get_demographic_breakdown
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coa, coo, year, population_type: 
                        get_demographic_breakdown_tool(self.api_client, coa, coo, year, population_type),
                    name="get_demographic_breakdown",
                    description=(
                        "Retrieve detailed age and sex distribution for specific population types. "
                        "Use when asked for granular demographic analysis, age pyramids, "
                        "or gender breakdowns of refugee populations."
                    )
                )
                tools.append(tool)
                self.register_tool("get_demographic_breakdown", tool.function)
            
            # Set the agent's tools
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for UNHCRDataFetcher: {e}")
            # Fallback to empty tools list
            self.tools = []
    
    def fetch_population_data(
        self,
        question: str,
        parameters: Dict[str, Any],
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        High-level method to fetch population data based on a question.
        
        Args:
            question: The user's question
            parameters: Extracted parameters (coo, coa, year, etc.)
            audience: Target audience for the analysis
            document_type: Document type for the analysis
            
        Returns:
            Population data with metadata
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        # Extract parameters
        coo = parameters.get('coo')
        coa = parameters.get('coa')
        year = parameters.get('year')
        years = parameters.get('years')
        population_types = parameters.get('population_types')
        coo_all = parameters.get('coo_all', False)
        coa_all = parameters.get('coa_all', False)
        
        # Build arguments for tool call
        args = {
            'coo': coo,
            'coa': coa,
            'year': year,
            'years': years,
            'population_types': population_types,
            'coo_all': coo_all,
            'coa_all': coa_all
        }
        
        # Filter out None values
        args = {k: v for k, v in args.items() if v is not None}
        
        try:
            # Call the appropriate tool based on parameters
            if years or (coo and coa):
                # Use get_population_trends for multi-year or comparison queries
                result = self.execute_tool("get_population_trends", **args)
                tool_used = "get_population_trends"
            elif coo or coa or year:
                # Use get_population_data for basic queries
                result = self.execute_tool("get_population_data", **args)
                tool_used = "get_population_data"
            else:
                # Default to all data
                result = self.execute_tool("get_population_data")
                tool_used = "get_population_data"
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters,
                'tool': tool_used,
                'audience': audience,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch population data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters,
                'tool': 'get_population_data',
                'audience': audience,
                'document_type': document_type
            }


class RSDExpert(UNHCRBaseAgent):
    """
    Specialist agent for Refugee Status Determination (RSD) data.
    
    This agent handles data related to asylum applications, decisions, and outcomes.
    """
    
    def __init__(self, **kwargs):
        """Initialize the RSD Expert agent."""
        kwargs.setdefault('role', 'RSD Expert')
        kwargs.setdefault('goal', 'Retrieve and analyze RSD application and decision data')
        
        super().__init__(**kwargs)
        
        # Initialize API client
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient for RSDExpert: {e}")
            self.api_client = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register RSD-specific tools."""
        try:
            from backend.mcp.tools.get_rsd_applications import get_rsd_applications_tool
            from backend.mcp.tools.get_rsd_decisions import get_rsd_decisions_tool
            
            tools = []
            
            # get_rsd_applications
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coo, coa, year, coo_all, coa_all: 
                        get_rsd_applications_tool(self.api_client, coo, coa, year, coo_all, coa_all),
                    name="get_rsd_applications",
                    description=(
                        "Retrieve Refugee Status Determination (RSD) application statistics. "
                        "Use when asked about asylum applications, claims, or requests for refugee status "
                        "by country, origin, or year."
                    )
                )
                tools.append(tool)
                self.register_tool("get_rsd_applications", tool.function)
            
            # get_rsd_decisions
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coo, coa, year, coo_all, coa_all: 
                        get_rsd_decisions_tool(self.api_client, coo, coa, year, coo_all, coa_all),
                    name="get_rsd_decisions",
                    description=(
                        "Retrieve Refugee Status Determination (RSD) decision outcomes. "
                        "Use when asked about approved/rejected asylum cases, recognition rates, "
                        "or refugee status determination results by country and year."
                    )
                )
                tools.append(tool)
                self.register_tool("get_rsd_decisions", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for RSDExpert: {e}")
            self.tools = []
    
    def fetch_rsd_data(
        self,
        question: str,
        parameters: Dict[str, Any],
        audience: str = "internal"
    ) -> Dict[str, Any]:
        """
        Fetch RSD data based on question and parameters.
        
        Args:
            question: The user's question
            parameters: Extracted parameters
            audience: Target audience
            
        Returns:
            RSD data with metadata
        """
        # Extract parameters
        coo = parameters.get('coo')
        coa = parameters.get('coa')
        year = parameters.get('year')
        coo_all = parameters.get('coo_all', False)
        coa_all = parameters.get('coa_all', False)
        
        # Determine which tool to use based on question
        question_lower = question.lower()
        
        try:
            if 'decision' in question_lower or 'outcome' in question_lower or 'approved' in question_lower:
                result = self.execute_tool(
                    "get_rsd_decisions",
                    coo=coo,
                    coa=coa,
                    year=year,
                    coo_all=coo_all,
                    coa_all=coa_all
                )
                tool_used = "get_rsd_decisions"
            else:
                result = self.execute_tool(
                    "get_rsd_applications",
                    coo=coo,
                    coa=coa,
                    year=year,
                    coo_all=coo_all,
                    coa_all=coa_all
                )
                tool_used = "get_rsd_applications"
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters,
                'tool': tool_used,
                'data_type': 'rsd'
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch RSD data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters,
                'tool': 'get_rsd_applications',
                'data_type': 'rsd'
            }
    
    def fetch_rsd_applications(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch RSD applications data (wrapper for fetch_rsd_data)."""
        return self.fetch_rsd_data(
            question=question,
            parameters=parameters or {},
            audience=audience
        )
    
    def fetch_rsd_decisions(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch RSD decisions data (wrapper for fetch_rsd_data)."""
        params = parameters or {}
        # Add decision-specific keywords to trigger decision tool
        if 'question' not in params:
            params['question'] = question + " decisions"
        return self.fetch_rsd_data(
            question=question,
            parameters=params,
            audience=audience
        )


class SolutionsExpert(UNHCRBaseAgent):
    """
    Specialist agent for durable solutions data.
    
    This agent handles data related to solutions to displacement including
    voluntary repatriation, resettlement, naturalization, and IDP returns.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Solutions Expert agent."""
        kwargs.setdefault('role', 'Solutions Expert')
        kwargs.setdefault('goal', 'Retrieve data on durable solutions to displacement')
        
        super().__init__(**kwargs)
        
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient for SolutionsExpert: {e}")
            self.api_client = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register solutions-specific tools."""
        try:
            from backend.mcp.tools.get_solutions import get_solutions_tool
            
            tools = []
            
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coo, coa, year, coo_all, coa_all: 
                        get_solutions_tool(self.api_client, coo, coa, year, coo_all, coa_all),
                    name="get_solutions",
                    description=(
                        "Retrieve durable solutions data including refugee returnees, resettlement, "
                        "naturalization, and IDP returns. Use when asked about solutions "
                        "to displacement, voluntary repatriation, or integration outcomes."
                    )
                )
                tools.append(tool)
                self.register_tool("get_solutions", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for SolutionsExpert: {e}")
            self.tools = []
    
    def fetch_solutions_data(
        self,
        question: str,
        parameters: Dict[str, Any],
        audience: str = "internal"
    ) -> Dict[str, Any]:
        """
        Fetch solutions data based on question and parameters.
        
        Args:
            question: The user's question
            parameters: Extracted parameters
            audience: Target audience
            
        Returns:
            Solutions data with metadata
        """
        # Extract parameters
        coo = parameters.get('coo')
        coa = parameters.get('coa')
        year = parameters.get('year')
        coo_all = parameters.get('coo_all', False)
        coa_all = parameters.get('coa_all', False)
        
        try:
            result = self.execute_tool(
                "get_solutions",
                coo=coo,
                coa=coa,
                year=year,
                coo_all=coo_all,
                coa_all=coa_all
            )
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters,
                'tool': 'get_solutions',
                'data_type': 'solutions'
            }
            
        except Exception as e:
            logger.error(f"Failed to fetch solutions data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters,
                'tool': 'get_solutions',
                'data_type': 'solutions'
            }
    
    def fetch_solutions(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch solutions data (wrapper for fetch_solutions_data)."""
        return self.fetch_solutions_data(
            question=question,
            parameters=parameters or {},
            audience=audience
        )


class DemographicsExpert(UNHCRBaseAgent):
    """
    Specialist agent for demographic breakdown data.
    
    This agent handles age and gender breakdown data for displaced populations.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Demographics Expert agent."""
        kwargs.setdefault('role', 'Demographics Expert')
        kwargs.setdefault('goal', 'Retrieve and analyze demographic breakdown data')
        
        super().__init__(**kwargs)
        
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient for DemographicsExpert: {e}")
            self.api_client = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register demographics-specific tools."""
        try:
            from backend.mcp.tools.get_demographics_data import get_demographics_data_tool
            from backend.mcp.tools.get_demographic_breakdown import get_demographic_breakdown_tool
            
            tools = []
            
            # get_demographics_data
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coo, coa, year, coo_all, coa_all, pop_type: 
                        get_demographics_data_tool(self.api_client, coo, coa, year, coo_all, coa_all, pop_type),
                    name="get_demographics_data",
                    description=(
                        "Retrieve age and sex breakdown data for forcibly displaced populations. "
                        "Use when asked about demographic composition or gender distribution."
                    )
                )
                tools.append(tool)
                self.register_tool("get_demographics_data", tool.function)
            
            # get_demographic_breakdown
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coa, coo, year, population_type: 
                        get_demographic_breakdown_tool(self.api_client, coa, coo, year, population_type),
                    name="get_demographic_breakdown",
                    description=(
                        "Retrieve detailed age and sex distribution for specific population types. "
                        "Use for granular demographic analysis, age pyramids, or gender breakdowns."
                    )
                )
                tools.append(tool)
                self.register_tool("get_demographic_breakdown", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for DemographicsExpert: {e}")
            self.tools = []
    
    def fetch_demographics(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch demographic breakdown data."""
        # Extract parameters
        coo = parameters.get('coo') if parameters else None
        coa = parameters.get('coa') if parameters else None
        year = parameters.get('year') if parameters else None
        coo_all = parameters.get('coo_all', False) if parameters else False
        coa_all = parameters.get('coa_all', False) if parameters else False
        pop_type = parameters.get('pop_type') if parameters else None
        
        try:
            result = self.execute_tool(
                "get_demographics_data",
                coo=coo,
                coa=coa,
                year=year,
                coo_all=coo_all,
                coa_all=coa_all,
                pop_type=pop_type
            )
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_demographics_data',
                'data_type': 'demographics'
            }
        except Exception as e:
            logger.error(f"Failed to fetch demographics data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_demographics_data',
                'data_type': 'demographics'
            }
    
    def fetch_breakdown(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch demographic breakdown data (alternative method)."""
        return self.fetch_demographics(
            question=question,
            parameters=parameters,
            audience=audience,
            document_type=document_type,
            **kwargs
        )


class TemporalAnalyzer(UNHCRBaseAgent):
    """
    Specialist agent for temporal analysis and trends.
    
    This agent focuses on time-series data and trend analysis.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Temporal Analyzer agent."""
        kwargs.setdefault('role', 'Temporal Analyzer')
        kwargs.setdefault('goal', 'Analyze population trends over time')
        
        super().__init__(**kwargs)
        
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient for TemporalAnalyzer: {e}")
            self.api_client = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register temporal analysis tools."""
        try:
            from backend.mcp.tools.get_population_trends import get_population_trends_tool
            
            tools = []
            
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coa, coo, years, population_types: 
                        get_population_trends_tool(self.api_client, coa, coo, years, population_types),
                    name="get_population_trends",
                    description=(
                        "Retrieve time series data showing population changes over multiple years. "
                        "Use for trend analysis and historical comparisons."
                    )
                )
                tools.append(tool)
                self.register_tool("get_population_trends", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for TemporalAnalyzer: {e}")
            self.tools = []
    
    def fetch_trends(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch temporal trends data."""
        # Extract parameters
        coa = parameters.get('coa') if parameters else None
        coo = parameters.get('coo') if parameters else None
        years = parameters.get('years') if parameters else None
        population_types = parameters.get('population_types') if parameters else None
        
        try:
            result = self.execute_tool(
                "get_population_trends",
                coa=coa,
                coo=coo,
                years=years,
                population_types=population_types
            )
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_population_trends',
                'data_type': 'trends'
            }
        except Exception as e:
            logger.error(f"Failed to fetch trends data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_population_trends',
                'data_type': 'trends'
            }
    
    def fetch_population_data(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch population data (alias for fetch_trends for backward compatibility)."""
        return self.fetch_trends(
            question=question,
            parameters=parameters,
            audience=audience,
            document_type=document_type,
            **kwargs
        )


class GeographyExpert(UNHCRBaseAgent):
    """
    Specialist agent for geographic analysis.
    
    This agent handles country-specific data and geographic analysis.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Geography Expert agent."""
        kwargs.setdefault('role', 'Geography Expert')
        kwargs.setdefault('goal', 'Analyze displacement data by geography and country')
        
        super().__init__(**kwargs)
        
        try:
            from backend.mcp.common import UNHCRAPIClient
            self.api_client = UNHCRAPIClient()
        except Exception as e:
            logger.warning(f"Could not initialize UNHCRAPIClient for GeographyExpert: {e}")
            self.api_client = None
        
        self._register_tools()
    
    def _register_tools(self):
        """Register geography-specific tools."""
        try:
            from backend.mcp.tools.get_country_key_figures import get_country_key_figures_tool
            
            tools = []
            
            if self.api_client:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    lambda coa, coo, year, population_types: 
                        get_country_key_figures_tool(self.api_client, coa, coo, year, population_types),
                    name="get_country_key_figures",
                    description=(
                        "Retrieve formatted key statistics and summaries for specific countries. "
                        "Use for country profiles and geographic analysis."
                    )
                )
                tools.append(tool)
                self.register_tool("get_country_key_figures", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for GeographyExpert: {e}")
            self.tools = []
    
    def fetch_geography_data(
        self,
        question: str,
        parameters: Dict[str, Any] = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Fetch geographic/geography data."""
        # Extract parameters
        coa = parameters.get('coa') if parameters else None
        coo = parameters.get('coo') if parameters else None
        year = parameters.get('year') if parameters else None
        population_types = parameters.get('population_types') if parameters else None
        
        try:
            result = self.execute_tool(
                "get_country_key_figures",
                coa=coa,
                coo=coo,
                year=year,
                population_types=population_types
            )
            
            return {
                'status': 'success',
                'data': result,
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_country_key_figures',
                'data_type': 'geography'
            }
        except Exception as e:
            logger.error(f"Failed to fetch geography data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'parameters': parameters or {},
                'tool': 'get_country_key_figures',
                'data_type': 'geography'
            }
