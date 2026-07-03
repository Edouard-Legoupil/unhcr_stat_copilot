"""
Tool: create_quarto_notebook
Create Quarto notebooks from data stories.
"""

from datetime import datetime
from pathlib import Path
from typing import Any, Optional
import yaml


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
    metadata: Optional[dict[str, Any]] = None
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
