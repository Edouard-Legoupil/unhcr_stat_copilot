# System Architecture

This document provides a comprehensive overview of the UNHCR Statistics Copilot system architecture, including component diagrams, data flow, and technical details.

## 📚 Table of Contents

- [System Overview](#system-overview)
- [High-Level Architecture](#high-level-architecture)
- [Component Architecture](#component-architecture)
  - [Backend Architecture](#backend-architecture)
  - [Frontend Architecture](#frontend-architecture)
  - [MCP Server Architecture](#mcp-server-architecture)
- [Data Flow](#data-flow)
- [Technology Stack](#technology-stack)
- [Module Descriptions](#module-descriptions)
- [Request Lifecycle](#request-lifecycle)

---

## 🎯 System Overview

The UNHCR Statistics Copilot is a multi-layered application that provides AI-powered analytics for UNHCR data through both REST API and MCP (Model Context Protocol) interfaces.

### Key Principles

1. **Separation of Concerns**: Clear division between data access, business logic, and presentation layers
2. **Modular Design**: Components are independent and can be developed/tested in isolation
3. **API-First**: All functionality is exposed through well-documented APIs
4. **Extensibility**: New tools and endpoints can be added without modifying core components
5. **Resilience**: Built-in retry logic, error handling, and rate limiting

---

## 🏗️ High-Level Architecture

```
┌─────────────────────────────────────────────────────────────────────────┐
│                              CLIENT LAYER                                     │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐    │
│  │  Web Browser │  │ AI Agents    │  │ Dashboards  │  │  CLI Tools  │    │
│  │  (React SPA) │  │ (MCP Client) │  │ (Metabase)  │  │ (curl, etc) │    │
│  └─────────────┘  └─────────────┘  └─────────────┘  └─────────────┘    │
└──────────────────────────┬──────────────────────────────────────────────┘
                         │ HTTP/HTTPS
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           GATEWAY LAYER (Optional)                           │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │ Azure Front Door │  │    NGINX        │  │  Load Balancer  │          │
│  │   (CDN, WAF)     │  │ (Reverse Proxy) │  │ (Traffic Dist.) │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
└──────────────────────────┬──────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                           APPLICATION LAYER                                  │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌─────────────────────────────────────────────────────────────────────┐ │
│  │                        FastAPI Application                             │ │
│  │  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │ │
│  │  │    REST API      │  │   MCP Server     │  │   Static Files   │    │ │
│  │  │   (20+ routes)   │  │   (Mounted)      │  │   (Frontend)     │    │ │
│  │  └─────────────────┘  └─────────────────┘  └─────────────────┘    │ │
│  │                                                                      │ │
│  │  ┌───────────────────────────────────────────────────────────────┐ │ │
│  │  │                        Middleware                               │ │ │
│  │  │  ┌──────────┐ ┌──────────┐ ┌──────────┐ ┌──────────┐        │ │ │
│  │  │  │  CORS     │ │ Rate Lim │ │ Auth     │ │ Logging  │        │ │ │
│  │  │  │ Middleware│ │ iter     │ │ Middleware│ │          │        │ │ │
│  │  │  └──────────┘ └──────────┘ └──────────┘ └──────────┘        │ │ │
│  │  └───────────────────────────────────────────────────────────────┘ │ │
│  └─────────────────────────────────────────────────────────────────────┘ │
│                                                                             │
└──────────────────────────┬──────────────────────────────────────────────┘
                         │
                         ▼
┌─────────────────────────────────────────────────────────────────────────┐
│                            DATA LAYER                                       │
├─────────────────────────────────────────────────────────────────────────┤
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐          │
│  │  UNHCR API       │  │  Vector Store    │  │   Local Cache   │          │
│  │  (External)      │  │  (Optional)      │  │   (In-Memory)   │          │
│  │                 │  │                 │  │                 │          │
│  │  - Population    │  │  - Reports       │  │  - Session data │          │
│  │  - RSD           │  │  - Context       │  │  - Analysis     │          │
│  │  - Demographics  │  │  - Embeddings    │  │    history     │          │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘          │
└─────────────────────────────────────────────────────────────────────────┘
```

---

## 🏛️ Component Architecture

### Backend Architecture

```
backend/
├── app.py                  # FastAPI application and main routes
├── main.py                 # Application entry point (uvicorn/gunicorn)
├── chat.py                 # Chat message processing logic
├── charts.py               # Chart and visualization generation
├── history.py              # Analysis history storage and retrieval
├── auth.py                 # Authentication and authorization
├── boot.sh                 # Startup script with health checks
├── requirements.txt        # Python dependencies
└── mcp/                    # MCP Server implementation
    ├── __init__.py
    ├── server.py           # FastMCP server initialization
    ├── common.py           # Common utilities and shared code
    └── tools/              # MCP tool implementations
        ├── __init__.py
        ├── get_population_data.py
        ├── get_demographics_data.py
        ├── get_rsd_applications.py
        ├── get_rsd_decisions.py
        ├── get_solutions.py
        ├── get_country_key_figures.py
        ├── get_population_trends.py
        ├── get_demographic_breakdown.py
        ├── retrieve_report_context.py
        ├── extract_visualization_structure.py
        ├── analyze_data_statistics.py
        ├── generate_visualization.py
        ├── generate_ai_data_story.py
        ├── get_usage_guidance.py
        ├── get_suggested_questions.py
        ├── apply_analysis_guardrails.py
        ├── create_quarto_notebook.py
        ├── safe_tool_selection.py
        ├── get_data_for_story.py
        ├── analysis_pipeline.py
        └── workflows.py
```

#### App.py Structure

```
┌─────────────────────────────────────────────────────────────┐
│                        app.py                                  │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  1. IMPORTS                                                     │
│     - FastAPI, dependencies                                     │
│     - Local modules (mcp.server, chat, charts, etc.)            │
│                                                                  │
│  2. APPLICATION SETUP                                          │
│     - Create FastAPI app                                        │
│     - Configure CORS                                            │
│     - Add middleware                                            │
│                                                                  │
│  3. MCP SERVER INITIALIZATION                                  │
│     - create_server()                                          │
│     - streamable_http_app()                                    │
│     - Mount at /mcp                                            │
│                                                                  │
│  4. LIFESPAN MANAGEMENT                                         │
│     - mcp_server.session_manager.run()                        │
│                                                                  │
│  5. DOCUMENTATION ENDPOINTS                                   │
│     - GET /api/mcp/docs                                        │
│     - GET /api/mcp/info                                        │
│     - GET /tools (enhanced)                                    │
│                                                                  │
│  6. MCP TOOL EXECUTION                                         │
│     - POST /tool                                               │
│     - POST /chat                                               │
│                                                                  │
│  7. ANALYSIS ENDPOINTS                                         │
│     - POST /story                                              │
│     - POST /report                                             │
│     - GET /history                                            │
│     - GET /history/{id}                                       │
│                                                                  │
│  8. VISUALIZATION ENDPOINTS                                   │
│     - GET /quarto/{id}                                         │
│     - GET /quarto/{id}/rendered                               │
│     - GET /quarto/{id}/pdf                                     │
│     - GET /quarto/{id}/word                                    │
│                                                                  │
│  9. UTILITY ENDPOINTS                                          │
│     - GET /health                                              │
│     - GET /suggestions                                          │
│     - GET /guidance                                            │
│     - GET /analysis-config                                     │
│     - POST /analysis/rate                                     │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

### Frontend Architecture

```
frontend/
├── public/                  # Static assets (images, favicon, etc.)
│   └── index.html           # Main HTML entry point
└── src/
    ├── index.jsx            # React application entry point
    ├── App.jsx              # Main React component
    ├── components/
    │   ├── ChatInterface.jsx     # Chat UI component
    │   ├── AnalysisViewer.jsx   # Analysis results display
    │   ├── IntegratedAnalysisViewer.jsx  # Full analysis view
    │   ├── AboutSection.jsx     # About section
    │   ├── Header.jsx           # Application header
    │   └── ...
    ├── hooks/              # Custom React hooks
    ├── services/           # API service layer
    ├── styles/             # CSS and styling
    │   └── unhcr.css        # UNHCR-specific styles
    └── utils/              # Utility functions
```

### MCP Server Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                    MCP Server Architecture                       │
├─────────────────────────────────────────────────────────────┤
│                                                                  │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    FastMCP (Smithery)                       │ │
│  │  - Server name: UNHCR Forcibly Displaced Populations        │ │
│  │  - Transport: Streamable HTTP                              │ │
│  │  - Mount path: /mcp                                        │ │
│  │  - Session: Async task group                              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                    Tool Manager                             │ │
│  │  - Tool registration                                       │ │
│  │  - Tool discovery                                          │ │
│  │  - Tool execution                                          │ │
│  └─────────────────────────────────────────────────────────┘ │
│                              │                                   │
│              ┌───────────────┼───────────────┐                  │
│              ▼               ▼               ▼                  │
│  ┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐   │
│  │  Tool Category  │ │  Tool Category  │ │  Tool Category  │   │
│  │   Population    │ │    Analysis     │ │   Workflows     │   │
│  │   (4 tools)     │ │   (7 tools)     │ │   (3 tools)     │   │
│  └─────────────────┘ └─────────────────┘ └─────────────────┘   │
│                              │                                   │
│                              ▼                                   │
│  ┌─────────────────────────────────────────────────────────┐ │
│  │                 Data Access Layer                          │ │
│  │  - UNHCR API Client (population, RSD, solutions)         │ │
│  │  - Vector Store (local reports, RAG)                      │ │
│  │  - Common utilities (validation, formatting)              │ │
│  └─────────────────────────────────────────────────────────┘ │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
```

---

## 🔄 Data Flow

### REST API Data Flow

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐    ┌──────────────┐
│ Client  │───▶│  FastAPI     │───▶│  Route       │───▶│  Service     │
│ Request │    │  Router      │    │  Handler     │    │  Layer       │
└─────────┘    └──────────────┘    └──────────────┘    └──────────────┘
                                                                  │
                                                                  ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Business Logic Layer                      │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  Chat Process   │  │   Tool Orch.    │  │  Analysis Gen.   │    │
│  │    (chat.py)     │  │ (mcp_bridge.py) │  │    (chat.py)     │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────────┐
│                           Data Access Layer                         │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────────┐    │
│  │  UNHCR API      │  │  Vector Store    │  │   Local Cache   │    │
│  │   Client         │  │   (RAG)          │  │    (History)    │    │
│  └─────────────────┘  └─────────────────┘  └─────────────────┘    │
└─────────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────┐
│  Response    │
│  (JSON/HTML) │
└─────────────┘
```

### MCP Protocol Data Flow

```
┌─────────┐    ┌──────────────┐    ┌──────────────┐
│ MCP     │───▶│  POST /mcp   │───▶│  Streamable  │
│ Client  │    │  (JSON-RPC)  │    │  HTTP Manager│
└─────────┘    └──────────────┘    └──────────────┘
                                          │
                                          ▼
┌─────────────────────────────────────────────────────────────┐
│                       MCP Request Processing                     │
│  1. Parse JSON-RPC request                                        │
│  2. Validate tool name and arguments                              │
│  3. Look up tool in registry                                     │
│  4. Execute tool function                                         │
│  5. Format response as JSON-RPC                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────────────────────────────────────────────────────┐
│                     Tool Execution Flow                          │
│                                                                  │
│  ┌─────────────┐    ┌─────────────┐    ┌─────────────┐        │
│  │  Validate   │───▶│   Call      │───▶│  Process    │        │
│  │  Arguments  │    │   Tool      │    │  Result     │        │
│  └─────────────┘    └─────────────┘    └─────────────┘        │
│                                                                  │
└─────────────────────────────────────────────────────────────┘
                              │
                              ▼
┌─────────────┐
│  JSON-RPC    │
│  Response    │
└─────────────┘
```

---

## 🛠️ Technology Stack

### Backend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| Python | Primary language | 3.11+ |
| FastAPI | Web framework | Latest |
| Uvicorn | ASGI server | Latest |
| Gunicorn | WSGI server | Latest |
| Pydantic | Data validation | v2 |
| FastMCP | MCP server framework | Latest |
| MCP SDK | Model Context Protocol | Latest |
| requests | HTTP client | Latest |
| aiohttp | Async HTTP client | Latest |
| slowapi | Rate limiting | Latest |

### Frontend Technologies

| Technology | Purpose | Version |
|------------|---------|---------|
| React | UI framework | 18+ |
| TypeScript | Type safety | Latest |
| Vite | Build tool | Latest |
| Tailwind CSS | Styling | Latest |

### Data & Storage

| Technology | Purpose | Version |
|------------|---------|---------|
| UNHCR API | Primary data source | External |
| DuckDB | Local vector store | Latest |
| SQLite | Local storage | Latest |

### DevOps & Infrastructure

| Technology | Purpose | Version |
|------------|---------|---------|
| Docker | Containerization | Latest |
| GitHub Actions | CI/CD | Latest |
| Azure App Service | Cloud hosting | Latest |
| Azure Container Apps | Container hosting | Latest |

---

## 📦 Module Descriptions

### Backend Modules

#### `app.py` - Main FastAPI Application

- **Purpose**: Core application with all API endpoints
- **Key Components**:
  - FastAPI app initialization
  - CORS middleware configuration
  - MCP server creation and mounting
  - Lifespan management
  - 20+ API endpoints
- **Dependencies**: `server.py`, `mcp_bridge.py`, `chat.py`, `charts.py`

#### `main.py` - Application Entry Point

- **Purpose**: Entry point for running the application
- **Key Components**:
  - Uvicorn server configuration
  - Static file serving
  - Application mounting

#### `chat.py` - Chat Processing

- **Purpose**: Process chat messages and generate responses
- **Key Components**:
  - Message parsing
  - Tool selection
  - Response formatting
  - Analysis generation

#### `mcp_bridge.py` - MCP Tool Bridge

- **Purpose**: Bridge between FastAPI and MCP server
- **Key Components**:
  - Tool schemas (MCP_TOOL_SCHEMAS)
  - Tool validation
  - Tool execution with retry logic
  - Error handling

#### `mcp/server.py` - MCP Server Implementation

- **Purpose**: FastMCP server with all tools registered
- **Key Components**:
  - Server creation with FastMCP
  - Tool registration (20+ tools)
  - Server metadata
  - Streamable HTTP transport

#### `mcp/common.py` - Common Utilities

- **Purpose**: Shared utilities for MCP tools
- **Key Components**:
  - UNHCR API client
  - Vector store retrieval
  - Data formatting
  - Configuration

### Frontend Modules

#### `ChatInterface.jsx` - Chat UI Component

- **Purpose**: Interactive chat interface for users
- **Key Features**:
  - Message input and display
  - Analysis result rendering
  - History navigation
  - Loading states

#### `IntegratedAnalysisViewer.jsx` - Analysis Viewer

- **Purpose**: Display comprehensive analysis results
- **Key Features**:
  - Story rendering
  - Visualization display
  - Data table rendering
  - Export options

---

## 🔄 Request Lifecycle

### FastAPI Request Lifecycle

```
1. Request received by Uvicorn/Gunicorn
   ↓
2. CORS middleware checks origin
   ↓
3. Rate limiting middleware checks limits
   ↓
4. FastAPI router matches route
   ↓
5. Route handler executes
   │
   ├── If MCP-related:
   │    ├── Forwards to mounted MCP app
   │    └── MCP server processes request
   │
   ├── If API endpoint:
   │    ├── Validates request
   │    ├── Executes business logic
   │    └── Returns JSON response
   │
   └── If static file:
        └── Serves from frontend/dist
   ↓
6. Response formatted (JSON or HTML)
   ↓
7. Response sent to client
```

### MCP Request Lifecycle

```
1. MCP client sends JSON-RPC request to /mcp
   ↓
2. FastAPI router matches /mcp mount
   ↓
3. Request forwarded to mcp_app (Streamable HTTP app)
   ↓
4. StreamableHTTPManager.handle_request() called
   ↓
5. Session verification (checks _task_group)
   │
   ├── If not initialized:
   │    └── Returns 500 "Task group is not initialized"
   │
   └── If initialized:
        ↓
6. Request parsing (JSON-RPC format)
   ↓
7. Tool lookup in registry
   ↓
8. Argument validation
   ↓
9. Tool execution
   ↓
10. Response formatting (JSON-RPC)
   ↓
11. Response sent to client
```

---

## 📊 Performance Considerations

### Caching

- **Rate Limiting**: 10 requests/minute per IP (configurable)
- **MCP Tool Caching**: Results not cached (real-time data)
- **Vector Store**: Local DuckDB with in-memory caching

### Concurrency

- **Gunicorn Workers**: 2-4 workers recommended for Azure
- **Async Support**: Full async/await for I/O operations
- **Task Groups**: AnyIO task groups for concurrent operations

### Resource Limits

- **Memory**: Optimized for Azure App Service (1-2GB recommended)
- **CPU**: Lightweight operations, suitable for serverless
- **Timeouts**: 300 seconds default for MCP requests

---

## 🔒 Security Considerations

### Authentication

- **Current**: Open access (no authentication)
- **Recommended**: Azure AD integration for production
- **CORS**: Configured to allow all origins (adjust for production)

### Data Protection

- **HTTPS**: Enforced in production (Azure handles SSL)
- **Input Validation**: Pydantic models for all requests
- **Rate Limiting**: Protection against abuse

### MCP Security

- **Origin Validation**: Allowed hosts configured
- **Transport Security**: HTTPS required in production
- **Session Management**: Task groups for isolation

---

## 📈 Scalability

### Horizontal Scaling

- **Stateless Design**: All endpoints are stateless
- **Session Storage**: In-memory (consider Redis for multi-instance)
- **Database**: External UNHCR API (no local DB required)

### Vertical Scaling

- **Worker Count**: Adjust Gunicorn workers based on CPU cores
- **Memory**: Scale up for larger datasets
- **Timeout**: Increase for complex analysis

### Recommendations

| Scenario | Workers | Memory | Notes |
|----------|---------|--------|-------|
| Development | 1 | 512MB | Local testing |
| Production (Small) | 2 | 1GB | Azure F1/B1 |
| Production (Medium) | 4 | 2GB | Azure P1v2 |
| Production (Large) | 8 | 4GB | High traffic |

---

*Last updated: July 7, 2026*
