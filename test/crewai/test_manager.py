"""
Tests for CrewAI Manager

This module tests the CrewAIManager class to ensure it:
- Initializes correctly
- Manages agents properly
- Executes workflows end-to-end
- Tracks metrics correctly
- Handles errors gracefully
"""

import pytest
import time
from typing import Any, Dict

from backend.crewai.manager import (
    CrewAIManager,
    WorkflowType,
    WorkflowStatus,
    WorkflowMetrics,
    AgentMetrics,
    ManagerMetrics,
    get_manager,
    reset_manager
)
from backend.crewai.crews import DataCrew, AnalysisCrew, StoryCrew, NotebookCrew, MasterCrew


class TestCrewAIManagerInitialization:
    """Test CrewAIManager initialization."""
    
    def test_manager_initialization(self):
        """Test basic manager initialization."""
        manager = CrewAIManager(initialize_agents=False)
        
        assert manager is not None
        assert manager._initialized == False
        assert len(manager._agents) == 0
    
    def test_manager_initialization_with_agents(self):
        """Test manager initialization with agents."""
        manager = CrewAIManager(initialize_agents=True)
        
        assert manager._initialized == True
        assert len(manager._agents) > 0
    
    def test_global_manager(self):
        """Test global manager singleton."""
        manager1 = get_manager()
        manager2 = get_manager()
        
        assert manager1 is manager2
    
    def test_reset_manager(self):
        """Test reset_manager function."""
        manager1 = get_manager()
        reset_manager()
        manager2 = get_manager()
        
        assert manager1 is not manager2


class TestCrewAIManagerAgents:
    """Test agent management in CrewAIManager."""
    
    def test_list_agents(self):
        """Test list_agents method."""
        manager = CrewAIManager(initialize_agents=True)
        
        agents = manager.list_agents()
        
        assert isinstance(agents, list)
        assert len(agents) > 0
    
    def test_get_agent(self):
        """Test get_agent method."""
        manager = CrewAIManager(initialize_agents=True)
        
        # Get a specific agent
        agent = manager.get_agent('data_fetcher')
        
        assert agent is not None
    
    def test_get_invalid_agent(self):
        """Test get_agent with invalid agent name."""
        manager = CrewAIManager(initialize_agents=True)
        
        with pytest.raises(ValueError):
            manager.get_agent('nonexistent_agent')
    
    def test_agent_references(self):
        """Test that agent references are set up correctly."""
        manager = CrewAIManager(initialize_agents=True)
        
        # Check that orchestrator has references to other agents
        orchestrator = manager.get_agent('analysis_orchestrator')
        
        assert orchestrator is not None


class TestCrewAIManagerWorkflows:
    """Test workflow execution in CrewAIManager."""
    
    def test_execute_full_workflow(self):
        """Test execute_workflow with FULL_ANALYSIS type."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.FULL_ANALYSIS,
            include_notebook=False
        )
        
        assert isinstance(result, dict)
        assert "status" in result
        assert "workflow_id" in result
        assert "metrics" in result
    
    def test_execute_quick_workflow(self):
        """Test execute_workflow with QUICK_ANALYSIS type."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.QUICK_ANALYSIS
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_data_only_workflow(self):
        """Test execute_workflow with DATA_ONLY type."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.DATA_ONLY
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_story_only_workflow(self):
        """Test execute_workflow with STORY_ONLY type."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.STORY_ONLY,
            use_rag=False
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_notebook_only_workflow(self):
        """Test execute_workflow with NOTEBOOK_ONLY type."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.NOTEBOOK_ONLY,
            story_content="Test story content"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_workflow_with_custom_parameters(self):
        """Test execute_workflow with custom parameters."""
        manager = CrewAIManager(initialize_agents=True)
        
        result = manager.execute_workflow(
            question="Test question about Syria",
            audience="public_donors",
            document_type="executive_summary",
            workflow_type=WorkflowType.FULL_ANALYSIS,
            use_rag=True,
            include_notebook=False,
            coo="SYR",
            year=2023
        )
        
        assert isinstance(result, dict)
        assert result.get("audience") == "public_donors"
        assert result.get("document_type") == "executive_summary"


class TestCrewAIManagerMetrics:
    """Test metrics tracking in CrewAIManager."""
    
    def test_metrics_initialization(self):
        """Test that metrics are initialized correctly."""
        manager = CrewAIManager(initialize_agents=False)
        
        metrics = manager.get_metrics()
        
        assert "total_workflows" in metrics
        assert "completed_workflows" in metrics
        assert "failed_workflows" in metrics
        assert "agent_count" in metrics
    
    def test_workflow_metrics_tracking(self):
        """Test that workflow metrics are tracked."""
        manager = CrewAIManager(initialize_agents=True)
        
        # Execute a workflow
        manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.DATA_ONLY
        )
        
        metrics = manager.get_metrics()
        
        assert metrics["total_workflows"] >= 1
    
    def test_reset_metrics(self):
        """Test reset_metrics method."""
        manager = CrewAIManager(initialize_agents=True)
        
        # Execute a workflow to generate some metrics
        manager.execute_workflow(
            question="Test question",
            workflow_type=WorkflowType.DATA_ONLY
        )
        
        # Reset metrics
        manager.reset_metrics()
        
        metrics = manager.get_metrics()
        
        assert metrics["total_workflows"] == 0
        assert metrics["completed_workflows"] == 0
        assert metrics["failed_workflows"] == 0


class TestWorkflowMetrics:
    """Test WorkflowMetrics dataclass."""
    
    def test_workflow_metrics_creation(self):
        """Test creating WorkflowMetrics."""
        from datetime import datetime
        
        metrics = WorkflowMetrics(
            workflow_id="test_123",
            workflow_type="full_analysis",
            start_time=datetime.now()
        )
        
        assert metrics.workflow_id == "test_123"
        assert metrics.workflow_type == "full_analysis"
        assert metrics.status == "pending"
    
    def test_workflow_metrics_to_dict(self):
        """Test converting WorkflowMetrics to dict."""
        from datetime import datetime
        
        metrics = WorkflowMetrics(
            workflow_id="test_123",
            workflow_type="full_analysis",
            start_time=datetime.now()
        )
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "workflow_id" in metrics_dict
        assert "workflow_type" in metrics_dict
        assert "start_time" in metrics_dict


class TestManagerMetrics:
    """Test ManagerMetrics dataclass."""
    
    def test_manager_metrics_creation(self):
        """Test creating ManagerMetrics."""
        metrics = ManagerMetrics()
        
        assert metrics.total_workflows == 0
        assert metrics.completed_workflows == 0
        assert metrics.failed_workflows == 0
        assert len(metrics.agent_metrics) == 0
    
    def test_manager_metrics_to_dict(self):
        """Test converting ManagerMetrics to dict."""
        metrics = ManagerMetrics()
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "total_workflows" in metrics_dict
        assert "completed_workflows" in metrics_dict


class TestAgentMetrics:
    """Test AgentMetrics dataclass."""
    
    def test_agent_metrics_creation(self):
        """Test creating AgentMetrics."""
        from datetime import datetime
        
        metrics = AgentMetrics(agent_name="test_agent")
        
        assert metrics.agent_name == "test_agent"
        assert metrics.execution_count == 0
        assert metrics.success_count == 0
        assert metrics.failure_count == 0
    
    def test_agent_metrics_to_dict(self):
        """Test converting AgentMetrics to dict."""
        metrics = AgentMetrics(agent_name="test_agent")
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "agent_name" in metrics_dict
        assert "execution_count" in metrics_dict


class TestCrewAIManagerShutdown:
    """Test manager shutdown."""
    
    def test_manager_shutdown(self):
        """Test manager shutdown."""
        manager = CrewAIManager(initialize_agents=True)
        
        # Shutdown should not raise an exception
        manager.shutdown()
        
        assert manager._initialized == False
        assert len(manager._agents) == 0
    
    def test_context_manager(self):
        """Test manager as context manager."""
        with CrewAIManager(initialize_agents=True) as manager:
            assert manager._initialized == True
            assert len(manager._agents) > 0
        
        # After exiting context, should be shut down
        assert manager._initialized == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
