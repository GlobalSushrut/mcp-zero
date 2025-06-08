"""
MCP-ZERO SDK: RPC Client Module

This module provides the low-level RPC client for communicating
with the MCP-ZERO Go RPC Layer. It handles connection management,
request throttling, and resource-efficient communication.
"""

import os
import time
import json
import logging
import threading
from typing import Dict, Any, Optional, Union, List, Callable
import requests
from requests.adapters import HTTPAdapter
from urllib3.util.retry import Retry

from .exceptions import APIError, ResourceLimitError
from .monitoring import ResourceMonitor

# Configure logging
logger = logging.getLogger("mcp_zero")

# Constants
DEFAULT_API_URL = "http://localhost:8082"
DEFAULT_TIMEOUT = 10.0  # Default request timeout
DEFAULT_RETRY_ATTEMPTS = 3
DEFAULT_BACKOFF_FACTOR = 0.5
DEFAULT_STATUS_FORCELIST = [429, 500, 502, 503, 504]
MAX_CONNECTIONS = 4  # Limit connections to reduce resource usage


class RPCClient:
    """
    Low-level client for communicating with the MCP-ZERO RPC Layer.
    
    This client is designed for minimal resource usage and includes:
    - Connection pooling with limited maximum connections
    - Automatic retry with exponential backoff
    - Request throttling based on resource usage
    - Low memory JSON processing
    """
    
    def __init__(
        self,
        api_url: Optional[str] = None,
        timeout: float = DEFAULT_TIMEOUT,
        resource_monitor: Optional[ResourceMonitor] = None
    ):
        """
        Initialize the RPC client.
        
        Args:
            api_url: URL of the MCP-ZERO RPC server
            timeout: Request timeout in seconds
            resource_monitor: Optional ResourceMonitor to track usage
        """
        self.api_url = api_url or os.environ.get("MCP_ZERO_API_URL", DEFAULT_API_URL)
        self.timeout = timeout
        self.resource_monitor = resource_monitor or ResourceMonitor()
        self._session = self._create_session()
        self._request_lock = threading.Semaphore(MAX_CONNECTIONS)
        self._headers = {"Content-Type": "application/json"}
        
        # Start monitoring if not already started
        if not hasattr(self.resource_monitor, "_monitoring_thread") or not self.resource_monitor._monitoring_thread:
            self.resource_monitor.start_monitoring()
            
        logger.debug(f"RPC client initialized for {self.api_url}")
    
    def _create_session(self) -> requests.Session:
        """Create a requests session with connection pooling and retry logic"""
        session = requests.Session()
        
        # Configure connection pooling
        retry_strategy = Retry(
            total=DEFAULT_RETRY_ATTEMPTS,
            backoff_factor=DEFAULT_BACKOFF_FACTOR,
            status_forcelist=DEFAULT_STATUS_FORCELIST
        )
        # Handle compatibility with different urllib3 versions
        # (method_whitelist for older versions, allowed_methods for newer)
        retry_strategy.method_whitelist = ["GET", "POST", "PUT", "DELETE"]
        
        adapter = HTTPAdapter(
            pool_connections=MAX_CONNECTIONS,
            pool_maxsize=MAX_CONNECTIONS,
            max_retries=retry_strategy
        )
        
        session.mount("http://", adapter)
        session.mount("https://", adapter)
        
        return session
    
    def get(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a GET request to the RPC server.
        
        Args:
            endpoint: API endpoint path (without base URL)
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
            ResourceLimitError: If resource constraints would be exceeded
        """
        url = self._build_url(endpoint)
        return self._request("GET", url, params=params, headers=headers)
    
    def post(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a POST request to the RPC server.
        
        Args:
            endpoint: API endpoint path (without base URL)
            data: Request payload
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
            ResourceLimitError: If resource constraints would be exceeded
        """
        url = self._build_url(endpoint)
        return self._request("POST", url, data=data, headers=headers)
    
    def put(
        self,
        endpoint: str,
        data: Dict[str, Any],
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a PUT request to the RPC server.
        
        Args:
            endpoint: API endpoint path (without base URL)
            data: Request payload
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
            ResourceLimitError: If resource constraints would be exceeded
        """
        url = self._build_url(endpoint)
        return self._request("PUT", url, data=data, headers=headers)
    
    def delete(
        self,
        endpoint: str,
        params: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a DELETE request to the RPC server.
        
        Args:
            endpoint: API endpoint path (without base URL)
            params: Optional query parameters
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
            ResourceLimitError: If resource constraints would be exceeded
        """
        url = self._build_url(endpoint)
        return self._request("DELETE", url, params=params, headers=headers)
    
    def _request(
        self,
        method: str,
        url: str,
        params: Optional[Dict[str, Any]] = None,
        data: Optional[Dict[str, Any]] = None,
        headers: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Send a request to the RPC server with resource monitoring.
        
        Args:
            method: HTTP method (GET, POST, etc.)
            url: Full URL
            params: Optional query parameters
            data: Optional request payload
            headers: Optional additional headers
            
        Returns:
            Response data as dictionary
            
        Raises:
            APIError: If the request fails
            ResourceLimitError: If resource constraints would be exceeded
        """
        # Check if we have enough resources before making the request
        if not self.resource_monitor.check_available_resources():
            cpu = self.resource_monitor.get_cpu_percent()
            memory = self.resource_monitor.get_memory_mb()
            raise ResourceLimitError(
                f"Cannot make RPC request: would exceed resource constraints "
                f"(CPU: {cpu:.1f}%, Memory: {memory:.1f}MB)"
            )
        
        # Apply throttling based on resource trends
        self._maybe_throttle()
        
        # Merge headers
        request_headers = self._headers.copy()
        if headers:
            request_headers.update(headers)
        
        # Serialize data with minimal memory usage
        json_data = None
        if data:
            json_data = json.dumps(data)
        
        # Acquire semaphore to limit concurrent connections
        with self._request_lock:
            try:
                # Track operation resource usage
                with self.resource_monitor.track_operation(f"rpc_{method.lower()}"):
                    start_time = time.time()
                    
                    response = self._session.request(
                        method=method,
                        url=url,
                        params=params,
                        data=json_data,
                        headers=request_headers,
                        timeout=self.timeout
                    )
                    
                    elapsed = time.time() - start_time
                    logger.debug(f"{method} {url} took {elapsed:.3f}s")
                    
                    # Check for errors
                    if response.status_code >= 400:
                        self._handle_error_response(response)
                    
                    # Parse response with minimal memory usage
                    try:
                        if response.text:
                            result = response.json()
                            return result
                        return {}
                    except json.JSONDecodeError as e:
                        raise APIError(
                            f"Failed to decode JSON response: {str(e)}",
                            status_code=response.status_code,
                            response=response
                        )
            
            except requests.RequestException as e:
                raise APIError(f"Request failed: {str(e)}")
    
    def _build_url(self, endpoint: str) -> str:
        """Build a full URL from an endpoint path"""
        # Ensure endpoint starts with /
        if not endpoint.startswith("/"):
            endpoint = f"/{endpoint}"
            
        # Combine base URL and endpoint
        return f"{self.api_url}{endpoint}"
    
    def _handle_error_response(self, response: requests.Response) -> None:
        """Handle error responses from the server"""
        status_code = response.status_code
        
        try:
            error_data = response.json() if response.text else {}
            error_message = error_data.get("error", response.text or "Unknown error")
        except json.JSONDecodeError:
            error_message = response.text or f"HTTP {status_code}"
        
        # Log the error
        logger.error(f"API error: {status_code} - {error_message}")
        
        # Raise appropriate exception
        raise APIError(
            f"API error: {error_message}",
            status_code=status_code,
            response=response
        )
    
    def _maybe_throttle(self) -> None:
        """Apply throttling if resource usage is high"""
        if not hasattr(self.resource_monitor, "_cpu_samples") or not self.resource_monitor._cpu_samples:
            return
            
        # Get the latest CPU sample and check if it's high
        with self.resource_monitor._lock:
            latest_cpu = self.resource_monitor._cpu_samples[-1] if self.resource_monitor._cpu_samples else 0
            
            # Calculate throttle delay based on CPU usage
            throttle_delay = 0
            if latest_cpu > 20.0:  # If over 20% CPU
                # Progressive throttling based on CPU usage
                throttle_factor = min(1.0, (latest_cpu - 20.0) / 7.0)  # Up to 1.0 at 27% CPU
                throttle_delay = throttle_factor * 0.5  # Up to 500ms delay
                
                if throttle_delay > 0.05:  # Only log if delay is significant
                    logger.debug(f"Throttling RPC request due to high CPU ({latest_cpu:.1f}%), delay: {throttle_delay:.3f}s")
                    time.sleep(throttle_delay)
    
    def __del__(self):
        """Cleanup when the client is garbage collected"""
        # Close the session
        try:
            if hasattr(self, "_session"):
                self._session.close()
        except:
            pass
