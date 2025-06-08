#!/usr/bin/env python3
"""
MCP-ZERO Agreement Client
Handles communication with the MCP-ZERO Solidity Agreement Server
"""

import os
import sys
import json
import time
import logging
import requests
import hashlib
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mcp_zero_agreement")

class AgreementClient:
    """Client for interacting with the MCP-ZERO Agreement Server"""
    
    def __init__(self, agreement_url: str, consensus_url: str):
        """Initialize Agreement client with server URLs"""
        self.agreement_url = agreement_url
        self.consensus_url = consensus_url
        logger.info(f"Agreement Client initialized for {agreement_url}")
        logger.info(f"Consensus endpoint set to {consensus_url}")
    
    def _agreement_request(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make request to Agreement server with error handling"""
        url = f"{self.agreement_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            # Log response time
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"Agreement request {endpoint}: {elapsed_ms:.0f}ms")
            
            # Check for error status codes
            response.raise_for_status()
            
            # Return response data
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Agreement error ({endpoint}): {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise
    
    def _consensus_request(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make request to Consensus server with error handling"""
        url = f"{self.consensus_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=10)
            
            # Log response time
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"Consensus request {endpoint}: {elapsed_ms:.0f}ms")
            
            # Check for error status codes
            response.raise_for_status()
            
            # Return response data
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"Consensus error ({endpoint}): {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise
    
    def _calculate_hash(self, data: Dict) -> str:
        """Calculate SHA-256 hash of data for agreement verification"""
        data_str = json.dumps(data, sort_keys=True)
        return hashlib.sha256(data_str.encode('utf-8')).hexdigest()
    
    def create_agreement(self, agent_id: str, policy_rules: List[Dict]) -> str:
        """Create a new agent agreement with policy rules"""
        data = {
            "agent_id": agent_id,
            "policy_rules": policy_rules,
            "created_at": time.time(),
            "version": "1.0"
        }
        
        # Calculate agreement hash
        agreement_hash = self._calculate_hash(data)
        data["agreement_hash"] = agreement_hash
        
        # Submit to agreement server
        response = self._agreement_request("api/v1/agreements", data)
        
        agreement_id = response.get("agreement_id", "")
        logger.info(f"Created agreement {agreement_id} for agent {agent_id}")
        return agreement_id
    
    def verify_action(self, agent_id: str, action: str, parameters: Dict) -> Dict[str, Any]:
        """Verify if an action complies with the agreement"""
        data = {
            "agent_id": agent_id,
            "action": action,
            "parameters": parameters,
            "timestamp": time.time()
        }
        
        # Calculate action hash for verification
        action_hash = self._calculate_hash(data)
        data["action_hash"] = action_hash
        
        # Submit to agreement verification
        return self._agreement_request("api/v1/verify", data)
    
    def record_consensus(self, agreement_id: str, action_hash: str) -> bool:
        """Record consensus on the validity of an action"""
        data = {
            "agreement_id": agreement_id,
            "action_hash": action_hash,
            "timestamp": time.time()
        }
        
        # Submit to consensus server
        response = self._consensus_request("api/v1/consensus", data)
        
        return response.get("success", False)
