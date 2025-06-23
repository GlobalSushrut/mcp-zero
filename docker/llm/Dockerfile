# MCP Zero LLM Service
FROM mcp-zero-base:latest

# Install additional dependencies for the LLM service
COPY docker/llm/requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# Copy the LLM service source code
COPY llm /app/llm

# Copy the offline-first service configurations
COPY docker/llm/config /app/config

WORKDIR /app/llm

# Following offline-first resilience pattern:
# 1. Start in offline mode by default
# 2. Attempt to connect to external LLM provider only once
# 3. Fall back permanently to local processing
ENV MCP_OFFLINE_FIRST=true \
    MCP_CONNECTION_ATTEMPTS=1 \
    MCP_START_OFFLINE=true

# Pre-download any necessary model files for offline operation
RUN python -m download_models

EXPOSE 8081

CMD ["python", "-m", "server"]
