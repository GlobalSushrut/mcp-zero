#!/usr/bin/env python3
"""
MCP-ZERO SDK: RPC Client Tests

This module tests the RPC client module that handles communication
with the MCP-ZERO Go RPC Layer. Tests include request handling,
throttling, resource monitoring integration, and error handling.
"""

import os
import sys
import unittest
import json
import time
import threading
from unittest.mock import patch, MagicMock

# Add the SDK to the Python path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_zero.rpc_client import RPCClient
from mcp_zero.exceptions import APIError, ResourceLimitError


class MockResponse:
    """Mock HTTP response for testing"""
    
    def __init__(self, status_code, json_data=None, text=""):
        self.status_code = status_code
        self._json_data = json_data or {}
        self.text = text
        
    def json(self):
        return self._json_data


class RPCClientTest(unittest.TestCase):
    """Test case for RPC client functionality"""
    
    def setUp(self):
        """Set up before each test"""
        # Set environment variables for testing
        os.environ["MCP_TESTING_MODE"] = "1"
        os.environ["MCP_ZERO_API_URL"] = "http://test.local:8082"
        
        # Create a mock resource monitor
        self.mock_resource_monitor = MagicMock()
        self.mock_resource_monitor.check_available_resources.return_value = True
        self.mock_resource_monitor.track_operation.return_value.__enter__ = MagicMock()
        self.mock_resource_monitor.track_operation.return_value.__exit__ = MagicMock()
        
        # Create client with mock resource monitor
        self.client = RPCClient(resource_monitor=self.mock_resource_monitor)
    
    def tearDown(self):
        """Clean up after each test"""
        # Clean up environment variables
        if "MCP_TESTING_MODE" in os.environ:
            del os.environ["MCP_TESTING_MODE"]
        if "MCP_ZERO_API_URL" in os.environ:
            del os.environ["MCP_ZERO_API_URL"]
    
    def test_init_with_defaults(self):
        """Test client initialization with default values"""
        client = RPCClient()
        self.assertEqual(client.api_url, "http://test.local:8082")  # From env var
        self.assertEqual(client.timeout, 10.0)
    
    def test_init_with_custom_values(self):
        """Test client initialization with custom values"""
        client = RPCClient(api_url="http://custom:9000", timeout=5.0)
        self.assertEqual(client.api_url, "http://custom:9000")
        self.assertEqual(client.timeout, 5.0)
    
    def test_build_url(self):
        """Test URL building"""
        # Test with leading slash
        url = self.client._build_url("/test/endpoint")
        self.assertEqual(url, "http://test.local:8082/test/endpoint")
        
        # Test without leading slash
        url = self.client._build_url("test/endpoint")
        self.assertEqual(url, "http://test.local:8082/test/endpoint")
    
    @patch('requests.Session.request')
    def test_get_request(self, mock_request):
        """Test GET request handling"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"result": "success"})
        
        # Make request
        result = self.client.get("/test/get", params={"param": "value"})
        
        # Check result
        self.assertEqual(result, {"result": "success"})
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "GET")
        self.assertEqual(kwargs["url"], "http://test.local:8082/test/get")
        self.assertEqual(kwargs["params"], {"param": "value"})
        self.assertIsNone(kwargs["data"])
    
    @patch('requests.Session.request')
    def test_post_request(self, mock_request):
        """Test POST request handling"""
        # Mock response
        mock_request.return_value = MockResponse(201, {"id": "new-item"})
        
        # Make request
        data = {"name": "test", "value": 42}
        result = self.client.post("/test/post", data)
        
        # Check result
        self.assertEqual(result, {"id": "new-item"})
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "POST")
        self.assertEqual(kwargs["url"], "http://test.local:8082/test/post")
        self.assertEqual(kwargs["data"], json.dumps(data))
    
    @patch('requests.Session.request')
    def test_put_request(self, mock_request):
        """Test PUT request handling"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"status": "updated"})
        
        # Make request
        data = {"id": "item-1", "name": "updated"}
        result = self.client.put("/test/put/item-1", data)
        
        # Check result
        self.assertEqual(result, {"status": "updated"})
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "PUT")
        self.assertEqual(kwargs["url"], "http://test.local:8082/test/put/item-1")
        self.assertEqual(kwargs["data"], json.dumps(data))
    
    @patch('requests.Session.request')
    def test_delete_request(self, mock_request):
        """Test DELETE request handling"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"status": "deleted"})
        
        # Make request
        result = self.client.delete("/test/delete/item-1")
        
        # Check result
        self.assertEqual(result, {"status": "deleted"})
        
        # Verify request was made correctly
        mock_request.assert_called_once()
        args, kwargs = mock_request.call_args
        self.assertEqual(kwargs["method"], "DELETE")
        self.assertEqual(kwargs["url"], "http://test.local:8082/test/delete/item-1")
    
    @patch('requests.Session.request')
    def test_error_handling(self, mock_request):
        """Test error response handling"""
        # Mock error response
        mock_request.return_value = MockResponse(
            404, 
            {"error": "Resource not found"},
            text='{"error": "Resource not found"}'
        )
        
        # Should raise APIError
        with self.assertRaises(APIError) as context:
            self.client.get("/test/nonexistent")
        
        # Check error properties
        self.assertEqual(context.exception.status_code, 404)
        self.assertIn("Resource not found", str(context.exception))
    
    @patch('requests.Session.request')
    def test_json_decode_error(self, mock_request):
        """Test handling of invalid JSON responses"""
        # Mock invalid JSON response
        mock_request.return_value = MockResponse(
            200,
            None,
            text='Invalid JSON'
        )
        mock_request.return_value.json = MagicMock(side_effect=json.JSONDecodeError("Invalid JSON", "", 0))
        
        # Should raise APIError
        with self.assertRaises(APIError) as context:
            self.client.get("/test/invalid-json")
        
        # Check error message
        self.assertIn("Failed to decode JSON", str(context.exception))
    
    @patch('requests.Session.request')
    def test_request_exception(self, mock_request):
        """Test handling of request exceptions"""
        # Mock request exception
        mock_request.side_effect = requests.RequestException("Connection failed")
        
        # Should raise APIError
        with self.assertRaises(APIError) as context:
            self.client.get("/test/connection-error")
        
        # Check error message
        self.assertIn("Connection failed", str(context.exception))
    
    def test_resource_limit_check(self):
        """Test resource limit check before making requests"""
        # Mock resource monitor to indicate insufficient resources
        self.mock_resource_monitor.check_available_resources.return_value = False
        self.mock_resource_monitor.get_cpu_percent.return_value = 30.0
        self.mock_resource_monitor.get_memory_mb.return_value = 850.0
        
        # Should raise ResourceLimitError
        with self.assertRaises(ResourceLimitError):
            self.client.get("/test/resource-heavy")
    
    @patch('time.sleep')
    @patch('requests.Session.request')
    def test_throttling(self, mock_request, mock_sleep):
        """Test request throttling based on CPU usage"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"result": "success"})
        
        # Configure resource monitor for high CPU
        self.mock_resource_monitor._cpu_samples = [22.5]  # Above throttling threshold
        self.mock_resource_monitor._lock = threading.Lock()
        
        # Make request
        result = self.client.get("/test/throttled")
        
        # Verify throttling was applied
        mock_sleep.assert_called_once()
        sleep_duration = mock_sleep.call_args[0][0]
        self.assertGreater(sleep_duration, 0)
        
        # Check that the request still succeeded
        self.assertEqual(result, {"result": "success"})
    
    @patch('requests.Session.request')
    def test_request_tracking(self, mock_request):
        """Test that operations are tracked by resource monitor"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"result": "success"})
        
        # Make request
        self.client.get("/test/tracked")
        
        # Verify operation was tracked
        self.mock_resource_monitor.track_operation.assert_called_once()
        args, _ = self.mock_resource_monitor.track_operation.call_args
        self.assertEqual(args[0], "rpc_get")
    
    @patch('requests.Session.request')
    def test_custom_headers(self, mock_request):
        """Test custom headers in requests"""
        # Mock response
        mock_request.return_value = MockResponse(200, {"result": "success"})
        
        # Make request with custom headers
        custom_headers = {"Authorization": "Bearer token123", "X-Custom": "Value"}
        self.client.get("/test/headers", headers=custom_headers)
        
        # Verify headers were passed
        args, kwargs = mock_request.call_args
        for key, value in custom_headers.items():
            self.assertEqual(kwargs["headers"][key], value)
        
        # Default content-type should still be present
        self.assertEqual(kwargs["headers"]["Content-Type"], "application/json")


if __name__ == "__main__":
    unittest.main()
