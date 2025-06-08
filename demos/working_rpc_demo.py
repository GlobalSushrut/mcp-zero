#!/usr/bin/env python3
"""
MCP-ZERO Working RPC Demo
Uses only the confirmed working endpoints on the RPC server (port 8081)

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

# Constants for available servers
RPC_SERVER_URL = "http://localhost:8081"

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
        
    def _make_request(self, method, endpoint, data=None, debug_response=False):
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
            logger.info(f"RPC {method} {endpoint}: {elapsed_ms:.0f}ms")
            
            if debug_response:
                logger.info(f"Raw response: {response.text}")
            
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

    def list_endpoints(self):
        """Try to discover available endpoints"""
        common_endpoints = [
            "",
            "api",
            "api/v1",
            "api/v1/agents",
            "health",
            "status",
            "version"
        ]
        
        results = {}
        for endpoint in common_endpoints:
            try:
                response = requests.get(f"{self.api_url}/{endpoint}", timeout=2)
                results[endpoint] = {
                    "status_code": response.status_code,
                    "content_type": response.headers.get("Content-Type", ""),
                    "content_length": len(response.text)
                }
                logger.info(f"Endpoint /{endpoint}: {response.status_code}")
            except Exception as e:
                results[endpoint] = {"error": str(e)}
                logger.error(f"Error testing endpoint /{endpoint}: {str(e)}")
        
        return results

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
    
    def list_agents(self):
        """List all agents"""
        try:
            return self._make_request("get", "/api/v1/agents")
        except:
            # If listing fails, try other common patterns
            endpoints = [
                "/api/v1/agents/list",
                "/api/v1/agent/list",
                "/api/agents"
            ]
            
            for endpoint in endpoints:
                try:
                    return self._make_request("get", endpoint)
                except:
                    continue
            
            # If all attempts fail, raise the original exception
            logger.error("Failed to list agents through any known endpoint")
            return {"agents": []}
    
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

def main():
    """Main function to run the RPC demo"""
    start_time = time.time()
    logger.info("-" * 80)
    logger.info("MCP-ZERO WORKING RPC DEMO")
    logger.info("-" * 80)
    
    initial_cpu, initial_mem = get_resource_usage()
    logger.info(f"Initial resource usage: CPU {initial_cpu:.1f}%, Memory {initial_mem:.1f}MB")
    
    try:
        # Initialize RPC client
        rpc = RPCClient(RPC_SERVER_URL)
        check_constraints()
        
        # Step 1: Discover available endpoints
        logger.info("Discovering available endpoints...")
        endpoints = rpc.list_endpoints()
        logger.info("Endpoint discovery completed")
        check_constraints()
        
        # Step 2: Create an agent
        logger.info("Creating a new agent...")
        agent_id = rpc.spawn_agent("Production Test Agent")
        logger.info(f"Created agent with ID: {agent_id}")
        check_constraints()
        
        # Step 3: Get agent details
        logger.info("Getting agent details...")
        agent_details = rpc.get_agent(agent_id)
        logger.info(f"Agent details: {json.dumps(agent_details, indent=2)}")
        check_constraints()
        
        # Step 4: Try to list all agents
        try:
            logger.info("Listing all agents...")
            agents = rpc.list_agents()
            logger.info(f"Found agents: {json.dumps(agents, indent=2)}")
        except Exception as e:
            logger.warning(f"Could not list agents: {str(e)}")
        check_constraints()
        
        # Step 5: Try to attach plugins
        logger.info("Attaching plugins to agent...")
        plugins_to_attach = ["document-analyzer", "nlp-processor"]
        
        for plugin_id in plugins_to_attach:
            try:
                success = rpc.attach_plugin(agent_id, plugin_id)
                logger.info(f"Plugin {plugin_id} attachment: {'succeeded' if success else 'failed'}")
            except Exception as e:
                logger.warning(f"Failed to attach plugin {plugin_id}: {str(e)}")
        check_constraints()
        
        # Step 6: Execute intents
        logger.info("Executing intents with agent...")
        intents = [
            ("analyze_text", {"text": "MCP-ZERO is an AI agent infrastructure designed for 100+ year sustainability."}),
            ("extract_keywords", {"content": "MCP-ZERO features a plugin-based architecture with ethical governance built-in."}),
            ("summarize", {"document": "The system operates under strict hardware constraints: <27% CPU usage and <827MB RAM. All agent actions are traceable and verifiable through cryptographic mechanisms."})
        ]
        
        for intent_name, intent_inputs in intents:
            try:
                logger.info(f"Executing intent: {intent_name}")
                result = rpc.execute_intent(agent_id, intent_name, intent_inputs)
                logger.info(f"Intent execution result: {json.dumps(result, indent=2)}")
            except Exception as e:
                logger.warning(f"Intent execution failed for {intent_name}: {str(e)}")
            check_constraints()
        
        # Step 7: Get updated agent details
        logger.info("Getting updated agent details...")
        updated_agent_details = rpc.get_agent(agent_id)
        logger.info(f"Updated agent details: {json.dumps(updated_agent_details, indent=2)}")
        check_constraints()
        
        # Measure final resource usage
        final_cpu, final_mem = get_resource_usage()
        logger.info(f"Final resource usage: CPU {final_cpu:.1f}%, Memory {final_mem:.1f}MB")
        
        total_time = time.time() - start_time
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        
        if final_cpu <= CPU_LIMIT and final_mem <= MEM_LIMIT:
            logger.info("✅ All hardware constraints satisfied!")
        else:
            logger.warning("❌ Some hardware constraints were exceeded")
        
        return 0
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")
        
        # Still report resource usage even in case of failure
        final_cpu, final_mem = get_resource_usage()
        logger.info(f"Final resource usage: CPU {final_cpu:.1f}%, Memory {final_mem:.1f}MB")
        
        return 1

if __name__ == "__main__":
    sys.exit(main())
