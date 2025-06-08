"""
MCP-ZERO Plugin Module

Defines Plugin abstractions and related functionality for MCP-ZERO plugin ecosystem.
"""

import os
import hashlib
import logging
from typing import Dict, List, Any, Optional, Union, Set, TYPE_CHECKING

import yaml

from .exceptions import PluginError

if TYPE_CHECKING:
    from .client import MCPClient

# Setup logger
logger = logging.getLogger("mcp_zero.plugins")


class PluginCapabilities:
    """
    Plugin capability declarations.
    
    Defines what a plugin is allowed to do within the MCP-ZERO sandbox.
    
    Attrs:
        state_access: Whether plugin can access agent state.
        plugin_call: Whether plugin can call other plugins.
        external_access: Whether plugin can access external resources.
        cpu_limit: Maximum CPU percentage for plugin execution.
        memory_limit: Maximum memory in MB for plugin execution.
        additional: Additional capability flags.
    """
    
    def __init__(
        self,
        state_access: bool = False,
        plugin_call: bool = False,
        external_access: bool = False,
        cpu_limit: float = 5.0,
        memory_limit: int = 50,
        additional: Dict[str, str] = None,
    ):
        self.state_access = state_access
        self.plugin_call = plugin_call
        self.external_access = external_access
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self.additional = additional or {}
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "PluginCapabilities":
        """Create from dictionary."""
        return cls(
            state_access=data.get("state_access", False),
            plugin_call=data.get("plugin_call", False),
            external_access=data.get("external_access", False),
            cpu_limit=data.get("cpu_limit", 5.0),
            memory_limit=data.get("memory_limit", 50),
            additional=data.get("additional", {}),
        )
    
    @classmethod
    def from_yaml(cls, path: str) -> "PluginCapabilities":
        """Load capabilities from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        return cls.from_dict(data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "state_access": self.state_access,
            "plugin_call": self.plugin_call,
            "external_access": self.external_access,
            "cpu_limit": self.cpu_limit,
            "memory_limit": self.memory_limit,
            "additional": self.additional,
        }
    
    def to_yaml(self, path: str) -> None:
        """Save to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f)

    def validate(self) -> bool:
        """
        Validate capabilities.
        
        Returns:
            True if valid, raises exception otherwise.
            
        Raises:
            PluginError: If capabilities are invalid.
        """
        if self.cpu_limit <= 0 or self.cpu_limit > 50:
            raise PluginError(f"Invalid CPU limit: {self.cpu_limit} (must be 0-50%)")
        
        if self.memory_limit <= 0 or self.memory_limit > 500:
            raise PluginError(f"Invalid memory limit: {self.memory_limit} (must be 0-500MB)")
        
        return True


class Plugin:
    """
    MCP-ZERO plugin representation.
    
    Attrs:
        id: Plugin identifier.
        capabilities: Plugin capabilities.
        metadata: Plugin metadata.
        wasm_path: Path to WASM module file.
    """
    
    def __init__(
        self,
        client: "MCPClient",
        plugin_id: str,
        capabilities: PluginCapabilities,
        metadata: Dict[str, str] = None,
        wasm_path: Optional[str] = None,
    ):
        self._client = client
        self._id = plugin_id
        self._capabilities = capabilities
        self._metadata = metadata or {
            "name": plugin_id,
            "version": "0.1.0",
            "author": "unknown",
            "description": "",
        }
        self._wasm_path = wasm_path
        self._hash = None
        
        # Calculate hash if WASM path is provided
        if wasm_path and os.path.exists(wasm_path):
            self._calculate_hash()
    
    @property
    def id(self) -> str:
        """Get plugin ID."""
        return self._id
    
    @property
    def capabilities(self) -> PluginCapabilities:
        """Get plugin capabilities."""
        return self._capabilities
    
    @property
    def metadata(self) -> Dict[str, str]:
        """Get plugin metadata."""
        return self._metadata.copy()
    
    @property
    def wasm_path(self) -> Optional[str]:
        """Get WASM module path."""
        return self._wasm_path
    
    @property
    def hash(self) -> Optional[str]:
        """Get plugin hash."""
        return self._hash
    
    def _calculate_hash(self) -> None:
        """Calculate BLAKE3 hash of plugin WASM module."""
        try:
            # Use BLAKE3 if available (preferred for MCP-ZERO)
            try:
                import blake3
                hasher = blake3.blake3()
            except ImportError:
                # Fall back to SHA3-256
                hasher = hashlib.sha3_256()
            
            with open(self._wasm_path, "rb") as f:
                # Read in chunks to handle large files
                for chunk in iter(lambda: f.read(4096), b""):
                    hasher.update(chunk)
            
            self._hash = hasher.hexdigest()
        except Exception as e:
            logger.warning(f"Failed to calculate plugin hash: {e}")
    
    def register(self) -> bool:
        """
        Register this plugin with MCP-ZERO.
        
        Returns:
            True on success.
            
        Raises:
            PluginError: If registration fails.
            ConnectionError: If not connected.
            FileNotFoundError: If WASM file not found.
        """
        if not self._wasm_path:
            raise PluginError("No WASM module path provided")
        
        if not os.path.exists(self._wasm_path):
            raise FileNotFoundError(f"WASM module not found: {self._wasm_path}")
        
        # Calculate hash if needed
        if not self._hash:
            self._calculate_hash()
        
        # Register with client
        self._client.register_plugin(
            plugin_id=self._id,
            wasm_path=self._wasm_path,
            capabilities=self._capabilities,
            metadata=self._metadata,
        )
        
        return True
    
    @classmethod
    def from_dict(cls, client: "MCPClient", data: Dict[str, Any]) -> "Plugin":
        """Create plugin from dictionary."""
        capabilities = PluginCapabilities.from_dict(data.get("capabilities", {}))
        
        return cls(
            client=client,
            plugin_id=data["id"],
            capabilities=capabilities,
            metadata=data.get("metadata", {}),
            wasm_path=data.get("wasm_path"),
        )
    
    @classmethod
    def from_yaml(cls, client: "MCPClient", path: str) -> "Plugin":
        """Create plugin from YAML file."""
        with open(path, "r") as f:
            data = yaml.safe_load(f)
        
        # If WASM path is relative, make it relative to YAML path
        wasm_path = data.get("wasm_path")
        if wasm_path and not os.path.isabs(wasm_path):
            dir_path = os.path.dirname(os.path.abspath(path))
            wasm_path = os.path.join(dir_path, wasm_path)
            data["wasm_path"] = wasm_path
        
        return cls.from_dict(client, data)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plugin to dictionary."""
        return {
            "id": self._id,
            "capabilities": self._capabilities.to_dict(),
            "metadata": self._metadata,
            "wasm_path": self._wasm_path,
            "hash": self._hash,
        }
    
    def to_yaml(self, path: str) -> None:
        """Save plugin to YAML file."""
        with open(path, "w") as f:
            yaml.dump(self.to_dict(), f)


class PluginRegistry:
    """
    Plugin registry for managing MCP-ZERO plugins.
    
    Acts as a cache and manager for local plugin information.
    """
    
    def __init__(self, client: "MCPClient", plugins_dir: str = None):
        self._client = client
        self._plugins_dir = plugins_dir or os.path.expanduser("~/.mcp_zero/plugins")
        self._plugins = {}
        
        # Create plugins directory if it doesn't exist
        os.makedirs(self._plugins_dir, exist_ok=True)
    
    @property
    def plugins_dir(self) -> str:
        """Get plugins directory."""
        return self._plugins_dir
    
    def get_plugin(self, plugin_id: str) -> Optional[Plugin]:
        """Get plugin by ID."""
        return self._plugins.get(plugin_id)
    
    def list_plugins(self) -> List[str]:
        """List all registered plugin IDs."""
        # Try to get from server first
        try:
            if self._client.is_connected():
                return self._client.list_plugins()
        except Exception as e:
            logger.warning(f"Failed to get plugins from server: {e}")
        
        # Fall back to local cache
        return list(self._plugins.keys())
    
    def register_plugin(self, plugin: Plugin) -> bool:
        """
        Register a plugin.
        
        Args:
            plugin: Plugin to register.
            
        Returns:
            True on success.
            
        Raises:
            PluginError: If registration fails.
        """
        try:
            plugin.register()
            self._plugins[plugin.id] = plugin
            return True
        except Exception as e:
            raise PluginError(f"Failed to register plugin: {e}")
    
    def load_from_directory(self, directory: str = None) -> List[str]:
        """
        Load plugins from directory.
        
        Args:
            directory: Optional directory path. If None, uses default.
            
        Returns:
            List of loaded plugin IDs.
        """
        directory = directory or self._plugins_dir
        
        if not os.path.exists(directory):
            logger.warning(f"Plugins directory not found: {directory}")
            return []
        
        loaded = []
        
        # Look for plugin YAML files
        for filename in os.listdir(directory):
            if not filename.endswith(".yaml") and not filename.endswith(".yml"):
                continue
            
            path = os.path.join(directory, filename)
            
            try:
                plugin = Plugin.from_yaml(self._client, path)
                self._plugins[plugin.id] = plugin
                loaded.append(plugin.id)
            except Exception as e:
                logger.error(f"Failed to load plugin from {path}: {e}")
        
        return loaded
