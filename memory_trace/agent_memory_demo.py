#!/usr/bin/env python3
"""
MCP-ZERO Agent Memory Tree Demo
Demonstrates how agents can maintain memory traces with ZK-traceable auditing

This demo shows:
1. Creating an agent with memory tree storage
2. Building a memory tree of reasoning steps
3. Registration with MCP-ZERO RPC server
4. Verification of memory trace integrity
"""

import os
import sys
import uuid
import time
import json
import random
import logging
import argparse
import requests
from typing import Dict, List, Any, Optional

# Add parent directory to path to import our modules
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_trace.db.memory_tree import DBMemoryTree, MemoryNode
from sdk.mcp_zero.agent import Agent
from sdk.mcp_zero.monitoring import ResourceMonitor

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("AgentMemoryDemo")

class MemoryTraceAgent:
    """Agent demonstration with memory tree tracing"""
    
    def __init__(self, db_path: str, rpc_url: str):
        """Initialize agent with memory tree"""
        self.agent_id = f"memory-agent-{uuid.uuid4()}"
        self.memory_tree = DBMemoryTree(db_path=db_path, rpc_url=rpc_url)
        self.resource_monitor = ResourceMonitor()
        self.resource_monitor.start_monitoring()
        logger.info(f"Initialized MemoryTraceAgent with ID: {self.agent_id}")
    
    def record_observation(self, content: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record an observation in the memory tree"""
        if metadata is None:
            metadata = {}
            
        # Add resource usage information to metadata
        if self.resource_monitor:
            cpu, ram = self.resource_monitor.get_current_usage()
            metadata["resource_usage"] = {
                "cpu_percent": cpu,
                "memory_mb": ram / (1024 * 1024)
            }
            
            # Check if within MCP-ZERO constraints
            metadata["within_constraints"] = (cpu < 27.0 and ram < 827 * 1024 * 1024)
        
        # Record timestamp
        metadata["timestamp"] = time.time()
        
        return self.memory_tree.add_memory(
            agent_id=self.agent_id,
            content=content,
            node_type="observation",
            metadata=metadata
        )
    
    def record_reasoning(self, content: str, parent_id: str, 
                        confidence: float, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record a reasoning step in the memory tree"""
        if metadata is None:
            metadata = {}
            
        metadata["confidence"] = confidence
        
        # Add resource usage information
        if self.resource_monitor:
            cpu, ram = self.resource_monitor.get_current_usage()
            metadata["resource_usage"] = {
                "cpu_percent": cpu,
                "memory_mb": ram / (1024 * 1024)
            }
        
        return self.memory_tree.add_memory(
            agent_id=self.agent_id,
            content=content,
            node_type="reasoning",
            metadata=metadata,
            parent_id=parent_id
        )
    
    def record_action(self, content: str, parent_id: str, 
                     action_type: str, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record an action in the memory tree"""
        if metadata is None:
            metadata = {}
            
        metadata["action_type"] = action_type
        
        # Add resource usage information
        if self.resource_monitor:
            cpu, ram = self.resource_monitor.get_current_usage()
            metadata["resource_usage"] = {
                "cpu_percent": cpu,
                "memory_mb": ram / (1024 * 1024)
            }
        
        return self.memory_tree.add_memory(
            agent_id=self.agent_id,
            content=content,
            node_type="action",
            metadata=metadata,
            parent_id=parent_id
        )
    
    def record_conclusion(self, content: str, parent_id: str,
                         confidence: float, metadata: Optional[Dict[str, Any]] = None) -> str:
        """Record a conclusion in the memory tree"""
        if metadata is None:
            metadata = {}
            
        metadata["confidence"] = confidence
        
        # Add resource usage information
        if self.resource_monitor:
            cpu, ram = self.resource_monitor.get_current_usage()
            metadata["resource_usage"] = {
                "cpu_percent": cpu,
                "memory_mb": ram / (1024 * 1024)
            }
        
        return self.memory_tree.add_memory(
            agent_id=self.agent_id,
            content=content,
            node_type="conclusion",
            metadata=metadata,
            parent_id=parent_id
        )
    
    def simulate_creative_task(self) -> str:
        """Simulate a creative writing task with memory tracing"""
        logger.info("Starting creative task simulation...")
        
        # Initial observation
        observation_id = self.record_observation(
            "Received request to create a short story about AI and humanity's partnership",
            metadata={
                "request_type": "creative_writing",
                "domain": "science_fiction"
            }
        )
        logger.info(f"Recorded initial observation: {observation_id}")
        
        # Planning reasoning
        planning_id = self.record_reasoning(
            "Need to structure a narrative with beginning, middle, and end. Should focus on "
            "collaborative relationship between AI and humans rather than conflict.",
            parent_id=observation_id,
            confidence=0.85,
            metadata={
                "themes": ["collaboration", "future", "technology"]
            }
        )
        logger.info(f"Recorded planning reasoning: {planning_id}")
        
        # Character development
        characters_id = self.record_reasoning(
            "Story will feature a human scientist working with an AI research assistant "
            "to solve a global crisis that neither could solve alone.",
            parent_id=planning_id,
            confidence=0.78,
            metadata={
                "characters": ["Dr. Elena Chen", "AURA-7 AI System"]
            }
        )
        logger.info(f"Recorded character development: {characters_id}")
        
        # Plot development actions
        act1_id = self.record_action(
            "Writing Act 1: Introduction of Dr. Chen and AURA-7, establishing the global crisis "
            "(climate instability causing unpredictable weather patterns).",
            parent_id=characters_id,
            action_type="writing_act1",
            metadata={
                "word_count": 250,
                "scene": "research_lab"
            }
        )
        logger.info(f"Recorded Act 1 writing: {act1_id}")
        
        act2_id = self.record_action(
            "Writing Act 2: Dr. Chen and AURA-7 encounter obstacles in their research. "
            "AURA-7 processes vast climate datasets while Dr. Chen provides creative intuition "
            "that algorithms miss.",
            parent_id=act1_id,
            action_type="writing_act2",
            metadata={
                "word_count": 350,
                "scene": "data_center"
            }
        )
        logger.info(f"Recorded Act 2 writing: {act2_id}")
        
        act3_id = self.record_action(
            "Writing Act 3: Breakthrough moment where AURA-7's pattern recognition "
            "combines with Dr. Chen's theoretical framework to create a solution. "
            "Implementation of their solution begins, showing early promise.",
            parent_id=act2_id,
            action_type="writing_act3",
            metadata={
                "word_count": 400,
                "scene": "crisis_control_center"
            }
        )
        logger.info(f"Recorded Act 3 writing: {act3_id}")
        
        # Story conclusion
        conclusion_id = self.record_conclusion(
            "Completed short story 'Patterns in the Storm' showcasing how "
            "AI and human strengths complement each other to solve a complex crisis "
            "that neither could have solved alone. The story emphasizes partnership "
            "rather than competition between humanity and technology.",
            parent_id=act3_id,
            confidence=0.92,
            metadata={
                "title": "Patterns in the Storm",
                "total_word_count": 1050,
                "themes": ["collaboration", "complementary strengths", "optimistic future"]
            }
        )
        logger.info(f"Recorded conclusion: {conclusion_id}")
        
        # Memory trace verification
        memory_path = self.memory_tree.get_memory_path(conclusion_id)
        is_valid = self.memory_tree.verify_memory_trace(memory_path)
        logger.info(f"Memory trace verification: {'Valid' if is_valid else 'Invalid'}")
        
        # Display memory path
        logger.info(f"Memory trace path length: {len(memory_path)}")
        logger.info("Memory trace path:")
        for i, node in enumerate(memory_path):
            logger.info(f"  {i}: {node['node_type']} - {node['content'][:50]}...")
        
        # Return the final conclusion ID
        return conclusion_id
    
    def simulate_reasoning_task(self) -> str:
        """Simulate a logical reasoning task with memory tracing"""
        logger.info("Starting reasoning task simulation...")
        
        # Initial observation
        observation_id = self.record_observation(
            "Analyzing data on renewable energy adoption rates across different regions",
            metadata={
                "data_source": "global_energy_statistics",
                "regions": ["North America", "Europe", "Asia", "Africa", "South America"]
            }
        )
        logger.info(f"Recorded initial observation: {observation_id}")
        
        # Data analysis steps
        analysis_id = self.record_reasoning(
            "Initial data shows varying adoption rates, with Europe leading in wind and solar, "
            "while North America has higher hydroelectric usage proportionally.",
            parent_id=observation_id,
            confidence=0.89,
            metadata={
                "data_points": 1250,
                "timeframe": "2020-2025"
            }
        )
        logger.info(f"Recorded data analysis: {analysis_id}")
        
        # Factor identification
        factors_id = self.record_reasoning(
            "Primary factors affecting adoption appear to be: government policy incentives, "
            "geographical advantages, existing infrastructure, and industrial composition.",
            parent_id=analysis_id,
            confidence=0.76,
            metadata={
                "factors": ["policy", "geography", "infrastructure", "industry"]
            }
        )
        logger.info(f"Recorded factor identification: {factors_id}")
        
        # Regional analysis actions
        for i, region in enumerate(["Europe", "North America", "Asia"]):
            region_id = self.record_action(
                f"Detailed analysis of {region}'s renewable adoption patterns, focusing "
                f"on policy frameworks and geographical constraints.",
                parent_id=factors_id,
                action_type="regional_analysis",
                metadata={
                    "region": region,
                    "data_points": 350 + i * 75,
                }
            )
            logger.info(f"Recorded {region} analysis: {region_id}")
            
            # Update parent for next iteration
            factors_id = region_id
        
        # Predictive modeling
        model_id = self.record_action(
            "Developing predictive model of adoption rates based on identified factors, "
            "with weighted coefficients for policy impact (0.4), geographical suitability (0.3), "
            "existing infrastructure (0.2), and industrial composition (0.1).",
            parent_id=factors_id,
            action_type="predictive_modeling",
            metadata={
                "model_type": "weighted_multivariate_regression",
                "accuracy": 0.83,
            }
        )
        logger.info(f"Recorded predictive modeling: {model_id}")
        
        # Final conclusions
        conclusion_id = self.record_conclusion(
            "Analysis reveals policy incentives have the strongest correlation with adoption rates, "
            "explaining approximately 40% of variation between regions. Geographical factors "
            "account for 30%, suggesting natural advantages are significant but can be "
            "offset by strong policy frameworks. Recommendation: focus international "
            "development efforts on policy alignment and knowledge transfer.",
            parent_id=model_id,
            confidence=0.91,
            metadata={
                "key_finding": "policy_dominance",
                "recommendation": "focus_on_policy_alignment",
                "confidence_interval": "87-94%"
            }
        )
        logger.info(f"Recorded conclusion: {conclusion_id}")
        
        # Return the final conclusion ID
        return conclusion_id

    def cleanup(self):
        """Clean up resources"""
        if self.resource_monitor:
            self.resource_monitor.stop_monitoring()
        
        # Close memory tree database
        self.memory_tree.close()


def verify_rpc_connection(rpc_url: str) -> bool:
    """Verify connection to MCP-ZERO RPC server"""
    try:
        response = requests.get(f"{rpc_url}/api/v1/health", timeout=5)
        return response.status_code == 200
    except Exception as e:
        logger.error(f"Failed to connect to RPC server: {e}")
        return False


def run_demo(db_path: str, rpc_url: str):
    """Run the agent memory trace demo"""
    # First check if we can connect to the RPC server
    logger.info(f"Checking connection to MCP-ZERO RPC server at {rpc_url}...")
    if not verify_rpc_connection(rpc_url):
        logger.warning(f"Could not connect to RPC server at {rpc_url}. Running in local-only mode.")
    else:
        logger.info("Successfully connected to MCP-ZERO RPC server.")
    
    # Create and run the agent
    agent = MemoryTraceAgent(db_path=db_path, rpc_url=rpc_url)
    
    try:
        # Simulate the creative task
        creative_conclusion_id = agent.simulate_creative_task()
        logger.info(f"Creative task completed with conclusion: {creative_conclusion_id}")
        
        # Simulate the reasoning task
        reasoning_conclusion_id = agent.simulate_reasoning_task()
        logger.info(f"Reasoning task completed with conclusion: {reasoning_conclusion_id}")
        
        # Get all memory nodes for the agent
        all_memories = agent.memory_tree.get_agent_memories(agent.agent_id)
        logger.info(f"Total memories created for agent: {len(all_memories)}")
        
        # Report memory types
        memory_types = {}
        for mem in all_memories:
            node_type = mem['node_type']
            memory_types[node_type] = memory_types.get(node_type, 0) + 1
        
        logger.info("Memory type distribution:")
        for mem_type, count in memory_types.items():
            logger.info(f"  - {mem_type}: {count}")
        
        # Report final resource usage
        if agent.resource_monitor:
            cpu, ram = agent.resource_monitor.get_current_usage()
            ram_mb = ram / (1024 * 1024)
            logger.info(f"Final resource usage: {cpu:.2f}% CPU, {ram_mb:.2f}MB RAM")
            
            # Check if within MCP-ZERO constraints
            within_constraints = (cpu < 27.0 and ram_mb < 827)
            logger.info(f"Within MCP-ZERO constraints: {within_constraints}")
        
        logger.info("Agent memory trace demo completed successfully!")
        
    finally:
        # Clean up resources
        agent.cleanup()


def main():
    """Main function to run the agent memory demo"""
    parser = argparse.ArgumentParser(description="MCP-ZERO Agent Memory Tree Demo")
    parser.add_argument("--db", default="agent_memory.db", help="Path to SQLite database file")
    parser.add_argument("--rpc", default="http://localhost:8081", help="MCP-ZERO RPC server URL")
    parser.add_argument("--delete", action="store_true", help="Delete existing database before testing")
    
    args = parser.parse_args()
    
    # Delete existing database file if requested
    if args.delete and os.path.exists(args.db):
        logger.info(f"Deleting existing database file: {args.db}")
        os.remove(args.db)
    
    run_demo(db_path=args.db, rpc_url=args.rpc)


if __name__ == "__main__":
    main()
