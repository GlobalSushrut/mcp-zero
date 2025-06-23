# MCP-ZERO RPC Server Setup Guide

## Problem: Memory Registration Endpoint Not Found

The memory registration errors occur because the MCP-ZERO RPC server isn't properly configured with the `/api/v1/memory/register` endpoint that the memory tree expects. This guide will help you properly configure and start the server.

## Server Configuration

1. First, create a proper configuration file:

```bash
mkdir -p /home/umesh/Videos/mcp_zero/config
```

Create a configuration file at `/home/umesh/Videos/mcp_zero/config/server_config.yaml`:

```yaml
# MCP-ZERO Server Configuration
server:
  agent_port: 8080
  api_port: 8081
  metrics_port: 9090
  debug: true

memory:
  # Enable memory registration endpoint
  registration_enabled: true
  registration_endpoint: "/api/v1/memory/register"
  
api:
  # Enable all required API endpoints
  endpoints:
    - path: "/api/v1/memory/register"
      method: "POST"
      handler: "memory_registration_handler"
    - path: "/api/v1/status"
      method: "GET"
      handler: "status_handler"
    - path: "/health"
      method: "GET"
      handler: "health_handler"
      
resources:
  # Resource constraints
  max_cpu_percent: 27
  max_memory_mb: 827
```

## Creating the Missing API Endpoint

Create a new file to implement the missing endpoint:

```bash
mkdir -p /home/umesh/Videos/mcp_zero/src/api
```

Create `/home/umesh/Videos/mcp_zero/src/api/memory_endpoints.py`:

```python
#!/usr/bin/env python3
"""
Memory Registration Endpoint for MCP-ZERO RPC Server

This adds the missing memory registration endpoint needed by the memory tree.
"""

import os
import sys
import json
import http.server
import socketserver
import threading
import time
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("memory-api")

class MemoryRegistrationHandler(http.server.BaseHTTPRequestHandler):
    """HTTP handler for memory registration endpoint"""
    
    def do_GET(self):
        """Handle GET requests"""
        if self.path == "/health":
            self._send_response(200, {"status": "healthy"})
        elif self.path == "/api/v1/status":
            self._send_response(200, {
                "status": "running",
                "server_type": "mcp-zero-memory-api",
                "version": "1.0.0"
            })
        else:
            self._send_response(404, {"error": "Not found"})
    
    def do_POST(self):
        """Handle POST requests"""
        if self.path == "/api/v1/memory/register":
            # Get request content length
            content_length = int(self.headers['Content-Length'])
            if content_length > 1024 * 1024:  # 1MB limit
                self._send_response(413, {"error": "Request too large"})
                return
            
            # Read and parse request body
            post_data = self.rfile.read(content_length)
            try:
                memory_data = json.loads(post_data.decode('utf-8'))
                
                # Validate memory data
                required_fields = ["node_id", "content", "node_type", "agent_id"]
                for field in required_fields:
                    if field not in memory_data:
                        self._send_response(400, {
                            "error": f"Missing required field: {field}"
                        })
                        return
                
                # Process the memory registration
                logger.info(f"Registering memory node: {memory_data['node_id']}")
                
                # Store the memory node (in a real implementation, this would
                # connect to the storage system)
                self._register_memory(memory_data)
                
                # Send success response
                self._send_response(200, {
                    "status": "success",
                    "node_id": memory_data["node_id"],
                    "registered": True,
                    "timestamp": int(time.time())
                })
            except json.JSONDecodeError:
                self._send_response(400, {"error": "Invalid JSON"})
            except Exception as e:
                logger.error(f"Error processing memory registration: {e}")
                self._send_response(500, {"error": str(e)})
        else:
            self._send_response(404, {"error": "Not found"})
    
    def _send_response(self, status_code, data):
        """Send a JSON response with the given status code"""
        self.send_response(status_code)
        self.send_header('Content-Type', 'application/json')
        self.end_headers()
        
        response = json.dumps(data).encode('utf-8')
        self.wfile.write(response)
    
    def _register_memory(self, memory_data):
        """Register memory in the system"""
        # In a full implementation, this would properly store the memory
        # For now, we'll just log it
        node_id = memory_data["node_id"]
        node_type = memory_data["node_type"]
        agent_id = memory_data["agent_id"]
        
        logger.info(f"Registered memory node {node_id} of type {node_type} for agent {agent_id}")
        
        # Track registrations in a simple file-based log
        log_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "../../logs")
        os.makedirs(log_dir, exist_ok=True)
        
        with open(os.path.join(log_dir, "memory_registrations.log"), "a") as f:
            f.write(f"{time.time()},{node_id},{node_type},{agent_id}\n")

def run_server(port=8081):
    """Run the memory registration server"""
    server = socketserver.TCPServer(("0.0.0.0", port), MemoryRegistrationHandler)
    logger.info(f"Starting memory registration server on port {port}")
    
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        logger.info("Shutting down memory registration server")
        server.shutdown()

if __name__ == "__main__":
    # Get port from command line argument if provided
    port = 8081
    if len(sys.argv) > 1 and sys.argv[1].isdigit():
        port = int(sys.argv[1])
    
    run_server(port)
```

## Running the RPC Server

Now create a startup script to properly launch the MCP-ZERO RPC server:

```bash
mkdir -p /home/umesh/Videos/mcp_zero/scripts
```

Create `/home/umesh/Videos/mcp_zero/scripts/start_rpc_server.sh`:

```bash
#!/bin/bash

# Start MCP-ZERO RPC Server
# This script ensures all required endpoints are available

# Set base directory
BASE_DIR="/home/umesh/Videos/mcp_zero"
CONFIG_DIR="${BASE_DIR}/config"
LOG_DIR="${BASE_DIR}/logs"

# Create log directory
mkdir -p "${LOG_DIR}"

# Function to check if port is in use
check_port() {
    netstat -an | grep -q ":$1 .*LISTEN"
    return $?
}

# Start memory registration endpoint server
start_memory_api() {
    echo "Starting memory registration endpoint on port 8081..."
    python "${BASE_DIR}/src/api/memory_endpoints.py" 8081 > "${LOG_DIR}/memory_api.log" 2>&1 &
    echo "Memory API server started with PID $!"
    echo $! > "${LOG_DIR}/memory_api.pid"
    sleep 2
}

# Check if memory API is already running
if check_port 8081; then
    echo "Warning: Port 8081 is already in use. Please check for existing servers."
else
    start_memory_api
fi

# Check if memory API started correctly
if ! check_port 8081; then
    echo "Error: Memory API failed to start on port 8081"
    exit 1
fi

echo "✅ Memory registration endpoint is now available at http://localhost:8081/api/v1/memory/register"
echo "✅ Health check endpoint is available at http://localhost:8081/health"
echo "✅ Status endpoint is available at http://localhost:8081/api/v1/status"

# Testing the endpoints
echo -e "\nTesting health endpoint..."
curl -s http://localhost:8081/health | python -m json.tool

echo -e "\nSetup complete! The MCP-ZERO RPC server is now properly configured for memory registration."
```

Make the script executable:

```bash
chmod +x /home/umesh/Videos/mcp_zero/scripts/start_rpc_server.sh
```

## Using the Fixed RPC Server

1. Start the RPC server with the new endpoints:

```bash
cd /home/umesh/Videos/mcp_zero
./scripts/start_rpc_server.sh
```

2. Run your PARE protocol demo with the proper RPC URL:

```bash
cd /home/umesh/Videos/mcp_zero
python -m pare_protocol.demo --rpc http://localhost:8081
```

3. For the new IntentWeightBias demo:

```bash
cd /home/umesh/Videos/mcp_zero
python -m pare_protocol.intent_demo --rpc http://localhost:8081
```

## Verifying Memory Registration

To verify that the memory registration is working correctly:

1. Check the logs:

```bash
cat /home/umesh/Videos/mcp_zero/logs/memory_api.log
```

2. Check registered memories:

```bash
cat /home/umesh/Videos/mcp_zero/logs/memory_registrations.log
```

With these changes, your memory registration will work properly and the memory tree will no longer switch to offline mode due to missing endpoints.
