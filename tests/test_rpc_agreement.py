#!/usr/bin/env python3
"""
RPC Agreement Integration Test
Tests the integration of Solidity agreement middleware with MCP-ZERO RPC server
"""

import os
import sys
import json
import time
import requests
import subprocess
import argparse

# Set base URL for API server
BASE_URL = "http://localhost:8082"

def start_server():
    """Start the MCP-ZERO server for testing"""
    print("Starting MCP-ZERO server...")
    
    # Run server in background
    server_process = subprocess.Popen(
        ["go", "run", "main.go"],
        cwd="/home/umesh/Videos/mcp_zero/src/rpc-layer/cmd/mcp-server",
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE
    )
    
    # Wait for server to start (crude but effective)
    time.sleep(3)
    
    return server_process

def test_health_check():
    """Test the health check endpoint"""
    print("\n1. Testing health check...")
    
    response = requests.get(f"{BASE_URL}/health")
    if response.status_code != 200:
        print(f"FAILED: Health check returned status {response.status_code}")
        return False
    
    print(f"SUCCESS: Health check returned {response.json()}")
    return True

def test_create_agreement():
    """Test creating a Solidity agreement"""
    print("\n2. Testing agreement creation with ethical policies...")
    
    # Define payload with compulsory ethical policies
    payload = {
        "consumer_id": "agent-123",
        "provider_id": "agent-456",
        "terms": {
            "max_calls": 100,
            "max_cpu": 0.5,
            "expires_at": int(time.time()) + 86400  # 1 day from now
        },
        "ethical_policies": ["content_safety", "fair_use"]
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Agreement creation returned status {response.status_code}")
        print(f"Response: {response.json()}")
        return None
    
    result = response.json()
    agreement_id = result.get("id")
    print(f"SUCCESS: Created agreement with ID: {agreement_id}")
    return agreement_id

def test_missing_ethical_policy():
    """Test that missing compulsory ethical policy is rejected"""
    print("\n3. Testing missing ethical policy rejection...")
    
    # Define payload with missing compulsory ethical policy
    payload = {
        "consumer_id": "agent-789",
        "provider_id": "agent-101112",
        "terms": {
            "max_calls": 100,
            "max_cpu": 0.5,
        },
        "ethical_policies": []  # Missing required policies
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements", json=payload)
    
    # Should fail with 400 Bad Request
    if response.status_code == 400:
        print(f"SUCCESS: Server correctly rejected agreement with missing ethical policies")
        print(f"Response: {response.json()}")
        return True
    else:
        print(f"FAILED: Server accepted agreement with missing ethical policies")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return False

def test_verify_agreement(agreement_id):
    """Test verifying an agreement"""
    print(f"\n4. Testing agreement verification for {agreement_id}...")
    
    response = requests.get(f"{BASE_URL}/api/v1/agreements/{agreement_id}")
    if response.status_code != 200:
        print(f"FAILED: Verification returned status {response.status_code}")
        print(f"Response: {response.json()}")
        return False
    
    result = response.json()
    print(f"SUCCESS: Agreement verification: Valid = {result.get('Valid')}")
    print(f"Ethical status: {result.get('EthicalStatus')}")
    print(f"Usage limits: {result.get('UsageLimits')}")
    return True

def test_ethical_compliance(agreement_id):
    """Test ethical compliance checking"""
    print(f"\n5. Testing ethical compliance for {agreement_id}...")
    
    # Test 1: Good content
    payload = {
        "content": "This is acceptable content",
        "quantity": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements/{agreement_id}/check", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Compliance check returned status {response.status_code}")
        print(f"Response: {response.json()}")
        return False
    
    result = response.json()
    print(f"Test 1 (good content): Compliant = {result.get('compliant')}")
    
    # Test 2: Bad content
    payload = {
        "content": "This contains harmful content",
        "quantity": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements/{agreement_id}/check", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Compliance check returned status {response.status_code}")
        print(f"Response: {response.json()}")
        return False
    
    result = response.json()
    print(f"Test 2 (bad content): Compliant = {result.get('compliant')}")
    print(f"Reason: {result.get('reason')}")
    
    # Test 3: Excessive usage
    payload = {
        "content": "This is acceptable content",
        "quantity": 5000  # Excessive
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements/{agreement_id}/check", json=payload)
    result = response.json()
    print(f"Test 3 (excessive usage): Compliant = {result.get('compliant')}")
    print(f"Reason: {result.get('reason')}")
    
    return True

def test_record_usage(agreement_id):
    """Test recording usage"""
    print(f"\n6. Testing usage recording for {agreement_id}...")
    
    # Record some usage
    payload = {
        "metric": "calls",
        "quantity": 10
    }
    
    response = requests.post(f"{BASE_URL}/api/v1/agreements/{agreement_id}/usage", json=payload)
    if response.status_code != 200:
        print(f"FAILED: Usage recording returned status {response.status_code}")
        print(f"Response: {response.json()}")
        return False
    
    result = response.json()
    print(f"SUCCESS: Usage recorded. Result: {result}")
    
    # Verify updated usage
    response = requests.get(f"{BASE_URL}/api/v1/agreements/{agreement_id}")
    result = response.json()
    print(f"Updated usage: {result.get('UsageCurrent')}")
    
    return True

def main():
    """Run the integration tests"""
    parser = argparse.ArgumentParser(description='Test MCP-ZERO RPC Agreement Integration')
    parser.add_argument('--no-server', action='store_true', help='Do not start a server (use existing one)')
    args = parser.parse_args()
    
    server_process = None
    
    try:
        # Start server if needed
        if not args.no_server:
            server_process = start_server()
        
        # Run tests
        test_health_check()
        agreement_id = test_create_agreement()
        if agreement_id:
            test_verify_agreement(agreement_id)
            test_ethical_compliance(agreement_id)
            test_record_usage(agreement_id)
        
        test_missing_ethical_policy()
        
        print("\nAll tests completed!")
        
    finally:
        # Clean up
        if server_process:
            print("Stopping server...")
            server_process.terminate()
            server_process.wait()

if __name__ == "__main__":
    main()
