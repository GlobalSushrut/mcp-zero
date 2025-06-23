"""
Example: Autonomous Agent with Offline-First Resilience
Application Category: AI Agent Platforms
"""

import os
import json
import time
from typing import Dict, List, Optional, Any
from enum import Enum

# Import MCP Zero components
from mcp_zero.agent.core import AgentCore
from mcp_zero.memory.offline_memory import OfflineMemoryStore
from mcp_zero.reasoning.local_reasoning import LocalReasoner
from mcp_zero.reasoning.llm_reasoning import LLMReasoner


class AgentMode(Enum):
    """Operating modes for the agent."""
    OFFLINE = "offline"
    ONLINE = "online"


class AutonomousAgent:
    """
    Autonomous agent with offline-first resilience pattern.
    Can operate entirely offline with local reasoning.
    """
    
    def __init__(
        self,
        agent_name: str,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None,
        local_storage_path: str = "./agent_data"
    ):
        # Start in offline mode by default (offline-first principle)
        self.mode = AgentMode.OFFLINE
        self.agent_name = agent_name
        
        # Initialize offline-capable components
        self.agent_core = AgentCore(agent_name=agent_name)
        self.memory = OfflineMemoryStore(storage_path=local_storage_path)
        
        # Initialize both reasoning engines
        self.local_reasoner = LocalReasoner()
        self.llm_reasoner = LLMReasoner(
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        
        # Attempt to connect once if API key is provided
        if api_key:
            self._try_connect_once()
    
    def _try_connect_once(self) -> None:
        """
        Try to connect to the LLM service exactly once.
        If successful, switch to online mode.
        If not, remain in offline mode permanently.
        """
        try:
            # Quick connection attempt with short timeout
            result = self.llm_reasoner.test_connection(timeout_seconds=2)
            if result:
                self.mode = AgentMode.ONLINE
                self.memory.log("Connected to LLM service, operating in enhanced mode")
            else:
                self.memory.log("LLM service unavailable, operating in local mode")
        except Exception as e:
            self.memory.log(f"Connection error: {str(e)}. Operating in local mode.")
            # No retry - remain in offline mode permanently
    
    def process_task(self, task: str) -> Dict[str, Any]:
        """
        Process a task with offline resilience.
        Uses enhanced reasoning if online, otherwise uses local reasoning.
        """
        start_time = time.time()
        
        # Record the task in memory
        self.memory.add_task(task)
        
        # Process based on current mode
        if self.mode == AgentMode.ONLINE:
            try:
                # Try online processing
                result = self.llm_reasoner.process(task)
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = AgentMode.OFFLINE
                self.memory.log(f"Online processing failed: {str(e)}. " 
                              f"Switching permanently to local processing.")
                # Continue with offline processing
                result = self.local_reasoner.process(task)
        else:
            # Use offline processing
            result = self.local_reasoner.process(task)
        
        # Record processing time and result
        processing_time = time.time() - start_time
        self.memory.add_result(task, result, processing_time)
        
        # Return result with mode information
        return {
            "result": result,
            "mode": self.mode.value,
            "processing_time": processing_time
        }
    
    def get_memory(self) -> List[Dict]:
        """Retrieve agent memory history."""
        return self.memory.get_history()


# Example usage
if __name__ == "__main__":
    # Create agent with offline-first resilience
    agent = AutonomousAgent(
        agent_name="TaskAssistant", 
        api_key=os.environ.get("LLM_API_KEY"),
        api_endpoint=os.environ.get("LLM_API_ENDPOINT"),
        local_storage_path="./task_assistant_data"
    )
    
    # Agent works regardless of connectivity
    result = agent.process_task("Summarize the quarterly sales data")
    print(f"Task processed in {result['mode']} mode")
    print(f"Result: {result['result']}")
    
    # Agent maintains state offline
    memory = agent.get_memory()
    print(f"Agent memory entries: {len(memory)}")
