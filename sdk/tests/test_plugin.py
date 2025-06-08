#!/usr/bin/env python3
"""
MCP-ZERO SDK: Plugin System Tests

This module tests the Plugin system which is critical for MCP-ZERO's
plugin-based extensibility architecture. Tests include plugin loading,
validation, sandboxing, and resource limiting.
"""

import os
import sys
import unittest
import tempfile
import hashlib
import json
from unittest.mock import patch, MagicMock

# Add the SDK to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_zero import Plugin, PluginRegistry
from mcp_zero.exceptions import PluginError, EthicalPolicyViolation


class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status_code, json_data=None, text="", content=None):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        self.content = content or b""
        
    def json(self):
        return self._json_data
        
    def iter_content(self, chunk_size=None):
        """Iterate content for download simulation"""
        if not self.content:
            return []
        
        for i in range(0, len(self.content), chunk_size or 1024):
            yield self.content[i:i + (chunk_size or 1024)]


class PluginTest(unittest.TestCase):
    """Test case for Plugin class functionality"""
    
    def setUp(self):
        """Set up before each test"""
        # Create temporary directory for test plugins
        self.temp_dir = tempfile.TemporaryDirectory()
        
        # Create test plugin files
        self.plugin_path = os.path.join(self.temp_dir.name, "test_plugin.wasm")
        self.plugin_content = b"Test WASM content with some binary data"
        
        with open(self.plugin_path, "wb") as f:
            f.write(self.plugin_content)
            
        # Create metadata file
        self.metadata = {
            "id": "test-plugin-123",
            "name": "test-plugin",
            "version": "1.0.0",
            "description": "A test plugin",
            "author": "MCP-ZERO Test",
            "ethical_policies": ["no_harmful_content", "data_minimization"],
            "resource_limits": {
                "max_memory_mb": 30,
                "max_cpu_percent": 5
            }
        }
        
        self.metadata_path = f"{self.plugin_path}.meta.json"
        with open(self.metadata_path, "w") as f:
            json.dump(self.metadata, f)
            
        # Calculate hash
        self.plugin_hash = hashlib.sha256(self.plugin_content).hexdigest()
    
    def tearDown(self):
        """Clean up after each test"""
        self.temp_dir.cleanup()
    
    def test_plugin_from_path(self):
        """Test creating a plugin from a local file path"""
        # Load plugin from path
        plugin = Plugin.from_path(self.plugin_path)
        
        # Check plugin properties
        self.assertEqual(plugin.id, self.metadata["id"])
        self.assertEqual(plugin.name, self.metadata["name"])
        self.assertEqual(plugin.version, self.metadata["version"])
        self.assertEqual(plugin.description, self.metadata["description"])
        self.assertEqual(plugin.author, self.metadata["author"])
        self.assertEqual(plugin.path, self.plugin_path)
        
        # Check hash calculation
        self.assertEqual(plugin.hash, self.plugin_hash)
        
        # Check ethical policies and resource limits
        self.assertEqual(len(plugin._ethical_policies), 2)
        self.assertIn("no_harmful_content", plugin._ethical_policies)
        self.assertEqual(plugin._resource_limits["max_memory_mb"], 30)
        self.assertEqual(plugin._resource_limits["max_cpu_percent"], 5)
    
    def test_plugin_from_path_no_metadata(self):
        """Test creating a plugin without a metadata file"""
        # Create plugin file without metadata
        plugin_path = os.path.join(self.temp_dir.name, "no_meta_plugin.wasm")
        with open(plugin_path, "wb") as f:
            f.write(b"Plugin with no metadata")
            
        # Load plugin from path
        plugin = Plugin.from_path(plugin_path)
        
        # Check default properties
        self.assertEqual(plugin.name, "no_meta_plugin")
        self.assertEqual(plugin.version, "0.1.0")
        self.assertEqual(plugin.path, plugin_path)
        
        # Check default resource limits
        self.assertEqual(plugin._resource_limits["max_memory_mb"], 50)
        self.assertEqual(plugin._resource_limits["max_cpu_percent"], 5)
    
    def test_plugin_invalid_path(self):
        """Test error handling for invalid plugin path"""
        invalid_path = "/nonexistent/path/to/plugin.wasm"
        
        # Should raise PluginError
        with self.assertRaises(PluginError):
            Plugin.from_path(invalid_path)
    
    @patch('wasmtime.Module')
    @patch('wasmtime.Engine')
    def test_plugin_load(self, mock_engine, mock_module):
        """Test loading a plugin into memory"""
        # Create mocks
        mock_engine.return_value = MagicMock()
        mock_module.return_value = MagicMock()
        
        # Create plugin
        plugin = Plugin.from_path(self.plugin_path)
        
        # Load the plugin
        plugin.load()
        
        # Verify module was created
        self.assertIsNotNone(plugin._module)
        mock_module.assert_called_once()
    
    @patch('wasmtime.Module')
    @patch('wasmtime.Engine')
    def test_plugin_hash_verification(self, mock_engine, mock_module):
        """Test plugin hash verification during load"""
        # Create plugin
        plugin = Plugin.from_path(self.plugin_path)
        
        # Tamper with the hash
        plugin.hash = "invalid-hash-value"
        
        # Should raise PluginError during load
        with self.assertRaises(PluginError):
            plugin.load()
    
    @patch('requests.Session.get')
    def test_registry_get_plugin(self, mock_get):
        """Test retrieving plugins from the registry"""
        # Mock API responses
        plugin_data = {
            "id": "registry-plugin-123",
            "name": "registry-plugin",
            "version": "2.0.0",
            "description": "A plugin from the registry",
            "author": "MCP-ZERO Registry",
            "download_url": "https://registry.example.com/download/registry-plugin",
            "hash": self.plugin_hash,
            "ethical_policies": ["privacy_preserving"],
            "resource_limits": {"max_memory_mb": 40}
        }
        
        mock_get.side_effect = [
            MockResponse(200, plugin_data),
            MockResponse(200, content=self.plugin_content)
        ]
        
        # Create temporary directory for registry
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                # Mock file operations for download
                mock_file.return_value.__enter__.return_value.write = MagicMock()
                
                # Create registry and get plugin
                registry = PluginRegistry()
                plugin = registry.get_plugin("registry-plugin")
                
                # Check plugin properties
                self.assertEqual(plugin.id, plugin_data["id"])
                self.assertEqual(plugin.name, plugin_data["name"])
                self.assertEqual(plugin.version, plugin_data["version"])
                self.assertEqual(plugin.hash, self.plugin_hash)
                
                # Verify API calls
                self.assertEqual(mock_get.call_count, 2)  # Plugin metadata and download
    
    @patch('requests.Session.get')
    def test_registry_plugin_not_found(self, mock_get):
        """Test handling when a plugin is not found in the registry"""
        # Mock API response for 404
        mock_get.return_value = MockResponse(404, text="Plugin not found")
        
        # Create registry
        registry = PluginRegistry()
        
        # Should raise PluginError
        with self.assertRaises(PluginError):
            registry.get_plugin("nonexistent-plugin")
    
    @patch('requests.Session.get')
    def test_list_available_plugins(self, mock_get):
        """Test listing available plugins in the registry"""
        # Mock API response
        plugins_list = {
            "plugins": [
                {"id": "plugin1", "name": "Plugin One", "version": "1.0.0"},
                {"id": "plugin2", "name": "Plugin Two", "version": "2.1.0"}
            ]
        }
        mock_get.return_value = MockResponse(200, plugins_list)
        
        # Create registry and list plugins
        registry = PluginRegistry()
        plugins = registry.list_available_plugins()
        
        # Verify results
        self.assertEqual(len(plugins), 2)
        self.assertEqual(plugins[0]["name"], "Plugin One")
        self.assertEqual(plugins[1]["id"], "plugin2")
    
    def test_plugin_to_dict(self):
        """Test converting a plugin to dictionary representation"""
        # Create plugin
        plugin = Plugin.from_path(self.plugin_path)
        
        # Convert to dict
        plugin_dict = plugin.to_dict()
        
        # Check dict properties
        self.assertEqual(plugin_dict["id"], self.metadata["id"])
        self.assertEqual(plugin_dict["name"], self.metadata["name"])
        self.assertEqual(plugin_dict["version"], self.metadata["version"])
        self.assertEqual(plugin_dict["hash"], self.plugin_hash)
        self.assertIn("ethical_policies", plugin_dict)
        self.assertIn("resource_limits", plugin_dict)
    
    @patch('wasmtime.Store')
    @patch('wasmtime.Engine')
    @patch('wasmtime.Module')
    @patch('wasmtime.Linker')
    @patch('wasmtime.WasiConfig')
    def test_plugin_call(self, mock_wasi, mock_linker, mock_module, mock_engine, mock_store):
        """Test calling a function in a plugin"""
        # Create mocks
        mock_engine.return_value = MagicMock()
        mock_store.return_value = MagicMock()
        mock_module.return_value = MagicMock()
        
        # Create mock linker with exports
        mock_instance = MagicMock()
        mock_function = MagicMock()
        mock_function.return_value = "function result"
        
        mock_instance.exports = {"test_function": mock_function}
        mock_linker_inst = MagicMock()
        mock_linker_inst.instantiate.return_value = mock_instance
        mock_linker.return_value = mock_linker_inst
        
        # Create plugin
        plugin = Plugin.from_path(self.plugin_path)
        
        # Call function
        result = plugin.call("test_function", "arg1", 42)
        
        # Verify function was called
        self.assertEqual(result, "function result")
        mock_function.assert_called_with("arg1", 42)
    
    @patch('wasmtime.Store')
    @patch('wasmtime.Engine')
    @patch('wasmtime.Module')
    @patch('wasmtime.Linker')
    @patch('wasmtime.WasiConfig')
    def test_plugin_call_function_not_found(self, mock_wasi, mock_linker, mock_module, mock_engine, mock_store):
        """Test error handling when calling a non-existent function"""
        # Create mocks
        mock_engine.return_value = MagicMock()
        mock_store.return_value = MagicMock()
        mock_module.return_value = MagicMock()
        
        # Create mock linker with empty exports
        mock_instance = MagicMock()
        mock_instance.exports = {}
        mock_linker_inst = MagicMock()
        mock_linker_inst.instantiate.return_value = mock_instance
        mock_linker.return_value = mock_linker_inst
        
        # Create plugin
        plugin = Plugin.from_path(self.plugin_path)
        
        # Should raise PluginError when function not found
        with self.assertRaises(PluginError):
            plugin.call("nonexistent_function")


if __name__ == "__main__":
    unittest.main()
