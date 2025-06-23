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
