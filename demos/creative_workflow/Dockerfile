FROM python:3.10-slim

# Set working directory
WORKDIR /app

# Copy required files
COPY requirements.txt ./
COPY *.py ./

# Create output directory
RUN mkdir -p output

# Install dependencies
RUN pip install --no-cache-dir -r requirements.txt

# Set environment variables
ENV MCP_RPC_URL=http://mcp-server:8082
ENV PYTHONUNBUFFERED=1

# Command to run the demo
CMD ["python", "run_creative_demo.py"]
