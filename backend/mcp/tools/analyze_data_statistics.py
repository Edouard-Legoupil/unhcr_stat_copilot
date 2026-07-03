"""
Tool: analyze_data_statistics
Perform statistical analysis on datasets.
"""

import statistics
from collections import Counter
from typing import Any, Optional


def analyze_data_statistics_tool(
    data: list[dict[str, Any]],
    numeric_columns: list[str],
    categorical_columns: Optional[list[str]] = None,
    correlation_columns: Optional[list[str]] = None
) -> dict[str, Any]:
    """
    Analyze data statistics and correlations (Phase 2 of AI reporting).
    
    Args:
        data: List of dictionaries representing data rows
        numeric_columns: List of numeric column names to analyze
        categorical_columns: List of categorical column names to analyze
        correlation_columns: List of column pairs to calculate correlations for
    
    Returns:
        Statistical analysis including distributions and correlations
    """
    if not data:
        return {'error': 'No data provided', 'status': 'error'}
        
    # Convert data to more workable format
    df = [{k: v for k, v in row.items() if k in numeric_columns + (categorical_columns or [])} for row in data]
    
    # Calculate basic statistics for numeric columns
    stats_results = {}
    
    for col in numeric_columns:
        values = [row.get(col) for row in df if row.get(col) is not None]
        if values:
            stats_results[col] = {
                'count': len(values),
                'mean': statistics.mean(values) if values else None,
                'median': statistics.median(values) if values else None,
                'min': min(values) if values else None,
                'max': max(values) if values else None,
                'std_dev': statistics.stdev(values) if len(values) > 1 else None
            }
    
    # Calculate frequency distributions for categorical columns
    freq_results = {}
    if categorical_columns:
        for col in categorical_columns:
            values = [row.get(col) for row in df if row.get(col) is not None]
            if values:
                freq_results[col] = dict(Counter(values))
    
    # Calculate correlations if requested
    correlation_results = {}
    if correlation_columns and len(correlation_columns) >= 2:
        try:
            import numpy as np
            from scipy.stats import pearsonr
            
            # Get the first two columns for correlation
            col1, col2 = correlation_columns[:2]
            values1 = [row.get(col1) for row in df if row.get(col1) is not None and row.get(col2) is not None]
            values2 = [row.get(col2) for row in df if row.get(col1) is not None and row.get(col2) is not None]
            
            if len(values1) >= 2 and len(values2) >= 2:
                corr, p_value = pearsonr(values1, values2)
                correlation_results[f'{col1}_vs_{col2}'] = {
                    'pearson_correlation': corr,
                    'p_value': p_value,
                    'sample_size': len(values1)
                }
        except ImportError:
            correlation_results['error'] = 'scipy not available for correlation calculation'
        except Exception as e:
            correlation_results['error'] = str(e)
    
    return {
        'statistics': stats_results,
        'frequencies': freq_results,
        'correlations': correlation_results,
        'metadata': {
            'source': 'UNHCR AI Data Analysis',
            'phase': 'statistical_analysis'
        }
    }
