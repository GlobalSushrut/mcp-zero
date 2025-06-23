#!/usr/bin/env python3
"""
PARE Chain Protocol - Core implementation

Provides the foundation for block-chain based agent training with:
- Block-child training hierarchies
- Hash-chained memory traces
- Consensus verification
- Integration with MCP-ZERO memory tree DB

Hardware constraints enforced: <27% CPU, <827MB RAM
"""

import os
import time
import json
import uuid
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple

# Import MCP-ZERO memory tree components
from memory_trace.db.memory_tree import DBMemoryTree, MemoryNode

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger("PAREProtocol")


class PAREChainProtocol:
    """
    Protocol for Agent Retrograde Evolution (PARE) Network Chain
    
    Implements block-child binary training with agent node hash chains
    that support retrograde learning with factorial voting consensus.
    """
    
    def __init__(self, db_path: str, rpc_url: str = "http://localhost:8081"):
        """
        Initialize PARE Chain Protocol
        
        Args:
            db_path: Path to the SQLite database for memory storage
            rpc_url: URL for the MCP-ZERO RPC server
        """
        self.protocol_id = str(uuid.uuid4())
        self.memory_tree = DBMemoryTree(db_path=db_path, rpc_url=rpc_url)
        self.active_blocks = {}  # Map of block_id -> TrainingBlock
        self.child_relationships = {}  # Map of parent_id -> List[child_id]
        self.block_root_hash = None
        logger.info(f"Initialized PARE Chain Protocol with ID: {self.protocol_id}")
    
    def create_training_block(self, 
                             agent_id: str, 
                             block_type: str, 
                             metadata: Dict[str, Any] = None) -> str:
        """
        Create a new training block in the chain
        
        Args:
            agent_id: ID of the agent associated with this block
            block_type: Type of training block (e.g., "perception", "reasoning", "action")
            metadata: Additional metadata for the block
            
        Returns:
            block_id: ID of the created block
        """
        if metadata is None:
            metadata = {}
            
        # Add timestamp and protocol ID to metadata
        metadata["timestamp"] = time.time()
        metadata["protocol_id"] = self.protocol_id
        
        # Create block in memory tree
        block_id = self.memory_tree.add_memory(
            agent_id=agent_id,
            content=f"PARE Training Block: {block_type}",
            node_type=f"training_block_{block_type}",
            metadata=metadata
        )
        
        # If this is the first block, set it as the root
        if self.block_root_hash is None:
            self.block_root_hash = self.memory_tree.get_memory(block_id)["hash"]
            
        return block_id
    
    def add_child_block(self, 
                       parent_id: str, 
                       agent_id: str, 
                       block_type: str,
                       metadata: Dict[str, Any] = None) -> str:
        """
        Add a child block connected to a parent block
        
        Args:
            parent_id: ID of the parent block
            agent_id: ID of the agent associated with this block
            block_type: Type of training block
            metadata: Additional metadata for the block
            
        Returns:
            block_id: ID of the created child block
        """
        if metadata is None:
            metadata = {}
            
        # Get parent block hash
        parent_block = self.memory_tree.get_memory(parent_id)
        if parent_block is None:
            raise ValueError(f"Parent block {parent_id} not found")
            
        # Add parent hash to metadata for chain verification
        metadata["parent_hash"] = parent_block["hash"]
        metadata["parent_id"] = parent_id
        
        # Create child block in memory tree
        block_id = self.memory_tree.add_memory(
            agent_id=agent_id,
            content=f"PARE Child Block: {block_type}",
            node_type=f"child_block_{block_type}",
            metadata=metadata,
            parent_id=parent_id
        )
        
        # Track child relationship
        if parent_id not in self.child_relationships:
            self.child_relationships[parent_id] = []
        self.child_relationships[parent_id].append(block_id)
        
        return block_id
    
    def add_training_data(self, 
                         block_id: str, 
                         data_content: str,
                         data_type: str,
                         metadata: Dict[str, Any] = None) -> str:
        """
        Add training data to a block
        
        Args:
            block_id: ID of the block to add data to
            data_content: Content of the training data
            data_type: Type of training data
            metadata: Additional metadata for the data
            
        Returns:
            data_id: ID of the created data node
        """
        if metadata is None:
            metadata = {}
            
        # Add timestamp and data type to metadata
        metadata["timestamp"] = time.time()
        metadata["data_type"] = data_type
        
        # Create data node in memory tree
        data_id = self.memory_tree.add_memory(
            agent_id=self.protocol_id,  # Use protocol ID as agent ID for data nodes
            content=data_content,
            node_type=f"training_data_{data_type}",
            metadata=metadata,
            parent_id=block_id
        )
        
        return data_id
    
    def add_llm_call(self, 
                    block_id: str, 
                    prompt: str, 
                    result: str,
                    metadata: Dict[str, Any] = None) -> str:
        """
        Record an LLM call associated with a training block
        
        Args:
            block_id: ID of the block associated with the LLM call
            prompt: The prompt sent to the LLM
            result: The result received from the LLM
            metadata: Additional metadata for the LLM call
            
        Returns:
            llm_id: ID of the created LLM call node
        """
        if metadata is None:
            metadata = {}
            
        # Add timestamp and LLM call details to metadata
        metadata["timestamp"] = time.time()
        metadata["prompt_length"] = len(prompt)
        metadata["result_length"] = len(result)
        
        # Create content with truncated prompt and result
        content = f"LLM Call - Prompt: {prompt[:100]}... Result: {result[:100]}..."
        
        # Create LLM call node in memory tree
        llm_id = self.memory_tree.add_memory(
            agent_id=self.protocol_id,
            content=content,
            node_type="llm_call",
            metadata=metadata,
            parent_id=block_id
        )
        
        # Store full prompt and result as separate nodes with LLM call as parent
        prompt_id = self.memory_tree.add_memory(
            agent_id=self.protocol_id,
            content=prompt,
            node_type="llm_prompt",
            metadata={"timestamp": time.time()},
            parent_id=llm_id
        )
        
        result_id = self.memory_tree.add_memory(
            agent_id=self.protocol_id,
            content=result,
            node_type="llm_result",
            metadata={"timestamp": time.time()},
            parent_id=llm_id
        )
        
        return llm_id
    
    def register_consensus_report(self,
                                block_id: str,
                                report_content: str,
                                votes: List[Dict[str, Any]],
                                metadata: Dict[str, Any] = None) -> str:
        """
        Register a consensus report for a training block
        
        Args:
            block_id: ID of the block the consensus is for
            report_content: Content of the consensus report
            votes: List of votes from participating agents
            metadata: Additional metadata for the report
            
        Returns:
            report_id: ID of the created consensus report node
        """
        if metadata is None:
            metadata = {}
            
        # Add timestamp and voting information to metadata
        metadata["timestamp"] = time.time()
        metadata["vote_count"] = len(votes)
        metadata["votes"] = votes
        
        # Create consensus report node in memory tree
        report_id = self.memory_tree.add_memory(
            agent_id=self.protocol_id,
            content=report_content,
            node_type="consensus_report",
            metadata=metadata,
            parent_id=block_id
        )
        
        return report_id
    
    def verify_chain_integrity(self, block_id: str) -> Tuple[bool, List[Dict]]:
        """
        Verify the integrity of the block chain from a given block to the root
        
        Args:
            block_id: ID of the block to verify chain from
            
        Returns:
            (is_valid, path): Tuple of validity boolean and memory path
        """
        # Get memory path from block to root
        memory_path = self.memory_tree.get_memory_path(block_id)
        
        # Verify memory trace using memory tree's built-in verification
        is_valid = self.memory_tree.verify_memory_trace(memory_path)
        
        return is_valid, memory_path
    
    def get_training_blocks_for_agent(self, agent_id: str) -> List[Dict]:
        """
        Get all training blocks for a specific agent
        
        Args:
            agent_id: ID of the agent to get blocks for
            
        Returns:
            blocks: List of training blocks
        """
        # Get all agent memories
        all_memories = self.memory_tree.get_agent_memories(agent_id)
        
        # Filter for training blocks
        training_blocks = [
            mem for mem in all_memories 
            if mem["node_type"].startswith("training_block_") or
               mem["node_type"].startswith("child_block_")
        ]
        
        return training_blocks
    
    def search_training_data(self, query: str, max_results: int = 10) -> List[Dict]:
        """
        Search for training data matching a query
        
        Args:
            query: Search query string
            max_results: Maximum number of results to return
            
        Returns:
            results: List of matching memory nodes
        """
        # Search memory tree for matching content
        search_results = self.memory_tree.search_memories(query, max_results)
        
        # Filter for training data nodes
        training_data = [
            res for res in search_results 
            if res["node_type"].startswith("training_data_")
        ]
        
        return training_data
    
    def get_child_blocks(self, parent_id: str) -> List[Dict]:
        """
        Get all child blocks for a parent block
        
        Args:
            parent_id: ID of the parent block
            
        Returns:
            children: List of child blocks
        """
        # Get child IDs for parent
        child_ids = self.child_relationships.get(parent_id, [])
        
        # Get child blocks
        children = [
            self.memory_tree.get_memory(child_id)
            for child_id in child_ids
        ]
        
        # Filter out None values (in case a child was deleted)
        return [child for child in children if child is not None]
    
    def close(self):
        """Close all resources"""
        self.memory_tree.close()
