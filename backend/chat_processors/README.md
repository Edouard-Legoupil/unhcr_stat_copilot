# Chat Processing Module

This module provides chat message processing for the UNHCR Statistics Copilot with support for both MCP-based and CrewAI-based orchestration.

## Architecture

The chat processing is now separated into two distinct implementations:

```
backend/
├── chat.py                          # Main module with router and exports
└── chat_processors/
    ├── mcp_processor.py             # MCP-based implementation
    └── crewai_processor.py          # CrewAI-based implementation with LLM
```

## Switching Between Processors

The processor is selected based on the `CHAT_PROCESSOR` environment variable:

```bash
# Use MCP (default)
CHAT_PROCESSOR=mcp

# Use CrewAI
CHAT_PROCESSOR=crewai
```

## Usage

### Basic Usage

```python
from backend.chat import process_chat_message

result = await process_chat_message(
    message="Show me refugee population trends in Syria",
    audience="policy_makers",
    document_type="executive_summary"
)

# Result includes:
# - question: The original question
# - analysis_type: "quarto_notebook"
# - quarto_content: Generated Quarto notebook
# - execution_source: "mcp" or "crewai"
```

### Advanced Usage

```python
from backend.chat import get_chat_processor, reset_chat_processor

# Get the current processor
processor = get_chat_processor()
print(processor.name)  # "mcp_processor" or "crewai_processor"

# Use it directly
result = await processor.process(
    message="...",
    audience="internal"
)

# Reset (useful for testing)
reset_chat_processor()
```

## CrewAI LLM Initialization

When using CrewAI processor (`CHAT_PROCESSOR=crewai`), the LLM is initialized in `crewai_processor.py`:

```python
from crewai import LLM

llm = LLM(
    model=f"azure/{os.getenv('AZURE_DEPLOYMENT_NAME', 'gpt-4.1')}",
    api_base=os.getenv("AZURE_OPENAI_ENDPOINT"),
    api_key=os.getenv("AZURE_OPENAI_API_KEY"),
    api_version=os.getenv("OPENAI_API_VERSION", "2024-10-21"),
    timeout=float(os.getenv("AZURE_OPENAI_TIMEOUT_SECONDS", "120"))
)
```

**Required Environment Variables for CrewAI:**
- `AZURE_OPENAI_ENDPOINT`
- `AZURE_OPENAI_API_KEY`
- `AZURE_DEPLOYMENT_NAME` (default: "gpt-4.1")
- `OPENAI_API_VERSION` (default: "2024-10-21")
- `AZURE_OPENAI_TIMEOUT_SECONDS` (default: "120")

## File Structure

### `backend/chat.py`
Main module that:
- Imports both processor classes from `backend/chat_processors/`
- Provides `get_chat_processor()` factory function
- Exports `process_chat_message()` convenience function
- Exports `ANALYSIS_CONFIG` and related utilities for backward compatibility

### `backend/chat_processors/mcp_processor.py`
MCP-based implementation that:
- Uses `call_tool()` to execute MCP tools directly
- Orchestrates workflow using Python functions
- Maintains the original behavior from the old `backend/chat.py`

### `backend/chat_processors/crewai_processor.py`
CrewAI-based implementation that:
- Initializes CrewAI LLM from environment variables
- Uses `CrewAIManager.execute_workflow()` for orchestration
- Delegates to CrewAI agents (AnalysisOrchestrator, DataFetcher, etc.)
- Connects to the same MCP server via tool adapters

## Backward Compatibility

The module maintains backward compatibility with the original `backend/chat.py`:

- `process_chat_message()` - Same signature, same behavior (routes based on env var)
- `run_tool_directly()` - Same signature
- `ANALYSIS_CONFIG` - Same configuration dictionary
- `get_analysis_config()` - Same utility function
- `get_available_document_types()` - Same utility function
- `get_default_document_type()` - Same utility function

## Migration from Old Code

If you were using the old `backend/chat.py` directly:

**Before:**
```python
from backend.chat import process_chat_message
result = await process_chat_message(...)
```

**After:**
```python
# Same import, same function call
from backend.chat import process_chat_message
result = await process_chat_message(...)

# To check which processor was used:
print(result.get("execution_source"))  # "mcp" or "crewai"
```

## Testing

```python
import os

# Test with MCP
os.environ["CHAT_PROCESSOR"] = "mcp"
from backend.chat import get_chat_processor, reset_chat_processor

processor = get_chat_processor()
assert processor.name == "mcp_processor"

# Switch to CrewAI
reset_chat_processor()
os.environ["CHAT_PROCESSOR"] = "crewai"
processor = get_chat_processor()
assert processor.name == "crewai_processor"
```

## Configuration Reference

| Environment Variable | Default | Description |
|----------------------|---------|-------------|
| `CHAT_PROCESSOR` | `mcp` | Select processor: "mcp" or "crewai" |
| `AZURE_DEPLOYMENT_NAME` | `gpt-4.1` | Azure OpenAI deployment name (CrewAI only) |
| `AZURE_OPENAI_ENDPOINT` | - | Azure OpenAI endpoint URL (CrewAI only) |
| `AZURE_OPENAI_API_KEY` | - | Azure OpenAI API key (CrewAI only) |
| `OPENAI_API_VERSION` | `2024-10-21` | API version (CrewAI only) |
| `AZURE_OPENAI_TIMEOUT_SECONDS` | `120` | Timeout in seconds (CrewAI only) |
