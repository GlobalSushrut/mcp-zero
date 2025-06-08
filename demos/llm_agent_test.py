#!/usr/bin/env python3
"""
Tests MCP-ZERO LLM Agent Interaction
"""
import json
import logging
import requests
import time

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("llm_agent_test")

# Service URLs
RPC_URL = "http://localhost:8081"
LLM_URL = "http://localhost:8083"  # Mock if not available

def create_agent():
    """Create a new agent via RPC"""
    logger.info("Creating new agent...")
    
    response = requests.post(
        f"{RPC_URL}/api/v1/agents",
        json={"name": f"llm-agent-{int(time.time())}"},
        timeout=3
    )
    agent_data = response.json()
    agent_id = agent_data.get("agent_id")
    
    logger.info(f"Created agent: {agent_id}")
    return agent_id

def attach_llm_plugin(agent_id):
    """Attach LLM plugin to agent"""
    logger.info(f"Attaching LLM plugin to agent {agent_id}...")
    
    response = requests.post(
        f"{RPC_URL}/api/v1/agents/{agent_id}/plugins",
        json={"plugin_id": "llm-processor"},
        timeout=3
    )
    result = response.json()
    
    logger.info(f"Plugin attachment result: {json.dumps(result, indent=2)}")
    return result.get("success", False)

def test_llm_interaction(agent_id, prompt):
    """Test LLM interaction through agent"""
    logger.info(f"Testing LLM interaction with agent {agent_id}...")
    logger.info(f"Prompt: {prompt}")
    
    # Prepare LLM request
    llm_request = {
        "intent": "generate_response",
        "inputs": {
            "prompt": prompt,
            "max_tokens": 100
        }
    }
    
    try:
        # Try direct LLM server first
        response = requests.post(
            f"{LLM_URL}/api/v1/generate",
            json={"prompt": prompt, "max_tokens": 100},
            timeout=5
        )
        response.raise_for_status()
        llm_direct = response.json()
        logger.info(f"Direct LLM response: {llm_direct.get('text', '')}")
        
    except requests.RequestException:
        logger.warning("LLM server unavailable, using RPC agent execute instead")
        
    # Always test via agent execution
    response = requests.post(
        f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
        json=llm_request,
        timeout=5
    )
    result = response.json()
    
    logger.info(f"LLM agent execution result: {json.dumps(result, indent=2)}")
    return result

if __name__ == "__main__":
    # Create agent
    agent_id = create_agent()
    
    # Attach LLM plugin
    attach_llm_plugin(agent_id)
    
    # Test LLM interaction
    test_prompt = "Explain how MCP-ZERO implements ethical governance in 2-3 sentences."
    llm_result = test_llm_interaction(agent_id, test_prompt)
    
    logger.info("LLM agent interaction test completed")
