"""
MCP-ZERO HTTP Adapter

Provides an adapter between the SDK and HTTP API exposed by the Go RPC server.
"""

import json
import logging
import requests
from typing import Dict, List, Any, Optional, Union

from .exceptions import ConnectionError, AgentError, ExecutionError

# Setup logger
logger = logging.getLogger("mcp_zero.http_adapter")

class HttpAdapter:
    """
    Adapter for MCP-ZERO HTTP API.
    
    This adapter translates between the Python SDK calls and the HTTP API endpoints
    exposed by the Go RPC server.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 8081,
        secure: bool = False,
        timeout: float = 10.0
    ):
        """
        Initialize the HTTP adapter.
        
        Args:
            host: Host address of the MCP-ZERO server.
            port: HTTP API port.
            secure: Whether to use HTTPS.
            timeout: Request timeout in seconds.
        """
        self.protocol = "https" if secure else "http"
        self.host = host
        self.port = port
        self.timeout = timeout
        self.base_url = f"{self.protocol}://{self.host}:{self.port}"
        self.connected = False
        
    def connect(self) -> None:
        """
        Check connection to the server.
        
        Raises:
            ConnectionError: If connection fails.
        """
        try:
            response = requests.get(
                f"{self.base_url}/health",
                timeout=self.timeout
            )
            response.raise_for_status()
            self.connected = True
            data = response.json()
            logger.info(f"Connected to MCP-ZERO {data.get('version', 'unknown')}")
        except (requests.RequestException, json.JSONDecodeError) as e:
            self.connected = False
            raise ConnectionError(f"Failed to connect to MCP-ZERO: {e}")
    
    def is_connected(self) -> bool:
        """Check if connected to the server."""
        return self.connected
    
    def disconnect(self) -> None:
        """Disconnect from the server."""
        self.connected = False
    
    def spawn_agent(self, config: Dict[str, Any]) -> Dict[str, Any]:
        """
        Spawn a new agent.
        
        Args:
            config: Agent configuration.
            
        Returns:
            Agent data including ID.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If agent creation fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents",
                json={"config": config},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    raise AgentError(error_data.get("error", str(e)))
                except (json.JSONDecodeError, KeyError):
                    pass
            raise AgentError(f"Failed to spawn agent: {e}")
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise AgentError(f"Failed to spawn agent: {e}")
    
    def list_agents(self, limit: int = 100, offset: int = 0) -> List[str]:
        """
        List available agent IDs.
        
        Args:
            limit: Maximum number of agents to list.
            offset: Offset for pagination.
            
        Returns:
            List of agent IDs.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If request fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            response = requests.get(
                f"{self.base_url}/api/v1/agents",
                params={"limit": limit, "offset": offset},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            return data.get("agents", [])
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise AgentError(f"Failed to list agents: {e}")
    
    def attach_plugin(self, agent_id: str, plugin_id: str) -> bool:
        """
        Attach plugin to agent.
        
        Returns:
            True on success.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If request fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/plugins",
                json={"plugin_id": plugin_id},
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise AgentError(f"Failed to attach plugin: {e}")
    
    def execute(
        self, 
        agent_id: str, 
        intent: str, 
        parameters: Optional[Dict[str, str]] = None
    ) -> Dict[str, Any]:
        """
        Execute an intent on an agent.
        
        Args:
            agent_id: Agent ID.
            intent: Intent to execute.
            parameters: Optional parameters for the intent.
            
        Returns:
            Execution result.
            
        Raises:
            ConnectionError: If not connected.
            ExecutionError: If execution fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/execute",
                json={
                    "intent": intent,
                    "parameters": parameters or {}
                },
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return response.json()
        except requests.HTTPError as e:
            if e.response.status_code == 400:
                try:
                    error_data = e.response.json()
                    raise ExecutionError(error_data.get("error", str(e)))
                except (json.JSONDecodeError, KeyError):
                    pass
            raise ExecutionError(f"Execution failed: {e}")
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise ExecutionError(f"Execution failed: {e}")
    
    def snapshot(self, agent_id: str) -> str:
        """
        Take a snapshot of an agent.
        
        Args:
            agent_id: Agent ID.
            
        Returns:
            Snapshot ID.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If request fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            response = requests.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/snapshot",
                timeout=self.timeout
            )
            
            response.raise_for_status()
            data = response.json()
            return data.get("snapshot_id", "")
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise AgentError(f"Failed to take snapshot: {e}")
    
    def recover(self, agent_id: str, snapshot_id: Optional[str] = None) -> bool:
        """
        Recover an agent from a snapshot.
        
        Args:
            agent_id: Agent ID.
            snapshot_id: Optional snapshot ID.
            
        Returns:
            True on success.
            
        Raises:
            ConnectionError: If not connected.
            AgentError: If request fails.
        """
        if not self.connected:
            raise ConnectionError("Not connected to MCP-ZERO")
        
        try:
            payload = {}
            if snapshot_id:
                payload["snapshot_id"] = snapshot_id
                
            response = requests.post(
                f"{self.base_url}/api/v1/agents/{agent_id}/recover",
                json=payload,
                timeout=self.timeout
            )
            
            response.raise_for_status()
            return True
        except (requests.RequestException, json.JSONDecodeError) as e:
            raise AgentError(f"Failed to recover agent: {e}")
