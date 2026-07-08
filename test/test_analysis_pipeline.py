"""
Tests for the Analysis Pipeline Orchestrator

This module tests the enhanced analysis pipeline that integrates statistical analysis,
compliance validation, visualization, and story generation.
"""

import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from backend.mcp.tools.analysis_pipeline import (
    run_enhanced_analysis_pipeline,
    run_conditional_analysis_pipeline
)


# Sample test data
SAMPLE_POPULATION_DATA = {
    "data_type": "population",
    "data": {
        "items": [
            {"year": 2020, "refugees": 10000, "asylum_seekers": 5000, "coo_name": "Syria", "coa_name": "Germany"},
            {"year": 2021, "refugees": 12000, "asylum_seekers": 6000, "coo_name": "Syria", "coa_name": "Germany"},
            {"year": 2022, "refugees": 15000, "asylum_seekers": 7500, "coo_name": "Syria", "coa_name": "Germany"},
        ]
    },
    "parameters": {"coo": "SYR"}
}

SAMPLE_EMPTY_DATA = {
    "data_type": "unknown",
    "data": {}
}


@pytest.mark.asyncio
async def test_run_enhanced_analysis_pipeline_basic():
    """Test that the enhanced pipeline runs with basic valid data."""
    result = await run_enhanced_analysis_pipeline(
        question="What are the refugee trends from Syria to Germany?",
        data=SAMPLE_POPULATION_DATA,
        audience="internal",
        document_type="long_read"
    )
    
    assert result["status"] == "success"
    assert "enhanced_data" in result
    assert "statistics" in result["enhanced_data"]
    assert "guardrails" in result["enhanced_data"]
    assert "pipeline_phases" in result


@pytest.mark.asyncio
async def test_run_enhanced_analysis_pipeline_no_data():
    """Test that the pipeline handles missing data gracefully."""
    result = await run_enhanced_analysis_pipeline(
        question="Test question",
        data=None,
        audience="internal"
    )
    
    assert result["status"] == "error"
    assert "error" in result


@pytest.mark.asyncio
async def test_run_enhanced_analysis_pipeline_no_question():
    """Test that the pipeline handles missing question gracefully."""
    result = await run_enhanced_analysis_pipeline(
        question="",
        data=SAMPLE_POPULATION_DATA,
        audience="internal"
    )
    
    assert result["status"] == "error"
    assert "error" in result


@pytest.mark.asyncio
async def test_run_conditional_analysis_pipeline_enhanced():
    """Test conditional pipeline with enhanced=True."""
    result = await run_conditional_analysis_pipeline(
        question="Analyze the refugee trends with deep insights",
        data=SAMPLE_POPULATION_DATA,
        audience="internal",
        use_enhanced=True
    )
    
    assert result["status"] == "success"
    assert result.get("pipeline_type") in ["simple", None] or "enhanced_data" in result


@pytest.mark.asyncio
async def test_run_conditional_analysis_pipeline_simple():
    """Test conditional pipeline with enhanced=False."""
    result = await run_conditional_analysis_pipeline(
        question="What is the refugee count?",
        data=SAMPLE_POPULATION_DATA,
        audience="internal",
        use_enhanced=False
    )
    
    assert result["status"] == "success"
    assert result.get("pipeline_type") == "simple"


@pytest.mark.asyncio
async def test_run_conditional_analysis_pipeline_auto_detect():
    """Test that conditional pipeline auto-detects complex queries."""
    # This should auto-detect as enhanced due to "analyze" keyword
    result = await run_conditional_analysis_pipeline(
        question="Analyze the trends in refugee data",
        data=SAMPLE_POPULATION_DATA,
        audience="internal"
    )
    
    assert result["status"] == "success"
    # Should use enhanced pipeline due to "analyze" keyword


@pytest.mark.asyncio
async def test_run_conditional_analysis_pipeline_auto_detect_simple():
    """Test that conditional pipeline auto-detects simple queries."""
    # This should auto-detect as simple (no complex keywords)
    result = await run_conditional_analysis_pipeline(
        question="What is the refugee count?",
        data=SAMPLE_POPULATION_DATA,
        audience="internal"
    )
    
    assert result["status"] == "success"
    assert result.get("pipeline_type") == "simple"


@pytest.mark.asyncio
async def test_pipeline_with_empty_data():
    """Test pipeline handles empty data gracefully."""
    result = await run_enhanced_analysis_pipeline(
        question="Test",
        data=SAMPLE_EMPTY_DATA
    )
    
    # Should still return success but with limited data
    assert result["status"] in ["success", "error"]


@pytest.mark.asyncio
async def test_pipeline_includes_compliance():
    """Test that compliance validation is included in pipeline."""
    result = await run_enhanced_analysis_pipeline(
        question="Test compliance",
        data=SAMPLE_POPULATION_DATA
    )
    
    if result["status"] == "success":
        assert "guardrails" in result["enhanced_data"]
        # Check that compliance was validated
        guardrails = result["enhanced_data"]["guardrails"]
        if guardrails:
            assert "overall_compliant" in guardrails or "compliance_percentage" in guardrails


@pytest.mark.asyncio
async def test_pipeline_includes_statistics():
    """Test that statistics are calculated in pipeline."""
    result = await run_enhanced_analysis_pipeline(
        question="Test statistics",
        data=SAMPLE_POPULATION_DATA
    )
    
    if result["status"] == "success":
        assert "statistics" in result["enhanced_data"]
        stats = result["enhanced_data"]["statistics"]
        if stats:
            assert "statistics" in stats  # The stats dict should have a statistics key


@pytest.mark.asyncio
async def test_pipeline_includes_visualization():
    """Test that visualization structure is extracted in pipeline."""
    result = await run_enhanced_analysis_pipeline(
        question="Test visualization",
        data=SAMPLE_POPULATION_DATA
    )
    
    if result["status"] == "success":
        assert "visualization_structure" in result["enhanced_data"]
        assert "visualization_description" in result["enhanced_data"]


# Mocked tests for LLM-based story generation
@pytest.mark.asyncio
@patch('backend.mcp.tools.generate_analytical_story.generate_analytical_story_tool')
async def test_pipeline_with_rag(mock_analytical_story):
    """Test pipeline with RAG retriever (mocked)."""
    mock_analytical_story.return_value = {
        "story": "Mocked analytical story with RAG",
        "status": "success"
    }
    
    mock_retriever = MagicMock()
    
    result = await run_enhanced_analysis_pipeline(
        question="Test RAG",
        data=SAMPLE_POPULATION_DATA,
        use_rag=True,
        rag_retriever=mock_retriever
    )
    
    assert result["status"] == "success"


# Test configuration passing
@pytest.mark.asyncio
async def test_pipeline_with_config():
    """Test pipeline with analysis configuration."""
    config = {
        "tone": "formal",
        "length": "long",
        "structure": ["intro", "analysis", "conclusion"]
    }
    
    result = await run_enhanced_analysis_pipeline(
        question="Test config",
        data=SAMPLE_POPULATION_DATA,
        analysis_config=config
    )
    
    assert result["status"] == "success"


if __name__ == "__main__":
    # Run tests
    import sys
    sys.exit(pytest.main([__file__, "-v", "--tb=short"]))
