#!/usr/bin/env python3
"""
MCP-ZERO SDK: Agent Tests

This module tests the core Agent class functionality including the agent lifecycle:
- spawn: Creating new agents
- attach_plugin: Adding capabilities
- execute: Running operations
- snapshot: Creating runtime snapshots
- recover: Restoring agent state

All tests ensure that operations remain within MCP-ZERO's strict hardware
constraints (<27% CPU, <827MB RAM).
"""

import os
import sys
import unittest
import time
import json
from unittest.mock import patch, MagicMock
import uuid

# Add the SDK to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_zero import Agent, Plugin
from mcp_zero.exceptions import MCPError, ResourceLimitError, EthicalPolicyViolation


class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    def json(self):
        return self._json_data


class AgentTest(unittest.TestCase):
    """Test case for Agent class functionality"""
    
    def setUp(self):
        """Set up before each test"""
        # Set environment variables for testing
        os.environ["MCP_TESTING_MODE"] = "1"
        os.environ["MCP_LOW_CPU_MODE"] = "1"
        
        # Mock UUID for predictable results
        self.test_uuid = "12345678-1234-5678-1234-567812345678"
        patcher = patch('uuid.uuid4', return_value=uuid.UUID(self.test_uuid))
        self.mock_uuid = patcher.start()
        self.addCleanup(patcher.stop)
    
    def tearDown(self):
        """Clean up after each test"""
        # Clean up environment variables
        if "MCP_TESTING_MODE" in os.environ:
            del os.environ["MCP_TESTING_MODE"]
        if "MCP_LOW_CPU_MODE" in os.environ:
            del os.environ["MCP_LOW_CPU_MODE"]
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_agent_spawn(self, mock_sign, mock_post):
        """Test agent spawn functionality"""
        # Mock the API response
        mock_post.return_value = MockResponse(201, {"id": self.test_uuid, "status": "created"})
        mock_sign.return_value = "mock-signature"
        
        # Create a new agent
        agent = Agent.spawn(name="test-agent")
        
        # Check agent properties
        self.assertEqual(agent.id, self.test_uuid)
        self.assertEqual(agent.name, "test-agent")
        self.assertTrue(agent.api_url.endswith("8082"))  # Default API URL
        
        # Verify API call
        mock_post.assert_called_once()
        # Extract call arguments
        args, kwargs = mock_post.call_args
        self.assertTrue(kwargs['json']['id'] == self.test_uuid)
        self.assertTrue(kwargs['json']['signature'] == "mock-signature")
        
        # Verify signature call
        mock_sign.assert_called_once()
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_attach_plugin(self, mock_sign, mock_post):
        """Test plugin attachment"""
        # Mock API responses for both agent creation and plugin attachment
        mock_post.side_effect = [
            MockResponse(201, {"id": self.test_uuid, "status": "created"}),
            MockResponse(200, {"status": "plugin_attached"})
        ]
        mock_sign.return_value = "mock-signature"
        
        # Create a mock plugin
        mock_plugin = MagicMock()
        mock_plugin.id = "plugin-123"
        mock_plugin.name = "test-plugin"
        mock_plugin.version = "1.0.0"
        mock_plugin.hash = "abc123"
        
        # Create agent and attach plugin
        agent = Agent.spawn(name="test-agent")
        result = agent.attach_plugin(mock_plugin)
        
        # Verify result
        self.assertTrue(result)
        self.assertEqual(len(agent.plugins), 1)
        self.assertEqual(agent.plugins[0], mock_plugin)
        
        # Verify API call
        self.assertEqual(mock_post.call_count, 2)  # One for spawn, one for attach
        
        # Get the second call arguments (for attach_plugin)
        _, kwargs = mock_post.call_args
        self.assertTrue('json' in kwargs)
        self.assertEqual(kwargs['json']['agent_id'], self.test_uuid)
        self.assertEqual(kwargs['json']['plugin_id'], "plugin-123")
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    @patch('mcp_zero.agent.verify_signature')
    def test_execute(self, mock_verify, mock_sign, mock_post):
        """Test agent execute functionality"""
        # Mock API responses
        mock_post.side_effect = [
            MockResponse(201, {"id": self.test_uuid, "status": "created"}),
            MockResponse(200, {
                "result": "Operation completed",
                "status": "success",
                "signature": "result-signature"
            })
        ]
        mock_sign.return_value = "mock-signature"
        mock_verify.return_value = True
        
        # Create agent
        agent = Agent.spawn(name="test-agent")
        
        # Mock resource monitor to always allow operations
        agent.resource_monitor.check_available_resources = MagicMock(return_value=True)
        
        # Execute an operation
        result = agent.execute("test_intent", {"param1": "value1"})
        
        # Verify result
        self.assertEqual(result["status"], "success")
        self.assertEqual(result["result"], "Operation completed")
        
        # Verify API call
        self.assertEqual(mock_post.call_count, 2)  # One for spawn, one for execute
        
        # Get the second call arguments (for execute)
        _, kwargs = mock_post.call_args
        self.assertTrue('json' in kwargs)
        self.assertEqual(kwargs['json']['intent'], "test_intent")
        self.assertEqual(kwargs['json']['inputs']['param1'], "value1")
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_execute_ethical_violation(self, mock_sign, mock_post):
        """Test ethical policy violation handling"""
        # Mock API response for spawn
        mock_post.side_effect = [
            MockResponse(201, {"id": self.test_uuid, "status": "created"}),
            MockResponse(403, {"policy_violation": "Content violates ethical guidelines"})
        ]
        mock_sign.return_value = "mock-signature"
        
        # Create agent
        agent = Agent.spawn(name="test-agent")
        
        # Mock resource monitor to always allow operations
        agent.resource_monitor.check_available_resources = MagicMock(return_value=True)
        
        # Execute an operation that violates ethical policies
        with self.assertRaises(EthicalPolicyViolation):
            agent.execute("unethical_intent", {"harmful": True})
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_resource_limit(self, mock_sign, mock_post):
        """Test resource limit handling"""
        # Mock API response for spawn
        mock_post.return_value = MockResponse(201, {"id": self.test_uuid, "status": "created"})
        mock_sign.return_value = "mock-signature"
        
        # Create agent
        agent = Agent.spawn(name="test-agent")
        
        # Mock resource monitor to deny operations
        agent.resource_monitor.check_available_resources = MagicMock(return_value=False)
        agent.resource_monitor.get_cpu_percent = MagicMock(return_value=30.0)
        agent.resource_monitor.get_memory_mb = MagicMock(return_value=850.0)
        
        # Execute an operation that should fail due to resource constraints
        with self.assertRaises(ResourceLimitError):
            agent.execute("resource_heavy", {"large_computation": True})
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_snapshot(self, mock_sign, mock_post):
        """Test snapshot creation"""
        # Mock API responses
        mock_post.side_effect = [
            MockResponse(201, {"id": self.test_uuid, "status": "created"}),
            MockResponse(201, {"snapshot_id": "snap-123456", "status": "created"})
        ]
        mock_sign.return_value = "mock-signature"
        
        # Create agent
        agent = Agent.spawn(name="test-agent")
        
        # Create a snapshot
        snapshot_id = agent.snapshot({"meta": "test-metadata"})
        
        # Verify result
        self.assertEqual(snapshot_id, "snap-123456")
        
        # Verify API call
        self.assertEqual(mock_post.call_count, 2)  # One for spawn, one for snapshot
        
        # Get the second call arguments (for snapshot)
        _, kwargs = mock_post.call_args
        self.assertTrue('json' in kwargs)
        self.assertEqual(kwargs['json']['agent_id'], self.test_uuid)
        self.assertEqual(kwargs['json']['metadata']['meta'], "test-metadata")
    
    @patch('requests.Session.get')
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    def test_recover(self, mock_sign, mock_post, mock_get):
        """Test agent recovery from snapshot"""
        snapshot_id = "snap-123456"
        agent_id = self.test_uuid
        
        # Mock API responses
        mock_get.return_value = MockResponse(200, {
            "agent_id": agent_id,
            "snapshot_id": snapshot_id,
            "plugins": [
                {"id": "plugin-123", "name": "test-plugin", "version": "1.0"}
            ]
        })
        mock_post.return_value = MockResponse(200, {
            "id": agent_id,
            "name": "recovered-agent",
            "status": "active"
        })
        mock_sign.return_value = "mock-signature"
        
        # Mock PluginRegistry
        with patch('mcp_zero.agent.PluginRegistry') as mock_registry_class:
            mock_registry = MagicMock()
            mock_registry_class.return_value = mock_registry
            
            # Mock plugin retrieval
            mock_plugin = MagicMock()
            mock_plugin.id = "plugin-123"
            mock_registry.get_plugin.return_value = mock_plugin
            
            # Recover the agent
            agent = Agent.recover(snapshot_id)
            
            # Verify agent properties
            self.assertEqual(agent.id, agent_id)
            self.assertEqual(agent.name, "recovered-agent")
            self.assertEqual(len(agent.plugins), 1)
            self.assertEqual(agent.plugins[0], mock_plugin)
            
            # Verify API calls
            mock_get.assert_called_once()
            mock_post.assert_called_once()
            
            # Verify plugin registry was queried
            mock_registry.get_plugin.assert_called_with("plugin-123")
    
    @patch('requests.Session.post')
    @patch('mcp_zero.agent.sign_operation')
    @patch('json.dump')
    def test_save_local_config(self, mock_dump, mock_sign, mock_post):
        """Test local configuration saving"""
        # Mock API response
        mock_post.return_value = MockResponse(201, {"id": self.test_uuid, "status": "created"})
        mock_sign.return_value = "mock-signature"
        
        # Create agent
        with patch('os.makedirs') as mock_makedirs:
            with patch('builtins.open', unittest.mock.mock_open()) as mock_file:
                agent = Agent.spawn(name="test-agent")
                
                # Verify local config was saved
                mock_makedirs.assert_called_once()
                mock_file.assert_called_once()
                mock_dump.assert_called_once()
                
                # Check arguments passed to json.dump
                args, _ = mock_dump.call_args
                config_data = args[0]
                self.assertEqual(config_data["id"], self.test_uuid)
                self.assertEqual(config_data["name"], "test-agent")


if __name__ == "__main__":
    unittest.main()
