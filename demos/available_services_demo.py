#!/usr/bin/env python3
"""
MCP-ZERO Available Services Demo
Uses only the actually running MCP-ZERO servers (RPC on 8081 and DB on 8082)

Hardware constraints: <27% CPU, <827MB RAM
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("mcp_zero_demo")

# Constants for available servers only
RPC_SERVER_URL = "http://localhost:8081"
DB_SERVER_URL = "http://localhost:8082"

# Hardware constraints
CPU_LIMIT = 27.0  # <27% CPU usage
MEM_LIMIT = 827.0  # <827MB RAM usage

def get_resource_usage():
    """Monitor resource usage to ensure we stay within hardware constraints"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        
        # Get CPU usage (short interval for quick measurement)
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Get memory usage in MB
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        return cpu_percent, memory_mb
    except ImportError:
        logger.warning("psutil not available, resource monitoring disabled")
        return 0.0, 0.0

def check_constraints():
    """Check if we're within hardware constraints"""
    cpu, mem = get_resource_usage()
    logger.info(f"Resource usage: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
    
    if cpu > CPU_LIMIT:
        logger.warning(f"CPU usage exceeds limit: {cpu:.1f}% > {CPU_LIMIT}%")
    
    if mem > MEM_LIMIT:
        logger.warning(f"Memory usage exceeds limit: {mem:.1f}MB > {MEM_LIMIT}MB")
        
    return cpu <= CPU_LIMIT and mem <= MEM_LIMIT

class RPCClient:
    """Client for interacting with the MCP-ZERO RPC server"""
    
    def __init__(self, api_url):
        """Initialize RPC client with server URL"""
        self.api_url = api_url
        logger.info(f"RPC Client initialized for {api_url}")
        
    def _make_request(self, method, endpoint, data=None):
        """Make HTTP request to RPC server with error handling"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            start_time = time.time()
            
            if method.lower() == "get":
                response = requests.get(url, headers=headers, timeout=5)
            else:  # POST
                response = requests.post(url, headers=headers, json=data, timeout=5)
            
            # Log response time for performance monitoring
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"RPC {method} {endpoint}: {elapsed_ms:.0f}ms")
            
            # Check for error status codes
            response.raise_for_status()
            
            # Return response data if available
            if response.text:
                return response.json()
            return {}
            
        except requests.RequestException as e:
            logger.error(f"RPC error ({method} {endpoint}): {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise

    def spawn_agent(self, name):
        """Create a new agent using the RPC API"""
        data = {"name": name}
        response = self._make_request("post", "/api/v1/agents", data)
        
        agent_id = response.get("agent_id")
        if not agent_id:
            raise ValueError("Failed to create agent: No agent_id in response")
            
        logger.info(f"Agent spawned with ID: {agent_id}")
        return agent_id
    
    def get_agent(self, agent_id):
        """Get agent details"""
        return self._make_request("get", f"/api/v1/agents/{agent_id}")
    
    def attach_plugin(self, agent_id, plugin_id):
        """Attach a plugin to an agent"""
        data = {"plugin_id": plugin_id}
        response = self._make_request("post", f"/api/v1/agents/{agent_id}/plugins", data)
        
        success = response.get("success", False)
        if not success:
            logger.warning(f"Failed to attach plugin {plugin_id} to agent {agent_id}")
            
        return success
    
    def execute_intent(self, agent_id, intent, inputs=None):
        """Execute an intent on the agent"""
        data = {
            "intent": intent,
            "inputs": inputs or {}
        }
        return self._make_request("post", f"/api/v1/agents/{agent_id}/execute", data)

class DBClient:
    """Client for interacting with the MCP-ZERO Database"""
    
    def __init__(self, db_url):
        """Initialize DB client with server URL"""
        self.db_url = db_url
        logger.info(f"DB Client initialized for {db_url}")
    
    def _db_request(self, method, endpoint, data=None):
        """Make request to DB server with error handling"""
        url = f"{self.db_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            start_time = time.time()
            
            if method.lower() == "get":
                response = requests.get(url, headers=headers, timeout=5)
            elif method.lower() == "delete":
                response = requests.delete(url, headers=headers, timeout=5)
            else:  # POST/PUT
                response = requests.post(url, headers=headers, json=data, timeout=5)
            
            # Log response time
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"DB {method} {endpoint}: {elapsed_ms:.0f}ms")
            
            # Check for error status codes
            response.raise_for_status()
            
            # Return response data if available
            if response.text:
                return response.json()
            return {}
            
        except requests.RequestException as e:
            logger.error(f"DB error ({method} {endpoint}): {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise
    
    def store_agent_state(self, agent_id, state):
        """Store agent state in the database"""
        data = {
            "agent_id": agent_id,
            "state": state,
            "timestamp": time.time()
        }
        response = self._db_request("post", "/api/v1/states", data)
        return response.get("success", False)
    
    def retrieve_agent_state(self, agent_id):
        """Retrieve agent state from the database"""
        response = self._db_request("get", f"/api/v1/states/{agent_id}")
        return response.get("state", {})

class AvailableServicesDemo:
    """Demo using only available MCP-ZERO servers"""
    
    def __init__(self, name):
        self.name = name
        self.agent_id = None
        
        # Initialize clients for available servers
        self.rpc = RPCClient(RPC_SERVER_URL)
        self.db = DBClient(DB_SERVER_URL)
        
        logger.info(f"Initialized AvailableServicesDemo '{name}'")
        check_constraints()
    
    def run_demo(self):
        """Run the demo with available services"""
        try:
            # Step 1: Create agent with RPC server
            logger.info("Creating agent with RPC server...")
            self.agent_id = self.rpc.spawn_agent(self.name)
            check_constraints()
            
            # Step 2: Get agent details
            logger.info("Getting agent details...")
            agent_details = self.rpc.get_agent(self.agent_id)
            logger.info(f"Agent details: {json.dumps(agent_details, indent=2)}")
            check_constraints()
            
            # Step 3: Store agent state in DB
            logger.info("Storing agent state in database...")
            initial_state = {
                "name": self.name,
                "agent_id": self.agent_id,
                "created_at": time.time(),
                "status": "active"
            }
            success = self.db.store_agent_state(self.agent_id, initial_state)
            logger.info(f"State storage {'succeeded' if success else 'failed'}")
            check_constraints()
            
            # Step 4: Attach plugins using RPC
            logger.info("Attaching plugins...")
            plugins = ["document-analyzer", "nlp-processor"]
            
            for plugin_id in plugins:
                success = self.rpc.attach_plugin(self.agent_id, plugin_id)
                status = "succeeded" if success else "failed"
                logger.info(f"Plugin attachment '{plugin_id}': {status}")
            check_constraints()
            
            # Step 5: Execute intent
            logger.info("Executing intent...")
            sample_text = "MCP-ZERO is an AI agent infrastructure designed for 100+ year sustainability."
            execution_result = self.rpc.execute_intent(
                self.agent_id,
                "analyze_text",
                {"text": sample_text}
            )
            logger.info(f"Execution result: {json.dumps(execution_result, indent=2)}")
            check_constraints()
            
            # Step 6: Retrieve agent state from DB
            logger.info("Retrieving agent state...")
            agent_state = self.db.retrieve_agent_state(self.agent_id)
            logger.info(f"Retrieved state: {json.dumps(agent_state, indent=2)}")
            check_constraints()
            
            return True
            
        except Exception as e:
            logger.error(f"Demo failed: {str(e)}")
            return False

def main():
    """Main function to run the available services demo"""
    start_time = time.time()
    logger.info("-" * 80)
    logger.info("MCP-ZERO AVAILABLE SERVICES DEMO")
    logger.info("-" * 80)
    
    initial_cpu, initial_mem = get_resource_usage()
    logger.info(f"Initial resource usage: CPU {initial_cpu:.1f}%, Memory {initial_mem:.1f}MB")
    
    # Run demo
    demo = AvailableServicesDemo("available-services-demo")
    success = demo.run_demo()
    
    # Report results
    final_cpu, final_mem = get_resource_usage()
    logger.info(f"Final resource usage: CPU {final_cpu:.1f}%, Memory {final_mem:.1f}MB")
    
    total_time = time.time() - start_time
    logger.info(f"Total execution time: {total_time:.2f} seconds")
    
    if final_cpu <= CPU_LIMIT and final_mem <= MEM_LIMIT:
        logger.info("✅ All hardware constraints satisfied!")
    else:
        logger.warning("❌ Some hardware constraints were exceeded")
    
    return 0 if success else 1

if __name__ == "__main__":
    sys.exit(main())
