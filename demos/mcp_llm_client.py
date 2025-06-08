#!/usr/bin/env python3
"""
MCP-ZERO LLM Client
Handles communication with the MCP-ZERO LLM Server
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List

logger = logging.getLogger("mcp_zero_llm")

class LLMClient:
    """Client for interacting with the MCP-ZERO LLM Server"""
    
    def __init__(self, llm_url: str):
        """Initialize LLM client with server URL"""
        self.llm_url = llm_url
        logger.info(f"LLM Client initialized for {llm_url}")
    
    def _llm_request(self, endpoint: str, data: Dict) -> Dict[str, Any]:
        """Make request to LLM server with error handling"""
        url = f"{self.llm_url}/{endpoint.lstrip('/')}"
        headers = {"Content-Type": "application/json"}
        
        try:
            start_time = time.time()
            response = requests.post(url, headers=headers, json=data, timeout=30)
            
            # Log response time
            elapsed_ms = (time.time() - start_time) * 1000
            logger.debug(f"LLM request to {endpoint}: {elapsed_ms:.0f}ms")
            
            # Check for error status codes
            response.raise_for_status()
            
            # Return response data
            return response.json()
            
        except requests.RequestException as e:
            logger.error(f"LLM error ({endpoint}): {str(e)}")
            if hasattr(e, "response") and e.response is not None:
                logger.error(f"Response: {e.response.status_code} - {e.response.text}")
            raise
    
    def generate_response(self, prompt: str, max_tokens: int = 100) -> str:
        """Generate a response from the LLM server"""
        data = {
            "prompt": prompt,
            "max_tokens": max_tokens,
            "temperature": 0.7,
        }
        response = self._llm_request("api/v1/generate", data)
        return response.get("text", "")
    
    def analyze_document(self, document: str, task: str) -> Dict[str, Any]:
        """Analyze a document for a specific task"""
        data = {
            "document": document,
            "task": task
        }
        return self._llm_request("api/v1/analyze", data)
    
    def extract_entities(self, text: str) -> List[Dict[str, Any]]:
        """Extract entities from text"""
        data = {"text": text}
        response = self._llm_request("api/v1/entities", data)
        return response.get("entities", [])
