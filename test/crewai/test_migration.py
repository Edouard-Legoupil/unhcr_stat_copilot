"""
Tests for CrewAI Migration Utilities

This module tests the migration utilities to ensure they:
- Load configuration correctly
- Route requests properly
- Track metrics accurately
- Handle errors gracefully
"""

import pytest
import os
from unittest.mock import MagicMock, patch
from typing import Any, Callable, Dict, Tuple

from backend.crewai.migration import (
    MigrationMode,
    RoutingStrategy,
    MigrationConfig,
    MigrationMetrics,
    MigrationRouter,
    get_migration_router,
    reset_migration_router,
    migration_context
)


class TestMigrationConfig:
    """Test MigrationConfig class."""
    
    def test_default_config(self):
        """Test default configuration values."""
        config = MigrationConfig()
        
        assert config.mode == MigrationMode.MCP_ONLY
        assert config.strategy == RoutingStrategy.RANDOM
        assert config.mcp_percentage == 100.0
        assert config.crewai_percentage == 0.0
        assert config.fallback_enabled == True
        assert config.track_metrics == True
    
    def test_from_env(self):
        """Test loading configuration from environment variables."""
        # Set environment variables
        env_vars = {
            "CREWAI_MIGRATION_MODE": "crewai_only",
            "CREWAI_ROUTING_STRATEGY": "percentage",
            "CREWAI_MCP_PERCENTAGE": "50.0",
            "CREWAI_CREWAI_PERCENTAGE": "50.0",
            "CREWAI_FALLBACK_ENABLED": "false",
            "CREWAI_TRACK_METRICS": "false"
        }
        
        with patch.dict(os.environ, env_vars):
            config = MigrationConfig.from_env()
            
            assert config.mode == MigrationMode.CREWAI_ONLY
            assert config.strategy == RoutingStrategy.PERCENTAGE
            assert config.mcp_percentage == 50.0
            assert config.crewai_percentage == 50.0
            assert config.fallback_enabled == False
            assert config.track_metrics == False
    
    def test_invalid_mode(self):
        """Test handling of invalid migration mode."""
        with patch.dict(os.environ, {"CREWAI_MIGRATION_MODE": "invalid_mode"}):
            config = MigrationConfig.from_env()
            
            # Should default to MCP_ONLY
            assert config.mode == MigrationMode.MCP_ONLY
    
    def test_normalize_percentages(self):
        """Test percentage normalization."""
        with patch.dict(os.environ, {
            "CREWAI_MCP_PERCENTAGE": "200.0",
            "CREWAI_CREWAI_PERCENTAGE": "100.0"
        }):
            config = MigrationConfig.from_env()
            
            # Should be normalized to 66.67 and 33.33
            assert abs(config.mcp_percentage - 66.67) < 0.01
            assert abs(config.crewai_percentage - 33.33) < 0.01


class TestMigrationMetrics:
    """Test MigrationMetrics class."""
    
    def test_default_metrics(self):
        """Test default metrics values."""
        metrics = MigrationMetrics()
        
        assert metrics.total_requests == 0
        assert metrics.mcp_requests == 0
        assert metrics.crewai_requests == 0
        assert metrics.mcp_successes == 0
        assert metrics.crewai_successes == 0
        assert metrics.avg_mcp_time == 0.0
        assert metrics.avg_crewai_time == 0.0
    
    def test_success_rates(self):
        """Test success rate calculations."""
        metrics = MigrationMetrics()
        
        # With no requests, success rate should be 0
        assert metrics.mcp_success_rate == 0.0
        assert metrics.crewai_success_rate == 0.0
        
        # With requests but no successes
        metrics.mcp_requests = 10
        metrics.mcp_failures = 10
        assert metrics.mcp_success_rate == 0.0
        
        # With some successes
        metrics.mcp_successes = 5
        assert metrics.mcp_success_rate == 50.0
    
    def test_to_dict(self):
        """Test converting metrics to dictionary."""
        metrics = MigrationMetrics()
        metrics.mcp_requests = 10
        metrics.crewai_requests = 5
        
        metrics_dict = metrics.to_dict()
        
        assert isinstance(metrics_dict, dict)
        assert "total_requests" in metrics_dict
        assert "mcp_requests" in metrics_dict
        assert "crewai_requests" in metrics_dict
        assert "mcp_success_rate" in metrics_dict
        assert "crewai_success_rate" in metrics_dict


class TestMigrationRouter:
    """Test MigrationRouter class."""
    
    def test_initialization(self):
        """Test router initialization."""
        config = MigrationConfig()
        router = MigrationRouter(config)
        
        assert router.config is config
        assert router.metrics is not None
        assert router._round_robin_index == 0
    
    def test_route_to_mcp(self):
        """Test routing to MCP."""
        config = MigrationConfig(mode=MigrationMode.MCP_ONLY)
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success", "result": "mcp_result"})
        crewai_func = MagicMock(return_value={"status": "success", "result": "crewai_result"})
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        assert source == "mcp"
        assert result["result"] == "mcp_result"
        assert router.metrics.mcp_requests == 1
    
    def test_route_to_crewai(self):
        """Test routing to CrewAI."""
        config = MigrationConfig(mode=MigrationMode.CREWAI_ONLY)
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success", "result": "mcp_result"})
        crewai_func = MagicMock(return_value={"status": "success", "result": "crewai_result"})
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        assert source == "crewai"
        assert result["result"] == "crewai_result"
        assert router.metrics.crewai_requests == 1
    
    def test_route_dual(self):
        """Test dual-run mode."""
        config = MigrationConfig(
            mode=MigrationMode.DUAL_RUN,
            dual_run_return="both"
        )
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success", "result": "mcp_result"})
        crewai_func = MagicMock(return_value={"status": "success", "result": "crewai_result"})
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        assert source == "dual"
        assert "mcp" in result
        assert "crewai" in result
        assert router.metrics.dual_run_requests == 1
    
    def test_route_fallback(self):
        """Test fallback mode."""
        config = MigrationConfig(
            mode=MigrationMode.FALLBACK,
            fallback_enabled=True
        )
        router = MigrationRouter(config)
        
        # CrewAI will fail
        crewai_func = MagicMock(side_effect=Exception("CrewAI error"))
        mcp_func = MagicMock(return_value={"status": "success", "result": "mcp_result"})
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        # Should have fallen back to MCP
        assert source == "mcp"
        assert result["result"] == "mcp_result"
        assert router.metrics.fallback_requests == 1
        assert metrics.get("fallback") == True
    
    def test_route_hybrid_percentage(self):
        """Test hybrid mode with percentage routing."""
        config = MigrationConfig(
            mode=MigrationMode.HYBRID,
            strategy=RoutingStrategy.PERCENTAGE,
            mcp_percentage=50.0,
            crewai_percentage=50.0
        )
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success", "result": "mcp_result"})
        crewai_func = MagicMock(return_value={"status": "success", "result": "crewai_result"})
        
        # Run multiple requests to test percentage distribution
        mcp_count = 0
        crewai_count = 0
        
        for _ in range(100):
            source, _, _ = router.route_request(
                tool_name="test_tool",
                parameters={},
                mcp_func=mcp_func,
                crewai_func=crewai_func
            )
            if source == "mcp":
                mcp_count += 1
            elif source == "crewai":
                crewai_count += 1
        
        # With 50/50 split, we should get roughly equal distribution
        assert 20 <= mcp_count <= 80
        assert 20 <= crewai_count <= 80
    
    def test_route_hybrid_tool_based(self):
        """Test hybrid mode with tool-based routing."""
        config = MigrationConfig(
            mode=MigrationMode.HYBRID,
            strategy=RoutingStrategy.TOOL_BASED,
            crewai_tools=["crewai_tool"],
            mcp_tools=["mcp_tool"]
        )
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success"})
        crewai_func = MagicMock(return_value={"status": "success"})
        
        # CrewAI tool should route to CrewAI
        source, _, _ = router.route_request(
            tool_name="crewai_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        assert source == "crewai"
        
        # MCP tool should route to MCP
        source, _, _ = router.route_request(
            tool_name="mcp_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        assert source == "mcp"
    
    def test_route_hybrid_audience_based(self):
        """Test hybrid mode with audience-based routing."""
        config = MigrationConfig(
            mode=MigrationMode.HYBRID,
            strategy=RoutingStrategy.AUDIENCE_BASED,
            crewai_audiences=["internal"],
            mcp_audiences=["public_donors"]
        )
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(return_value={"status": "success"})
        crewai_func = MagicMock(return_value={"status": "success"})
        
        # Internal audience should route to CrewAI
        source, _, _ = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func,
            audience="internal"
        )
        assert source == "crewai"
        
        # Public donors audience should route to MCP
        source, _, _ = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func,
            audience="public_donors"
        )
        assert source == "mcp"
    
    def test_error_handling_mcp(self):
        """Test error handling for MCP execution."""
        config = MigrationConfig(mode=MigrationMode.MCP_ONLY)
        router = MigrationRouter(config)
        
        mcp_func = MagicMock(side_effect=Exception("MCP error"))
        crewai_func = MagicMock()
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        assert source == "mcp"
        assert result["status"] == "error"
        assert router.metrics.mcp_failures == 1
    
    def test_error_handling_crewai(self):
        """Test error handling for CrewAI execution."""
        config = MigrationConfig(mode=MigrationMode.CREWAI_ONLY)
        router = MigrationRouter(config)
        
        mcp_func = MagicMock()
        crewai_func = MagicMock(side_effect=Exception("CrewAI error"))
        
        source, result, metrics = router.route_request(
            tool_name="test_tool",
            parameters={},
            mcp_func=mcp_func,
            crewai_func=crewai_func
        )
        
        assert source == "crewai"
        assert result["status"] == "error"
        assert router.metrics.crewai_failures == 1
    
    def test_get_metrics(self):
        """Test get_metrics method."""
        config = MigrationConfig()
        router = MigrationRouter(config)
        
        metrics = router.get_metrics()
        
        assert isinstance(metrics, dict)
        assert "total_requests" in metrics
        assert "config" in metrics
        assert metrics["config"]["mode"] == "mcp_only"
    
    def test_reset_metrics(self):
        """Test reset_metrics method."""
        config = MigrationConfig()
        router = MigrationRouter(config)
        
        # Generate some metrics
        mcp_func = MagicMock(return_value={"status": "success"})
        crewai_func = MagicMock(return_value={"status": "success"})
        
        router.route_request("test", {}, mcp_func, crewai_func)
        
        # Reset
        router.reset_metrics()
        
        metrics = router.get_metrics()
        assert metrics["total_requests"] == 0
    
    def test_set_mode(self):
        """Test set_mode method."""
        config = MigrationConfig()
        router = MigrationRouter(config)
        
        router.set_mode(MigrationMode.CREWAI_ONLY)
        assert router.config.mode == MigrationMode.CREWAI_ONLY
        
        router.set_mode("mcp_only")
        assert router.config.mode == MigrationMode.MCP_ONLY
    
    def test_set_strategy(self):
        """Test set_strategy method."""
        config = MigrationConfig()
        router = MigrationRouter(config)
        
        router.set_strategy(RoutingStrategy.PERCENTAGE)
        assert router.config.strategy == RoutingStrategy.PERCENTAGE
        
        router.set_strategy("tool_based")
        assert router.config.strategy == RoutingStrategy.TOOL_BASED


class TestGlobalRouter:
    """Test global router instance."""
    
    def test_global_router_singleton(self):
        """Test global router is a singleton."""
        router1 = get_migration_router()
        router2 = get_migration_router()
        
        assert router1 is router2
    
    def test_reset_global_router(self):
        """Test reset_global_router function."""
        router1 = get_migration_router()
        reset_migration_router()
        router2 = get_migration_router()
        
        assert router1 is not router2


class TestMigrationContext:
    """Test migration_context context manager."""
    
    def test_context_manager_mode(self):
        """Test context manager changes mode temporarily."""
        router = get_migration_router()
        original_mode = router.config.mode
        
        with migration_context(MigrationMode.CREWAI_ONLY) as ctx_router:
            assert ctx_router.config.mode == MigrationMode.CREWAI_ONLY
        
        # Should be restored after exiting context
        assert router.config.mode == original_mode
    
    def test_context_manager_string_mode(self):
        """Test context manager with string mode."""
        router = get_migration_router()
        original_mode = router.config.mode
        
        with migration_context("crewai_only") as ctx_router:
            assert ctx_router.config.mode == MigrationMode.CREWAI_ONLY
        
        assert router.config.mode == original_mode


class TestResultComparison:
    """Test result comparison functionality."""
    
    def test_compare_results_both_success(self):
        """Test comparing two successful results."""
        router = MigrationRouter()
        
        mcp_result = {"status": "success", "data": {"key": "value"}}
        crewai_result = {"status": "success", "data": {"key": "value"}}
        
        assert router._compare_results(mcp_result, crewai_result) == True
    
    def test_compare_results_different_keys(self):
        """Test comparing results with different keys."""
        router = MigrationRouter()
        
        mcp_result = {"status": "success", "mcp_key": "value"}
        crewai_result = {"status": "success", "crewai_key": "value"}
        
        assert router._compare_results(mcp_result, crewai_result) == False
    
    def test_compare_results_different_values(self):
        """Test comparing results with different values."""
        router = MigrationRouter()
        
        mcp_result = {"status": "success", "key": "mcp_value"}
        crewai_result = {"status": "success", "key": "crewai_value"}
        
        assert router._compare_results(mcp_result, crewai_result) == False
    
    def test_compare_results_one_error(self):
        """Test comparing when one result has an error."""
        router = MigrationRouter()
        
        mcp_result = {"status": "error", "error": "MCP error"}
        crewai_result = {"status": "success", "data": {"key": "value"}}
        
        assert router._compare_results(mcp_result, crewai_result) == False


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
