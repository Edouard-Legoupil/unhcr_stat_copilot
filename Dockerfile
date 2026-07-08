
# ============================================
# Stage 1: Frontend builder (Vite/React)
# ============================================
FROM node:20-alpine AS frontend-builder

WORKDIR /app
# Use separate copy to leverage Docker layer caching on npm installs
COPY frontend/package*.json ./
RUN npm ci && echo "✅ NPM modules installed"

# Copy frontend source and build
COPY frontend/ .
RUN npm run build && echo "✅ Frontend build complete"


# ============================================
# Stage 2: Final Python application image
# ============================================
FROM python:3.11-slim AS final

# Install OS dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    curl \
    wget \
    dnsutils \
    procps \
    net-tools \
    util-linux \
    build-essential \
    # Install fonts for matplotlib (Lato is required by unhcrpyplotstyle)
    fonts-lato \
    fonts-dejavu \
    fonts-liberation \
    fontconfig \
    && wget https://github.com/quarto-dev/quarto-cli/releases/download/v1.9.38/quarto-1.9.38-linux-amd64.deb \
    && apt-get update \
    && apt-get install -y ./quarto-1.9.38-linux-amd64.deb \
    && quarto check \
    && rm quarto-1.9.38-linux-amd64.deb \
    && rm -rf /var/lib/apt/lists/*



# ------------------------------------------------
# Create app directory
# ------------------------------------------------
WORKDIR /app

# ------------------------------------------------
# Create ONE Python venv used by the whole image
# ------------------------------------------------
RUN python -m venv /venv
ENV PATH="/venv/bin:$PATH"
ENV PYTHONUNBUFFERED=1
ENV PYTHONPATH=/app

# ------------------------------------------------
# Dependency install
# ------------------------------------------------
RUN mkdir -p backend
COPY backend/requirements.txt backend/

RUN pip install --upgrade pip \
    && pip install --no-cache-dir uvicorn fastapi gunicorn \
    && pip install --no-cache-dir -r backend/requirements.txt \
    # Rebuild matplotlib font cache to pick up newly installed fonts
    && python -c "import matplotlib.font_manager; matplotlib.font_manager._rebuild()"

# ------------------------------------------------
# Copy backend source code
# ------------------------------------------------
COPY backend/ backend/

# Remove any local virtualenv files
RUN rm -rf /app/backend/venv || true

# ------------------------------------------------
# Copy frontend static build files
# ------------------------------------------------
COPY --from=frontend-builder /app/dist /app/frontend/dist

# ------------------------------------------------
# Create directories for logs, data, and file storage
# ------------------------------------------------
RUN mkdir -p /app/log /app/data /app/uploads /app/generated \
    && chmod -R 755 /app/log /app/data /app/uploads /app/generated

# ------------------------------------------------
# Copy vector store database and markdown reports
# ------------------------------------------------
RUN mkdir -p /app/data/vector_store /app/data/markdown_reports
#COPY ./data/vector_store/unhcr_reports.duckdb /app/data/vector_store/ 2>/dev/null || true

# ------------------------------------------------
# Expose the container port
# ------------------------------------------------
EXPOSE 8080

# ------------------------------------------------
# Add start script
# ------------------------------------------------
COPY boot.sh /usr/local/bin/boot.sh
RUN chmod +x /usr/local/bin/boot.sh

# ------------------------------------------------
# Allow for SSH (for Azure tunnel)
# ------------------------------------------------
RUN apt-get update && apt-get install -y --no-install-recommends openssh-server \
    && rm -rf /var/lib/apt/lists/*

RUN ssh-keygen -A && mkdir -p /var/run/sshd
RUN echo "root:Docker!" | chpasswd
COPY sshd_config /etc/ssh/sshd_config
EXPOSE 2222

# ------------------------------------------------
# Default command
# ------------------------------------------------
CMD ["/usr/local/bin/boot.sh"]
