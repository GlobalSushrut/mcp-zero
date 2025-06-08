"""
MCP-ZERO SDK: Agent Module

This module provides the Agent class, which is the primary interface for
interacting with the MCP-ZERO AI agent infrastructure.

The Agent class implements the core lifecycle methods:
- spawn: Create a new agent with unique ID
- attach_plugin: Add capabilities through sandboxed plugins
- execute: Run traceable operations
- snapshot: Create runtime snapshots
- recover: Restore agent state
"""

import os
import time
import uuid
import logging
import json
from typing import Dict, Any, List, Optional, Union
import requests

from .exceptions import MCPError, ResourceLimitError, EthicalPolicyViolation
from .plugin import Plugin, PluginRegistry
from .monitoring import ResourceMonitor
from .crypto import sign_operation, verify_signature

# Configure logging
logger = logging.getLogger("mcp_zero")

# Constants
DEFAULT_API_URL = "http://localhost:8082"  # Default to local API
DEFAULT_TIMEOUT = 10.0  # Default request timeout
AGENT_CONFIG_PATH = os.path.expanduser("~/.mcp_zero/agents")


class Agent:
    """
    The Agent class represents an AI agent in the MCP-ZERO ecosystem.
    
    Agents are lightweight, resource-constrained entities that can be
    extended with capabilities through sandboxed plugins.
    """
    
    def __init__(self, agent_id: str, name: Optional[str] = None, api_url: Optional[str] = None):
        """
        Initialize an agent with the given ID.
        
        Args:
            agent_id: The unique identifier for this agent
            name: Optional human-readable name
            api_url: Optional API endpoint (defaults to local server)
        """
        self.id = agent_id
        self.name = name or f"agent-{agent_id[:8]}"
        self.api_url = api_url or os.environ.get("MCP_ZERO_API_URL", DEFAULT_API_URL)
        self.plugins: List[Plugin] = []
        self.resource_monitor = ResourceMonitor()
        self.headers = {"Content-Type": "application/json"}
        self._session = requests.Session()
        
        # Start resource monitoring
        self.resource_monitor.start_monitoring()
        
        logger.debug(f"Agent {self.name} ({self.id}) initialized with API endpoint {self.api_url}")

    @classmethod
    def spawn(cls, name: Optional[str] = None, api_url: Optional[str] = None) -> 'Agent':
        """
        Spawn a new agent with a unique ID.
        
        Args:
            name: Optional human-readable name
            api_url: Optional API endpoint
            
        Returns:
            A new Agent instance
            
        Raises:
            MCPError: If agent creation fails
        """
        # Create a new agent ID
        agent_id = str(uuid.uuid4())
        
        # Create the agent locally first
        agent = cls(agent_id=agent_id, name=name, api_url=api_url)
        
        try:
            # Register with the API
            endpoint = f"{agent.api_url}/api/v1/agents"
            payload = {
                "id": agent_id,
                "name": agent.name,
                "metadata": {
                    "created_at": time.time(),
                    "sdk_version": agent._get_sdk_version()
                }
            }
            
            # Sign the request
            signature = sign_operation("spawn", payload)
            payload["signature"] = signature
            
            # Make the request with resource monitoring
            with agent.resource_monitor.track_operation("spawn"):
                response = agent._session.post(
                    endpoint, 
                    json=payload,
                    headers=agent.headers,
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code != 201:
                    error_msg = f"Failed to create agent: {response.status_code}"
                    if response.text:
                        error_msg += f" - {response.text}"
                    raise MCPError(error_msg)
                
                # Save agent info locally
                agent._save_local_config()
                
                logger.info(f"Agent {agent.name} ({agent.id}) successfully created")
                return agent
                
        except Exception as e:
            logger.error(f"Agent creation failed: {str(e)}")
            raise MCPError(f"Failed to create agent: {str(e)}") from e
    
    def attach_plugin(self, plugin: Plugin) -> bool:
        """
        Attach a plugin to this agent.
        
        Plugins provide additional capabilities to the agent in a
        sandboxed environment with resource controls.
        
        Args:
            plugin: The Plugin instance to attach
            
        Returns:
            True if the plugin was successfully attached
            
        Raises:
            MCPError: If the plugin could not be attached
        """
        try:
            endpoint = f"{self.api_url}/api/v1/agents/{self.id}/plugins"
            
            payload = {
                "agent_id": self.id,
                "plugin_id": plugin.id,
                "plugin_name": plugin.name,
                "plugin_version": plugin.version,
                "plugin_hash": plugin.hash
            }
            
            # Sign the request
            signature = sign_operation("attach_plugin", payload)
            payload["signature"] = signature
            
            # Make the request with resource monitoring
            with self.resource_monitor.track_operation("attach_plugin"):
                response = self._session.post(
                    endpoint, 
                    json=payload,
                    headers=self.headers,
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code != 200:
                    error_msg = f"Failed to attach plugin: {response.status_code}"
                    if response.text:
                        error_msg += f" - {response.text}"
                    raise MCPError(error_msg)
                
                # Add to local plugins list
                self.plugins.append(plugin)
                logger.info(f"Plugin {plugin.name} successfully attached to agent {self.name}")
                return True
                
        except Exception as e:
            logger.error(f"Plugin attachment failed: {str(e)}")
            raise MCPError(f"Failed to attach plugin: {str(e)}") from e
    
    def execute(self, 
                intent: str, 
                inputs: Dict[str, Any], 
                policy_constraints: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        """
        Execute an operation with the given intent and inputs.
        
        This method enforces resource constraints and ethical policies.
        
        Args:
            intent: The intention of the operation
            inputs: Input parameters for the operation
            policy_constraints: Optional ethical policy constraints
            
        Returns:
            The operation results
            
        Raises:
            ResourceLimitError: If operation would exceed resource constraints
            EthicalPolicyViolation: If operation would violate ethical policies
            MCPError: If execution fails
        """
        try:
            endpoint = f"{self.api_url}/api/v1/agents/{self.id}/execute"
            
            payload = {
                "agent_id": self.id,
                "intent": intent,
                "inputs": inputs,
                "timestamp": time.time(),
                "policy_constraints": policy_constraints or {}
            }
            
            # Sign the request
            signature = sign_operation("execute", payload)
            payload["signature"] = signature
            
            # Check if we have enough resources
            if not self.resource_monitor.check_available_resources():
                raise ResourceLimitError(
                    f"Cannot execute operation: would exceed resource constraints "
                    f"(CPU: {self.resource_monitor.get_cpu_percent()}%, "
                    f"Memory: {self.resource_monitor.get_memory_mb()}MB)"
                )
            
            # Make the request with resource monitoring
            with self.resource_monitor.track_operation("execute"):
                response = self._session.post(
                    endpoint, 
                    json=payload,
                    headers=self.headers,
                    timeout=DEFAULT_TIMEOUT
                )
                
                # Handle various response scenarios
                if response.status_code == 403:
                    error_data = response.json()
                    if "policy_violation" in error_data:
                        raise EthicalPolicyViolation(error_data["policy_violation"])
                    raise MCPError(f"Permission denied: {response.text}")
                    
                elif response.status_code != 200:
                    error_msg = f"Execution failed with status {response.status_code}"
                    if response.text:
                        error_msg += f": {response.text}"
                    raise MCPError(error_msg)
                
                # Return the execution results
                result = response.json()
                
                # Verify the result signature
                if "signature" in result:
                    if not verify_signature("execute_result", result):
                        logger.warning(f"Result signature verification failed for agent {self.id}")
                
                logger.info(f"Agent {self.name} successfully executed intent: {intent}")
                return result
                
        except ResourceLimitError:
            # Re-raise resource errors
            raise
        except EthicalPolicyViolation:
            # Re-raise ethical violations
            raise
        except Exception as e:
            logger.error(f"Execution failed: {str(e)}")
            raise MCPError(f"Failed to execute operation: {str(e)}") from e
    
    def snapshot(self, metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Create a snapshot of the agent's current state.
        
        Args:
            metadata: Optional metadata for the snapshot
            
        Returns:
            Snapshot ID string
            
        Raises:
            MCPError: If snapshot creation fails
        """
        try:
            endpoint = f"{self.api_url}/api/v1/agents/{self.id}/snapshots"
            
            payload = {
                "agent_id": self.id,
                "timestamp": time.time(),
                "metadata": metadata or {}
            }
            
            # Sign the request
            signature = sign_operation("snapshot", payload)
            payload["signature"] = signature
            
            # Make the request with resource monitoring
            with self.resource_monitor.track_operation("snapshot"):
                response = self._session.post(
                    endpoint, 
                    json=payload,
                    headers=self.headers,
                    timeout=DEFAULT_TIMEOUT
                )
                
                if response.status_code != 201:
                    error_msg = f"Failed to create snapshot: {response.status_code}"
                    if response.text:
                        error_msg += f" - {response.text}"
                    raise MCPError(error_msg)
                
                result = response.json()
                snapshot_id = result.get("snapshot_id")
                
                logger.info(f"Snapshot {snapshot_id} created for agent {self.name}")
                return snapshot_id
                
        except Exception as e:
            logger.error(f"Snapshot creation failed: {str(e)}")
            raise MCPError(f"Failed to create snapshot: {str(e)}") from e
    
    @classmethod
    def recover(cls, snapshot_id: str, api_url: Optional[str] = None) -> 'Agent':
        """
        Recover an agent from a snapshot.
        
        Args:
            snapshot_id: The ID of the snapshot to recover from
            api_url: Optional API endpoint
            
        Returns:
            A reconstructed Agent instance
            
        Raises:
            MCPError: If recovery fails
        """
        api_url = api_url or os.environ.get("MCP_ZERO_API_URL", DEFAULT_API_URL)
        
        try:
            # First get snapshot metadata
            session = requests.Session()
            endpoint = f"{api_url}/api/v1/snapshots/{snapshot_id}"
            
            response = session.get(
                endpoint,
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to retrieve snapshot: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise MCPError(error_msg)
            
            snapshot_data = response.json()
            agent_id = snapshot_data.get("agent_id")
            
            if not agent_id:
                raise MCPError("Invalid snapshot data: missing agent_id")
            
            # Now recover the agent
            recovery_endpoint = f"{api_url}/api/v1/agents/{agent_id}/recover"
            
            payload = {
                "snapshot_id": snapshot_id,
                "timestamp": time.time()
            }
            
            # Sign the request
            signature = sign_operation("recover", payload)
            payload["signature"] = signature
            
            response = session.post(
                recovery_endpoint,
                json=payload,
                headers={"Content-Type": "application/json"},
                timeout=DEFAULT_TIMEOUT
            )
            
            if response.status_code != 200:
                error_msg = f"Failed to recover agent: {response.status_code}"
                if response.text:
                    error_msg += f" - {response.text}"
                raise MCPError(error_msg)
            
            # Get the recovered agent metadata
            agent_data = response.json()
            name = agent_data.get("name")
            
            # Create a new agent instance
            agent = cls(agent_id=agent_id, name=name, api_url=api_url)
            
            # Populate plugins from the snapshot data
            plugin_data = snapshot_data.get("plugins", [])
            registry = PluginRegistry()
            
            for plugin_info in plugin_data:
                plugin_id = plugin_info.get("id")
                if plugin_id:
                    plugin = registry.get_plugin(plugin_id)
                    if plugin:
                        agent.plugins.append(plugin)
            
            logger.info(f"Agent {agent.name} ({agent.id}) recovered from snapshot {snapshot_id}")
            return agent
            
        except Exception as e:
            logger.error(f"Agent recovery failed: {str(e)}")
            raise MCPError(f"Failed to recover agent: {str(e)}") from e
    
    def _save_local_config(self) -> None:
        """Save agent configuration to local disk for persistence"""
        try:
            # Create directory if it doesn't exist
            os.makedirs(AGENT_CONFIG_PATH, exist_ok=True)
            
            # Save agent config
            config_path = os.path.join(AGENT_CONFIG_PATH, f"{self.id}.json")
            config = {
                "id": self.id,
                "name": self.name,
                "api_url": self.api_url,
                "created_at": time.time(),
                "plugins": [p.to_dict() for p in self.plugins]
            }
            
            with open(config_path, 'w') as f:
                json.dump(config, f)
                
            logger.debug(f"Saved agent config to {config_path}")
            
        except Exception as e:
            logger.warning(f"Failed to save agent config: {str(e)}")
    
    def _get_sdk_version(self) -> str:
        """Get the SDK version"""
        try:
            from .version import __version__
            return __version__
        except ImportError:
            return "unknown"
    
    def __del__(self):
        """Cleanup when the agent is garbage collected"""
        try:
            self.resource_monitor.stop_monitoring()
        except:
            pass
