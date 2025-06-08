#!/usr/bin/env python3
"""
MCP-ZERO DB Client
Handles communication with the MCP-ZERO Storage Layer (MongoDB+HeapBT)
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mcp_zero_db")

class DBClient:
    """Client for interacting with the MCP-ZERO Database"""
    
    def __init__(self, db_url: str):
        """Initialize DB client with server URL"""
        self.db_url = db_url
        logger.info(f"DB Client initialized for {db_url}")
    
    def _db_request(self, method: str, endpoint: str, data: Dict = None) -> Dict[str, Any]:
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
    
    # Agent state storage operations
    
    def store_agent_state(self, agent_id: str, state: Dict[str, Any]) -> bool:
        """Store agent state in the database"""
        data = {
            "agent_id": agent_id,
            "state": state,
            "timestamp": time.time()
        }
        response = self._db_request("post", "/api/v1/states", data)
        return response.get("success", False)
    
    def retrieve_agent_state(self, agent_id: str) -> Dict[str, Any]:
        """Retrieve agent state from the database"""
        response = self._db_request("get", f"/api/v1/states/{agent_id}")
        return response.get("state", {})
    
    # Plugin registry operations
    
    def register_plugin(self, plugin_id: str, metadata: Dict[str, Any]) -> bool:
        """Register a plugin in the database"""
        data = {
            "plugin_id": plugin_id,
            "metadata": metadata,
            "registered_at": time.time()
        }
        response = self._db_request("post", "/api/v1/plugins", data)
        return response.get("success", False)
    
    def get_plugin_metadata(self, plugin_id: str) -> Dict[str, Any]:
        """Get plugin metadata from the database"""
        response = self._db_request("get", f"/api/v1/plugins/{plugin_id}")
        return response.get("metadata", {})
        
    # Trace storage operations (for ZK-traceable auditing)
    
    def store_execution_trace(self, agent_id: str, intent: str, trace: Dict[str, Any]) -> str:
        """Store execution trace for ZK-traceable auditing"""
        data = {
            "agent_id": agent_id,
            "intent": intent,
            "trace": trace,
            "timestamp": time.time()
        }
        response = self._db_request("post", "/api/v1/traces", data)
        return response.get("trace_id", "")
