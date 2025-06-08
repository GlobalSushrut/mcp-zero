#!/usr/bin/env python3
"""
MCP-ZERO SDK Production Demo
A minimal but complete example showing core functionality with real RPC server.
"""

import os
import sys
import logging
import time

# Add SDK to path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "../sdk")))

from mcp_zero import Agent, Plugin, ResourceMonitor
from mcp_zero.exceptions import MCPError
from mcp_zero.rpc_client import RPCClient

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("demo")

def main():
    """Run a minimal production demo of MCP-ZERO capabilities"""
    try:
        # 0. Connect to the real RPC server
        rpc_client = RPCClient(api_url="http://localhost:8081")
        logger.info("Connected to real RPC server at http://localhost:8081")
        
        # 1. Initialize resource monitoring
        monitor = ResourceMonitor()
        monitor.start_monitoring()
        logger.info(f"Initial resource usage: CPU {monitor.get_cpu_percent():.1f}%, Memory {monitor.get_memory_mb():.1f}MB")
        
        # 2. Create an agent
        logger.info("Creating agent...")
        agent = Agent.spawn(
            name="document-analyzer",
            api_url="http://localhost:8081"  # Connect to the real server
        )
        
        # Set the resource monitor after creation
        agent.resource_monitor = monitor
        logger.info(f"Agent created with ID: {agent.id}")
        
        # 3. Load plugins (using dummy path for demo)
        dummy_plugin_path = os.path.join(os.path.dirname(__file__), "dummy_plugin.wasm")
        # Create empty file for demo purposes
        with open(dummy_plugin_path, "wb") as f:
            f.write(b"WASM\x01\x00\x00\x00")
            
        try:
            logger.info("Loading plugin...")
            plugin = Plugin.from_path(dummy_plugin_path)
            agent.attach_plugin(plugin)
            logger.info(f"Plugin '{plugin.name}' attached")
        except MCPError as e:
            logger.warning(f"Plugin demo skipped: {str(e)}")
            
        # 4. Execute an intent
        logger.info("Executing test intent...")
        result = agent.execute(
            intent="analyze_document",
            inputs={"text": "This is a test document for MCP-ZERO demo."}
        )
        logger.info(f"Execution result: {result}")
        
        # 5. Create a snapshot
        logger.info("Creating snapshot...")
        snapshot_id = agent.snapshot({"demo": True, "timestamp": "2025-06-07"})
        logger.info(f"Snapshot created with ID: {snapshot_id}")
        
        # 6. Report final resource usage
        logger.info(f"Final resource usage: CPU {monitor.get_cpu_percent():.1f}%, Memory {monitor.get_memory_mb():.1f}MB")
        logger.info(f"Peak resource usage: CPU {monitor.get_peak_cpu():.1f}%, Memory {monitor.get_peak_memory_mb():.1f}MB")
        
        return True
        
    except MCPError as e:
        logger.error(f"MCP-ZERO Error: {str(e)}")
        return False
    except Exception as e:
        logger.error(f"Unexpected error: {str(e)}")
        return False

if __name__ == "__main__":
    success = main()
    sys.exit(0 if success else 1)
