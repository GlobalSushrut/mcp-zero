#!/usr/bin/env python3
"""
MCP-ZERO Real Server Demo
Demonstrates direct integration with MCP-ZERO RPC Server
"""

import os
import sys
import json
import logging
import requests
import time
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("real_demo")

# Constants
API_URL = "http://localhost:8081"
CPU_LIMIT = 27.0  # <27% CPU usage
MEM_LIMIT = 827.0  # <827MB RAM usage

def api_request(method, endpoint, data=None, optional=False):
    """Make an API request to the MCP-ZERO RPC server"""
    url = f"{API_URL}/{endpoint.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers)
        else:  # POST
            response = requests.post(url, headers=headers, json=data)
        
        # Check for error status codes
        if response.status_code == 404 and optional:
            logger.warning(f"Optional endpoint not available: {endpoint}")
            return {"status": "skipped", "reason": "endpoint_not_available"}
        
        response.raise_for_status()
        
        # Return response data if available
        if response.text:
            return response.json()
        return {}
        
    except requests.RequestException as e:
        if optional:
            logger.warning(f"Optional operation failed: {endpoint} - {str(e)}")
            return {"status": "skipped", "reason": "request_failed"}
        
        logger.error(f"API error: {str(e)}")
        if hasattr(e, "response") and e.response is not None:
            logger.error(f"Response: {e.response.status_code} - {e.response.text}")
        raise

def spawn_agent(agent_name):
    """Create a new agent using the RPC API"""
    agent_id = f"agent-{int(time.time())}"
    
    # Create agent request
    data = {
        "id": agent_id,
        "name": agent_name
    }
    
    # Make the request
    response = api_request("post", "/api/v1/agents", data)
    logger.info(f"Agent created: {response}")
    
    return agent_id

def attach_plugin(agent_id, plugin_id="demo-plugin-001"):
    """Attach a plugin to an agent"""
    # Plugin attachment request
    data = {
        "agent_id": agent_id,
        "plugin_id": plugin_id
    }
    
    # Make the request
    response = api_request("post", f"/api/v1/agents/{agent_id}/plugins", data)
    logger.info(f"Plugin attached: {response}")
    
    return True

def execute_intent(agent_id, intent, inputs):
    """Execute an intent on the agent"""
    # Execute request
    data = {
        "agent_id": agent_id,
        "intent": intent,
        "inputs": inputs
    }
    
    # Make the request
    response = api_request("post", f"/api/v1/agents/{agent_id}/execute", data)
    logger.info(f"Execution result: {response}")
    
    return response

def create_snapshot(agent_id):
    """Create a snapshot of the agent"""
    # Snapshot request
    data = {
        "agent_id": agent_id,
        "metadata": {
            "demo": True,
            "timestamp": time.strftime("%Y-%m-%d %H:%M:%S")
        }
    }
    
    # Mark as optional since it might not be implemented in current version
    response = api_request("post", f"/api/v1/agents/{agent_id}/snapshots", data, optional=True)
    
    if response.get("status") == "skipped":
        logger.info("Snapshot creation skipped: API endpoint not available")
        return "skipped"
        
    logger.info(f"Snapshot created: {response}")
    
    # Return snapshot ID if available
    return response.get("snapshot_id", "unknown")

def recover_agent(snapshot_id):
    """Recover an agent from a snapshot"""
    # Skip if snapshot_id is not valid
    if snapshot_id == "skipped":
        logger.info("Recovery skipped: No valid snapshot available")
        return None
        
    # Recovery request
    data = {
        "snapshot_id": snapshot_id
    }
    
    # Mark as optional since it might not be implemented in current version
    response = api_request("post", f"/api/v1/snapshots/{snapshot_id}/recover", data, optional=True)
    
    if response.get("status") == "skipped":
        logger.info("Recovery skipped: API endpoint not available")
        return None
        
    logger.info(f"Agent recovered: {response}")
    
    return response.get("agent_id")

def get_resource_usage():
    """Get current CPU and memory usage"""
    try:
        import psutil
        # Get CPU usage for the current process
        process = psutil.Process(os.getpid())
        cpu_percent = process.cpu_percent(interval=0.1)
        memory_info = process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
        
        return cpu_percent, memory_mb
    except ImportError:
        logger.warning("psutil not available - resource monitoring disabled")
        return 0.0, 0.0

def check_resource_constraints():
    """Check if current resource usage meets MCP-ZERO constraints"""
    cpu_percent, memory_mb = get_resource_usage()
    
    logger.info(f"Current resource usage: CPU {cpu_percent:.1f}%, Memory {memory_mb:.1f}MB")
    
    # Check constraints
    cpu_ok = cpu_percent < CPU_LIMIT
    memory_ok = memory_mb < MEM_LIMIT
    
    if not cpu_ok:
        logger.warning(f"CPU usage exceeds limit: {cpu_percent:.1f}% > {CPU_LIMIT}%")
    
    if not memory_ok:
        logger.warning(f"Memory usage exceeds limit: {memory_mb:.1f}MB > {MEM_LIMIT}MB")
    
    return cpu_ok and memory_ok

def main():
    """Run the MCP-ZERO RPC Server demo"""
    start_time = time.time()
    
    try:
        logger.info("==== MCP-ZERO RPC Server Demo ====")
        logger.info(f"Connecting to server at {API_URL}")
        logger.info(f"Hardware constraints: <{CPU_LIMIT}% CPU, <{MEM_LIMIT}MB RAM")
        
        # Initial resource check
        check_resource_constraints()
        
        # 1. Create agent
        logger.info("\n1. Creating new agent...")
        agent_id = spawn_agent("document-assistant")
        logger.info(f"Agent created with ID: {agent_id}")
        check_resource_constraints()
        
        # 2. Attach plugin
        logger.info("\n2. Attaching plugin...")
        try:
            attach_plugin(agent_id)
            logger.info("Plugin attached successfully")
        except Exception as e:
            logger.warning(f"Plugin attachment skipped: {str(e)}")
        check_resource_constraints()
        
        # 3. Execute intent
        logger.info("\n3. Executing document analysis intent...")
        result = execute_intent(
            agent_id=agent_id,
            intent="analyze_document",
            inputs={"text": "This is a test document for MCP-ZERO."}
        )
        logger.info(f"Execution completed with result: {result}")
        check_resource_constraints()
        
        # 4. Create snapshot (optional)
        logger.info("\n4. Creating snapshot...")
        snapshot_id = create_snapshot(agent_id)
        if snapshot_id != "skipped":
            logger.info(f"Snapshot created with ID: {snapshot_id}")
        check_resource_constraints()
        
        # 5. Recover from snapshot (optional)
        logger.info("\n5. Recovering agent from snapshot...")
        recovered_id = recover_agent(snapshot_id)
        if recovered_id:
            logger.info(f"Recovery successful. New agent ID: {recovered_id}")
        check_resource_constraints()
        
        # Final resource check
        logger.info("\nFinal resource check:")
        check_resource_constraints()
        
        # Execution time
        execution_time = time.time() - start_time
        logger.info(f"\n==== Demo completed successfully in {execution_time:.2f} seconds ====")
        return True
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        execution_time = time.time() - start_time
        logger.info(f"Demo failed after {execution_time:.2f} seconds")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
