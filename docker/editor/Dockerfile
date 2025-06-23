# MCP Zero Editor Service
FROM mcp-zero-base:latest

# Install additional dependencies for the editor service
COPY docker/editor/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the editor source code
COPY editor /app/editor

# Copy the offline-first service configurations
COPY docker/editor/config /app/config

WORKDIR /app/editor

# Following offline-first resilience pattern:
# 1. Start in offline mode by default
# 2. Attempt to connect to remote services only once
# 3. Fall back permanently to local processing
ENV MCP_OFFLINE_FIRST=true \
    MCP_CONNECTION_ATTEMPTS=1 \
    MCP_START_OFFLINE=true

EXPOSE 8080

CMD ["python", "-m", "src.main"]
