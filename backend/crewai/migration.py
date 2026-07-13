"""
CrewAI Migration Utilities for UNHCR Statistics Copilot

This module provides utilities for migrating from MCP-based tool orchestration
to CrewAI-based agent orchestration. It includes:

- Dual-run mode: Execute both MCP and CrewAI workflows for comparison
- Traffic routing: Route requests to MCP or CrewAI based on configuration
- Rollback capabilities: Revert to MCP if CrewAI fails
- Migration metrics: Track migration progress and success rates
"""

import logging
import os
import time
from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any, Callable, Dict, List, Optional, Tuple, Union
from contextlib import contextmanager

logger = logging.getLogger(__name__)


class MigrationMode(Enum):
    """Migration mode for request routing."""
    MCP_ONLY = "mcp_only"           # Use only MCP tools (default, pre-migration)
    CREWAI_ONLY = "crewai_only"     # Use only CrewAI agents (full migration)
    DUAL_RUN = "dual_run"          # Run both and compare results
    HYBRID = "hybrid"              # Route based on traffic percentage
    FALLBACK = "fallback"          # Try CrewAI first, fallback to MCP on error


class RoutingStrategy(Enum):
    """Strategy for routing requests between MCP and CrewAI."""
    RANDOM = "random"              # Random distribution
    ROUND_ROBIN = "round_robin"    # Round-robin distribution
    PERCENTAGE = "percentage"      # Percentage-based distribution
    TOOL_BASED = "tool_based"      # Route based on tool type
    AUDIENCE_BASED = "audience_based"  # Route based on audience type


@dataclass
class MigrationConfig:
    """Configuration for CrewAI migration."""
    mode: MigrationMode = MigrationMode.MCP_ONLY
    strategy: RoutingStrategy = RoutingStrategy.RANDOM
    
    # Traffic percentages (for PERCENTAGE strategy)
    mcp_percentage: float = 100.0
    crewai_percentage: float = 0.0
    
    # Tool-specific routing
    crewai_tools: List[str] = field(default_factory=list)
    mcp_tools: List[str] = field(default_factory=list)
    
    # Audience-specific routing
    crewai_audiences: List[str] = field(default_factory=list)
    mcp_audiences: List[str] = field(default_factory=list)
    
    # Dual-run settings
    dual_run_compare: bool = True
    dual_run_return: str = "both"  # "both", "mcp", "crewai"
    
    # Fallback settings
    fallback_enabled: bool = True
    fallback_timeout: float = 5.0  # seconds before fallback
    
    # Enable/disable migration tracking
    track_metrics: bool = True
    
    @classmethod
    def from_env(cls) -> "MigrationConfig":
        """Load configuration from environment variables."""
        mode_str = os.getenv("CREWAI_MIGRATION_MODE", "mcp_only")
        try:
            mode = MigrationMode(mode_str)
        except ValueError:
            mode = MigrationMode.MCP_ONLY
            logger.warning(f"Invalid CREWAI_MIGRATION_MODE: {mode_str}, defaulting to MCP_ONLY")
        
        strategy_str = os.getenv("CREWAI_ROUTING_STRATEGY", "random")
        try:
            strategy = RoutingStrategy(strategy_str)
        except ValueError:
            strategy = RoutingStrategy.RANDOM
            logger.warning(f"Invalid CREWAI_ROUTING_STRATEGY: {strategy_str}, defaulting to RANDOM")
        
        mcp_pct = float(os.getenv("CREWAI_MCP_PERCENTAGE", "100.0"))
        crewai_pct = float(os.getenv("CREWAI_CREWAI_PERCENTAGE", "0.0"))
        
        # Normalize percentages
        total = mcp_pct + crewai_pct
        if total > 0:
            mcp_pct = (mcp_pct / total) * 100
            crewai_pct = (crewai_pct / total) * 100
        
        # Parse tool lists
        crewai_tools = os.getenv("CREWAI_CREWAI_TOOLS", "").split(",") if os.getenv("CREWAI_CREWAI_TOOLS") else []
        mcp_tools = os.getenv("CREWAI_MCP_TOOLS", "").split(",") if os.getenv("CREWAI_MCP_TOOLS") else []
        
        # Parse audience lists
        crewai_audiences = os.getenv("CREWAI_CREWAI_AUDIENCES", "").split(",") if os.getenv("CREWAI_CREWAI_AUDIENCES") else []
        mcp_audiences = os.getenv("CREWAI_MCP_AUDIENCES", "").split(",") if os.getenv("CREWAI_MCP_AUDIENCES") else []
        
        dual_run_compare = os.getenv("CREWAI_DUAL_RUN_COMPARE", "true").lower() == "true"
        dual_run_return = os.getenv("CREWAI_DUAL_RUN_RETURN", "both")
        
        fallback_enabled = os.getenv("CREWAI_FALLBACK_ENABLED", "true").lower() == "true"
        fallback_timeout = float(os.getenv("CREWAI_FALLBACK_TIMEOUT", "5.0"))
        
        track_metrics = os.getenv("CREWAI_TRACK_METRICS", "true").lower() == "true"
        
        return cls(
            mode=mode,
            strategy=strategy,
            mcp_percentage=mcp_pct,
            crewai_percentage=crewai_pct,
            crewai_tools=crewai_tools,
            mcp_tools=mcp_tools,
            crewai_audiences=crewai_audiences,
            mcp_audiences=mcp_audiences,
            dual_run_compare=dual_run_compare,
            dual_run_return=dual_run_return,
            fallback_enabled=fallback_enabled,
            fallback_timeout=fallback_timeout,
            track_metrics=track_metrics
        )


@dataclass
class MigrationMetrics:
    """Metrics for tracking migration progress."""
    total_requests: int = 0
    mcp_requests: int = 0
    crewai_requests: int = 0
    dual_run_requests: int = 0
    fallback_requests: int = 0
    
    mcp_successes: int = 0
    mcp_failures: int = 0
    crewai_successes: int = 0
    crewai_failures: int = 0
    
    avg_mcp_time: float = 0.0
    avg_crewai_time: float = 0.0
    
    comparison_mismatches: int = 0
    comparison_total: int = 0
    
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert metrics to dictionary."""
        return {
            'total_requests': self.total_requests,
            'mcp_requests': self.mcp_requests,
            'crewai_requests': self.crewai_requests,
            'dual_run_requests': self.dual_run_requests,
            'fallback_requests': self.fallback_requests,
            'mcp_successes': self.mcp_successes,
            'mcp_failures': self.mcp_failures,
            'crewai_successes': self.crewai_successes,
            'crewai_failures': self.crewai_failures,
            'avg_mcp_time': self.avg_mcp_time,
            'avg_crewai_time': self.avg_crewai_time,
            'comparison_mismatches': self.comparison_mismatches,
            'comparison_total': self.comparison_total,
            'mcp_success_rate': self.mcp_success_rate,
            'crewai_success_rate': self.crewai_success_rate,
            'error_count': len(self.errors),
            'warning_count': len(self.warnings)
        }
    
    @property
    def mcp_success_rate(self) -> float:
        """Calculate MCP success rate."""
        total = self.mcp_requests
        if total == 0:
            return 0.0
        return (self.mcp_successes / total) * 100
    
    @property
    def crewai_success_rate(self) -> float:
        """Calculate CrewAI success rate."""
        total = self.crewai_requests
        if total == 0:
            return 0.0
        return (self.crewai_successes / total) * 100


class MigrationRouter:
    """
    Router for migrating from MCP to CrewAI.
    
    This class handles request routing between MCP tools and CrewAI agents
    based on the configured migration mode and strategy.
    """
    
    def __init__(self, config: Optional[MigrationConfig] = None):
        """
        Initialize the Migration Router.
        
        Args:
            config: Migration configuration (loaded from env if not provided)
        """
        self.config = config or MigrationConfig.from_env()
        self.metrics = MigrationMetrics()
        self._round_robin_index = 0
        self._start_time = time.time()
        
        logger.info(f"MigrationRouter initialized with mode={self.config.mode.value}")
    
    def route_request(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        mcp_func: Callable,
        crewai_func: Callable,
        audience: Optional[str] = None
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """
        Route a request to MCP or CrewAI based on configuration.
        
        Args:
            tool_name: Name of the tool being called
            parameters: Parameters for the tool
            mcp_func: MCP implementation of the tool
            crewai_func: CrewAI implementation of the tool
            audience: Target audience (for audience-based routing)
            
        Returns:
            Tuple of (source, result, metrics) where:
            - source: "mcp", "crewai", or "dual"
            - result: The result from the execution
            - metrics: Additional metrics about the execution
        """
        start_time = time.time()
        
        # Determine route based on mode and strategy
        if self.config.mode == MigrationMode.MCP_ONLY:
            return self._route_to_mcp(tool_name, parameters, mcp_func, start_time)
        
        elif self.config.mode == MigrationMode.CREWAI_ONLY:
            return self._route_to_crewai(tool_name, parameters, crewai_func, start_time)
        
        elif self.config.mode == MigrationMode.DUAL_RUN:
            return self._route_dual(tool_name, parameters, mcp_func, crewai_func, start_time)
        
        elif self.config.mode == MigrationMode.HYBRID:
            return self._route_hybrid(tool_name, parameters, mcp_func, crewai_func, audience, start_time)
        
        elif self.config.mode == MigrationMode.FALLBACK:
            return self._route_fallback(tool_name, parameters, mcp_func, crewai_func, start_time)
        
        else:
            # Default to MCP
            return self._route_to_mcp(tool_name, parameters, mcp_func, start_time)
    
    def _route_to_mcp(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        mcp_func: Callable,
        start_time: float
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """Route request to MCP."""
        try:
            result = mcp_func(**parameters)
            duration = time.time() - start_time
            
            self.metrics.mcp_requests += 1
            self.metrics.mcp_successes += 1
            self.metrics.total_requests += 1
            
            # Update average time
            current_total = self.metrics.avg_mcp_time * (self.metrics.mcp_requests - 1)
            self.metrics.avg_mcp_time = (current_total + duration) / self.metrics.mcp_requests
            
            return "mcp", result, {
                'duration': duration,
                'routed_to': 'mcp'
            }
        except Exception as e:
            self.metrics.mcp_requests += 1
            self.metrics.mcp_failures += 1
            self.metrics.total_requests += 1
            self.metrics.errors.append(f"MCP error for {tool_name}: {str(e)}")
            
            logger.error(f"MCP execution failed for {tool_name}: {e}")
            return "mcp", {'status': 'error', 'error': str(e)}, {
                'duration': time.time() - start_time,
                'routed_to': 'mcp',
                'error': str(e)
            }
    
    def _route_to_crewai(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        crewai_func: Callable,
        start_time: float
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """Route request to CrewAI."""
        try:
            result = crewai_func(**parameters)
            duration = time.time() - start_time
            
            self.metrics.crewai_requests += 1
            self.metrics.crewai_successes += 1
            self.metrics.total_requests += 1
            
            # Update average time
            current_total = self.metrics.avg_crewai_time * (self.metrics.crewai_requests - 1)
            self.metrics.avg_crewai_time = (current_total + duration) / self.metrics.crewai_requests
            
            return "crewai", result, {
                'duration': duration,
                'routed_to': 'crewai'
            }
        except Exception as e:
            self.metrics.crewai_requests += 1
            self.metrics.crewai_failures += 1
            self.metrics.total_requests += 1
            self.metrics.errors.append(f"CrewAI error for {tool_name}: {str(e)}")
            
            logger.error(f"CrewAI execution failed for {tool_name}: {e}")
            return "crewai", {'status': 'error', 'error': str(e)}, {
                'duration': time.time() - start_time,
                'routed_to': 'crewai',
                'error': str(e)
            }
    
    def _route_dual(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        mcp_func: Callable,
        crewai_func: Callable,
        start_time: float
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """Execute both MCP and CrewAI and compare results."""
        self.metrics.dual_run_requests += 1
        self.metrics.total_requests += 1
        
        mcp_start = time.time()
        mcp_result = None
        crewai_result = None
        
        try:
            mcp_result = mcp_func(**parameters)
            mcp_duration = time.time() - mcp_start
            self.metrics.mcp_requests += 1
            self.metrics.mcp_successes += 1
        except Exception as e:
            mcp_duration = time.time() - mcp_start
            self.metrics.mcp_requests += 1
            self.metrics.mcp_failures += 1
            mcp_result = {'status': 'error', 'error': str(e)}
            self.metrics.errors.append(f"MCP error in dual run for {tool_name}: {e}")
        
        crewai_start = time.time()
        try:
            crewai_result = crewai_func(**parameters)
            crewai_duration = time.time() - crewai_start
            self.metrics.crewai_requests += 1
            self.metrics.crewai_successes += 1
        except Exception as e:
            crewai_duration = time.time() - crewai_start
            self.metrics.crewai_requests += 1
            self.metrics.crewai_failures += 1
            crewai_result = {'status': 'error', 'error': str(e)}
            self.metrics.errors.append(f"CrewAI error in dual run for {tool_name}: {e}")
        
        total_duration = time.time() - start_time
        
        # Compare results if both succeeded and comparison is enabled
        if self.config.dual_run_compare and mcp_result.get('status') == 'success' and crewai_result.get('status') == 'success':
            self.metrics.comparison_total += 1
            if not self._compare_results(mcp_result, crewai_result):
                self.metrics.comparison_mismatches += 1
                self.metrics.warnings.append(f"Result mismatch for {tool_name}")
                logger.warning(f"Result mismatch between MCP and CrewAI for {tool_name}")
        
        # Return based on configuration
        if self.config.dual_run_return == "both":
            return "dual", {
                'mcp': mcp_result,
                'crewai': crewai_result,
                'durations': {
                    'mcp': mcp_duration,
                    'crewai': crewai_duration,
                    'total': total_duration
                }
            }, {
                'duration': total_duration,
                'routed_to': 'dual',
                'mcp_duration': mcp_duration,
                'crewai_duration': crewai_duration
            }
        elif self.config.dual_run_return == "mcp":
            return "mcp", mcp_result, {
                'duration': total_duration,
                'routed_to': 'dual (returned mcp)',
                'crewai_duration': crewai_duration
            }
        else:  # crewai
            return "crewai", crewai_result, {
                'duration': total_duration,
                'routed_to': 'dual (returned crewai)',
                'mcp_duration': mcp_duration
            }
    
    def _route_hybrid(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        mcp_func: Callable,
        crewai_func: Callable,
        audience: Optional[str],
        start_time: float
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """Route based on strategy (percentage, tool-based, audience-based)."""
        # Check tool-based routing
        if tool_name in self.config.crewai_tools:
            return self._route_to_crewai(tool_name, parameters, crewai_func, start_time)
        if tool_name in self.config.mcp_tools:
            return self._route_to_mcp(tool_name, parameters, mcp_func, start_time)
        
        # Check audience-based routing
        if audience and audience in self.config.crewai_audiences:
            return self._route_to_crewai(tool_name, parameters, crewai_func, start_time)
        if audience and audience in self.config.mcp_audiences:
            return self._route_to_mcp(tool_name, parameters, mcp_func, start_time)
        
        # Check percentage-based routing
        import random
        rand_val = random.random() * 100
        if rand_val < self.config.crewai_percentage:
            return self._route_to_crewai(tool_name, parameters, crewai_func, start_time)
        else:
            return self._route_to_mcp(tool_name, parameters, mcp_func, start_time)
    
    def _route_fallback(
        self,
        tool_name: str,
        parameters: Dict[str, Any],
        mcp_func: Callable,
        crewai_func: Callable,
        start_time: float
    ) -> Tuple[str, Any, Dict[str, Any]]:
        """Try CrewAI first, fallback to MCP on error."""
        # Try CrewAI
        try:
            result = crewai_func(**parameters)
            duration = time.time() - start_time
            
            self.metrics.crewai_requests += 1
            self.metrics.crewai_successes += 1
            self.metrics.total_requests += 1
            
            current_total = self.metrics.avg_crewai_time * (self.metrics.crewai_requests - 1)
            self.metrics.avg_crewai_time = (current_total + duration) / self.metrics.crewai_requests
            
            return "crewai", result, {
                'duration': duration,
                'routed_to': 'crewai',
                'fallback': False
            }
        except Exception as e:
            self.metrics.crewai_requests += 1
            self.metrics.crewai_failures += 1
            self.metrics.fallback_requests += 1
            self.metrics.errors.append(f"CrewAI fallback for {tool_name}: {str(e)}")
            
            logger.warning(f"CrewAI failed for {tool_name}, falling back to MCP: {e}")
            
            # Fallback to MCP
            if self.config.fallback_enabled:
                mcp_result = mcp_func(**parameters)
                mcp_duration = time.time() - start_time
                
                self.metrics.mcp_requests += 1
                if mcp_result.get('status') != 'error':
                    self.metrics.mcp_successes += 1
                else:
                    self.metrics.mcp_failures += 1
                
                current_total = self.metrics.avg_mcp_time * (self.metrics.mcp_requests - 1)
                self.metrics.avg_mcp_time = (current_total + mcp_duration) / self.metrics.mcp_requests
                
                return "mcp", mcp_result, {
                    'duration': mcp_duration,
                    'routed_to': 'mcp',
                    'fallback': True,
                    'original_error': str(e)
                }
            else:
                return "crewai", {'status': 'error', 'error': str(e)}, {
                    'duration': time.time() - start_time,
                    'routed_to': 'crewai',
                    'fallback': False,
                    'error': str(e)
                }
    
    def _compare_results(self, mcp_result: Dict, crewai_result: Dict) -> bool:
        """
        Compare results from MCP and CrewAI executions.
        
        This is a simple comparison that checks for major differences.
        Should be enhanced based on actual result structures.
        
        Args:
            mcp_result: Result from MCP execution
            crewai_result: Result from CrewAI execution
            
        Returns:
            True if results are similar, False if there are significant differences
        """
        # If either failed, consider them different
        if mcp_result.get('status') == 'error' or crewai_result.get('status') == 'error':
            return mcp_result.get('status') == crewai_result.get('status')
        
        # Compare key fields
        # This is a simplified comparison - should be enhanced
        mcp_keys = set(mcp_result.keys()) - {'duration', 'timestamps'}
        crewai_keys = set(crewai_result.keys()) - {'duration', 'timestamps'}
        
        # Check for major structural differences
        if mcp_keys != crewai_keys:
            missing_in_mcp = crewai_keys - mcp_keys
            missing_in_crewai = mcp_keys - crewai_keys
            if missing_in_mcp or missing_in_crewai:
                logger.warning(f"Key mismatch: MCP missing {missing_in_mcp}, CrewAI missing {missing_in_crewai}")
                return False
        
        # Check for data differences in common fields
        for key in mcp_keys & crewai_keys:
            mcp_val = mcp_result[key]
            crewai_val = crewai_result[key]
            
            # Skip comparison for certain types
            if isinstance(mcp_val, (dict, list)) and isinstance(crewai_val, (dict, list)):
                continue
            
            if mcp_val != crewai_val:
                logger.warning(f"Value mismatch for key '{key}': MCP={mcp_val}, CrewAI={crewai_val}")
                return False
        
        return True
    
    def get_metrics(self) -> Dict[str, Any]:
        """Get current migration metrics."""
        return {
            **self.metrics.to_dict(),
            'uptime_seconds': time.time() - self._start_time,
            'config': {
                'mode': self.config.mode.value,
                'strategy': self.config.strategy.value,
                'mcp_percentage': self.config.mcp_percentage,
                'crewai_percentage': self.config.crewai_percentage
            }
        }
    
    def reset_metrics(self):
        """Reset all migration metrics."""
        self.metrics = MigrationMetrics()
        self._round_robin_index = 0
        self._start_time = time.time()
        logger.info("Migration metrics reset")
    
    def set_mode(self, mode: Union[MigrationMode, str]):
        """Set the migration mode."""
        if isinstance(mode, str):
            self.config.mode = MigrationMode(mode)
        else:
            self.config.mode = mode
        logger.info(f"Migration mode set to {self.config.mode.value}")
    
    def set_strategy(self, strategy: Union[RoutingStrategy, str]):
        """Set the routing strategy."""
        if isinstance(strategy, str):
            self.config.strategy = RoutingStrategy(strategy)
        else:
            self.config.strategy = strategy
        logger.info(f"Routing strategy set to {self.config.strategy.value}")


# Global router instance
_router: Optional[MigrationRouter] = None


def get_migration_router() -> MigrationRouter:
    """Get the global migration router instance."""
    global _router
    if _router is None:
        _router = MigrationRouter()
    return _router


def reset_migration_router():
    """Reset the global migration router instance."""
    global _router
    if _router is not None:
        _router.reset_metrics()
    _router = MigrationRouter()


@contextmanager
def migration_context(mode: Optional[Union[MigrationMode, str]] = None):
    """
    Context manager for temporarily changing migration mode.
    
    Args:
        mode: Temporary migration mode to use
        
    Example:
        with migration_context(MigrationMode.CREWAI_ONLY):
            # All requests in this block will use CrewAI only
            result = router.route_request(...)
    """
    router = get_migration_router()
    original_mode = router.config.mode
    
    if mode is not None:
        if isinstance(mode, str):
            router.set_mode(MigrationMode(mode))
        else:
            router.set_mode(mode)
    
    try:
        yield router
    finally:
        router.set_mode(original_mode)
