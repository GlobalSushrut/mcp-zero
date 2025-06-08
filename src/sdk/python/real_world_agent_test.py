#!/usr/bin/env python3
"""
MCP-ZERO Real-World Agent Test

This script tests the complete MCP-ZERO stack:
- Rust kernel (agent core functionality)
- Go RPC server (communication layer)
- Python SDK (client interface)

It creates and manages a simple AI agent that processes
basic intents and demonstrates the complete agent lifecycle.

Hardware monitoring is included to verify we stay within the
specified constraints (<27% CPU, <827MB RAM).
"""

import os
import time
import json
import subprocess
import argparse
import psutil
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional

# Import the MCP-ZERO Python SDK
from mcp_zero.client import MCPClient
from mcp_zero.agents import AgentConfig

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)

logger = logging.getLogger("mcp_zero_test")


class ResourceMonitor:
    """Monitors system resource usage during test execution."""
    
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.rpc_process = None
        self.start_time = time.time()
        self.resource_log = []
        
    def set_rpc_process(self, pid):
        try:
            self.rpc_process = psutil.Process(pid)
        except psutil.NoSuchProcess:
            logger.error(f"No process found with PID {pid}")
            
    def sample_usage(self) -> Dict[str, Any]:
        """Sample the current resource usage."""
        cpu_percent = self.process.cpu_percent(interval=0.1)
        memory_info = self.process.memory_info()
        memory_mb = memory_info.rss / (1024 * 1024)  # Convert to MB
        
        rpc_cpu = 0
        rpc_memory_mb = 0
        
        if self.rpc_process:
            try:
                rpc_cpu = self.rpc_process.cpu_percent(interval=0.1)
                rpc_memory_mb = self.rpc_process.memory_info().rss / (1024 * 1024)
            except (psutil.NoSuchProcess, psutil.AccessDenied):
                logger.warning("Could not access RPC process metrics")
        
        sample = {
            "timestamp": datetime.now().isoformat(),
            "elapsed_seconds": time.time() - self.start_time,
            "sdk_cpu_percent": cpu_percent,
            "sdk_memory_mb": memory_mb,
            "rpc_cpu_percent": rpc_cpu,
            "rpc_memory_mb": rpc_memory_mb,
            "total_cpu_percent": cpu_percent + rpc_cpu,
            "total_memory_mb": memory_mb + rpc_memory_mb
        }
        
        self.resource_log.append(sample)
        return sample
    
    def get_summary(self) -> Dict[str, Any]:
        """Get summary statistics of resource usage."""
        if not self.resource_log:
            return {"error": "No resource data collected"}
        
        cpu_values = [entry["total_cpu_percent"] for entry in self.resource_log]
        memory_values = [entry["total_memory_mb"] for entry in self.resource_log]
        
        return {
            "samples": len(self.resource_log),
            "duration_seconds": time.time() - self.start_time,
            "cpu_percent": {
                "min": min(cpu_values),
                "max": max(cpu_values),
                "avg": sum(cpu_values) / len(cpu_values)
            },
            "memory_mb": {
                "min": min(memory_values),
                "max": max(memory_values),
                "avg": sum(memory_values) / len(memory_values)
            },
            "within_constraints": max(cpu_values) < 27.0 and max(memory_values) < 827.0
        }
    
    def save_report(self, filename: str):
        """Save resource monitoring report to a file."""
        summary = self.get_summary()
        
        with open(filename, 'w') as f:
            json.dump({
                "summary": summary,
                "detailed_log": self.resource_log
            }, f, indent=2)
            
        logger.info(f"Resource monitoring report saved to {filename}")
        
        # Also log summary to console
        logger.info(f"Resource Usage Summary:")
        logger.info(f"  CPU: {summary['cpu_percent']['avg']:.2f}% avg, {summary['cpu_percent']['max']:.2f}% peak")
        logger.info(f"  RAM: {summary['memory_mb']['avg']:.2f}MB avg, {summary['memory_mb']['max']:.2f}MB peak")
        logger.info(f"  Within constraints: {summary['within_constraints']}")


def find_rpc_server_pid() -> Optional[int]:
    """Find the PID of the running MCP RPC server process."""
    for proc in psutil.process_iter(['pid', 'name', 'cmdline']):
        try:
            cmdline = proc.info['cmdline']
            if cmdline and len(cmdline) > 0:
                cmd = " ".join(cmdline)
                if 'mcp-server' in cmd:
                    return proc.info['pid']
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            pass
    return None


def run_agent_lifecycle_test():
    """Run the complete agent lifecycle test."""
    monitor = ResourceMonitor()
    
    # Find running RPC server process
    rpc_pid = find_rpc_server_pid()
    if rpc_pid:
        logger.info(f"Found RPC server process with PID {rpc_pid}")
        monitor.set_rpc_process(rpc_pid)
    else:
        logger.warning("RPC server process not found. Only SDK resource usage will be monitored.")
    
    # Start MCP Client
    logger.info("Initializing MCP-ZERO client...")
    client = MCPClient()
    
    try:
        # Connect to the server
        sample = monitor.sample_usage()
        logger.info(f"Connecting to MCP-ZERO server (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        client.connect()
        
        # Create agent configuration
        config = AgentConfig(
            name="test_real_world_agent", 
            entry_plugin="core",  # Use 'core' as the default entry plugin
            intents=["greet", "calculate", "summarize"],
            metadata={
                "description": "Test agent for MCP-ZERO integration",
                "version": "1.0.0",
                "author": "MCP-ZERO Team"
            }
        )
        
        # Spawn an agent
        sample = monitor.sample_usage()
        logger.info(f"Spawning agent (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        agent = client.spawn_agent(config)
        logger.info(f"Agent spawned with ID: {agent.id}")
        
        # Attach plugins to the agent
        sample = monitor.sample_usage()
        logger.info(f"Attaching plugins (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        
        # Attach greeting plugin
        logger.info("Attaching greeting plugin...")
        result = agent.attach_plugin("greeting-plugin")
        logger.info(f"Plugin attachment result: {result}")
        monitor.sample_usage()
        
        # Attach calculator plugin
        logger.info("Attaching calculator plugin...")
        result = agent.attach_plugin("calculator-plugin")
        logger.info(f"Plugin attachment result: {result}")
        monitor.sample_usage()
        
        # Execute intents
        sample = monitor.sample_usage()
        logger.info(f"Executing intents (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        
        # Execute greeting intent
        logger.info("Executing 'greet' intent...")
        result = agent.execute("greet", {"name": "User"})
        logger.info(f"Greet result: {result}")
        monitor.sample_usage()
        
        # Execute calculation intent
        logger.info("Executing 'calculate' intent...")
        result = agent.execute("calculate", {"operation": "add", "a": "5", "b": "3"})
        logger.info(f"Calculate result: {result}")
        monitor.sample_usage()
        
        # Take snapshot
        sample = monitor.sample_usage()
        logger.info(f"Creating snapshot (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        snapshot_id = agent.snapshot()
        logger.info(f"Snapshot created with ID: {snapshot_id}")
        
        # Simulate some state change
        logger.info("Executing another intent to change agent state...")
        result = agent.execute("calculate", {"operation": "multiply", "a": "7", "b": "6"})
        logger.info(f"Calculate result: {result}")
        monitor.sample_usage()
        
        # Recover from snapshot
        sample = monitor.sample_usage()
        logger.info(f"Recovering from snapshot (CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB)")
        recovery_result = agent.recover(snapshot_id)
        logger.info(f"Recovery result: {recovery_result}")
        monitor.sample_usage()
        
        # List all agents 
        logger.info("Listing all agents...")
        agents = client.list_agents()
        logger.info(f"Found {len(agents)} agents")
        
        # Final resource check
        sample = monitor.sample_usage()
        logger.info(f"Final resource usage: CPU: {sample['total_cpu_percent']:.2f}%, RAM: {sample['total_memory_mb']:.2f}MB")
        
    finally:
        # Disconnect client
        logger.info("Disconnecting from MCP-ZERO server...")
        client.disconnect()
        
        # Generate resource usage report
        monitor.save_report("mcp_zero_resource_usage.json")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="MCP-ZERO Real-World Agent Test")
    args = parser.parse_args()
    
    try:
        run_agent_lifecycle_test()
        logger.info("✅ Real-world agent test completed successfully!")
    except Exception as e:
        logger.error(f"❌ Test failed: {str(e)}", exc_info=True)
