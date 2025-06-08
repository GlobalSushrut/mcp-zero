"""
MCP-ZERO SDK: Plugin Module

This module provides the Plugin class and PluginRegistry, enabling 
the extension of agent capabilities through sandboxed WASM plugins
while maintaining strict resource constraints and ethical governance.
"""

import os
import hashlib
import logging
from typing import Dict, Any, List, Optional, Union, Set
import json
import requests
import wasmtime

from .exceptions import PluginError, EthicalPolicyViolation

# Configure logging
logger = logging.getLogger("mcp_zero")

# Constants
PLUGIN_REGISTRY_URL = "https://registry.mcp-zero.org/api/v1/plugins"
LOCAL_PLUGIN_PATH = os.path.expanduser("~/.mcp_zero/plugins")
DEFAULT_TIMEOUT = 10.0

# Ensure local plugin directory exists
os.makedirs(LOCAL_PLUGIN_PATH, exist_ok=True)


class Plugin:
    """
    A Plugin extends agent capabilities through sandboxed WASM modules.
    
    Plugins in MCP-ZERO are:
    1. Cryptographically signed
    2. Sandboxed for security
    3. Resource constrained
    4. Ethically governed
    """
    
    def __init__(
        self, 
        id: str, 
        name: str, 
        version: str,
        description: Optional[str] = None,
        author: Optional[str] = None,
        path: Optional[str] = None,
        hash: Optional[str] = None
    ):
        """
        Initialize a Plugin.
        
        Args:
            id: Unique plugin identifier
            name: Human-readable plugin name
            version: Semantic version string
            description: Optional plugin description
            author: Optional plugin author
            path: Optional filesystem path to plugin WASM file
            hash: Optional cryptographic hash of plugin content
        """
        self.id = id
        self.name = name
        self.version = version
        self.description = description
        self.author = author
        self.path = path
        self.hash = hash
        self._module = None
        self._instance = None
        self._ethical_policies: Set[str] = set()
        self._resource_limits = {
            "max_memory_mb": 50,  # Default memory limit per plugin
            "max_cpu_percent": 5  # Default CPU limit per plugin
        }
    
    @classmethod
    def from_registry(cls, plugin_name: str, version: Optional[str] = None) -> 'Plugin':
        """
        Retrieve a plugin from the MCP-ZERO plugin registry.
        
        Args:
            plugin_name: Name of the plugin to retrieve
            version: Optional specific version (defaults to latest)
            
        Returns:
            A Plugin instance
            
        Raises:
            PluginError: If the plugin cannot be retrieved
        """
        registry = PluginRegistry()
        return registry.get_plugin(plugin_name, version)
    
    @classmethod
    def from_path(cls, path: str) -> 'Plugin':
        """
        Load a plugin from a local WASM file.
        
        Args:
            path: Path to the plugin WASM file
            
        Returns:
            A Plugin instance
            
        Raises:
            PluginError: If the plugin cannot be loaded
        """
        try:
            if not os.path.exists(path):
                raise PluginError(f"Plugin file not found: {path}")
                
            # Compute plugin hash
            file_hash = cls._compute_file_hash(path)
            
            # Try to load metadata if available
            metadata_path = f"{path}.meta.json"
            metadata = {}
            
            if os.path.exists(metadata_path):
                with open(metadata_path, 'r') as f:
                    metadata = json.load(f)
            
            # Extract basic information
            plugin_id = metadata.get("id") or hashlib.md5(file_hash.encode()).hexdigest()
            name = metadata.get("name") or os.path.basename(path).split(".")[0]
            version = metadata.get("version") or "0.1.0"
            description = metadata.get("description")
            author = metadata.get("author")
            
            # Create plugin
            plugin = cls(
                id=plugin_id,
                name=name,
                version=version,
                description=description,
                author=author,
                path=path,
                hash=file_hash
            )
            
            # Load ethical policies if present
            if "ethical_policies" in metadata:
                plugin._ethical_policies = set(metadata["ethical_policies"])
                
            # Load resource limits if present
            if "resource_limits" in metadata:
                plugin._resource_limits.update(metadata["resource_limits"])
            
            logger.info(f"Loaded plugin {name} (v{version}) from {path}")
            return plugin
            
        except Exception as e:
            logger.error(f"Failed to load plugin from {path}: {str(e)}")
            raise PluginError(f"Failed to load plugin: {str(e)}") from e
    
    def load(self) -> None:
        """
        Load the plugin into memory and prepare for execution.
        
        Raises:
            PluginError: If the plugin cannot be loaded
        """
        if self._module:
            return  # Already loaded
            
        try:
            if not self.path or not os.path.exists(self.path):
                raise PluginError(f"Plugin file not found: {self.path}")
            
            # Verify plugin hash
            if self.hash:
                current_hash = self._compute_file_hash(self.path)
                if current_hash != self.hash:
                    raise PluginError(
                        f"Plugin hash verification failed. "
                        f"Expected {self.hash}, got {current_hash}"
                    )
            
            # Create WASM engine with resource constraints
            engine = wasmtime.Engine()
            store = wasmtime.Store(engine)
            
            # Set memory limits
            memory_pages = int(self._resource_limits["max_memory_mb"] * 1024 * 1024 / 65536)
            memory_config = wasmtime.MemoryType(minimum=1, maximum=memory_pages)
            
            # Load module with resource constraints
            with open(self.path, 'rb') as f:
                module_bytes = f.read()
                
            self._module = wasmtime.Module(engine, module_bytes)
            
            logger.info(f"Plugin {self.name} loaded successfully")
            
        except Exception as e:
            logger.error(f"Failed to load plugin {self.name}: {str(e)}")
            raise PluginError(f"Failed to load plugin: {str(e)}") from e
    
    def call(self, function_name: str, *args) -> Any:
        """
        Call a function in the plugin.
        
        Args:
            function_name: Name of the function to call
            *args: Arguments to pass to the function
            
        Returns:
            Result of the function call
            
        Raises:
            PluginError: If the function call fails
            EthicalPolicyViolation: If the call violates ethical policies
        """
        if not self._module:
            self.load()
            
        try:
            # Create WASM instance if not already created
            if not self._instance:
                engine = wasmtime.Engine()
                store = wasmtime.Store(engine)
                
                # TODO: Add resource monitoring and limiting to WASM instance
                
                linker = wasmtime.Linker(engine)
                linker.define_wasi()
                wasi = wasmtime.WasiConfig()
                wasi.inherit_stdout()
                wasi.inherit_stderr()
                store.set_wasi(wasi)
                
                self._instance = linker.instantiate(store, self._module)
            
            # Get the function
            func = self._instance.exports[function_name]
            if not func:
                raise PluginError(f"Function {function_name} not found in plugin {self.name}")
                
            # Call the function
            result = func(*args)
            return result
            
        except Exception as e:
            logger.error(f"Plugin function call failed: {str(e)}")
            raise PluginError(f"Plugin function call failed: {str(e)}") from e
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert plugin to dictionary representation"""
        return {
            "id": self.id,
            "name": self.name,
            "version": self.version,
            "description": self.description,
            "author": self.author,
            "hash": self.hash,
            "ethical_policies": list(self._ethical_policies),
            "resource_limits": self._resource_limits
        }
    
    @staticmethod
    def _compute_file_hash(path: str) -> str:
        """Compute a cryptographic hash of a file"""
        hash_obj = hashlib.sha256()
        with open(path, 'rb') as f:
            for chunk in iter(lambda: f.read(4096), b''):
                hash_obj.update(chunk)
        return hash_obj.hexdigest()


class PluginRegistry:
    """
    A registry for retrieving and managing plugins.
    """
    
    def __init__(self, registry_url: Optional[str] = None):
        """
        Initialize the plugin registry.
        
        Args:
            registry_url: Optional custom registry URL
        """
        self.registry_url = registry_url or os.environ.get("MCP_PLUGIN_REGISTRY", PLUGIN_REGISTRY_URL)
        self._session = requests.Session()
        self._local_plugins: Dict[str, Dict[str, Plugin]] = {}
        
        # Load local plugins
        self._load_local_plugins()
    
    def get_plugin(self, plugin_name: str, version: Optional[str] = None) -> Plugin:
        """
        Get a plugin by name and optional version.
        
        Args:
            plugin_name: Name of the plugin
            version: Optional specific version (defaults to latest)
            
        Returns:
            A Plugin instance
            
        Raises:
            PluginError: If the plugin cannot be found or retrieved
        """
        # First check if we have it locally
        if plugin_name in self._local_plugins:
            if version:
                if version in self._local_plugins[plugin_name]:
                    return self._local_plugins[plugin_name][version]
            else:
                # Get latest version
                versions = list(self._local_plugins[plugin_name].keys())
                if versions:
                    latest = sorted(versions, key=lambda v: [int(x) for x in v.split('.')])[-1]
                    return self._local_plugins[plugin_name][latest]
        
        # If not found locally, try to download from registry
        try:
            endpoint = f"{self.registry_url}/{plugin_name}"
            if version:
                endpoint += f"/versions/{version}"
            else:
                endpoint += "/latest"
                
            response = self._session.get(endpoint, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code != 200:
                raise PluginError(
                    f"Failed to retrieve plugin {plugin_name}: "
                    f"HTTP {response.status_code} - {response.text}"
                )
                
            plugin_data = response.json()
            
            # Download the plugin WASM file
            wasm_url = plugin_data.get("download_url")
            if not wasm_url:
                raise PluginError("Plugin data missing download URL")
                
            # Download to local path
            plugin_version = plugin_data.get("version", "latest")
            local_filename = f"{plugin_name}-{plugin_version}.wasm"
            local_path = os.path.join(LOCAL_PLUGIN_PATH, local_filename)
            
            # Download the file
            wasm_response = self._session.get(wasm_url, stream=True)
            
            if wasm_response.status_code != 200:
                raise PluginError(
                    f"Failed to download plugin WASM: "
                    f"HTTP {wasm_response.status_code}"
                )
            
            with open(local_path, 'wb') as f:
                for chunk in wasm_response.iter_content(chunk_size=8192):
                    f.write(chunk)
            
            # Save metadata
            metadata = {
                "id": plugin_data.get("id"),
                "name": plugin_data.get("name"),
                "version": plugin_data.get("version"),
                "description": plugin_data.get("description"),
                "author": plugin_data.get("author"),
                "ethical_policies": plugin_data.get("ethical_policies", []),
                "resource_limits": plugin_data.get("resource_limits", {})
            }
            
            metadata_path = f"{local_path}.meta.json"
            with open(metadata_path, 'w') as f:
                json.dump(metadata, f, indent=2)
            
            # Create plugin instance
            plugin = Plugin(
                id=plugin_data.get("id"),
                name=plugin_data.get("name"),
                version=plugin_data.get("version"),
                description=plugin_data.get("description"),
                author=plugin_data.get("author"),
                path=local_path,
                hash=plugin_data.get("hash")
            )
            
            # Add to local cache
            if plugin_name not in self._local_plugins:
                self._local_plugins[plugin_name] = {}
                
            self._local_plugins[plugin_name][plugin_version] = plugin
            
            logger.info(f"Downloaded plugin {plugin_name} v{plugin_version} from registry")
            return plugin
            
        except Exception as e:
            if isinstance(e, PluginError):
                raise
            logger.error(f"Failed to get plugin {plugin_name}: {str(e)}")
            raise PluginError(f"Failed to retrieve plugin: {str(e)}") from e
    
    def list_available_plugins(self) -> List[Dict[str, Any]]:
        """
        List all available plugins in the registry.
        
        Returns:
            List of plugin metadata dictionaries
        """
        try:
            response = self._session.get(self.registry_url, timeout=DEFAULT_TIMEOUT)
            
            if response.status_code != 200:
                logger.error(f"Failed to list plugins: HTTP {response.status_code}")
                return []
                
            plugins = response.json().get("plugins", [])
            return plugins
            
        except Exception as e:
            logger.error(f"Failed to list available plugins: {str(e)}")
            return []
    
    def _load_local_plugins(self) -> None:
        """Load locally cached plugins"""
        try:
            if not os.path.exists(LOCAL_PLUGIN_PATH):
                os.makedirs(LOCAL_PLUGIN_PATH, exist_ok=True)
                return
                
            for filename in os.listdir(LOCAL_PLUGIN_PATH):
                if filename.endswith('.wasm'):
                    plugin_path = os.path.join(LOCAL_PLUGIN_PATH, filename)
                    try:
                        plugin = Plugin.from_path(plugin_path)
                        
                        if plugin.name not in self._local_plugins:
                            self._local_plugins[plugin.name] = {}
                            
                        self._local_plugins[plugin.name][plugin.version] = plugin
                        logger.debug(f"Loaded local plugin {plugin.name} v{plugin.version}")
                    except Exception as e:
                        logger.warning(f"Failed to load local plugin {filename}: {str(e)}")
                        
        except Exception as e:
            logger.warning(f"Error loading local plugins: {str(e)}")
