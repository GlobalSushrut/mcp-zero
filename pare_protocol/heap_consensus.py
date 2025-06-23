#!/usr/bin/env python3
"""
Factorial Voting Consensus for PARE Network Chain Protocol

Implements a binary heap-based factorial voting mechanism for achieving
consensus in agent training. This ensures integrity and reliability
in multi-agent training scenarios while maintaining cryptographic
verification within MCP-ZERO's memory trace system.
"""

import uuid
import time
import math
import hashlib
import heapq
import logging
from typing import Dict, List, Any, Optional, Tuple, Union, Set

# Configure logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("FactorialConsensus")

class FactorialVotingConsensus:
    """
    Factorial Voting Consensus for agent training verification
    
    Features:
    - Binary heap structure for efficient priority-based voting
    - Factorial weight assignment for voter influence scaling
    - Cryptographic verification integrated with memory tree
    - Mining-based vote validation for computational integrity
    """
    
    def __init__(self, consensus_threshold: float = 0.66, 
                mining_difficulty: int = 2, 
                voter_weights: Optional[Dict[str, float]] = None):
        """
        Initialize consensus mechanism
        
        Args:
            consensus_threshold: Threshold for consensus agreement (0.0 to 1.0)
            mining_difficulty: Computational difficulty for vote mining (higher = more compute)
            voter_weights: Optional pre-assigned weights for voters
        """
        self.consensus_id = str(uuid.uuid4())
        self.consensus_threshold = consensus_threshold
        self.mining_difficulty = mining_difficulty
        self.created_at = time.time()
        self.last_updated = self.created_at
        
        # Voter weights (agent_id -> weight)
        self.voter_weights = voter_weights or {}
        
        # Active votes and consensus state
        self.votes = []  # Binary heap for priority-based processing
        self.processed_votes = {}  # agent_id -> vote details
        self.consensus_reached = False
        self.consensus_result = None
        self.consensus_details = {}
        
        # Cryptographic verification
        self.consensus_hash = self._calculate_consensus_hash()
        
        logger.info(f"Created factorial voting consensus {self.consensus_id[:8]} with "
                   f"threshold {consensus_threshold}, difficulty {mining_difficulty}")
    
    def _calculate_consensus_hash(self) -> str:
        """Calculate cryptographic hash of consensus state"""
        # Combine core data for hashing
        hash_data = {
            "consensus_id": self.consensus_id,
            "consensus_threshold": self.consensus_threshold,
            "mining_difficulty": self.mining_difficulty,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "vote_count": len(self.processed_votes),
            "consensus_reached": self.consensus_reached,
            "consensus_result": str(self.consensus_result)
        }
        
        # Calculate hash
        hash_string = hashlib.sha256(str(hash_data).encode()).hexdigest()
        return hash_string
    
    def _calculate_vote_hash(self, agent_id: str, proposal: Any, nonce: int) -> str:
        """
        Calculate vote hash for mining validation
        
        Args:
            agent_id: ID of voting agent
            proposal: The proposal being voted on
            nonce: Nonce value for mining
            
        Returns:
            Cryptographic hash of the vote
        """
        vote_data = {
            "agent_id": agent_id,
            "proposal": str(proposal),
            "nonce": nonce,
            "timestamp": time.time()
        }
        
        return hashlib.sha256(str(vote_data).encode()).hexdigest()
    
    def _validate_vote_mining(self, vote_hash: str) -> bool:
        """
        Validate that vote meets mining difficulty requirement
        
        Args:
            vote_hash: Vote hash to validate
            
        Returns:
            True if vote hash meets difficulty requirement
        """
        # Check if vote hash starts with required number of zeros
        # This is a simplified mining validation
        return vote_hash.startswith("0" * self.mining_difficulty)
    
    def _calculate_factorial_weight(self, base_weight: float, vote_position: int) -> float:
        """
        Calculate factorial-based weight for a vote
        
        Args:
            base_weight: Base weight of the voter
            vote_position: Position in voting sequence
            
        Returns:
            Factorial-adjusted weight
        """
        # Use factorial diminishing to adjust weight based on position
        # This creates a factorial priority system
        if vote_position <= 1:
            return base_weight
        else:
            # Factorial diminishing factor (1/n!)
            factorial = math.factorial(vote_position)
            return base_weight / factorial
    
    def register_voter(self, agent_id: str, weight: float = 1.0) -> None:
        """
        Register a voter with a specific weight
        
        Args:
            agent_id: ID of the voting agent
            weight: Weight to assign to the voter
        """
        self.voter_weights[agent_id] = weight
        self.last_updated = time.time()
        self.consensus_hash = self._calculate_consensus_hash()
        
        logger.info(f"Registered voter {agent_id[:8]} with weight {weight}")
    
    def submit_vote(self, agent_id: str, proposal: Any, confidence: float,
                  metadata: Optional[Dict[str, Any]] = None) -> Tuple[bool, str]:
        """
        Submit a vote for consensus processing
        
        Args:
            agent_id: ID of the voting agent
            proposal: Proposal content being voted on
            confidence: Confidence level in the vote (0.0 to 1.0)
            metadata: Optional additional metadata
            
        Returns:
            (success, message): Success status and message
        """
        # Check if agent is registered
        if agent_id not in self.voter_weights:
            self.register_voter(agent_id)  # Auto-register with default weight
        
        # Get base weight for this agent
        base_weight = self.voter_weights[agent_id]
        
        # Perform vote mining for integrity verification
        nonce = 0
        vote_hash = ""
        mining_start = time.time()
        
        # Mine until difficulty requirement met or timeout
        timeout = min(2.0, 0.1 * self.mining_difficulty)  # Adaptive timeout based on difficulty
        while time.time() - mining_start < timeout:
            vote_hash = self._calculate_vote_hash(agent_id, proposal, nonce)
            if self._validate_vote_mining(vote_hash):
                break
            nonce += 1
        
        # Check if mining succeeded
        if not self._validate_vote_mining(vote_hash):
            return False, "Vote mining failed to meet difficulty requirement"
        
        # Calculate initial vote weight using confidence and base weight
        initial_weight = base_weight * confidence
        
        # Determine vote position for this agent (if already voted, use same position)
        vote_position = len(self.processed_votes) + 1
        if agent_id in self.processed_votes:
            vote_position = self.processed_votes[agent_id]["position"]
        
        # Calculate factorial weight
        factorial_weight = self._calculate_factorial_weight(initial_weight, vote_position)
        
        # Create vote entry
        vote_entry = {
            "agent_id": agent_id,
            "proposal": proposal,
            "confidence": confidence,
            "base_weight": base_weight,
            "factorial_weight": factorial_weight,
            "position": vote_position,
            "vote_hash": vote_hash,
            "nonce": nonce,
            "timestamp": time.time(),
            "metadata": metadata or {}
        }
        
        # Add to processed votes
        self.processed_votes[agent_id] = vote_entry
        
        # Add to priority queue (negative weight for max-heap behavior)
        heapq.heappush(self.votes, (-factorial_weight, agent_id, vote_entry))
        
        # Update consensus state
        self._update_consensus_state()
        
        logger.info(f"Vote submitted by {agent_id[:8]} with weight {factorial_weight:.4f} "
                   f"(pos={vote_position}, nonce={nonce})")
        
        return True, f"Vote accepted with weight {factorial_weight:.4f}"
    
    def _update_consensus_state(self) -> None:
        """Update the current consensus state based on votes"""
        if not self.votes:
            return
        
        # Group votes by proposal
        proposals = {}
        total_weight = 0
        
        for _, _, vote in self.votes:
            proposal_str = str(vote["proposal"])
            if proposal_str not in proposals:
                proposals[proposal_str] = {"weight": 0, "votes": []}
            
            proposals[proposal_str]["weight"] += vote["factorial_weight"]
            proposals[proposal_str]["votes"].append(vote)
            total_weight += vote["factorial_weight"]
        
        # Find proposal with highest weight
        top_proposal = max(proposals.items(), key=lambda x: x[1]["weight"])
        proposal_key, proposal_data = top_proposal
        
        # Calculate consensus metrics
        consensus_ratio = proposal_data["weight"] / total_weight if total_weight > 0 else 0
        
        # Check if consensus threshold is met
        if consensus_ratio >= self.consensus_threshold:
            self.consensus_reached = True
            self.consensus_result = proposal_key  # Use the string directly as the result
            
            self.consensus_details = {
                "winning_proposal": proposal_key,
                "consensus_ratio": consensus_ratio,
                "total_weight": total_weight,
                "winning_weight": proposal_data["weight"],
                "vote_count": len(self.processed_votes),
                "supporting_agents": [v["agent_id"] for v in proposal_data["votes"]],
                "reached_at": time.time()
            }
            
            logger.info(f"Consensus reached: {proposal_key} with {consensus_ratio:.2%} support")
        else:
            self.consensus_reached = False
            self.consensus_details = {
                "leading_proposal": proposal_key,
                "consensus_ratio": consensus_ratio,
                "total_weight": total_weight,
                "winning_weight": proposal_data["weight"],
                "vote_count": len(self.processed_votes),
                "threshold": self.consensus_threshold
            }
        
        # Update state
        self.last_updated = time.time()
        self.consensus_hash = self._calculate_consensus_hash()
    
    def get_top_votes(self, count: int = 3) -> List[Dict[str, Any]]:
        """
        Get the top votes by weight
        
        Args:
            count: Maximum number of votes to return
            
        Returns:
            List of vote details
        """
        # Copy votes to avoid modifying original heap
        votes_copy = self.votes.copy()
        results = []
        
        # Extract top votes from heap
        for _ in range(min(count, len(votes_copy))):
            if votes_copy:
                _, _, vote = heapq.heappop(votes_copy)
                results.append(vote)
        
        return results
    
    def get_vote_distribution(self) -> Dict[str, Dict[str, Any]]:
        """
        Get vote distribution across proposals
        
        Returns:
            Dictionary mapping proposals to vote aggregates
        """
        # Group votes by proposal
        proposals = {}
        total_weight = 0
        
        for _, _, vote in self.votes:
            proposal_str = str(vote["proposal"])
            if proposal_str not in proposals:
                proposals[proposal_str] = {
                    "weight": 0, 
                    "count": 0, 
                    "agents": set(),
                    "confidence_avg": 0
                }
            
            proposals[proposal_str]["weight"] += vote["factorial_weight"]
            proposals[proposal_str]["count"] += 1
            proposals[proposal_str]["agents"].add(vote["agent_id"])
            proposals[proposal_str]["confidence_avg"] = (
                (proposals[proposal_str]["confidence_avg"] * (proposals[proposal_str]["count"] - 1) +
                 vote["confidence"]) / proposals[proposal_str]["count"]
            )
            total_weight += vote["factorial_weight"]
        
        # Calculate percentages
        for p in proposals.values():
            p["weight_percent"] = (p["weight"] / total_weight * 100) if total_weight > 0 else 0
            p["agents"] = list(p["agents"])  # Convert set to list for serialization
        
        return proposals
    
    def get_consensus_status(self) -> Dict[str, Any]:
        """
        Get current consensus status
        
        Returns:
            Dictionary with consensus status details
        """
        return {
            "consensus_id": self.consensus_id,
            "consensus_reached": self.consensus_reached,
            "consensus_result": self.consensus_result,
            "consensus_details": self.consensus_details,
            "consensus_hash": self.consensus_hash,
            "vote_count": len(self.processed_votes),
            "last_updated": self.last_updated,
            "mining_difficulty": self.mining_difficulty,
            "threshold": self.consensus_threshold
        }
        
    def finalize_consensus(self) -> Dict[str, Any]:
        """
        Finalize the consensus and return the final result.
        This completes the consensus round and returns the final decision.
        
        Returns:
            Dictionary with consensus result details
        """
        # Update consensus state one final time
        self._update_consensus_state()
        
        # Get vote distribution
        proposals = self.get_vote_distribution()
        
        # Prepare result dictionary
        result = {
            "consensus_id": self.consensus_id,
            "consensus_reached": self.consensus_reached,
            "consensus_result": self.consensus_result,
            "vote_count": len(self.processed_votes),
            "proposals": proposals,
            "timestamp": time.time()
        }
        
        # Add support percentage if consensus was reached
        if self.consensus_reached and self.consensus_details:
            result["support_percentage"] = self.consensus_details.get("consensus_ratio", 0)
            result["winning_weight"] = self.consensus_details.get("winning_weight", 0)
            result["total_weight"] = self.consensus_details.get("total_weight", 0)
        
        return result
    
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert consensus state to serializable dictionary
        
        Returns:
            Dictionary representation of consensus
        """
        return {
            "consensus_id": self.consensus_id,
            "consensus_threshold": self.consensus_threshold,
            "mining_difficulty": self.mining_difficulty,
            "created_at": self.created_at,
            "last_updated": self.last_updated,
            "voter_weights": self.voter_weights,
            "processed_votes": self.processed_votes,
            "consensus_reached": self.consensus_reached,
            "consensus_result": self.consensus_result,
            "consensus_details": self.consensus_details,
            "consensus_hash": self.consensus_hash
        }
    
    @staticmethod
    def from_dict(data: Dict[str, Any]) -> "FactorialVotingConsensus":
        """
        Create consensus object from dictionary
        
        Args:
            data: Dictionary representation of consensus
            
        Returns:
            Reconstructed consensus object
        """
        # Create consensus with basic parameters
        consensus = FactorialVotingConsensus(
            consensus_threshold=data["consensus_threshold"],
            mining_difficulty=data["mining_difficulty"],
            voter_weights=data["voter_weights"]
        )
        
        # Restore remaining state
        consensus.consensus_id = data["consensus_id"]
        consensus.created_at = data["created_at"]
        consensus.last_updated = data["last_updated"]
        consensus.processed_votes = data["processed_votes"]
        consensus.consensus_reached = data["consensus_reached"]
        consensus.consensus_result = data["consensus_result"]
        consensus.consensus_details = data["consensus_details"]
        
        # Rebuild votes heap
        for agent_id, vote in data["processed_votes"].items():
            heapq.heappush(consensus.votes, (-vote["factorial_weight"], agent_id, vote))
        
        # Recalculate hash to ensure integrity
        consensus.consensus_hash = consensus._calculate_consensus_hash()
        
        return consensus
