#!/bin/bash

set -e

echo "========================================="
echo "Starting UNHCR-Stat-Copilot"
echo "========================================="

ROOT_DIR=$(pwd)

BACKEND_DIR="${ROOT_DIR}/backend"
FRONTEND_DIR="${ROOT_DIR}/frontend"

# --------------------------------------------------
# Backend
# --------------------------------------------------

echo ""
echo "Starting FastAPI backend..."
echo ""

# --------------------------------------------------
# Backend Setup
# --------------------------------------------------

echo ""
echo "Preparing backend..."
echo ""

cd "${BACKEND_DIR}"

if [ ! -d ".venv" ]; then

    echo "Creating Python 3.12 virtual environment..."

    uv venv --python 3.12

fi

source .venv/bin/activate

echo "Python version:"
python --version

echo ""
echo "Installing backend requirements..."
echo ""

pip install --upgrade pip
uv pip install -r requirements.txt

echo ""
echo "Starting FastAPI backend..."
echo ""
cd "${ROOT_DIR}"
uvicorn backend.app:app \
    --host 0.0.0.0 \
    --port 8000 \
    --reload &

BACKEND_PID=$!

echo ""
echo "Backend started"
echo "PID: ${BACKEND_PID}"
echo "Swagger: http://localhost:8000/docs"
echo ""

# --------------------------------------------------
# Frontend
# --------------------------------------------------

echo "Starting React frontend..."
echo ""

cd "${FRONTEND_DIR}"
npm install

npm run dev -- \
    --host 0.0.0.0 \
    --port 5173 &

FRONTEND_PID=$!

echo ""
echo "Frontend started"
echo "PID: ${FRONTEND_PID}"
echo "URL: http://localhost:5173"
echo ""

# --------------------------------------------------
# Shutdown handler
# --------------------------------------------------

cleanup() {

    echo ""
    echo "Stopping services..."
    echo ""

    kill ${BACKEND_PID} 2>/dev/null || true
    kill ${FRONTEND_PID} 2>/dev/null || true

    exit 0
}

trap cleanup SIGINT SIGTERM

echo ""
echo "========================================="
echo "UNHCR-Stat-Copilot Running"
echo "========================================="
echo ""
echo "Frontend : http://localhost:5173"
echo "Backend  : http://localhost:8000"
echo "Swagger  : http://localhost:8000/docs"
echo "MCP      : http://localhost:8000/mcp"
echo ""
echo "Press CTRL+C to stop"
echo ""

wait