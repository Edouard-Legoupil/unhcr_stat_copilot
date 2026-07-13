"""
Data Task Definitions for UNHCR Statistics Copilot CrewAI

This module contains CrewAI task definitions for data fetching and validation.
"""

import logging
from typing import Any, Callable, Dict, List, Optional, Union

# Import CrewAI Task (with fallback mock)
try:
    from crewai import Task as CrewAITask
    CREWAI_AVAILABLE = True
except ImportError:
    CREWAI_AVAILABLE = False
    logging.warning("CrewAI not installed. Using mock Task class.")
    
    class CrewAITask:
        """Mock CrewAI Task for development without CrewAI installed."""
        def __init__(self, **kwargs):
            self.name = kwargs.get('name', 'Mock Task')
            self.description = kwargs.get('description', 'Mock task description')
            self.expected_output = kwargs.get('expected_output', '')
            self.agent = kwargs.get('agent')
            self.context = kwargs.get('context', [])
            self.tools = kwargs.get('tools', [])
            self.async_execution = kwargs.get('async_execution', False)
            self.output_file = kwargs.get('output_file')
        
        def execute(self, *args, **kwargs) -> Any:
            """Mock task execution."""
            return {"status": "mocked", "result": f"Task {self.name} executed"}

from backend.crewai.agents import (
    UNHCRDataFetcher,
    RSDExpert,
    SolutionsExpert,
    DemographicsExpert,
    TemporalAnalyzer,
    GeographyExpert
)

logger = logging.getLogger(__name__)


def create_data_task(
    name: str,
    description: str,
    agent: Any,
    expected_output: str,
    context: Optional[List] = None,
    tools: Optional[List] = None,
    async_execution: bool = False
) -> CrewAITask:
    """
    Factory function to create a data task.
    
    Args:
        name: Task name
        description: Task description
        agent: Agent to execute the task
        expected_output: Expected output format/description
        context: Context variables for the task
        tools: Tools available to the task
        async_execution: Whether to execute asynchronously
        
    Returns:
        Configured CrewAI Task
    """
    return CrewAITask(
        name=name,
        description=description,
        agent=agent,
        expected_output=expected_output,
        context=context or [],
        tools=tools or [],
        async_execution=async_execution
    )


class FetchPopulationDataTask:
    """
    Task to fetch population data from UNHCR API.
    
    This task uses the UNHCRDataFetcher agent to retrieve
    population statistics for a given question and parameters.
    """
    
    def __init__(
        self,
        agent: Optional[UNHCRDataFetcher] = None,
        question: str = "",
        parameters: Optional[Dict] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        """
        Initialize the FetchPopulationDataTask.
        
        Args:
            agent: UNHCRDataFetcher agent instance
            question: Analysis question
            parameters: Data retrieval parameters
            audience: Target audience
            document_type: Document type
        """
        self.agent = agent
        self.question = question
        self.parameters = parameters or {}
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        """
        Get the CrewAI Task instance.
        
        Returns:
            Configured CrewAI Task
        """
        if not self.agent:
            self.agent = UNHCRDataFetcher(
                audience=self.audience,
                document_type=self.document_type
            )
        
        return create_data_task(
            name="fetch_population_data",
            description=(
                f"Fetch UNHCR population data for question: {self.question}"
            ),
            agent=self.agent,
            expected_output=(
                "A dictionary containing population data with structure: "
                "{'status': str, 'data': dict, 'metadata': dict}"
            ),
            context=[
                self.question,
                self.parameters,
                self.audience,
                self.document_type
            ],
            async_execution=False
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the task directly (without CrewAI).
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            Task execution result
        """
        if not self.agent:
            self.agent = UNHCRDataFetcher(
                audience=self.audience,
                document_type=self.document_type
            )
        
        try:
            result = self.agent.fetch_population_data(
                question=self.question,
                parameters=self.parameters,
                audience=self.audience,
                document_type=self.document_type,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"Error executing FetchPopulationDataTask: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': self.question
            }


class FetchAllDataTask:
    """
    Task to fetch all types of UNHCR data.
    
    This task uses multiple agents to retrieve comprehensive data:
    - Population data
    - RSD applications and decisions
    - Solutions data
    - Demographics
    - Trends
    - Geographic data
    """
    
    def __init__(
        self,
        question: str = "",
        parameters: Optional[Dict] = None,
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        """
        Initialize the FetchAllDataTask.
        
        Args:
            question: Analysis question
            parameters: Data retrieval parameters
            audience: Target audience
            document_type: Document type
        """
        self.question = question
        self.parameters = parameters or {}
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        """
        Get the CrewAI Task instance.
        
        Note: This creates a task that can be executed by a Crew.
        For direct execution, use the execute() method.
        
        Returns:
            Configured CrewAI Task
        """
        from backend.crewai.crews import DataCrew
        
        # Create a DataCrew for this task
        data_crew = DataCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        
        # We'll use the data fetcher agent as the primary agent
        agent = UNHCRDataFetcher(
            audience=self.audience,
            document_type=self.document_type
        )
        
        return create_data_task(
            name="fetch_all_data",
            description=(
                f"Fetch all UNHCR data types for question: {self.question}"
            ),
            agent=agent,
            expected_output=(
                "A dictionary containing all data types: "
                "{'status': str, 'data': {'population': dict, 'rsd_applications': dict, "
                "'rsd_decisions': dict, 'solutions': dict, 'demographics': dict, "
                "'trends': dict, 'geography': dict}}"
            ),
            context=[
                self.question,
                self.parameters,
                self.audience,
                self.document_type
            ],
            async_execution=False
        )
    
    def execute(self, **kwargs) -> Dict[str, Any]:
        """
        Execute the task directly.
        
        Args:
            **kwargs: Additional keyword arguments
            
        Returns:
            Task execution result
        """
        from backend.crewai.crews import DataCrew
        
        data_crew = DataCrew(
            audience=self.audience,
            document_type=self.document_type
        )
        
        try:
            result = data_crew.fetch_all_data(
                question=self.question,
                parameters=self.parameters,
                **kwargs
            )
            return result
        except Exception as e:
            logger.error(f"Error executing FetchAllDataTask: {e}")
            return {
                'status': 'error',
                'error': str(e),
                'question': self.question
            }


class ValidateDataTask:
    """
    Task to validate fetched UNHCR data.
    
    This task ensures that retrieved data meets quality standards
    and contains the necessary fields for analysis.
    """
    
    def __init__(
        self,
        data: Dict[str, Any] = None,
        question: str = "",
        audience: str = "internal",
        document_type: str = "technical_report"
    ):
        """
        Initialize the ValidateDataTask.
        
        Args:
            data: Data to validate
            question: Analysis question
            audience: Target audience
            document_type: Document type
        """
        self.data = data or {}
        self.question = question
        self.audience = audience
        self.document_type = document_type
    
    def get_task(self) -> CrewAITask:
        """
        Get the CrewAI Task instance.
        
        Returns:
            Configured CrewAI Task
        """
        agent = UNHCRDataFetcher(
            audience=self.audience,
            document_type=self.document_type
        )
        
        return create_data_task(
            name="validate_data",
            description=(
                f"Validate UNHCR data for question: {self.question}"
            ),
            agent=agent,
            expected_output=(
                "A dictionary containing validation results: "
                "{'status': str, 'valid': bool, 'issues': list, 'warnings': list}"
            ),
            context=[
                self.data,
                self.question,
                self.audience,
                self.document_type
            ],
            async_execution=False
        )
    
    def execute(self, data: Optional[Dict] = None, **kwargs) -> Dict[str, Any]:
        """
        Execute the task directly.
        
        Args:
            data: Data to validate (overrides instance data)
            **kwargs: Additional keyword arguments
            
        Returns:
            Task execution result
        """
        validate_data = data or self.data
        
        # Simple validation - check for required fields
        issues = []
        warnings = []
        
        # Check if data is empty
        if not validate_data:
            issues.append("No data provided for validation")
            return {
                'status': 'error',
                'valid': False,
                'issues': issues,
                'warnings': warnings
            }
        
        # Check for common data fields
        if 'population' in validate_data:
            pop_data = validate_data['population']
            if not isinstance(pop_data, dict):
                issues.append("Population data should be a dictionary")
            elif 'status' in pop_data and pop_data['status'] == 'error':
                warnings.append("Population data retrieval encountered errors")
        else:
            warnings.append("No population data found")
        
        # Check each data type
        expected_types = [
            'population', 'rsd_applications', 'rsd_decisions',
            'solutions', 'demographics', 'trends', 'geography'
        ]
        
        for data_type in expected_types:
            if data_type not in validate_data:
                warnings.append(f"No {data_type} data found")
            elif validate_data[data_type].get('status') == 'error':
                warnings.append(f"{data_type} data retrieval encountered errors")
        
        return {
            'status': 'success' if not issues else 'partial_success',
            'valid': len(issues) == 0,
            'issues': issues,
            'warnings': warnings,
            'data_quality': 'high' if not issues and not warnings else 
                          'medium' if not issues else 'low'
        }
