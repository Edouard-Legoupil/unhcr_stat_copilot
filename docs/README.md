# UNHCR Statistics Copilot Documentation

**UNHCR Statistics Copilot** is an AI-powered analytics platform for UNHCR (United Nations High Commissioner for Refugees) data. It provides comprehensive access to forcibly displaced populations statistics, Refugee Status Determination (RSD) data, demographic information, and analytical tools through a Model Context Protocol (MCP) server.

## 📚 Table of Contents

- [Overview](#overview)
- [Quick Start](#quick-start)
- [Architecture](#architecture)
- [Core Features](#core-features)
- [API Endpoints](#api-endpoints)
- [MCP Server Integration](#mcp-server-integration)
- [Deployment](#deployment)
- [Development](#development)
- [Troubleshooting](#troubleshooting)
- [Contributing](#contributing)
- [License](#license)

---

## 🎯 Overview

The UNHCR Statistics Copilot provides:

- **Real-time data access** to UNHCR's population statistics API
- **20+ specialized tools** for data analysis, visualization, and reporting
- **MCP Server** for integration with AI agents and chat interfaces
- **FastAPI backend** with comprehensive REST API
- **React frontend** for interactive data exploration
- **Quarto notebook generation** for reproducible reports

### Key Capabilities

| Category | Tools | Count |
|----------|-------|-------|
| Data Tools | get_data_for_story, safe_tool_selection | 2 |
| Population Data | get_population_data, get_demographics_data, get_population_trends | 3 |
| RSD Data | get_rsd_applications, get_rsd_decisions | 2 |
| Solutions | get_solutions, get_country_key_figures | 2 |
| Analysis | analyze_data_statistics, apply_analysis_guardrails | 2 |
| Visualization | extract_visualization_structure, generate_visualization | 2 |
| Story Generation | generate_ai_data_story, generate_analytical_story, create_quarto_notebook | 3 |
| Workflows | full_analysis_workflow, quick_analysis, compare_analysis | 3 |
| Utilities | get_usage_guidance, get_suggested_questions, retrieve_report_context | 3 |

---

## 🚀 Quick Start

### Prerequisites

- Python 3.11+
- Node.js 20+
- Docker (for containerized deployment)
- Git

### Local Development Setup

```bash
# Clone the repository
git clone <repository-url>
cd unhcr_stat_copilot

# Backend setup
cd backend
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
pip install -r requirements.txt

# Frontend setup
cd ../frontend
npm install
npm run build

# Run the application
cd ..
# Use boot.sh or start with gunicorn
gunicorn backend.main:app --bind 0.0.0.0:8000 --workers 2
```

### Docker Deployment

```bash
# Build the image
docker build -t unhcr-stat-copilot .

# Run the container
docker run -p 8080:8080 -e PORT=8080 unhcr-stat-copilot
```

### Azure App Service Deployment

```bash
# Deploy using Azure CLI
az webapp up --name <app-name> --resource-group <resource-group> --sku F1

# Or using GitHub Actions
# Configure Azure credentials in GitHub Secrets and push to main branch
```

---

## 🏗️ Architecture

See [ARCHITECTURE.md](./ARCHITECTURE.md) for detailed system architecture.

### High-Level Overview

```
┌─────────────────────────────────────────────────────────────┐
│                      Client Applications                        │
│   (Web Browser, AI Agents, Dashboards, CLI Tools)             │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                      Load Balancer / Gateway                   │
│                    (Azure Front Door, NGINX)                  │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                   FastAPI Application                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │   REST API       │  │ MCP Server Mount  │  │  Static     │ │
│  │   Endpoints      │  │   at /mcp         │  │  Frontend   │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
│  ┌─────────────────┐  ┌─────────────────┐                    │
│  │   /tools         │  │   /api/mcp/docs  │                    │
│  │   /tool          │  │   /api/mcp/info  │                    │
│  │   /chat          │  │   /health        │                    │
│  │   /docs          │  │   /redoc         │                    │
│  └─────────────────┘  └─────────────────┘                    │
└─────────────────────────┬────────────────────────────────────┘
                          │
                          ▼
┌─────────────────────────────────────────────────────────────┐
│                     External Services                           │
│  ┌─────────────────┐  ┌─────────────────┐  ┌─────────────┐ │
│  │  UNHCR API       │  │  Vector Store    │  │  Quartz     │ │
│  │  (Population     │  │  (Local reports)  │  │  (Scheduling)│ │
│  │   Statistics)    │  │                  │  │              │ │
│  └─────────────────┘  └─────────────────┘  └─────────────┘ │
└─────────────────────────────────────────────────────────────┘
```

### Component Details

1. **Backend (`backend/`)**
   - FastAPI application with 20+ API endpoints
   - MCP Server using FastMCP framework
   - Tool orchestration layer
   - Data access layer for UNHCR API
   - Rate limiting and authentication

2. **Frontend (`frontend/`)**
   - React-based single-page application
   - Interactive chat interface
   - Data visualization components
   - Analysis history and management

3. **MCP Server (`backend/mcp/`)**
   - Model Context Protocol implementation
   - 20+ tools for data access and analysis
   - Streamable HTTP transport
   - Tool discovery and execution

---

## ✨ Core Features

### MCP Tools

All MCP tools follow a consistent pattern:

```python
# Tool definition
def my_tool(param1: str, param2: int | None = None) -> dict:
    """
    Description of what the tool does.
    
    Args:
        param1: Description of parameter 1
        param2: Description of parameter 2 (optional)
    
    Returns:
        Dictionary with tool results
    """
    # Tool implementation
    return {"result": "data"}
```

### Key

#### 🎯 Data & Context
- `get_suggested_questions` - Generate suggested analysis questions
- `safe_tool_selection` - Select the right tool for a question
- `get_usage_guidance` - Get guidance on tool usage
- `get_data_for_story` - Get appropriate data for story generation

#### 📊 Population Data
- `get_population_data` - Retrieve forcibly displaced population statistics
- `get_demographics_data` - Get demographic breakdown by age and sex
- `get_population_trends` - Analyze population changes over time
- `get_country_key_figures` - Get key statistics for specific countries

#### ⚖️ Refugee Status Determination (RSD)
- `get_rsd_applications` - Retrieve asylum application statistics
- `get_rsd_decisions` - Get RSD decision outcomes

#### 🎯 Solutions
- `get_solutions` - Retrieve durable solutions data (returns, resettlement, naturalization)

#### 📈 Analysis & Statistics
- `analyze_data_statistics` - Perform statistical analysis on datasets

#### 📊 Visualization
- `extract_visualization_structure` - Extract metadata from visualizations
- `generate_visualization` - Generate AI-powered descriptions for charts

#### 📖 Story Generation
- `generate_analytical_story` - Generate analytical narratives
- `apply_analysis_guardrails` - Apply UNHCR methodology guardrails
- `retrieve_report_context` - Retrieve context from UNHCR reports
- `create_quarto_notebook` - Create reproducible Quarto notebooks (.qmd)

#### 🔄 Workflows
- `full_analysis_workflow` - Complete end-to-end analysis (question → data → story → notebook)
- `quick_analysis` - Fast analysis without notebook generation
- `compare_analysis` - Comparative analysis across multiple scenarios


---

## 🔌 API Endpoints

See [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) for complete API reference.

### Base URL
```
http://localhost:8000  # Development
https://<app-name>.azurewebsites.net  # Azure Production
```

### Authentication
Currently, the API is open and does not require authentication. For production deployments, Azure AD authentication can be enabled.

### Main Endpoints

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET | `/` | API root with service info |
| GET | `/health` | Health check endpoint |
| GET | `/docs` | Swagger UI documentation |
| GET | `/redoc` | ReDoc documentation |
| GET | `/openapi.json` | OpenAPI schema |

### MCP Documentation Endpoints

| Method | Endpoint | Description | Response Format |
|--------|----------|-------------|-----------------|
| GET | `/api/mcp/docs` | Full MCP documentation | JSON or HTML |
| GET | `/api/mcp/info` | Server metadata | JSON or HTML |
| GET | `/tools` | Enhanced tool catalog | JSON or HTML |

### MCP Protocol Endpoint

| Method | Endpoint | Description |
|--------|----------|-------------|
| GET/POST | `/mcp` | MCP Streamable HTTP transport |
| POST | `/mcp/` | MCP tool execution (with trailing slash) |

### Tool Execution

| Method | Endpoint | Description |
|--------|----------|-------------|
| POST | `/tool` | Execute a specific MCP tool |
| POST | `/chat` | Process chat messages |
| POST | `/story` | Generate data stories |
| POST | `/report` | Generate reports |
| GET | `/suggestions` | Get usage suggestions |
| GET | `/guidance` | Get usage guidance |

---

## 🔗 MCP Server Integration

See [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) for detailed integration guide.

### Quick Integration

```python
from backend.mcp.server import create_server

# Create the MCP server
mcp_server = create_server()

# Get the Streamable HTTP app
mcp_app = mcp_server.streamable_http_app()

# The server provides 20+ tools for UNHCR data analysis
# Access via HTTP POST to /mcp with MCP protocol format
```

### Using with MCP Clients

```bash
# Using the MCP Inspector CLI
mcp-inspector --server-url http://localhost:8000/mcp

# Or with curl
curl -X POST http://localhost:8000/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_population_data", "arguments": {}}'
```

### Tool Discovery

The MCP server provides tool discovery through the standard MCP protocol. Clients can:

1. List all available tools
2. Get tool descriptions and parameter schemas
3. Execute tools with arguments
4. Receive structured JSON responses

---

## ☁️ Deployment

See [DEPLOYMENT.md](./DEPLOYMENT.md) for detailed deployment guides.

### Supported Platforms

- ✅ **Docker** - Containerized deployment
- ✅ **Azure App Service** - Fully managed cloud hosting
- ✅ **Azure Container Apps** - Container-based cloud hosting
- ✅ **Local Development** - Direct Python execution
- ✅ **Kubernetes** - Container orchestration

### Environment Variables

| Variable | Description | Default |
|----------|-------------|---------|
| `PORT` | Application port | 8000 |
| `WEBSITES_PORT` | Azure App Service port | - |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true |
| `MCP_SERVER_URL` | MCP server base URL | http://localhost:8000/mcp/ |
| `MCP_TIMEOUT_SECONDS` | MCP request timeout | 30 |
| `MCP_MAX_RETRIES` | Maximum MCP retries | 3 |

---

## 💻 Development

See [DEVELOPMENT.md](./DEVELOPMENT.md) for development setup and workflows.

### Project Structure

```
unhcr_stat_copilot/
├── backend/
│   ├── __init__.py
│   ├── app.py              # FastAPI application
│   ├── main.py             # Application entry point
│   ├── chat.py             # Chat processing
│   ├── charts.py           # Chart generation
│   ├── history.py          # Analysis history
│   ├── auth.py             # Authentication
│   └── mcp/
│       ├── __init__.py
│       ├── server.py       # MCP server implementation
│       ├── common.py       # Common utilities
│       └── tools/          # MCP tool implementations
│           ├── __init__.py
│           ├── get_population_data.py
│           ├── get_demographics_data.py
│           └── ... (20+ tool files)
├── frontend/
│   ├── public/
│   └── src/
│       └── components/     # React components
├── docs/                  # Documentation
├── boot.sh               # Startup script
├── Dockerfile            # Docker configuration
└── README.md
```

### Development Workflow

1. **Create a new MCP tool**
   - Add tool function in `backend/mcp/tools/`
   - Register in `backend/mcp/server.py`
   - Update `MCP_TOOL_SCHEMAS` in `backend/mcp_bridge.py`

2. **Add a new API endpoint**
   - Add route in `backend/app.py`
   - Add request/response models
   - Add to OpenAPI schema

3. **Test the changes**
   ```bash
   # Run tests
   pytest
   
   # Test locally
   python -m backend.main
   
   # Test MCP tools
   curl -X POST http://localhost:8000/mcp -d '{"tool": "tool_name", "arguments": {}}'
   ```

4. **Deploy**
   - Commit changes
   - Push to main branch
   - Azure deployment triggers automatically

---

## 🐛 Troubleshooting

See [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) for common issues and solutions.

### Common Issues

| Issue | Solution |
|-------|----------|
| 405 Method Not Allowed on `/mcp` | Ensure health check endpoints are defined (fixed in latest commit) |
| 503 MCP server unavailable | Check that `mcp_server.session_manager.run()` is in lifespan |
| OpenAPI schema errors | Fix ellipsis (`...`) in response examples |
| Mount conflicts | Use `/api/mcp/` for documentation, `/mcp` for MCP protocol |

### Debug Mode

```bash
# Run with debug logging
python -m backend.main --log-level debug

# Or set environment variable
export LOG_LEVEL=DEBUG
python -m backend.main
```

### Health Checks

```bash
# Check main API
curl http://localhost:8000/health

# Check MCP server
curl http://localhost:8000/mcp

# Check documentation endpoints
curl http://localhost:8000/api/mcp/docs
curl http://localhost:8000/api/mcp/info
```

---

## 🤝 Contributing

Contributions are welcome! Please follow these guidelines:

1. **Fork the repository** and create a feature branch
2. **Follow the existing code style** and conventions
3. **Add tests** for new functionality
4. **Update documentation** for new features
5. **Submit a pull request** with a clear description

### Code Style

- Python: PEP 8 with 4-space indentation
- Type hints: Required for all functions
- Docstrings: Required for all public functions
- Imports: Grouped by standard library, third-party, local

### Testing

```bash
# Run all tests
pytest

# Run with coverage
pytest --cov=backend --cov=frontend

# Run specific test file
pytest tests/test_mcp.py
```

---

## 📄 License

This project is licensed under the MIT License. See [LICENSE](../LICENSE) for details.

---

## 📞 Support

For issues, questions, or feedback:

- **GitHub Issues**: Report bugs and feature requests
- **Documentation**: Check the docs directory for comprehensive guides
- **MCP Protocol**: See https://modelcontextprotocol.io for protocol specification

---

*Last updated: July 7, 2026*
