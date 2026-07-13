"""
Analyst Agents for UNHCR Statistics Copilot

These agents perform analysis operations including statistical analysis,
compliance validation, and visualization.
"""

import logging
from typing import Any, Dict, List, Optional

from backend.crewai.agents.base import UNHCRBaseAgent
from backend.crewai.config import CrewAIConfig, AudienceConfigManager
from backend.crewai.tools.adapters import MCPToolAdapter

logger = logging.getLogger(__name__)


class StatisticalAnalyzer(UNHCRBaseAgent):
    """
    Specialist agent for statistical analysis of UNHCR data.
    
    This agent performs comprehensive statistical analysis including
    descriptive statistics, correlations, and distributions.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Statistical Analyst agent."""
        kwargs.setdefault('role', 'Statistical Analyst')
        kwargs.setdefault('goal', 'Perform comprehensive statistical analysis on displacement data')
        
        super().__init__(**kwargs)
        self._register_tools()
    
    def _register_tools(self):
        """Register statistical analysis tools."""
        try:
            from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
            from backend.mcp.tools.semantic_constants import is_identifier_field
            
            tools = []
            
            # Adapt the analyze_data_statistics tool
            tool = MCPToolAdapter.adapt_mcp_tool(
                analyze_data_statistics_tool,
                name="analyze_data_statistics",
                description=(
                    "Perform statistical analysis on datasets including descriptive statistics, "
                    "correlations, and distributions. Use this tool when asked for data analysis, "
                    "statistical summaries, or insights from numerical data."
                )
            )
            tools.append(tool)
            self.register_tool("analyze_data_statistics", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for StatisticalAnalyzer: {e}")
            self.tools = []
    
    def analyze_data(
        self,
        data: List[Dict[str, Any]],
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        Perform statistical analysis on the provided data.
        
        Args:
            data: List of data items to analyze
            audience: Target audience for the analysis
            document_type: Document type for the analysis
            
        Returns:
            Statistical analysis results with metadata
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        # Get configuration for audience
        config = AudienceConfigManager.get_config(audience, document_type)
        
        try:
            # Prepare data for analysis
            if not data or not isinstance(data, list):
                return {
                    'status': 'error',
                    'error': 'No valid data provided for analysis',
                    'audience': audience,
                    'document_type': document_type
                }
            
            # Identify numeric and categorical columns
            if data and len(data) > 0 and isinstance(data[0], dict):
                numeric_cols = []
                categorical_cols = []
                
                for key, value in data[0].items():
                    if isinstance(value, (int, float)):
                        # Skip identifier fields
                        if not (is_identifier_field(key) or any(
                            skip in key.lower() 
                            for skip in ['iso', 'hst', 'ooc', 'oip', 'id']
                        )):
                            numeric_cols.append(key)
                    elif isinstance(value, str):
                        # Include categorical columns that are likely dimensions
                        if any(cat in key.lower() for cat in ['year', 'coo', 'coa', 'name', 'country']):
                            categorical_cols.append(key)
                
                # Execute the analysis
                result = self.execute_tool(
                    "analyze_data_statistics",
                    data=data,
                    numeric_columns=numeric_cols,
                    categorical_columns=categorical_cols if categorical_cols else None,
                    correlation_columns=numeric_cols[:3] if len(numeric_cols) >= 3 else None
                )
                
                return {
                    'status': 'success',
                    'analysis': result,
                    'data_summary': {
                        'rows': len(data),
                        'numeric_columns': numeric_cols,
                        'categorical_columns': categorical_cols
                    },
                    'audience': audience,
                    'document_type': document_type,
                    'config': config
                }
            else:
                return {
                    'status': 'error',
                    'error': 'Invalid data format for analysis',
                    'audience': audience,
                    'document_type': document_type
                }
            
        except Exception as e:
            logger.error(f"Failed to analyze data: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'audience': audience,
                'document_type': document_type
            }
    
    def analyze_statistics(
        self,
        data: List[Dict[str, Any]],
        question: str = None,
        audience: str = "internal",
        document_type: str = "technical_report",
        **kwargs
    ) -> Dict[str, Any]:
        """Analyze statistics (alias for analyze_data)."""
        return self.analyze_data(
            data=data,
            audience=audience,
            document_type=document_type
        )
    
    def validate_guardrails(
        self,
        data: Any = None,
        analysis: Any = None,
        question: str = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Validate guardrails - StatisticalAnalyzer returns a basic validation."""
        # StatisticalAnalyzer doesn't perform guardrails validation
        # This is a placeholder that returns success
        return {
            'status': 'success',
            'valid': True,
            'issues': [],
            'warnings': [],
            'data': data,
            'analysis': analysis,
            'question': question,
            'audience': audience,
            'document_type': document_type
        }


class GuardrailsValidator(UNHCRBaseAgent):
    """
    Specialist agent for UNHCR methodology guardrails validation.
    
    This agent ensures all analyses follow UNHCR methodology standards
    and international guidelines.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Guardrails Validator agent."""
        kwargs.setdefault('role', 'Guardrails Validator')
        kwargs.setdefault('goal', 'Ensure analyses follow UNHCR methodology standards')
        
        super().__init__(**kwargs)
        self._register_tools()
    
    def _register_tools(self):
        """Register guardrails validation tools."""
        try:
            from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
            
            tools = []
            
            # Adapt the guardrails tool
            tool = MCPToolAdapter.adapt_mcp_tool(
                apply_analysis_guardrails_tool,
                name="apply_analysis_guardrails",
                description=(
                    "Apply UNHCR methodology guardrails to ensure analyses follow international standards. "
                    "Use this tool to validate analysis requests, check compliance with statistical standards, "
                    "and ensure proper interpretation of UNHCR data."
                )
            )
            tools.append(tool)
            self.register_tool("apply_analysis_guardrails", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for GuardrailsValidator: {e}")
            self.tools = []
    
    def validate_analysis(
        self,
        analysis_request: Dict[str, Any],
        data: Optional[Dict[str, Any]] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        Validate an analysis request against UNHCR methodology standards.
        
        Args:
            analysis_request: The analysis request to validate
            data: Optional data that has been retrieved
            audience: Target audience for the analysis
            document_type: Document type for the analysis
            
        Returns:
            Validation results with compliance information
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        try:
            # Extract relevant information for validation
            population_type = analysis_request.get('population_type')
            country_iso = analysis_request.get('country_iso')
            year = analysis_request.get('year')
            context = analysis_request.get('context', '')
            
            # Get data fields if data is provided
            data_fields = []
            if data and isinstance(data, dict):
                if 'items' in data and isinstance(data['items'], list) and len(data['items']) > 0:
                    data_fields = list(data['items'][0].keys()) if isinstance(data['items'][0], dict) else []
                elif isinstance(data, list) and len(data) > 0 and isinstance(data[0], dict):
                    data_fields = list(data[0].keys())
            
            # Execute validation
            result = self.execute_tool(
                "apply_analysis_guardrails",
                analysis_request=analysis_request,
                population_type=population_type,
                country_iso=country_iso,
                year=year,
                detailed_report=True
            )
            
            return {
                'status': 'success',
                'validation': result,
                'compliance_score': result.get('compliance_percentage', 0),
                'issues': result.get('issues', []),
                'warnings': result.get('warnings', []),
                'audience': audience,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Failed to validate analysis: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'audience': audience,
                'document_type': document_type,
                'compliance_score': 0
            }
    
    def validate_guardrails(
        self,
        data: Optional[Dict[str, Any]] = None,
        analysis: Optional[Dict[str, Any]] = None,
        question: str = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Validate guardrails (alias for validate_analysis)."""
        # Build analysis_request from parameters
        analysis_request = analysis or {}
        if question:
            analysis_request['question'] = question
        
        return self.validate_analysis(
            analysis_request=analysis_request,
            data=data,
            audience=audience,
            document_type=document_type
        )


class ToolSelector(UNHCRBaseAgent):
    """
    Specialist agent for selecting appropriate tools for analysis.
    
    This agent determines which UNHCR data tools should be used for specific queries.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Tool Selector agent."""
        kwargs.setdefault('role', 'Tool Selector')
        kwargs.setdefault('goal', 'Determine the appropriate UNHCR data tools for specific queries')
        
        super().__init__(**kwargs)
        self._register_tools()
    
    def _register_tools(self):
        """Register tool selection tools."""
        try:
            from backend.mcp.tools.safe_tool_selection import safe_tool_selection_tool
            
            tools = []
            
            # Adapt the tool selection tool
            tool = MCPToolAdapter.adapt_mcp_tool(
                safe_tool_selection_tool,
                name="safe_tool_selection",
                description=(
                    "Safely select the appropriate tool for a given question by analyzing its content. "
                    "Use this tool to determine which UNHCR data tool should be used for a specific query."
                )
            )
            tools.append(tool)
            self.register_tool("safe_tool_selection", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for ToolSelector: {e}")
            self.tools = []
    
    def select_tools(
        self,
        question: str,
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        Select appropriate tools for a given question.
        
        Args:
            question: The user's question
            audience: Target audience for the analysis
            document_type: Document type for the analysis
            
        Returns:
            Tool selection results with recommended tools and parameters
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        try:
            # Execute tool selection
            result = self.execute_tool("safe_tool_selection", question=question)
            
            # Parse the result
            if isinstance(result, str):
                try:
                    import json
                    result = json.loads(result)
                except Exception:
                    result = {'tool': result}
            
            return {
                'status': 'success',
                'selection': result,
                'question': question,
                'audience': audience,
                'document_type': document_type
            }
            
        except Exception as e:
            logger.error(f"Failed to select tools: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': question,
                'audience': audience,
                'document_type': document_type
            }


class VisualizationExpert(UNHCRBaseAgent):
    """
    Specialist agent for visualization structure and description.
    
    This agent extracts visualization metadata and generates descriptions
    for charts and graphs.
    """
    
    def __init__(self, **kwargs):
        """Initialize the Visualization Expert agent."""
        kwargs.setdefault('role', 'Visualization Expert')
        kwargs.setdefault('goal', 'Extract visualization metadata and generate descriptions')
        
        super().__init__(**kwargs)
        self._register_tools()
    
    def _register_tools(self):
        """Register visualization tools."""
        try:
            from backend.mcp.tools.extract_visualization_structure import extract_visualization_structure_tool
            from backend.mcp.tools.generate_visualization_description import generate_visualization_description_tool
            
            tools = []
            
            # Adapt extract_visualization_structure
            tool = MCPToolAdapter.adapt_mcp_tool(
                extract_visualization_structure_tool,
                name="extract_visualization_structure",
                description=(
                    "Extract and structure visualization metadata for AI-generated reports. "
                    "Use this tool when asked to create charts, graphs, or visual representations "
                    "of data for reporting purposes."
                )
            )
            tools.append(tool)
            self.register_tool("extract_visualization_structure", tool.function)
            
            # Adapt generate_visualization_description
            # Note: This is async, so we need special handling
            import inspect
            if inspect.iscoroutinefunction(generate_visualization_description_tool):
                async def async_wrapper(*args, **kwargs):
                    return await generate_visualization_description_tool(*args, **kwargs)
                tool = MCPToolAdapter.adapt_mcp_tool(
                    async_wrapper,
                    name="generate_visualization_description",
                    description=(
                        "Generate AI-powered descriptions and interpretations for visualizations. "
                        "Use this tool when asked to explain charts, provide insights from graphs, "
                        "or create narrative descriptions of data visualizations."
                    )
                )
            else:
                tool = MCPToolAdapter.adapt_mcp_tool(
                    generate_visualization_description_tool,
                    name="generate_visualization_description",
                    description=(
                        "Generate AI-powered descriptions and interpretations for visualizations. "
                        "Use this tool when asked to explain charts, provide insights from graphs, "
                        "or create narrative descriptions of data visualizations."
                    )
                )
            tools.append(tool)
            self.register_tool("generate_visualization_description", tool.function)
            
            self.tools = tools
            
        except Exception as e:
            logger.error(f"Error registering tools for VisualizationExpert: {e}")
            self.tools = []
    
    def extract_visualization(
        self,
        data: Dict[str, Any],
        visualization_type: str = "line_chart",
        audience: str = "internal",
        document_type: str = "technical_report"
    ) -> Dict[str, Any]:
        """
        Extract visualization structure and description from data.
        
        Args:
            data: The data to visualize
            visualization_type: Type of visualization (default: line_chart)
            audience: Target audience for the analysis
            document_type: Document type for the analysis
            
        Returns:
            Visualization structure and description
        """
        # Validate audience and document type
        audience = AudienceConfigManager.validate_audience(audience)
        document_type = AudienceConfigManager.validate_document_type(audience, document_type)
        
        try:
            # Detect visualization type and labels from data
            if data and isinstance(data, dict):
                items = data.get('items', [])
                if items and isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
                    # Auto-detect visualization type
                    viz_type = visualization_type
                    
                    # Try to detect axis labels from data
                    x_label = "Year"
                    y_label = "Count"
                    title = f"Analysis: {audience} - {document_type}"
                    
                    # Look for year/time fields
                    for key in items[0].keys():
                        if 'year' in key.lower():
                            x_label = key
                            break
                    
                    # Look for numeric value fields (excluding IDs)
                    for key in items[0].keys():
                        if isinstance(items[0][key], (int, float)) and 'year' not in key.lower():
                            if not any(skip in key.lower() for skip in ['id', '_id', 'iso', 'hst', 'ooc', 'oip']):
                                y_label = key
                                break
                    
                    # Extract visualization structure
                    structure = self.execute_tool(
                        "extract_visualization_structure",
                        visualization_type=viz_type,
                        title=title,
                        x_axis_label=x_label,
                        y_axis_label=y_label
                    )
                    
                    # Generate visualization description
                    description = self.execute_tool(
                        "generate_visualization_description",
                        structure=structure,
                        description_type="detailed",
                        max_length=500,
                        focus_areas=["trends", "comparisons", "outliers"]
                    )
                    
                    return {
                        'status': 'success',
                        'structure': structure,
                        'description': description,
                        'visualization_type': viz_type,
                        'labels': {
                            'title': title,
                            'x': x_label,
                            'y': y_label
                        },
                        'audience': audience,
                        'document_type': document_type
                    }
                else:
                    return {
                        'status': 'error',
                        'error': 'Invalid data format for visualization',
                        'audience': audience,
                        'document_type': document_type
                    }
            else:
                return {
                    'status': 'error',
                    'error': 'No data provided for visualization',
                    'audience': audience,
                    'document_type': document_type
                }
            
        except Exception as e:
            logger.error(f"Failed to extract visualization: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'audience': audience,
                'document_type': document_type
            }
    
    def extract_visualization_structure(
        self,
        data: Dict[str, Any],
        analysis: Dict[str, Any] = None,
        question: str = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Extract visualization structure (alias for extract_visualization)."""
        return self.extract_visualization(
            data=data,
            audience=audience,
            document_type=document_type
        )
    
    def generate_visualization_description(
        self,
        data: Dict[str, Any],
        analysis: Dict[str, Any] = None,
        question: str = None,
        audience: str = "internal",
        document_type: str = None,
        **kwargs
    ) -> Dict[str, Any]:
        """Generate visualization description using the MCP tool directly."""
        try:
            # Execute the generate_visualization_description tool directly
            result = self.execute_tool(
                "generate_visualization_description",
                data=data,
                analysis=analysis or {},
                question=question or "",
                description_type="detailed",
                max_length=500
            )
            
            return {
                'status': 'success',
                'description': result,
                'audience': audience,
                'document_type': document_type
            }
        except Exception as e:
            logger.error(f"Failed to generate visualization description: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'audience': audience,
                'document_type': document_type
            }
