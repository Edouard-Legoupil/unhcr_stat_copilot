# Deployment Guide

Complete deployment documentation for the UNHCR Statistics Copilot on Docker, Azure, and other platforms.

## 📚 Table of Contents

- [Deployment Options](#deployment-options)
- [Docker Deployment](#docker-deployment)
  - [Quick Start](#quick-start)
  - [Configuration](#configuration)
  - [Custom Docker Build](#custom-docker-build)
  - [Docker Compose](#docker-compose)
- [Azure Deployment](#azure-deployment)
  - [Azure App Service](#azure-app-service)
  - [Azure Container Apps](#azure-container-apps)
  - [Azure Container Instances](#azure-container-instances)
  - [Azure Kubernetes Service (AKS)](#azure-kubernetes-service-aks)
- [Local Development Deployment](#local-development-deployment)
- [Kubernetes Deployment](#kubernetes-deployment)
- [Environment Variables](#environment-variables)
- [Port Configuration](#port-configuration)
- [SSL/TLS Configuration](#ssltls-configuration)
- [Health Checks](#health-checks)
- [Monitoring & Logging](#monitoring--logging)
- [Security Considerations](#security-considerations)
- [Performance Tuning](#performance-tuning)
- [CI/CD Pipeline](#cicd-pipeline)
- [Troubleshooting Deployment Issues](#troubleshooting-deployment-issues)

---

## 🎯 Deployment Options

The UNHCR Statistics Copilot can be deployed on multiple platforms:

| Platform | Type | Recommended For | Complexity | Cost |
|----------|------|----------------|------------|------|
| [Docker](#docker-deployment) | Container | Local development, Testing | ⭐ | Free |
| [Azure App Service](#azure-app-service) | PaaS | Production (Simple) | ⭐⭐ | Low-Medium |
| [Azure Container Apps](#azure-container-apps) | CaaS | Production (Container-native) | ⭐⭐⭐ | Medium |
| [Azure Container Instances](#azure-container-instances) | Serverless | Testing, Temporary | ⭐⭐ | Low |
| [Kubernetes](#kubernetes-deployment) | Orchestration | Production (Scale) | ⭐⭐⭐⭐ | Medium-High |
| [Local Python](#local-development-deployment) | Direct | Development | ⭐ | Free |

**Recommendation**: Use **Azure App Service** for production deployments due to its simplicity and built-in features. Use **Docker** for local development and testing.

---

## 🐳 Docker Deployment

### Quick Start

The fastest way to deploy the UNHCR Statistics Copilot is using Docker.

#### Prerequisites
- Docker installed and running
- Docker CLI available
- Minimum 2GB RAM recommended for container

#### Build and Run

```bash
# Clone the repository (if not already done)
git clone <repository-url>
cd unhcr_stat_copilot

# Build the Docker image
docker build -t unhcr-stat-copilot .

# Run the container
docker run -p 8080:8080 -e PORT=8080 unhcr-stat-copilot
```

The application will be available at `http://localhost:8080`

#### Docker Build Details

The Dockerfile uses a **multi-stage build** to optimize the final image:

1. **Stage 1 (frontend-builder)**: Uses Node.js 20 to build the React frontend
2. **Stage 2 (final)**: Uses Python 3.11 slim with all dependencies

This approach reduces the final image size and improves security by not including Node.js in production.

### Configuration

#### Environment Variables

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| `PORT` | Application port | 8080 | No |
| `WEBSITES_PORT` | Azure-specific port | - | No |
| `WEB_CONCURRENCY` | Gunicorn worker count | 2 | No |
| `RATE_LIMIT_ENABLED` | Enable rate limiting | true | No |
| `LOG_LEVEL` | Logging verbosity | info | No |

#### Docker Run with Custom Configuration

```bash
# With custom port
docker run -p 9000:9000 -e PORT=9000 unhcr-stat-copilot

# With custom workers
docker run -p 8080:8080 -e PORT=8080 -e WEB_CONCURRENCY=4 unhcr-stat-copilot

# With rate limiting disabled (not recommended for production)
docker run -p 8080:8080 -e RATE_LIMIT_ENABLED=false unhcr-stat-copilot

# With debug logging
docker run -p 8080:8080 -e LOG_LEVEL=debug unhcr-stat-copilot
```

### Custom Docker Build

#### Using Build Arguments

```bash
# Build with custom Python version
docker build --build-arg PYTHON_VERSION=3.11-slim -t unhcr-stat-copilot .
```

#### Multi-Architecture Builds

For ARM-based systems (Apple Silicon, Raspberry Pi, etc.):

```bash
# Build for ARM64
docker build --platform linux/arm64 -t unhcr-stat-copilot-arm64 .

# Build for multiple platforms
docker buildx build --platform linux/amd64,linux/arm64 -t unhcr-stat-copilot --push .
```

### Docker Compose

For more complex deployments with multiple services:

```yaml
# docker-compose.yml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "8080:8080"
    environment:
      - PORT=8080
      - WEB_CONCURRENCY=2
      - RATE_LIMIT_ENABLED=true
      - LOG_LEVEL=info
    volumes:
      - ./data:/app/data
    restart: unless-stopped
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:8080/health"]
      interval: 30s
      timeout: 10s
      retries: 3

  # Optional: Add a reverse proxy
  nginx:
    image: nginx:alpine
    ports:
      - "80:80"
      - "443:443"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app
```

Start with:
```bash
docker-compose up -d
```

---

## ☁️ Azure Deployment

### Azure App Service

**Recommended** for production deployments due to its simplicity and managed infrastructure.

#### Prerequisites
- Azure account with contributor permissions
- Azure CLI installed (`az`)
- GitHub account (for CI/CD)

#### Step 1: Create Azure Resources

```bash
# Login to Azure
az login

# Set your subscription
az account set --subscription "Your-Subscription-Name"

# Create a resource group
az group create --name unhcr-copilot-rg --location swedencentral

# Create App Service plan (Free tier for testing)
az appservice plan create \
  --name unhcr-copilot-plan \
  --resource-group unhcr-copilot-rg \
  --sku F1 \
  --is-linux

# Create the web app
az webapp create \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --plan unhcr-copilot-plan \
  --runtime "PYTHON:3.11" \
  --os-type Linux \
  --startup-file "gunicorn backend.main:app --bind 0.0.0.0:$PORT --workers 2 --worker-class uvicorn.workers.UvicornWorker"
```

#### Step 2: Configure Application Settings

```bash
# Set port configuration
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings WEBSITES_PORT=8080

# Set other configuration
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings WEB_CONCURRENCY=2

az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings RATE_LIMIT_ENABLED=true
```

#### Step 3: Enable Container Deployment

For container-based deployment:

```bash
# Configure container registry
az webapp config container set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --docker-custom-image-name <your-dockerhub-username>/unhcr-stat-copilot:latest \
  --docker-registry-server-url https://index.docker.io

# If using Azure Container Registry
az webapp config container set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --docker-custom-image-name <acr-name>.azurecr.io/unhcr-stat-copilot:latest \
  --docker-registry-server-url https://<acr-name>.azurecr.io \
  --docker-registry-server-username <username> \
  --docker-registry-server-password <password>
```

#### Step 4: Deploy Using Azure CLI

```bash
# Deploy from local directory (Azurite CLI)
az webapp up \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --sku F1 \
  --runtime "PYTHON:3.11"
```

#### Step 5: Configure Custom Domain (Optional)

```bash
# Create a CNAME record pointing to your-app.azurewebsites.net
# Then configure in Azure:

az webapp config hostname add \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --hostname copilot.yourdomain.com

# Configure SSL certificate (requires Azure App Service Certificate)
az webapp config ssl create \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --certificate-name copilot-cert \
  --certificate-password <password> \
  --server-farm-id /subscriptions/.../serverFarms/unhcr-copilot-plan
```

### Azure Container Apps

For container-native deployments with better scaling:

```bash
# Create Container Apps environment
az containerapp env create \
  --name unhcr-copilot-env \
  --resource-group unhcr-copilot-rg \
  --location swedencentral

# Create the container app
az containerapp create \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --environment unhcr-copilot-env \
  --image <your-dockerhub-username>/unhcr-stat-copilot:latest \
  --target-port 8080 \
  --ingress external \
  --cpu 1 \
  --memory 2Gi \
  --min-replicas 1 \
  --max-replicas 3

# Update configuration
az containerapp update \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --set-env-vars "PORT=8080 WEB_CONCURRENCY=2 RATE_LIMIT_ENABLED=true"
```

### Azure Container Instances

For temporary or test deployments:

```bash
# Create a container instance
az container create \
  --name unhcr-stat-copilot-test \
  --resource-group unhcr-copilot-rg \
  --image <your-dockerhub-username>/unhcr-stat-copilot:latest \
  --ports 8080 \
  --ip-address Public \
  --dns-name-label unhcr-copilot-test \
  --environment-variables PORT=8080 \
  --cpu 1 \
  --memory 2

# The app will be available at: http://unhcr-copilot-test.swedencentral.azurecontainer.io:8080
```

### Azure Kubernetes Service (AKS)

For large-scale deployments:

```yaml
# deployment.yaml
apiVersion: apps/v1
kind: Deployment
metadata:
  name: unhcr-stat-copilot
  labels:
    app: unhcr-stat-copilot
spec:
  replicas: 3
  selector:
    matchLabels:
      app: unhcr-stat-copilot
  template:
    metadata:
      labels:
        app: unhcr-stat-copilot
    spec:
      containers:
      - name: unhcr-stat-copilot
        image: <your-dockerhub-username>/unhcr-stat-copilot:latest
        ports:
        - containerPort: 8080
        env:
        - name: PORT
          value: "8080"
        - name: WEB_CONCURRENCY
          value: "2"
        - name: RATE_LIMIT_ENABLED
          value: "true"
        resources:
          requests:
            cpu: "500m"
            memory: "1Gi"
          limits:
            cpu: "1"
            memory: "2Gi"
        livenessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 30
          periodSeconds: 10
        readinessProbe:
          httpGet:
            path: /health
            port: 8080
          initialDelaySeconds: 5
          periodSeconds: 5
---
apiVersion: v1
kind: Service
metadata:
  name: unhcr-stat-copilot
spec:
  selector:
    app: unhcr-stat-copilot
  ports:
  - protocol: TCP
    port: 80
    targetPort: 8080
  type: LoadBalancer
```

Apply with:
```bash
kubectl apply -f deployment.yaml
```

---

## 💻 Local Development Deployment

### Using boot.sh

The project includes a comprehensive startup script for local development:

```bash
# Make boot.sh executable
chmod +x boot.sh

# Run with default settings (port 8000)
./boot.sh

# Run with custom port
PORT=9000 ./boot.sh

# Run with debug logging
LOG_LEVEL=debug ./boot.sh
```

The `boot.sh` script:
- Detects Azure environment or local deployment
- Configures port automatically
- Starts SSH server (for Azure tunnel)
- Launches Gunicorn with Uvicorn workers
- Provides health check information
- Shows all documentation endpoints

### Direct Python Execution

```bash
# Using uvicorn directly (development mode)
python -m backend.main

# With custom port
python -m backend.main --port 9000

# With Gunicorn (production mode)
gunicorn backend.main:app --bind 0.0.0.0:8080 --workers 2 --worker-class uvicorn.workers.UvicornWorker

# With auto-reload (development)
gunicorn backend.main:app --bind 0.0.0.0:8080 --workers 1 --reload --worker-class uvicorn.workers.UvicornWorker
```

### Verifying Local Deployment

```bash
# Check health
curl http://localhost:8080/health

# Check root endpoint
curl http://localhost:8080/

# Check MCP server
curl http://localhost:8080/mcp

# Check MCP documentation
curl http://localhost:8080/api/mcp/docs

# Check tool list
curl http://localhost:8080/tools

# Access Swagger UI
# Open http://localhost:8080/docs in browser

# Access ReDoc
# Open http://localhost:8080/redoc in browser
```

---

## 🌐 Kubernetes Deployment

### Prerequisites
- Kubernetes cluster (Minikube, Kind, AKS, EKS, GKE, etc.)
- kubectl configured
- Helm (optional)

### Basic Deployment

See the [AKS deployment](#azure-kubernetes-service-aks) section for a complete example.

### Helm Chart

For easier Kubernetes deployments, you can use Helm:

```bash
# Create a Helm chart
helm create unhcr-stat-copilot

# Edit values.yaml
# deployment:
#   image: your-dockerhub-username/unhcr-stat-copilot:latest
#   port: 8080
#   env:
#     PORT: 8080
#     WEB_CONCURRENCY: 2
#   replicas: 3
#   resources:
#     requests:
#       cpu: 500m
#       memory: 1Gi
#     limits:
#       cpu: 1
#       memory: 2Gi

# Deploy
helm install unhcr-stat-copilot ./unhcr-stat-copilot

# Upgrade
helm upgrade unhcr-stat-copilot ./unhcr-stat-copilot

# Uninstall
helm uninstall unhcr-stat-copilot
```

---

## ⚙️ Environment Variables

### Complete Environment Variable Reference

| Variable | Description | Default | Required |
|----------|-------------|---------|----------|
| **Application** |
| `PORT` | Port to bind the application to | 8000 | No |
| `WEBSITES_PORT` | Azure App Service port override | - | No |
| `WEB_CONCURRENCY` | Number of Gunicorn workers | 2 | No |
| `RATE_LIMIT_ENABLED` | Enable/disable rate limiting | true | No |
| `LOG_LEVEL` | Logging level (debug, info, warning, error) | info | No |
| **MCP Server** |
| `MCP_SERVER_URL` | Base URL for MCP server | http://localhost:8000/mcp/ | No |
| `MCP_TIMEOUT_SECONDS` | MCP request timeout | 30 | No |
| `MCP_MAX_RETRIES` | Maximum MCP retry attempts | 3 | No |
| **Authentication** |
| `AZURE_CLIENT_ID` | Azure AD client ID | - | No |
| `AZURE_CLIENT_SECRET` | Azure AD client secret | - | No |
| `AZURE_TENANT_ID` | Azure AD tenant ID | - | No |
| **CORS** |
| `ALLOWED_ORIGINS` | Comma-separated allowed origins | * | No |
| **Database/Storage** |
| `STORAGE_ACCOUNT` | Azure Storage account name | - | No |
| `STORAGE_KEY` | Azure Storage access key | - | No |

### Setting Environment Variables

#### Docker

```bash
# Run with environment variables
docker run -p 8080:8080 \
  -e PORT=8080 \
  -e WEB_CONCURRENCY=4 \
  -e RATE_LIMIT_ENABLED=true \
  -e LOG_LEVEL=debug \
  unhcr-stat-copilot

# Using .env file
echo "PORT=8080" > .env
echo "WEB_CONCURRENCY=4" >> .env

# Then mount it
docker run -p 8080:8080 --env-file .env unhcr-stat-copilot
```

#### Azure App Service

```bash
# Set single environment variable
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings PORT=8080

# Set multiple environment variables
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings WEB_CONCURRENCY=2 RATE_LIMIT_ENABLED=true LOG_LEVEL=info
```

#### Kubernetes

```yaml
# In your deployment.yaml
env:
- name: PORT
  value: "8080"
- name: WEB_CONCURRENCY
  value: "2"
- name: RATE_LIMIT_ENABLED
  value: "true"
- name: LOG_LEVEL
  value: "info"
```

---

## 🎯 Port Configuration

### Important: Port Binding

The application **must** bind to the port specified in the `PORT` or `WEBSITES_PORT` environment variable. Azure and other platforms use this for routing.

#### Docker

```bash
# The container port must match the internal application port
docker run -p 8080:8080 -e PORT=8080 unhcr-stat-copilot

# If you want external port 80 to map to internal 8080
docker run -p 80:8080 -e PORT=8080 unhcr-stat-copilot
```

#### Azure App Service

Azure automatically sets `WEBSITES_PORT` for container deployments. Your application **must** listen on this port:

```bash
# In boot.sh, the port is automatically detected from WEBSITES_PORT
# If WEBSITES_PORT is not set, it falls back to PORT, then to 8080

# Ensure your application binds to 0.0.0.0:PORT (not 127.0.0.1)
# This is already configured in boot.sh
```

#### Azure Container Apps

```bash
# Specify target-port in the container app configuration
target-port: 8080  # Must match the PORT your app listens on
```

### Troubleshooting Port Issues

**Problem**: Azure returns "HTTP Request: POST https://.../mcp HTTP/1.1 405 Method Not Allowed"

**Solution**: This is typically caused by:
1. **Port mismatch**: Your app is not listening on the expected port
2. **Health check failing**: Azure health probes expect HTTP 200 on `/` or `/health`

**Fix**:
```bash
# Verify your app is listening on the correct port
docker run -p 8080:8080 -e PORT=8080 unhcr-stat-copilot

# Check health endpoint
curl http://localhost:8080/health

# Check root endpoint
curl http://localhost:8080/

# Check MCP endpoint
curl http://localhost:8080/mcp
```

Ensure all return HTTP 200 with valid JSON responses.

---

## 🔒 SSL/TLS Configuration

### Azure App Service (Automatic)

Azure App Service automatically provides SSL certificates for `*.azurewebsites.net` domains. For custom domains, use:

```bash
# Create SSL binding
az webapp config ssl bind \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --certificate-thumbprint <thumbprint> \
  --ssl-type SNI
```

### Docker with Nginx Reverse Proxy

```nginx
# nginx.conf
server {
    listen 80;
    server_name copilot.yourdomain.com;
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl;
    server_name copilot.yourdomain.com;
    
    ssl_certificate /etc/letsencrypt/live/copilot.yourdomain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/copilot.yourdomain.com/privkey.pem;
    
    location / {
        proxy_pass http://app:8080;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

### Kubernetes with Ingress

```yaml
# ingress.yaml
apiVersion: networking.k8s.io/v1
kind: Ingress
metadata:
  name: unhcr-stat-copilot-ingress
  annotations:
    kubernetes.io/ingress.class: nginx
    cert-manager.io/cluster-issuer: letsencrypt-prod
spec:
  tls:
  - hosts:
    - copilot.yourdomain.com
    secretName: unhcr-stat-copilot-tls
  rules:
  - host: copilot.yourdomain.com
    http:
      paths:
      - path: /
        pathType: Prefix
        backend:
          service:
            name: unhcr-stat-copilot
            port:
              number: 80
```

---

## 🏥 Health Checks

The application provides multiple health check endpoints:

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/health` | GET | Comprehensive health check |
| `/` | GET | API root with service info |
| `/mcp` | GET/POST | MCP endpoint health check |

### Azure Health Probes

Azure App Service automatically sends health probes to the root endpoint (`/`). The application is configured to handle this:

```python
# In backend/app.py
@app.get("/")
async def read_root():
    return {
        "application": "UNHCR Stat Copilot",
        "version": "1.0.0",
        "mcp": "/mcp",
        "chat": "/chat",
        "docs": "/docs",
        "health": "/health"
    }

# In boot.sh
# Health check information is displayed at startup
```

### Custom Health Probe Configuration

#### Azure App Service

```bash
# Configure health check path
az webapp config set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --health-check-path /health

# Configure health check interval
az webapp config set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --health-check-interval 60
```

#### Kubernetes

```yaml
# In deployment.yaml
livenessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 30
  periodSeconds: 10
  timeoutSeconds: 5
  failureThreshold: 3

readinessProbe:
  httpGet:
    path: /health
    port: 8080
  initialDelaySeconds: 5
  periodSeconds: 5
  timeoutSeconds: 2
  failureThreshold: 3
```

---

## 📊 Monitoring & Logging

### Built-in Monitoring

The application includes Prometheus metrics endpoint:

```bash
# Get Prometheus metrics
curl http://localhost:8080/metrics
```

Metrics include:
- Request counts
- Error rates
- Response latency
- Active requests

### Azure Monitor Integration

```bash
# Enable Application Insights
az monitor app-insights create \
  --name unhcr-copilot-insights \
  --resource-group unhcr-copilot-rg \
  --location swedencentral

# Link to App Service
az webapp config appsettings set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --settings APPINSIGHTS_INSTRUMENTATIONKEY=<instrumentation-key>
```

### Docker Logging

```bash
# View container logs
docker logs <container-name>

# Follow logs
docker logs -f <container-name>

# View logs with timestamps
docker logs -t <container-name>

# Save logs to file
docker logs <container-name> > app.log 2>&1
```

### Azure App Service Logging

```bash
# Stream application logs
az webapp log tail \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --follow

# Download logs
az webapp log download \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --log-file app-logs.zip

# Configure log retention
az webapp config set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --detailed-error-messages true \
  --logging-level verbose
```

---

## 🔐 Security Considerations

### Authentication

**Current State**: The API is open and does not require authentication by default.

**Recommended for Production**:

#### Azure AD Authentication

```python
# In backend/app.py
from backend.auth import verify_azure_auth, get_optional_user

@app.get("/protected")
async def protected_route(user: UserInfo = Depends(verify_azure_auth)):
    return {"user": user.email}
```

Configure in Azure:
```bash
# Enable Azure AD authentication
az webapp auth config set \
  --name unhcr-stat-copilot \
  --resource-group unhcr-copilot-rg \
  --action LoginWithAzureActiveDirectory \
  --aad-client-id <client-id> \
  --aad-client-secret <client-secret> \
  --aad-tenant-id <tenant-id>
```

### CORS Configuration

```python
# In backend/app.py
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # Adjust for production
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

For production, restrict to specific origins:
```python
allow_origins=[
    "https://yourdomain.com",
    "https://www.yourdomain.com",
    "https://app.yourdomain.com"
]
```

### Rate Limiting

Enabled by default (10 requests/minute per IP):

```bash
# Disable rate limiting (not recommended)
RATE_LIMIT_ENABLED=false

# Configure rate limits in backend/app.py
limiter = Limiter(
    key_func=get_remote_address,
    enabled=RATE_LIMIT_ENABLED
)

# Per-endpoint rate limits
@app.post("/tool")
@limiter.limit("10/minute")
async def execute_tool(...):
    ...
```

### HTTPS Enforcement

Always use HTTPS in production:

- **Azure App Service**: HTTPS is automatically enforced
- **Docker with Nginx**: Configure SSL certificates
- **Kubernetes**: Use Ingress with TLS

---

## ⚡ Performance Tuning

### Gunicorn Configuration

The `boot.sh` script configures Gunicorn with optimal settings:

```bash
# From boot.sh
exec gunicorn backend.main:app \
    --bind "0.0.0.0:${BIND_PORT}" \
    --workers "${WEB_CONCURRENCY}" \
    --worker-class uvicorn.workers.UvicornWorker \
    --timeout 300 \
    --keep-alive 60 \
    --access-logfile - \
    --error-logfile - \
    --log-level info \
    --preload
```

#### Worker Count Recommendations

| Environment | CPU Cores | Recommended Workers | Memory |
|-------------|-----------|-------------------|---------|
| Development | 1-2 | 1-2 | 512MB |
| Azure (F1) | 1 | 2 | 1GB |
| Azure (B1) | 1 | 2-3 | 1-2GB |
| Azure (P1v2) | 2 | 3-4 | 2GB |
| Production (4+ cores) | 4+ | 2n+1 | 4GB+ |

**Formula**: `workers = 2 * CPU cores + 1` (maximum of 4-8 for most workloads)

### Timeout Configuration

| Setting | Recommended Value | Description |
|---------|------------------|-------------|
| `--timeout` | 300 | Request timeout in seconds |
| `--keep-alive` | 60 | Keep-alive connections in seconds |
| `MCP_TIMEOUT_SECONDS` | 30 | MCP tool request timeout |
| `MCP_MAX_RETRIES` | 3 | Maximum MCP retry attempts |

### Memory Optimization

- **Docker**: Set memory limits in `docker run`
- **Azure App Service**: Select appropriate tier
- **Kubernetes**: Set resource requests and limits

### Caching

The application does not cache MCP tool results (real-time data). For static content:

- Frontend assets are pre-built and served as static files
- Consider adding Redis for session storage in multi-instance deployments

---

## 🚀 CI/CD Pipeline

### GitHub Actions

Create a workflow file for automated deployments:

```yaml
# .github/workflows/deploy.yml
name: Deploy to Azure

on:
  push:
    branches: [ main ]
  pull_request:
    branches: [ main ]

jobs:
  build-and-deploy:
    runs-on: ubuntu-latest
    steps:
    - uses: actions/checkout@v4

    - name: Login to Docker Hub
      uses: docker/login-action@v2
      with:
        username: ${{ secrets.DOCKER_HUB_USERNAME }}
        password: ${{ secrets.DOCKER_HUB_TOKEN }}

    - name: Build and push Docker image
      run: |
        docker build -t ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:${{ github.sha }} .
        docker push ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:${{ github.sha }}
        docker tag ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:${{ github.sha }} ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:latest
        docker push ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:latest

    - name: Deploy to Azure
      uses: azure/webapps-deploy@v2
      with:
        app-name: unhcr-stat-copilot
        publish-profile: ${{ secrets.AZURE_WEBAPP_PUBLISH_PROFILE }}
        images: ${{ secrets.DOCKER_HUB_USERNAME }}/unhcr-stat-copilot:latest
```

### Azure DevOps Pipeline

```yaml
# azure-pipelines.yml
trigger:
  - main

pool:
  vmImage: 'ubuntu-latest'

steps:
- task: Docker@2
  inputs:
    containerRegistry: 'DockerHub'
    repository: 'unhcr-stat-copilot'
    command: 'buildAndPush'
    Dockerfile: '**/Dockerfile'
    tags: |
      $(Build.BuildId)
      latest

- task: AzureWebAppContainer@1
  inputs:
    azureSubscription: 'AzureServiceConnection'
    appName: 'unhcr-stat-copilot'
    containers: 'unhcr-stat-copilot:latest'
    multistageYamlFile: '**/Dockerfile'
```

---

## 🐛 Troubleshooting Deployment Issues

### Common Issues

#### Issue: "405 Method Not Allowed" on `/mcp`

**Cause**: Azure health check is sending POST requests to `/mcp`, but the MCP endpoint only accepts POST. However, there might be a mount conflict.

**Solution**: This has been **fixed in the latest commit** by adding explicit health check endpoints:

```python
# In backend/app.py
@app.post("/mcp", include_in_schema=False)
async def mcp_health_check():
    return {"status": "ok", "message": "MCP endpoint active", "mcp_protocol": "/mcp/"}

@app.get("/mcp", include_in_schema=False)
async def mcp_health_check_get():
    return {"status": "ok", "message": "MCP endpoint active", "mcp_protocol": "/mcp/"}
```

**Verification**:
```bash
# Test GET request
curl http://localhost:8080/mcp

# Test POST request
curl -X POST http://localhost:8080/mcp -H "Content-Type: application/json" -d '{"tool": "get_usage_guidance", "arguments": {}}'
```

#### Issue: FastAPI Docs Not Loading

**Problem**: `Failed to load API definition. Errors: Fetch error Internal Server Error /openapi.json`

**Cause**: This typically happens when:
1. There are syntax errors in the OpenAPI schema
2. Ellipsis (`...`) are used in response examples
3. Response models are not properly defined

**Solution**: 
1. Fix all ellipsis in response examples (replaced with actual values)
2. Ensure all endpoints have proper response models
3. Verify `/openapi.json` directly:

```bash
curl http://localhost:8080/openapi.json | python -m json.tool
```

#### Issue: `/mcp/docs` and `/mcp/info` Not Found

**Cause**: Documentation endpoints were mounted at `/api/mcp/docs` and `/api/mcp/info`, not `/mcp/docs`.

**Solution**: Use the correct endpoints:
- `/api/mcp/docs` - Full MCP documentation
- `/api/mcp/info` - Server metadata
- `/mcp` - MCP protocol endpoint

**Verification**:
```bash
# Correct endpoints
curl http://localhost:8080/api/mcp/docs
curl http://localhost:8080/api/mcp/info
```

#### Issue: Redoc Not Referencing Correct API

**Cause**: Redoc configuration was pointing to wrong documentation endpoints.

**Solution**: 
1. Use `/api/mcp/docs` for MCP documentation
2. Use `/docs` for Swagger UI (FastAPI default)
3. Use `/redoc` for ReDoc (FastAPI default)

```python
# In backend/app.py
# Both /docs and /redoc are provided by FastAPI automatically
# MCP-specific documentation is at /api/mcp/docs
```

#### Issue: Container Fails to Start

**Debugging Steps**:

```bash
# Check container logs
docker logs <container-id>

# Run container interactively
docker run -it --entrypoint /bin/sh unhcr-stat-copilot

# Check if port is available
netstat -tlnp | grep 8080

# Check application import
python -c "from backend.main import app; print('Import successful')"

# Check dependencies
pip list | grep -E "(fastapi|uvicorn|gunicorn|fastmcp)"
```

#### Issue: 503 MCP Server Unavailable

**Cause**: The MCP server session manager is not running.

**Solution**: Ensure the lifespan context manager is properly configured:

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
# Check MCP server health
curl http://localhost:8080/mcp

# Check if tools are available
curl http://localhost:8080/tools
```

### Deployment Checklist

Before deploying to production, verify:

- [ ] Health endpoint returns HTTP 200: `curl /health`
- [ ] Root endpoint returns HTTP 200: `curl /`
- [ ] MCP endpoint is accessible: `curl /mcp`
- [ ] Tool list is available: `curl /tools`
- [ ] Documentation endpoints work: `curl /api/mcp/docs`
- [ ] Swagger UI loads: Open `/docs` in browser
- [ ] ReDoc loads: Open `/redoc` in browser
- [ ] Rate limiting is configured correctly
- [ ] CORS settings are appropriate for your environment
- [ ] Port binding matches expected port (PORT/WEBSITES_PORT)
- [ ] Application logs are being captured
- [ ] Health checks pass (Azure/Kubernetes)

---

## 📚 See Also

- [README.md](./README.md) - Main documentation
- [ARCHITECTURE.md](./ARCHITECTURE.md) - System architecture
- [API_DOCUMENTATION.md](./API_DOCUMENTATION.md) - API reference
- [MCP_INTEGRATION.md](./MCP_INTEGRATION.md) - MCP integration guide
- [DEVELOPMENT.md](./DEVELOPMENT.md) - Development setup
- [TROUBLESHOOTING.md](./TROUBLESHOOTING.md) - Common issues and solutions

---

*Last updated: July 7, 2026*
