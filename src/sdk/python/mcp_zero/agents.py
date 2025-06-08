"""
MCP-ZERO Agent Module

Defines Agent abstractions and related functionality for MCP-ZERO.
"""

import time
import logging
from enum import Enum
from typing import Dict, List, Optional, Any, Union, TYPE_CHECKING

import yaml

from .exceptions import AgentError, PluginError, ExecutionError

if TYPE_CHECKING:
    from .client import MCPClient

# Setup logger
logger = logging.getLogger("mcp_zero.agents")


class AgentStatus(Enum):
    """Agent status enum."""
    ACTIVE = "active"
    RECOVERED = "recovered"
    PAUSED = "paused"
    TERMINATED = "terminated"


class HardwareConstraints:
    """
    Hardware constraints for an agent.
    
    Attrs:
        cpu_limit: Maximum CPU percentage (0-100).
        memory_limit: Maximum memory in MB.
    """
    
    def __init__(self, cpu_limit: float = 10.0, memory_limit: int = 100):
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "HardwareConstraints":
        """Create from dictionary."""
        return cls(
            cpu_limit=data.get("cpu_limit", 10.0),
            memory_limit=data.get("memory_limit", 100),
        )
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
        }


class AgentConfig:
    """
    Agent configuration.
    
    Attrs:
        name: Agent name.
        entry_plugin: Entry plugin ID.
        intents: List of supported intents.
        hm: Hardware constraints.
        metadata: Additional metadata.
    """
    
    def __init__(
        self, 
        name: str,
        entry_plugin: str,
        intents: Optional[List[str]] = None,
        hm: Optional[HardwareConstraints] = None,
        metadata: Optional[Dict[str, str]] = None,
    ):
        self.name = name
        self.entry_plugin = entry_plugin
        self.intents = intents or ["default"]
        self.hm = hm or HardwareConstraints()
        self.metadata = metadata or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "AgentConfig":
        """Create from dictionary."""
        hm = None
        if "hm" in data:
            hm = HardwareConstraints.from_dict(data["hm"])
        
        return cls(
            name=data.get("name", "default"),
            entry_plugin=data.get("entry_plugin", "core"),
            intents=data.get("intents", ["default"]),
            hm=hm,
            metadata=data.get("metadata", {}),
        )
    
    @classmethod
    def from_yaml(cls, path: str) -> "AgentConfig":
        """Create from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "name": self.name,
            "entry_plugin": self.entry_plugin,
            "intents": self.intents,
            "hm": self.hm.to_dict(),
            "metadata": self.metadata,
        }
    
    def to_yaml(self, path: str) -> None:
        """Save to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f)


class Agent:
    """
    MCP-ZERO agent representation.
    
    Provides methods for agent lifecycle management and intent execution.
    """
    
    def __init__(
        self, 
        client: "MCPClient",
        agent_id: str,
        config: AgentConfig,
        status: AgentStatus = AgentStatus.ACTIVE,
    ):
        self._client = client
        self._id = agent_id
        self._config = config
        self._status = status
        self._plugins = set()
        self._created_at = time.time()
        self._updated_at = time.time()
    
    @property
    def id(self) -> str:
        """Get agent ID."""
        return self._id
    
    @property
    def name(self) -> str:
        """Get agent name."""
        return self._config.name
    
    @property
    def status(self) -> AgentStatus:
        """Get agent status."""
        return self._status
    
    @property
    def config(self) -> AgentConfig:
        """Get agent configuration."""
        return self._config
    
    @property
    def created_at(self) -> float:
        """Get agent creation timestamp."""
        return self._created_at
    
    @property
    def updated_at(self) -> float:
        """Get agent update timestamp."""
        return self._updated_at
    
    @property
    def plugins(self) -> set:
        """Get attached plugins."""
        return self._plugins.copy()
    
    def attach_plugin(self, plugin_id: str) -> bool:
        """
        Attach a plugin to this agent.
        
        Args:
            plugin_id: Plugin ID to attach.
            
        Returns:
            True on success.
            
        Raises:
            AgentError: If agent is terminated or error occurs.
            PluginError: If plugin does not exist or attachment fails.
        """
        if self._status == AgentStatus.TERMINATED:
            raise AgentError("Cannot attach plugin to terminated agent")
        
        logger.info(f"Attaching plugin {plugin_id} to agent {self._id}")
        
        try:
            success = self._client._http_adapter.attach_plugin(self._id, plugin_id)
            if success:
                self._plugins.add(plugin_id)
                self._updated_at = time.time()
                return True
            else:
                raise PluginError(f"Failed to attach plugin {plugin_id} to agent {self._id}")
        except Exception as e:
            raise PluginError(f"Failed to attach plugin: {e}")
    
    def execute(
        self, 
        intent: str, 
        parameters: Dict[str, str] = None
    ) -> Dict[str, Any]:
        """
        Execute an intent on this agent.
        
        Args:
            intent: Intent to execute.
            parameters: Optional parameters for the intent.
            
        Returns:
            Execution result.
            
        Raises:
            AgentError: If agent is terminated.
            ExecutionError: If execution fails.
        """
        if self._status == AgentStatus.TERMINATED:
            raise AgentError("Cannot execute intent on terminated agent")
        
        if self._status == AgentStatus.PAUSED:
            logger.warning("Executing intent on paused agent")
        
        if intent not in self._config.intents:
            logger.warning(f"Intent '{intent}' not in agent's declared intents")
        
        logger.info(f"Executing intent '{intent}' on agent {self._id}")
        
        try:
            result = self._client._http_adapter.execute(self._id, intent, parameters or {})
            self._updated_at = time.time()
            return result
        except Exception as e:
            raise ExecutionError(f"Intent execution failed: {e}")
    
    def snapshot(self) -> str:
        """
        Take a snapshot of this agent's current state.
        
        Returns:
            Snapshot ID.
            
        Raises:
            AgentError: If agent is terminated or snapshot fails.
        """
        if self._status == AgentStatus.TERMINATED:
            raise AgentError("Cannot snapshot terminated agent")
        
        logger.info(f"Taking snapshot of agent {self._id}")
        
        try:
            snapshot_id = self._client._http_adapter.snapshot(self._id)
            self._updated_at = time.time()
            return snapshot_id
        except Exception as e:
            raise AgentError(f"Snapshot failed: {e}")
    
    def recover(self, snapshot_id: Optional[str] = None) -> bool:
        """
        Recover this agent from a snapshot.
        
        Args:
            snapshot_id: Optional snapshot ID. If None, uses latest.
            
        Returns:
            True on success.
            
        Raises:
            AgentError: If recovery fails.
        """
        logger.info(f"Recovering agent {self._id}")
        
        try:
            success = self._client._http_adapter.recover(self._id, snapshot_id)
            if success:
                self._status = AgentStatus.RECOVERED
                self._updated_at = time.time()
                return True
            else:
                raise AgentError(f"Recovery failed for agent {self._id}")
        except Exception as e:
            raise AgentError(f"Recovery failed: {e}")
    
    def pause(self) -> bool:
        """
        Pause this agent.
        
        Returns:
            True on success.
            
        Raises:
            AgentError: If agent is terminated or pause fails.
        """
        if self._status == AgentStatus.TERMINATED:
            raise AgentError("Cannot pause terminated agent")
        
        logger.info(f"Pausing agent {self._id}")
        
        # Will be implemented after protobuf generation
        # TODO: Implement when API supports this
        
        # Mock implementation
        self._status = AgentStatus.PAUSED
        self._updated_at = time.time()
        return True
    
    def resume(self) -> bool:
        """
        Resume this agent.
        
        Returns:
            True on success.
            
        Raises:
            AgentError: If agent is terminated or resume fails.
        """
        if self._status == AgentStatus.TERMINATED:
            raise AgentError("Cannot resume terminated agent")
        
        if self._status != AgentStatus.PAUSED:
            logger.warning("Resuming agent that is not paused")
            return True
        
        logger.info(f"Resuming agent {self._id}")
        
        # Will be implemented after protobuf generation
        # TODO: Implement when API supports this
        
        # Mock implementation
        self._status = AgentStatus.ACTIVE
        self._updated_at = time.time()
        return True
    
    def terminate(self) -> bool:
        """
        Terminate this agent.
        
        Returns:
            True on success.
        """
        if self._status == AgentStatus.TERMINATED:
            logger.warning("Agent already terminated")
            return True
        
        logger.info(f"Terminating agent {self._id}")
        
        # Will be implemented after protobuf generation
        # TODO: Implement when API supports this
        
        # Mock implementation
        self._status = AgentStatus.TERMINATED
        self._updated_at = time.time()
        return True
    
    def get_resource_usage(self) -> Dict[str, float]:
        """
        Get current resource usage.
        
        Returns:
            Dictionary with CPU and memory usage.
        """
        # Will be implemented after protobuf generation
        # TODO: Implement when API supports this
        
        # Mock implementation
        return {
            "cpu_percent": 5.0,
            "memory_mb": 20.0,
            "cpu_utilization": 50.0,  # % of allocated
            "memory_utilization": 20.0,  # % of allocated
        }
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "id": self._id,
            "name": self._config.name,
            "status": self._status.value,
            "config": self._config.to_dict(),
            "plugins": list(self._plugins),
            "created_at": self._created_at,
            "updated_at": self._updated_at,
        }
