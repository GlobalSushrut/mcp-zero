#!/usr/bin/env python3
"""
MCP-ZERO RPC Client
Handles communication with the MCP-ZERO RPC Layer (Go)
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mcp_zero_rpc")

class RPCClient:
    """Client for interacting with the MCP-ZERO RPC server"""
    
    def __init__(self, api_url: str):
        """Initialize RPC client with server URL"""
        self.api_url = api_url
        logger.info(f"RPC Client initialized for {api_url}")
        
    def _make_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
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

    # Core Agent Lifecycle Operations
    
    def spawn_agent(self, name: str) -> str:
        """Create a new agent using the RPC API"""
        data = {"name": name}
        response = self._make_request("post", "/api/v1/agents", data)
        
        agent_id = response.get("agent_id")
        if not agent_id:
            raise ValueError("Failed to create agent: No agent_id in response")
            
        logger.info(f"Agent spawned with ID: {agent_id}")
        return agent_id
    
    def get_agent(self, agent_id: str) -> Dict[str, Any]:
        """Get agent details"""
        return self._make_request("get", f"/api/v1/agents/{agent_id}")
    
    def attach_plugin(self, agent_id: str, plugin_id: str) -> bool:
        """Attach a plugin to an agent"""
        data = {"plugin_id": plugin_id}
        response = self._make_request("post", f"/api/v1/agents/{agent_id}/plugins", data)
        
        success = response.get("success", False)
        if not success:
            logger.warning(f"Failed to attach plugin {plugin_id} to agent {agent_id}")
            
        return success
    
    def execute_intent(self, agent_id: str, intent: str, inputs: Dict = None) -> Dict[str, Any]:
        """Execute an intent on the agent"""
        data = {
            "intent": intent,
            "inputs": inputs or {}
        }
        return self._make_request("post", f"/api/v1/agents/{agent_id}/execute", data)
    
    def list_agents(self, limit: int = 10, offset: int = 0) -> List[str]:
        """List available agents"""
        response = self._make_request("get", f"/api/v1/agents?limit={limit}&offset={offset}")
        return response.get("agents", [])
