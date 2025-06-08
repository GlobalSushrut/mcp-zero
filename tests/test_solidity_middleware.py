#!/usr/bin/env python3
"""
Test suite for Solidity Agreement Middleware integration
"""
import os
import sys
import json
import time
import unittest
import subprocess
import requests

# Add project root to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from unittest.mock import patch, MagicMock
from mcp_zero.testing import MockRPCServer, TestAgent

class TestSolidityMiddleware(unittest.TestCase):
    """Test the Solidity Agreement Middleware integration"""
    
    @classmethod
    def setUpClass(cls):
        """Start mock RPC server for testing"""
        cls.server = MockRPCServer()
        cls.server.start()
        time.sleep(1)  # Give server time to start
        
    @classmethod
    def tearDownClass(cls):
        """Stop mock server"""
        cls.server.stop()
        
    def setUp(self):
        """Set up for each test"""
        self.consumer = TestAgent("consumer")
        self.provider = TestAgent("provider")
        
    def test_create_agreement(self):
        """Test creating a Solidity agreement through middleware"""
        terms = {
            "max_calls": 100,
            "max_cpu": 0.5,
            "valid_days": 30
        }
        
        # Ethical policies must include compulsory ones
        ethical_policies = ["content_safety", "fair_use", "data_privacy"]
        
        # Create agreement 
        response = requests.post(
            f"{self.server.base_url}/agreements",
            json={
                "consumer_id": self.consumer.id,
                "provider_id": self.provider.id,
                "terms": terms,
                "ethical_policies": ethical_policies
            }
        )
        
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertIn("id", data)
        agreement_id = data["id"]
        
        # Verify the agreement exists
        response = requests.get(
            f"{self.server.base_url}/agreements/{agreement_id}"
        )
        self.assertEqual(response.status_code, 200)
        
    def test_missing_ethical_policy(self):
        """Test that missing compulsory ethical policies are rejected"""
        terms = {
            "max_calls": 100,
            "valid_days": 30
        }
        
        # Missing content_safety which is compulsory
        ethical_policies = ["fair_use", "data_privacy"]
        
        # Create agreement - should fail
        response = requests.post(
            f"{self.server.base_url}/agreements",
            json={
                "consumer_id": self.consumer.id,
                "provider_id": self.provider.id,
                "terms": terms,
                "ethical_policies": ethical_policies
            }
        )
        
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("error", data)
        self.assertIn("compulsory", data["error"].lower())
        
    def test_ethical_compliance(self):
        """Test ethical compliance checks"""
        # Create valid agreement first
        terms = {
            "max_calls": 100,
            "max_cpu": 0.5,
            "valid_days": 30
        }
        
        ethical_policies = ["content_safety", "fair_use", "data_privacy"]
        
        # Create agreement 
        response = requests.post(
            f"{self.server.base_url}/agreements",
            json={
                "consumer_id": self.consumer.id,
                "provider_id": self.provider.id,
                "terms": terms,
                "ethical_policies": ethical_policies
            }
        )
        
        agreement_id = response.json()["id"]
        
        # Test valid content - should pass
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/check",
            json={
                "content": "This is acceptable content",
                "quantity": 10
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertTrue(data["compliant"])
        
        # Test excessive resource usage - should fail
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/check",
            json={
                "content": "This is acceptable content",
                "quantity": 5000  # Exceeds fair use policy
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["compliant"])
        self.assertIn("excessive", data["reason"].lower())
        
        # Test harmful content - should fail
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/check",
            json={
                "content": "This contains harmful content",
                "quantity": 10
            }
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["compliant"])
        self.assertIn("prohibited content", data["reason"].lower())
        
    def test_usage_recording(self):
        """Test recording usage against an agreement"""
        # Create valid agreement first
        terms = {
            "max_calls": 5,  # Low limit to test exceeding
            "valid_days": 30
        }
        
        ethical_policies = ["content_safety", "fair_use"]
        
        # Create agreement 
        response = requests.post(
            f"{self.server.base_url}/agreements",
            json={
                "consumer_id": self.consumer.id,
                "provider_id": self.provider.id,
                "terms": terms,
                "ethical_policies": ethical_policies
            }
        )
        
        agreement_id = response.json()["id"]
        
        # Record usage - should succeed
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/usage",
            json={
                "metric": "calls",
                "quantity": 2
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Record more usage - should succeed
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/usage",
            json={
                "metric": "calls",
                "quantity": 2
            }
        )
        self.assertEqual(response.status_code, 200)
        
        # Record usage that exceeds limit - should fail
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/usage",
            json={
                "metric": "calls",
                "quantity": 2
            }
        )
        self.assertEqual(response.status_code, 400)
        data = response.json()
        self.assertIn("limit exceeded", data["error"].lower())
        
    def test_agreement_expiration(self):
        """Test that expired agreements are rejected"""
        # Create agreement that expires immediately
        terms = {
            "max_calls": 100,
            "expires_at": int(time.time()) - 1  # Already expired
        }
        
        ethical_policies = ["content_safety", "fair_use"]
        
        # Create agreement 
        response = requests.post(
            f"{self.server.base_url}/agreements",
            json={
                "consumer_id": self.consumer.id,
                "provider_id": self.provider.id,
                "terms": terms,
                "ethical_policies": ethical_policies
            }
        )
        
        agreement_id = response.json()["id"]
        
        # Verify agreement - should fail due to expiration
        response = requests.get(
            f"{self.server.base_url}/agreements/{agreement_id}"
        )
        self.assertEqual(response.status_code, 200)
        data = response.json()
        self.assertFalse(data["valid"])
        self.assertIn("expired", data["error_message"].lower())
        
        # Try to record usage - should fail
        response = requests.post(
            f"{self.server.base_url}/agreements/{agreement_id}/usage",
            json={
                "metric": "calls",
                "quantity": 1
            }
        )
        self.assertEqual(response.status_code, 400)
        

if __name__ == "__main__":
    unittest.main()
