"""
LLM Service for MCP Zero Editor

Provides resilient access to LLM APIs with offline-first capability.
"""

import os
import time
import json
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Callable

# Add parent directory to path to import MCP Zero components
import sys
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import MCP Zero resilient components
from src.security import rate_limiter
from src.api import telemetry_collector

logger = logging.getLogger("mcp_zero.editor.llm_service")


class LLMServiceMode(Enum):
    """Operating modes for LLM service."""
    ONLINE = "online"   # Connected to external API
    OFFLINE = "offline"  # Using local fallbacks only


class LLMService:
    """
    Resilient service for LLM API integration.
    
    Follows offline-first approach with graceful fallback to local
    processing if API is unavailable.
    """
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        local_cache_dir: Optional[str] = None,
        model_name: str = "gpt-4"
    ):
        """
        Initialize LLM service.
        
        Args:
            api_key: API key for LLM service (None to use env var)
            api_endpoint: API endpoint URL (None for default)
            local_cache_dir: Directory for local caching
            model_name: Default model to use
        """
        # Use environment variable if no API key provided
        self.api_key = api_key or os.environ.get("LLM_API_KEY")
        self.api_endpoint = api_endpoint
        self.model_name = model_name
        
        # Default local cache directory
        self.cache_dir = local_cache_dir or os.path.expanduser("~/.mcp_editor/llm_cache")
        os.makedirs(self.cache_dir, exist_ok=True)
        
        # Start in offline mode by default
        self.mode = LLMServiceMode.OFFLINE
        self._lock = threading.RLock()
        
        # Rate limiter for API calls
        self.rate_limiter = rate_limiter.get_limiter("llm_api")
        if not self.rate_limiter:
            self.rate_limiter = rate_limiter.create_limiter(
                name="llm_api",
                requests_per_period=60,  # Default: 1 request per second
                period_seconds=60
            )
        
        # Try to connect to API if credentials provided
        if self.api_key:
            self._try_connect()
        
        logger.info(f"LLM service initialized in {self.mode.value} mode")
        
    def _try_connect(self) -> bool:
        """
        Try to connect to LLM API.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import requests
            
            # Simple health check request
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            # Use a minimal request to test connection
            data = {
                "model": self.model_name,
                "messages": [{"role": "user", "content": "Hello"}],
                "max_tokens": 5
            }
            
            # Test endpoint
            endpoint = self.api_endpoint or "https://api.openai.com/v1/chat/completions"
            
            response = requests.post(
                endpoint,
                headers=headers,
                json=data,
                timeout=5.0
            )
            
            if response.status_code == 200:
                self.mode = LLMServiceMode.ONLINE
                logger.info("Successfully connected to LLM API")
                return True
            else:
                logger.warning(f"Failed to connect to LLM API: {response.status_code}")
                return False
                
        except Exception as e:
            logger.warning(f"Failed to connect to LLM API: {str(e)}")
            return False
    
    def complete(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Get completion from LLM.
        
        Args:
            prompt: The prompt to complete
            context: Additional context
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response containing completion
        """
        # Record telemetry
        start_time = time.time()
        telemetry_collector.record(
            "llm.request",
            mode=self.mode.value,
            prompt_length=len(prompt)
        )
        
        # Check rate limit first
        if not self.rate_limiter.allow_request("default"):
            logger.warning("Rate limit exceeded for LLM API")
            return {
                "error": "Rate limit exceeded",
                "text": "I'm processing too many requests right now. Please try again later."
            }
        
        # Try online mode first if available
        if self.mode == LLMServiceMode.ONLINE and self.api_key:
            try:
                result = self._online_complete(prompt, context, max_tokens)
                
                # Record telemetry for successful completion
                telemetry_collector.record(
                    "llm.response",
                    mode=self.mode.value,
                    duration_ms=(time.time() - start_time) * 1000,
                    success=True
                )
                
                return result
            except Exception as e:
                logger.error(f"Error in online completion: {str(e)}")
                # Fall back to offline mode
                self.mode = LLMServiceMode.OFFLINE
                logger.warning("Switched to offline mode due to API error")
        
        # Use offline mode as fallback
        result = self._offline_complete(prompt, context, max_tokens)
        
        # Record telemetry for offline completion
        telemetry_collector.record(
            "llm.response",
            mode=self.mode.value,
            duration_ms=(time.time() - start_time) * 1000,
            success=True,
            fallback=True
        )
        
        return result
    
    def _online_complete(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Get completion from online LLM API.
        
        Args:
            prompt: The prompt to complete
            context: Additional context
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response containing completion
        """
        import requests
        
        full_prompt = prompt
        if context:
            full_prompt = f"{context}\n\n{prompt}"
        
        # Prepare API request
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        data = {
            "model": self.model_name,
            "messages": [{"role": "user", "content": full_prompt}],
            "max_tokens": max_tokens
        }
        
        # Make API request
        endpoint = self.api_endpoint or "https://api.openai.com/v1/chat/completions"
        response = requests.post(
            endpoint,
            headers=headers,
            json=data,
            timeout=30.0
        )
        
        # Process response
        if response.status_code == 200:
            result = response.json()
            return {
                "text": result["choices"][0]["message"]["content"],
                "model": result.get("model", self.model_name),
                "tokens": {
                    "prompt": result.get("usage", {}).get("prompt_tokens", 0),
                    "completion": result.get("usage", {}).get("completion_tokens", 0),
                    "total": result.get("usage", {}).get("total_tokens", 0)
                }
            }
        else:
            raise Exception(f"API error: {response.status_code} - {response.text}")
            
    def _offline_complete(
        self,
        prompt: str,
        context: Optional[str] = None,
        max_tokens: int = 1000
    ) -> Dict[str, Any]:
        """
        Get completion using offline fallbacks.
        
        Args:
            prompt: The prompt to complete
            context: Additional context
            max_tokens: Maximum tokens to generate
            
        Returns:
            Response containing completion
        """
        # Try to find in cache first
        cache_key = self._get_cache_key(prompt)
        cached = self._get_from_cache(cache_key)
        
        if cached:
            return cached
        
        # Basic fallback response
        return {
            "text": "I'm currently operating in offline mode and can't process your request. "
                   "Please check your API key and internet connection.",
            "tokens": {
                "prompt": len(prompt) // 4,  # Rough estimate
                "completion": 0,
                "total": len(prompt) // 4
            },
            "model": "offline-fallback"
        }
    
    def _get_cache_key(self, prompt: str) -> str:
        """Generate cache key from prompt."""
        import hashlib
        return hashlib.md5(prompt.encode('utf-8')).hexdigest()
    
    def _get_from_cache(self, cache_key: str) -> Optional[Dict[str, Any]]:
        """Get cached response if available."""
        cache_path = os.path.join(self.cache_dir, f"{cache_key}.json")
        
        if os.path.exists(cache_path):
            try:
                with open(cache_path, 'r') as f:
                    return json.load(f)
            except Exception:
                pass
        
        return None
