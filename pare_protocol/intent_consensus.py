"""
IntentConsensus - Integration of IntentWeightBias with Heap Consensus

This module integrates the adaptive IntentWeightBias system with the 
factorial voting heap consensus mechanism for improved decision making.
"""

import time
import json
import hashlib
from typing import Dict, List, Any, Optional, Tuple

from .heap_consensus import FactorialVotingConsensus
from .intent_weight_bias import IntentWeightBias

class IntentAwareConsensus(FactorialVotingConsensus):
    """
    Extends FactorialVotingConsensus with adaptive intent-based weighting.
    
    This enhanced consensus mechanism:
    1. Adjusts vote weights based on historical intent patterns
    2. Adapts to changing agent performance over time
    3. Provides intent-aware confidence scoring
    4. Maintains compatibility with the base consensus mechanism
    """
    
    def __init__(self, 
                 consensus_threshold: float = 0.66, 
                 mining_difficulty: int = 1,
                 intent_dimensions: Tuple[int, int] = (10, 10),
                 learning_rate: float = 0.05):
        """
        Initialize the intent-aware consensus mechanism.
        
        Args:
            consensus_threshold: Threshold required to reach consensus (0.0-1.0)
            mining_difficulty: Mining difficulty for vote validation
            intent_dimensions: Size of the intent space grid
            learning_rate: Base learning rate for intent bias
        """
        # Initialize the base heap consensus
        super().__init__(consensus_threshold, mining_difficulty)
        
        # Initialize the intent weight bias system
        self.intent_bias = IntentWeightBias(
            dimensions=intent_dimensions,
            learning_rate=learning_rate
        )
        
        # Track consensus history for learning
        self.consensus_history = []
        
    def submit_vote(self, 
                    agent_id: str, 
                    proposal: str, 
                    confidence: float = 1.0, 
                    metadata: Optional[Dict] = None) -> Dict[str, Any]:
        """
        Submit a vote with intent-aware adjusted confidence.
        
        Args:
            agent_id: ID of the voting agent
            proposal: The proposal string being voted on
            confidence: Raw confidence score (0.0 to 1.0)
            metadata: Optional metadata for the vote
            
        Returns:
            Dictionary with vote submission results
        """
        # Create intent data from vote information
        intent_data = {
            "agent_id": agent_id,
            "proposal": proposal,
            "raw_confidence": confidence,
            "metadata": metadata or {}
        }
        
        # Get intent-adjusted confidence
        adjusted_confidence = self.intent_bias.integrate_with_consensus(
            proposal=proposal, 
            agent_id=agent_id, 
            confidence=confidence
        )
        
        # Submit to base consensus with adjusted confidence
        success, message = super().submit_vote(
            agent_id=agent_id,
            proposal=proposal,
            confidence=adjusted_confidence,
            metadata=metadata
        )
        
        # Create result dictionary instead of modifying the tuple
        result = {
            "success": success,
            "message": message,
            "intent_adjustment": {
                "raw_confidence": confidence,
                "adjusted_confidence": adjusted_confidence,
                "adjustment_factor": adjusted_confidence / confidence if confidence > 0 else 1.0
            }
        }
        
        return result
    
    def get_consensus_status(self) -> Dict[str, Any]:
        """
        Get the current consensus status with intent metrics.
        
        Returns:
            Dictionary with consensus status and intent metrics
        """
        # Get base consensus status
        status = super().get_consensus_status()
        
        # Add intent bias metrics
        status["intent_metrics"] = self.intent_bias.generate_metrics()
        
        return status
    
    def finalize_consensus(self) -> Dict[str, Any]:
        """
        Finalize consensus and learn from the outcome.
        
        Returns:
            Dictionary with finalized consensus result
        """
        # Get consensus state from the base class instance attributes directly
        # rather than relying on the return value from super().finalize_consensus()
        consensus_status = self.get_consensus_status()
        
        # Create our own result dictionary with known fields
        result = {
            "consensus_id": self.consensus_id,
            "consensus_reached": consensus_status["consensus_reached"],
            "consensus_result": consensus_status["consensus_result"],
            "support_percentage": consensus_status.get("support_percentage", 0),
            "vote_count": len(self.processed_votes) if hasattr(self, 'processed_votes') else len(self.votes),
            "timestamp": time.time()
        }
        
        # Also call the parent implementation, but don't rely on its return value
        # for our core data to avoid potential type mismatches
        super().finalize_consensus()
        
        if result["consensus_reached"]:
            # Record this consensus for learning
            self.consensus_history.append({
                "timestamp": time.time(),
                "result": result["consensus_result"],
                "support": result["support_percentage"],
                "votes": len(self.votes)
            })
            
            # Learn from this outcome
            # For each vote, update the intent bias based on whether
            # the agent voted for the winning proposal
            for vote in self.votes:
                # Extract vote information based on its type
                if isinstance(vote, dict):
                    # If vote is a dictionary
                    agent_id = vote.get("agent_id", "")
                    vote_proposal = vote.get("proposal", "")
                    confidence = vote.get("confidence", 1.0)
                elif isinstance(vote, tuple) and len(vote) >= 3:
                    # If vote is a tuple, assuming format (agent_id, proposal, confidence, ...)
                    agent_id = vote[0]
                    vote_proposal = vote[1]
                    confidence = vote[2]
                else:
                    # Skip this vote if we can't parse it
                    continue
                
                # Get the consensus result safely
                consensus_result = result.get("consensus_result", "") 
                
                # Calculate outcome value based on alignment with consensus
                outcome_value = 1.0 if vote_proposal == consensus_result else 0.0
                
                # Create intent data
                intent_data = {
                    "agent_id": agent_id,
                    "proposal": vote_proposal
                }
                
                # Ensure confidence is a float before passing it
                if isinstance(confidence, dict):
                    # If confidence is somehow a dictionary, try to extract a float value
                    float_confidence = confidence.get('value', 1.0) if isinstance(confidence, dict) else 1.0
                elif isinstance(confidence, (int, float)):
                    # If confidence is already a number, use it
                    float_confidence = float(confidence)
                else:
                    # Default confidence if none of the above works
                    float_confidence = 1.0
                
                # Register intent observation with validated float confidence
                self.intent_bias.register_intent(
                    intent_data=intent_data,
                    outcome_value=outcome_value,
                    confidence=float_confidence
                )
                
            # Add learning record to result
            result["learning_applied"] = True
            result["learning_metrics"] = self.intent_bias.generate_metrics()
        
        return result
    
    def serialize(self) -> Dict[str, Any]:
        """
        Serialize the consensus state including intent bias.
        
        Returns:
            Dictionary with serialized state
        """
        # Get base serialization
        data = super().serialize()
        
        # Add intent bias data
        data["intent_bias"] = self.intent_bias.serialize()
        data["consensus_history"] = self.consensus_history[-100:] if len(self.consensus_history) > 100 else self.consensus_history
        
        return data
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'IntentAwareConsensus':
        """
        Recreate consensus object from serialized data.
        
        Args:
            data: Dictionary created by serialize()
            
        Returns:
            New IntentAwareConsensus instance
        """
        # Extract intent bias parameters
        intent_dimensions = tuple(data["intent_bias"]["dimensions"])
        learning_rate = data["intent_bias"]["learning_rate"]
        
        # Create new instance
        instance = cls(
            consensus_threshold=data["consensus_threshold"],
            mining_difficulty=data["mining_difficulty"],
            intent_dimensions=intent_dimensions,
            learning_rate=learning_rate
        )
        
        # Restore state
        instance.voters = data["voters"]
        instance.votes = data["votes"]
        instance.vote_heap = data["vote_heap"]
        instance.intent_bias = IntentWeightBias.deserialize(data["intent_bias"])
        instance.consensus_history = data["consensus_history"]
        
        return instance
