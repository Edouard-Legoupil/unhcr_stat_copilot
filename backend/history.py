import json
import os
import uuid
from datetime import datetime
from typing import List, Dict, Optional, Any
import logging

logger = logging.getLogger(__name__)


def _make_serializable(obj: Any, visited: Optional[set] = None) -> Any:
    """
    Convert an object to a JSON-serializable format, handling circular references.
    
    Args:
        obj: The object to convert
        visited: Set of object ids already visited (for circular reference detection)
    
    Returns:
        A JSON-serializable version of the object
    """
    if visited is None:
        visited = set()
    
    # Handle circular references
    obj_id = id(obj)
    if obj_id in visited:
        return "[CIRCULAR REFERENCE]"
    
    visited = visited | {obj_id}  # Create a new set to avoid mutating the parent's set
    
    if obj is None or isinstance(obj, (bool, int, float, str)):
        return obj
    elif isinstance(obj, (list, tuple)):
        return [_make_serializable(item, visited) for item in obj]
    elif isinstance(obj, dict):
        return {str(k): _make_serializable(v, visited) for k, v in obj.items()}
    else:
        # Convert other types to string representation
        try:
            return str(obj)
        except Exception:
            return f"[UNKNOWN TYPE: {type(obj).__name__}]"

# Ensure the history directories exist
HISTORY_DIR = "./data/analysis_history"
QUARTO_DIR = "./data/quarto_analyses"
os.makedirs(HISTORY_DIR, exist_ok=True)
os.makedirs(QUARTO_DIR, exist_ok=True)

def save_analysis(analysis_data: Dict) -> str:
    """
    Save an analysis to the history storage.
    
    Args:
        analysis_data: The analysis data to save
        
    Returns:
        The ID of the saved analysis
    """
    try:
        # Generate a unique ID for this analysis
        analysis_id = str(uuid.uuid4())
        
        # Add metadata
        analysis_data["id"] = analysis_id
        analysis_data["timestamp"] = datetime.now().isoformat()
        
        # Create filename
        filename = f"{analysis_id}.json"
        filepath = os.path.join(HISTORY_DIR, filename)
        
        # Save to file
        # Use _make_serializable to handle any circular references
        serializable_data = _make_serializable(analysis_data)
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_data, f, indent=2, ensure_ascii=False)
        
        logger.info(f"Saved analysis {analysis_id}")
        return analysis_id
        
    except Exception as e:
        logger.error(f"Failed to save analysis: {e}")
        raise

def get_all_analyses() -> List[Dict]:
    """
    Get all saved analyses, sorted by timestamp (newest first).
    
    Returns:
        List of analysis metadata
    """
    try:
        analyses = []
        
        # Get all JSON files in the history directory
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(HISTORY_DIR, filename)
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        analysis_data = json.load(f)
                        # Skip JSON files that have corresponding Quarto files
                        # (these are metadata files for Quarto analyses, not standalone JSON analyses)
                        if analysis_data.get("quarto_filename"):
                            quarto_filepath = analysis_data["filepath"]
                            if os.path.exists(quarto_filepath):
                                # This is metadata for a Quarto analysis, skip it
                                continue
                        
                        analyses.append({
                            "id": analysis_data["id"],
                            "question": analysis_data.get("question", "Unknown"),
                            "tool": analysis_data.get("tool", "unknown"),
                            "timestamp": analysis_data["timestamp"],
                            "filepath": filepath
                        })
                except Exception as e:
                    logger.warning(f"Failed to read analysis file {filename}: {e}")
        
        # Sort by timestamp (newest first)
        analyses.sort(key=lambda x: x["timestamp"], reverse=True)
        return analyses
        
    except Exception as e:
        logger.error(f"Failed to get analyses: {e}")
        return []

def get_analysis(analysis_id: str) -> Optional[Dict]:
    """
    Get a specific analysis by ID.
    
    Args:
        analysis_id: The ID of the analysis to retrieve
        
    Returns:
        The analysis data, or None if not found
    """
    try:
        filepath = os.path.join(HISTORY_DIR, f"{analysis_id}.json")
        
        if not os.path.exists(filepath):
            return None
            
        with open(filepath, "r", encoding="utf-8") as f:
            return json.load(f)
            
    except Exception as e:
        logger.error(f"Failed to get analysis {analysis_id}: {e}")
        return None

def delete_analysis(analysis_id: str) -> bool:
    """
    Delete an analysis by ID.
    
    Args:
        analysis_id: The ID of the analysis to delete
        
    Returns:
        True if deletion was successful, False otherwise
    """
    try:
        filepath = os.path.join(HISTORY_DIR, f"{analysis_id}.json")
        
        if os.path.exists(filepath):
            os.remove(filepath)
            logger.info(f"Deleted analysis {analysis_id}")
            return True
        
        return False
        
    except Exception as e:
        logger.error(f"Failed to delete analysis {analysis_id}: {e}")
        return False

def save_quarto_analysis(quarto_content: str, metadata: dict) -> dict:
    """
    Save an analysis directly as a Quarto file (.qmd).
    
    Args:
        quarto_content: The Quarto content to save
        metadata: Metadata about the analysis
        
    Returns:
        A dictionary containing:
        - filename: The filename of the saved Quarto file
        - filepath: The full path to the saved file
        - id: The generated analysis ID
        - metadata: The updated metadata with ID and filepath
    """
    try:
        # Generate a unique ID for this analysis
        analysis_id = str(uuid.uuid4())
        
        # Create a safe filename from the question
        question = metadata.get("question", "analysis")[:50].replace(" ", "_")
        safe_question = "".join(c for c in question if c.isalnum() or c in ("_", "-"))
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        # Create filename
        filename = f"{timestamp}_{safe_question}_{analysis_id}.qmd"
        filepath = os.path.join(QUARTO_DIR, filename)
        
        # Add metadata as a header to the Quarto file
        html_comments = f"""<!-- Analysis ID: {analysis_id} -->
<!-- Generated: {datetime.now().isoformat()} -->
<!-- Question: {metadata.get('question', 'N/A')} -->

"""
        
        # Check if quarto_content already has a YAML header (starts with ---)
        # If it does, don't add another YAML header - just add the HTML comments before the existing header
        if quarto_content.strip().startswith("---"):
            # Content already has YAML header, insert HTML comments at the beginning
            full_content = html_comments + quarto_content
        else:
            # Create full YAML header with metadata
            yaml_header = f"""---
title: "{metadata.get('question', 'UNHCR Analysis')}"
author: "UNHCR Statistics Copilot Assistant"
date: "{datetime.now().isoformat()}"
format: html
theme: unhcr
---

"""
            # Combine metadata header with quarto content
            full_content = yaml_header + html_comments + quarto_content
        
        # Save to file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_content)
        
        logger.info(f"Saved Quarto analysis {analysis_id} as {filename}")
        
        # Also save metadata for indexing
        metadata["id"] = analysis_id
        metadata["timestamp"] = datetime.now().isoformat()
        metadata["quarto_filename"] = filename
        metadata["filepath"] = filepath
        metadata["analysis_type"] = metadata.get("analysis_type", "comprehensive_quarto")
        
        # Save metadata to history directory for indexing
        # Use _make_serializable to handle any circular references
        history_filepath = os.path.join(HISTORY_DIR, f"{analysis_id}.json")
        serializable_metadata = _make_serializable(metadata)
        with open(history_filepath, "w", encoding="utf-8") as f:
            json.dump(serializable_metadata, f, indent=2, ensure_ascii=False)
        
        # Return a dict with both the filename and the updated metadata
        return {
            "filename": filename,
            "filepath": filepath,
            "id": analysis_id,
            "metadata": metadata
        }
        
    except Exception as e:
        logger.error(f"Failed to save Quarto analysis: {e}")
        raise


def get_quarto_analyses() -> List[Dict]:
    """
    Get all saved Quarto analyses from the history directory.
    
    Returns:
        List of analysis metadata for Quarto files
    """
    try:
        analyses = []
        
        # Get all JSON files in the history directory (these contain metadata for Quarto files)
        for filename in os.listdir(HISTORY_DIR):
            if filename.endswith(".json"):
                filepath = os.path.join(HISTORY_DIR, filename)
                
                try:
                    with open(filepath, "r", encoding="utf-8") as f:
                        analysis_data = json.load(f)
                        # Only include analyses that have quarto_filename AND the corresponding .qmd file exists
                        if analysis_data.get("quarto_filename"):
                            quarto_filepath = analysis_data["filepath"]
                            # Check if the actual Quarto file exists
                            if os.path.exists(quarto_filepath):
                                analyses.append({
                                    "id": analysis_data["id"],
                                    "question": analysis_data.get("question", "Unknown"),
                                    "tool": analysis_data.get("analysis_type", "quarto"),
                                    "timestamp": analysis_data["timestamp"],
                                    "filepath": analysis_data["filepath"],
                                    "quarto_filename": analysis_data["quarto_filename"],
                                    "analysis_type": "quarto"
                                })
                            else:
                                # This is a JSON analysis with Quarto metadata, not a true Quarto analysis
                                logger.debug(f"Skipping {filename} - Quarto file {quarto_filepath} does not exist")
                except Exception as e:
                    logger.warning(f"Failed to read analysis file {filename}: {e}")
        
        return analyses
        
    except Exception as e:
        logger.error(f"Failed to get Quarto analyses: {e}")
        return []


def cleanup_old_analyses(max_analyses: int = 100) -> int:
    """
    Clean up old analyses, keeping only the most recent ones.
    
    Args:
        max_analyses: Maximum number of analyses to keep
        
    Returns:
        Number of analyses deleted
    """
    try:
        all_analyses = get_all_analyses()
        
        if len(all_analyses) <= max_analyses:
            return 0
            
        # Delete oldest analyses
        analyses_to_delete = all_analyses[max_analyses:]
        deleted_count = 0
        
        for analysis in analyses_to_delete:
            if delete_analysis(analysis["id"]):
                deleted_count += 1
        
        logger.info(f"Cleaned up {deleted_count} old analyses")
        return deleted_count
        
    except Exception as e:
        logger.error(f"Failed to cleanup old analyses: {e}")
        return 0