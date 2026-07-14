"""
Tool: generate_analytical_story
Generate analytical stories and narratives from UNHCR data with optional RAG enrichment.

This is the unified story generation tool that combines the functionality of both
generate_analytical_story and generate_ai_data_story, with RAG support enabled by default
and graceful fallback logging.
"""

import json
import logging
from datetime import datetime
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def generate_analytical_story_tool(
    result: Optional[dict] = None,
    data: Optional[dict] = None,
    question: str = "",
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    analysis_config: Optional[dict] = None,
    # RAG parameters - enabled by default with graceful fallback
    use_rag: bool = True,
    rag_retriever: Any = None,
    rag_top_k: int = 5,
    rag_fetch_k: int = 20,
    rag_rerank: bool = False,
    rag_year: Optional[str] = None,
    rag_report_type: Optional[str] = None,
    rag_section_contains: Optional[str] = None,
    rag_exclude_figures_tables: bool = False,
    # Additional parameters for backwards compatibility with generate_ai_data_story
    context: Optional[str] = None,
    story_type: str = "analytical",
    max_tokens: int = 500,
    apply_guardrails: bool = True,
) -> dict[str, Any]:
    """
    Generate analytical stories from data results with optional RAG enrichment.
    
    Uses either LLM-based story generation (if Azure OpenAI is configured)
    or a fallback template-based approach. RAG is attempted by default when
    rag_retriever is available, with graceful fallback and logging.
    
    Args:
        result: Data result from previous analysis
        data: Alternative name for result
        question: Original user question
        audience: Target audience for the analysis
        document_type: Type of document being generated
        analysis_config: Analysis configuration
        use_rag: Whether to attempt RAG-enriched generation (default: True)
        rag_retriever: Optional UNHCRVectorRetriever instance for RAG enrichment
        rag_top_k: Number of top results to retrieve
        rag_fetch_k: Number of results to fetch before re-ranking
        rag_rerank: Whether to use re-ranking
        rag_year: Filter RAG results by year
        rag_report_type: Filter RAG results by report type
        rag_section_contains: Filter RAG results by section content
        rag_exclude_figures_tables: Exclude figures and tables from RAG results
        context: Additional context for story generation (backwards compat)
        story_type: Type of story to generate
        max_tokens: Maximum tokens for LLM generation
        apply_guardrails: Whether to apply UNHCR methodology guardrails
    
    Returns:
        Dictionary containing the generated story, metadata, and fallback information
    """
    # Track attempt history for observability
    attempt_history = []
    
    # Extract parameters - use result if provided, otherwise data
    if result is None:
        result = data
    
    # Use context if provided, otherwise question
    generation_context = context or question
    
    # Extract analysis configuration if available
    tone = None
    length_config = None
    structure = None
    if analysis_config and isinstance(analysis_config, dict):
        tone = analysis_config.get("tone")
        length_config = analysis_config.get("length")
        structure = analysis_config.get("structure")
    
    try:
        story_content = None
        
        # Attempt 1: RAG-enriched LLM generation (if enabled and retriever available)
        if use_rag and rag_retriever is not None:
            attempt_history.append({
                "attempt": 1,
                "method": "rag_llm",
                "timestamp": datetime.now().isoformat(),
                "status": "attempting"
            })
            try:
                from backend.llm import generate_story_from_data
                from backend.mcp.common import summarize_retrieved_context_for_story
                
                # Retrieve RAG context
                rag_query = rag_retriever.formulate_query(
                    user_request=generation_context,
                    data_summary=json.dumps(result, default=str)[:500] if result else None
                )
                
                retrieved_chunks = rag_retriever.retrieve(
                    query=rag_query,
                    top_k=rag_top_k,
                    fetch_k=rag_fetch_k,
                    year=rag_year,
                    report_type=rag_report_type,
                    section_contains=rag_section_contains,
                    exclude_figures_tables=rag_exclude_figures_tables,
                    rerank=rag_rerank
                )
                
                # Summarize retrieved context for LLM
                rag_context = ""
                if retrieved_chunks:
                    chunk_texts = [chunk.text for chunk in retrieved_chunks]
                    rag_context = summarize_retrieved_context_for_story(
                        "\n\n".join(chunk_texts)
                    )
                
                # Prepare enriched prompt with RAG context
                if rag_context:
                    # Create a version of the data that includes RAG context
                    enriched_data = {
                        **result,
                        "rag_context": rag_context,
                        "rag_chunks": len(retrieved_chunks)
                    } if result else {"rag_context": rag_context}
                    
                    # Generate story with RAG-enriched data
                    story_content = await generate_story_from_data(
                        question=generation_context,
                        data=enriched_data,
                        audience=audience,
                        document_type=document_type,
                        tone=tone,
                        length_config=length_config,
                        structure=structure
                    )
                    
                    attempt_history[-1]["status"] = "success"
                    attempt_history[-1]["rag_chunks_retrieved"] = len(retrieved_chunks)
                    
                else:
                    # RAG available but no chunks retrieved - try without RAG
                    attempt_history[-1]["status"] = "no_rag_results"
                    story_content = None
                    
            except Exception as e:
                attempt_history[-1]["status"] = "failed"
                attempt_history[-1]["error"] = str(e)
                logger.warning(f"RAG-enriched LLM story generation failed: {e}")
                story_content = None
        
        # Attempt 2: Standard LLM generation (without RAG)
        if not story_content:
            attempt_history.append({
                "attempt": 2,
                "method": "llm",
                "timestamp": datetime.now().isoformat(),
                "status": "attempting"
            })
            try:
                from backend.llm import generate_story_from_data
                story_content = await generate_story_from_data(
                    question=generation_context,
                    data=result,
                    audience=audience,
                    document_type=document_type,
                    tone=tone,
                    length_config=length_config,
                    structure=structure
                )
                attempt_history[-1]["status"] = "success"
            except Exception as e:
                attempt_history[-1]["status"] = "failed"
                attempt_history[-1]["error"] = str(e)
                logger.warning(f"Standard LLM story generation failed: {e}")
                story_content = None
        
        # Attempt 3: Template-based generation
        if not story_content:
            attempt_history.append({
                "attempt": 3,
                "method": "template",
                "timestamp": datetime.now().isoformat(),
                "status": "attempting"
            })
            try:
                story_content = _generate_story_from_template(
                    question=generation_context,
                    result=result,
                    audience=audience,
                    document_type=document_type,
                    analysis_config=analysis_config
                )
                attempt_history[-1]["status"] = "success"
            except Exception as e:
                attempt_history[-1]["status"] = "failed"
                attempt_history[-1]["error"] = str(e)
                logger.warning(f"Template story generation failed: {e}")
                story_content = None
        
        if not story_content:
            # Final fallback - minimal story
            story_content = f"# Analysis: {generation_context}\n\nNo story could be generated. Please check the data and try again."
            attempt_history.append({
                "attempt": 4,
                "method": "minimal_fallback",
                "timestamp": datetime.now().isoformat(),
                "status": "success"
            })
        
        # Generate a better title from the question/context
        clean_question = generation_context
        for prefix in ["Generate an analysis of ", "Generate analysis of ", "Analyze ", "Analysis of ", "Generate ", "Create "]:
            if clean_question.startswith(prefix):
                clean_question = clean_question[len(prefix):]
        
        # Capitalize properly - title case with exceptions for small words
        words = clean_question.split()
        if words:
            # Small words to keep lowercase (unless first or last word)
            small_words = {'a', 'an', 'the', 'and', 'but', 'or', 'for', 'nor', 'as', 'at', 
                          'by', 'for', 'in', 'of', 'on', 'per', 'to', 'from', 'with'}
            title_words = []
            for i, word in enumerate(words):
                if not word:  # Skip empty strings
                    continue
                if i == 0 or i == len(words) - 1:
                    # Always capitalize first and last word
                    if len(word) == 1:
                        title_words.append(word.upper())
                    else:
                        title_words.append(word[0].upper() + word[1:].lower())
                elif word.lower() in small_words:
                    # Keep small words lowercase
                    title_words.append(word.lower())
                else:
                    # Capitalize other words
                    if len(word) == 1:
                        title_words.append(word.upper())
                    else:
                        title_words.append(word[0].upper() + word[1:].lower())
            title = ' '.join(title_words)
        else:
            title = clean_question
        
        # Ensure title has context - add prefix if it doesn't start with a proper noun
        title_words_list = title.split()
        first_word_lower = title_words_list[0].lower() if title_words_list else ""
        if first_word_lower not in ['refugees', 'refugee', 'displaced', 'asylum', 'migration', 'population', 'trends', 'data', 'analysis', 'unhcr']:
            title = f"UNHCR Analysis: {title}"
        
        # Log the story content for debugging
        logger.info(f"Generated story content (length: {len(story_content) if story_content else 0})")
        
        return {
            "title": title,
            "story": story_content,
            "story_type": story_type,
            "metadata": {
                "source": "UNHCR AI Story Generation",
                "question": generation_context,
                "data_type": result.get("data_type", "unknown") if result else "unknown",
                "timestamp": datetime.now().isoformat(),
                "generation_method": attempt_history[-1]["method"] if attempt_history else "unknown",
                "fallback_history": attempt_history,
                "rag_enabled": use_rag,
                "rag_available": rag_retriever is not None,
                "rag_used": any(a.get("method") == "rag_llm" and a.get("status") == "success" for a in attempt_history),
            },
            "status": "success",
            "warnings": [
                a for a in attempt_history if a.get("status") == "failed"
            ] if any(a.get("status") == "failed" for a in attempt_history) else None,
        }
    except Exception as e:
        logger.exception(f"Failed to generate analytical story: {e}")
        return {
            "error": f"Failed to generate analytical story: {str(e)}",
            "status": "error",
            "question": generation_context,
            "data_summary": str(result)[:200] if result else "No data",
            "metadata": {
                "fallback_history": attempt_history,
                "timestamp": datetime.now().isoformat()
            }
        }


def _generate_story_from_template(
    question: str,
    result: Optional[dict],
    audience: Optional[str],
    document_type: Optional[str],
    analysis_config: Optional[dict]
) -> str:
    """
    Generate a story using templates instead of LLM.
    
    Args:
        question: The original question
        result: Data result
        audience: Target audience
        document_type: Document type
        analysis_config: Analysis configuration
    
    Returns:
        Generated story content
    """
    # Extract structure from analysis_config or use defaults based on document_type
    structure = []
    if analysis_config and isinstance(analysis_config, dict):
        structure = analysis_config.get("structure", [])
    
    # If no structure from config, use document_type defaults
    if not structure and document_type:
        document_structures = {
            "long_read": [
                "introduction",
                "context", 
                "key findings",
                "deep dive analysis",
                "implications",
                "conclusion"
            ],
            "technical_report": [
                "abstract",
                "introduction",
                "methodology",
                "results",
                "discussion",
                "conclusion",
                "references"
            ],
            "executive_summary": [
                "executive summary",
                "key findings",
                "recommendations",
                "appendix"
            ]
        }
        structure = document_structures.get(document_type.lower(), [
            "introduction",
            "data overview",
            "key findings",
            "methodology",
            "conclusion"
        ])
    
    # If still no structure, use default
    if not structure:
        structure = [
            "introduction",
            "data overview",
            "key findings", 
            "methodology",
            "conclusion"
        ]
    
    # Build story components
    story_parts = []
    
    # Title - use the cleaned title that will be generated by the main function
    # For now, use a cleaned version of the question
    clean_q = question
    for prefix in ["Generate an analysis of ", "Generate analysis of ", "Analyze ", "Analysis of ", "Generate ", "Create "]:
        if clean_q.startswith(prefix):
            clean_q = clean_q[len(prefix):]
    story_parts.append(f"# Analysis: {clean_q}")
    story_parts.append("")
    
    # Generate sections based on structure
    for section in structure:
        section_title = section.title() if not section.startswith("#") else section.lstrip("# ").strip()
        section_level = 2
        
        # Count leading # to determine heading level
        if section.startswith("#"):
            section_level = len(section.split()[0]) if section.split() else 2
            section_title = section.lstrip("# ").strip()
        
        heading = "#" * section_level + " " + section_title
        story_parts.append(heading)
        story_parts.append("")
        
        # Generate content for each section
        section_content = _generate_section_content(
            section=section.lower(),
            question=question,
            result=result,
            audience=audience,
            document_type=document_type,
            analysis_config=analysis_config
        )
        
        if section_content:
            story_parts.append(section_content)
            story_parts.append("")
    
    return "\n".join(story_parts)


def _generate_section_content(
    section: str,
    question: str,
    result: Optional[dict],
    audience: Optional[str],
    document_type: Optional[str],
    analysis_config: Optional[dict]
) -> str:
    """
    Generate content for a specific section based on the section name and available data.
    
    Args:
        section: Section name (lowercase)
        question: The original question
        result: Data result
        audience: Target audience
        document_type: Document type
        analysis_config: Analysis configuration
    
    Returns:
        Content for the section
    """
    content_lines = []
    
    # Handle different section types
    if "introduction" in section:
        content_lines.append(f"This analysis addresses the question: **{question}**")
        if audience:
            content_lines.append(f"This report is prepared for a {audience} audience.")
        if document_type:
            content_lines.append(f"Document type: {document_type}")
            
    elif "context" in section:
        content_lines.append("This section provides contextual background for the analysis.")
        if result and isinstance(result, dict):
            if "metadata" in result:
                metadata = result.get("metadata", {})
                if "source" in metadata:
                    content_lines.append(f"Data source: {metadata['source']}")
                if "timespan" in metadata:
                    content_lines.append(f"Time period: {metadata['timespan']}")
        content_lines.append("The analysis is based on official UNHCR statistics and follows established methodological guidelines.")
        
    elif "data overview" in section or "data_overview" in section:
        if result and isinstance(result, dict):
            if "data" in result and isinstance(result["data"], list):
                content_lines.append(f"- **Records**: {len(result['data'])}")
            elif "data" in result and isinstance(result["data"], dict):
                content_lines.append(f"- **Data fields**: {list(result['data'].keys())}")
            
            if "data_type" in result:
                content_lines.append(f"- **Data type**: {result['data_type']}")
            
            if "question" in result:
                content_lines.append(f"- **Original question**: {result['question']}")
        else:
            content_lines.append("- No data available for detailed analysis")
            
    elif "key findings" in section or "findings" in section:
        if result and isinstance(result, dict):
            # Use enriched statistics if available from get_data_for_story
            if "statistics" in result and result["statistics"]:
                stats = result["statistics"].get("statistics", {})
                if stats:
                    content_lines.append("- **Statistical Analysis:**")
                    for field, stat_data in stats.items():
                        mean_val = stat_data.get('mean')
                        median_val = stat_data.get('median')
                        min_val = stat_data.get('min')
                        max_val = stat_data.get('max')
                        std_val = stat_data.get('std_dev')
                        count_val = stat_data.get('count')
                        
                        parts = []
                        if count_val is not None:
                            parts.append(f"n={count_val}")
                        if mean_val is not None:
                            parts.append(f"mean={mean_val:.2f}")
                        if median_val is not None:
                            parts.append(f"median={median_val:.2f}")
                        if min_val is not None and max_val is not None:
                            parts.append(f"range=[{min_val}, {max_val}]")
                        if std_val is not None:
                            parts.append(f"std={std_val:.2f}")
                        
                        if parts:
                            content_lines.append(f"  - **{field}**: {', '.join(parts)}")
                    
                    # Add correlations if available
                    correlations = result["statistics"].get("correlations", {})
                    if correlations:
                        content_lines.append("- **Correlations:**")
                        for corr_key, corr_data in correlations.items():
                            if isinstance(corr_data, dict):
                                content_lines.append(f"  - {corr_key}: r={corr_data.get('pearson_correlation', 0):.3f}, "
                                                   f"p={corr_data.get('p_value', 0):.4f}")
            
            # Use guardrails compliance if available
            if "guardrails" in result and result["guardrails"]:
                guardrails = result["guardrails"]
                overall_compliant = guardrails.get("overall_compliant", False)
                compliance_pct = guardrails.get("compliance_percentage", 0)
                compliance_level = guardrails.get("compliance_level", "UNKNOWN")
                
                status_icon = "✓" if overall_compliant else "✗"
                content_lines.append(f"- **UNHCR Compliance**: {status_icon} {compliance_pct:.0f}% ({compliance_level})")
                
                # Add specific compliance details
                if not overall_compliant:
                    content_lines.append("  - *Recommendations available for improvement*")
            
            if "data" in result:
                data = result["data"]
                if isinstance(data, list) and len(data) > 0:
                    content_lines.append("- Data retrieved successfully")
                    content_lines.append(f"- Total entries: {len(data)}")
                    
                    # Show sample of first few items
                    if len(data) > 0:
                        sample = data[0]
                        if isinstance(sample, dict):
                            content_lines.append("- Sample data structure:")
                            for key, value in list(sample.items())[:5]:
                                content_lines.append(f"  - {key}: {value}")
                elif isinstance(data, dict):
                    # Check if this is a UNHCR API response with items
                    if "items" in data and isinstance(data["items"], list):
                        items = data["items"]
                        content_lines.append(f"- Data retrieved: {len(items)} records")
                        
                        # Extract meaningful statistics from items
                        if len(items) > 0 and isinstance(items[0], dict):
                            # Try to find numeric fields for analysis
                            numeric_fields = []
                            year_field = None
                            for key, value in items[0].items():
                                if isinstance(value, (int, float)) and not any(skip in key.lower() for skip in ['id', '_id', 'iso']):
                                    numeric_fields.append(key)
                                if 'year' in key.lower():
                                    year_field = key
                            
                            if numeric_fields:
                                content_lines.append(f"- Key metrics available: {', '.join(numeric_fields)}")
                            
                            if year_field:
                                years = [str(item.get(year_field)) for item in items if item.get(year_field)]
                                if years:
                                    content_lines.append(f"- Time range: {min(years)} to {max(years)}")
                        
                        # Show summary statistics for numeric fields
                        if len(items) > 0 and isinstance(items[0], dict):
                            numeric_data = {}
                            for item in items:
                                for key in numeric_fields:
                                    val = item.get(key)
                                    if isinstance(val, (int, float)):
                                        if key not in numeric_data:
                                            numeric_data[key] = []
                                        numeric_data[key].append(val)
                            
                            for field, values in numeric_data.items():
                                if values:
                                    content_lines.append(f"- {field}: min={min(values)}, max={max(values)}, avg={sum(values)/len(values):.1f}")
                    else:
                        # Generic dict handling - but exclude large values
                        content_lines.append("- Data structure:")
                        for key, value in list(data.items())[:10]:
                            # Don't include large lists or dicts
                            if isinstance(value, (list, dict)) and len(str(value)) > 200:
                                content_lines.append(f"  - {key}: [{len(value) if isinstance(value, (list, dict)) else type(value).__name__} items]")
                            else:
                                content_lines.append(f"  - {key}: {value}")
        else:
            content_lines.append("- No specific findings available from the data")
            
    elif "deep dive" in section or "analysis" in section:
        content_lines.append("This section provides a detailed examination of the data and trends.")
        if result and isinstance(result, dict):
            if "data" in result:
                data = result["data"]
                if isinstance(data, list) and len(data) > 1:
                    content_lines.append(f"The dataset contains {len(data)} records spanning multiple periods.")
                    # Try to identify time-based data
                    if data and isinstance(data[0], dict):
                        year_cols = [k for k in data[0].keys() if 'year' in k.lower()]
                        if year_cols:
                            years = [str(item.get(year_cols[0])) for item in data if item.get(year_cols[0])]
                            if years:
                                content_lines.append(f"Time range: {min(years) if years else 'N/A'} to {max(years) if years else 'N/A'}")
                elif isinstance(data, dict):
                    # Check if this is a UNHCR API response with items
                    if "items" in data and isinstance(data["items"], list) and len(data["items"]) > 1:
                        items = data["items"]
                        content_lines.append(f"The dataset contains {len(items)} records spanning multiple periods.")
                        # Try to identify time-based data
                        if items and isinstance(items[0], dict):
                            year_cols = [k for k in items[0].keys() if 'year' in k.lower()]
                            if year_cols:
                                years = [str(item.get(year_cols[0])) for item in items if item.get(year_cols[0])]
                                if years:
                                    content_lines.append(f"Time range: {min(years)} to {max(years)}")
                            
                            # Analyze trends for numeric fields
                            numeric_fields = []
                            for key, value in items[0].items():
                                if isinstance(value, (int, float)) and not any(skip in key.lower() for skip in ['id', '_id', 'iso']):
                                    numeric_fields.append(key)
                            
                            if numeric_fields:
                                content_lines.append("Trend analysis:")
                                for field in numeric_fields:
                                    values = [item.get(field) for item in items if isinstance(item.get(field), (int, float))]
                                    if len(values) > 1:
                                        # Calculate trend direction
                                        if values[-1] > values[0]:
                                            trend = "increasing"
                                        elif values[-1] < values[0]:
                                            trend = "decreasing"
                                        else:
                                            trend = "stable"
                                        change = values[-1] - values[0]
                                        pct_change = (change / values[0] * 100) if values[0] != 0 else 0
                                        content_lines.append(f"  - {field}: {trend} trend ({change:+.0f} total, {pct_change:+.1f}% change)")
        
    elif "methodology" in section:
        content_lines.append("- Data sourced from UNHCR official statistics")
        content_lines.append("- Analysis follows UNHCR methodological guidelines")
        content_lines.append("- All data is aggregate-level only")
        if analysis_config and isinstance(analysis_config, dict):
            if "tone" in analysis_config:
                content_lines.append(f"- Analysis tone: {analysis_config['tone']}")
        
        # Add guardrails compliance details if available
        if result and isinstance(result, dict) and "guardrails" in result and result["guardrails"]:
            guardrails = result["guardrails"]
            content_lines.append("")
            content_lines.append("- **Compliance Details:**")
            
            # Population definition compliance
            if 'population_definition' in guardrails:
                pop_comp = guardrails['population_definition']
                content_lines.append(f"  - Population definition: {'✓ Compliant' if pop_comp.get('compliant') else '✗ Non-compliant'}")
            
            # Country code validation
            if 'country_code' in guardrails:
                country_comp = guardrails['country_code']
                content_lines.append(f"  - Country code: {'✓ Valid' if country_comp.get('compliant') else '✗ Invalid'}")
            
            # Data disaggregation
            if 'data_disaggregation' in guardrails:
                disagg_comp = guardrails['data_disaggregation']
                content_lines.append(f"  - Data disaggregation: {'✓ Compliant' if disagg_comp.get('compliant') else '✗ Needs improvement'}")
            
            # Data completeness
            if 'data_completeness' in guardrails:
                complete_comp = guardrails['data_completeness']
                content_lines.append(f"  - Data completeness: {'✓ Complete' if complete_comp.get('compliant') else '✗ Incomplete'}")
            
            # Data consistency
            if 'data_consistency' in guardrails:
                consistent_comp = guardrails['data_consistency']
                content_lines.append(f"  - Data consistency: {'✓ Consistent' if consistent_comp.get('compliant') else '✗ Inconsistent'}")
            
            # Storytelling guardrails
            if 'storytelling_guardrails' in guardrails:
                story_comp = guardrails['storytelling_guardrails']
                content_lines.append(f"  - Terminology: {'✓ Compliant' if story_comp.get('compliant') else '✗ Needs review'}")
                
    elif "implications" in section:
        content_lines.append("This section explores the implications of the findings.")
        if result and isinstance(result, dict):
            data_type = result.get("data_type", "unknown")
            content_lines.append(f"The {data_type} data suggests several important implications for policy and practice.")
            
            # Add data-specific implications
            if "data" in result:
                data = result["data"]
                if isinstance(data, dict) and "items" in data and isinstance(data["items"], list):
                    items = data["items"]
                    if len(items) > 0 and isinstance(items[0], dict):
                        # Check for displacement-related fields
                        displacement_fields = [k for k in items[0].keys() if k.lower() in ['refugees', 'asylum_seekers', 'idps', 'returned_refugees', 'stateless']]
                        if displacement_fields:
                            content_lines.append("- Population trends indicate changing displacement patterns that may require resource reallocation")
                        
                        # Check for year field - if time series, add temporal implications
                        year_fields = [k for k in items[0].keys() if 'year' in k.lower()]
                        if year_fields and len(items) > 1:
                            content_lines.append("- Temporal analysis reveals evolving situations that necessitate ongoing monitoring")
                            
            content_lines.append("- Humanitarian response may need to be adjusted based on these trends")
            content_lines.append("- Further analysis is recommended to understand root causes")
        
    elif "conclusion" in section:
        content_lines.append(f"This analysis provides insights into {question.lower()}. For more detailed")
        content_lines.append("analysis, please refine your query or contact a data specialist.")
        
    elif "abstract" in section:
        content_lines.append(f"**Abstract:** This analysis examines {question.lower()} using UNHCR data.")
        content_lines.append("The study provides insights into refugee and displacement trends.")
        
    elif "executive summary" in section:
        content_lines.append(f"**Executive Summary:** This report presents key findings from the analysis of {question.lower()}.")
        
    elif "recommendations" in section:
        content_lines.append("Based on the analysis, the following recommendations are proposed:")
        content_lines.append("- Conduct further investigation into identified trends")
        content_lines.append("- Share findings with relevant stakeholders")
        content_lines.append("- Consider policy adjustments based on emerging patterns")
        
    elif "discussion" in section:
        content_lines.append("This section discusses the results in the context of broader refugee and displacement issues.")
        
    elif "references" in section:
        content_lines.append("**References**")
        content_lines.append("- UNHCR Population Statistics Database")
        content_lines.append("- UNHCR Methodological Guidelines")
        
    elif "appendix" in section:
        content_lines.append("**Appendix:** Additional technical details and supplementary information can be provided upon request.")
        
    else:
        # Default content for unknown sections
        content_lines.append(f"This section provides information related to {section}.")
    
    return "\n".join(content_lines)
