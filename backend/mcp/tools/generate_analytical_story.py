"""
Tool: generate_analytical_story
Generate analytical stories and narratives from UNHCR data.
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
) -> dict[str, Any]:
    """
    Generate analytical stories from data results.
    
    Uses either LLM-based story generation (if Azure OpenAI is configured)
    or a fallback template-based approach.
    
    Args:
        result: Data result from previous analysis
        data: Alternative name for result
        question: Original user question
        audience: Target audience for the analysis
        document_type: Type of document being generated
        analysis_config: Analysis configuration
    
    Returns:
        Dictionary containing the generated story and metadata
    """
    # Extract parameters - use result if provided, otherwise data
    if result is None:
        result = data
    
    # Extract analysis configuration if available
    tone = None
    length_config = None
    structure = None
    if analysis_config and isinstance(analysis_config, dict):
        tone = analysis_config.get("tone")
        length_config = analysis_config.get("length")
        structure = analysis_config.get("structure")
    
    try:
        # Try LLM-based story generation first
        story_content = None
        try:
            # Import inside try block to handle import-time errors
            from backend.llm import generate_story_from_data
            story_content = await generate_story_from_data(
                question, result, 
                audience=audience, 
                document_type=document_type,
                tone=tone,
                length_config=length_config,
                structure=structure
            )
        except Exception as e:
            logger.debug(f"LLM story generation failed: {e}, falling back to template-based approach")
            # Fallback to template-based story generation
            story_content = _generate_story_from_template(question, result, audience, document_type, analysis_config)
        
        if not story_content:
            # If somehow we still don't have content, use template
            story_content = _generate_story_from_template(question, result, audience, document_type, analysis_config)
        
        # Generate a better title from the question
        # Remove "Generate an analysis of" or similar prefixes
        clean_question = question
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
                if i == 0 or i == len(words) - 1:
                    # Always capitalize first and last word
                    title_words.append(word[0].upper() + word[1:].lower())
                elif word.lower() in small_words:
                    # Keep small words lowercase
                    title_words.append(word.lower())
                else:
                    # Capitalize other words
                    title_words.append(word[0].upper() + word[1:].lower())
            title = ' '.join(title_words)
        else:
            title = clean_question
        
        # Ensure title has context - add prefix if it doesn't start with a proper noun
        first_word_lower = title.split()[0].lower() if title.split() else ""
        if first_word_lower not in ['refugees', 'refugee', 'displaced', 'asylum', 'migration', 'population', 'trends', 'data', 'analysis', 'unhcr']:
            title = f"UNHCR Analysis: {title}"
        
        return {
            "title": title,
            "story": story_content,
            "story_type": "analytical",
            "metadata": {
                "source": "UNHCR AI Story Generation",
                "question": question,
                "data_type": result.get("data_type", "unknown") if result else "unknown",
                "timestamp": datetime.now().isoformat()
            },
            "status": "success"
        }
    except Exception as e:
        logger.exception(f"Failed to generate analytical story: {e}")
        return {
            "error": f"Failed to generate analytical story: {str(e)}",
            "status": "error",
            "question": question,
            "data_summary": str(result)[:200] if result else "No data"
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
                
    elif "implications" in section:
        content_lines.append("This section explores the implications of the findings.")
        if result and isinstance(result, dict):
            data_type = result.get("data_type", "unknown")
            content_lines.append(f"The {data_type} data suggests several important implications for policy and practice.")
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
