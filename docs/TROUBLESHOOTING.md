# Troubleshooting Guide

Comprehensive troubleshooting documentation for the UNHCR Statistics Copilot, addressing common issues encountered during development, deployment, and usage.

## 📚 Table of Contents

- [Quick Start](#quick-start)
- [Common Error Messages](#common-error-messages)
- [MCP Server Issues](#mcp-server-issues)
- [API/Endpoint Issues](#apiendpoint-issues)
- [Docker Issues](#docker-issues)
- [Azure Deployment Issues](#azure-deployment-issues)
- [Frontend Issues](#frontend-issues)
- [Authentication Issues](#authentication-issues)
- [Performance Issues](#performance-issues)
- [Network/Connectivity Issues](#networkconnectivity-issues)
- [Data/Database Issues](#datadatabase-issues)
- [Dependency Issues](#dependency-issues)
- [Testing Issues](#testing-issues)
- [Log Analysis](#log-analysis)
- [Self-Help Checklist](#self-help-checklist)
- [Getting Help](#getting-help)

---

## 🚀 Quick Start

Before diving into specific issues, try these general troubleshooting steps:

### 1. Check Basic Health

```bash
# Check if the application is running
curl http://localhost:8080/health

# Check root endpoint
curl http://localhost:8080/

# Check MCP server
curl http://localhost:8080/mcp
```

**Expected**: All should return HTTP 200 with JSON responses.

### 2. Check Logs

```bash
# Docker logs
docker logs <container-name>

# Azure App Service logs
az webapp log tail --name unhcr-stat-copilot --resource-group unhcr-copilot-rg

# Local Python logs
# (if running locally, check terminal output)
```

### 3. Verify Dependencies

```bash
# Python dependencies
pip list | grep -E "(fastapi|uvicorn|gunicorn|fastmcp|mcp)"

# Node.js dependencies (if applicable)
npm list | grep -E "(react|typescript|vite)"
```

### 4. Test with a Simple Request

```bash
# Test a simple tool that doesn't require external API
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_usage_guidance", "arguments": {}}'
```

---

## ❌ Common Error Messages

### Error: "405 Method Not Allowed"

**Problem**: Attempting to POST to an endpoint that only accepts GET, or vice versa.

**Common Scenarios**:
1. Azure health check POSTing to `/mcp`
2. Trying to GET a POST-only endpoint
3. Incorrect endpoint URL

**Solutions**:

#### For Azure Deployment

This was a **previous attempted fix** that has been **reverted** because it caused JSON-RPC parsing errors. The health check endpoints at `/mcp` were returning plain JSON instead of JSON-RPC format, which broke MCP clients.

**Current Solution**: The `/mcp` health check endpoints have been removed. Requests to `/mcp` are now automatically redirected to `/mcp/` where the FastMCP server handles them properly.

**Important**: For Azure deployments, configure health checks to use `/health` instead of `/mcp`.

**For Azure App Service**: 
- Set the health check path to `/health` in your App Service configuration
- Or set `WEBSITE_HEALTHCHECK_PATH=/health` environment variable

**Verification**:
```bash
# Test GET request - should redirect to /mcp/
curl -i http://localhost:8080/mcp
# Should return: 307 Temporary Redirect to /mcp/

# Test health check endpoint
curl http://localhost:8080/health
# Should return: {"status": "healthy", ...}
```

#### For Other Cases

Check the correct HTTP method for the endpoint:

| Endpoint | Methods |
|----------|---------|
| `/health` | GET |
| `/` | GET |
| `/mcp` | GET, POST |
| `/tool` | POST |
| `/chat` | POST |
| `/story` | POST |
| `/report` | POST |
| `/history` | GET |
| `/tools` | GET |
| `/api/mcp/docs` | GET |
| `/api/mcp/info` | GET |
| `/docs` | GET |
| `/redoc` | GET |

**Solution**: Use the correct HTTP method.

```bash
# Correct: GET for /tools
curl http://localhost:8080/tools

# Correct: POST for /tool
curl -X POST http://localhost:8080/tool -H "Content-Type: application/json" -d '{}'
```

---

### Error: "404 Not Found"

**Problem**: The requested endpoint does not exist.

**Common Causes**:
1. Typo in endpoint URL
2. Missing leading slash
3. Wrong port number
4. Application not running
5. Frontend routing issues

**Solutions**:

#### Check Endpoint Exists

```bash
# List all available endpoints
curl http://localhost:8080/openapi.json | python -m json.tool | grep -A 1 "paths"

# Or check Swagger UI
# Open http://localhost:8080/docs in browser
```

#### Verify Application is Running

```bash
# Check process is running
ps aux | grep -E "(python|gunicorn|uvicorn)" | grep -v grep

# Check port is listening
netstat -tlnp | grep 8080
# or
lsof -i :8080
```

#### Check Port Number

```bash
# Verify your application is using the expected port
curl http://localhost:8080/health

# If not working, try other common ports
curl http://localhost:8000/health
curl http://localhost:9000/health
```

#### Fix: `/api/mcp/docs` vs `/mcp/docs`

**Problem**: Documentation endpoints were incorrectly referenced as `/mcp/docs` and `/mcp/info`.

**Solution**: Use the correct endpoints:

```bash
# Correct endpoints
curl http://localhost:8080/api/mcp/docs
curl http://localhost:8080/api/mcp/info

# NOT these (which will return 404)
curl http://localhost:8080/mcp/docs
curl http://localhost:8080/mcp/info
```

---

### Error: "500 Internal Server Error"

**Problem**: An unexpected error occurred on the server.

**Common Causes**:
1. Syntax error in code
2. Missing dependencies
3. Database connection issues
4. External API failures
5. Unhandled exceptions

**Debugging Steps**:

#### Check Server Logs

```bash
# Docker
docker logs <container-name>

# Local
tail -50 nohup.out  # If running in background

# Or check terminal where you started the app
```

#### Enable Debug Logging

```bash
# Stop current server
# Then restart with debug logging
LOG_LEVEL=debug python -m backend.main

# Or for Docker
docker run -p 8080:8080 -e PORT=8080 -e LOG_LEVEL=debug unhcr-stat-copilot
```

#### Get Detailed Error

```bash
# Make a request and capture full response
curl -v http://localhost:8080/some-endpoint 2>&1 | tail -20

# Or with Python
python -c "
import requests
try:
    r = requests.get('http://localhost:8080/some-endpoint')
    print('Status:', r.status_code)
    print('Response:', r.text)
except Exception as e:
    print('Error:', e)
    import traceback
    traceback.print_exc()
"
```

#### Common 500 Causes and Fixes

| Error | Cause | Solution |
|-------|-------|----------|
| `ModuleNotFoundError` | Missing Python package | `pip install <package>` |
| `ImportError` | Cannot find module | Check `PYTHONPATH`, ensure backend/ is accessible |
| `NameError` | Variable not defined | Check for typos, scope issues |
| `TypeError` | Invalid operation | Check argument types |
| `KeyError` | Dictionary key missing | Add default values or check keys |

---

### Error: "503 Service Unavailable"

**Problem**: The service is temporarily unavailable.

**Common Causes**:
1. MCP server not initialized
2. Rate limiting triggered
3. Too many concurrent requests
4. Service is restarting
5. Resource exhaustion (memory/CPU)

**Solutions**:

#### Check MCP Server Status

```bash
# Check if MCP server is responding
curl http://localhost:8080/mcp

# Check if tools are available
curl http://localhost:8080/tools
```

#### Verify Lifespan Management

The MCP server requires proper lifespan management:

```python
# In backend/app.py
@asynccontextmanager
async def lifespan(app: FastAPI):
    async with mcp_session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
```

**Verification**:
```bash
# Check if lifespan is configured
python -c "from backend.app import app; print('Lifespan configured:', hasattr(app, 'lifespan'))"
```

#### Check Rate Limiting

```bash
# Check rate limit status
curl -v http://localhost:8080/tool 2>&1 | grep -i rate

# Check rate limit headers
curl -I http://localhost:8080/tool

# Look for: X-RateLimit-Limit, X-RateLimit-Remaining, X-RateLimit-Reset
```

**Solution**: Wait and retry, or disable rate limiting temporarily:

```bash
# Disable rate limiting
RATE_LIMIT_ENABLED=false python -m backend.main
```

#### Check Resource Usage

```bash
# Check memory usage (Linux)
top -u $(whoami)
free -m

# Check CPU usage
top -c
htop  # if installed

# Docker resource usage
docker stats <container-name>
```

---

### Error: "Failed to load API definition. Errors: Fetch error Internal Server Error /openapi.json"

**Problem**: FastAPI Swagger UI cannot load the OpenAPI schema.

**Common Causes**:
1. Ellipsis (`...`) in response examples
2. Invalid type hints
3. Circular imports
4. Syntax errors in endpoint definitions
5. Missing dependencies

**Solutions**:

#### Check OpenAPI Schema Directly

```bash
# Get the OpenAPI schema
curl http://localhost:8080/openapi.json 2>&1

# Validate JSON
curl -s http://localhost:8080/openapi.json | python -m json.tool
```

If this fails with an error, the issue is in the schema generation.

#### Fix Ellipsis in Response Examples

**Problem**: Response examples using `...` (ellipsis) cause JSON serialization errors.

**Solution**: Replace all ellipsis with actual values or `None`:

```python
# Bad (causes error)
responses={
    200: {
        "description": "Success",
        "content": {
            "application/json": {
                "example": {"data": ...}  # Ellipsis!
            }
        }
    }
}

# Good (fixed)
responses={
    200: {
        "description": "Success",
        "content": {
            "application/json": {
                "example": {"data": None}  # Or actual value
            }
        }
    }
}
```

**Verification**:
```bash
# Search for ellipsis in Python files
grep -r "\.\.\." backend/*.py backend/**/*.py
```

#### Validate All Endpoints

```python
# In backend/app.py
from fastapi import FastAPI

# Create a test to validate OpenAPI schema
def test_openapi_schema():
    from backend.app import app
    
    # Get the OpenAPI schema
    schema = app.openapi()
    
    # Try to serialize it (this will fail if there are issues)
    import json
    json.dumps(schema)
    
    print("OpenAPI schema is valid!")

if __name__ == "__main__":
    test_openapi_schema()
```

Run with:
```bash
python -c "from backend.app import app; import json; print(json.dumps(app.openapi()))"
```

#### Check for Circular Imports

```bash
# Use dephell to check circular imports
pip install dephell

dephell deps tree --filter circular backend/
```

**Solution**: Restructure imports or use lazy imports:

```python
# Instead of:
from backend.mcp.server import mcp_server

# Use lazy import:
def get_mcp_server():
    from backend.mcp.server import mcp_server
    return mcp_server
```

---

## 🤖 MCP Server Issues

### Issue: MCP Tools Not Available

**Problem**: Tools are not appearing in `/tools` endpoint.

**Debugging Steps**:

```bash
# Check tools endpoint
curl http://localhost:8080/tools

# Check MCP server info
curl http://localhost:8080/api/mcp/info

# Check MCP docs
curl http://localhost:8080/api/mcp/docs
```

**Expected**: Should list 20+ tools.

**Solutions**:

#### Verify Tool Registration

```python
# In backend/mcp/server.py
from backend.mcp.tools import (
    get_population_data,
    get_demographics_data,
    # ... all other tools
)

def create_server():
    server = FastMCPServer(...)
    
    # Ensure all tools are added
    server.add_tool(get_population_data)
    server.add_tool(get_demographics_data)
    # ... add all tools
    
    return server
```

**Verification**:
```bash
# Check if tools are registered in mcp_server
python -c "
from backend.mcp.server import create_server
server = create_server()
print('Registered tools:', [t.name for t in server._tool_manager.list_tools()])
"
```

#### Check MCP_TOOL_SCHEMAS

```python
# In backend/mcp_bridge.py
from backend.mcp_bridge import MCP_TOOL_SCHEMAS

print(f"Total tools in MCP_TOOL_SCHEMAS: {len(MCP_TOOL_SCHEMAS)}")
print("Tool names:", list(MCP_TOOL_SCHEMAS.keys()))
```

#### Verify MCP Session Manager

```bash
# Check if session manager is running
python -c "
from backend.app import mcp_session_manager
print('Session manager:', mcp_session_manager)
print('Running:', hasattr(mcp_session_manager, 'run'))
"
```

### Issue: MCP Tool Execution Fails

**Problem**: Tool execution returns 503 or other error.

**Debugging Steps**:

```bash
# Test a simple tool
curl -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_usage_guidance", "arguments": {}}'

# Test with more details
curl -v -X POST http://localhost:8080/mcp \
  -H "Content-Type: application/json" \
  -d '{"tool": "get_usage_guidance", "arguments": {}}' 2>&1
```

**Solutions**:

#### Check Tool Function Directly

```python
# Test tool function directly
python -c "
import asyncio
from backend.mcp.tools.get_usage_guidance import get_usage_guidance

async def test():
    try:
        result = await get_usage_guidance()
        print('Result:', result)
    except Exception as e:
        print('Error:', e)
        import traceback
        traceback.print_exc()

asyncio.run(test())
"
```

#### Verify Tool Schema

```python
# Check tool schema in MCP_TOOL_SCHEMAS
python -c "
from backend.mcp_bridge import MCP_TOOL_SCHEMAS
schema = MCP_TOOL_SCHEMAS.get('get_usage_guidance')
print('Schema:', schema)
"
```

#### Check for Import Errors

```bash
# Try importing the tool module
python -c "from backend.mcp.tools.get_usage_guidance import get_usage_guidance; print('Import successful')"
```

### Issue: MCP Server Session Not Initialized

**Problem**: Error message: "Task group is not initialized" or "503 MCP server unavailable"

**Solution**: Ensure the lifespan context manager is properly configured:

```python
# In backend/app.py
from contextlib import asynccontextmanager
from backend.mcp.server import create_server

mcp_server = create_server()
mcp_app = mcp_server.streamable_http_app()
mcp_session_manager = mcp_server.session_manager

@asynccontextmanager
async def lifespan(app: FastAPI):
    # This is critical - starts the session manager
    async with mcp_session_manager.run():
        yield

app = FastAPI(lifespan=lifespan)
```

**Verification**:
```bash
# Check lifespan is configured
python -c "from backend.app import app; print('Has lifespan:', hasattr(app, 'lifespan'))"

# Test MCP endpoint
curl http://localhost:8080/mcp
```

---

## 🌐 API/Endpoint Issues

### Issue: Swagger UI Not Loading

**Problem**: `/docs` endpoint returns blank page or error.

**Solutions**:

#### Check OpenAPI Schema

```bash
# Get and validate OpenAPI schema
curl -s http://localhost:8080/openapi.json | python -m json.tool > /dev/null

# If this fails, there's a schema issue
```

#### Fix Ellipsis (Most Common Cause)

Search and replace all ellipsis (`...`) in response examples:

```bash
# Find all ellipsis in Python files
grep -rn "\.\.\." backend/ --include="*.py"

# Replace with None or actual values
# ... in response examples -> None or actual dict
```

#### Check for Invalid Type Hints

```bash
# Use mypy to check type hints
pip install mypy
mypy backend/app.py --ignore-missing-imports
```

**Common Issues**:
- Using `list` instead of `list[str]` or `List[str]`
- Using `dict` instead of `dict[str, Any]`
- Mixing `Optional[X]` with `X | None`

### Issue: ReDoc Not Referencing Correct API

**Problem**: `/redoc` doesn't show MCP documentation correctly.

**Solution**: ReDoc and Swagger UI are automatically generated by FastAPI. The MCP-specific documentation is at:

- `/api/mcp/docs` - Full MCP documentation (JSON or HTML)
- `/api/mcp/info` - Server metadata
- `/docs` - Swagger UI (FastAPI default, includes all endpoints)
- `/redoc` - ReDoc (FastAPI default, includes all endpoints)

**Verification**:
```bash
# Check all documentation endpoints
curl http://localhost:8080/docs | head -20
curl http://localhost:8080/redoc | head -20
curl http://localhost:8080/api/mcp/docs | head -20
```

### Issue: OpenAPI Schema Generation Error

**Problem**: `/openapi.json` returns 500 error.

**Debugging Steps**:

```python
# Test OpenAPI generation directly
python -c "
from backend.app import app
try:
    schema = app.openapi()
    print('Schema generated successfully')
    print('Number of paths:', len(schema.get('paths', {})))
except Exception as e:
    print('Error generating schema:', e)
    import traceback
    traceback.print_exc()
"
```

**Common Solutions**:

1. **Fix ellipsis** in response examples
2. **Add proper type hints** to all Pydantic models
3. **Remove circular imports**
4. **Check for custom response classes** that might not be serializable

### Issue: CORS Issues

**Problem**: Browser blocks requests due to CORS policy.

**Solutions**:

#### Verify CORS Configuration

```python
# In backend/app.py
from fastapi.middleware.cors import CORSMiddleware

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Or specific origins
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Test CORS Headers

```bash
# Check CORS headers
curl -I -X OPTIONS http://localhost:8080/health \
  -H "Origin: http://example.com" \
  -H "Access-Control-Request-Method: GET"

# Look for: Access-Control-Allow-Origin, Access-Control-Allow-Methods
```

**Solution for Production**: Restrict to specific origins:

```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "http://localhost:3000",  # For local frontend development
]
```

---

## 🐳 Docker Issues

### Issue: Docker Build Fails

**Problem**: `docker build` command fails with error.

**Debugging Steps**:

```bash
# Get detailed error output
docker build -t unhcr-stat-copilot . --no-cache

# Or with progress output
docker build -t unhcr-stat-copilot . --progress=plain
```

**Common Causes and Solutions**:

| Error | Cause | Solution |
|-------|-------|----------|
| `COPY failed` | File not found | Check file paths in Dockerfile |
| `pip install failed` | Network issue | Check internet connection, use `--network=host` |
| `npm install failed` | Network issue | Same as above |
| `quarto check failed` | Quartz CLI issue | Check quarto installation in Dockerfile |
| `Dockerfile syntax error` | Invalid Dockerfile | Check Dockerfile syntax |

### Issue: Docker Container Fails to Start

**Problem**: Container starts but crashes immediately.

**Debugging Steps**:

```bash
# Check container logs
docker logs <container-id>

# Run container interactively
docker run -it --entrypoint /bin/sh unhcr-stat-copilot

# Check what's in the container
ls -la /app/
```

**Common Causes**:

#### Missing Required Files

```bash
# Check if required files exist
docker run --rm unhcr-stat-copilot ls /app/backend/
```

**Solution**: Ensure all files are copied in Dockerfile:

```dockerfile
COPY backend/ backend/
COPY frontend/ frontend/
```

#### Python Import Errors

```bash
# Test import in container
docker run --rm -it unhcr-stat-copilot python -c "from backend.app import app; print('OK')"
```

**Solution**: Check `PYTHONPATH` in Dockerfile:

```dockerfile
ENV PYTHONPATH=/app
```

#### Port Already in Use

```bash
# Check if port is available
netstat -tlnp | grep 8080

# Or
lsof -i :8080
```

**Solution**: Either stop the process using the port or change the port:

```bash
# Stop process using port 8080
kill $(lsof -t -i :8080)

# Or run on different port
docker run -p 8081:8080 unhcr-stat-copilot
```

### Issue: Docker Container Runs but Application Not Accessible

**Problem**: Container is running but can't access application.

**Debugging Steps**:

```bash
# Check if application is listening
docker exec <container-id> netstat -tlnp

# Check application logs
docker exec <container-id> cat /var/log/app.log 2>/dev/null || echo "No log file"

# Test from inside container
docker exec <container-id> curl -s http://localhost:8080/health
```

**Common Causes**:

#### Application Not Binding to 0.0.0.0

```bash
# Check what address application is binding to
docker exec <container-id> ps aux | grep -E "(python|gunicorn)"
```

**Solution**: Ensure application binds to `0.0.0.0`:

```python
# In boot.sh and backend/main.py
--bind 0.0.0.0:${PORT}
```

#### Port Mapping Incorrect

```bash
# Check port mapping
docker inspect <container-id> | grep -A 5 HostPort
```

**Solution**: Ensure port mapping is correct:

```bash
# Map external 8080 to internal 8080
docker run -p 8080:8080 unhcr-stat-copilot
```

### Issue: Docker Image Too Large

**Problem**: Docker image is too large for deployment.

**Debugging Steps**:

```bash
# Check image size
docker images | grep unhcr-stat-copilot

# Check layer sizes
docker history unhcr-stat-copilot
```

**Solutions**:

#### Clean Up Build Cache

```bash
# Remove unused images and containers
docker system prune -a

# Rebuild with clean cache
docker build --no-cache -t unhcr-stat-copilot .
```

#### Optimize Dockerfile

1. **Use multi-stage builds** (already implemented)
2. **Clean up apt cache**:

```dockerfile
RUN apt-get update && \
    apt-get install -y package && \
    rm -rf /var/lib/apt/lists/*
```

3. **Clean up pip cache**:

```dockerfile
RUN pip install --no-cache-dir package
```

4. **Use smaller base images**:

```dockerfile
FROM python:3.11-slim
# Instead of python:3.11
```

### Issue: Docker Volume Mount Issues

**Problem**: Changes to local files not reflected in container.

**Solutions**:

#### Ensure Volume Mounts Are Correct

```bash
# Check mount points
docker inspect <container-id> | grep -A 10 Mounts
```

**Correct Mount Command**:

```bash
docker run -v $(pwd)/backend:/app/backend -v $(pwd)/frontend:/app/frontend ...
```

#### Use Named Volumes

```bash
# Create named volume
docker volume create unhcr_backend

# Run with named volume
docker run -v unhcr_backend:/app/backend ...
```

#### Check File Permissions

```bash
# Ensure files are readable
chmod -R 755 backend/ frontend/

# Or in Dockerfile
RUN chmod -R 755 /app
```

---

## ☁️ Azure Deployment Issues

### Issue: Azure Health Check Fails

**Problem**: Azure marks application as unhealthy.

**Debugging Steps**:

```bash
# Check Azure health probe logs
az webapp log tail --name unhcr-stat-copilot --resource-group unhcr-copilot-rg

# Check health endpoint manually
curl https://unhcr-stat-copilot.azurewebsites.net/health
```

**Common Causes**:

#### Root Endpoint Not Returning 200

**Solution**: Ensure root endpoint returns HTTP 200:

```python
# In backend/app.py
@app.get("/")
async def read_root():
    return {
        "application": "UNHCR Stat Copilot",
        "version": "1.0.0",
        "status": "ok"
    }
```

#### Health Endpoint Returns Error

**Solution**: Check health endpoint implementation:

```python
# In backend/app.py
@app.get("/health")
async def health():
    return {
        "status": "ok",
        "service": "unhcr-statistics-copilot"
    }
```

#### MCP Endpoint 405 Error

This is the **most common Azure deployment issue** and has been **fixed in the latest commit**.

**Problem**: Azure sends POST requests to `/mcp` for health checks, but this causes conflicts with MCP protocol.

**Fix Applied**: The `/mcp` health check endpoints have been **removed**. 

**Important**: Azure health checks should be configured to use `/health` instead of `/mcp`.

**Verification**:
```bash
# Test health check endpoint
curl https://unhcr-stat-copilot.azurewebsites.net/health

# Test MCP endpoint (should redirect to /mcp/)
curl -i https://unhcr-stat-copilot.azurewebsites.net/mcp
```

### Issue: Azure Deployment Times Out

**Problem**: Deployment takes too long and times out.

**Common Causes**:
1. Slow internet connection
2. Large Docker image
3. Too many dependencies
4. Frontend build taking too long

**Solutions**:

#### Increase Timeout

```bash
# Azure has a default timeout of 230 seconds
# For longer builds, use Azure DevOps or GitHub Actions

# Or use --timeout flag with az webapp up
timeout 600 az webapp up --name unhcr-stat-copilot --resource-group unhcr-copilot-rg
```

#### Optimize Docker Build

1. **Use build cache**:

```bash
# Don't use --no-cache for production builds
docker build -t unhcr-stat-copilot .
```

2. **Pre-build frontend**:

```bash
# Build frontend before Docker build
cd frontend && npm run build
cd ..

# Then build Docker image (which will be faster)
docker build -t unhcr-stat-copilot .
```

#### Use Deployment Slots

```bash
# Create deployment slot
az webapp deployment slot create \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --slot staging

# Deploy to staging slot
az webapp deployment slot auto-swap \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --slot staging \
  --auto-swap-enabled true
```

### Issue: Azure Container Registry Issues

**Problem**: Issues pushing to or pulling from Azure Container Registry.

**Debugging Steps**:

```bash
# Check ACR login
az acr login --name <acr-name>

# Check image exists
az acr repository list --name <acr-name> --output table

# Check image tags
az acr repository show-tags --name <acr-name> --repository unhcr-stat-copilot --output table
```

**Solutions**:

#### Login to ACR

```bash
# Login to Azure Container Registry
az acr login --name <acr-name>

# Or use admin credentials
docker login <acr-name>.azurecr.io -u <username> -p <password>
```

#### Tag and Push Image Correctly

```bash
# Tag image for ACR
docker tag unhcr-stat-copilot:latest <acr-name>.azurecr.io/unhcr-stat-copilot:latest

# Push to ACR
docker push <acr-name>.azurecr.io/unhcr-stat-copilot:latest
```

#### Configure Web App to Use ACR

```bash
az webapp config container set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --docker-custom-image-name <acr-name>.azurecr.io/unhcr-stat-copilot:latest \
  --docker-registry-server-url https://<acr-name>.azurecr.io \
  --docker-registry-server-username <username> \
  --docker-registry-server-password <password>
```

### Issue: Azure "405 Method Not Allowed" or JSON-RPC Parsing Errors on `/mcp`

**Problem**: Azure logs show: `HTTP Request: POST https://.../mcp "HTTP/1.1 405 Method Not Allowed"` or MCP clients fail with JSON-RPC validation errors.

**Root Cause**: There was a conflict between:
1. Direct `/mcp` endpoints that returned plain JSON for health checks
2. The FastMCP mount at `/mcp` that expected JSON-RPC protocol

The direct endpoints were intercepting requests and returning non-JSON-RPC responses, which broke MCP clients.

**Fix Applied in Latest Commit**: The `/mcp` health check endpoints have been **removed** to avoid conflicts. Requests to `/mcp` are now automatically redirected to `/mcp/` where the FastMCP server handles them properly.

**Important**: Azure health checks should be configured to use `/health` instead of `/mcp`.

**Verification for Azure**:
```bash
# Test health check endpoint (use this for Azure health checks)
curl https://unhcr-stat-copilot.azurewebsites.net/health
# Should return: {"status": "healthy", ...}

# Test MCP endpoint (should redirect to /mcp/)
curl -i https://unhcr-stat-copilot.azurewebsites.net/mcp
# Should return: 307 Temporary Redirect to /mcp/

# Test actual MCP tool execution (requires MCP client)
# MCP clients will follow the redirect and work properly
```

### Issue: Azure WEBSITES_PORT Configuration

**Problem**: Application not accessible on Azure.

**Root Cause**: Azure App Service sets `WEBSITES_PORT` environment variable, but application is not configured to use it.

**Solution**: The `boot.sh` script already handles this:

```bash
# From boot.sh
if [ -n "${WEBSITES_PORT:-}" ]; then
    BIND_PORT="${WEBSITES_PORT}"
else
    BIND_PORT="8080"
fi
```

**Verification**:
```bash
# Check WEBSITES_PORT is set
az webapp config appsettings list \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  | grep WEBSITES_PORT

# Set if not present
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings WEBSITES_PORT=8080
```

---

## 💻 Frontend Issues

### Issue: Frontend Not Loading

**Problem**: Frontend returns blank page or 404.

**Debugging Steps**:

```bash
# Check if frontend files exist
ls -la frontend/dist/

# Check if frontend is mounted
curl http://localhost:8080/ | grep -i "html\|react\|div"
```

**Solutions**:

#### Rebuild Frontend

```bash
cd frontend
npm run build
cd ..
```

#### Check Frontend Mount in backend/main.py

```python
# In backend/main.py
from fastapi.staticfiles import StaticFiles
import os

frontend_dist_path = "/app/frontend/dist"
if os.path.exists(frontend_dist_path):
    app.mount("/", StaticFiles(directory=frontend_dist_path, html=True), name="frontend")
```

**Verification**:
```bash
# Check if frontend files are being served
curl http://localhost:8080/ | head -5
# Should return HTML
```

### Issue: Frontend API Requests Fail

**Problem**: Frontend can't connect to backend API.

**Debugging Steps**:

```bash
# Check CORS headers
curl -I -X OPTIONS http://localhost:8080/chat \
  -H "Origin: http://localhost:3000" \
  -H "Access-Control-Request-Method: POST"

# Check if backend is running
curl http://localhost:8080/health
```

**Solutions**:

#### Configure CORS Properly

```python
# In backend/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://localhost:3000",  # Vite dev server
        "http://localhost:5173",  # Vite default
        "http://localhost:8080",  # For when served from backend
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

#### Check Frontend API Base URL

```jsx
// In frontend/src/services/api.js
const API_BASE_URL = window.location.origin || 'http://localhost:8080';

// Or for development
const API_BASE_URL = import.meta.env.MODE === 'development' 
  ? 'http://localhost:8080' 
  : window.location.origin;
```

### Issue: Frontend Build Fails

**Problem**: `npm run build` fails.

**Debugging Steps**:

```bash
# Get detailed error
cd frontend
npm run build 2>&1 | tail -50

# Check Node.js version
node --version

# Check npm version
npm --version
```

**Common Solutions**:

#### Clear node_modules and Reinstall

```bash
cd frontend
rm -rf node_modules package-lock.json
npm cache clean --force
npm install
```

#### Check for Syntax Errors

```bash
# Run TypeScript check
npx tsc --noEmit

# Run ESLint
npx eslint src/
```

#### Update Dependencies

```bash
cd frontend
npm update
npm run build
```

---

## 🔐 Authentication Issues

### Issue: Authentication Required But Not Configured

**Problem**: API returns 401 Unauthorized.

**Current State**: The API is open and does not require authentication by default.

**Solutions**:

#### Disable Authentication (Development)

```python
# In backend/app.py
from backend.auth import get_optional_user

# Use get_optional_user instead of verify_azure_auth
@app.post("/tool")
async def execute_tool(
    request: Request,
    tool_request: ToolRequest,
    user: UserInfo = Depends(get_optional_user)  # Changed from verify_azure_auth
):
    ...
```

#### Enable Azure AD Authentication (Production)

```python
# In backend/app.py
from backend.auth import verify_azure_auth

@app.post("/tool")
async def execute_tool(
    request: Request,
    tool_request: ToolRequest,
    user: UserInfo = Depends(verify_azure_auth)
):
    ...
```

Configure in Azure:

```bash
az webapp auth config set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --action LoginWithAzureActiveDirectory \
  --aad-client-id <client-id> \
  --aad-client-secret <client-secret> \
  --aad-tenant-id <tenant-id>
```

### Issue: Azure AD Configuration Missing

**Problem**: Azure AD authentication fails.

**Debugging Steps**:

```bash
# Check environment variables
az webapp config appsettings list \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg

# Check Azure AD configuration
az webapp auth config show \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg
```

**Solutions**:

#### Set Azure AD Environment Variables

```bash
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings AZURE_CLIENT_ID=<client-id> \
           AZURE_CLIENT_SECRET=<client-secret> \
           AZURE_TENANT_ID=<tenant-id>
```

#### Verify Azure AD App Registration

1. Go to Azure Portal > Azure Active Directory > App registrations
2. Find your application
3. Check "Redirect URIs" include: `https://<app-name>.azurewebsites.net/.auth/login/aad/callback`
4. Check "API permissions" are configured
5. Check "Certificates & secrets" has a client secret

---

## ⚡ Performance Issues

### Issue: Slow API Response

**Problem**: API endpoints are slow to respond.

**Debugging Steps**:

```bash
# Measure response time
curl -w "\nTime: %{time_total}s\n" http://localhost:8080/health

# Profile endpoint
python -c "
import time
import requests

start = time.time()
r = requests.get('http://localhost:8080/tools')
elapsed = time.time() - start
print(f'Response time: {elapsed:.3f}s')
"
```

**Solutions**:

#### Check External API Calls

```python
# Add timing to external API calls
import time

async def call_unhcr_api(endpoint, **kwargs):
    start = time.time()
    result = await actual_call(endpoint, **kwargs)
    elapsed = time.time() - start
    logger.info(f"UNHCR API {endpoint} took {elapsed:.3f}s")
    return result
```

#### Optimize MCP Tool Execution

```python
# In backend/mcp_bridge.py
import time

async def call_tool(tool_name: str, arguments: dict) -> dict:
    start = time.time()
    try:
        result = await tool_function(**arguments)
        elapsed = time.time() - start
        logger.info(f"Tool {tool_name} executed in {elapsed:.3f}s")
        return result
    except Exception as e:
        elapsed = time.time() - start
        logger.error(f"Tool {tool_name} failed after {elapsed:.3f}s: {e}")
        raise
```

#### Add Caching for Non-Real-Time Data

```python
# In backend/mcp/tools/get_population_data.py
from functools import lru_cache
import asyncio

# Cache results for 5 minutes
@lru_cache(maxsize=100)
async def cached_get_population_data(coo: str, coa: str, year: int):
    return await get_population_data(coo, coa, year)
```

### Issue: High Memory Usage

**Problem**: Application uses too much memory.

**Debugging Steps**:

```bash
# Check memory usage
ps aux | grep python | grep -v grep

# Docker memory usage
docker stats <container-id>

# Python memory profiling
pip install memory-profiler
python -m memory_profiler -m backend.main
```

**Solutions**:

#### Reduce Gunicorn Workers

```bash
# In boot.sh
WEB_CONCURRENCY=1 ./boot.sh  # Instead of 2

# Or
WEB_CONCURRENCY=2 ./boot.sh  # Maximum recommended for most deployments
```

#### Optimize Data Structures

Avoid loading large datasets into memory:

```python
# Bad: Load all data at once
all_data = await get_all_population_data()

# Good: Use generators or pagination
async for data in get_population_data_paginated():
    process(data)
```

### Issue: Rate Limiting Too Strict

**Problem**: Users get rate limited too often.

**Solutions**:

#### Adjust Rate Limits

```python
# In backend/app.py
RATE_LIMIT_ENABLED = os.getenv("RATE_LIMIT_ENABLED", "true").lower() == "true"

limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED
)

# Per-endpoint limits
@app.post("/tool")
@limiter.limit("20/minute")  # Increased from 10
async def execute_tool(...):
    ...
```

#### Disable Rate Limiting (Development)

```bash
RATE_LIMIT_ENABLED=false python -m backend.main

# Or in Docker
docker run -p 8080:8080 -e RATE_LIMIT_ENABLED=false unhcr-stat-copilot
```

---

## 🌐 Network/Connectivity Issues

### Issue: Cannot Connect to UNHCR API

**Problem**: Tools that call UNHCR API fail.

**Debugging Steps**:

```bash
# Test UNHCR API directly
curl -v "https://api.unhcr.org/population/v1/population/get?coo=SYR&coa=TUR&year=2024" 2>&1 | tail -20

# Check DNS resolution
nslookup api.unhcr.org

# Check network connectivity
ping api.unhcr.org
```

**Solutions**:

#### Check Network Configuration

```python
# In Dockerfile or deployment
# Ensure network tools are available
RUN apt-get update && apt-get install -y curl wget dnsutils
```

#### Configure Proxy (If Needed)

```bash
# Set HTTP proxy
export HTTP_PROXY=http://proxy.example.com:8080
export HTTPS_PROXY=http://proxy.example.com:8080

# Or in Docker
docker run -e HTTP_PROXY=http://proxy.example.com:8080 ...
```

### Issue: DNS Resolution Fails

**Problem**: DNS lookup times out.

**Debugging Steps**:

```bash
# Test DNS resolution
nslookup google.com
dig google.com
cat /etc/resolv.conf
```

**Solutions**:

#### Use Specific DNS Servers

```bash
# In Docker
docker run --dns 8.8.8.8 --dns 8.8.4.4 ...

# In Dockerfile
# Add to Dockerfile
RUN echo "nameserver 8.8.8.8" > /etc/resolv.conf
```

---

## 💾 Data/Database Issues

### Issue: Analysis History Not Saved

**Problem**: Analysis results are not persisted.

**Debugging Steps**:

```bash
# Check if database file exists
ls -la backend/*.db

# Check history endpoint
curl http://localhost:8080/history
```

**Solutions**:

#### Check Database Configuration

```python
# In backend/history.py
import sqlite3

# Check database path
DATABASE_PATH = "backend/history.db"

# Ensure directory exists
import os
os.makedirs(os.path.dirname(DATABASE_PATH), exist_ok=True)

# Connect to database
conn = sqlite3.connect(DATABASE_PATH)
```

#### Verify File Permissions

```bash
# Check file permissions
ls -la backend/history.db

# Ensure writable
chmod 666 backend/history.db
```

### Issue: Database Locked

**Problem**: Database is locked, cannot write.

**Debugging Steps**:

```bash
# Check for locked database
lsof backend/history.db
```

**Solutions**:

#### Use WAL Mode (Write-Ahead Logging)

```python
# In backend/history.py
conn = sqlite3.connect(DATABASE_PATH)
conn.execute("PRAGMA journal_mode=WAL")
```

#### Increase Timeout

```python
# In backend/history.py
conn = sqlite3.connect(DATABASE_PATH, timeout=30)  # 30 seconds timeout
```

---

## 📦 Dependency Issues

### Issue: Missing Python Dependencies

**Problem**: `ModuleNotFoundError` when importing.

**Debugging Steps**:

```bash
# Check installed packages
pip list

# Check if package is in requirements.txt
grep <package-name> backend/requirements.txt
```

**Solutions**:

#### Install Missing Package

```bash
pip install <package-name>

# Add to requirements.txt
pip freeze > backend/requirements.txt
```

#### Check for Version Conflicts

```bash
# Check package versions
pip show <package-name>

# Try specific version
pip install <package-name>==x.y.z
```

### Issue: Incompatible Package Versions

**Problem**: Version conflicts between packages.

**Debugging Steps**:

```bash
# Check for conflicts
pip check

# Check dependency tree
pipdeptree

# Or
pip install pipdeptree && pipdeptree
```

**Solutions**:

#### Use Compatible Versions

```bash
# Find compatible versions
pip install <package1>==x.y.z <package2>==a.b.c

# Or use pip-tools
pip-compile requirements.in
```

#### Use Virtual Environment

```bash
# Create fresh virtual environment
python -m venv venv --clear

# Activate and reinstall
source venv/bin/activate
pip install -r backend/requirements.txt
```

---

## 🧪 Testing Issues

### Issue: Tests Fail

**Problem**: pytest tests fail.

**Debugging Steps**:

```bash
# Run tests with verbose output
pytest -v

# Run with traceback
pytest -v --tb=short

# Run specific test
pytest tests/test_mcp.py::test_specific_function -v
```

**Solutions**:

#### Check Test Dependencies

```bash
# Ensure test dependencies are installed
pip install pytest pytest-asyncio httpx
```

#### Fix Test Configuration

```python
# In tests/conftest.py
import pytest
from fastapi.testclient import TestClient
from backend.app import app

@pytest.fixture
def client():
    return TestClient(app)

@pytest.fixture
def mock_external_api():
    # Mock external API calls
    pass
```

#### Update Test Data

```python
# In your test file
def test_something():
    # Use realistic test data
    test_data = {"coo": "SYR", "coa": "TUR", "year": 2024}
    
    # Instead of
    test_data = {"key": "..."}  # Ellipsis causes issues!
```

---

## 📋 Log Analysis

### Understanding Log Output

#### Backend Logs

```
# Format: timestamp - module - level - message
2026-07-07 12:00:00,123 - backend.app - INFO - Starting server
2026-07-07 12:00:00,456 - backend.mcp_bridge - DEBUG - Calling tool: get_population_data
2026-07-07 12:00:01,234 - backend.mcp_bridge - ERROR - Tool execution failed: ConnectionError
```

**Log Levels**:
- DEBUG: Detailed debugging information
- INFO: General information
- WARNING: Potential issues
- ERROR: Serious problems
- CRITICAL: Critical errors

#### Azure Logs

```bash
# Get Azure logs
az webapp log tail --name unhcr-stat-copilot --resource-group unhcr-copilot-rg

# Filter for errors
grep -i error logs.txt

# Filter for specific module
grep mcp logs.txt
```

#### Docker Logs

```bash
# Get container logs
docker logs <container-id>

# Follow logs
docker logs -f <container-id>

# Get logs with timestamps
docker logs -t <container-id>

# Save to file
docker logs <container-id> > docker.log 2>&1
```

### Common Log Patterns

| Pattern | Meaning | Action |
|---------|---------|--------|
| `ModuleNotFoundError: No module named X` | Missing Python package | Install package |
| `ConnectionError: Failed to connect` | External API unavailable | Check network, retry |
| `KeyError: 'key'` | Dictionary key missing | Add default value or check data |
| `TypeError: 'NoneType' object is not subscriptable` | Variable is None | Add null check |
| `asyncio.TimeoutError` | Request timed out | Increase timeout |
| `405 Method Not Allowed` | Wrong HTTP method | Use correct method |
| `404 Not Found` | Endpoint doesn't exist | Check URL |

---

## ✅ Self-Help Checklist

Before asking for help, go through this checklist:

### [ ] Application Basics
- [ ] Is the application running? (`ps aux | grep python`)
- [ ] Is the port correct? (`netstat -tlnp | grep 8080`)
- [ ] Does `/health` return 200? (`curl http://localhost:8080/health`)
- [ ] Does `/` return 200? (`curl http://localhost:8080/`)

### [ ] MCP Server
- [ ] Does `/mcp` return 200 for GET? (`curl http://localhost:8080/mcp`)
- [ ] Does `/mcp` return 200 for POST? (`curl -X POST http://localhost:8080/mcp -d '{}'`)
- [ ] Are tools available? (`curl http://localhost:8080/tools`)
- [ ] Does `/api/mcp/docs` work? (`curl http://localhost:8080/api/mcp/docs`)

### [ ] Documentation
- [ ] Does `/docs` load in browser? (Swagger UI)
- [ ] Does `/redoc` load in browser? (ReDoc)
- [ ] Does `/openapi.json` return valid JSON? (`curl -s http://localhost:8080/openapi.json | python -m json.tool`)

### [ ] External Dependencies
- [ ] Are all Python packages installed? (`pip list`)
- [ ] Are all Node.js packages installed? (`npm list`)
- [ ] Is Docker running? (`docker ps`)
- [ ] Are environment variables set? (`printenv | grep -E "(PORT|WEBSITES)"`)

### [ ] Network
- [ ] Can you access external APIs? (`curl -v https://api.unhcr.org`)
- [ ] Is DNS working? (`nslookup google.com`)
- [ ] Are ports open? (`telnet localhost 8080`)

### [ ] Common Issues
- [ ] No ellipsis (`...`) in response examples
- [ ] All tools registered in `MCP_TOOL_SCHEMAS`
- [ ] MCP server lifespan configured
- [ ] CORS configured properly
- [ ] Rate limiting configured
- [ ] Port binding correct (0.0.0.0:PORT)

---

## 🆘 Getting Help

If you've gone through the self-help checklist and are still having issues:

### 1. Gather Information

Before asking for help, collect:
- Error message (full text)
- Steps to reproduce
- Expected behavior
- Actual behavior
- Screenshots (if UI issue)
- Logs (relevant portions)
- Environment info (OS, versions, etc.)

### 2. Search Existing Issues

```bash
# Search GitHub issues
gh issue list | grep -i "your error"

# Or search in browser
# Go to: https://github.com/<org>/<repo>/issues?q=your+error
```

### 3. Create a New Issue

When creating a new issue, include:

```markdown
## Description
Brief description of the problem.

## Steps to Reproduce
1. Step 1
2. Step 2
3. Step 3

## Expected Behavior
What should happen.

## Actual Behavior
What actually happens.

## Error Message
```
Full error message here
```

## Environment
- OS: [Windows/macOS/Linux]
- Python version: 3.x
- Node.js version: 20.x
- Docker version: x.x.x
- Deployment: [local/Docker/Azure/other]

## Additional Information
Any other relevant information.

## Self-Help Checklist
- [x] I checked the application is running
- [x] I checked the logs
- [x] I searched existing issues
- [x] I tried the suggested solutions
```

### 4. Ask for Help

You can ask for help in:
- GitHub Discussions
- Slack/Teams channel (if available)
- Email the development team
- Stack Overflow (tag with appropriate tags)

---

## 📚 See Also

- [README.md](./README.md) - Main documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - API reference
- [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) - MCP integration guide
- [DEPLOYMENT.md](./DEPLOYMENT.md) - Deployment guide
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup

---

*Last updated: July 7, 2026*
