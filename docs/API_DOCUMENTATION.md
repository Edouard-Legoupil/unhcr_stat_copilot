# API Documentation

Complete reference for all REST API endpoints in the UNHCR Statistics Copilot.

## 📚 Table of Contents

- [Base URL](#base-url)
- [Authentication](#authentication)
- [Response Format](#response-format)
- [Error Handling](#error-handling)
- [Rate Limiting](#rate-limiting)
- [Endpoints](#endpoints)
  - [Health & Status](#health--status)
  - [MCP Documentation](#mcp-documentation)
  - [Tool Execution](#tool-execution)
  - [Chat & Analysis](#chat--analysis)
  - [History & Reports](#history--reports)
  - [Utility Endpoints](#utility-endpoints)
- [OpenAPI Schema](#openapi-schema)
- [Examples](#examples)

---

## 🌐 Base URL

```
# Development
http://localhost:8000

# Production (Azure)
https://<app-name>.azurewebsites.net
```

All endpoints are relative to the base URL.

---

## 🔐 Authentication

**Current Status**: No authentication required (open access)

**Recommended for Production**: Azure AD authentication

### Azure AD Configuration

```python
# In backend/app.py
from backend.auth import verify_azure_auth, get_optional_user

@app.get("/protected")
async def protected_route(user: UserInfo = Depends(verify_azure_auth)):
    return {"user": user.email}
```

---

## 📤 Response Format

All endpoints return JSON responses with the following structure:

### Success Response

```json
{
  "status": "success",
  "data": { ... },
  "message": "Optional success message"
}
```

### Error Response

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

---

## ⚡ Rate Limiting

- **Enabled**: Yes (configurable via `RATE_LIMIT_ENABLED`)
- **Default Limit**: 10 requests per minute per IP
- **Header**: `X-RateLimit-Limit`, `X-RateLimit-Remaining`, `X-RateLimit-Reset`

### Rate Limit Configuration

```bash
# Enable/disable
RATE_LIMIT_ENABLED=true

# Customize limits
# (configured in backend/app.py)
```

---

## 📡 Endpoints

---

### 🏥 Health & Status

#### GET `/health`

Check the health status of the service.

**Request**
```bash
curl http://localhost:8000/health
```

**Response**
```json
{
  "status": "healthy",
  "service": "unhcr-statistics-copilot",
  "frontend": true,
  "api": "available"
}
```

**Status Codes**
- `200 OK` - Service is healthy

---

#### GET `/`

Get API root information.

**Request**
```bash
curl http://localhost:8000/
```

**Response**
```json
{
  "application": "UNHCR Copilot",
  "version": "1.0.0",
  "mcp": "/mcp",
  "chat": "/chat",
  "docs": "/docs",
  "frontend": "/",
  "health": "/health"
}
```

---

### 📚 MCP Documentation

#### GET `/api/mcp/docs`

Get comprehensive MCP server documentation.

**Request**
```bash
# JSON response
curl http://localhost:8000/api/mcp/docs

# HTML response (browser)
curl -H "Accept: text/html" http://localhost:8000/api/mcp/docs
```

**Response (JSON)**
```json
{
  "server": {
    "name": "UNHCR Forcibly Displaced Populations MCP Server",
    "description": "Provides UNHCR population data tools and data-story generation...",
    "version": "1.0.0"
  },
  "tools": {
    "get_population_data": {
      "description": "Retrieve forcibly displaced population statistics from UNHCR",
      "required_params": [],
      "optional_params": ["coo", "coa", "year", "coo_all", "coa_all"],
      "param_types": {
        "coo": "str",
        "coa": "str",
        "year": ["str", "int"],
        "coo_all": "bool",
        "coa_all": "bool"
      },
      "example": "call_tool('get_population_data', {'coo': 'SYR', 'year': 2024})"
    },
    ... (20+ tools)
  },
  "endpoints": {
    "mcp_base": "/mcp",
    "mcp_docs": "/api/mcp/docs",
    "mcp_info": "/api/mcp/info",
    "tools_list": "/tools",
    "execute_tool": "/tool",
    "chat": "/chat",
    "health": "/health"
  },
  "total_tools": 20,
  "documentation": {
    "format": "JSON",
    "generated_at": "2026-07-07T12:00:00Z",
    "fastapi_docs": "/docs",
    "redoc": "/redoc"
  }
}
```

**Response (HTML)**
Returns a beautiful HTML documentation page with:
- Interactive navigation
- Collapsible sections
- Copy-to-clipboard functionality
- Live endpoint testing

**Status Codes**
- `200 OK` - Documentation retrieved

---

#### GET `/api/mcp/info`

Get MCP server metadata and summary.

**Request**
```bash
curl http://localhost:8000/api/mcp/info
```

**Response**
```json
{
  "server": {
    "name": "UNHCR Forcibly Displaced Populations MCP Server",
    "description": "Provides UNHCR population data tools and data-story generation...",
    "version": "1.0.0"
  },
  "endpoint": "/mcp",
  "tools_count": 20,
  "tool_names": [
    "get_population_data",
    "get_demographics_data",
    "get_rsd_applications",
    "get_rsd_decisions",
    "get_solutions",
    "get_country_key_figures",
    "get_population_trends",
    "get_demographic_breakdown",
    "retrieve_report_context",
    "extract_visualization_structure",
    "analyze_data_statistics",
    "generate_visualization_description",
    "generate_ai_data_story",
    "get_usage_guidance",
    "get_suggested_questions",
    "apply_analysis_guardrails",
    "create_quarto_notebook",
    "safe_tool_selection",
    "get_data_for_story",
    "full_analysis_workflow",
    "quick_analysis",
    "compare_analysis"
  ],
  "status": "running",
  "documentation_endpoints": {
    "full_docs": "/api/mcp/docs",
    "tool_list": "/tools"
  },
  "timestamp": "2026-07-07T12:00:00Z"
}
```

**Status Codes**
- `200 OK` - Server info retrieved

---

#### GET `/tools`

List all available MCP tools with detailed metadata.

**Request**
```bash
curl http://localhost:8000/tools
```

**Response**
```json
{
  "tools": [
    {
      "name": "get_population_data",
      "description": "Retrieve forcibly displaced population statistics from UNHCR",
      "required_params": [],
      "optional_params": ["coo", "coa", "year", "coo_all", "coa_all"],
      "param_types": {
        "coo": "str",
        "coa": "str",
        "year": ["str", "int"],
        "coo_all": "bool",
        "coa_all": "bool"
      },
      "example_usage": "call_tool('get_population_data', {'coo': 'SYR', 'year': 2024})",
      "execution_endpoint": "/tool"
    },
    ... (all 20 tools)
  ],
  "total": 20,
  "server": "UNHCR Forcibly Displaced Populations MCP Server",
  "mcp_endpoint": "/mcp",
  "full_documentation": "/api/mcp/docs",
  "server_info": "/api/mcp/info"
}
```

**Status Codes**
- `200 OK` - Tool list retrieved

---

### 🛠️ Tool Execution

#### POST `/tool`

Execute a specific MCP tool with provided arguments.

**Request**
```bash
curl -X POST http://localhost:8000/tool \
  -H "Content-Type: application/json" \
  -d '{
    "tool": "get_population_data",
    "arguments": {
      "coo": "SYR",
      "coa": "TUR",
      "year": 2024
    }
  }'
```

**Request Body**
```json
{
  "tool": "string (required)",
  "arguments": "object (required)"
}
```

**Response**
```json
{
  "tool": "get_population_data",
  "result": {
    "data": [
      {
        "coo": "SYR",
        "coa": "TUR",
        "year": 2024,
        "value": 3680000,
        "population_type": "Refugees",
        "source": "UNHCR"
      }
    ],
    "metadata": {
      "total": 1,
      "query": {
        "coo": "SYR",
        "coa": "TUR",
        "year": 2024
      },
      "timestamp": "2026-07-07T12:00:00Z"
    }
  },
  "user": {
    "name": "user@example.com"
  }
}
```

**Status Codes**
- `200 OK` - Tool executed successfully
- `400 Bad Request` - Invalid tool request or validation error
- `401 Unauthorized` - Authentication required
- `503 Service Unavailable` - MCP server unavailable

---

#### POST `/chat`

Process a chat message and generate a response.

**Request**
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{
    "message": "What are the latest refugee numbers from Syria?",
    "origin": "SYR",
    "destination": "TUR",
    "topic": "refugee_statistics",
    "timespan": "2020-2024",
    "audience": "policy_maker",
    "document_type": "executive_summary"
  }'
```

**Request Body**
```json
{
  "message": "string (required)",
  "origin": "string (optional)",
  "destination": "string (optional)",
  "topic": "string (optional)",
  "timespan": "string (optional)",
  "audience": "string (optional)",
  "document_type": "string (optional)"
}
```

**Response**
```json
{
  "analysis": {
    "id": "uuid",
    "question": "What are the latest refugee numbers from Syria?",
    "answer": "As of 2024, there are approximately 3.68 million Syrian refugees in Turkey...",
    "data_sources": ["UNHCR API"],
    "methodology": "Data retrieved from UNHCR Population API",
    "confidence": "high",
    "caveats": ["Data may have a 1-2 month lag"],
    "recommendations": ["Consider cross-referencing with Turkish government data"]
  },
  "visualization": {
    "type": "chart",
    "data": [...],
    "structure": { ... }
  },
  "tools_used": ["get_population_data", "generate_ai_data_story"],
  "metadata": {
    "timestamp": "2026-07-07T12:00:00Z",
    "duration_ms": 1500,
    "user": "user@example.com"
  }
}
```

**Status Codes**
- `200 OK` - Chat processed successfully
- `400 Bad Request` - Invalid request
- `503 Service Unavailable` - MCP server unavailable

---

### 📊 Chat & Analysis

#### POST `/story`

Generate a data story from provided data and parameters.

**Request**
```bash
curl -X POST http://localhost:8000/story \
  -H "Content-Type: application/json" \
  -d '{
    "data": {"refugees": 3680000, "year": 2024},
    "visualization_data": { ... },
    "question": "What are the refugee trends?",
    "audience": "policy_maker",
    "document_type": "executive_summary"
  }'
```

**Request Body**
```json
{
  "data": "object (optional)",
  "visualization_data": "object (optional)",
  "question": "string (optional)",
  "audience": "string (optional)",
  "document_type": "string (optional)"
}
```

**Response**
```json
{
  "status": "success",
  "story": {
    "title": "Syrian Refugee Trends in Turkey: 2020-2024",
    "content": "Comprehensive analysis of refugee data...",
    "metadata": {
      "audience": "policy_maker",
      "document_type": "executive_summary",
      "word_count": 500,
      "sections": ["Introduction", "Data Analysis", "Recommendations"]
    }
  },
  "visualization": {
    "type": "chart",
    "data": [...],
    "structure": { ... }
  },
  "tools_used": ["generate_ai_data_story", "analyze_data_statistics"],
  "analysis_id": "uuid"
}
```

**Status Codes**
- `200 OK` - Story generated successfully

---

#### POST `/report`

Generate a comprehensive report with analysis and visualizations.

**Request**
```bash
curl -X POST http://localhost:8000/report \
  -H "Content-Type: application/json" \
  -d '{
    "question": "Analyze refugee trends from Syria",
    "origin": "SYR",
    "destination": "TUR",
    "timespan": "2020-2024",
    "audience": "policy_maker",
    "document_type": "policy_report",
    "style": "detailed",
    "include_notebook": true,
    "include_html": true,
    "include_pdf": false
  }'
```

**Request Body**
```json
{
  "question": "string (required)",
  "origin": "string (optional)",
  "destination": "string (optional)",
  "topic": "string (optional)",
  "timespan": "string (optional)",
  "year": "int/string (optional)",
  "years": "string (optional)",
  "population_types": "array (optional)",
  "coo_all": "bool (optional)",
  "coa_all": "bool (optional)",
  "audience": "string (optional)",
  "document_type": "string (optional)",
  "style": "string (optional)",
  "use_enhanced": "bool (optional, default: true)",
  "use_rag": "bool (optional, default: false)",
  "include_notebook": "bool (optional, default: true)",
  "include_html": "bool (optional, default: true)",
  "include_pdf": "bool (optional, default: false)",
  "output_path": "string (optional)"
}
```

**Response**
```json
{
  "status": "success",
  "analysis_id": "uuid",
  "report": {
    "title": "Refugee Trends Analysis: Syria to Turkey (2020-2024)",
    "story": "Comprehensive analysis...",
    "data": {...},
    "metadata": {...}
  },
  "notebook_path": "/quarto/uuid",
  "html_path": "/quarto/uuid.html",
  "pdf_path": null,
  "tools_used": [...],
  "timestamp": "2026-07-07T12:00:00Z"
}
```

**Status Codes**
- `200 OK` - Report generated successfully
- `400 Bad Request` - Invalid parameters

---

### 📜 History & Reports

#### GET `/history`

Get all analysis history.

**Request**
```bash
curl http://localhost:8000/history
```

**Response**
```json
{
  "analyses": [
    {
      "id": "uuid",
      "question": "What are the refugee trends?",
      "timestamp": "2026-07-07T12:00:00Z",
      "tools_used": ["get_population_data", "generate_ai_data_story"],
      "duration_ms": 1500,
      "status": "completed",
      "has_notebook": true,
      "has_visualization": true
    },
    ...
  ],
  "total": 10,
  "page": 1,
  "page_size": 20
}
```

**Status Codes**
- `200 OK` - History retrieved

---

#### GET `/history/{analysis_id}`

Get a specific analysis from history.

**Request**
```bash
curl http://localhost:8000/history/<analysis-id>
```

**Response**
```json
{
  "id": "uuid",
  "question": "What are the refugee trends?",
  "answer": "Comprehensive analysis...",
  "data": {...},
  "visualization": {...},
  "metadata": {
    "timestamp": "2026-07-07T12:00:00Z",
    "tools_used": [...],
    "duration_ms": 1500
  }
}
```

**Status Codes**
- `200 OK` - Analysis retrieved
- `404 Not Found` - Analysis not found

---

#### GET `/quarto/{analysis_id}`

Get Quarto notebook metadata.

**Request**
```bash
curl http://localhost:8000/quarto/<analysis-id>
```

**Response**
```json
{
  "id": "uuid",
  "title": "Analysis Report",
  "format": "quarto",
  "status": "completed",
  "created_at": "2026-07-07T12:00:00Z",
  "paths": {
    "qmd": "/quarto/uuid/report.qmd",
    "rendered": "/quarto/uuid/report.html",
    "pdf": "/quarto/uuid/report.pdf",
    "word": "/quarto/uuid/report.docx"
  }
}
```

---

#### GET `/quarto/{analysis_id}/rendered`

Get rendered HTML of a Quarto notebook.

**Request**
```bash
curl http://localhost:8000/quarto/<analysis-id>/rendered
```

**Response**
```html
<!DOCTYPE html>
<html>
  ... rendered Quarto notebook ...
</html>
```

---

#### GET `/quarto/{analysis_id}/pdf`

Get PDF version of a Quarto notebook.

**Request**
```bash
curl http://localhost:8000/quarto/<analysis-id>/pdf
```

**Response**: PDF file download

---

#### GET `/quarto/{analysis_id}/word`

Get Word document version of a Quarto notebook.

**Request**
```bash
curl http://localhost:8000/quarto/<analysis-id>/word
```

**Response**: Word document download

---

### 🎛️ Utility Endpoints

#### GET `/suggestions`

Get usage suggestions and guidance.

**Request**
```bash
curl http://localhost:8000/suggestions
```

**Response**
```json
{
  "guidance": "Welcome to UNHCR Copilot...",
  "features": [
    "Natural language queries",
    "20+ specialized tools",
    "Interactive visualizations",
    "Reproducible reports"
  ],
  "examples": [
    "What are the latest refugee numbers from Syria?",
    "Show me demographic breakdown for Afghanistan refugees",
    "Compare RSD applications by country"
  ],
  "categories": {
    "Population Data": ["get_population_data", "get_demographics_data"],
    "RSD Data": ["get_rsd_applications", "get_rsd_decisions"],
    "Analysis": ["analyze_data_statistics", "apply_analysis_guardrails"]
  }
}
```

---

#### GET `/guidance`

Get detailed guidance on using the system.

**Request**
```bash
curl http://localhost:8000/guidance
```

---

#### GET `/analysis-config`

Get analysis configuration for different audiences.

**Request**
```bash
curl http://localhost:8000/analysis-config
```

**Response**
```json
{
  "status": "success",
  "config": {
    "audiences": {
      "policy_makers": {
        "document_types": ["executive_summary", "briefing_note", "policy_report"],
        "default": "executive_summary",
        "style": "concise",
        "length": "short"
      },
      "technical_experts": {
        "document_types": ["technical_report", "data_analysis", "methodology_note"],
        "default": "technical_report",
        "style": "detailed",
        "length": "long"
      }
    }
  }
}
```

---

#### GET `/analysis-config/{audience}`

Get configuration for a specific audience.

**Request**
```bash
curl http://localhost:8000/analysis-config/policy_makers
```

---

#### POST `/analysis/rate`

Rate an analysis result.

**Request**
```bash
curl -X POST http://localhost:8000/analysis/rate \
  -H "Content-Type: application/json" \
  -d '{
    "analysis_id": "uuid",
    "rating": 5,
    "feedback": "Very helpful analysis"
  }'
```

**Request Body**
```json
{
  "analysis_id": "string (required)",
  "rating": "int (1-5, required)",
  "feedback": "string (optional)"
}
```

---

### 📄 OpenAPI Schema

The OpenAPI schema is available at `/openapi.json` and provides machine-readable documentation for all endpoints.

**Request**
```bash
curl http://localhost:8000/openapi.json
```

**Schema Includes**
- All REST API endpoints
- Request/response schemas
- Parameter descriptions
- Authentication requirements
- Response examples

---

### 📖 Interactive Documentation

Two interactive documentation interfaces are available:

#### Swagger UI

**URL**: `/docs`

- Interactive API exploration
- Try endpoints directly from the browser
- View request/response examples
- Download OpenAPI schema

#### ReDoc

**URL**: `/redoc`

- Beautiful, responsive documentation
- Organized by tags
- Searchable
- Print-friendly

Both interfaces are auto-generated from the OpenAPI schema and include all endpoints, including MCP documentation endpoints.

---

## 💡 Examples

### Complete Analysis Workflow

```bash
# 1. Get tool list
curl http://localhost:8000/tools

# 2. Execute a tool
curl -X POST http://localhost:8000/tool \
  -d '{"tool": "get_population_data", "arguments": {"coo": "SYR", "year": 2024}}'

# 3. Process chat message
curl -X POST http://localhost:8000/chat \
  -d '{"message": "What are the refugee trends from Syria?"}'

# 4. Generate a report
curl -X POST http://localhost:8000/report \
  -d '{"question": "Analyze refugee trends", "audience": "policy_maker"}'

# 5. Check history
curl http://localhost:8000/history
```

### Using MCP Directly

```bash
# Get MCP server info
curl http://localhost:8000/api/mcp/info

# Get full documentation
curl http://localhost:8000/api/mcp/docs

# Use MCP protocol (Streamable HTTP)
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_population_data", "arguments": {}}'
```

---

## 🎯 Best Practices

1. **Use the `/tools` endpoint** to discover available tools and their parameters
2. **Check `/health`** before making requests to ensure service availability
3. **Handle rate limits** gracefully using the `Retry-After` header
4. **Use POST for modifications** (tool execution, chat, reports)
5. **Use GET for retrieval** (documentation, history, config)
6. **Validate responses** - all endpoints return consistent JSON format
7. **Check status codes** - handle 4xx and 5xx errors appropriately

---

## 📞 Support

For API-related questions:
- Check the interactive documentation at `/docs` or `/redoc`
- Review the MCP documentation at `/api/mcp/docs`
- See the troubleshooting guide in [TROUBLESHOOTING.md](./TROUBLESHOOTING.md)

---

*Last updated: July 7, 2026*
