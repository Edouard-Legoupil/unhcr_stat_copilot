"""
Tool: create_quarto_notebook
Create Quarto notebooks from data stories.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml


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
        # Generate notebook content
        yaml_header = {
            'title': title or 'UNHCR Data Analysis',
            'author': author or 'UNHCR Statistics Copilot',
            'date': date or datetime.now().strftime('%Y-%m-%d'),
            'format': {
                'html': {
                    'theme': 'cosmo' if use_unhcr_theme else None,
                    'css': 'styles.css' if use_unhcr_style else None
                }
            }
        }
        
        if metadata:
            yaml_header['metadata'] = metadata
        
        if original_query:
            yaml_header['original_query'] = original_query
        
        yaml_str = yaml.dump(yaml_header, default_flow_style=False, allow_unicode=True)
        
        # Add Quartro-specific markers
        quarto_content = f"""---
{yaml_str}---

"""
        
        if include_code_cells:
            if data is not None:
                # Generate actual visualization code from data
                viz_code = _generate_data_visualization_code(data)
                quarto_content += f"""```{{python}}
# Data Analysis Code
{viz_code}
```

"""
            else:
                # Fallback to placeholder if no data
                quarto_content += """```{python}
# Data Analysis Code
# Add your analysis code here
print("UNHCR Data Analysis")
```

"""
        
        quarto_content += f"""# {title or 'UNHCR Data Analysis'}

{story_content}

"""
        
        if include_code_cells:
            quarto_content += """```{python}
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
        return {
            'error': f'Failed to create Quarto notebook: {str(e)}',
            'status': 'error'
        }
