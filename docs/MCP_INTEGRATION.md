# MCP Server Integration Guide

Complete guide to integrating with the UNHCR Statistics Copilot MCP Server.

## 📚 Table of Contents

- [Overview](#overview)
- [MCP Protocol Basics](#mcp-protocol-basics)
- [Server Configuration](#server-configuration)
- [Client Integration](#client-integration)
  - [Python Integration](#python-integration)
  - [JavaScript/TypeScript Integration](#javascripttypescript-integration)
  - [CLI Tools](#cli-tools)
- [Tool Discovery](#tool-discovery)
- [Tool Execution](#tool-execution)
- [Error Handling](#error-handling)
- [Best Practices](#best-practices)
- [Examples](#examples)
- [Troubleshooting](#troubleshooting)

---

## 🎯 Overview

The UNHCR Statistics Copilot provides a **Model Context Protocol (MCP)** server that exposes 20+ specialized tools for accessing and analyzing UNHCR data. The MCP server uses the **Streamable HTTP** transport protocol, making it easy to integrate with any HTTP-capable client.

### Key Features

- ✅ **20+ specialized tools** for UNHCR data analysis
- ✅ **Streamable HTTP transport** - No WebSocket required
- ✅ **JSON-RPC compatible** - Standard request/response format
- ✅ **Tool discovery** - List all available tools with descriptions
- ✅ **Type-safe arguments** - All tools have defined parameter schemas
- ✅ **Error handling** - Consistent error responses
- ✅ **Rate limiting** - Built-in protection against abuse

### Use Cases

1. **AI Agents**: Connect AI assistants to UNHCR data
2. **Chat Applications**: Build chatbots with UNHCR data access
3. **Dashboards**: Integrate UNHCR data into existing dashboards
4. **CLI Tools**: Create command-line tools for data analysis
5. **Automation**: Automate UNHCR data retrieval and reporting

---

## 📡 MCP Protocol Basics

### Transport Protocol

The UNHCR MCP server uses **Streamable HTTP**, which is a simple HTTP-based transport for MCP:

- **Protocol**: HTTP/1.1 or HTTP/2
- **Content-Type**: `application/json`
- **Encoding**: UTF-8
- **Method**: POST for all requests

### Request Format

All MCP requests are JSON-RPC 2.0 compatible:

```json
{
  "jsonrpc": "2.0",
  "id": "unique-request-id",
  "method": "tool_name",
  "params": {
    "arguments": { ... }
  }
}
```

However, the UNHCR server also accepts a simplified format:

```json
{
  "tool": "tool_name",
  "arguments": { ... }
}
```

### Response Format

All responses follow JSON-RPC 2.0 format:

```json
{
  "jsonrpc": "2.0",
  "id": "request-id",
  "result": { ... },
  "error": null
}
```

Or simplified:

```json
{
  "status": "success",
  "data": { ... },
  "error": null
}
```

### Endpoint

```
POST /mcp
Host: localhost:8000
Content-Type: application/json
```

---

## ⚙️ Server Configuration

### Server Details

| Property | Value |
|----------|-------|
| **Server Name** | UNHCR Forcibly Displaced Populations MCP Server |
| **Version** | 1.0.0 |
| **Transport** | Streamable HTTP |
| **Mount Path** | `/mcp` |
| **Streamable HTTP Path** | `/` |

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `MCP_SERVER_URL` | Base URL for MCP server | `http://localhost:8000/mcp/` |
| `MCP_TIMEOUT_SECONDS` | Request timeout | 30 |
| `MCP_MAX_RETRIES` | Maximum retry attempts | 3 |

### Health Check

The MCP server endpoint responds to simple health checks:

```bash
# Simple GET request
curl http://localhost:8000/mcp

# Response: 200 OK with health info
{
  "status": "ok",
  "message": "MCP endpoint active",
  "mcp_protocol": "/mcp/"
}
```

---

## 🔌 Client Integration

### Python Integration

#### Using `requests` Library

```python
import requests
import json

MCP_SERVER_URL = "http://localhost:8000/mcp"

def call_mcp_tool(tool_name: str, arguments: dict):
    """Call an MCP tool and return the result."""
    payload = {
        "tool": tool_name,
        "arguments": arguments
    }
    
    response = requests.post(
        MCP_SERVER_URL,
        json=payload,
        headers={"Content-Type": "application/json"},
        timeout=30
    )
    
    response.raise_for_status()
    return response.json()

# Example usage
result = call_mcp_tool("get_population_data", {
    "coo": "SYR",
    "coa": "TUR",
    "year": 2024
})

print(result)
```

#### Using `httpx` (Recommended for Async)

```python
import httpx
import asyncio

MCP_SERVER_URL = "http://localhost:8000/mcp"

async def call_mcp_tool_async(tool_name: str, arguments: dict):
    """Async MCP tool call."""
    payload = {
        "tool": tool_name,
        "arguments": arguments
    }
    
    async with httpx.AsyncClient(timeout=30) as client:
        response = await client.post(
            MCP_SERVER_URL,
            json=payload,
            headers={"Content-Type": "application/json"}
        )
        response.raise_for_status()
        return response.json()

# Example usage
async def main():
    result = await call_mcp_tool_async("get_population_data", {
        "coo": "SYR",
        "year": 2024
    })
    print(result)

asyncio.run(main())
```

#### Using MCP Python SDK

```python
from mcp import ClientSession
from mcp.client.streamable_http import streamablehttp_client

async def use_mcp_sdk():
    async with streamablehttp_client("http://localhost:8000/mcp/") as (read, write, _):
        async with ClientSession(read, write) as session:
            await session.initialize()
            
            # Call a tool
            result = await session.call_tool(
                "get_population_data",
                {"coo": "SYR", "year": 2024}
            )
            
            # Process result
            print(result.content)

asyncio.run(use_mcp_sdk())
```

### JavaScript/TypeScript Integration

#### Using `fetch` API

```typescript
interface MCPRequest {
  tool: string;
  arguments: Record<string, any>;
}

interface MCPResponse {
  status: string;
  data: any;
  error?: string;
}

const MCP_SERVER_URL = "http://localhost:8000/mcp";

async function callMCPTool(tool: string, args: Record<string, any>): Promise<MCPResponse> {
  const payload: MCPRequest = {
    tool,
    arguments: args
  };

  const response = await fetch(MCP_SERVER_URL, {
    method: "POST",
    headers: {
      "Content-Type": "application/json"
    },
    body: JSON.stringify(payload)
  });

  if (!response.ok) {
    throw new Error(`MCP request failed: ${response.status} ${response.statusText}`);
  }

  return response.json();
}

// Example usage
async function getPopulationData() {
  const result = await callMCPTool("get_population_data", {
    coo: "SYR",
    coa: "TUR",
    year: 2024
  });
  
  console.log(result);
}

getPopulationData();
```

#### Using Axios

```typescript
import axios from 'axios';

const MCP_SERVER_URL = "http://localhost:8000/mcp";

interface MCPRequest {
  tool: string;
  arguments: Record<string, any>;
}

async function callMCPTool(tool: string, args: Record<string, any>) {
  const payload: MCPRequest = {
    tool,
    arguments: args
  };

  const response = await axios.post(MCP_SERVER_URL, payload, {
    headers: {
      "Content-Type": "application/json"
    },
    timeout: 30000
  });

  return response.data;
}

// Example usage
callMCPTool("get_population_data", { coo: "SYR", year: 2024 })
  .then(console.log)
  .catch(console.error);
```

### CLI Tools

#### Using `curl`

```bash
# Simple tool call
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_population_data", "arguments": {"coo": "SYR", "year": 2024}}'

# With jq for pretty printing
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_population_data", "arguments": {"coo": "SYR"}}' | jq

# Save to file
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_population_data", "arguments": {"coo": "SYR"}}' \
  -o response.json
```

#### Using MCP Inspector

```bash
# Install MCP Inspector
npm install -g mcp-inspector

# Inspect the server
mcp-inspector --server-url http://localhost:8000/mcp

# This provides:
# - Tool discovery
# - Interactive testing
# - Request/response logging
```

---

## 🔍 Tool Discovery

### List All Tools

Use the `/tools` endpoint to get a complete list of available tools:

```bash
curl http://localhost:8000/tools
```

Or the MCP-specific endpoint:

```bash
curl http://localhost:8000/api/mcp/docs
```

### Get Tool Information

```bash
# Get full documentation
curl http://localhost:8000/api/mcp/docs

# Get server info
curl http://localhost:8000/api/mcp/info
```

### Tool Schema

Each tool has the following schema:

```json
{
  "name": "tool_name",
  "description": "Human-readable description",
  "required_params": ["param1", "param2"],
  "optional_params": ["param3", "param4"],
  "param_types": {
    "param1": "str",
    "param2": "int",
    "param3": ["str", "int"],
    "param4": "bool"
  },
  "example_usage": "call_tool('tool_name', {param1: 'value'})"
}
```

---

## ⚡ Tool Execution

### Execution Flow

1. **Client** sends POST request to `/mcp` with tool name and arguments
2. **Server** validates request format and tool existence
3. **Server** validates arguments against tool schema
4. **Server** executes tool function with provided arguments
5. **Tool** makes any necessary API calls (e.g., to UNHCR API)
6. **Tool** returns result to server
7. **Server** formats response and returns to client

### Request Format

```json
{
  "tool": "string (required)",
  "arguments": "object (required)"
}
```

### Response Format

```json
{
  "tool": "string",
  "result": "any",
  "user": "object (optional)"
}
```

### Tool Categories

#### 📊 Population Data Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `get_population_data` | Get forcibly displaced population statistics | None |
| `get_demographics_data` | Get age/sex breakdown data | None |
| `get_population_trends` | Get population changes over time | None |
| `get_demographic_breakdown` | Get detailed demographic analysis | None |
| `get_country_key_figures` | Get key statistics for countries | None |

#### ⚖️ RSD (Refugee Status Determination) Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `get_rsd_applications` | Get RSD application statistics | None |
| `get_rsd_decisions` | Get RSD decision outcomes | None |

#### 🎯 Solutions Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `get_solutions` | Get durable solutions data | None |

#### 📈 Analysis Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `analyze_data_statistics` | Perform statistical analysis | `data`, `numeric_columns` |
| `apply_analysis_guardrails` | Apply methodology validation | `analysis_request` |

#### 📊 Visualization Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `extract_visualization_structure` | Extract visualization metadata | `visualization_type` |
| `generate_visualization` | Generate description for visualization | `structure`, `statistics` |

#### 📖 Story Generation Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `generate_ai_data_story` | Generate AI data story | `visualization_data` |
| `generate_analytical_story` | Generate analytical story | None |
| `create_quarto_notebook` | Create Quarto notebook | `story_content` |

#### 🔄 Workflow Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `full_analysis_workflow` | Complete analysis workflow | `question` |
| `quick_analysis` | Quick analysis (no notebook) | `question` |
| `compare_analysis` | Compare multiple scenarios | `question_template`, `comparisons` |

#### 🎯 Data & Context Tools

| Tool | Description | Required Params |
|------|-------------|-----------------|
| `retrieve_report_context` | Retrieve context from reports | `request` |
| `get_data_for_story` | Get data for story generation | `question` |
| `safe_tool_selection` | Select appropriate tool | `question` |
| `get_usage_guidance` | Get usage guidance | None |
| `get_suggested_questions` | Get suggested questions | None |

---

## ❌ Error Handling

### Error Response Format

```json
{
  "status": "error",
  "error": {
    "code": "ERROR_CODE",
    "message": "Human-readable error message",
    "details": { ... }
  }
}
```

### Common Error Codes

| Code | HTTP Status | Description | Solution |
|------|--------------|-------------|----------|
| `INVALID_TOOL` | 400 | Tool does not exist | Check tool name in `/tools` |
| `INVALID_ARGUMENTS` | 400 | Arguments don't match schema | Validate arguments |
| `MISSING_REQUIRED_ARG` | 400 | Required argument missing | Provide all required params |
| `MCP_UNAVAILABLE` | 503 | MCP server not available | Check server health |
| `TIMEOUT` | 504 | Request timeout | Increase timeout or retry |
| `RATE_LIMITED` | 429 | Too many requests | Wait and retry |
| `INTERNAL_ERROR` | 500 | Server error | Check logs, report issue |

### Error Handling Examples

#### Python

```python
import requests
from requests.exceptions import HTTPError

try:
    response = requests.post(
        "http://localhost:8000/mcp",
        json={"tool": "invalid_tool"},
        timeout=30
    )
    response.raise_for_status()
    result = response.json()
except HTTPError as e:
    if e.response.status_code == 400:
        error_data = e.response.json()
        print(f"Validation error: {error_data['error']['message']}")
    elif e.response.status_code == 503:
        print("MCP server unavailable, please retry")
    else:
        print(f"Error: {e}")
except requests.exceptions.Timeout:
    print("Request timeout, please retry")
except requests.exceptions.RequestException as e:
    print(f"Request failed: {e}")
```

#### JavaScript

```typescript
async function callMCPTool(tool: string, args: any) {
  try {
    const response = await fetch("http://localhost:8000/mcp", {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ tool, arguments: args }),
      timeout: 30000
    });

    if (!response.ok) {
      const error = await response.json();
      throw new Error(error.error?.message || "MCP request failed");
    }

    return await response.json();
  } catch (error) {
    if (error.name === "AbortError") {
      console.error("Request timeout");
    } else if (error.name === "TypeError") {
      console.error("Network error");
    } else {
      console.error(`Error: ${error.message}`);
    }
    throw error;
  }
}
```

---

## 🎯 Best Practices

### 1. Always Validate Inputs

```python
# Check tool exists
tools = requests.get("http://localhost:8000/tools").json()["tools"]
tool_names = [t["name"] for t in tools]

if tool_name not in tool_names:
    raise ValueError(f"Unknown tool: {tool_name}")

# Validate arguments
tool_schema = next(t for t in tools if t["name"] == tool_name)
required_params = tool_schema["required_params"]

for param in required_params:
    if param not in arguments:
        raise ValueError(f"Missing required parameter: {param}")
```

### 2. Implement Retry Logic

```python
import requests
import time
from requests.exceptions import RequestException

def call_mcp_tool_with_retry(tool, arguments, max_retries=3, timeout=30):
    for attempt in range(max_retries):
        try:
            response = requests.post(
                "http://localhost:8000/mcp",
                json={"tool": tool, "arguments": arguments},
                timeout=timeout
            )
            response.raise_for_status()
            return response.json()
        except RequestException as e:
            if attempt < max_retries - 1:
                wait_time = 2 ** attempt  # Exponential backoff
                time.sleep(wait_time)
            else:
                raise
```

### 3. Use Timeouts

```python
# Always set a timeout
response = requests.post(
    "http://localhost:8000/mcp",
    json=payload,
    timeout=30  # 30 seconds
)
```

### 4. Batch Requests When Possible

```python
# Instead of multiple individual calls:
results = []
for tool in tools:
    results.append(call_mcp_tool(tool, args))

# Consider batching if the API supports it
# (Note: Current implementation doesn't support batching)
```

### 5. Cache Responses When Appropriate

```python
import functools
import requests

cache = {}

def cached_mcp_call(timeout=300):
    """Cache MCP tool calls for `timeout` seconds."""
    def decorator(func):
        @functools.wraps(func)
        def wrapper(tool, arguments):
            cache_key = f"{tool}:{hash(frozenset(arguments.items()))}"
            if cache_key in cache:
                cached_result, cached_time = cache[cache_key]
                if time.time() - cached_time < timeout:
                    return cached_result
            
            result = func(tool, arguments)
            cache[cache_key] = (result, time.time())
            return result
        return wrapper
    return decorator

@cached_mcp_call(timeout=300)  # 5 minutes
def call_mcp_tool(tool, arguments):
    # ... implementation
```

### 6. Log Requests for Debugging

```python
import logging
import requests

logger = logging.getLogger(__name__)

def call_mcp_tool(tool, arguments):
    logger.debug(f"Calling MCP tool: {tool} with args: {arguments}")
    
    try:
        response = requests.post(
            "http://localhost:8000/mcp",
            json={"tool": tool, "arguments": arguments},
            timeout=30
        )
        logger.debug(f"Response status: {response.status_code}")
        response.raise_for_status()
        return response.json()
    except Exception as e:
        logger.error(f"MCP tool call failed: {tool} - {e}")
        raise
```

---

## 📝 Examples

### Example 1: Population Data Analysis

```python
import requests

# Get population data
response = requests.post(
    "http://localhost:8000/mcp",
    json={
        "tool": "get_population_data",
        "arguments": {
            "coo": "SYR",  # Country of Origin (ISO 3-letter code)
            "coa": "TUR",  # Country of Asylum (ISO 3-letter code)
            "year": 2024
        }
    }
)

result = response.json()
print(f"Population: {result['result']['data'][0]['value']}")
```

### Example 2: Demographic Breakdown

```python
import requests

# Get demographic breakdown
response = requests.post(
    "http://localhost:8000/mcp",
    json={
        "tool": "get_demographics_data",
        "arguments": {
            "coo": "SYR",
            "coa": "TUR",
            "year": 2024
        }
    }
)

result = response.json()
print(f"Demographic data: {result['result']['data']}")
```

### Example 3: RSD Applications

```python
import requests

# Get RSD applications
response = requests.post(
    "http://localhost:8000/mcp",
    json={
        "tool": "get_rsd_applications",
        "arguments": {
            "coo": "SYR",
            "coa": "DEU",  # Germany
            "year": 2024
        }
    }
)

result = response.json()
print(f"RSD applications: {result['result']['data']}")
```

### Example 4: Generate Data Story

```python
import requests

# Generate a data story
response = requests.post(
    "http://localhost:8000/mcp",
    json={
        "tool": "generate_ai_data_story",
        "arguments": {
            "visualization_data": {
                "data": [{"year": 2020, "value": 1000}, {"year": 2024, "value": 2000}],
                "structure": {
                    "visualization_type": "line_chart",
                    "labels": {"title": "Refugee Trends", "x": "Year", "y": "Count"}
                }
            },
            "context": "Analyze refugee trends from Syria",
            "story_type": "analytical",
            "max_tokens": 500
        }
    }
)

result = response.json()
print(f"Story: {result['result']['story']}")
```

### Example 5: Full Analysis Workflow

```python
import requests

# Execute full analysis workflow
response = requests.post(
    "http://localhost:8000/mcp",
    json={
        "tool": "full_analysis_workflow",
        "arguments": {
            "question": "What are the latest trends in refugee populations from Syria?",
            "origin": "SYR",
            "destination": "TUR",
            "timespan": "2020-2024",
            "audience": "policy_maker",
            "document_type": "executive_summary",
            "use_enhanced": True,
            "use_rag": True,
            "include_notebook": True
        }
    }
)

result = response.json()
print(f"Analysis ID: {result['result']['analysis_id']}")
print(f"Story: {result['result']['story']}")
```

### Example 6: JavaScript - Complete Integration

```javascript
class UNHCRAPIClient {
  constructor(baseUrl = "http://localhost:8000") {
    this.baseUrl = baseUrl;
  }

  async callTool(tool, args) {
    const response = await fetch(`${this.baseUrl}/mcp`, {
      method: "POST",
      headers: {"Content-Type": "application/json"},
      body: JSON.stringify({ tool, arguments: args })
    });

    if (!response.ok) {
      throw new Error(`MCP request failed: ${response.status}`);
    }

    return response.json();
  }

  async getPopulationData(coo, coa, year) {
    return this.callTool("get_population_data", { coo, coa, year });
  }

  async getDemographicsData(coo, coa, year) {
    return this.callTool("get_demographics_data", { coo, coa, year });
  }

  async getRSDAplications(coo, coa, year) {
    return this.callTool("get_rsd_applications", { coo, coa, year });
  }

  async generateAnalysis(question, options = {}) {
    return this.callTool("full_analysis_workflow", {
      question,
      ...options
    });
  }
}

// Usage
const client = new UNHCRAPIClient();

async function analyzeRefugeeData() {
  const population = await client.getPopulationData("SYR", "TUR", 2024);
  console.log("Population:", population);

  const demographics = await client.getDemographicsData("SYR", "TUR", 2024);
  console.log("Demographics:", demographics);

  const analysis = await client.generateAnalysis(
    "What are the refugee trends from Syria?",
    { origin: "SYR", destination: "TUR", timespan: "2020-2024" }
  );
  console.log("Analysis:", analysis);
}

analyzeRefugeeData();
```

---

## 🐛 Troubleshooting

### Common Issues and Solutions

| Issue | Cause | Solution |
|-------|-------|----------|
| Connection refused | Server not running | Start the server with `python -m backend.main` |
| 404 Not Found | Wrong endpoint | Use `/mcp` (not `/mcp/`) for tool calls |
| 400 Bad Request | Invalid JSON | Validate request format |
| 400 Bad Request | Unknown tool | Check tool name in `/tools` |
| 400 Bad Request | Invalid args | Validate arguments against schema |
| 503 Service Unavailable | MCP server not ready | Check server health at `/mcp` |
| Timeout | Slow response | Increase timeout or check server logs |
| Rate limited | Too many requests | Wait and retry with exponential backoff |

### Debugging Steps

1. **Check server health**
   ```bash
   curl http://localhost:8000/health
   ```

2. **Check MCP endpoint**
   ```bash
   curl http://localhost:8000/mcp
   ```

3. **List available tools**
   ```bash
   curl http://localhost:8000/tools
   ```

4. **Check server logs**
   ```bash
   # If running locally
   python -m backend.main --log-level debug
   ```

5. **Test with a simple tool**
   ```bash
   curl -X POST http://localhost:8000/mcp \
     -d '{"tool": "get_usage_guidance", "arguments": {}}'
   ```

### Connection Testing Script

```python
import requests

def test_mcp_connection():
    """Test MCP server connection and basic functionality."""
    base_url = "http://localhost:8000"
    
    # Test 1: Health check
    try:
        r = requests.get(f"{base_url}/health")
        assert r.status_code == 200
        print("✓ Health check passed")
    except Exception as e:
        print(f"✗ Health check failed: {e}")
        return False
    
    # Test 2: MCP endpoint
    try:
        r = requests.get(f"{base_url}/mcp")
        assert r.status_code == 200
        print("✓ MCP endpoint accessible")
    except Exception as e:
        print(f"✗ MCP endpoint failed: {e}")
        return False
    
    # Test 3: Tool list
    try:
        r = requests.get(f"{base_url}/tools")
        assert r.status_code == 200
        tools = r.json()["tools"]
        print(f"✓ Tool list retrieved ({len(tools)} tools)")
    except Exception as e:
        print(f"✗ Tool list failed: {e}")
        return False
    
    # Test 4: Simple tool call
    try:
        r = requests.post(
            f"{base_url}/mcp",
            json={"tool": "get_usage_guidance", "arguments": {}}
        )
        assert r.status_code == 200
        print("✓ Tool call successful")
    except Exception as e:
        print(f"✗ Tool call failed: {e}")
        return False
    
    return True

if __name__ == "__main__":
    if test_mcp_connection():
        print("\n✓ All tests passed! MCP server is working correctly.")
    else:
        print("\n✗ Some tests failed. Please check the server.")
```

---

## 📚 Additional Resources

- [MCP Specification](https://modelcontextprotocol.io/specification)
- [FastMCP Documentation](https://github.com/modelcontextprotocol/fastmcp)
- [UNHCR API Documentation](https://api.unhcr.org/documentation)
- [API Documentation](../API_DOCUMENTATION.md)
- [Troubleshooting Guide](../TROUBLESHOOTING.md)

---

*Last updated: July 7, 2026*
