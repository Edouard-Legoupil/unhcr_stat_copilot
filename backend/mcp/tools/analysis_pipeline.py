"""
Tool: analysis_pipeline
Enhanced analysis pipeline that leverages all available tools.

This module provides orchestration for the complete analysis workflow,
integrating statistical analysis, compliance validation, visualization,
and story generation.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def run_enhanced_analysis_pipeline(
    question: str,
    data: dict,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    analysis_config: Optional[dict] = None,
    use_rag: bool = False,
    rag_retriever: Any = None
) -> dict:
    """
    Run the complete analysis pipeline with all tools.
    
    This orchestrator integrates:
    - Statistical analysis (analyze_data_statistics)
    - Compliance validation (apply_analysis_guardrails)
    - Visualization structure extraction (extract_visualization_structure)
    - Visualization description generation (generate_visualization_description)
    - AI-powered story generation (generate_ai_data_story or generate_analytical_story)
    
    Args:
        question: User's original question
        data: Retrieved data from get_data_for_story or other data source
        audience: Target audience for the analysis
        document_type: Document type (e.g., 'long_read', 'technical_report')
        analysis_config: Analysis configuration dictionary
        use_rag: Whether to use RAG-enriched story generation
        rag_retriever: Optional RAG retriever instance for LLM-based stories
    
    Returns:
        Enhanced story with statistics, guardrails, and visualization descriptions
    """
    # Validate inputs
    if not data:
        return {
            'error': 'No data provided for analysis pipeline',
            'status': 'error'
        }
    
    if not question:
        return {
            'error': 'No question provided for analysis pipeline',
            'status': 'error'
        }
    
    # Extract items from nested data structure
    items = []
    data_field = data.get('data', data) if isinstance(data, dict) else data
    
    if isinstance(data_field, dict):
        items = data_field.get('items', [])
    elif isinstance(data_field, list):
        items = data_field
    
    # Determine data type
    data_type = data.get('data_type', 'unknown') if isinstance(data, dict) else 'unknown'
    
    # Phase 1: Statistical Analysis
    # Calculate stats (mean, median, std, correlations) for numeric data
    stats_result = None
    try:
        from backend.mcp.tools.analyze_data_statistics import analyze_data_statistics_tool
        from backend.mcp.tools.semantic_constants import is_identifier_field
        
        if items and isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
            # Extract numeric columns (exclude IDs and codes)
            numeric_cols = [
                k for k, v in items[0].items()
                if isinstance(v, (int, float))
                and not (is_identifier_field(k) or any(skip in k.lower() for skip in ['iso', 'hst', 'ooc', 'oip']))
            ]
            
            # Extract categorical columns (exclude identifier fields)
            categorical_cols = [
                k for k, v in items[0].items()
                if isinstance(v, str) 
                and any(cat in k.lower() for cat in ['year', 'coo', 'coa', 'name'])
                and not is_identifier_field(k)  # Exclude identifier fields
            ]
            
            if numeric_cols:
                # Note: analyze_data_statistics_tool is synchronous, not async
                stats_result = analyze_data_statistics_tool(
                    data=items,
                    numeric_columns=numeric_cols,
                    categorical_columns=categorical_cols if categorical_cols else None
                )
                logger.info("Completed statistical analysis")
    except Exception as e:
        logger.warning(f"Statistical analysis failed: {e}")
        # Continue without statistics - non-blocking
        stats_result = None
    
    # Phase 2: Compliance Validation
    # Validate data against UNHCR methodology standards
    guardrails_result = None
    try:
        from backend.mcp.tools.apply_analysis_guardrails import apply_analysis_guardrails_tool
        
        data_fields = list(items[0].keys()) if items and isinstance(items[0], dict) else []
        
        # Note: apply_analysis_guardrails_tool is synchronous, not async
        guardrails_result = apply_analysis_guardrails_tool(
            analysis_request={
                'context': question,
                'data_fields': data_fields
            },
            population_type=data_type,
            country_iso=data.get('parameters', {}).get('coo') if isinstance(data, dict) else None
        )
        logger.info("Completed compliance validation")
    except Exception as e:
        logger.warning(f"Compliance validation failed: {e}")
        # Continue without guardrails - non-blocking
        guardrails_result = None
    
    # Phase 3: Visualization Structure
    # Extract metadata from visualizations
    visualization_structure = None
    try:
        from backend.mcp.tools.extract_visualization_structure import extract_visualization_structure_tool
        
        # Auto-detect visualization type and labels from data
        viz_type = "line_chart"  # Default
        viz_title = f"Analysis: {question[:100]}"
        
        # Try to detect axis labels from data
        x_label = "Year"
        y_label = "Count"
        
        if items and isinstance(items, list) and len(items) > 0 and isinstance(items[0], dict):
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
        
        visualization_structure = extract_visualization_structure_tool(
            visualization_type=viz_type,
            title=viz_title,
            x_axis_label=x_label,
            y_axis_label=y_label
        )
        logger.info("Extracted visualization structure")
    except Exception as e:
        logger.warning(f"Visualization structure extraction failed: {e}")
        # Continue without structure - non-blocking
        visualization_structure = None
    
    # Phase 4: Generate visualization descriptions
    visualization_description = None
    try:
        from backend.mcp.tools.generate_visualization_description import generate_visualization_description_tool
        
        if visualization_structure and stats_result:
            visualization_description = await generate_visualization_description_tool(
                structure=visualization_structure,
                statistics=stats_result,
                description_type="detailed",
                max_length=500,
                focus_areas=["trends", "comparisons", "outliers"]
            )
            logger.info("Generated visualization description")
    except Exception as e:
        logger.warning(f"Visualization description generation failed: {e}")
        # Continue without description - non-blocking
        visualization_description = None
    
    # Phase 5: Generate enhanced story
    # Pass all enriched data to story generator
    enhanced_data = {
        **data,
        'statistics': stats_result,
        'guardrails': guardrails_result,
        'visualization_structure': visualization_structure,
        'visualization_description': visualization_description,
        'compliance_score': guardrails_result.get('compliance_percentage', 0) if guardrails_result else 0
    }
    
    # Choose story generator based on configuration
    if use_rag and rag_retriever:
        # Use AI-powered story generation with RAG enrichment
        try:
            from backend.mcp.tools.generate_ai_data_story import generate_ai_data_story_tool
            
            story_result = await generate_ai_data_story_tool(
                rag_retriever=rag_retriever,
                visualization_data=enhanced_data,
                context=question,
                story_type='analytical',
                apply_guardrails=analysis_config.get('apply_guardrails', True) if analysis_config else True,
                use_report_context=True,
                max_tokens=analysis_config.get('max_tokens', 500) if analysis_config else 500
            )
            
            if story_result and isinstance(story_result, dict):
                return {
                    **story_result,
                    'enhanced_data': enhanced_data,
                    'pipeline_phases': ['statistics', 'guardrails', 'visualization', 'story'],
                    'status': 'success'
                }
        except Exception as e:
            logger.warning(f"AI data story generation failed: {e}, falling back to analytical story")
    
    # Fallback: Use template-based analytical story generator
    try:
        from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
        
        story_result = await generate_analytical_story_tool(
            result=enhanced_data,
            data=enhanced_data,
            question=question,
            audience=audience,
            document_type=document_type,
            analysis_config=analysis_config
        )
        
        if story_result and isinstance(story_result, dict):
            return {
                **story_result,
                'enhanced_data': enhanced_data,
                'pipeline_phases': ['statistics', 'guardrails', 'visualization', 'story'],
                'status': 'success'
            }
    except Exception as e:
        logger.error(f"Analytical story generation failed: {e}")
        return {
            'error': f'Story generation failed: {str(e)}',
            'status': 'error',
            'enhanced_data': enhanced_data
        }
    
    # Final fallback
    return {
        'error': 'No story generator available',
        'status': 'error',
        'enhanced_data': enhanced_data
    }


async def run_conditional_analysis_pipeline(
    question: str,
    data: dict,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    analysis_config: Optional[dict] = None,
    use_enhanced: bool = False,
    rag_retriever: Any = None
) -> dict:
    """
    Run conditional analysis pipeline - use enhanced for complex queries, simple for basic ones.
    
    This implements Option C from the refactoring plan - use enhanced pipeline for complex queries,
    simple pipeline for basic ones.
    
    Args:
        question: User's original question
        data: Retrieved data
        audience: Target audience
        document_type: Document type
        analysis_config: Analysis configuration
        use_enhanced: Force enhanced pipeline (if True) or simple pipeline (if False)
        rag_retriever: Optional RAG retriever for LLM-based stories
    
    Returns:
        Generated story with appropriate level of enrichment
    """
    # Determine if we should use enhanced pipeline
    if use_enhanced is None:
        # Auto-detect based on question complexity
        # Use enhanced for questions that suggest deep analysis
        complex_keywords = [
            'analyze', 'trends', 'comparison', 'correlation', 'relationship',
            'pattern', 'insight', 'deep dive', 'comprehensive', 'detailed'
        ]
        question_lower = question.lower()
        use_enhanced = any(keyword in question_lower for keyword in complex_keywords)
    
    if use_enhanced:
        logger.info("Using enhanced analysis pipeline for complex query")
        # Use the full enhanced pipeline
        result = await run_enhanced_analysis_pipeline(
            question=question,
            data=data,
            audience=audience,
            document_type=document_type,
            analysis_config=analysis_config,
            use_rag=rag_retriever is not None,
            rag_retriever=rag_retriever
        )
        return result
    else:
        logger.info("Using simple analysis pipeline for basic query")
        # Use simplified pipeline - just generate analytical story without extra enrichment
        try:
            from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
            
            story_result = await generate_analytical_story_tool(
                result=data,
                data=data,
                question=question,
                audience=audience,
                document_type=document_type,
                analysis_config=analysis_config
            )
            
            return {
                **story_result,
                'pipeline_phases': ['story'],
                'pipeline_type': 'simple',
                'status': 'success'
            }
        except Exception as e:
            logger.error(f"Simple story generation failed: {e}")
            return {
                'error': f'Story generation failed: {str(e)}',
                'status': 'error'
            }
