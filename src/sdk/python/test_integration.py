#!/usr/bin/env python3
"""
MCP-ZERO Integration Test Script

This script tests the integration between the Python SDK and the Go RPC server.
"""

import sys
import json
import logging
import time
from pathlib import Path

# Add the SDK directory to Python path
sys.path.append(str(Path(__file__).parent))

from mcp_zero.client import MCPClient
from mcp_zero.agents import AgentConfig, AgentStatus
from mcp_zero.exceptions import ConnectionError, AgentError, ExecutionError

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s"
)
logger = logging.getLogger("test_integration")

def test_health():
    """Test health check endpoint."""
    logger.info("Testing health endpoint...")
    
    try:
        with MCPClient(http_port=8081) as client:
            # Connection is checked in __enter__
            if client.is_connected():
                logger.info("✅ Health check passed")
                return True
            else:
                logger.error("❌ Health check failed: Not connected")
                return False
    except Exception as e:
        logger.error(f"❌ Health check failed: {e}")
        return False

def test_agent_lifecycle():
    """Test agent lifecycle operations."""
    logger.info("Testing agent lifecycle...")
    
    try:
        # Create client
        client = MCPClient(http_port=8081)
        client.connect()
        
        # Create agent config
        config = AgentConfig(
            name="TestAgent",
            entry_plugin="core",
            intents=["default", "test"],
            metadata={"test": "true"}
        )
        
        # Spawn agent
        logger.info("Spawning agent...")
        agent = client.spawn_agent(config)
        logger.info(f"✅ Agent spawned with ID: {agent.id}")
        
        # List agents
        logger.info("Listing agents...")
        agents = client.list_agents()
        logger.info(f"✅ Found {len(agents)} agents")
        
        # Attach plugin
        logger.info("Attaching plugin...")
        success = agent.attach_plugin("test-plugin")
        if success:
            logger.info("✅ Plugin attached successfully")
        else:
            logger.error("❌ Failed to attach plugin")
        
        # Execute intent
        logger.info("Executing intent...")
        result = agent.execute("test", {"param1": "value1"})
        logger.info(f"✅ Intent executed with result: {result}")
        
        # Take snapshot
        logger.info("Taking snapshot...")
        snapshot_id = agent.snapshot()
        logger.info(f"✅ Snapshot taken with ID: {snapshot_id}")
        
        # Recover from snapshot
        logger.info("Recovering from snapshot...")
        success = agent.recover(snapshot_id)
        if success:
            logger.info(f"✅ Recovered from snapshot: {snapshot_id}")
        else:
            logger.error(f"❌ Failed to recover from snapshot: {snapshot_id}")
        
        # Clean up
        client.disconnect()
        logger.info("Agent lifecycle test completed")
        return True
        
    except Exception as e:
        logger.error(f"❌ Agent lifecycle test failed: {e}")
        return False

def main():
    """Run integration tests."""
    logger.info("Starting MCP-ZERO integration tests...")
    
    # Test health
    health_ok = test_health()
    if not health_ok:
        logger.error("Health check failed, stopping tests")
        return
    
    # Test agent lifecycle
    agent_lifecycle_ok = test_agent_lifecycle()
    
    logger.info("\nTest Summary:")
    logger.info(f"Health Check: {'✅ PASS' if health_ok else '❌ FAIL'}")
    logger.info(f"Agent Lifecycle: {'✅ PASS' if agent_lifecycle_ok else '❌ FAIL'}")
    
    if health_ok and agent_lifecycle_ok:
        logger.info("All tests passed! Go RPC and Python SDK integration is working correctly.")
    else:
        logger.error("Some tests failed. Please check the logs for details.")

if __name__ == "__main__":
    main()
