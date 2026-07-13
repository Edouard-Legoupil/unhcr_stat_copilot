"""
Tests for CrewAI Integration

This module tests the integration between:
- CrewAI and MCP server
- CrewAI and FastAPI app
- CrewAI and existing tools
"""

import pytest
from unittest.mock import MagicMock, patch
from typing import Any, Dict

from backend.crewai.mcp_integration import (
    CrewAIToolAdapter,
    get_crewai_tools
)
from backend.crewai.manager import CrewAIManager, WorkflowType


class TestCrewAIToolAdapter:
    """Test CrewAIToolAdapter class."""
    
    def test_adapter_initialization(self):
        """Test adapter initialization."""
        adapter = CrewAIToolAdapter()
        
        assert adapter is not None
        assert adapter.manager is not None
    
    def test_get_manager(self):
        """Test get_manager method."""
        adapter = CrewAIToolAdapter()
        
        manager = adapter.get_manager()
        
        assert isinstance(manager, CrewAIManager)
    
    def test_get_tool_registry(self):
        """Test get_tool_registry method."""
        adapter = CrewAIToolAdapter()
        
        registry = adapter.get_tool_registry()
        
        assert isinstance(registry, dict)
        assert len(registry) > 0
        
        # Check for expected tools
        expected_tools = [
            'crewai_get_population_data',
            'crewai_fetch_all_data',
            'crewai_analyze_data_statistics',
            'crewai_generate_analytical_story',
            'crewai_create_quarto_notebook',
            'crewai_full_analysis_workflow',
            'crewai_execute_workflow'
        ]
        
        for tool in expected_tools:
            assert tool in registry, f"Tool {tool} not found in registry"


class TestCrewAIDataTools:
    """Test CrewAI data fetching tools."""
    
    def test_get_population_data_tool(self):
        """Test crewai_get_population_data_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_get_population_data_tool(
            coo="SYR",
            coa="FRA",
            year=2023
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_fetch_all_data_tool(self):
        """Test crewai_fetch_all_data_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_fetch_all_data_tool(
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result


class TestCrewAIAnalysisTools:
    """Test CrewAI analysis tools."""
    
    def test_analyze_data_statistics_tool(self):
        """Test crewai_analyze_data_statistics_tool."""
        adapter = CrewAIToolAdapter()
        
        test_data = {"test": "data"}
        result = adapter.crewai_analyze_data_statistics_tool(
            data=test_data,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_apply_analysis_guardrails_tool(self):
        """Test crewai_apply_analysis_guardrails_tool."""
        adapter = CrewAIToolAdapter()
        
        test_data = {"test": "data"}
        test_analysis = {"test": "analysis"}
        result = adapter.crewai_apply_analysis_guardrails_tool(
            data=test_data,
            analysis=test_analysis,
            question="Test question"
        )
        
        assert isinstance(result, dict)


class TestCrewAIStoryTools:
    """Test CrewAI story tools."""
    
    def test_generate_analytical_story_tool(self):
        """Test crewai_generate_analytical_story_tool."""
        adapter = CrewAIToolAdapter()
        
        test_data = {"test": "data"}
        result = adapter.crewai_generate_analytical_story_tool(
            data=test_data,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_get_data_for_story_tool(self):
        """Test crewai_get_data_for_story_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_get_data_for_story_tool(
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result


class TestCrewAINotebookTools:
    """Test CrewAI notebook tools."""
    
    def test_create_quarto_notebook_tool(self):
        """Test crewai_create_quarto_notebook_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_create_quarto_notebook_tool(
            story_content="Test story content"
        )
        
        assert isinstance(result, dict)
        assert "status" in result


class TestCrewAIWorkflowTools:
    """Test CrewAI workflow tools."""
    
    def test_full_analysis_workflow_tool(self):
        """Test crewai_full_analysis_workflow_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_full_analysis_workflow_tool(
            question="Test question",
            include_notebook=False
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_quick_analysis_tool(self):
        """Test crewai_quick_analysis_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_quick_analysis_tool(
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_compare_analysis_tool(self):
        """Test crewai_compare_analysis_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_compare_analysis_tool(
            question="Compare A and B"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_workflow_tool(self):
        """Test crewai_execute_workflow_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_execute_workflow_tool(
            question="Test question",
            workflow_type="full_analysis"
        )
        
        assert isinstance(result, dict)
        assert "status" in result


class TestCrewAIMetricsTools:
    """Test CrewAI metrics tools."""
    
    def test_get_metrics_tool(self):
        """Test crewai_get_metrics_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_get_metrics_tool()
        
        assert isinstance(result, dict)
        assert "total_workflows" in result
    
    def test_reset_metrics_tool(self):
        """Test crewai_reset_metrics_tool."""
        adapter = CrewAIToolAdapter()
        
        result = adapter.crewai_reset_metrics_tool()
        
        assert isinstance(result, dict)
        assert result["status"] == "success"


class TestGlobalAdapter:
    """Test global adapter instance."""
    
    def test_global_adapter(self):
        """Test global adapter instance."""
        adapter1 = CrewAIToolAdapter()
        
        # The adapter is created fresh each time, not a singleton
        # But we can test that it works
        assert adapter1 is not None
    
    def test_get_crewai_tools_function(self):
        """Test get_crewai_tools function."""
        tools = get_crewai_tools()
        
        assert isinstance(tools, dict)
        assert len(tools) > 0


class TestWorkflowTypeConversion:
    """Test workflow type conversion."""
    
    def test_string_to_workflow_type(self):
        """Test converting string to WorkflowType."""
        adapter = CrewAIToolAdapter()
        
        # This is tested in the execute_workflow_tool method
        result = adapter.crewai_execute_workflow_tool(
            question="Test question",
            workflow_type="full_analysis"
        )
        
        assert isinstance(result, dict)
    
    def test_invalid_workflow_type(self):
        """Test handling of invalid workflow type."""
        adapter = CrewAIToolAdapter()
        
        # Should default to FULL_ANALYSIS
        result = adapter.crewai_execute_workflow_tool(
            question="Test question",
            workflow_type="invalid_type"
        )
        
        assert isinstance(result, dict)


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
