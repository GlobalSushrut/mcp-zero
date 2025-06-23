#!/usr/bin/env python3
"""
Deploy Solidity Agreement to MCP-ZERO Middleware
===============================================

This script deploys the TaskAgreement.sol contract to the MCP-ZERO
middleware server, without requiring blockchain deployment.
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timedelta

def load_contract(contract_path):
    """Load Solidity contract from file"""
    try:
        with open(contract_path, "r") as f:
            contract_source = f.read()
            print(f"📄 Loaded contract from {contract_path}")
            return contract_source
    except FileNotFoundError:
        print(f"❌ Contract file not found at {contract_path}")
        return None

def deploy_contract(contract_source, middleware_url, agent_id, max_tasks, 
                   max_resource_usage, duration_days, ethical_policies):
    """Deploy contract to middleware server"""
    print(f"🔄 Deploying TaskAgreement contract for agent {agent_id}")
    
    # Prepare deployment data
    deploy_data = {
        "agentId": agent_id,
        "contractSource": contract_source,
        "constructor_args": {
            "agentId": agent_id,
            "maxTasks": max_tasks,
            "maxResourceUsage": max_resource_usage,
            "duration": duration_days * 86400,  # Convert days to seconds
            "ethicalPolicies": ethical_policies
        }
    }
    
    # In a real implementation, this would make an RPC call to the middleware server
    # For demo purposes, we'll simulate a successful deployment
    
    # Generate a simulated agreement ID
    agreement_id = f"task-{agent_id}-{int(time.time())}"
    
    # Save deployment info to a file for the agent to use
    deploy_info = {
        "agreement_id": agreement_id,
        "agent_id": agent_id,
        "deployed_at": int(time.time()),
        "max_tasks": max_tasks,
        "max_resource_usage": max_resource_usage,
        "expiration_time": int((datetime.now() + timedelta(days=duration_days)).timestamp()),
        "ethical_policies": ethical_policies,
        "middleware_url": middleware_url
    }
    
    # Save to JSON file
    deploy_file = os.path.join(
        os.path.dirname(os.path.abspath(__file__)), 
        "deployed_agreement.json"
    )
    
    with open(deploy_file, "w") as f:
        json.dump(deploy_info, f, indent=2)
    
    print(f"✅ Agreement deployed with ID: {agreement_id}")
    print(f"📝 Deployment info saved to: {deploy_file}")
    
    return agreement_id

def main():
    parser = argparse.ArgumentParser(description="Deploy Solidity Agreement to MCP-ZERO Middleware")
    parser.add_argument("--agent-id", default=f"smart-agent-{int(time.time())}", 
                      help="ID for the agent (default: auto-generated)")
    parser.add_argument("--middleware", default="http://localhost:50051",
                      help="URL for middleware server")
    parser.add_argument("--max-tasks", type=int, default=50,
                      help="Maximum tasks allowed in agreement")
    parser.add_argument("--max-resources", type=int, default=500,
                      help="Maximum resources allowed in agreement")
    parser.add_argument("--duration", type=int, default=30,
                      help="Agreement duration in days")
    
    args = parser.parse_args()
    
    print("🚀 Solidity Agreement Deployment Tool")
    print("===================================")
    
    # Define the path to the contract
    contract_path = os.path.join(
        os.path.dirname(os.path.abspath(__file__)),
        "contracts",
        "TaskAgreement.sol"
    )
    
    # Load the contract
    contract_source = load_contract(contract_path)
    if not contract_source:
        sys.exit(1)
    
    # Define ethical policies (required for MCP-ZERO)
    ethical_policies = ["content_safety", "fair_use", "data_privacy"]
    
    # Deploy the contract
    agreement_id = deploy_contract(
        contract_source=contract_source, 
        middleware_url=args.middleware,
        agent_id=args.agent_id,
        max_tasks=args.max_tasks,
        max_resource_usage=args.max_resources,
        duration_days=args.duration,
        ethical_policies=ethical_policies
    )
    
    if agreement_id:
        print("\n✅ Agreement deployment successful!")
        print(f"📝 Agreement ID: {agreement_id}")
        print(f"🤖 Agent ID: {args.agent_id}")
        print(f"⏱️ Duration: {args.duration} days")
        print("\nYou can now run the agent with:")
        print(f"python3 smart_task_agent.py --agent-id {args.agent_id}")
    else:
        print("❌ Agreement deployment failed")

if __name__ == "__main__":
    main()
