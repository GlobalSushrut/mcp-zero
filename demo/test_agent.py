#!/usr/bin/env python3
"""
MCP-ZERO Demo Agent Test

This script demonstrates the complete lifecycle of an MCP-ZERO agent:
1. spawn() - Create a new agent
2. attach_plugin() - Add capabilities via plugins
3. execute() - Run intents with traceability
4. snapshot() - Save agent state
5. recover() - Restore from snapshot

Hardware constraints are enforced throughout the process.
"""

import os
import sys
import time
import yaml
import logging
from pathlib import Path

from mcp_zero import (
    MCPClient, 
    AgentConfig, 
    Agent, 
    TraceManager, 
    setup_logger
)

# Setup logging
setup_logger(level="DEBUG")
logger = logging.getLogger("mcp_demo")

# Demo configuration
BASE_DIR = Path(__file__).parent
CONFIG_DIR = BASE_DIR / "configs"
AGENT_CONFIG_PATH = CONFIG_DIR / "agent_config.yaml"
PLUGIN_CONFIG_PATH = CONFIG_DIR / "plugin_config.yaml"


def load_agent_config():
    """Load agent configuration from YAML file."""
    logger.info(f"Loading agent config from {AGENT_CONFIG_PATH}")
    
    if not AGENT_CONFIG_PATH.exists():
        logger.error(f"Config file not found: {AGENT_CONFIG_PATH}")
        sys.exit(1)
    
    return AgentConfig.from_yaml(str(AGENT_CONFIG_PATH))


def run_demo():
    """Run the complete agent lifecycle demo."""
    logger.info("Starting MCP-ZERO Demo Agent Test")
    logger.info("=" * 50)
    
    # Create client - in a real scenario, this would connect to the Go RPC server
    # For the demo, we'll use the mock implementations in the client
    logger.info("Initializing MCP-ZERO client")
    client = MCPClient(host="localhost", port=50051)
    
    try:
        # Step 1: Spawn an agent
        logger.info("\n\n--- STEP 1: AGENT SPAWNING ---")
        agent_config = load_agent_config()
        logger.info(f"Spawning agent with name: {agent_config.name}")
        
        # This would normally make an RPC call to the kernel
        agent = client.spawn_agent(agent_config)
        logger.info(f"Agent spawned successfully with ID: {agent.id}")
        logger.info(f"Status: {agent.status.value}")
        
        # Step 2: Attach plugin
        logger.info("\n\n--- STEP 2: PLUGIN ATTACHMENT ---")
        plugin_id = "math-plugin"
        logger.info(f"Attaching plugin: {plugin_id}")
        
        success = agent.attach_plugin(plugin_id)
        if success:
            logger.info(f"Plugin {plugin_id} attached successfully")
        else:
            logger.error(f"Failed to attach plugin {plugin_id}")
            return
        
        logger.info(f"Agent plugins: {', '.join(agent.plugins)}")
        
        # Step 3: Execute intent
        logger.info("\n\n--- STEP 3: INTENT EXECUTION ---")
        intent = "calculate"
        parameters = {
            "operation": "add",
            "values": [5, 7, 3]
        }
        logger.info(f"Executing intent: {intent} with params: {parameters}")
        
        result = agent.execute(intent, parameters)
        logger.info(f"Execution result: {result}")
        logger.info(f"Trace ID: {result.get('trace_id', 'unknown')}")
        
        # Step 4: Create snapshot
        logger.info("\n\n--- STEP 4: AGENT SNAPSHOT ---")
        snapshot_id = agent.snapshot()
        logger.info(f"Created snapshot with ID: {snapshot_id}")
        
        # Execute another intent to modify state
        logger.info("Executing another intent to modify agent state...")
        agent.execute("store", {"key": "test", "value": "data"})
        
        # Step 5: Recover from snapshot
        logger.info("\n\n--- STEP 5: AGENT RECOVERY ---")
        logger.info(f"Recovering agent from snapshot: {snapshot_id}")
        
        success = agent.recover(snapshot_id)
        if success:
            logger.info(f"Agent recovered successfully, status: {agent.status.value}")
        else:
            logger.error("Failed to recover agent")
        
        # Check resource usage
        logger.info("\n\n--- RESOURCE MONITORING ---")
        resources = agent.get_resource_usage()
        logger.info(f"CPU usage: {resources['cpu_percent']}%")
        logger.info(f"Memory usage: {resources['memory_mb']}MB")
        logger.info(f"CPU utilization: {resources['cpu_utilization']}% of limit")
        logger.info(f"Memory utilization: {resources['memory_utilization']}% of limit")
        
        # Verify execution trace
        logger.info("\n\n--- TRACE VERIFICATION ---")
        trace_manager = TraceManager(client)
        
        # Use the trace ID from the earlier execution
        trace_id = result.get('trace_id', None)
        if trace_id:
            logger.info(f"Verifying trace: {trace_id}")
            trace = trace_manager.get_trace(trace_id)
            logger.info(f"Trace: {trace}")
            
            # Verify using ZK proof
            verified = trace_manager.verify(trace_id)
            logger.info(f"Trace verification: {'Successful' if verified else 'Failed'}")
        
        # Finally, terminate the agent
        logger.info("\n\n--- AGENT TERMINATION ---")
        agent.terminate()
        logger.info(f"Agent terminated, status: {agent.status.value}")
        
        logger.info("\n\nDemo completed successfully!")
        
    except Exception as e:
        logger.error(f"Error in demo: {e}", exc_info=True)
    finally:
        # Clean up
        client.close()


if __name__ == "__main__":
    run_demo()
