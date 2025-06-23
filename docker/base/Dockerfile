# MCP Zero Base Image
# Provides the foundation for all MCP Zero services
FROM python:3.9-slim

# Set environment variables
ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=off \
    PIP_DISABLE_PIP_VERSION_CHECK=on

# Set working directory
WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y --no-install-recommends \
    build-essential \
    git \
    curl \
    && apt-get clean \
    && rm -rf /var/lib/apt/lists/*

# Install basic Python dependencies
COPY docker/base/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Set up offline-first defaults
# This ensures services start in offline mode by default
ENV MCP_OFFLINE_FIRST=true \
    MCP_CONNECTION_ATTEMPTS=1

# Add healthcheck
HEALTHCHECK --interval=30s --timeout=30s --start-period=5s --retries=3 \
    CMD curl -f http://localhost:8080/health || exit 1

# Add entrypoint script
COPY docker/base/entrypoint.sh /entrypoint.sh
RUN chmod +x /entrypoint.sh

ENTRYPOINT ["/entrypoint.sh"]
