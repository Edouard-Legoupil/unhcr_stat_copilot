"""
Workflow Tools for UNHCR Statistics Copilot

This module provides composite "meta-tools" that orchestrate multiple underlying tools
to provide complete, end-to-end workflows for common analysis tasks.

These workflows provide higher-level abstractions that reduce the complexity for
AI agents and external consumers of the MCP server.
"""

import logging
from typing import Any, Optional

logger = logging.getLogger(__name__)


async def full_analysis_workflow_tool(
    question: str,
    origin: Optional[str] = None,
    destination: Optional[str] = None,
    topic: Optional[str] = None,
    timespan: Optional[str] = None,
    year: Optional[str | int] = None,
    years: Optional[str] = None,
    population_types: Optional[list[str]] = None,
    coo_all: bool = False,
    coa_all: bool = False,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
    style: Optional[str] = None,
    use_enhanced: bool = True,
    use_rag: bool = False,
    rag_retriever: Any = None,
    include_notebook: bool = True,
    include_html: bool = True,
    include_pdf: bool = True,
    output_path: Optional[str] = None,
) -> dict[str, Any]:
    """
    Complete end-to-end analysis workflow: question → data → enrichment → story → notebook
    
    This is the highest-level workflow that orchestrates all steps of the analysis:
    1. Question classification and tool selection (safe_tool_selection)
    2. Data retrieval and enrichment (get_data_for_story)
    3. Story generation (generate_analytical_story with unified RAG support)
    4. Quarto notebook creation (create_quarto_notebook)
    
    Args:
        question: The user's analysis question
        origin: Country of origin (optional, extracted from question if not provided)
        destination: Destination country (optional, extracted from question if not provided)
        topic: Analysis topic (optional, extracted from question if not provided)
        timespan: Time span for analysis (optional, extracted from question if not provided)
        year: Specific year (optional)
        years: Multiple years (optional)
        population_types: List of population types to include (optional)
        coo_all: Get all origin countries (optional)
        coa_all: Get all asylum countries (optional)
        audience: Target audience for the analysis (optional, default: "internal")
        document_type: Type of document to generate (optional, default: "long_read")
        style: Writing style (optional, default: "formal")
        use_enhanced: Whether to use enhanced analysis pipeline (default: True)
        use_rag: Whether to use RAG-enriched story generation (default: False)
                 Requires rag_retriever to be provided
        rag_retriever: Optional RAG retriever instance for LLM-based story generation
        include_notebook: Whether to include Quarto notebook in output (default: True)
        include_html: Whether to render HTML (default: True)
        include_pdf: Whether to render PDF (default: True)
        output_path: Optional path for the Quarto notebook (default: auto-generated)
    
    Returns:
        Complete analysis result including:
        - data: Retrieved and enriched data
        - story: Generated analytical story (template-based or RAG-enriched)
        - notebook: Generated Quarto notebook (if include_notebook=True)
        - metadata: Full workflow metadata and observability data
    """
    try:
        from backend.mcp.tools.safe_tool_selection import safe_tool_selection_tool
        from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
        from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
        from backend.mcp.tools.create_quarto_notebook import create_quarto_notebook_tool
        from backend.mcp.common import UNHCRAPIClient
        from backend.question_parser import extract_question_parameters
        import os
        from datetime import datetime
        import uuid
        
        api_client = UNHCRAPIClient()
        
        # Track workflow execution
        workflow_sequence = []
        start_time = datetime.now()
        
        # Step 1: Question classification and parameter extraction
        logger.info(f"Step 1/4: Classifying question: {question[:100]}")
        
        # Extract parameters from question if not provided
        extracted_params = await extract_question_parameters(question)
        
        # Use provided parameters or extracted ones
        final_origin = origin or extracted_params.get("origin")
        final_destination = destination or extracted_params.get("destination")
        final_topic = topic or extracted_params.get("topic")
        final_timespan = timespan or extracted_params.get("timespan")
        
        # Handle list of countries by joining with comma
        if isinstance(final_origin, list):
            final_origin = ','.join(final_origin)
        if isinstance(final_destination, list):
            final_destination = ','.join(final_destination)
        
        # Merge with any additional parameters
        data_params = {
            'question': question,
            'coo': final_origin,
            'coa': final_destination,
            'year': year,
            'years': years,
            'population_types': population_types,
            'coo_all': coo_all,
            'coa_all': coa_all,
            'audience': audience or "internal",
            'document_type': document_type or "long_read",
            'origin': final_origin,
            'destination': final_destination,
            'topic': final_topic,
            'timespan': final_timespan,
        }
        
        # Filter out None values
        data_params = {k: v for k, v in data_params.items() if v is not None}
        
        # Step 1.5: Tool selection
        selection = await safe_tool_selection_tool(question)
        if selection and isinstance(selection, dict):
            # Merge selection parameters
            selection_params = selection.get("parameters", {})
            if selection_params:
                data_params.update(selection_params)
        
        workflow_sequence.append({
            "step": 1,
            "action": "question_classification",
            "timestamp": datetime.now().isoformat(),
            "duration_ms": 0
        })
        
        # Step 2: Data retrieval and enrichment
        logger.info(f"Step 2/4: Retrieving data for: {question[:100]}")
        step_2_start = datetime.now()
        
        data_result = await get_data_for_story_tool(
            api_client,
            **data_params
        )
        
        step_2_end = datetime.now()
        workflow_sequence[-1]["duration_ms"] = round((step_2_end - step_1_start).total_seconds() * 1000, 2)
        workflow_sequence.append({
            "step": 2,
            "action": "data_retrieval_and_enrichment",
            "timestamp": step_2_end.isoformat(),
            "duration_ms": round((step_2_end - step_2_start).total_seconds() * 1000, 2),
            "data_items": len(data_result.get("data", {}).get("items", [])) if isinstance(data_result.get("data"), dict) else 0
        })
        
        # Check for errors in data retrieval
        if data_result.get("error"):
            return {
                "status": "error",
                "error": data_result.get("error"),
                "question": question,
                "workflow": "full_analysis",
                "completed_steps": 2,
                "total_steps": 4
            }
        
        # Step 3: Story generation
        logger.info(f"Step 3/4: Generating story for: {question[:100]}")
        step_3_start = datetime.now()
        
        # Use unified story generator with RAG support
        # Build full analysis_config with defaults based on document_type
        full_analysis_config = analysis_config
        if document_type and not analysis_config:
            doc_configs = {
                "long_read": {
                    "tone": style or "analytical, narrative, engaging",
                    "length": {"wordRange": "1200-3000", "readingTime": "6-15 min", "density": "medium-high"},
                    "structure": ["introduction", "context", "key findings", "deep dive analysis", "implications", "conclusion"],
                    "document_type": document_type
                },
                "technical_report": {
                    "tone": style or "formal",
                    "length": {"wordRange": "2000-5000", "readingTime": "10-20 min", "density": "high"},
                    "structure": ["abstract", "introduction", "methodology", "results", "discussion", "conclusion", "references"],
                    "document_type": document_type
                },
                "executive_summary": {
                    "tone": style or "concise, action-oriented",
                    "length": {"wordRange": "500-1500", "readingTime": "3-8 min", "density": "medium"},
                    "structure": ["executive summary", "key findings", "recommendations", "appendix"],
                    "document_type": document_type
                }
            }
            full_analysis_config = doc_configs.get(document_type.lower(), {
                "tone": style or "formal",
                "document_type": document_type
            })
        
        # Generate story using unified tool with RAG enabled by default
        story_result = await generate_analytical_story_tool(
            result=data_result,
            data=data_result,
            question=question,
            audience=audience or "internal",
            document_type=document_type or "long_read",
            analysis_config=full_analysis_config,
            use_rag=use_rag,
            rag_retriever=rag_retriever if use_rag else None,
            rag_top_k=5,
            rag_fetch_k=20,
            rag_rerank=False,
            context=question
        )
        
        step_3_end = datetime.now()
        workflow_sequence.append({
            "step": 3,
            "action": "story_generation",
            "timestamp": step_3_end.isoformat(),
            "duration_ms": round((step_3_end - step_3_start).total_seconds() * 1000, 2),
            "story_length": len(story_result.get("story", ""))
        })
        
        # Check for errors in story generation
        if story_result.get("error"):
            return {
                "status": "error",
                "error": story_result.get("error"),
                "question": question,
                "data": data_result,
                "workflow": "full_analysis",
                "completed_steps": 3,
                "total_steps": 4
            }
        
        # Step 4: Quarto notebook generation
        notebook_result = None
        if include_notebook:
            logger.info(f"Step 4/4: Generating Quarto notebook for: {question[:100]}")
            step_4_start = datetime.now()
            
            # Generate unique filename if not provided
            if not output_path:
                timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
                safe_title = "_".join(question.split()[:10])
                analysis_id = str(uuid.uuid4())[:8]
                output_path = f"/tmp/quarto_{timestamp}_{safe_title}_{analysis_id}.qmd"
            
            # Extract data for notebook
            notebook_data = data_result.get("data")
            if isinstance(notebook_data, dict):
                notebook_data = notebook_data.get("items", notebook_data)
            
            # Extract enriched metadata from data_result if available
            # These are added by get_data_for_story
            enriched_metadata = {
                "workflow": "full_analysis",
                "question": question,
                "audience": audience or "internal",
                "document_type": document_type or "long_read",
                "style": style or "formal",
                "parameters": {
                    "origin": final_origin,
                    "destination": final_destination,
                    "topic": final_topic,
                    "timespan": final_timespan
                }
            }
            
            # Add enriched data from data_result to metadata for notebook
            if isinstance(data_result, dict) and "data" in data_result:
                data_field = data_result["data"]
                if isinstance(data_field, dict):
                    if "statistics" in data_field:
                        enriched_metadata["statistics"] = data_field["statistics"]
                    if "guardrails" in data_field:
                        enriched_metadata["guardrails"] = data_field["guardrails"]
                    if "visualization_structure" in data_field:
                        enriched_metadata["visualization_structure"] = data_field["visualization_structure"]
                    if "visualization_description" in data_field:
                        enriched_metadata["visualization_description"] = data_field["visualization_description"]
            
            # Create notebook with all metadata
            # Ensure story_content is a string - extract text properly
            story_content = story_result.get("story", "")
            
            # Import the text extraction utility
            from backend.mcp.tools.create_quarto_notebook import _extract_text_from_message
            
            if not isinstance(story_content, str):
                story_content = _extract_text_from_message(story_content)
                if not story_content:
                    # Fallback to string representation
                    if isinstance(story_content, list):
                        story_content = '\n'.join(str(item) for item in story_content)
                    else:
                        story_content = str(story_content)
            
            # If story_content is a string but looks like a stringified dict/message object,
            # try to extract the actual text content
            if isinstance(story_content, str) and story_content.strip().startswith("{"):
                # This looks like a stringified dict - try to parse and extract
                try:
                    import ast
                    parsed = ast.literal_eval(story_content)
                    extracted = _extract_text_from_message(parsed)
                    if extracted:
                        story_content = extracted
                except (ValueError, SyntaxError):
                    # ast.literal_eval failed (likely due to newlines in the string representation)
                    # Try to parse as JSON by converting single quotes to double quotes
                    import json
                    import re
                    try:
                        # Convert single quotes to double quotes for JSON compatibility
                        # But be careful with escaped single quotes and newlines
                        json_str = story_content
                        # Replace single quotes with double quotes (simple approach)
                        json_str = json_str.replace("'", '"')
                        # Fix escaped quotes that might have been created
                        json_str = json_str.replace('\\"', '"')
                        parsed = json.loads(json_str)
                        extracted = _extract_text_from_message(parsed)
                        if extracted:
                            story_content = extracted
                    except (json.JSONDecodeError, ValueError):
                        # JSON parsing failed, try regex to find 'text' field
                        # Look for pattern like 'text': '...' or "text": "..."
                        # Handle escaped newlines in the text
                        text_matches = re.findall(r"(?:['\"])\s*text\s*(?:['\"]):\s*(?:['\"])([^'\"]*(?:\\.[^'\"]*)*)(?:'\")", story_content)
                        if text_matches:
                            # Get the first text match and unescape it
                            story_content = text_matches[0].encode().decode('unicode_escape')
                        else:
                            # Last resort: try to find content array and extract text
                            content_match = re.search(r"(?:['\"])\s*content\s*(?:['\"]):\s*\[\s*({[^}]*})\s*\]", story_content)
                            if content_match:
                                content_str = content_match.group(1)
                                # Try to parse this content dict
                                try:
                                    content_dict = json.loads(content_str.replace("'", '"'))
                                    story_content = content_dict.get('text', story_content)
                                except:
                                    pass
                            # If we still have a stringified dict, log warning
                            if story_content.strip().startswith("{"):
                                logger.warning(f"Could not extract text from story_content: {story_content[:200]}")
            
            notebook_result = await create_quarto_notebook_tool(
                story_content=story_content,
                title=story_result.get("title", f"UNHCR Analysis: {question[:50]}"),
                output_path=output_path,
                author="UNHCR Statistics Copilot",
                include_code_cells=True,
                use_unhcr_theme=True,
                use_unhcr_style=True,
                original_query=question,
                metadata=enriched_metadata,
                data=notebook_data,
                render_html=include_html,
                render_pdf=include_pdf
            )
            
            step_4_end = datetime.now()
            workflow_sequence.append({
                "step": 4,
                "action": "notebook_generation",
                "timestamp": step_4_end.isoformat(),
                "duration_ms": round((step_4_end - step_4_start).total_seconds() * 1000, 2),
                "file_path": output_path
            })
        
        end_time = datetime.now()
        total_duration_ms = round((end_time - start_time).total_seconds() * 1000, 2)
        
        # Build final result
        result = {
            "status": "success",
            "question": question,
            "data": data_result,
            "story": story_result,
            "notebook": notebook_result,
            "workflow": "full_analysis",
            "metadata": {
                "start_time": start_time.isoformat(),
                "end_time": end_time.isoformat(),
                "total_duration_ms": total_duration_ms,
                "completed_steps": 4 if include_notebook else 3,
                "workflow_sequence": workflow_sequence,
                "audience": audience or "internal",
                "document_type": document_type or "long_read",
                "style": style or "formal",
                "use_enhanced": use_enhanced,
                "use_rag": use_rag,
                "rag_available": use_rag and rag_retriever is not None
            }
        }
        
        # Add file paths if notebook was generated
        if notebook_result and isinstance(notebook_result, dict):
            result["file_path"] = notebook_result.get("path")
            result["html_path"] = notebook_result.get("html_path")
            result["pdf_path"] = notebook_result.get("pdf_path")
        
        logger.info(f"Full analysis workflow completed in {total_duration_ms}ms")
        return result
        
    except Exception as e:
        logger.exception(f"Full analysis workflow failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "question": question,
            "workflow": "full_analysis",
            "completed_steps": 0,
            "total_steps": 4,
            "use_rag": use_rag,
            "rag_available": use_rag and rag_retriever is not None
        }


async def quick_analysis_tool(
    question: str,
    audience: Optional[str] = None,
    document_type: Optional[str] = None,
) -> dict[str, Any]:
    """
    Quick analysis workflow: question → data → simple story (no notebook)
    
    This is a lightweight workflow for quick analysis requests that don't require
    notebook generation or enhanced pipeline features.
    
    Args:
        question: The user's analysis question
        audience: Target audience (optional, default: "internal")
        document_type: Document type (optional, default: "executive_summary")
    
    Returns:
        Quick analysis result with story and data
    """
    try:
        from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
        from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
        from backend.mcp.common import UNHCRAPIClient
        
        api_client = UNHCRAPIClient()
        
        # Step 1: Get data (using simple parameters)
        data_result = await get_data_for_story_tool(
            api_client,
            question=question,
            audience=audience or "internal",
            document_type=document_type or "executive_summary"
        )
        
        if data_result.get("error"):
            return {
                "status": "error",
                "error": data_result.get("error"),
                "question": question
            }
        
        # Step 2: Generate story
        story_result = await generate_analytical_story_tool(
            result=data_result,
            data=data_result,
            question=question,
            audience=audience or "internal",
            document_type=document_type or "executive_summary"
        )
        
        return {
            "status": "success",
            "question": question,
            "data": data_result,
            "story": story_result,
            "workflow": "quick_analysis"
        }
        
    except Exception as e:
        logger.exception(f"Quick analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "question": question,
            "workflow": "quick_analysis"
        }


async def compare_analysis_tool(
    question_template: str,
    comparisons: list[dict[str, Any]],
    audience: Optional[str] = None,
) -> dict[str, Any]:
    """
    Comparative analysis workflow: Run the same analysis for multiple scenarios
    
    This workflow runs the same question template against multiple parameter sets
    (e.g., different countries, years, or population types) and returns a
    comparative analysis.
    
    Args:
        question_template: Question template with {placeholders} for parameters
        comparisons: List of parameter dictionaries to compare
        audience: Target audience (optional, default: "internal")
    
    Example:
        question_template: "What are the refugee trends from {country}?"
        comparisons: [
            {"country": "SYR", "year": "2020"},
            {"country": "SYR", "year": "2021"},
            {"country": "SYR", "year": "2022"}
        ]
    
    Returns:
        Comparative analysis with results for each scenario
    """
    try:
        from backend.mcp.tools.get_data_for_story import get_data_for_story_tool
        from backend.mcp.tools.generate_analytical_story import generate_analytical_story_tool
        from backend.mcp.common import UNHCRAPIClient
        
        api_client = UNHCRAPIClient()
        
        results = []
        
        for i, params in enumerate(comparisons):
            # Format the question with parameters
            formatted_question = question_template.format(**params)
            
            # Get data
            data_params = {
                'question': formatted_question,
                'audience': audience or "internal",
                **params
            }
            data_result = await get_data_for_story_tool(api_client, **data_params)
            
            # Generate story
            story_result = await generate_analytical_story_tool(
                result=data_result,
                data=data_result,
                question=formatted_question,
                audience=audience or "internal"
            )
            
            results.append({
                "scenario": params,
                "formatted_question": formatted_question,
                "data": data_result,
                "story": story_result
            })
        
        return {
            "status": "success",
            "question_template": question_template,
            "comparisons": comparisons,
            "results": results,
            "count": len(results),
            "workflow": "comparative_analysis"
        }
        
    except Exception as e:
        logger.exception(f"Comparative analysis failed: {e}")
        return {
            "status": "error",
            "error": str(e),
            "question_template": question_template,
            "workflow": "comparative_analysis"
        }
