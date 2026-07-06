"""
Tool: create_quarto_notebook
Create Quarto notebooks from data stories.
"""

import json
import logging
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
    text_str = str(text) if not isinstance(text, str) else text
    return text_str.replace('{{', '\{{').replace('}}', '\}}').replace('{%', '\{%').replace('%}', '\%}')


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


def _generate_data_visualization_code(data: Any, data_name: str = "data") -> str:
    """
    Generate Python code for data visualization based on the data structure.
    
    Args:
        data: The data to visualize (dict or list)
        data_name: Variable name for the data
        
    Returns:
        Python code string with data loading and visualization
    """
    code_lines = []
    
    # Import statements
    code_lines.append("import pandas as pd")
    code_lines.append("import matplotlib.pyplot as plt")
    code_lines.append("import seaborn as sns")
    code_lines.append("")
    
    # Set style
    code_lines.append("# Set visualization style")
    code_lines.append("plt.style.use('seaborn-v0_8-darkgrid')")
    code_lines.append("sns.set_palette('husl')")
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
        
        # Analyze numeric columns for visualization
        numeric_cols = []
        first_item = actual_data[0]
        if isinstance(first_item, dict):
            for key, value in first_item.items():
                # Try to detect numeric columns
                if isinstance(value, (int, float)):
                    # Include actual numeric values (not IDs)
                    # Skip ID columns and categorical codes
                    if not any(skip in key.lower() for skip in ['id', '_id', 'iso', 'hst', 'ooc', 'oip']):
                        numeric_cols.append(key)
                elif isinstance(value, str) and value.isdigit():
                    # For string fields that are numeric, only include if they're meaningful
                    # Skip ID columns, categorical codes, and zero-value fields
                    if not any(skip in key.lower() for skip in ['id', '_id', 'iso', 'coo', 'coa', 'hst', 'ooc', 'oip', 'returned', 'stateless']):
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
                # Time series plot
                code_lines.append("# Plot 1: Time series of numeric variables")
                code_lines.append(f"plt.figure(figsize=(12, 6))")
                
                # Plot each numeric column
                for col in numeric_cols:
                    if col != year_col:
                        code_lines.append(f"sns.lineplot(data=df, x='{year_col}', y='{col}', label='{col}')")
                
                code_lines.append("plt.title('Trends Over Time')")
                code_lines.append("plt.xlabel('Year')")
                code_lines.append("plt.ylabel('Count')")
                code_lines.append("plt.legend()")
                code_lines.append("plt.tight_layout()")
                code_lines.append("plt.show()")
                code_lines.append("")
                
                # Bar chart for most recent year
                code_lines.append("# Plot 2: Values for most recent year")
                code_lines.append(f"recent_year = df['{year_col}'].max()")
                code_lines.append(f"recent_data = df[df['{year_col}'] == recent_year]")
                code_lines.append("")
                code_lines.append("if not recent_data.empty:")
                code_lines.append("    recent_numeric = recent_data.select_dtypes(include=['number']).drop(columns=['" + year_col + "'], errors='ignore')")
                code_lines.append("    if not recent_numeric.empty:")
                code_lines.append("        plt.figure(figsize=(10, 5))")
                code_lines.append("        recent_numeric.iloc[0].plot(kind='bar')")
                code_lines.append("        plt.title(f'Values for Year {recent_year}')")
                code_lines.append("        plt.ylabel('Count')")
                code_lines.append("        plt.xticks(rotation=45)")
                code_lines.append("        plt.tight_layout()")
                code_lines.append("        plt.show()")
                code_lines.append("")
            else:
                # Bar chart for all numeric columns
                code_lines.append("# Plot: Distribution of numeric values")
                code_lines.append("plt.figure(figsize=(12, 6))")
                if len(numeric_cols) > 0:
                    cols_str = ", ".join([f"'{c}'" for c in numeric_cols])
                    code_lines.append(f"df[[{cols_str}]].plot(kind='bar')")
                code_lines.append("plt.title('Numeric Values Distribution')")
                code_lines.append("plt.xticks(rotation=45)")
                code_lines.append("plt.tight_layout()")
                code_lines.append("plt.show()")
                code_lines.append("")
        
        # Add summary statistics
        code_lines.append("# Summary statistics")
        code_lines.append("print(\"Data Summary:\")")
        code_lines.append(f"print(df.describe())")
        code_lines.append("")
        
    elif isinstance(data, dict):
        # Single dict - convert to DataFrame
        code_lines.append("# Load data into DataFrame")
        code_lines.append(f"{data_name} = {json.dumps(data, indent=2)}")
        code_lines.append(f"df = pd.DataFrame([{data_name}])")
        code_lines.append("")
        code_lines.append("# Display the data")
        code_lines.append(f"print(\"Data:\")")
        code_lines.append(f"print(df)")
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
) -> dict[str, Any]:
    """
    Create a Quarto notebook from story content.
    
    Args:
        story_content: The main content for the notebook
        output_path: Path to save the notebook
        title: Title for the notebook
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
        # Try to use Jinja2 template first
        template = _load_template("quarto_notebook.j2")
        
        if template and JINJA2_AVAILABLE:
            # Generate Python code if data is provided and code cells are requested
            python_code = ""
            if include_code_cells and data is not None:
                python_code = _generate_data_visualization_code(data)
            
            # Prepare template variables
            timestamp = date or datetime.now().isoformat()
            
            # Escape story_content for Jinja2 to prevent template rendering issues
            escaped_story = _escape_jinja(story_content) if story_content else ""
            
            # Build metadata for template
            template_metadata = metadata or {}
            if 'tool_sequence' not in template_metadata:
                template_metadata['tool_sequence'] = []
            
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
                metadata=template_metadata
            )
        else:
            # Fallback to manual generation if template is not available
            logger.warning("Using manual Quarto generation (Jinja2 template not available)")
            
            # Escape story_content for safe insertion
            escaped_story = _escape_jinja(story_content) if story_content else ""
            
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
                    # Generate actual visualization code from data
                    viz_code = _generate_data_visualization_code(data)
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
        
        return {
            'content': quarto_content,
            'format': 'quarto',
            'path': output_path,
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
