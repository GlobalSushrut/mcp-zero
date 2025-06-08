#!/usr/bin/env python3
"""
Tests MCP-ZERO Agent-to-Agent Interaction and Memory Storage/Retrieval
"""
import json
import logging
import requests
import time
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("agent_memory_test")

# Service URLs
RPC_URL = "http://localhost:8081"
DB_URL = "http://localhost:8082"

def create_agents():
    """Create two agents for interaction testing"""
    logger.info("Creating agent pair for interaction test...")
    
    agents = []
    for i in range(2):
        response = requests.post(
            f"{RPC_URL}/api/v1/agents",
            json={"name": f"agent-{i}-{int(time.time())}"},
            timeout=3
        )
        agent_id = response.json().get("agent_id")
        agents.append(agent_id)
        logger.info(f"Created agent {i+1}: {agent_id}")
    
    return agents

def attach_plugins(agent_ids):
    """Attach required plugins to agents"""
    logger.info("Attaching plugins to agents...")
    
    for idx, agent_id in enumerate(agent_ids):
        plugins = ["agent-comms", "memory-store"] if idx == 0 else ["agent-comms"]
        
        for plugin in plugins:
            response = requests.post(
                f"{RPC_URL}/api/v1/agents/{agent_id}/plugins",
                json={"plugin_id": plugin},
                timeout=3
            )
            result = response.json()
            logger.info(f"Plugin {plugin} attachment to {agent_id}: {result.get('success', False)}")

def test_agent_interaction(agent_ids):
    """Test agent-to-agent interaction"""
    logger.info("Testing agent-to-agent interaction...")
    
    # Source and target agents
    source_id, target_id = agent_ids
    
    # Message for agent interaction
    message = {
        "content": "Request analysis of sustainability metrics",
        "metadata": {
            "priority": "high",
            "requested_at": time.time()
        }
    }
    
    # Execute interaction intent
    interaction_request = {
        "intent": "send_message",
        "inputs": {
            "target_agent_id": target_id,
            "message": message
        }
    }
    
    response = requests.post(
        f"{RPC_URL}/api/v1/agents/{source_id}/execute",
        json=interaction_request,
        timeout=5
    )
    result = response.json()
    
    logger.info(f"Agent interaction result: {json.dumps(result, indent=2)}")
    return result

def store_agent_memory(agent_id, memory_data):
    """Store memory data for an agent"""
    logger.info(f"Storing memory for agent {agent_id}...")
    
    # Create memory storage request with ZK-traceable hash
    memory_hash = hashlib.sha256(json.dumps(memory_data).encode()).hexdigest()
    
    storage_data = {
        "agent_id": agent_id,
        "memory_data": memory_data,
        "memory_hash": memory_hash,
        "timestamp": time.time()
    }
    
    try:
        # Try real DB server first
        response = requests.post(
            f"{DB_URL}/api/v1/memories",
            json=storage_data,
            timeout=3
        )
        response.raise_for_status()
        result = response.json()
        
    except requests.RequestException:
        logger.warning("DB server endpoint unavailable, using RPC execute as fallback")
        # Use agent execute as fallback
        memory_request = {
            "intent": "store_memory",
            "inputs": storage_data
        }
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
            json=memory_request,
            timeout=3
        )
        result = response.json()
    
    logger.info(f"Memory storage result: {json.dumps(result, indent=2)}")
    return memory_hash

def retrieve_agent_memory(agent_id, memory_hash):
    """Retrieve memory data for an agent"""
    logger.info(f"Retrieving memory for agent {agent_id}...")
    
    try:
        # Try real DB server first
        response = requests.get(
            f"{DB_URL}/api/v1/memories/{agent_id}/{memory_hash}",
            timeout=3
        )
        response.raise_for_status()
        result = response.json()
        
    except requests.RequestException:
        logger.warning("DB server endpoint unavailable, using RPC execute as fallback")
        # Use agent execute as fallback
        retrieval_request = {
            "intent": "retrieve_memory",
            "inputs": {
                "agent_id": agent_id,
                "memory_hash": memory_hash
            }
        }
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
            json=retrieval_request,
            timeout=3
        )
        result = response.json()
    
    logger.info(f"Memory retrieval result: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    # Create two agents
    agent_ids = create_agents()
    
    # Attach required plugins
    attach_plugins(agent_ids)
    
    # Test agent interaction
    interaction_result = test_agent_interaction(agent_ids)
    
    # Create sample memory
    test_memory = {
        "interaction_id": str(int(time.time())),
        "content": "Analysis of sustainability metrics shows 98% compliance",
        "status": "completed",
        "created_at": time.time()
    }
    
    # Test memory storage
    memory_hash = store_agent_memory(agent_ids[0], test_memory)
    
    # Test memory retrieval
    retrieved_memory = retrieve_agent_memory(agent_ids[0], memory_hash)
    
    logger.info("Agent interaction and memory tests completed")
