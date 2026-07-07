"""
Tool: create_quarto_notebook
Create Quarto notebooks from data stories.
"""

import json
import logging
import os
import re
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml

try:
    import jinja2
    JINJA2_AVAILABLE = True
except ImportError:
    JINJA2_AVAILABLE = False

logger = logging.getLogger(__name__)


def _extract_text_from_message(content: Any) -> str:
    """
    Extract text content from various message formats.
    
    Handles:
    - Plain strings
    - Lists of message objects (LLM response format)
    - Dicts with 'content' or 'text' keys
    - Nested structures
    - Azure OpenAI format with content as list of dicts
    - LLM message objects with 'raw_text', 'message', 'story' fields
    
    Args:
        content: The content to extract text from
        
    Returns:
        Extracted text as a string
    """
    if content is None:
        return ""
    
    if isinstance(content, str):
        # Clean up any JSON artifacts at the edges
        cleaned = content.strip()
        if cleaned.startswith('[') and cleaned.endswith(']'):
            try:
                parsed = json.loads(cleaned)
                return _extract_text_from_message(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        if cleaned.startswith('{') and cleaned.endswith('}'):
            try:
                parsed = json.loads(cleaned)
                return _extract_text_from_message(parsed)
            except (json.JSONDecodeError, TypeError):
                pass
        return cleaned
    
    if isinstance(content, list):
        # Handle list of message objects (LLM response format)
        texts = []
        for item in content:
            if isinstance(item, dict):
                # Enhanced: Check multiple possible text fields in order of priority
                text_fields = ['text', 'content', 'raw_text', 'message', 'story', 'narrative']
                text_found = False
                for key in text_fields:
                    if key in item:
                        text = _extract_text_from_message(item[key])
                        if text:
                            texts.append(text)
                            text_found = True
                            break
                
                if not text_found:
                    # Try to extract text from any value that's not metadata
                    for key, value in item.items():
                        if key not in ['type', 'role', 'name', 'usage', 'model']:
                            text = _extract_text_from_message(value)
                            if text:
                                texts.append(text)
                                text_found = True
                                break
                
                if not text_found:
                    # Try string representation
                    text = _extract_text_from_message(item)
                    if text:
                        texts.append(text)
            elif isinstance(item, str):
                item_cleaned = item.strip()
                if item_cleaned:
                    texts.append(item_cleaned)
            else:
                # Try string conversion as fallback
                text = _extract_text_from_message(item)
                if text:
                    texts.append(text)
        
        if texts:
            return "\n\n".join(texts)
        return ""
    
    if isinstance(content, dict):
        # Azure OpenAI message format: {'type': 'message', 'content': [...]}
        if 'content' in content and isinstance(content['content'], list):
            # Extract text from each content item
            texts = []
            for citem in content['content']:
                if isinstance(citem, dict) and 'text' in citem:
                    texts.append(citem['text'])
                elif isinstance(citem, str):
                    texts.append(citem)
                else:
                    text = _extract_text_from_message(citem)
                    if text:
                        texts.append(text)
            if texts:
                return '\n\n'.join(texts)
        
        # Try common text fields in priority order
        text_fields = ['story', 'content', 'text', 'raw_text', 'message', 'narrative', 'description']
        for key in text_fields:
            if key in content:
                text = _extract_text_from_message(content[key])
                if text:
                    return text
        
        # If no text field found, try to extract from nested content
        if 'content' in content:
            return _extract_text_from_message(content['content'])
        
        # Try any non-metadata field
        for key, value in content.items():
            if key not in ['type', 'role', 'name', 'usage', 'model', 'finish_reason']:
                text = _extract_text_from_message(value)
                if text:
                    return text
        
        # Return string representation as fallback
        try:
            return str(content)
        except Exception:
            return ""
    
    # Fallback: convert to string
    try:
        return str(content)
    except Exception:
        return ""


def _render_quarto_file(qmd_path: str | Path, output_dir: str | Path, render_html: bool = True, render_pdf: bool = True) -> dict[str, Any]:
    """
    Render a Quarto file to HTML and/or PDF using the Quarto CLI.
    
    Args:
        qmd_path: Path to the .qmd file to render
        output_dir: Directory to save rendered files
        render_html: Whether to render HTML
        render_pdf: Whether to render PDF
        
    Returns:
        Dictionary with paths to rendered files and status information
    """
    qmd_path = Path(qmd_path)
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    results = {
        'html_path': None,
        'pdf_path': None,
        'html_rendered': False,
        'pdf_rendered': False,
        'errors': []
    }
    
    # Check if Quarto CLI is available
    try:
        result = subprocess.run(['quarto', '--version'], capture_output=True, text=True)
        if result.returncode != 0:
            logger.warning("Quarto CLI not available - rendering will be skipped")
            results['errors'].append("Quarto CLI not available")
            return results
    except FileNotFoundError:
        logger.warning("Quarto CLI not found - rendering will be skipped")
        results['errors'].append("Quarto CLI not found")
        return results
    
    # Render HTML
    if render_html:
        try:
            # Change to output directory and render without --output flag
            # Quarto will auto-generate output with same name as input but .html extension
            original_cwd = os.getcwd()
            os.chdir(output_dir)
            
            # Create a symlink or copy to current directory with simple name
            temp_qmd = output_dir / "temp_analysis.qmd"
            if temp_qmd.exists():
                temp_qmd.unlink()
            shutil.copy2(qmd_path, temp_qmd)
            
            result = subprocess.run(
                ['quarto', 'render', 'temp_analysis.qmd', '--to', 'html'],
                capture_output=True,
                text=True,
                cwd=output_dir
            )
            
            os.chdir(original_cwd)
            
            # Check for auto-generated HTML file
            html_path = output_dir / "temp_analysis.html"
            if result.returncode == 0 and html_path.exists():
                # Move to final location
                final_html_path = output_dir / f"{qmd_path.stem}.html"
                if final_html_path.exists():
                    final_html_path.unlink()
                html_path.rename(final_html_path)
                results['html_path'] = str(final_html_path)
                results['html_rendered'] = True
                logger.info(f"Successfully rendered HTML: {final_html_path}")
            else:
                logger.error(f"Failed to render HTML: {result.stderr}")
                results['errors'].append(f"HTML rendering failed: {result.stderr}")
                # Cleanup temp file
                if temp_qmd.exists():
                    temp_qmd.unlink()
        except Exception as e:
            logger.error(f"Exception during HTML rendering: {e}")
            results['errors'].append(f"HTML rendering exception: {str(e)}")
        finally:
            try:
                os.chdir(original_cwd)
            except:
                pass
    
    # Render PDF
    if render_pdf:
        try:
            # Change to output directory and render without --output flag
            original_cwd_pdf = os.getcwd()
            os.chdir(output_dir)
            
            # Create a symlink or copy to current directory with simple name
            temp_qmd = output_dir / "temp_analysis.qmd"
            if temp_qmd.exists():
                temp_qmd.unlink()
            shutil.copy2(qmd_path, temp_qmd)
            
            result = subprocess.run(
                ['quarto', 'render', 'temp_analysis.qmd', '--to', 'pdf'],
                capture_output=True,
                text=True,
                cwd=output_dir
            )
            
            os.chdir(original_cwd)
            
            # Check for auto-generated PDF file
            pdf_path = output_dir / "temp_analysis.pdf"
            if result.returncode == 0 and pdf_path.exists():
                # Move to final location
                final_pdf_path = output_dir / f"{qmd_path.stem}.pdf"
                if final_pdf_path.exists():
                    final_pdf_path.unlink()
                pdf_path.rename(final_pdf_path)
                results['pdf_path'] = str(final_pdf_path)
                results['pdf_rendered'] = True
                logger.info(f"Successfully rendered PDF: {final_pdf_path}")
            else:
                logger.error(f"Failed to render PDF: {result.stderr}")
                results['errors'].append(f"PDF rendering failed: {result.stderr}")
                # Cleanup temp file
                if temp_qmd.exists():
                    temp_qmd.unlink()
        except Exception as e:
            logger.error(f"Exception during PDF rendering: {e}")
            results['errors'].append(f"PDF rendering exception: {str(e)}")
        finally:
            try:
                os.chdir(original_cwd_pdf)
            except:
                pass
    
    return results


def _escape_jinja(text: str | list | Any) -> str:
    """
    Escape Jinja2 special characters in text to prevent template rendering issues.
    
    Args:
        text: Text that may contain Jinja2 syntax, or any object that can be converted to string
        
    Returns:
        Text with Jinja2 syntax escaped
    """
    if text is None:
        return ""
    text_str = _extract_text_from_message(text) if not isinstance(text, str) else text
    return text_str.replace('{{', r'\{{').replace('}}', r'\}}').replace('{%', r'\{%').replace('%}', r'\%}')


def _quote_yaml(text: str) -> str:
    """
    Quote a string for YAML to handle special characters (colons, etc.).
    
    Args:
        text: Text that may contain YAML special characters
        
    Returns:
        Quoted text safe for YAML
    """
    if not text:
        return ''
    # Check if the text contains characters that need quoting in YAML
    # These include: : { } [ ] , & * # ? | - < > = ! % @ ` (space followed by colon is OK in plain style)
    # Also need to check for strings that start with special characters or look like dates/times/booleans
    special_chars = '{}[],&*#?|<>=!%@`'
    # Also quote if contains colon followed by space (which is interpreted as key-value separator)
    has_colon_space = ': ' in text
    
    if has_colon_space or any(char in text for char in special_chars):
        # Use double quotes and escape any existing double quotes
        escaped_text = text.replace('"', '\\"')
        return f'"{escaped_text}"'
    
    # Also check if the text looks like a boolean, null, date, or number
    # These should be quoted to be treated as strings
    lower_text = text.lower()
    if lower_text in ('true', 'false', 'yes', 'no', 'null', 'none', 'on', 'off'):
        escaped_text = text.replace('"', '\\"')
        return f'"{escaped_text}"'
    
    return text


def _load_template(template_name: str = "quarto_notebook.j2") -> Optional[jinja2.Template]:
    """
    Load a Jinja2 template from the templates directory.
    
    Args:
        template_name: Name of the template file
        
    Returns:
        Compiled Jinja2 template or None if not available
    """
    if not JINJA2_AVAILABLE:
        logger.warning("Jinja2 not available, using manual template generation")
        return None
    
    try:
        templates_dir = Path(__file__).parent.parent.parent / "templates"
        if not templates_dir.exists():
            logger.warning(f"Templates directory not found at {templates_dir}")
            return None
        
        # Create Jinja2 environment with custom filters
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=False,
            undefined=jinja2.StrictUndefined
        )
        
        # Add custom filter for escaping Jinja syntax in content
        env.filters['escape_jinja'] = _escape_jinja
        
        # Add custom filter for quoting YAML strings
        env.filters['quote_yaml'] = _quote_yaml
        
        return env.get_template(template_name)
    except Exception as e:
        logger.error(f"Failed to load template {template_name}: {e}")
        return None


def _generate_data_visualization_code(
    data: Any, 
    data_name: str = "data",
    visualization_description: Optional[dict] = None,
    statistics: Optional[dict] = None
) -> str:
    """
    Generate Python code for data visualization based on the data structure.
    
    Args:
        data: The data to visualize (dict or list)
        data_name: Variable name for the data
        visualization_description: Optional visualization description dict
        statistics: Optional statistics dict for enhanced comments
        
    Returns:
        Python code string with data loading and visualization
        Note: Code is generated without leading indentation - the Quarto template
        will handle indentation within the code cell.
    """
    code_lines = []
    
    # Add visualization description as comments if available
    if visualization_description and isinstance(visualization_description, dict):
        desc = visualization_description.get('description', '')
        if desc:
            code_lines.append(f"# Visualization Description: {desc[:200]}")
            code_lines.append("")
    
    # Add statistics summary as comments if available
    if statistics and isinstance(statistics, dict):
        stats_summary = statistics.get('summary', '')
        if stats_summary:
            code_lines.append(f"# Statistics Summary: {stats_summary[:200]}")
            code_lines.append("")
    
    # Import statements - NO leading indentation
    code_lines.append("import pandas as pd")
    code_lines.append("import matplotlib.pyplot as plt")
    code_lines.append("import numpy as np")
    code_lines.append("import unhcrpyplotstyle  # noqa: F401")
    code_lines.append("")
    
    # Configure matplotlib for SVG output in Quarto
    code_lines.append("# Configure matplotlib to generate SVG images for responsive rendering in Quarto")
    code_lines.append("# This ensures charts are vector-based and scale properly on all devices")
    code_lines.append("plt.rcParams['figure.facecolor'] = 'white'  # Ensure white background for SVG")
    code_lines.append("plt.rcParams['svg.fonttype'] = 'none'  # Use system fonts for better text rendering")
    code_lines.append("")
    code_lines.append("# Set SVG as the default format for Quarto/Jupyter inline rendering")
    code_lines.append("try:")
    code_lines.append("    %config InlineBackend.figure_format = 'svg'")
    code_lines.append("except:")
    code_lines.append("    pass  # Ignore if not in IPython/Jupyter environment")
    code_lines.append("")
    
    # Add data validation helper functions
    code_lines.append("# Data validation helpers to prevent matplotlib errors")
    code_lines.append("def has_valid_data(df, numeric_cols, year_col=None, x_col=None, y_cols=None):")
    code_lines.append('    """Check if DataFrame has valid data for plotting."""')
    code_lines.append("    if df.empty:")
    code_lines.append("        return False, \"DataFrame is empty\"")
    code_lines.append("    if len(df) == 0:")
    code_lines.append("        return False, \"No data points available\"")
    code_lines.append("    if not numeric_cols:")
    code_lines.append("        return False, \"No numeric columns to plot\"")
    code_lines.append("    # Check if all numeric columns have NaN or zero values")
    code_lines.append("    for col in numeric_cols:")
    code_lines.append("        if col in df.columns:")
    code_lines.append("            if df[col].isna().all():")
    code_lines.append("                return False, f\"Column '{col}' contains only NaN values\"")
    code_lines.append("    # Check if year column has valid range if provided")
    code_lines.append("    if year_col and year_col in df.columns:")
    code_lines.append("        unique_years = df[year_col].dropna().nunique()")
    code_lines.append("        if unique_years < 1:")
    code_lines.append("            return False, f\"Year column '{year_col}' has insufficient unique values\"")
    code_lines.append("    # Check axis ranges to prevent matplotlib NaN errors")
    code_lines.append("    # Check if x_col has valid range (vmin != vmax)")
    code_lines.append("    if x_col and x_col in df.columns:")
    code_lines.append("        x_values = df[x_col].dropna()")
    code_lines.append("        if len(x_values) == 0:")
    code_lines.append("            return False, f\"X-axis column '{x_col}' has no valid values\"")
    code_lines.append("        if len(x_values.unique()) < 2:  # Need at least 2 unique values for a range")
    code_lines.append("            return False, f\"X-axis column '{x_col}' has insufficient variation (need at least 2 unique values)\"")
    code_lines.append("    # Check if y_cols have valid ranges")
    code_lines.append("    if y_cols:")
    code_lines.append("        for y_col in y_cols:")
    code_lines.append("            if y_col in df.columns:")
    code_lines.append("                y_values = df[y_col].dropna()")
    code_lines.append("                if len(y_values) == 0:")
    code_lines.append("                    return False, f\"Y-axis column '{y_col}' has no valid values\"")
    code_lines.append("                # Check if all non-zero values are the same (would cause axis range issues)")
    code_lines.append("                non_zero_values = y_values[y_values != 0]")
    code_lines.append("                if len(non_zero_values) > 0 and len(non_zero_values.unique()) < 2:")
    code_lines.append("                    return False, f\"Column '{y_col}' has all identical non-zero values\"")
    code_lines.append("    return True, \"Data is valid for plotting\"")
    code_lines.append("")
    code_lines.append("")
    code_lines.append("# Additional matplotlib error prevention")
    code_lines.append("def is_numeric_column_valid(df, col):")
    code_lines.append('    """Check if a numeric column has valid data for plotting."""')
    code_lines.append("    if col not in df.columns:")
    code_lines.append("        return False")
    code_lines.append("    values = df[col].dropna()")
    code_lines.append("    if len(values) == 0:")
    code_lines.append("        return False")
    code_lines.append("    # Check if all values are the same (would cause axis range issues)")
    code_lines.append("    if len(values.unique()) < 2:")
    code_lines.append("        return False")
    code_lines.append("    return True")
    code_lines.append("")
    code_lines.append("")
    code_lines.append("# Function to ensure numeric columns are properly typed")
    code_lines.append("def convert_to_numeric(df, columns):")
    code_lines.append('    """Convert specified columns to numeric, coercing errors to NaN."""')
    code_lines.append("    for col in columns:")
    code_lines.append("        if col in df.columns:")
    code_lines.append("            df[col] = pd.to_numeric(df[col], errors='coerce')")
    code_lines.append("    return df")
    code_lines.append("")
    code_lines.append("")
    code_lines.append("# Function to get valid numeric columns for plotting")
    code_lines.append("def get_valid_numeric_columns(df, numeric_cols):")
    code_lines.append('    """Get list of numeric columns that have enough valid data for plotting."""')
    code_lines.append("    valid_cols = []")
    code_lines.append("    for col in numeric_cols:")
    code_lines.append("        if col in df.columns:")
    code_lines.append("            # Convert to numeric if needed")
    code_lines.append("            numeric_series = pd.to_numeric(df[col], errors='coerce')")
    code_lines.append("            non_null_count = numeric_series.notna().sum()")
    code_lines.append("            unique_count = numeric_series.dropna().nunique()")
    code_lines.append("            # Need at least 1 non-null values and some variation")
    code_lines.append("            if non_null_count >= 1 and unique_count >= 1:")
    code_lines.append("                valid_cols.append(col)")
    code_lines.append("    return valid_cols")
    code_lines.append("")
    code_lines.append("")
    
    # Set UNHCR visualization style
    code_lines.append("# Apply UNHCR brand compliance styles")
    
    # Use recommended styles from visualization description if available
    if visualization_description and isinstance(visualization_description, dict):
        style_info = visualization_description.get('unhcrpyplotstyle', {})
        if style_info and isinstance(style_info, dict):
            styles = style_info.get('styles', ['unhcrpyplotstyle'])
            code_lines.append(f"plt.style.use({styles})")
        else:
            code_lines.append("plt.style.use('unhcrpyplotstyle')")
    else:
        # Default to base UNHCR style
        code_lines.append("plt.style.use('unhcrpyplotstyle')")
    code_lines.append("")
    
    # Extract actual data from nested structures
    # Handle common UNHCR API response patterns
    actual_data = data
    if isinstance(data, dict):
        if 'items' in data:
            actual_data = data['items']
        elif 'total' in data and isinstance(data['total'], list):
            actual_data = data['total']
    
    # Convert data to JSON and load into DataFrame
    if isinstance(actual_data, list) and len(actual_data) > 0:
        # List of dicts - convert to DataFrame
        code_lines.append("# Load data into DataFrame")
        code_lines.append(f"{data_name} = {json.dumps(actual_data, indent=2)}")
        code_lines.append(f"df = pd.DataFrame({data_name})")
        code_lines.append("")
        code_lines.append("# Convert all potential numeric columns to numeric type")
        code_lines.append("# This prevents string representation of numbers from causing issues")
        code_lines.append("# Exclude columns that are clearly identifiers or names")
        code_lines.append("exclude_cols = ['coo_id', 'coo_name', 'coo_iso', 'coa_id', 'coa_name', 'coa_iso']")
        code_lines.append("potential_numeric_cols = [col for col in df.columns if col not in exclude_cols]")
        code_lines.append("df = convert_to_numeric(df, potential_numeric_cols)")
        code_lines.append("")
        
        # Analyze numeric columns for visualization
        numeric_cols = []
        first_item = actual_data[0]
        if isinstance(first_item, dict):
            for key, value in first_item.items():
                # Try to detect numeric columns
                if isinstance(value, (int, float)):
                    # Include actual numeric values (not IDs)
                    # Skip ID columns and categorical codes
                    if not any(skip in key.lower() for skip in ['_id', '_name', '_iso', 'coo', 'coa']):
                        numeric_cols.append(key)
                elif isinstance(value, str) and (value.isdigit() or value.replace('.', '').replace('-', '').isdigit()):
                    # For string fields that are numeric, include if they could be numeric
                    # Skip ID columns, categorical codes
                    if not any(skip in key.lower() for skip in ['_id', '_name', '_iso']):
                        numeric_cols.append(key)
        
        # Generate visualizations based on data structure
        if numeric_cols:
            # Check if there's a year column
            year_col = None
            for col in first_item.keys() if isinstance(first_item, dict) else []:
                if 'year' in col.lower():
                    year_col = col
                    break
            
            if year_col and len(numeric_cols) > 1:
                # Time series plot using matplotlib (UNHCR compliant)
                code_lines.append("# Plot 1: Time series of numeric variables")
                code_lines.append("try:")
                code_lines.append(f"    # Validate data and get valid numeric columns for plotting")
                code_lines.append(f"    numeric_cols_for_plot = [c for c in {numeric_cols} if c != '{year_col}']")
                code_lines.append(f"    valid_numeric_cols = get_valid_numeric_columns(df, numeric_cols_for_plot)")
                code_lines.append(f"    is_valid, message = has_valid_data(df, valid_numeric_cols, year_col='{year_col}', x_col='{year_col}', y_cols=valid_numeric_cols)")
                code_lines.append("    if not is_valid:")
                code_lines.append("        print(f'Cannot create time series plot: {message}')")
                code_lines.append("    elif len(valid_numeric_cols) == 0:")
                code_lines.append("        print('No valid numeric columns found for time series plot')")
                code_lines.append("    else:")
                code_lines.append(f"        fig, ax = plt.subplots(figsize=(12, 6))")
                
                # Plot each valid numeric column using matplotlib
                code_lines.append("        # Plot only columns with valid data")
                code_lines.append("        plotted_cols = []")
                for col in numeric_cols:
                    if col != year_col and col in valid_numeric_cols:
                        code_lines.append(f"        # Check if {col} has variation for plotting")
                        code_lines.append(f"        if is_numeric_column_valid(df, '{col}'):")
                        code_lines.append(f"            ax.plot(df['{year_col}'], df['{col}'], label='{col}', marker='o')")
                        code_lines.append(f"            plotted_cols.append('{col}')")
                
                code_lines.append("        if len(plotted_cols) == 0:")
                code_lines.append("            print('No valid data to plot for time series')")
                code_lines.append("        else:")
                code_lines.append("            ax.set_title('Trends Over Time', fontfamily='Lato', fontsize=14)")
                code_lines.append("            ax.set_xlabel('Year', fontfamily='Lato')")
                code_lines.append("            ax.set_ylabel('Count', fontfamily='Lato')")
                code_lines.append("            ax.legend(fontsize=10)")
                code_lines.append("            ax.grid(True, alpha=0.3)")
                code_lines.append("            plt.tight_layout()")
                
                # Add UNHCR source attribution
                code_lines.append("            # Add UNHCR source attribution")
                code_lines.append("            plt.figtext(0.5, 0.01, 'Source: UNHCR Population Data | © UNHCR, the UN Refugee Agency', ha='center', fontfamily='Lato', fontsize=8)")
                code_lines.append("            plt.show()")
                code_lines.append("except Exception as e:")
                code_lines.append("    print(f'Error creating time series plot: {str(e)}')")
                code_lines.append("")
                
                # Bar chart for most recent year using matplotlib
                code_lines.append("# Plot 2: Values for most recent year")
                code_lines.append("try:")
                code_lines.append(f"    # Validate data before plotting")
                code_lines.append(f"    if '{year_col}' not in df.columns:")
                code_lines.append("        print('Year column not found for recent year plot')")
                code_lines.append("    else:")
                code_lines.append(f"        recent_year = df['{year_col}'].max()")
                code_lines.append(f"        recent_data = df[df['{year_col}'] == recent_year]")
                code_lines.append("")
                code_lines.append("        if not recent_data.empty:")
                code_lines.append("            # Get valid numeric columns, excluding the year column")
                code_lines.append(f"            recent_numeric = recent_data.select_dtypes(include=['number']).drop(columns=['{year_col}'], errors='ignore')")
                code_lines.append("            if not recent_numeric.empty:")
                code_lines.append("                # Check if we have valid numeric data with variation")
                code_lines.append("                valid_recent_cols = []")
                code_lines.append("                for col in recent_numeric.columns:")
                code_lines.append("                    col_values = recent_numeric[col].dropna()")
                code_lines.append("                    if len(col_values) > 0 and len(col_values.unique()) >= 1:")
                code_lines.append("                        # Check if there's at least some variation or meaningful values")
                code_lines.append("                        non_zero = col_values[col_values != 0]")
                code_lines.append("                        if len(non_zero) > 0 or col_values.iloc[0] != 0:")
                code_lines.append("                            valid_recent_cols.append(col)")
                code_lines.append("                if len(valid_recent_cols) > 0 and recent_numeric[valid_recent_cols].iloc[0].notna().any():")
                code_lines.append("                    fig, ax = plt.subplots(figsize=(10, 5))")
                code_lines.append("                    ax.bar(valid_recent_cols, recent_numeric[valid_recent_cols].iloc[0], color='#0072BC')")
                code_lines.append("                    ax.set_title(f'Values for Year {recent_year}', fontfamily='Lato', fontsize=14)")
                code_lines.append("                    ax.set_ylabel('Count', fontfamily='Lato')")
                code_lines.append("                    ax.tick_params(axis='x', rotation=45)")
                code_lines.append("                    ax.grid(True, alpha=0.3, axis='y')")
                code_lines.append("                    plt.tight_layout()")
                code_lines.append("                    plt.figtext(0.5, 0.01, 'Source: UNHCR Population Data | © UNHCR, the UN Refugee Agency', ha='center', fontfamily='Lato', fontsize=8)")
                code_lines.append("                    plt.show()")
                code_lines.append("                else:")
                code_lines.append("                    print('No valid numeric data with variation for recent year bar chart')")
                code_lines.append("            else:")
                code_lines.append("                print('No numeric columns found for recent year bar chart')")
                code_lines.append("        else:")
                code_lines.append("            print('No data for most recent year')")
                code_lines.append("except Exception as e:")
                code_lines.append("    print(f'Error creating recent year bar chart: {str(e)}')")
                code_lines.append("")
            else:
                # Bar chart for all numeric columns using matplotlib
                code_lines.append("# Plot: Distribution of numeric values")
                code_lines.append("try:")
                code_lines.append("    # Get valid numeric columns for distribution plot")
                code_lines.append(f"    valid_cols = get_valid_numeric_columns(df, {numeric_cols})")
                code_lines.append(f"    is_valid, message = has_valid_data(df, valid_cols)")
                code_lines.append("    if not is_valid:")
                code_lines.append("        print(f'Cannot create distribution plot: {message}')")
                code_lines.append("    elif len(valid_cols) == 0:")
                code_lines.append("        print('No valid numeric columns to plot')")
                code_lines.append("    else:")
                code_lines.append("        # Calculate sums, handling potential errors")
                code_lines.append("        sums = []")
                code_lines.append("        final_cols = []")
                code_lines.append("        for c in valid_cols:")
                code_lines.append("            try:")
                code_lines.append("                col_sum = df[c].sum()")
                code_lines.append("                if not np.isnan(col_sum) and not np.isinf(col_sum):")
                code_lines.append("                    sums.append(col_sum)")
                code_lines.append("                    final_cols.append(c)")
                code_lines.append("            except (TypeError, ValueError):")
                code_lines.append("                # Skip columns that can't be summed")
                code_lines.append("                pass")
                code_lines.append("        if len(final_cols) > 0 and len(sums) > 0:")
                code_lines.append("            fig, ax = plt.subplots(figsize=(12, 6))")
                code_lines.append("            # Use UNHCR primary blue for bars")
                code_lines.append("            colors = ['#0072BC'] * len(final_cols)")
                code_lines.append("            ax.bar(range(len(final_cols)), sums, color=colors)")
                code_lines.append("            ax.set_xticks(range(len(final_cols)))")
                code_lines.append("            ax.set_xticklabels(final_cols, rotation=45, ha='right')")
                code_lines.append("            ax.set_title('Numeric Values Distribution', fontfamily='Lato', fontsize=14)")
                code_lines.append("            ax.set_ylabel('Total', fontfamily='Lato')")
                code_lines.append("            ax.grid(True, alpha=0.3, axis='y')")
                code_lines.append("            plt.tight_layout()")
                code_lines.append("            plt.figtext(0.5, 0.01, 'Source: UNHCR Population Data | © UNHCR, the UN Refugee Agency', ha='center', fontfamily='Lato', fontsize=8)")
                code_lines.append("            plt.show()")
                code_lines.append("        else:")
                code_lines.append("            print('No valid data to plot for distribution chart')")
                code_lines.append("except Exception as e:")
                code_lines.append("    print(f'Error creating distribution plot: {str(e)}')")
                code_lines.append("")
        else:
            code_lines.append("# No numeric columns found in data for visualization")
            code_lines.append("print('No numeric columns available for chart generation')")
            code_lines.append("")
        
        # Add summary statistics with validation
        code_lines.append("# Summary statistics")
        code_lines.append("try:")
        code_lines.append("    if not df.empty:")
        code_lines.append("        print(\"Data Summary:\")")
        code_lines.append(f"        print(df.describe())")
        code_lines.append("    else:")
        code_lines.append("        print('No data available for summary')")
        code_lines.append("except Exception as e:")
        code_lines.append("    print(f'Error generating summary: {str(e)}')")
        code_lines.append("")
        
    elif isinstance(data, dict):
        # Single dict - convert to DataFrame
        code_lines.append("# Load data into DataFrame")
        code_lines.append(f"{data_name} = {json.dumps(data, indent=2)}")
        code_lines.append(f"df = pd.DataFrame([{data_name}])")
        code_lines.append("")
        code_lines.append("# Display the data")
        code_lines.append("try:")
        code_lines.append(f"    print(\"Data:\")")
        code_lines.append(f"    print(df)")
        code_lines.append("except Exception as e:")
        code_lines.append("    print(f'Error displaying data: {str(e)}')")
        code_lines.append("")
    else:
        code_lines.append("# No valid data structure for visualization")
        code_lines.append("print('No data available for visualization')")
        code_lines.append("")
    
    return "\n".join(code_lines)


async def create_quarto_notebook_tool(
    story_content: str,
    output_path: Optional[str] = None,
    title: Optional[str] = None,
    author: Optional[str] = None,
    date: Optional[str] = None,
    include_code_cells: bool = False,
    use_unhcr_theme: bool = True,
    use_unhcr_style: bool = True,
    original_query: Optional[str] = None,
    metadata: Optional[dict[str, Any]] = None,
    data: Optional[Any] = None,
    render_html: bool = True,
    render_pdf: bool = True,
) -> dict[str, Any]:
    """
    Create a Quarto notebook from story content.
    
    By default, always pre-renders to HTML and PDF for performance.
    All metadata is stored in the YAML header (visible only in source, not rendered output).
    Code cells use echo: false to hide code in rendered output.
    """
    """
    Create a Quarto notebook from story content.
    
    Args:
        story_content: The main content for the notebook
        output_path: Path to save the notebook
        title: Title for the notebook
        render_html: Whether to automatically render HTML after creation
        render_pdf: Whether to automatically render PDF after creation
        author: Author name
        date: Date for the notebook
        include_code_cells: Whether to include code cells
        use_unhcr_theme: Whether to use UNHCR theme
        use_unhcr_style: Whether to use UNHCR style
        original_query: Original query that generated the story
        metadata: Additional metadata
        data: The data used for the analysis (will generate visualization code if provided)
    
    Returns:
        Generated notebook content and metadata
    """
    try:
        # Clean and extract story content from various formats (message objects, dicts, etc.)
        cleaned_story = _extract_text_from_message(story_content) if story_content else ""
        
        # Try to use Jinja2 template first
        template = _load_template("quarto_notebook.j2")
        
        if template and JINJA2_AVAILABLE:
            # Generate Python code if data is provided and code cells are requested
            python_code = ""
            if include_code_cells and data is not None:
                # Extract visualization description from metadata if available
                viz_description = None
                viz_structure = None
                stats_data = None
                guardrails_data = None
                
                if metadata:
                    viz_description = metadata.get('visualization_description')
                    viz_structure = metadata.get('visualization_structure')
                    stats_data = metadata.get('statistics')
                    guardrails_data = metadata.get('guardrails')
                
                # Generate code with optional visualization description
                python_code = _generate_data_visualization_code(
                    data, 
                    visualization_description=viz_description,
                    statistics=stats_data
                )
            
            # Prepare template variables
            timestamp = date or datetime.now().isoformat()
            
            # Escape story_content for Jinja2 to prevent template rendering issues
            escaped_story = _escape_jinja(cleaned_story) if cleaned_story else ""
            
            # Build metadata for template
            template_metadata = metadata or {}
            if 'tool_sequence' not in template_metadata:
                template_metadata['tool_sequence'] = []
            
            # Extract visualization description for potential use in template
            viz_description = metadata.get('visualization_description') if metadata else None
            viz_structure = metadata.get('visualization_structure') if metadata else None
            stats_data = metadata.get('statistics') if metadata else None
            guardrails_data = metadata.get('guardrails') if metadata else None
            
            # Render the template
            quarto_content = template.render(
                title=title or 'UNHCR Data Analysis',
                author=author or 'UNHCR Statistics Copilot',
                date=date or datetime.now().strftime('%Y-%m-%d'),
                use_unhcr_theme=use_unhcr_theme,
                use_unhcr_style=use_unhcr_style,
                include_code_cells=include_code_cells,
                python_code=python_code,
                story_content=escaped_story,
                timestamp=timestamp,
                audience=metadata.get('audience') if metadata else None,
                document_type=metadata.get('document_type') if metadata else None,
                analysis_config=metadata.get('analysis_config') if metadata else None,
                original_query=original_query,
                metadata=template_metadata,
                # NEW: Pass visualization metadata for template use
                visualization_description=viz_description,
                visualization_structure=viz_structure,
                statistics=stats_data,
                guardrails=guardrails_data
            )
        else:
            # Fallback to manual generation if template is not available
            logger.warning("Using manual Quarto generation (Jinja2 template not available)")
            
            # Use cleaned story content
            escaped_story = _escape_jinja(cleaned_story) if cleaned_story else ""
            
            # Generate notebook content
            yaml_header = {
                'title': title or 'UNHCR Data Analysis',
                'author': author or 'UNHCR Statistics Copilot',
                'date': date or datetime.now().strftime('%Y-%m-%d'),
                'format': {
                    'html': {
                        'embed-resources': True,
                        'standalone': True
                    }
                }
            }
            
            # Add theme configuration
            if use_unhcr_theme:
                yaml_header['format']['html']['theme'] = ['unhcr', 'cosmo']
                yaml_header['format']['html']['css'] = 'unhcr.css'
            else:
                yaml_header['format']['html']['theme'] = 'cosmo'
            
            # Disable alternate format links (Other Formats section)
            yaml_header['format']['html']['format-links'] = False
            
            # Add PDF format
            yaml_header['format']['pdf'] = {
                'documentclass': 'article',
                'papersize': 'a4',
                'geometry': ['top=30mm', 'left=20mm', 'right=20mm', 'bottom=30mm']
            }
            
            yaml_header['editor'] = 'visual'
            yaml_header['engine'] = 'jupyter'
            
            if metadata:
                yaml_header['metadata'] = metadata
            
            if original_query:
                yaml_header['original_query'] = original_query
            
            yaml_str = yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True, sort_keys=False)
            
            # Add Quartro-specific markers
            quarto_content = f"""---
{yaml_str}---

"""
            
            if include_code_cells:
                if data is not None:
                    # Extract visualization metadata from metadata if available
                    viz_description = None
                    stats_data = None
                    if metadata:
                        viz_description = metadata.get('visualization_description')
                        stats_data = metadata.get('statistics')
                    
                    # Generate actual visualization code from data with enriched info
                    viz_code = _generate_data_visualization_code(
                        data,
                        visualization_description=viz_description,
                        statistics=stats_data
                    )
                    quarto_content += f"""```{{python}}
#| echo: false
# Data Analysis Code
{viz_code}
```

"""
                else:
                    # Fallback to placeholder if no data
                    quarto_content += """```{python}
#| echo: false
# Data Analysis Code
# Add your analysis code here
print("UNHCR Data Analysis")
```

"""
            
            quarto_content += f"""# {title or 'UNHCR Data Analysis'}

{escaped_story}

"""
            
            if include_code_cells:
                quarto_content += """```{python}
#| echo: false
# Additional analysis can be added here
```
"""
        
        # Save to file if output_path is provided
        if output_path:
            output_dir = Path(output_path).parent
            output_dir.mkdir(parents=True, exist_ok=True)
            with open(output_path, 'w', encoding='utf-8') as f:
                f.write(quarto_content)
            
            # Pre-render HTML and PDF if requested
            render_results = {'html_path': None, 'pdf_path': None, 'errors': []}
            if render_html or render_pdf:
                render_results = _render_quarto_file(
                    qmd_path=output_path,
                    output_dir=output_dir,
                    render_html=render_html,
                    render_pdf=render_pdf
                )
        else:
            render_results = {'html_path': None, 'pdf_path': None, 'errors': []}
        
        return {
            'content': quarto_content,
            'format': 'quarto',
            'path': output_path,
            'html_path': render_results.get('html_path'),
            'pdf_path': render_results.get('pdf_path'),
            'rendered': {
                'html': render_results.get('html_rendered', False),
                'pdf': render_results.get('pdf_rendered', False)
            },
            'render_errors': render_results.get('errors', []),
            'metadata': {
                'title': title,
                'author': author,
                'date': date,
                'source': 'UNHCR Quarto Notebook Generator'
            },
            'status': 'success'
        }
    except Exception as e:
        logger.exception(f"Failed to create Quarto notebook: {e}")
        return {
            'error': f'Failed to create Quarto notebook: {str(e)}',
            'status': 'error'
        }
