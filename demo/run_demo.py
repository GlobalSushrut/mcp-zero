#!/usr/bin/env python3
"""
MCP-ZERO Concise Demo Runner

This script demonstrates the core features of MCP-ZERO infrastructure
using our IntelliAgent implementation.
"""
import os
import sys
import time
import json
import logging
import psutil
from datetime import datetime

# Add SDK to path
sys.path.append(os.path.join(os.path.dirname(__file__), "..", "src", "sdk", "python"))

# Import MCP-ZERO SDK
from mcp_zero import Agent, AgentConfig, HardwareConstraints
from mcp_zero.http_adapter import HttpAdapter

# Configure logging
logging.basicConfig(level=logging.INFO, format="%(asctime)s [%(levelname)s] %(message)s")
logger = logging.getLogger("mcp_zero.demo")

# Resource monitoring
class ResourceMonitor:
    def __init__(self):
        self.process = psutil.Process(os.getpid())
        self.start_time = time.time()
        self.metrics = []
        
    def measure(self, label):
        cpu = self.process.cpu_percent(interval=0.1)
        mem = self.process.memory_info().rss / (1024 * 1024)  # MB
        self.metrics.append({"label": label, "cpu": cpu, "mem_mb": mem})
        logger.info(f"[{label}] CPU: {cpu:.1f}%, Memory: {mem:.1f}MB")
        return cpu, mem

def main():
    # Initialize monitoring
    monitor = ResourceMonitor()
    
    # MCP-ZERO server connection
    mcp_host = os.environ.get("MCP_HOST", "localhost")
    mcp_port = int(os.environ.get("MCP_HTTP_PORT", "8081"))
    
    logger.info(f"Connecting to MCP-ZERO server at {mcp_host}:{mcp_port}")
    adapter = HttpAdapter(host=mcp_host, port=mcp_port)
    
    # Explicitly connect to the server
    try:
        adapter.connect()
    except Exception as e:
        logger.error(f"Failed to connect to MCP-ZERO server: {e}")
        return
    
    # Create agent config
    config = AgentConfig(
        name="intelliagent",
        entry_plugin="core_assistant",
        intents=["answer", "search", "analyze", "translate", "compute"],
        hm=HardwareConstraints(cpu_limit=25.0, memory_limit=800),  # Following MCP-ZERO v7 constraints (CPU <27%, RAM <827MB)
        metadata={"purpose": "demo", "created_at": datetime.now().isoformat()}
    )
    
    try:
        # List all available agents
        logger.info("Listing all available agents...")
        agents = adapter.list_agents(limit=100, offset=0)
        logger.info(f"Available agents: {len(agents)}")
        for i, agent_id in enumerate(agents):
            # The API returns agent IDs as strings, not dictionaries
            logger.info(f"  Agent {i+1}: {agent_id}")
        monitor.measure("list_agents")
        
        # 1. Spawn agent
        logger.info("Spawning agent...")
        agent_data = adapter.spawn_agent(config=config.to_dict())
        agent_id = agent_data.get("id")
        agent = Agent(adapter, agent_id)
        logger.info(f"Agent spawned with ID: {agent_id}")
        monitor.measure("agent_spawned")
        
        # 2. Attach plugins
        plugins = ["core_assistant", "knowledge_base", "calculator", "language_translator", "cryptography"]
        for plugin in plugins:
            # Using HttpAdapter directly since Agent might wrap differently
            success = adapter.attach_plugin(agent_id=agent_id, plugin_id=plugin)
            if success:
                logger.info(f"Plugin {plugin} attached successfully")
                monitor.measure(f"plugin_{plugin}_attached")
        
        # 3. Execute intents
        # Answer intent
        result = adapter.execute(agent_id, "answer", {"question": "What is MCP-ZERO?"})
        logger.info(f"Answer result: {json.dumps(result, indent=2)}")
        monitor.measure("answer_intent")
        # Take first snapshot
        logger.info("Taking snapshot after basic info...")
        snapshot_id = adapter.snapshot(agent_id)
        logger.info(f"Snapshot created with ID: {snapshot_id}")
        monitor.measure("snapshot_taken")
        
        # Calculator intent
        result = adapter.execute(agent_id, "compute", {"operation": "add", "a": "42", "b": "58"})
        logger.info(f"Calculation result: {json.dumps(result, indent=2)}")
        monitor.measure("calculator_intent")
        
        # Translation intent
        result = adapter.execute(agent_id, "translate", {
            "text": "Hello world",
            "source_language": "en",
            "target_language": "es"
        })
        logger.info(f"Translation result: {json.dumps(result, indent=2)}")
        monitor.measure("translate_intent")
        
        # Store knowledge
        kb_result = adapter.execute(agent_id, "store", {
            "content": "MCP-ZERO is a sustainable AI agent infrastructure.",
            "category": "technology"
        })
        kb_id = kb_result.get("result", {}).get("id", "")
        logger.info(f"Knowledge stored with ID: {kb_id}")
        monitor.measure("store_knowledge")
        # Recover from first snapshot
        logger.info(f"Recovering from first snapshot: {snapshot_id}")
        success = adapter.recover(agent_id, snapshot_id)
        if success:
            logger.info("Agent recovered from first snapshot")
            monitor.measure("recovered_from_first_snapshot")
        
        # 5. Execute post-recovery intent
        result = adapter.execute(agent_id, "search", {"query": "AI infrastructure"}) 
        logger.info(f"Post-recovery search: {json.dumps(result, indent=2)}") 
        monitor.measure("post_recovery_intent")
        
        # Summary
        peak_cpu = max(m["cpu"] for m in monitor.metrics)
        peak_mem = max(m["mem_mb"] for m in monitor.metrics)
        logger.info(f"Demo completed successfully")
        logger.info(f"Peak CPU: {peak_cpu:.1f}%, Peak Memory: {peak_mem:.1f}MB")
        
        # Save metrics
        with open("demo_metrics.json", "w") as f:
            json.dump({
                "metrics": monitor.metrics,
                "peak_cpu": peak_cpu,
                "peak_mem": peak_mem,
                "runtime_seconds": time.time() - monitor.start_time
            }, f, indent=2)
        
    except Exception as e:
        logger.error(f"Demo failed: {str(e)}")

if __name__ == "__main__":
    main()
