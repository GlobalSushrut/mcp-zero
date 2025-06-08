#!/usr/bin/env python3
"""
Basic test for Solidity Agreement Middleware in MCP-ZERO
Tests health check and agreement creation only
"""

import requests
import json
import time

# Configuration
BASE_URL = "http://localhost:8082"
HEADERS = {"Content-Type": "application/json"}

def test_health_check():
    """Test server health check endpoint"""
    print("\n1. Testing health check...")
    response = requests.get(f"{BASE_URL}/health")
    
    if response.status_code == 200:
        print(f"SUCCESS: Health check returned {response.json()}")
        return True
    else:
        print(f"FAILED: Health check failed with status {response.status_code}")
        print(response.text)
        return False

def test_agreement_creation():
    """Test agreement creation with required ethical policies"""
    print("\n2. Testing agreement creation with ethical policies...")
    
    payload = {
        "consumer_id": "TestClient",
        "provider_id": "MCP-ZERO",
        "expires_at": "2026-06-07T00:00:00Z",
        "ethical_policies": ["content_safety", "fair_use"],
        "usage_limits": {
            "calls": 100,
            "cpu": 0.5
        },
        "terms": {"version": "1.0"}
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agreements", 
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code in [200, 201]:
        agreement_id = response.json().get("id")
        print(f"SUCCESS: Created agreement with ID: {agreement_id}")
        return agreement_id
    else:
        print(f"FAILED: Agreement creation failed with status {response.status_code}")
        print(response.text)
        return None

def main():
    """Execute tests in sequence"""
    print("MCP-ZERO Solidity Middleware Basic Test")
    print("======================================")
    
    # Step 1: Test health check
    if not test_health_check():
        print("Health check failed, aborting further tests")
        return
    
    # Step 2: Test agreement creation
    agreement_id = test_agreement_creation()
    if not agreement_id:
        print("Agreement creation failed, aborting further tests")
        return
        
    print("\nAll basic tests completed successfully!")

if __name__ == "__main__":
    main()
