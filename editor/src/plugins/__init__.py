"""
Plugin System for MCP Zero Editor

A lightweight plugin system that follows the offline-first resilience pattern.
Plugins can enhance editor capabilities without external dependencies.
"""

import os
import sys
import importlib
import logging
import threading
from typing import Dict, List, Optional, Any, Callable

# Add parent directory to path to import MCP Zero components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../../..')))

# Import MCP Zero components
from src.api import telemetry_collector
from src.api.health_checker import HealthChecker

logger = logging.getLogger("mcp_zero.editor.plugins")

class PluginManager:
    """
    Manager for editor plugins.
    
    Follows offline-first resilience pattern:
    - Loads plugins from local directory first
    - Falls back to basic functionality if plugins fail
    - Never retries failed plugins
    - Records plugin health status
    """
    
    def __init__(self, plugin_dirs: Optional[List[str]] = None, health_checker: Optional[HealthChecker] = None):
        """
        Initialize plugin manager.
        
        Args:
            plugin_dirs: List of directories to search for plugins
            health_checker: Optional health checker for monitoring plugin health
        """
        self.plugins: Dict[str, Any] = {}
        self.failed_plugins: Dict[str, str] = {}
        self.plugin_dirs = plugin_dirs or [
            os.path.join(os.path.dirname(__file__), "builtin"),
            os.path.join(os.path.expanduser("~"), ".mcp_zero", "editor", "plugins")
        ]
        self.health_checker = health_checker
        self._lock = threading.RLock()
        
        # Create user plugin directory if it doesn't exist
        user_plugin_dir = os.path.join(os.path.expanduser("~"), ".mcp_zero", "editor", "plugins")
        os.makedirs(user_plugin_dir, exist_ok=True)
        
        logger.info(f"Plugin manager initialized with dirs: {self.plugin_dirs}")
        
    def discover_plugins(self) -> Dict[str, Any]:
        """
        Discover available plugins in plugin directories.
        
        Returns:
            Dictionary of plugin names and module objects
        """
        discovered = {}
        
        # Following offline-first pattern - no repeated attempts to load plugins
        with self._lock:
            for plugin_dir in self.plugin_dirs:
                if os.path.exists(plugin_dir) and os.path.isdir(plugin_dir):
                    try:
                        # Look for Python files that might be plugins
                        for filename in os.listdir(plugin_dir):
                            if filename.endswith(".py") and not filename.startswith("_"):
                                plugin_name = filename[:-3]  # Remove .py extension
                                plugin_path = os.path.join(plugin_dir, filename)
                                
                                # Skip already discovered plugins
                                if plugin_name in discovered or plugin_name in self.failed_plugins:
                                    continue
                                
                                # Record telemetry
                                telemetry_collector.record("editor.plugin.discover", plugin=plugin_name)
                                
                                try:
                                    # Import the plugin module
                                    spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
                                    if spec and spec.loader:
                                        module = importlib.util.module_from_spec(spec)
                                        spec.loader.exec_module(module)
                                        
                                        # Check if it's a valid plugin
                                        if hasattr(module, "plugin_info") and callable(getattr(module, "initialize_plugin", None)):
                                            discovered[plugin_name] = module
                                            logger.info(f"Discovered plugin: {plugin_name}")
                                        else:
                                            logger.warning(f"Invalid plugin format: {plugin_name}")
                                except Exception as e:
                                    self.failed_plugins[plugin_name] = str(e)
                                    logger.error(f"Error loading plugin {plugin_name}: {str(e)}")
                    except Exception as e:
                        logger.error(f"Error accessing plugin directory {plugin_dir}: {str(e)}")
                        
        return discovered
    
    def load_plugins(self, editor_instance: Any = None) -> None:
        """
        Load and initialize discovered plugins.
        
        Args:
            editor_instance: Editor instance to pass to plugins
        """
        # Discover plugins
        discovered = self.discover_plugins()
        
        # Load each plugin with offline-first approach
        with self._lock:
            for plugin_name, module in discovered.items():
                # Skip if already loaded
                if plugin_name in self.plugins:
                    continue
                
                try:
                    # Initialize the plugin
                    plugin_instance = module.initialize_plugin(editor_instance)
                    self.plugins[plugin_name] = {
                        "module": module,
                        "instance": plugin_instance,
                        "info": getattr(module, "plugin_info", {})
                    }
                    
                    # Register health check if available
                    if self.health_checker and hasattr(plugin_instance, "check_health"):
                        self.health_checker.register_check(
                            f"plugin.{plugin_name}", 
                            plugin_instance.check_health,
                            timeout=1.0
                        )
                    
                    logger.info(f"Loaded plugin: {plugin_name}")
                    
                    # Record telemetry
                    telemetry_collector.record("editor.plugin.load", plugin=plugin_name)
                    
                except Exception as e:
                    self.failed_plugins[plugin_name] = str(e)
                    logger.error(f"Failed to load plugin {plugin_name}: {str(e)}")
                    
                    # Record telemetry for failure
                    telemetry_collector.record(
                        "editor.plugin.load_failed", 
                        plugin=plugin_name,
                        error=str(e)
                    )
    
    def get_plugin(self, name: str) -> Optional[Any]:
        """
        Get a loaded plugin by name.
        
        Args:
            name: Name of the plugin
            
        Returns:
            Plugin instance or None if not found
        """
        with self._lock:
            if name in self.plugins:
                return self.plugins[name]["instance"]
        return None
    
    def call_hook(self, hook_name: str, *args, **kwargs) -> List[Any]:
        """
        Call a hook on all plugins that support it.
        
        Args:
            hook_name: Name of the hook to call
            *args: Arguments to pass to the hook
            **kwargs: Keyword arguments to pass to the hook
            
        Returns:
            List of results from plugins
        """
        results = []
        
        with self._lock:
            for plugin_name, plugin_data in self.plugins.items():
                plugin = plugin_data["instance"]
                
                # Check if plugin has the hook
                if hasattr(plugin, hook_name) and callable(getattr(plugin, hook_name)):
                    try:
                        # Call the hook
                        result = getattr(plugin, hook_name)(*args, **kwargs)
                        results.append((plugin_name, result))
                    except Exception as e:
                        logger.error(f"Error calling {hook_name} on plugin {plugin_name}: {str(e)}")
                        
        return results
    
    def shutdown(self) -> None:
        """Shut down all plugins."""
        with self._lock:
            for plugin_name, plugin_data in self.plugins.items():
                plugin = plugin_data["instance"]
                
                # Call shutdown if available
                if hasattr(plugin, "shutdown") and callable(plugin.shutdown):
                    try:
                        plugin.shutdown()
                        logger.info(f"Shutdown plugin: {plugin_name}")
                    except Exception as e:
                        logger.error(f"Error shutting down plugin {plugin_name}: {str(e)}")


# Create a basic plugin template
class BasePlugin:
    """Base class for editor plugins."""
    
    def __init__(self, editor=None):
        """
        Initialize plugin.
        
        Args:
            editor: Editor instance
        """
        self.editor = editor
        
    def initialize(self) -> bool:
        """
        Initialize the plugin.
        
        Returns:
            True if successful, False otherwise
        """
        return True
    
    def shutdown(self) -> None:
        """Clean up resources when editor is closing."""
        pass
    
    def check_health(self) -> bool:
        """
        Check if plugin is healthy.
        
        Returns:
            True if healthy, False otherwise
        """
        return True
