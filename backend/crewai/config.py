"""
Configuration Management for CrewAI Agents

This module provides audience-specific configuration management for CrewAI agents,
ensuring that all agents respect the UNHCR analysis configuration system.
"""

import logging
from typing import Any, Dict, List, Optional

logger = logging.getLogger(__name__)


# Import the existing ANALYSIS_CONFIG from chat.py
# This ensures consistency between legacy and CrewAI systems
try:
    from backend.chat import (
        ANALYSIS_CONFIG,
        get_available_document_types,
        get_default_document_type,
        get_analysis_config
    )
    CONFIG_AVAILABLE = True
except ImportError:
    logger.warning("Could not import ANALYSIS_CONFIG from backend.chat")
    CONFIG_AVAILABLE = False
    ANALYSIS_CONFIG = {}


class AudienceConfigManager:
    """
    Manages audience-specific configuration for CrewAI agents.
    
    This class provides a bridge between the existing ANALYSIS_CONFIG system
    and CrewAI agents, ensuring consistent behavior across both systems.
    """
    
    @staticmethod
    def get_config(
        audience: str,
        document_type: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Get the full analysis configuration for a given audience and document type.
        
        Args:
            audience: The target audience (internal, public_donors, private_donors, government, media)
            document_type: The document type (optional, defaults to audience default)
            
        Returns:
            Configuration dictionary including tone, length, structure, etc.
        """
        if not CONFIG_AVAILABLE:
            logger.warning("ANALYSIS_CONFIG not available, returning defaults")
            return AudienceConfigManager._get_default_config(audience, document_type)
        
        try:
            return get_analysis_config(audience, document_type or "")
        except Exception as e:
            logger.error(f"Error getting analysis config: {e}")
            return AudienceConfigManager._get_default_config(audience, document_type)
    
    @staticmethod
    def get_available_types(audience: str) -> List[str]:
        """
        Get the list of available document types for a given audience.
        
        Args:
            audience: The target audience
            
        Returns:
            List of available document type strings
        """
        if not CONFIG_AVAILABLE:
            logger.warning("ANALYSIS_CONFIG not available, returning defaults")
            return AudienceConfigManager._get_default_types(audience)
        
        try:
            return get_available_document_types(audience)
        except Exception as e:
            logger.error(f"Error getting available types: {e}")
            return AudienceConfigManager._get_default_types(audience)
    
    @staticmethod
    def get_default_type(audience: str) -> str:
        """
        Get the default document type for a given audience.
        
        Args:
            audience: The target audience
            
        Returns:
            Default document type string
        """
        if not CONFIG_AVAILABLE:
            logger.warning("ANALYSIS_CONFIG not available, returning defaults")
            return AudienceConfigManager._get_default_type(audience)
        
        try:
            return get_default_document_type(audience)
        except Exception as e:
            logger.error(f"Error getting default type: {e}")
            return AudienceConfigManager._get_default_type(audience)
    
    @staticmethod
    def validate_audience(audience: str) -> str:
        """
        Validate an audience string and return a valid audience.
        
        Args:
            audience: The audience to validate
            
        Returns:
            Validated audience string (falls back to 'internal' if invalid)
        """
        valid_audiences = ['internal', 'public_donors', 'private_donors', 'government', 'media']
        
        if audience in valid_audiences:
            return audience
        
        logger.warning(f"Invalid audience '{audience}', defaulting to 'internal'")
        return 'internal'
    
    @staticmethod
    def validate_document_type(audience: str, document_type: str) -> str:
        """
        Validate a document type for a given audience.
        
        Args:
            audience: The target audience
            document_type: The document type to validate
            
        Returns:
            Validated document type (falls back to audience default if invalid)
        """
        available_types = AudienceConfigManager.get_available_types(audience)
        
        if document_type in available_types:
            return document_type
        
        logger.warning(
            f"Invalid document type '{document_type}' for audience '{audience}', "
            f"defaulting to '{AudienceConfigManager.get_default_type(audience)}'"
        )
        return AudienceConfigManager.get_default_type(audience)
    
    @staticmethod
    def get_audience_metadata(audience: str) -> Dict[str, Any]:
        """
        Get metadata about a specific audience for agent context.
        
        Args:
            audience: The target audience
            
        Returns:
            Dictionary with audience metadata for agent backstory/context
        """
        audience_metadata = {
            'internal': {
                'description': 'Internal UNHCR staff and analysts',
                'purpose': 'Technical analysis and research reports',
                'tone_guidelines': 'Formal, precise, objective, methodology-focused',
                'typical_use_cases': ['Internal reporting', 'Research analysis', 'Methodology documentation']
            },
            'public_donors': {
                'description': 'Public sector donors and funding organizations',
                'purpose': 'Fundraising and impact reporting',
                'tone_guidelines': 'Clear, impactful, accessible, results-oriented',
                'typical_use_cases': ['Fundraising campaigns', 'Impact reports', 'Public communications']
            },
            'private_donors': {
                'description': 'Private sector donors and investors',
                'purpose': 'Investor relations and strategic briefings',
                'tone_guidelines': 'Strategic, persuasive, results-oriented, professional',
                'typical_use_cases': ['Investor reports', 'Strategic briefings', 'Donor communications']
            },
            'government': {
                'description': 'Government agencies and policy makers',
                'purpose': 'Policy briefings and decision support',
                'tone_guidelines': 'Formal, rigorous, policy-oriented, evidence-based',
                'typical_use_cases': ['Policy briefings', 'Official reports', 'Decision support']
            },
            'media': {
                'description': 'Media organizations and journalists',
                'purpose': 'Public awareness and news reporting',
                'tone_guidelines': 'Concise, factual, headline-ready, engaging',
                'typical_use_cases': ['Press releases', 'News articles', 'Public awareness campaigns']
            }
        }
        
        return audience_metadata.get(audience, audience_metadata['internal'])
    
    @staticmethod
    def _get_default_config(audience: str, document_type: Optional[str]) -> Dict[str, Any]:
        """Get default configuration when ANALYSIS_CONFIG is not available."""
        audience = AudienceConfigManager.validate_audience(audience)
        
        # Default configurations
        default_configs = {
            'internal': {
                'tone': 'formal, precise, objective',
                'length': {
                    'wordRange': '2000-5000',
                    'readingTime': '10-25 min',
                    'density': 'high'
                },
                'structure': ['objective', 'methodology', 'data analysis', 'results', 'limitations']
            },
            'public_donors': {
                'tone': 'clear, impactful, accessible',
                'length': {
                    'wordRange': '300-700',
                    'readingTime': '2-3 min',
                    'density': 'medium'
                },
                'structure': ['headline insight', 'key statistics', 'impact highlights', 'call to action']
            },
            'private_donors': {
                'tone': 'strategic, persuasive, results-oriented',
                'length': {
                    'wordRange': '300-700',
                    'readingTime': '2-3 min',
                    'density': 'medium-high'
                },
                'structure': ['key insights', 'impact metrics', 'value proposition', 'opportunities']
            },
            'government': {
                'tone': 'formal, rigorous, policy-oriented',
                'length': {
                    'wordRange': '2500-6000',
                    'readingTime': '12-30 min',
                    'density': 'very high'
                },
                'structure': ['executive summary', 'background', 'methodology', 'findings', 'policy implications']
            },
            'media': {
                'tone': 'concise, factual, headline-ready',
                'length': {
                    'wordRange': '250-600',
                    'readingTime': '1-3 min',
                    'density': 'high'
                },
                'structure': ['key message', 'top statistics', 'context', 'why it matters']
            }
        }
        
        config = default_configs.get(audience, default_configs['internal'])
        
        return {
            'audience': audience,
            'document_type': document_type or 'technical_report',
            'config': config,
            'default_type': 'technical_report'
        }
    
    @staticmethod
    def _get_default_types(audience: str) -> List[str]:
        """Get default document types when ANALYSIS_CONFIG is not available."""
        audience = AudienceConfigManager.validate_audience(audience)
        
        default_types = {
            'internal': ['technical_report', 'long_read', 'executive_summary'],
            'public_donors': ['executive_summary', 'long_read', 'social_media'],
            'private_donors': ['executive_summary', 'long_read', 'linkedin_post'],
            'government': ['technical_report', 'executive_summary', 'long_read'],
            'media': ['executive_summary', 'long_read', 'social_media']
        }
        
        return default_types.get(audience, default_types['internal'])
    
    @staticmethod
    def _get_default_type(audience: str) -> str:
        """Get default document type when ANALYSIS_CONFIG is not available."""
        audience = AudienceConfigManager.validate_audience(audience)
        
        default_types = {
            'internal': 'technical_report',
            'public_donors': 'executive_summary',
            'private_donors': 'executive_summary',
            'government': 'technical_report',
            'media': 'executive_summary'
        }
        
        return default_types.get(audience, 'technical_report')


class CrewAIConfig:
    """
    Global configuration for CrewAI integration.
    
    This class provides centralized configuration for all CrewAI components.
    """
    
    # CrewAI settings
    VERBOSE = True
    MAX_ITER = 10
    MEMORY_ENABLED = True
    ALLOW_DELEGATION = True
    CACHE_ENABLED = True
    
    # Execution settings
    TIMEOUT_SECONDS = 30
    MAX_RETRIES = 3
    PARALLEL_TASKS = 2
    
    # Logging settings
    LOG_LEVEL = "INFO"
    LOG_FORMAT = "%(asctime)s - %(name)s - %(levelname)s - %(message)s"
    
    # RAG settings (for enriched story generation)
    RAG_ENABLED = True
    RAG_TOP_K = 5
    RAG_FETCH_K = 20
    RAG_RERANK = True
    
    # Quarto settings
    QUARTO_INCLUDE_CODE = False
    QUARTO_USE_THEME = True
    QUARTO_USE_STYLE = True
    
    @classmethod
    def load_from_env(cls):
        """Load configuration from environment variables."""
        import os
        
        # CrewAI settings
        cls.VERBOSE = os.getenv("CREWAI_VERBOSE", "true").lower() == "true"
        cls.MAX_ITER = int(os.getenv("CREWAI_MAX_ITER", "10"))
        cls.MEMORY_ENABLED = os.getenv("CREWAI_MEMORY", "true").lower() == "true"
        cls.ALLOW_DELEGATION = os.getenv("CREWAI_DELEGATION", "true").lower() == "true"
        cls.CACHE_ENABLED = os.getenv("CREWAI_CACHE", "true").lower() == "true"
        
        # Execution settings
        cls.TIMEOUT_SECONDS = int(os.getenv("CREWAI_TIMEOUT", "30"))
        cls.MAX_RETRIES = int(os.getenv("CREWAI_RETRIES", "3"))
        cls.PARALLEL_TASKS = int(os.getenv("CREWAI_PARALLEL", "2"))
        
        # Logging settings
        cls.LOG_LEVEL = os.getenv("CREWAI_LOG_LEVEL", "INFO")
        
        # RAG settings
        cls.RAG_ENABLED = os.getenv("CREWAI_RAG_ENABLED", "true").lower() == "true"
        cls.RAG_TOP_K = int(os.getenv("CREWAI_RAG_TOP_K", "5"))
        cls.RAG_FETCH_K = int(os.getenv("CREWAI_RAG_FETCH_K", "20"))
        cls.RAG_RERANK = os.getenv("CREWAI_RAG_RERANK", "true").lower() == "true"
        
        # Quarto settings
        cls.QUARTO_INCLUDE_CODE = os.getenv("QUARTO_INCLUDE_CODE", "false").lower() == "true"
        cls.QUARTO_USE_THEME = os.getenv("QUARTO_USE_THEME", "true").lower() == "true"
        cls.QUARTO_USE_STYLE = os.getenv("QUARTO_USE_STYLE", "true").lower() == "true"


# Load configuration from environment
CrewAIConfig.load_from_env()
