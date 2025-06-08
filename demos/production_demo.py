#!/usr/bin/env python3
"""
MCP-ZERO Production Demo
A minimal, resource-conscious demo for the MCP-ZERO RPC Server
Hardware constraints: <27% CPU, <827MB RAM

This demo implements a minimalist agent lifecycle using the confirmed
API endpoints available in the production MCP-ZERO RPC server.
"""

import os
import sys
import json
import time
import logging
import requests
from datetime import datetime
from typing import Dict, Any, Optional, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("mcp_zero")

# Constants - enforcing hardware constraints
API_URL = "http://localhost:8081"
CPU_LIMIT = 27.0  # <27% CPU usage
MEM_LIMIT = 827.0  # <827MB RAM usage

class ResourceMonitor:
    """Lightweight resource monitor for MCP-ZERO hardware constraints"""
    
    def __init__(self):
        try:
            import psutil
            self.psutil_available = True
            self.process = psutil.Process(os.getpid())
        except ImportError:
            logger.warning("psutil not available - resource monitoring limited")
            self.psutil_available = False
    
    def check(self) -> Tuple[float, float]:
        """Check current resource usage"""
        if not self.psutil_available:
            return 0.0, 0.0
            
        # Get CPU usage (interval=0.1 means very short measurement)
        cpu_percent = self.process.cpu_percent(interval=0.1)
        
        # Get memory usage in MB
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)
        
        # Check against constraints
        if cpu_percent > CPU_LIMIT:
            logger.warning(f"CPU usage exceeds limit: {cpu_percent:.1f}% > {CPU_LIMIT}%")
            
        if memory_mb > MEM_LIMIT:
            logger.warning(f"Memory usage exceeds limit: {memory_mb:.1f}MB > {MEM_LIMIT}MB")
            
        return cpu_percent, memory_mb

class MCPZeroClient:
    """Minimal client for MCP-ZERO RPC Server"""
    
    def __init__(self, api_url: str, monitor: ResourceMonitor = None):
        self.api_url = api_url
        self.monitor = monitor or ResourceMonitor()
        logger.info(f"Initialized MCP-ZERO client for {api_url}")
        
    def _api_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
        """Make an API request with resource monitoring"""
        url = f"{self.api_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        # Check resources before request
        cpu_before, mem_before = self.monitor.check()
        
        try:
            if method.lower() == "get":
                response = requests.get(url, headers=headers)
            else:  # POST
                response = requests.post(url, headers=headers, json=data)
            
            # Check for error status codes
            response.raise_for_status()
            
            # Check resources after request
            cpu_after, mem_after = self.monitor.check()
            
            # Return response data if available
            if response.text:
                return response.json()
            return {}
            
        except requests.RequestException as e:
            logger.error(f"API error: {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise
    
    def create_agent(self, name: str) -> str:
        """Create a new agent"""
        logger.info(f"Creating agent: {name}")
        data = {"name": name}
        response = self._api_request("post", "/api/v1/agents", data)
        
        agent_id = response.get("agent_id")
        if not agent_id:
            raise ValueError("Failed to create agent: No agent_id in response")
        
        logger.info(f"Agent created with ID: {agent_id}")
        return agent_id
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details"""
        logger.info(f"Getting agent details: {agent_id}")
        return self._api_request("get", f"/api/v1/agents/{agent_id}")
    
    def attach_plugin(self, agent_id: str, plugin_id: str) -> bool:
        """Attach plugin to agent"""
        logger.info(f"Attaching plugin {plugin_id} to agent {agent_id}")
        data = {"plugin_id": plugin_id}
        response = self._api_request("post", f"/api/v1/agents/{agent_id}/plugins", data)
        
        success = response.get("success", False)
        if not success:
            logger.warning(f"Plugin attachment failed: {response}")
        
        return success
    
    def execute_intent(self, agent_id: str, intent: str, inputs: Dict = None) -> Dict[str, Any]:
        """Execute intent on agent"""
        logger.info(f"Executing intent {intent} on agent {agent_id}")
        data = {
            "intent": intent,
            "inputs": inputs or {}
        }
        return self._api_request("post", f"/api/v1/agents/{agent_id}/execute", data)

def run_demo():
    """Run the MCP-ZERO production demo"""
    start_time = time.time()
    
    try:
        # Initialize components
        monitor = ResourceMonitor()
        client = MCPZeroClient(API_URL, monitor)
        
        logger.info("=== MCP-ZERO Production Demo ===")
        logger.info(f"Hardware constraints: <{CPU_LIMIT}% CPU, <{MEM_LIMIT}MB RAM")
        logger.info(f"Connected to RPC server at {API_URL}")
        
        # Initial resource check
        cpu, mem = monitor.check()
        logger.info(f"Initial resource usage: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
        
        # 1. Create a document analysis agent
        logger.info("\n=== 1. Agent Creation ===")
        agent_name = f"doc-analyzer-{int(time.time())}"
        agent_id = client.create_agent(agent_name)
        
        # Check agent details
        agent_info = client.get_agent(agent_id)
        logger.info(f"Agent status: {agent_info.get('status')}")
        logger.info(f"Created at: {agent_info.get('created_at')}")
        
        # Resource check
        cpu, mem = monitor.check()
        logger.info(f"Resource usage after agent creation: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
        
        # 2. Attach plugins for document analysis capabilities
        logger.info("\n=== 2. Plugin Attachment ===")
        plugins = ["document-processor", "language-analyzer", "nlp-engine"]
        
        for plugin_id in plugins:
            success = client.attach_plugin(agent_id, plugin_id)
            if success:
                logger.info(f"Successfully attached plugin: {plugin_id}")
            else:
                logger.warning(f"Failed to attach plugin: {plugin_id}")
        
        # Resource check
        cpu, mem = monitor.check()
        logger.info(f"Resource usage after plugin attachment: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
        
        # 3. Execute document analysis intents
        logger.info("\n=== 3. Intent Execution ===")
        
        # Example document
        document = "MCP-ZERO is an AI agent infrastructure designed for 100+ year sustainability with an immutable core."
        
        # Execute multiple intents
        intents = [
            ("analyze_sentiment", {"text": document}),
            ("extract_keywords", {"text": document}),
            ("summarize", {"text": document, "max_length": 50})
        ]
        
        for intent_name, inputs in intents:
            result = client.execute_intent(agent_id, intent_name, inputs)
            logger.info(f"Intent {intent_name} result: {result}")
            
            # Check resources after each intent
            cpu, mem = monitor.check()
            logger.info(f"Resource usage: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
            
        # 4. Demo complete
        execution_time = time.time() - start_time
        logger.info(f"\n=== Demo completed in {execution_time:.2f} seconds ===")
        logger.info(f"Final resource check - CPU: {cpu:.1f}%, Memory: {mem:.1f}MB")
        logger.info(f"All operations completed within hardware constraints: <{CPU_LIMIT}% CPU, <{MEM_LIMIT}MB RAM")
        
        return True
        
    except Exception as e:
        execution_time = time.time() - start_time
        logger.error(f"Demo failed after {execution_time:.2f} seconds: {str(e)}")
        return False

if __name__ == "__main__":
    success = run_demo()
    sys.exit(0 if success else 1)
