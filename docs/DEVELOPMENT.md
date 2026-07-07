# Development Guide

Complete development setup and workflow documentation for the UNHCR Statistics Copilot.

## 📚 Table of Contents

- [Getting Started](#getting-started)
- [Prerequisites](#prerequisites)
- [Project Structure](#project-structure)
- [Setup Instructions](#setup-instructions)
  - [Backend Setup](#backend-setup)
  - [Frontend Setup](#frontend-setup)
  - [Docker Setup](#docker-setup)
- [Development Workflow](#development-workflow)
- [Code Organization](#code-organization)
  - [Backend Structure](#backend-structure)
  - [Frontend Structure](#frontend-structure)
  - [MCP Server Structure](#mcp-server-structure)
- [Adding New Features](#adding-new-features)
  - [Adding a New MCP Tool](#adding-a-new-mcp-tool)
  - [Adding a New API Endpoint](#adding-a-new-api-endpoint)
  - [Adding a New Frontend Component](#adding-a-new-frontend-component)
- [Testing](#testing)
  - [Backend Testing](#backend-testing)
  - [Frontend Testing](#frontend-testing)
  - [Integration Testing](#integration-testing)
- [Debugging](#debugging)
  - [Backend Debugging](#backend-debugging)
  - [Frontend Debugging](#frontend-debugging)
  - [MCP Server Debugging](#mcp-server-debugging)
- [Code Quality](#code-quality)
  - [Code Style Guidelines](#code-style-guidelines)
  - [Type Hints](#type-hints)
  - [Docstrings](#docstrings)
  - [Error Handling](#error-handling)
- [Git Workflow](#git-workflow)
- [Pull Request Process](#pull-request-process)
- [Local Development Tips](#local-development-tips)
- [Hot Reload](#hot-reload)
- [Environment Configuration](#environment-configuration)
- [IDE Setup](#ide-setup)
  - [VS Code](#vs-code)
  - [PyCharm](#pycharm)
  - [Other Editors](#other-editors)
- [Performance Tips](#performance-tips)
- [Common Development Tasks](#common-development-tasks)

---

## 🚀 Getting Started

Welcome to the UNHCR Statistics Copilot development guide! This document will help you set up your development environment and start contributing to the project.

---

## 📋 Prerequisites

Before you begin, ensure you have the following installed:

### Required Software

| Software | Version | Purpose | Download |
|----------|---------|---------|----------|
| Python | 3.11+ | Backend development | [python.org](https://www.python.org) |
| Node.js | 20+ | Frontend development | [nodejs.org](https://nodejs.org) |
| Git | 2.x+ | Version control | [git-scm.com](https://git-scm.com) |
| Docker | 20.x+ | Containerization | [docker.com](https://www.docker.com) |

### Optional Software

| Software | Purpose |
|----------|---------|
| VS Code | Code editor (recommended) |
| PyCharm | Python IDE |
| Postman | API testing |
| Insomnia | API testing |
| pgAdmin / DBeaver | Database tools |

### Python Packages

```bash
# Check Python version
python --version
# Expected: Python 3.11.x or higher

# Check pip version
pip --version
```

### Node.js Packages

```bash
# Check Node.js version
node --version
# Expected: v20.x.x or higher

# Check npm version
npm --version
# Expected: 10.x.x or higher
```

---

## 📂 Project Structure

```
unhcr_stat_copilot/
├── backend/                          # Backend (FastAPI + MCP Server)
│   ├── __init__.py
│   ├── app.py                      # Main FastAPI application
│   ├── main.py                     # Application entry point
│   ├── boot.sh                     # Startup script
│   ├── auth.py                     # Authentication and authorization
│   ├── chat.py                     # Chat message processing
│   ├── charts.py                   # Chart and visualization generation
│   ├── history.py                  # Analysis history management
│   ├── requirements.txt            # Python dependencies
│   └── mcp/                        # MCP Server implementation
│       ├── __init__.py
│       ├── server.py               # FastMCP server setup
│       ├── common.py               # Common utilities
│       ├── observability.py         # Monitoring and metrics
│       ├── mcp_bridge.py            # Bridge between FastAPI and MCP
│       └── tools/                  # MCP tool implementations
│           ├── __init__.py
│           ├── get_population_data.py
│           ├── get_demographics_data.py
│           ├── get_rsd_applications.py
│           ├── get_rsd_decisions.py
│           ├── get_solutions.py
│           ├── get_country_key_figures.py
│           ├── get_population_trends.py
│           ├── get_demographic_breakdown.py
│           ├── retrieve_report_context.py
│           ├── extract_visualization_structure.py
│           ├── analyze_data_statistics.py
│           ├── generate_visualization_description.py
│           ├── generate_ai_data_story.py
│           ├── generate_analytical_story.py
│           ├── create_quarto_notebook.py
│           ├── get_usage_guidance.py
│           ├── get_suggested_questions.py
│           ├── apply_analysis_guardrails.py
│           ├── safe_tool_selection.py
│           ├── get_data_for_story.py
│           ├── analysis_pipeline.py
│           └── workflows.py
├── frontend/                         # Frontend (React + TypeScript)
│   ├── public/
│   │   └── index.html               # Main HTML entry point
│   ├── src/
│   │   ├── index.jsx                # React application entry
│   │   ├── App.jsx                  # Main React component
│   │   ├── components/              # React components
│   │   │   ├── ChatInterface.jsx
│   │   │   ├── AnalysisViewer.jsx
│   │   │   ├── IntegratedAnalysisViewer.jsx
│   │   │   ├── AboutSection.jsx
│   │   │   ├── Header.jsx
│   │   │   └── ...
│   │   ├── hooks/                   # Custom React hooks
│   │   ├── services/                # API service layer
│   │   ├── styles/                  # CSS and styling
│   │   │   └── unhcr.css
│   │   └── utils/                   # Utility functions
│   ├── package.json
│   ├── vite.config.js
│   └── ...
├── docs/                           # Documentation
│   ├── README.md
│   ├── ARCHITECTURE.md
│   ├── API_DOCUMENTATION.md
│   ├── MCP_INTEGRATION.md
│   ├── DEPLOYMENT.md
│   └── DEVELOPMENT.md
├── boot.sh                        # Universal startup script
├── Dockerfile                    # Docker configuration
├── .env.example                  # Environment variables template
├── .gitignore
├── README.md
└── LICENSE
```

---

## 🔧 Setup Instructions

### Backend Setup

#### Step 1: Clone the Repository

```bash
# Clone the repository
git clone <repository-url>
cd unhcr_stat_copilot

# Check out the desired branch
git checkout main
```

#### Step 2: Create Python Virtual Environment

```bash
# Create virtual environment
python -m venv venv

# Activate on macOS/Linux
source venv/bin/activate

# Activate on Windows
# venv\Scripts\activate

# Verify activation (should show venv path)
which python
# or: where python (Windows)
```

#### Step 3: Install Python Dependencies

```bash
# Navigate to backend directory
cd backend

# Install requirements
pip install -r requirements.txt

# Navigate back to project root
cd ..
```

The `requirements.txt` includes all necessary packages:
- fastapi
- uvicorn
- gunicorn
- fastmcp
- mcp
- requests
- aiohttp
- slowapi
- python-dotenv
- pydantic
- ... and more

#### Step 4: Verify Backend Installation

```bash
# Test FastAPI import
python -c "import fastapi; print('FastAPI:', fastapi.__version__)"

# Test MCP import
python -c "import fastmcp; print('FastMCP:', fastmcp.__version__)"

# Test application import
python -c "from backend.app import app; print('Backend app imported successfully')"
```

### Frontend Setup

#### Step 1: Install Node.js Dependencies

```bash
# Navigate to frontend directory
cd frontend

# Install npm packages
npm install

# Navigate back to project root
cd ..
```

The `package.json` includes:
- react
- react-dom
- typescript
- vite
- @vitejs/plugin-react
- tailwindcss
- ... and more

#### Step 2: Build Frontend

```bash
# Navigate to frontend directory
cd frontend

# Build for development
npm run build

# Or build for production
npm run build --mode production

# Navigate back to project root
cd ..
```

#### Step 3: Verify Frontend Build

```bash
# Check if dist directory exists
ls -la frontend/dist/

# Check index.html
cat frontend/dist/index.html | head -20
```

### Docker Setup

#### Build Docker Image

```bash
# Build the image
docker build -t unhcr-stat-copilot .

# Check images
docker images | grep unhcr-stat-copilot
```

#### Run Container for Development

```bash
# Run with auto-reload (for development)
docker run -p 8080:8080 \
  -v $(pwd)/backend:/app/backend \
  -v $(pwd)/frontend:/app/frontend \
  -e PORT=8080 \
  -e LOG_LEVEL=debug \
  --entrypoint "/bin/sh" \
  -it unhcr-stat-copilot \
  -c "pip install -r backend/requirements.txt && cd frontend && npm install && npm run build && python -m backend.main --reload"
```

---

## 🔄 Development Workflow

### Starting the Application

#### Method 1: Using boot.sh (Recommended)

```bash
# Make boot.sh executable
chmod +x boot.sh

# Run with default settings (port 8080)
./boot.sh

# Run with custom port
PORT=9000 ./boot.sh

# Run with debug logging
LOG_LEVEL=debug ./boot.sh
```

The `boot.sh` script:
- Detects Azure or local environment
- Configures port automatically
- Starts SSH server (for Azure tunnel)
- Validates application imports
- Launches Gunicorn with Uvicorn workers
- Shows all available endpoints

#### Method 2: Direct Python Execution

```bash
# Using uvicorn (development mode with auto-reload)
python -m backend.main

# With custom host and port
python -m backend.main --host 0.0.0.0 --port 9000

# Without auto-reload (production mode)
python -m backend.main --reload false
```

#### Method 3: Using Gunicorn

```bash
# For production (no auto-reload)
gunicorn backend.main:app \
  --bind 0.0.0.0:8080 \
  --workers 2 \
  --worker-class uvicorn.workers.UvicornWorker

# For development (single worker with auto-reload)
gunicorn backend.main:app \
  --bind 0.0.0.0:8080 \
  --workers 1 \
  --reload \
  --worker-class uvicorn.workers.UvicornWorker
```

### Verifying the Application

After starting the application, verify it's working:

```bash
# Check health
curl http://localhost:8080/health

# Check root endpoint
curl http://localhost:8080/

# Check MCP server
curl http://localhost:8080/mcp

# Check tool list
curl http://localhost:8080/tools

# Check MCP documentation
curl http://localhost:8080/api/mcp/docs

# Access Swagger UI (open in browser)
# http://localhost:8080/docs

# Access ReDoc (open in browser)
# http://localhost:8080/redoc
```

### Stopping the Application

```bash
# If using Ctrl+C in terminal
# Press Ctrl+C to stop

# If running in background
pkill -f "gunicorn backend.main:app"
# or
pkill -f "python -m backend.main"

# Check running processes
ps aux | grep -E "(gunicorn|uvicorn|python.*backend)"
```

---

## 🏗️ Code Organization

### Backend Structure

```
backend/
├── app.py              # Main FastAPI application with all endpoints
├── main.py             # Application entry point (uvicorn/gunicorn)
├── auth.py             # Authentication and authorization
├── chat.py             # Chat message processing logic
├── charts.py           # Chart and visualization generation
├── history.py          # Analysis history storage and retrieval
├── mcp_bridge.py       # Bridge between FastAPI and MCP server
└── mcp/                # MCP Server implementation
    ├── server.py       # FastMCP server initialization
    ├── common.py       # Common utilities and shared code
    ├── observability.py # Monitoring, metrics, and logging
    └── tools/          # MCP tool implementations
        ├── __init__.py
        ├── get_population_data.py
        ├── get_demographics_data.py
        └── ... (20+ tool files)
```

#### app.py Overview

The `app.py` file contains:
- FastAPI application initialization
- CORS middleware configuration
- Rate limiting setup
- MCP server creation and mounting
- All API endpoints (health, MCP docs, tools, chat, history, etc.)
- Lifespan management for MCP server

#### MCP Server Structure

```
backend/mcp/
├── server.py           # Main MCP server setup
│   ├── create_server() # Creates FastMCP server with all tools
│   └── Tool registration (20+ tools)
├── common.py           # Shared utilities
│   ├── UNHCR API client
│   ├── Vector store retrieval
│   ├── Data formatting
│   └── Configuration
└── tools/              # Individual tool implementations
    ├── __init__.py      # Tool exports
    ├── get_population_data.py
    ├── get_demographics_data.py
    └── ...
```

Each tool follows the same pattern:

```python
"""
Tool description and metadata.
"""

from typing import Optional
from backend.mcp.common import unwrap_function

@unwrap_function
async def get_population_data(
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[int | str] = None,
    coo_all: bool = False,
    coa_all: bool = False
) -> dict:
    """
    Retrieve forcibly displaced population statistics from UNHCR.
    
    Args:
        coo: Country of origin (ISO 3-letter code)
        coa: Country of asylum (ISO 3-letter code)
        year: Year of data
        coo_all: Get all countries of origin
        coa_all: Get all countries of asylum
    
    Returns:
        Dictionary with population data
    """
    # Tool implementation
    from backend.mcp.common import call_unhcr_api
    return await call_unhcr_api("population", **locals())
```

### Frontend Structure

```
frontend/
├── public/
│   └── index.html       # Main HTML entry point
└── src/
    ├── index.jsx        # React application entry
    ├── App.jsx          # Main React component
    ├── components/
    │   ├── ChatInterface.jsx     # Chat UI component
    │   ├── AnalysisViewer.jsx   # Analysis results display
    │   ├── IntegratedAnalysisViewer.jsx  # Full analysis view
    │   ├── AboutSection.jsx     # About section
    │   ├── Header.jsx           # Application header
    │   └── ...
    ├── hooks/           # Custom React hooks
    │   ├── useChat.js    # Chat functionality hook
    │   └── ...
    ├── services/       # API service layer
    │   ├── api.js       # API client
    │   └── ...
    ├── styles/         # CSS and styling
    │   └── unhcr.css    # UNHCR-specific styles
    └── utils/          # Utility functions
        └── helpers.js
```

---

## ✨ Adding New Features

### Adding a New MCP Tool

#### Step 1: Create the Tool File

```bash
# Navigate to tools directory
cd backend/mcp/tools

# Create new tool file
touch new_tool_name.py
```

#### Step 2: Implement the Tool

```python
# backend/mcp/tools/new_tool_name.py
"""
New Tool: new_tool_name

Description: Brief description of what this tool does.
"""

from typing import Optional
from backend.mcp.common import unwrap_function

@unwrap_function
async def new_tool_name(
    param1: str,
    param2: Optional[int] = None,
    param3: bool = False
) -> dict:
    """
    Detailed description of the tool's purpose and functionality.
    
    Args:
        param1: Description of parameter 1 (required)
        param2: Description of parameter 2 (optional)
        param3: Description of parameter 3 (optional, default: False)
    
    Returns:
        dict: Description of the return value structure
        
    Example:
        >>> await new_tool_name("value1", param2=100)
        {"result": "...", "data": [...]}
    """
    # Tool implementation
    # Add your logic here
    result = {
        "param1": param1,
        "param2": param2,
        "param3": param3,
        "result": "success"
    }
    return result
```

#### Step 3: Register the Tool

Edit `backend/mcp/server.py`:

```python
# Add import at the top
from backend.mcp.tools.new_tool_name import new_tool_name

# Add tool to server creation
def create_server():
    server = FastMCPServer(
        name="UNHCR Forcibly Displaced Populations",
        instructions="Provides UNHCR population data tools and data-story generation...",
    )
    
    # Add new tool
    server.add_tool(new_tool_name)
    
    # ... other tools
    
    return server
```

#### Step 4: Add to MCP_TOOL_SCHEMAS

Edit `backend/mcp_bridge.py`:

```python
MCP_TOOL_SCHEMAS = {
    # ... existing tools
    "new_tool_name": {
        "required": ["param1"],
        "optional": ["param2", "param3"],
        "types": {
            "param1": str,
            "param2": int,
            "param3": bool
        }
    }
}
```

#### Step 5: Test the New Tool

```bash
# Test via API
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "new_tool_name", "arguments": {"param1": "test_value"}}'

# Test via MCP protocol
curl -X POST http://localhost:8080/tool \
  -H "Content-Type: application/json" \
  -d '{"tool": "new_tool_name", "arguments": {"param1": "test_value"}}'

# Check tool appears in list
curl http://localhost:8080/tools | grep new_tool_name
```

### Adding a New API Endpoint

#### Step 1: Add the Endpoint to app.py

```python
# backend/app.py

from pydantic import BaseModel
from typing import Optional

# Create request model
class NewEndpointRequest(BaseModel):
    field1: str
    field2: Optional[int] = None

# Create response model
class NewEndpointResponse(BaseModel):
    result: str
    data: dict

# Add the endpoint
@app.post("/new-endpoint",
          summary="New Endpoint",
          description="Description of the new endpoint",
          response_model=NewEndpointResponse,
          tags=["New Feature"])
@limiter.limit("10/minute")
async def new_endpoint(
    request: Request,
    data: NewEndpointRequest,
    user: UserInfo = Depends(verify_azure_auth)
):
    """
    Process new endpoint request.
    
    Args:
        data: Request data
        user: Authenticated user
    
    Returns:
        NewEndpointResponse: Response data
    """
    # Process the request
    result = process_new_request(data)
    
    return NewEndpointResponse(
        result="success",
        data=result
    )
```

#### Step 2: Add Rate Limiting (Optional)

```python
# Custom rate limit for the endpoint
@app.post("/new-endpoint")
@limiter.limit("20/minute")  # Different rate limit
async def new_endpoint(...):
    ...
```

#### Step 3: Test the New Endpoint

```bash
# Test with curl
curl -X POST http://localhost:8080/new-endpoint \
  -H "Content-Type: application/json" \
  -d '{"field1": "value1", "field2": 100}'

# Check it appears in OpenAPI schema
curl http://localhost:8080/openapi.json | grep new-endpoint

# Access via Swagger UI
# Open http://localhost:8080/docs and find the new endpoint
```

### Adding a New Frontend Component

#### Step 1: Create the Component File

```bash
# Navigate to components directory
cd frontend/src/components

# Create new component
touch NewComponent.jsx
```

#### Step 2: Implement the Component

```jsx
// frontend/src/components/NewComponent.jsx
import React, { useState, useEffect } from 'react';

/**
 * NewComponent - Description of the component
 * 
 * @param {Object} props - Component props
 * @param {string} props.title - Component title
 * @param {Function} props.onAction - Callback for user actions
 * @returns {JSX.Element} Rendered component
 */
const NewComponent = ({ title = 'Default Title', onAction }) => {
  const [data, setData] = useState(null);
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState(null);

  useEffect(() => {
    // Fetch data on mount
    const fetchData = async () => {
      setLoading(true);
      try {
        // Call API
        const response = await fetch('/api/new-endpoint', {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ field1: 'value' })
        });
        const result = await response.json();
        setData(result);
      } catch (err) {
        setError(err.message);
      } finally {
        setLoading(false);
      }
    };

    fetchData();
  }, []);

  const handleAction = () => {
    if (onAction) {
      onAction(data);
    }
  };

  if (loading) return <div>Loading...</div>;
  if (error) return <div className="error">{error}</div>;

  return (
    <div className="new-component">
      <h2>{title}</h2>
      <button onClick={handleAction}>Trigger Action</button>
      {data && (
        <pre>{JSON.stringify(data, null, 2)}</pre>
      )}
    </div>
  );
};

NewComponent.propTypes = {
  title: PropTypes.string,
  onAction: PropTypes.func
};

export default NewComponent;
```

#### Step 3: Use the Component

```jsx
// In App.jsx or another component
import NewComponent from './components/NewComponent';

const App = () => {
  const handleAction = (data) => {
    console.log('Action triggered:', data);
  };

  return (
    <div>
      <NewComponent title="My New Component" onAction={handleAction} />
    </div>
  );
};
```

#### Step 4: Rebuild Frontend

```bash
# Navigate to frontend directory
cd frontend

# Rebuild
npm run build

# Navigate back
cd ..

# Restart the backend to pick up new frontend files
# (or use --reload flag)
```

---

## 🧪 Testing

### Backend Testing

#### Running Tests

```bash
# Run all tests
pytest

# Run with verbose output
pytest -v

# Run specific test file
pytest tests/test_mcp.py

# Run specific test function
pytest tests/test_mcp.py::test_tool_execution

# Run with coverage
pytest --cov=backend --cov-report=html

# Open coverage report in browser
open htmlcov/index.html
```

#### Test File Structure

```python
# tests/test_mcp.py
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_mcp():
    # Mock MCP server if needed
    pass

def test_health_endpoint(client):
    """Test the health check endpoint."""
    response = client.get("/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"

def test_mcp_tool_execution(client, mock_mcp):
    """Test MCP tool execution."""
    response = client.post(
        "/tool",
        json={
            "tool": "get_usage_guidance",
            "arguments": {}
        }
    )
    assert response.status_code == 200
    assert "tool" in response.json()

def test_tools_endpoint(client):
    """Test tools list endpoint."""
    response = client.get("/tools")
    assert response.status_code == 200
    assert "tools" in response.json()
    assert len(response.json()["tools"]) > 0
```

#### Test Database

The project uses SQLite for local storage:

```bash
# Check if database exists
ls -la backend/*.db

# Reset database (for testing)
rm -f backend/*.db
```

### Frontend Testing

#### Running Frontend Tests

```bash
# Navigate to frontend directory
cd frontend

# Run tests
npm test

# Run tests with coverage
npm test -- --coverage

# Run specific test file
npm test -- --testPathPattern=Component.test
```

#### Test File Structure

```jsx
// frontend/src/components/NewComponent.test.jsx
import React from 'react';
import { render, screen, fireEvent } from '@testing-library/react';
import NewComponent from './NewComponent';

describe('NewComponent', () => {
  it('renders with title', () => {
    render(<NewComponent title="Test Title" />);
    expect(screen.getByText('Test Title')).toBeInTheDocument();
  });

  it('calls onAction when button clicked', () => {
    const mockAction = jest.fn();
    render(<NewComponent onAction={mockAction} />);
    fireEvent.click(screen.getByText('Trigger Action'));
    expect(mockAction).toHaveBeenCalled();
  });
});
```

### Integration Testing

#### Testing Full Workflow

```python
# tests/test_integration.py
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.fixture
def client():
    return TestClient(app)

def test_chat_to_analysis_workflow(client):
    """Test complete chat to analysis workflow."""
    # Send chat message
    chat_response = client.post(
        "/chat",
        json={
            "message": "What are the latest refugee numbers from Syria?",
            "audience": "policy_maker"
        }
    )
    assert chat_response.status_code == 200
    
    # Check analysis was saved
    history_response = client.get("/history")
    assert history_response.status_code == 200
    assert len(history_response.json()["analyses"]) > 0
```

#### Testing MCP Tool Execution

```python
# tests/test_mcp_tools.py
import pytest
from backend.mcp.tools.get_population_data import get_population_data

@pytest.mark.asyncio
async def test_get_population_data():
    """Test the get_population_data tool."""
    result = await get_population_data(
        coo="SYR",
        coa="TUR",
        year=2024
    )
    assert isinstance(result, dict)
    assert "data" in result or "error" in result
```

---

## 🐛 Debugging

### Backend Debugging

#### Logging

```python
# In any backend file
import logging

logger = logging.getLogger(__name__)

# Log messages at different levels
logger.debug("Debug message")
logger.info("Info message")
logger.warning("Warning message")
logger.error("Error message")
logger.exception("Exception with traceback")  # Use in except blocks
```

#### Enable Debug Logging

```bash
# Run with debug logging
LOG_LEVEL=debug python -m backend.main

# Or via environment variable
export LOG_LEVEL=debug
python -m backend.main
```

#### Debugging FastAPI

```python
# In backend/app.py or main.py
import logging

# Configure detailed logging
logging.basicConfig(
    level=logging.DEBUG,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler("debug.log")
    ]
)

# Or use uvicorn's built-in logging
python -m backend.main --log-level debug
```

#### Debugging MCP Server

```python
# In backend/mcp/server.py
import logging

mcp_logger = logging.getLogger("mcp")
mcp_logger.setLevel(logging.DEBUG)

# Add handler
mcp_handler = logging.StreamHandler()
mcp_handler.setLevel(logging.DEBUG)
mcp_logger.addHandler(mcp_handler)
```

#### Debugging with pdb

```python
# Insert breakpoint in code
import pdb; pdb.set_trace()

# Or use the newer breakpoint() function (Python 3.7+)
breakpoint()
```

#### Debugging with ipdb

```bash
# Install ipdb
pip install ipdb

# Use in code
import ipdb; ipdb.set_trace()
```

### Frontend Debugging

#### Browser Developer Tools

- **Chrome**: F12 or Ctrl+Shift+I
- **Firefox**: F12 or Ctrl+Shift+K
- **Edge**: F12 or Ctrl+Shift+I

#### Console Logging

```jsx
// In any component
console.log("Debug message");
console.info("Info message");
console.warn("Warning message");
console.error("Error message");

// Log objects
console.log("Data:", data);
console.table(data);  // For arrays/objects

// Timing
console.time("operation");
// ... code ...
console.timeEnd("operation");
```

#### Debugging React with React Developer Tools

1. Install [React Developer Tools](https://react.dev/learn/react-developer-tools) browser extension
2. Open the extension in your browser
3. Select the React component to inspect
4. View props, state, and hooks

#### Debugging API Calls

```jsx
// In your service file or component
const fetchData = async () => {
  try {
    console.log("Fetching data...");
    const response = await fetch('/api/endpoint', {
      method: 'POST',
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ key: 'value' })
    });
    
    console.log("Response status:", response.status);
    console.log("Response headers:", [...response.headers]);
    
    const data = await response.json();
    console.log("Response data:", data);
    
    return data;
  } catch (error) {
    console.error("Fetch error:", error);
    throw error;
  }
};
```

#### Debugging with VS Code

Create a `.vscode/launch.json` file:

```json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Backend",
      "type": "python",
      "request": "launch",
      "module": "backend.main",
      "args": ["--reload"],
      "env": {
        "PORT": "8080",
        "LOG_LEVEL": "debug"
      },
      "justMyCode": false
    },
    {
      "name": "Python: Backend (Uvicorn)",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": ["backend.main:app", "--host", "0.0.0.0", "--port", "8080", "--reload"],
      "env": {
        "PORT": "8080",
        "LOG_LEVEL": "debug"
      }
    }
  ]
}
```

### MCP Server Debugging

#### Check MCP Server Status

```bash
# Check MCP endpoint
curl http://localhost:8080/mcp

# Check MCP documentation
curl http://localhost:8080/api/mcp/docs

# Check MCP info
curl http://localhost:8080/api/mcp/info

# List tools
curl http://localhost:8080/tools
```

#### Debug MCP Tool Execution

```python
# In backend/mcp_bridge.py
import logging

mcp_bridge_logger = logging.getLogger("mcp_bridge")
mcp_bridge_logger.setLevel(logging.DEBUG)

async def call_tool(tool_name: str, arguments: dict) -> dict:
    """Call an MCP tool with enhanced logging."""
    mcp_bridge_logger.debug(f"Calling tool: {tool_name} with args: {arguments}")
    
    try:
        # ... existing code ...
        result = await tool_function(**arguments)
        mcp_bridge_logger.debug(f"Tool {tool_name} result: {result}")
        return result
    except Exception as e:
        mcp_bridge_logger.error(f"Tool {tool_name} error: {e}")
        raise
```

#### Test MCP Tool Directly

```python
# In a Python shell or script
import asyncio
from backend.mcp.tools.get_population_data import get_population_data

async def test():
    result = await get_population_data(coo="SYR", coa="TUR", year=2024)
    print("Result:", result)

asyncio.run(test())
```

---

## 🎨 Code Quality

### Code Style Guidelines

#### Python

- **Indentation**: 4 spaces (no tabs)
- **Line Length**: Maximum 120 characters (soft limit)
- **Naming**: snake_case for variables and functions, PascalCase for classes
- **Imports**: Grouped by type (standard library, third-party, local)

```python
# Good example
import os
import sys

from typing import Optional
from fastapi import FastAPI

from backend.common import helper_function
from backend.mcp.tools import get_population_data
```

#### JavaScript/React

- **Indentation**: 2 spaces
- **Naming**: camelCase for variables and functions, PascalCase for components
- **Props**: Use destructuring

```jsx
// Good example
const MyComponent = ({ 
  userName, 
  userEmail, 
  onSubmit 
}) => {
  const [loading, setLoading] = useState(false);
  
  // ...
};
```

### Type Hints

#### Python Type Hints

```python
# Basic types
def greet(name: str) -> str:
    return f"Hello, {name}"

# Optional types
def get_user(id: int) -> Optional[dict]:
    # ...
    return None

# Union types
def process_value(value: int | str | None) -> str:
    return str(value or "")

# Collections
def get_items(ids: list[int]) -> list[dict]:
    # ...
    return []

# Dictionaries
def get_config() -> dict[str, Any]:
    # ...
    return {}

# Using TypedDict
from typing import TypedDict

class UserInfo(TypedDict):
    email: str
    name: str
    roles: list[str]

def get_user_info() -> UserInfo:
    return {"email": "user@example.com", "name": "John", "roles": ["user"]}
```

#### TypeScript Type Hints

```typescript
// Interface
interface User {
  id: number;
  name: string;
  email: string;
  roles: string[];
}

// Type alias
type Status = 'active' | 'inactive' | 'suspended';

// Function with types
const greetUser = (user: User): string => {
  return `Hello, ${user.name}`;
};

// Optional properties
interface Config {
  timeout?: number;
  retries?: number;
  enabled?: boolean;
}

// Generic types
const firstItem = <T>(items: T[]): T | undefined => {
  return items[0];
};
```

### Docstrings

#### Python Docstrings

Use Google-style docstrings:

```python
def get_population_data(
    coo: Optional[str] = None,
    coa: Optional[str] = None,
    year: Optional[int | str] = None
) -> dict:
    """
    Retrieve forcibly displaced population statistics from UNHCR.
    
    Retrieves population data for refugees, asylum-seekers, and other
    forcibly displaced populations from the UNHCR API.
    
    Args:
        coo: Country of origin (ISO 3-letter code). If None, returns all countries.
        coa: Country of asylum (ISO 3-letter code). If None, returns all countries.
        year: Year of data. If None, returns latest available data.
    
    Returns:
        dict: Dictionary containing:
            - data: List of population records
            - metadata: Query metadata including count and timestamp
    
    Raises:
        ValueError: If coo or coa are not valid ISO codes
        ConnectionError: If UNHCR API is unavailable
    
    Example:
        >>> await get_population_data(coo="SYR", coa="TUR", year=2024)
        {
            "data": [{"coo": "SYR", "coa": "TUR", "year": 2024, "value": 3680000}],
            "metadata": {"count": 1, "timestamp": "2024-01-01T00:00:00Z"}
        }
    """
    # ... implementation
```

#### JavaScript/TypeScript Docstrings

Use JSDoc style:

```typescript
/**
 * Retrieves UNHCR population data for a specific query.
 * 
 * @param {Object} params - Query parameters
 * @param {string} [params.coo] - Country of origin (ISO 3-letter code)
 * @param {string} [params.coa] - Country of asylum (ISO 3-letter code)
 * @param {number|string} [params.year] - Year of data
 * @returns {Promise<Object>} - Population data with metadata
 * @throws {Error} - If API request fails
 * 
 * @example
 * const data = await getPopulationData({ coo: 'SYR', coa: 'TUR', year: 2024 });
 */
async function getPopulationData(params: {
  coo?: string;
  coa?: string;
  year?: number | string;
} = {}): Promise<PopulationData> {
  // ... implementation
}
```

### Error Handling

#### Python Error Handling

```python
# Specific exceptions
from fastapi import HTTPException

try:
    result = await some_operation()
except ValueError as e:
    logger.error(f"Value error: {e}")
    raise HTTPException(status_code=400, detail=str(e))
except ConnectionError as e:
    logger.error(f"Connection error: {e}")
    raise HTTPException(status_code=503, detail="Service unavailable")
except Exception as e:
    logger.exception(f"Unexpected error: {e}")
    raise HTTPException(status_code=500, detail="Internal server error")

# Custom exceptions
class MCPToolError(Exception):
    """Raised when an MCP tool encounters an error."""
    def __init__(self, tool_name: str, message: str):
        self.tool_name = tool_name
        self.message = message
        super().__init__(f"{tool_name}: {message}")
```

#### JavaScript/TypeScript Error Handling

```typescript
// Try-catch with proper error handling
try {
  const response = await fetch('/api/endpoint');
  
  if (!response.ok) {
    throw new Error(`HTTP error! status: ${response.status}`);
  }
  
  const data = await response.json();
  return data;
} catch (error) {
  // Handle different error types
  if (error instanceof TypeError) {
    console.error('Network error:', error.message);
  } else if (error instanceof Error) {
    console.error('Request error:', error.message);
  } else {
    console.error('Unknown error:', error);
  }
  
  // Re-throw or return error
  throw error;
}

// Custom error classes
class APIError extends Error {
  constructor(message: string, public statusCode: number) {
    super(message);
    this.name = 'APIError';
    this.statusCode = statusCode;
  }
}

class ValidationError extends Error {
  constructor(message: string, public fields: string[]) {
    super(message);
    this.name = 'ValidationError';
    this.fields = fields;
  }
}
```

---

## 🔄 Git Workflow

### Branching Strategy

| Branch Type | Naming Convention | Purpose |
|-------------|-------------------|---------|
| `main` | `main` | Production-ready code |
| `develop` | `develop` | Integration branch |
| Feature | `feature/<description>` | New features |
| Bugfix | `bugfix/<description>` | Bug fixes |
| Hotfix | `hotfix/<description>` | Critical fixes |
| Documentation | `docs/<description>` | Documentation updates |
| Refactor | `refactor/<description>` | Code refactoring |

### Creating a Feature Branch

```bash
# Ensure you're on main
git checkout main

# Pull latest changes
git pull origin main

# Create new feature branch
git checkout -b feature/add-new-mcp-tool

# Push to remote
git push origin feature/add-new-mcp-tool
```

### Committing Changes

```bash
# Stage changes
git add backend/mcp/tools/new_tool.py

# Or stage all changes
git add .

# Commit with message
git commit -m "feat(mcp): add new_tool_name MCP tool"

# Push changes
git push origin feature/add-new-mcp-tool
```

### Commit Message Format

Use Conventional Commits format:

```
<type>(<scope>): <description>

<body>

<footer>
```

**Types**: feat, fix, docs, style, refactor, perf, test, chore, build, ci, revert

**Scopes**: mcp, api, frontend, backend, deployment, tests, docs

**Examples**:
- `feat(mcp): add get_population_trends tool`
- `fix(api): handle null values in tool responses`
- `docs: update README with deployment instructions`
- `chore: update dependencies`

### Rebasing

```bash
# While on feature branch
git fetch origin

# Rebase onto main
git rebase origin/main

# Resolve conflicts if any
# (edit files, git add, git rebase --continue)

# Force push (after rebase)
git push origin feature/add-new-mcp-tool --force-with-lease
```

---

## 📝 Pull Request Process

### Before Submitting a Pull Request

1. **Ensure all tests pass**
   ```bash
   pytest
   cd frontend && npm test
   ```

2. **Run linting/formatting**
   ```bash
   # Python
   pip install black isort flake8
   black backend/
   isort backend/
   flake8 backend/
   
   # JavaScript
   cd frontend
   npm run lint
   npm run format
   ```

3. **Update documentation**
   - Update relevant documentation files
   - Add API documentation if new endpoints were added
   - Update tool descriptions if MCP tools were modified

4. **Test locally**
   ```bash
   # Start the application
   ./boot.sh
   
   # Test all changes
   curl http://localhost:8080/health
   curl http://localhost:8080/tools
   ```

### Creating a Pull Request

1. Push your branch to remote
2. Go to GitHub/GitLab repository
3. Click "Create Pull Request"
4. Fill in PR template
5. Add reviewers
6. Link to any related issues
7. Submit PR

### Pull Request Template

```markdown
## 📌 Description

Brief description of the changes.

## 🎯 Related Issues

- Fixes #123
- Relates to #456

## 📝 Changes

- Added new MCP tool: `get_population_trends`
- Updated API documentation
- Fixed bug in tool execution

## ✅ Checklist

- [x] All tests pass
- [x] Code follows style guidelines
- [x] Documentation updated
- [x] Breaking changes documented
- [x] Screenshots added (if UI changes)

## 🔍 Testing

Describe how you tested your changes:
- Manual testing with curl
- Unit tests added
- Integration tests pass

## 📊 Performance Impact

Describe any performance implications:
- No performance impact
- Reduced API latency by X%
- Increased memory usage by Y MB

## 🚀 Deployment Notes

Any special deployment instructions:
- Requires new environment variable: `NEW_VAR=value`
- Database migration needed
- Cache invalidation required
```

### After PR Submission

1. **Address review comments**
   - Fix issues pointed out in review
   - Commit changes and push to branch
   - Comment on PR to notify reviewers

2. **Merge PR**
   - Squash and merge (preferred)
   - Or rebase and merge
   - Or merge commit

3. **Delete branch** (optional)
   ```bash
   git branch -d feature/add-new-mcp-tool
   git push origin --delete feature/add-new-mcp-tool
   ```

---

## 💡 Local Development Tips

### Hot Reload

#### Backend Hot Reload

```bash
# Using uvicorn with --reload
python -m backend.main --reload

# Using gunicorn with single worker and reload
# (Note: Gunicorn reload doesn't work well with multiple workers)
gunicorn backend.main:app \
  --bind 0.0.0.0:8080 \
  --workers 1 \
  --reload \
  --worker-class uvicorn.workers.UvicornWorker
```

#### Frontend Hot Reload

```bash
# In frontend directory
cd frontend

# Run development server with hot reload
npm run dev

# The frontend will be available at http://localhost:5173
# And will proxy API requests to http://localhost:8080
```

### Using Docker with Hot Reload

```bash
# Build the image first
docker build -t unhcr-stat-copilot .

# Run with volume mounts for hot reload
docker run -p 8080:8080 \
  -v $(pwd)/backend:/app/backend \
  -v $(pwd)/frontend:/app/frontend \
  -e PORT=8080 \
  -e LOG_LEVEL=debug \
  unhcr-stat-copilot
```

### Running Multiple Services

```bash
# Terminal 1: Backend
python -m backend.main --reload

# Terminal 2: Frontend (if using Vite)
cd frontend && npm run dev

# Terminal 3: Monitoring
watch -n 1 "curl -s http://localhost:8080/health | jq"
```

### Using make Commands

Create a `Makefile` for common tasks:

```makefile
.PHONY: install install-backend install-frontend build run test lint clean

PORT ?= 8080

install: install-backend install-frontend

install-backend:
	cd backend && pip install -r requirements.txt

install-frontend:
	cd frontend && npm install

build: install
	cd frontend && npm run build

run:
	PORT=${PORT} LOG_LEVEL=debug python -m backend.main --reload

run-production:
	PORT=${PORT} gunicorn backend.main:app --bind 0.0.0.0:${PORT} --workers 2 --worker-class uvicorn.workers.UvicornWorker

test:
	pytest

lint:
	cd backend && black . && isort . && flake8 .
	cd frontend && npm run lint

clean:
	rm -rf backend/__pycache__ backend/*.pyc backend/*.db
	rm -rf frontend/node_modules frontend/dist
	docker system prune -f
```

Use with:
```bash
make install
make run
make test
make lint
```

---

## 🌍 Environment Configuration

### Using .env File

Create a `.env` file in the project root:

```bash
# .env
PORT=8080
LOG_LEVEL=debug
RATE_LIMIT_ENABLED=true
WEB_CONCURRENCY=2

# Azure configuration (optional)
AZURE_CLIENT_ID=your-client-id
AZURE_CLIENT_SECRET=your-client-secret
AZURE_TENANT_ID=your-tenant-id

# UNHCR API configuration (if needed)
UNHCR_API_URL=https://api.unhcr.org/population/v1
UNHCR_API_KEY=your-api-key
```

Load the `.env` file:

```python
# In backend/app.py and backend/main.py
from dotenv import load_dotenv
load_dotenv()
```

### Multiple Environments

Create separate `.env` files for different environments:

```bash
# .env.development
PORT=8080
LOG_LEVEL=debug
RATE_LIMIT_ENABLED=false

# .env.production
PORT=8080
LOG_LEVEL=info
RATE_LIMIT_ENABLED=true

# .env.test
PORT=8081
LOG_LEVEL=warning
RATE_LIMIT_ENABLED=false
```

Load specific environment:

```python
# Load .env.development
load_dotenv('.env.development')

# Or use command line
export ENV_FILE=.env.development
python -c "from dotenv import load_dotenv; load_dotenv(os.getenv('ENV_FILE'))"
```

---

## 💻 IDE Setup

### VS Code

#### Recommended Extensions

| Extension | Purpose |
|-----------|---------|
| Python | Python support |
| Pylance | Python type hints and IntelliSense |
| Jupyter | Jupyter notebook support |
| ESLint | JavaScript linting |
| Prettier | Code formatting |
| GitLens | Git supercharged |
| REST Client | HTTP requests from VS Code |
| Thunder Client | API testing |
| Docker | Docker support |

#### Recommended Settings

```json
// .vscode/settings.json
{
  "python.pythonPath": "venv/bin/python",
  "python.linting.enabled": true,
  "python.linting.flake8Enabled": true,
  "python.formatting.provider": "black",
  "[python]": {
    "editor.defaultFormatter": "ms-python.black-formatter",
    "editor.formatOnSave": true,
    "editor.codeActionsOnSave": {
      "source.organizeImports": true
    }
  },
  "editor.tabSize": 2,
  "editor.insertSpaces": true,
  "files.exclude": {
    "**/__pycache__": true,
    "**/*.pyc": true,
    "venv": true,
    "node_modules": true,
    ".env": true
  }
}
```

#### Launch Configuration

```json
// .vscode/launch.json
{
  "version": "0.2.0",
  "configurations": [
    {
      "name": "Python: Backend (Debug)",
      "type": "python",
      "request": "launch",
      "module": "backend.main",
      "args": ["--reload"],
      "env": {
        "PORT": "8080",
        "LOG_LEVEL": "debug"
      },
      "justMyCode": false
    },
    {
      "name": "Python: Backend (Uvicorn)",
      "type": "python",
      "request": "launch",
      "module": "uvicorn",
      "args": [
        "backend.main:app",
        "--host", "0.0.0.0",
        "--port", "8080",
        "--reload"
      ],
      "env": {
        "PORT": "8080",
        "LOG_LEVEL": "debug"
      }
    },
    {
      "name": "Python: Run Tests",
      "type": "python",
      "request": "launch",
      "module": "pytest",
      "args": [
        "-v",
        "--no-header"
      ],
      "console": "integratedTerminal"
    }
  ]
}
```

### PyCharm

#### Project Setup

1. Open the project folder in PyCharm
2. Go to File > Settings > Project > Python Interpreter
3. Click the gear icon > Add
4. Select "Existing Environment" and browse to `venv/bin/python`

#### Run Configuration

1. Go to Run > Edit Configurations
2. Click + > Python
3. Script path: `backend/main.py`
4. Working directory: Project root
5. Environment variables: `PORT=8080;LOG_LEVEL=debug`
6. Click OK

#### Code Style

1. Go to File > Settings > Editor > Code Style > Python
2. Set indentation to 4 spaces
3. Set maximum line length to 120
4. Enable "Ensure line feed at file end on Save"
5. Enable "Strip trailing spaces on Save"

### Other Editors

For any editor, ensure:
- Python 3.11+ support
- PEP 8 compliance
- Black formatter integration
- isort for import sorting
- ESLint/Prettier for JavaScript

---

## ⚡ Performance Tips

### Backend Performance

1. **Use async/await** for I/O operations
2. **Cache expensive computations** when appropriate
3. **Limit concurrent MCP requests** to avoid overwhelming external APIs
4. **Use connection pooling** for external services
5. **Set appropriate timeouts** for external requests

```python
# Good: Async I/O
import aiohttp

async def fetch_data():
    async with aiohttp.ClientSession() as session:
        async with session.get(url) as response:
            return await response.json()

# Bad: Synchronous I/O (blocks event loop)
import requests

def fetch_data():
    response = requests.get(url)
    return response.json()
```

### Frontend Performance

1. **Use React.memo** for expensive components
2. **Use useMemo** for expensive calculations
3. **Use useCallback** for event handlers
4. **Virtualize long lists** with libraries like `react-window`
5. **Lazy load components** with React.lazy

```jsx
// Lazy loading
const HeavyComponent = React.lazy(() => import('./HeavyComponent'));

// Memoization
const MyComponent = React.memo(({ data }) => {
  const processedData = useMemo(() => {
    return expensiveCalculation(data);
  }, [data]);

  const handleClick = useCallback(() => {
    // ...
  }, []);

  return <div>{processedData}</div>;
});
```

### MCP Server Performance

1. **Set appropriate timeouts** for tool execution
2. **Limit concurrent tool executions**
3. **Cache tool results** when appropriate (for non-real-time data)
4. **Validate arguments early** to avoid expensive operations

```python
# In backend/mcp_bridge.py
from backend.mcp.server import mcp_server

# Configure MCP server timeout
mcp_server.settings.request_timeout = 30  # seconds

# Configure max concurrent requests
mcp_server.settings.max_concurrent_requests = 10
```

---

## 🎯 Common Development Tasks

### Task: Add a New Country Code

```python
# In a configuration file (e.g., backend/config/countries.py)
COUNTRY_CODES = {
    "SYR": "Syria",
    "TUR": "Turkey",
    "AFG": "Afghanistan",
    # Add new codes here
    "UKR": "Ukraine",
}

# Update validation
from backend.config.countries import COUNTRY_CODES

def validate_country_code(code: str) -> bool:
    return code.upper() in COUNTRY_CODES
```

### Task: Update Dependencies

```bash
# Update Python dependencies
cd backend
pip install --upgrade package-name
pip freeze > requirements.txt

# Or use pip-tools
pip-compile requirements.in

# Update Node.js dependencies
cd frontend
npm update package-name
# Or
npm install package-name@latest
```

### Task: Run Database Migration

```bash
# If using Alembic for database migrations
cd backend
alembic revision --autogenerate -m "add_new_table"
alembic upgrade head

# Or for simple SQLite
# Just modify the schema in your code
# SQLite will handle it automatically
```

### Task: Clean Build

```bash
# Remove all build artifacts
rm -rf backend/__pycache__ backend/*.pyc backend/*.db
rm -rf frontend/node_modules frontend/dist
rm -rf venv

# Rebuild everything
git checkout .
python -m venv venv
source venv/bin/activate
pip install -r backend/requirements.txt
cd frontend && npm install && npm run build
cd ..
```

### Task: Generate API Documentation

```bash
# FastAPI automatically generates OpenAPI schema
# Access at /openapi.json

# Download OpenAPI schema
curl http://localhost:8080/openapi.json > openapi.json

# Generate Swagger UI (already built-in)
# Access at /docs

# Generate ReDoc (already built-in)
# Access at /redoc
```

### Task: Profile Application

```bash
# Install profiler
pip install cProfile

# Profile the application
python -m cProfile -o profile.stats -m backend.main

# Analyze profile
python -m pstats profile.stats
```

### Task: Memory Profiling

```bash
# Install memory profiler
pip install memory-profiler

# Profile memory usage
python -m memory_profiler -m backend.main
```

---

## 📚 See Also

- [README.md](./README.md) - Main documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - API reference
- [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) - MCP integration guide
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions

---

*Last updated: July 7, 2026*
