#!/usr/bin/env python3
"""
MCP-ZERO Plugin Manager
Handles plugin loading, validation, and execution for MCP-ZERO agents
"""
import importlib.util
import logging
import os
import sys
from typing import Dict, List, Any, Optional, Callable

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('plugin_manager')

class PluginManager:
    """
    Manager for agent plugins
    Handles plugin loading, validation, and execution
    """
    
    def __init__(self, plugins_path: str = "deploy/plugins"):
        """
        Initialize the plugin manager
        
        Args:
            plugins_path: Path to plugin storage directory
        """
        self.plugins_path = plugins_path
        self.loaded_plugins = {}
        
        # Ensure plugins directory exists
        os.makedirs(plugins_path, exist_ok=True)
        
        logger.info(f"Plugin Manager initialized with path: {plugins_path}")
        
    def load_plugin(self, plugin_path: str) -> Dict[str, Any]:
        """
        Load a plugin from file
        
        Args:
            plugin_path: Path to plugin file
            
        Returns:
            Plugin descriptor with functions
        """
        try:
            if not os.path.exists(plugin_path):
                logger.error(f"Plugin file not found: {plugin_path}")
                return None
                
            plugin_name = os.path.basename(plugin_path).split('.')[0]
            plugin_type = self._get_plugin_type(plugin_path)
            
            if plugin_type == "python":
                plugin = self._load_python_plugin(plugin_path, plugin_name)
            elif plugin_type == "javascript":
                plugin = self._load_js_plugin(plugin_path, plugin_name)
            else:
                logger.error(f"Unsupported plugin type: {plugin_type}")
                return None
                
            if plugin:
                self.loaded_plugins[plugin_name] = plugin
                logger.info(f"Loaded plugin: {plugin_name} ({plugin_type})")
                return plugin
            else:
                logger.error(f"Failed to load plugin: {plugin_name}")
                return None
        except Exception as e:
            logger.error(f"Error loading plugin {plugin_path}: {str(e)}")
            return None
            
    def _get_plugin_type(self, plugin_path: str) -> str:
        """Determine plugin type from file extension"""
        ext = os.path.splitext(plugin_path)[1].lower()
        if ext == '.py':
            return "python"
        elif ext in ['.js', '.mjs']:
            return "javascript"
        else:
            return "unknown"
            
    def _load_python_plugin(self, plugin_path: str, plugin_name: str) -> Dict[str, Any]:
        """Load a Python plugin"""
        try:
            # Create module spec
            spec = importlib.util.spec_from_file_location(plugin_name, plugin_path)
            if spec is None:
                logger.error(f"Failed to create module spec for {plugin_path}")
                return None
                
            # Load module
            module = importlib.util.module_from_spec(spec)
            spec.loader.exec_module(module)
            
            # Extract plugin metadata
            metadata = getattr(module, "PLUGIN_METADATA", {})
            if not metadata:
                # Create default metadata
                metadata = {
                    "name": plugin_name,
                    "version": "1.0.0",
                    "description": f"Plugin {plugin_name}"
                }
                
            # Create plugin descriptor
            plugin = {
                "name": plugin_name,
                "type": "python",
                "path": plugin_path,
                "metadata": metadata,
                "functions": {}
            }
            
            # Find callable functions in the module
            for attr_name in dir(module):
                attr = getattr(module, attr_name)
                if callable(attr) and not attr_name.startswith('_'):
                    plugin["functions"][attr_name] = attr
                    
            return plugin
        except Exception as e:
            logger.error(f"Error loading Python plugin: {str(e)}")
            return None
            
    def _load_js_plugin(self, plugin_path: str, plugin_name: str) -> Dict[str, Any]:
        """Load a JavaScript plugin"""
        try:
            # In a real implementation, would use a JavaScript runtime
            # For now, just create a basic plugin descriptor
            with open(plugin_path, 'r') as f:
                content = f.read()
                
            # Extract metadata from comments (simplified)
            metadata = {
                "name": plugin_name,
                "version": "1.0.0",
                "description": f"JavaScript plugin {plugin_name}"
            }
            
            # Look for metadata in first comment block
            if content.startswith('/*'):
                comment_end = content.find('*/')
                if comment_end > 0:
                    comment = content[2:comment_end]
                    for line in comment.split('\n'):
                        if ':' in line:
                            key, value = line.split(':', 1)
                            metadata[key.strip().lower()] = value.strip()
                            
            plugin = {
                "name": plugin_name,
                "type": "javascript",
                "path": plugin_path,
                "metadata": metadata,
                "content": content,
                # In a real implementation, would expose JS functions
                "functions": {}
            }
            
            return plugin
        except Exception as e:
            logger.error(f"Error loading JavaScript plugin: {str(e)}")
            return None
            
    def execute_plugin_function(self, 
                               plugin_name: str, 
                               function_name: str, 
                               args: List[Any] = None, 
                               kwargs: Dict[str, Any] = None) -> Any:
        """
        Execute a function from a loaded plugin
        
        Args:
            plugin_name: Name of the plugin
            function_name: Name of the function to execute
            args: Positional arguments (optional)
            kwargs: Keyword arguments (optional)
            
        Returns:
            Function return value or None on error
        """
        if plugin_name not in self.loaded_plugins:
            logger.error(f"Plugin not loaded: {plugin_name}")
            return None
            
        plugin = self.loaded_plugins[plugin_name]
        if plugin["type"] != "python":
            logger.error(f"Cannot execute non-Python plugin function: {plugin_name}.{function_name}")
            return None
            
        if function_name not in plugin["functions"]:
            logger.error(f"Function not found in plugin: {plugin_name}.{function_name}")
            return None
            
        try:
            func = plugin["functions"][function_name]
            result = func(*(args or []), **(kwargs or {}))
            return result
        except Exception as e:
            logger.error(f"Error executing plugin function {plugin_name}.{function_name}: {str(e)}")
            return None
            
    def list_plugins(self) -> List[Dict[str, Any]]:
        """
        List all loaded plugins
        
        Returns:
            List of plugin descriptors
        """
        return [
            {
                "name": name,
                "type": plugin["type"],
                "path": plugin["path"],
                "metadata": plugin["metadata"],
                "functions": list(plugin["functions"].keys()) if plugin["type"] == "python" else []
            }
            for name, plugin in self.loaded_plugins.items()
        ]
        
    def unload_plugin(self, plugin_name: str) -> bool:
        """
        Unload a plugin
        
        Args:
            plugin_name: Name of plugin to unload
            
        Returns:
            True if successful, False otherwise
        """
        if plugin_name not in self.loaded_plugins:
            logger.warning(f"Plugin not loaded: {plugin_name}")
            return False
            
        try:
            del self.loaded_plugins[plugin_name]
            logger.info(f"Unloaded plugin: {plugin_name}")
            return True
        except Exception as e:
            logger.error(f"Error unloading plugin: {str(e)}")
            return False
