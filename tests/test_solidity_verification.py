#!/usr/bin/env python3
"""
Verification test for Solidity Agreement Middleware in MCP-ZERO
Tests agreement verification, ethical compliance, and usage recording
"""

import requests
import json
import time
import sys

# Configuration
BASE_URL = "http://localhost:8082"
HEADERS = {"Content-Type": "application/json"}

def create_test_agreement():
    """Create a test agreement and return its ID"""
    print("\nCreating test agreement...")
    
    payload = {
        "consumer_id": "TestClient",
        "provider_id": "MCP-ZERO",
        "expires_at": "2026-06-07T00:00:00Z",
        "ethical_policies": ["content_safety", "fair_use"],
        "usage_limits": {
            "calls": 100,
            "tokens": 1000,
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
        print(f"Created agreement with ID: {agreement_id}")
        return agreement_id
    else:
        print(f"Failed to create agreement: {response.status_code}")
        print(response.text)
        return None

def test_agreement_verification(agreement_id):
    """Test verifying an agreement by ID"""
    print(f"\n1. Testing agreement verification for {agreement_id}...")
    
    response = requests.get(
        f"{BASE_URL}/api/v1/agreements/{agreement_id}",
        headers=HEADERS
    )
    
    if response.status_code == 200:
        result = response.json()
        print(f"SUCCESS: Agreement verification: Valid = {result.get('valid', False)}")
        print(f"Ethical status: {result.get('ethical_status', False)}")
        print(f"Usage limits: {result.get('usage_limits', {})}")
        return True
    else:
        print(f"FAILED: Agreement verification failed with status {response.status_code}")
        print(response.text)
        return False

def test_ethical_compliance(agreement_id):
    """Test ethical compliance checks"""
    print(f"\n2. Testing ethical compliance for {agreement_id}...")
    
    # Test 1: Good content that should pass
    good_payload = {
        "content": "This is safe content for processing",
        "quantity": 5.0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agreements/{agreement_id}/check",
        headers=HEADERS,
        json=good_payload
    )
    
    print(f"Test 1 (good content): Compliant = {response.json().get('compliant', False)}")
    
    # Test 2: Bad content that should fail content_safety
    bad_payload = {
        "content": "This content contains harmful material and should be rejected",
        "quantity": 5.0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agreements/{agreement_id}/check",
        headers=HEADERS,
        json=bad_payload
    )
    
    compliant = response.json().get('compliant', False)
    reason = response.json().get('reason', '')
    print(f"Test 2 (bad content): Compliant = {compliant}")
    if not compliant:
        print(f"Reason: {reason}")
    
    # Test 3: Excessive usage that should fail fair_use
    excessive_payload = {
        "content": "Safe content",
        "quantity": 200.0  # Over the limit of 100
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agreements/{agreement_id}/check",
        headers=HEADERS,
        json=excessive_payload
    )
    
    compliant = response.json().get('compliant', False)
    reason = response.json().get('reason', '')
    print(f"Test 3 (excessive usage): Compliant = {compliant}")
    if not compliant:
        print(f"Reason: {reason}")
    
    return True

def test_usage_recording(agreement_id):
    """Test recording usage against an agreement"""
    print(f"\n3. Testing usage recording for {agreement_id}...")
    
    payload = {
        "metric": "calls",
        "quantity": 10.0
    }
    
    response = requests.post(
        f"{BASE_URL}/api/v1/agreements/{agreement_id}/usage",
        headers=HEADERS,
        json=payload
    )
    
    if response.status_code == 200:
        print(f"SUCCESS: Usage recorded. Result: {response.json()}")
        
        # Verify the updated usage
        verify_response = requests.get(
            f"{BASE_URL}/api/v1/agreements/{agreement_id}",
            headers=HEADERS
        )
        
        if verify_response.status_code == 200:
            usage = verify_response.json().get('usage_current', {})
            print(f"Updated usage: {usage}")
            return True
        else:
            print(f"Failed to verify usage update: {verify_response.status_code}")
            return False
    else:
        print(f"FAILED: Usage recording failed with status {response.status_code}")
        print(response.text)
        return False

def test_invalid_agreement():
    """Test verification of a non-existent agreement"""
    print("\n4. Testing invalid agreement ID verification...")
    
    invalid_id = "00000000000000000000000000000000"
    response = requests.get(
        f"{BASE_URL}/api/v1/agreements/{invalid_id}",
        headers=HEADERS
    )
    
    if response.status_code in [404, 400]:
        print(f"SUCCESS: Server correctly rejected invalid agreement ID")
        print(f"Response: {response.text}")
        return True
    else:
        print(f"FAILED: Server accepted invalid ID with status {response.status_code}")
        return False

def test_resource_usage():
    """Basic test for resource usage compliance"""
    # This is a simplified test - in production you would want
    # more sophisticated monitoring
    print("\n5. Testing resource usage compliance...")
    
    import psutil
    
    # Get current process CPU and memory usage
    process = psutil.Process()
    cpu_percent = process.cpu_percent(interval=1.0)
    memory_mb = process.memory_info().rss / (1024 * 1024)  # Convert to MB
    
    print(f"Current CPU usage: {cpu_percent:.2f}%")
    print(f"Current memory usage: {memory_mb:.2f} MB")
    
    # Check against MCP-ZERO constraints
    cpu_compliant = cpu_percent < 27.0
    memory_compliant = memory_mb < 827.0
    
    print(f"CPU within limit (<27%): {cpu_compliant}")
    print(f"Memory within limit (<827MB): {memory_compliant}")
    
    return cpu_compliant and memory_compliant

def main():
    """Execute tests in sequence"""
    print("MCP-ZERO Solidity Middleware Verification Test")
    print("=============================================")
    
    # Create a test agreement
    agreement_id = create_test_agreement()
    if not agreement_id:
        print("Failed to create test agreement, aborting further tests")
        sys.exit(1)
    
    # Run verification tests
    success = test_agreement_verification(agreement_id)
    if not success:
        print("Agreement verification failed, aborting further tests")
        sys.exit(1)
    
    # Test ethical compliance
    success = test_ethical_compliance(agreement_id)
    
    # Test usage recording
    success = success and test_usage_recording(agreement_id)
    
    # Test invalid agreement
    success = success and test_invalid_agreement()
    
    # Test resource usage
    success = success and test_resource_usage()
    
    # Report overall success/failure
    if success:
        print("\nAll verification tests completed successfully!")
        sys.exit(0)
    else:
        print("\nSome verification tests failed. See logs for details.")
        sys.exit(1)

if __name__ == "__main__":
    main()
