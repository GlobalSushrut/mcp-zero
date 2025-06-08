#!/usr/bin/env python3
"""
MCP-ZERO API Endpoint Discovery
Maps available endpoints on the MCP-ZERO RPC server
"""

import requests
import json
import sys
import logging
from typing import Dict, List, Any, Tuple

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("discovery")

# Constants
API_URL = "http://localhost:8081"
DEFAULT_TIMEOUT = 2  # seconds

def test_endpoint(method: str, endpoint: str, data: Dict = None) -> Tuple[bool, Any]:
    """Test if an endpoint exists and is accessible"""
    url = f"{API_URL}/{endpoint.lstrip('/')}"
    headers = {"Content-Type": "application/json"}
    
    try:
        if method.lower() == "get":
            response = requests.get(url, headers=headers, timeout=DEFAULT_TIMEOUT)
        else:  # POST
            response = requests.post(url, headers=headers, json=data, timeout=DEFAULT_TIMEOUT)
        
        # Check if endpoint exists (not 404)
        if response.status_code == 404:
            return False, None
            
        # Try to parse response as JSON
        try:
            result = response.json()
        except:
            result = response.text
            
        return True, {
            "status_code": response.status_code,
            "response": result
        }
        
    except requests.RequestException as e:
        return False, f"Error: {str(e)}"

def discover_endpoints():
    """Discover available API endpoints"""
    logger.info("=== MCP-ZERO API Endpoint Discovery ===")
    
    # Common API paths to test
    test_paths = [
        # Root endpoints
        ("GET", ""),
        ("GET", "api"),
        ("GET", "api/v1"),
        
        # Agent endpoints
        ("GET", "api/v1/agents"),
        ("POST", "api/v1/agents", {"name": "discovery-test-agent"}),
        
        # Try to find an existing agent for further testing
        ("GET", "api/v1/agents?limit=1"),
    ]
    
    # Store successful endpoints
    available_endpoints = {}
    test_agent_id = None
    
    # Test initial endpoints
    for method, path, *args in test_paths:
        data = args[0] if args else None
        logger.info(f"Testing {method} /{path}")
        exists, result = test_endpoint(method, path, data)
        
        if exists:
            available_endpoints[f"{method} /{path}"] = result
            logger.info(f"✓ Endpoint available: {result}")
            
            # Try to extract an agent ID for further testing
            if path == "api/v1/agents?limit=1" and result and isinstance(result.get("response"), dict):
                agents = result.get("response", {}).get("agents", [])
                if agents and len(agents) > 0:
                    test_agent_id = agents[0]
                    logger.info(f"Found test agent: {test_agent_id}")
                    
        else:
            logger.info(f"✗ Endpoint not available")
    
    # If we have a test agent, check agent-specific endpoints
    if test_agent_id:
        agent_paths = [
            # Agent-specific endpoints
            ("GET", f"api/v1/agents/{test_agent_id}"),
            ("GET", f"api/v1/agents/{test_agent_id}/plugins"),
            ("POST", f"api/v1/agents/{test_agent_id}/plugins", {"plugin_id": "discovery-test"}),
            ("POST", f"api/v1/agents/{test_agent_id}/execute", {
                "intent": "test_intent", 
                "inputs": {"test": "value"}
            }),
            ("GET", f"api/v1/agents/{test_agent_id}/snapshots"),
            ("POST", f"api/v1/agents/{test_agent_id}/snapshots", {"metadata": {"test": True}}),
        ]
        
        # Test agent-specific endpoints
        for method, path, *args in agent_paths:
            data = args[0] if args else None
            logger.info(f"Testing {method} /{path}")
            exists, result = test_endpoint(method, path, data)
            
            if exists:
                available_endpoints[f"{method} /{path}"] = result
                logger.info(f"✓ Endpoint available: {result}")
                
                # Check for snapshot creation
                if "snapshots" in path and method == "POST" and result:
                    snapshot_id = result.get("response", {}).get("snapshot_id")
                    if snapshot_id:
                        logger.info(f"Testing snapshot recovery: {snapshot_id}")
                        recovery_exists, recovery_result = test_endpoint(
                            "POST", 
                            f"api/v1/snapshots/{snapshot_id}/recover", 
                            {"snapshot_id": snapshot_id}
                        )
                        if recovery_exists:
                            available_endpoints[f"POST /api/v1/snapshots/{snapshot_id}/recover"] = recovery_result
                            logger.info(f"✓ Recovery endpoint available: {recovery_result}")
            else:
                logger.info(f"✗ Endpoint not available")
    
    # Print summary
    logger.info("\n=== MCP-ZERO API Endpoint Summary ===")
    if available_endpoints:
        for endpoint, result in available_endpoints.items():
            status = result.get("status_code") if isinstance(result, dict) else "Unknown"
            logger.info(f"{endpoint} - Status: {status}")
    else:
        logger.info("No endpoints available")
    
    # Return available endpoints
    return available_endpoints

if __name__ == "__main__":
    try:
        endpoints = discover_endpoints()
        
        # Save endpoints to file
        with open("discovered_endpoints.json", "w") as f:
            json.dump(endpoints, f, indent=2)
        
        logger.info(f"Endpoint discovery completed. Results saved to discovered_endpoints.json")
        sys.exit(0)
    except Exception as e:
        logger.error(f"Discovery failed: {str(e)}")
        sys.exit(1)
