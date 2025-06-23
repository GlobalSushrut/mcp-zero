#!/usr/bin/env python3
"""
PARE Network Chain Protocol - Training Block Implementation
Supports hierarchical block-child training structure for agent learning
"""

import time
import uuid
import hashlib
import logging
from typing import Dict, List, Any, Optional, Tuple, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("TrainingBlock")

class TrainingBlock:
    """
    Training Block for the PARE Network Chain Protocol
    
    Represents a discrete unit of agent training with:
    - Unique block ID and hash for blockchain-like verification
    - Parent-child relationships for hierarchical learning
    - Support for multiple training iterations and checkpoints
    - Integration with memory tree for persistence
    """
    
    def __init__(self, 
                agent_id: str,
                block_type: str,
                parent_id: Optional[str] = None,
                parent_hash: Optional[str] = None,
                metadata: Optional[Dict[str, Any]] = None):
        """
        Initialize a new training block
        
        Args:
            agent_id: ID of the agent this block is associated with
            block_type: Type of training (perception, reasoning, action, etc.)
            parent_id: Optional ID of parent block (None for root blocks)
            parent_hash: Optional hash of parent block for verification
            metadata: Optional metadata for the block
        """
        self.block_id = str(uuid.uuid4())
        self.agent_id = agent_id
        self.block_type = block_type
        self.parent_id = parent_id
        self.parent_hash = parent_hash
        self.created_at = time.time()
        self.last_updated = self.created_at
        self.metadata = metadata or {}
        
        # Internal state for training
        self.children: Dict[str, "TrainingBlock"] = {}
        self.data_entries: List[Dict[str, Any]] = []
        self.llm_calls: List[Dict[str, Any]] = []
        self.consensus_reports: List[Dict[str, Any]] = []
        self.training_state = "initialized"
        
        # Calculate initial hash (will be updated as block content changes)
        self._calculate_block_hash()
        
        logger.info(f"Created {block_type} block {self.block_id[:8]} for agent {agent_id[:8]}")
    
    def _calculate_block_hash(self) -> str:
        """
        Calculate cryptographic hash of the block content
        
        Returns:
            Hash string of the block
        """
        # Combine core data
        hash_data = {
            "block_id": self.block_id,
            "agent_id": self.agent_id,
            "block_type": self.block_type,
            "parent_id": self.parent_id,
            "parent_hash": self.parent_hash,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "metadata": self.metadata,
            "training_state": self.training_state,
            "data_count": len(self.data_entries),
            "child_count": len(self.children),
            "llm_call_count": len(self.llm_calls),
            "consensus_count": len(self.consensus_reports),
        }
        
        # Calculate hash as in MCP-ZERO memory tree
        hash_string = hashlib.sha256(str(hash_data).encode()).hexdigest()
        self.block_hash = hash_string
        return hash_string
    
    def add_child_block(self,
                       agent_id: str,
                       block_type: str,
                       metadata: Optional[Dict[str, Any]] = None) -> "TrainingBlock":
        """
        Add a child training block to this block
        
        Args:
            agent_id: ID of the agent for the child block
            block_type: Type of training for the child block
            metadata: Optional metadata for the child block
            
        Returns:
            The created child block
        """
        # Create new child block
        child = TrainingBlock(
            agent_id=agent_id,
            block_type=block_type,
            parent_id=self.block_id,
            parent_hash=self.block_hash,
            metadata=metadata
        )
        
        # Add to children dictionary
        self.children[child.block_id] = child
        
        # Update our hash since content changed
        self.last_updated = time.time()
        self._calculate_block_hash()
        
        return child
    
    def add_training_data(self,
                         data_content: str,
                         data_type: str,
                         metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add training data to this block
        
        Args:
            data_content: Content of the training data
            data_type: Type of data (e.g., "observation", "feature", etc.)
            metadata: Optional metadata for the data
            
        Returns:
            data_id: ID of the added data entry
        """
        data_id = str(uuid.uuid4())
        
        # Create data entry
        data_entry = {
            "data_id": data_id,
            "content": data_content,
            "data_type": data_type,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        # Add to data entries list
        self.data_entries.append(data_entry)
        
        # Update block state
        self.last_updated = time.time()
        self._calculate_block_hash()
        
        return data_id
    
    def add_llm_call(self, 
                    prompt: str, 
                    result: str,
                    metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Record an LLM call for this training block
        
        Args:
            prompt: The prompt sent to the LLM
            result: The result received from the LLM
            metadata: Optional metadata for the LLM call
            
        Returns:
            call_id: ID of the added LLM call
        """
        call_id = str(uuid.uuid4())
        
        # Create LLM call entry
        llm_call = {
            "call_id": call_id,
            "prompt": prompt,
            "result": result,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        # Add to LLM calls list
        self.llm_calls.append(llm_call)
        
        # Update block state
        self.last_updated = time.time()
        self._calculate_block_hash()
        
        return call_id
    
    def add_consensus_report(self, 
                           report_content: str,
                           votes: List[Dict[str, Any]],
                           metadata: Optional[Dict[str, Any]] = None) -> str:
        """
        Add a consensus report to this block
        
        Args:
            report_content: Content of the consensus report
            votes: List of votes from participating agents
            metadata: Optional metadata for the report
            
        Returns:
            report_id: ID of the added consensus report
        """
        report_id = str(uuid.uuid4())
        
        # Create consensus report entry
        consensus_report = {
            "report_id": report_id,
            "content": report_content,
            "votes": votes,
            "metadata": metadata or {},
            "timestamp": time.time()
        }
        
        # Add to consensus reports list
        self.consensus_reports.append(consensus_report)
        
        # Update training state if this is a final consensus
        if metadata and metadata.get("is_final", False):
            self.training_state = "completed"
        
        # Update block state
        self.last_updated = time.time()
        self._calculate_block_hash()
        
        return report_id
    
    def update_training_state(self, new_state: str, reason: Optional[str] = None) -> None:
        """
        Update the training state of this block
        
        Args:
            new_state: New training state
            reason: Optional reason for the state change
        """
        old_state = self.training_state
        self.training_state = new_state
        
        # Add state change to metadata
        if "state_changes" not in self.metadata:
            self.metadata["state_changes"] = []
            
        self.metadata["state_changes"].append({
            "from": old_state,
            "to": new_state,
            "timestamp": time.time(),
            "reason": reason
        })
        
        # Update block state
        self.last_updated = time.time()
        self._calculate_block_hash()
        
        logger.info(f"Block {self.block_id[:8]} state changed: {old_state} -> {new_state}")
    
    def get_training_path(self) -> List[Dict[str, Any]]:
        """
        Get the full training path from root to this block
        
        Returns:
            List of block metadata dictionaries in path order
        """
        # This method would need to be implemented with memory tree integration
        # Placeholder for now
        return [{"block_id": self.block_id, "block_hash": self.block_hash}]
    
    def verify_parent_chain(self) -> bool:
        """
        Verify the integrity of the parent chain
        
        Returns:
            True if chain is valid, False otherwise
        """
        # This method would need to be implemented with memory tree integration
        # Placeholder for now
        return True
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert block to dictionary for serialization
        
        Returns:
            Dictionary representation of the block
        """
        return {
            "block_id": self.block_id,
            "block_hash": self.block_hash,
            "agent_id": self.agent_id,
            "block_type": self.block_type,
            "parent_id": self.parent_id,
            "parent_hash": self.parent_hash,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "training_state": self.training_state,
            "metadata": self.metadata,
            "data_count": len(self.data_entries),
            "llm_call_count": len(self.llm_calls),
            "consensus_count": len(self.consensus_reports),
            "child_count": len(self.children),
        }
    
    @staticmethod
    def from_dict(block_dict: Dict[str, Any]) -> "TrainingBlock":
        """
        Create a TrainingBlock from a dictionary
        
        Args:
            block_dict: Dictionary representation of a block
            
        Returns:
            TrainingBlock instance
        """
        # Create a new block instance without init parameters
        block = TrainingBlock.__new__(TrainingBlock)
        
        # Set attributes directly
        block.block_id = block_dict["block_id"]
        block.block_hash = block_dict["block_hash"]
        block.agent_id = block_dict["agent_id"]
        block.block_type = block_dict["block_type"]
        block.parent_id = block_dict["parent_id"]
        block.parent_hash = block_dict["parent_hash"]
        block.created_at = block_dict["created_at"]
        block.last_updated = block_dict["last_updated"]
        block.training_state = block_dict["training_state"]
        block.metadata = block_dict["metadata"]
        block.children = {}
        block.data_entries = []
        block.llm_calls = []
        block.consensus_reports = []
        
        return block
