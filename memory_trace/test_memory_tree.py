#!/usr/bin/env python3
"""
Memory Tree Trace Test Script
Tests the database-backed memory tree for agent memory tracking
"""

import os
import sys
import time
import uuid
import logging
import argparse
from typing import Dict, List, Any

# Add parent directory to path to import our module
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from memory_trace.db.memory_tree import DBMemoryTree, MemoryNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[logging.StreamHandler()]
)
logger = logging.getLogger("MemoryTreeTest")

def create_agent_memory_tree(db_path: str = "agent_memory.db") -> None:
    """Create and test an agent memory tree with multiple nodes"""
    
    logger.info("Initializing DB Memory Tree...")
    tree = DBMemoryTree(db_path=db_path)
    
    # Create a test agent ID
    agent_id = f"test-agent-{uuid.uuid4()}"
    logger.info(f"Testing with agent ID: {agent_id}")
    
    # Create root memory - initial observation
    logger.info("Creating root memory node...")
    root_id = tree.add_memory(
        agent_id=agent_id,
        content="Initial observation of the environment",
        node_type="observation",
        metadata={
            "environment": "test-env",
            "timestamp": time.time(),
            "resource_usage": {"cpu": 0.05, "memory": 120}
        }
    )
    logger.info(f"Created root memory node: {root_id}")
    
    # Create child memory - reasoning step
    logger.info("Creating reasoning memory node...")
    reasoning_id = tree.add_memory(
        agent_id=agent_id,
        content="Based on the environment, I should explore the available options",
        node_type="reasoning",
        metadata={
            "confidence": 0.85,
            "resource_usage": {"cpu": 0.08, "memory": 145}
        },
        parent_id=root_id
    )
    logger.info(f"Created reasoning memory node: {reasoning_id}")
    
    # Create multiple action memories
    actions = [
        "Query the database for available information",
        "Analyze the information for patterns",
        "Generate a hypothesis based on patterns"
    ]
    
    action_ids = []
    for i, action in enumerate(actions):
        logger.info(f"Creating action memory node {i+1}...")
        action_id = tree.add_memory(
            agent_id=agent_id,
            content=action,
            node_type="action",
            metadata={
                "action_type": "information_processing",
                "step": i+1,
                "resource_usage": {"cpu": 0.12, "memory": 156}
            },
            parent_id=reasoning_id
        )
        action_ids.append(action_id)
        logger.info(f"Created action memory node: {action_id}")
    
    # Create a conclusion memory
    logger.info("Creating conclusion memory node...")
    conclusion_id = tree.add_memory(
        agent_id=agent_id,
        content="The analysis reveals a correlation between X and Y factors",
        node_type="conclusion",
        metadata={
            "confidence": 0.92,
            "factors": ["X", "Y", "Z"],
            "resource_usage": {"cpu": 0.15, "memory": 178}
        },
        parent_id=action_ids[-1]
    )
    logger.info(f"Created conclusion memory node: {conclusion_id}")
    
    # Test retrieval of memories
    logger.info("\nTesting memory retrieval:")
    
    # Get memory path from root to conclusion
    memory_path = tree.get_memory_path(conclusion_id)
    logger.info(f"Memory path length: {len(memory_path)}")
    
    logger.info("\nMemory trace path:")
    for i, node in enumerate(memory_path):
        logger.info(f"Level {i}: {node['node_type']} - {node['content'][:50]}...")
    
    # Verify memory trace integrity
    is_valid = tree.verify_memory_trace(memory_path)
    logger.info(f"Memory trace verification: {'Valid' if is_valid else 'Invalid'}")
    
    # Test memory search
    search_results = tree.search_memories("correlation")
    logger.info(f"\nSearch for 'correlation' found {len(search_results)} results")
    
    # Test getting all memories for agent
    all_memories = tree.get_agent_memories(agent_id)
    logger.info(f"Total memories for agent: {len(all_memories)}")
    
    # Show agent memory types
    memory_types = {}
    for mem in all_memories:
        node_type = mem['node_type']
        memory_types[node_type] = memory_types.get(node_type, 0) + 1
    
    logger.info("Memory type distribution:")
    for mem_type, count in memory_types.items():
        logger.info(f"  - {mem_type}: {count}")
        
    logger.info("\nMemory tree test completed successfully!")

def main():
    """Main function to run the memory tree test"""
    parser = argparse.ArgumentParser(description="Test the MCP-ZERO Memory Tree")
    parser.add_argument("--db", default="agent_memory.db", help="Path to SQLite database file")
    parser.add_argument("--delete", action="store_true", help="Delete existing database before testing")
    
    args = parser.parse_args()
    
    # Delete existing database file if requested
    if args.delete and os.path.exists(args.db):
        logger.info(f"Deleting existing database file: {args.db}")
        os.remove(args.db)
    
    create_agent_memory_tree(db_path=args.db)

if __name__ == "__main__":
    main()
