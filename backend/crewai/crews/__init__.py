"""
Crews module for UNHCR Statistics Copilot

This module has been simplified to use a single UNHCRCrew class
instead of multiple separate crews (DataCrew, AnalysisCrew, StoryCrew, NotebookCrew, MasterCrew).

The single crew uses MCP tools directly via the AnalysisOrchestrator agent,
minimizing complexity and token consumption while maintaining full functionality.

For backward compatibility, the old crew classes are available in the backup:
- DataCrew (removed)
- AnalysisCrew (removed)
- StoryCrew (removed)
- NotebookCrew (removed)
- MasterCrew (removed)

All functionality is now consolidated in UNHCRCrew in backend.crewai.crew module.
"""

# Re-export the simplified crew
from backend.crewai.crew import UNHCRCrew, get_crew

__all__ = ['UNHCRCrew', 'get_crew']

# For backward compatibility, provide references to the new crew
# Users should update their code to use UNHCRCrew directly
DataCrew = UNHCRCrew
AnalysisCrew = UNHCRCrew
StoryCrew = UNHCRCrew
NotebookCrew = UNHCRCrew
MasterCrew = UNHCRCrew

__all__.extend(['DataCrew', 'AnalysisCrew', 'StoryCrew', 'NotebookCrew', 'MasterCrew'])
