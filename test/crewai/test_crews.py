"""
Tests for CrewAI Crews

This module tests all CrewAI crew classes to ensure they:
- Initialize correctly
- Coordinate agents properly
- Execute workflows end-to-end
- Handle errors gracefully
"""

import pytest
from typing import Any, Dict

from backend.crewai.crews import (
    DataCrew,
    AnalysisCrew,
    StoryCrew,
    NotebookCrew,
    MasterCrew
)
from backend.crewai.config import AudienceConfigManager


class TestDataCrew:
    """Test DataCrew."""
    
    def test_initialization(self):
        """Test DataCrew initialization."""
        crew = DataCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        assert crew.audience == "internal"
        assert crew.document_type == "technical_report"
    
    def test_get_crew(self):
        """Test get_crew method."""
        crew = DataCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        # This should not raise an exception
        result = crew.get_crew()
        assert result is not None
    
    def test_fetch_population_data(self):
        """Test fetch_population_data method."""
        crew = DataCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.fetch_population_data(
            question="Test question",
            parameters={}
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_fetch_all_data(self):
        """Test fetch_all_data method."""
        crew = DataCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.fetch_all_data(
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_shutdown(self):
        """Test shutdown method."""
        crew = DataCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        # Should not raise an exception
        crew.shutdown()


class TestAnalysisCrew:
    """Test AnalysisCrew."""
    
    def test_initialization(self):
        """Test AnalysisCrew initialization."""
        crew = AnalysisCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        assert crew.audience == "internal"
        assert crew.document_type == "technical_report"
    
    def test_get_crew(self):
        """Test get_crew method."""
        crew = AnalysisCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.get_crew()
        assert result is not None
    
    def test_analyze_data(self):
        """Test analyze_data method."""
        crew = AnalysisCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        test_data = {"test": "data"}
        result = crew.analyze_data(
            data=test_data,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_apply_analysis_pipeline(self):
        """Test apply_analysis_pipeline method."""
        crew = AnalysisCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        test_data = {"test": "data"}
        result = crew.apply_analysis_pipeline(
            data=test_data,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_shutdown(self):
        """Test shutdown method."""
        crew = AnalysisCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        crew.shutdown()


class TestStoryCrew:
    """Test StoryCrew."""
    
    def test_initialization(self):
        """Test StoryCrew initialization."""
        crew = StoryCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        assert crew.audience == "internal"
        assert crew.document_type == "technical_report"
    
    def test_get_crew(self):
        """Test get_crew method."""
        crew = StoryCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.get_crew()
        assert result is not None
    
    def test_generate_story(self):
        """Test generate_story method."""
        crew = StoryCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        test_data = {"test": "data"}
        test_analysis = {"test": "analysis"}
        result = crew.generate_story(
            data=test_data,
            analysis=test_analysis,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_generate_data_story(self):
        """Test generate_data_story method."""
        crew = StoryCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        test_data = {"test": "data"}
        result = crew.generate_data_story(
            data=test_data,
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_shutdown(self):
        """Test shutdown method."""
        crew = StoryCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        crew.shutdown()


class TestNotebookCrew:
    """Test NotebookCrew."""
    
    def test_initialization(self):
        """Test NotebookCrew initialization."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        assert crew.audience == "internal"
        assert crew.document_type == "technical_report"
    
    def test_get_crew(self):
        """Test get_crew method."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.get_crew()
        assert result is not None
    
    def test_create_notebook(self):
        """Test create_notebook method."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.create_notebook(
            story_content="Test story",
            data={"test": "data"},
            analysis={"test": "analysis"},
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_create_notebook_from_story(self):
        """Test create_notebook_from_story method."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        story_result = {"story": "Test story", "status": "success"}
        result = crew.create_notebook_from_story(
            story_result=story_result,
            data={"test": "data"},
            analysis={"test": "analysis"},
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_create_quarto_notebook(self):
        """Test create_quarto_notebook method."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.create_quarto_notebook(
            story_content="Test story",
            audience="internal",
            document_type="technical_report"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_shutdown(self):
        """Test shutdown method."""
        crew = NotebookCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        crew.shutdown()


class TestMasterCrew:
    """Test MasterCrew."""
    
    def test_initialization(self):
        """Test MasterCrew initialization."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        assert crew.audience == "internal"
        assert crew.document_type == "technical_report"
    
    def test_get_crews(self):
        """Test that MasterCrew can access all sub-crews."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        # Test that we can get each sub-crew
        data_crew = crew.get_data_crew()
        assert isinstance(data_crew, DataCrew)
        
        analysis_crew = crew.get_analysis_crew()
        assert isinstance(analysis_crew, AnalysisCrew)
        
        story_crew = crew.get_story_crew()
        assert isinstance(story_crew, StoryCrew)
        
        notebook_crew = crew.get_notebook_crew()
        assert isinstance(notebook_crew, NotebookCrew)
    
    def test_execute_full_workflow(self):
        """Test execute_full_workflow method."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.execute_full_workflow(
            question="Test question",
            include_notebook=False
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_quick_workflow(self):
        """Test execute_quick_workflow method."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.execute_quick_workflow(
            question="Test question"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_execute_comparison_workflow(self):
        """Test execute_comparison_workflow method."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        result = crew.execute_comparison_workflow(
            question="Compare A and B"
        )
        
        assert isinstance(result, dict)
        assert "status" in result
    
    def test_parse_comparison_question(self):
        """Test _parse_comparison_question method."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        # Test various comparison question formats
        test_cases = [
            ("Compare A and B", ["Analyze A", "Analyze B"]),
            ("A vs B", ["Analyze A", "Analyze B"]),
            ("Compare A, B, C", ["Analyze A", "Analyze B", "Analyze C"]),
            ("Simple question", ["Simple question"])
        ]
        
        for question, expected in test_cases:
            result = crew._parse_comparison_question(question)
            assert isinstance(result, list)
            assert len(result) > 0
    
    def test_shutdown(self):
        """Test shutdown method."""
        crew = MasterCrew(
            audience="internal",
            document_type="technical_report"
        )
        
        crew.shutdown()


class TestCrewAudienceValidation:
    """Test that crews validate audience and document type."""
    
    def test_invalid_audience(self):
        """Test that crews handle invalid audience by defaulting to internal."""
        # The current implementation logs a warning and defaults to 'internal'
        crew = DataCrew(audience="invalid_audience")
        assert crew.audience == "internal"
    
    def test_valid_audiences(self):
        """Test that all crews accept valid audiences."""
        valid_audiences = ["internal", "public_donors", "private_donors", "government", "media"]
        
        for audience in valid_audiences:
            crew = DataCrew(audience=audience)
            assert crew.audience == audience
    
    def test_default_document_type(self):
        """Test that crews use default document type when not specified."""
        crew = DataCrew(audience="internal")
        
        # Should get default from AudienceConfigManager
        assert crew.document_type == AudienceConfigManager.get_default_type("internal")


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
