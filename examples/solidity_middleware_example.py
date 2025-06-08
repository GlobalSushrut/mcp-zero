#!/usr/bin/env python3
"""
MCP-ZERO Solidity Agreement Example (Middleware-based)
This example shows how to use Solidity agreements without blockchain
while enforcing compulsory ethical policies.
"""

import asyncio
import json
from datetime import datetime, timedelta

from mcp_zero.sdk import Agent
from mcp_zero.agreements import SolidityAgreement
from mcp_zero.ethical import PolicyRegistry

async def main():
    print("MCP-ZERO Solidity Agreement Example (Middleware-based)")
    print("=====================================================")
    
    # Create consumer and provider agents
    consumer = Agent.spawn(name="consumer")
    provider = Agent.spawn(name="provider")
    
    print(f"Created consumer agent: {consumer.id}")
    print(f"Created provider agent: {provider.id}")
    
    # Define agreement terms
    terms = {
        "max_calls": 100,
        "max_cpu": 0.5,  # CPU cores
        "expires_at": (datetime.now() + timedelta(days=30)).timestamp()
    }
    
    # Define ethical policies (content_safety and fair_use are compulsory)
    ethical_policies = ["content_safety", "fair_use", "data_privacy"]
    
    # Create Solidity agreement through middleware (no blockchain)
    print("\nCreating agreement...")
    agreement_id = await SolidityAgreement.create(
        consumer_id=consumer.id,
        provider_id=provider.id,
        terms=terms,
        ethical_policies=ethical_policies,
        use_middleware=True  # Skip blockchain, use middleware
    )
    
    print(f"Agreement created: {agreement_id}")
    
    # Verify the agreement
    print("\nVerifying agreement...")
    verification = await SolidityAgreement.verify(
        agreement_id=agreement_id,
        use_middleware=True
    )
    
    print(f"Agreement valid: {verification.valid}")
    print(f"Ethical status: {verification.ethical_status}")
    print(f"Current usage: {verification.usage_current}")
    print(f"Usage limits: {verification.usage_limits}")
    
    # Record some usage
    print("\nRecording usage...")
    await SolidityAgreement.record_usage(
        agreement_id=agreement_id,
        method_name="process_data",
        metric="calls",
        quantity=1,
        use_middleware=True
    )
    
    print("Usage recorded")
    
    # Try an operation with ethical check
    print("\nTesting ethical compliance...")
    try:
        # This should pass
        params = {
            "content": "This is acceptable content",
            "quantity": 1
        }
        
        compliant, reason = await SolidityAgreement.check_ethical_compliance(
            agreement_id=agreement_id,
            params=params,
            use_middleware=True
        )
        
        print(f"Ethical check 1: {compliant}")
        
        # This should fail (excessive usage)
        params = {
            "content": "This is acceptable content",
            "quantity": 5000  # Exceeds fair use policy
        }
        
        compliant, reason = await SolidityAgreement.check_ethical_compliance(
            agreement_id=agreement_id,
            params=params,
            use_middleware=True
        )
        
        print(f"Ethical check 2: {compliant}")
        print(f"Reason: {reason}")
        
    except Exception as e:
        print(f"Error in ethical check: {e}")
    
    # Execute a function in the agreement
    print("\nExecuting agreement function...")
    try:
        result = await SolidityAgreement.execute_function(
            agreement_id=agreement_id,
            function_name="getUsage",
            params={"metric": "calls"},
            use_middleware=True
        )
        print(f"Function result: {result}")
    except Exception as e:
        print(f"Error executing function: {e}")
    
    print("\nExample complete!")

if __name__ == "__main__":
    asyncio.run(main())
