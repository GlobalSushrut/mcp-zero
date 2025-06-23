"""
IntentWeightBias - Adaptive Learning Extension for PARE Protocol

This module extends the PARE Network Chain Protocol with adaptive learning capabilities
that adjust weights over time based on observed intent patterns and outcomes.
"""

import time
import math
import hashlib
import json
from typing import Dict, List, Tuple, Any, Optional
import numpy as np

class IntentWeightBias:
    """
    Implements adaptive learning through intent-based weight adjustments.
    
    This class provides:
    1. Intent pattern recognition and classification
    2. Time-decay weighted bias adjustments
    3. Confidence scoring with historical context
    4. Integration with heap consensus and retrograde learning
    """
    
    def __init__(self, 
                 dimensions: Tuple[int, int] = (10, 10),
                 learning_rate: float = 0.05, 
                 decay_factor: float = 0.98,
                 confidence_threshold: float = 0.70):
        """
        Initialize the IntentWeightBias system.
        
        Args:
            dimensions: Size of the intent space grid (rows, cols)
            learning_rate: Base rate for weight adjustments
            decay_factor: Time decay factor for historical weight influence
            confidence_threshold: Minimum confidence required for adjustment
        """
        self.dimensions = dimensions
        self.learning_rate = learning_rate
        self.decay_factor = decay_factor
        self.confidence_threshold = confidence_threshold
        
        # Initialize weight matrices
        self.intent_weights = np.zeros(dimensions)
        self.bias_adjustments = np.zeros(dimensions)
        self.confidence_scores = np.zeros(dimensions)
        
        # History tracking
        self.adjustment_history = []
        self.last_active_timestamp = {}  # Map of grid positions to last activity time
        
        # Adaptive parameters
        self.adaptive_learning_rate = learning_rate
        self.learning_iterations = 0
        
    def compute_intent_position(self, intent_data: Dict[str, Any]) -> Tuple[int, int]:
        """
        Map intent data to a position in the intent space grid.
        
        Args:
            intent_data: Dictionary containing intent features
            
        Returns:
            Tuple (row, col) representing position in the intent grid
        """
        # Create a deterministic hash from the intent data
        intent_str = json.dumps(intent_data, sort_keys=True)
        intent_hash = hashlib.sha256(intent_str.encode()).hexdigest()
        
        # Map the hash to grid coordinates
        hash_val = int(intent_hash[:8], 16)
        row = hash_val % self.dimensions[0]
        col = (hash_val // self.dimensions[0]) % self.dimensions[1]
        
        return (row, col)
    
    def register_intent(self, 
                       intent_data: Dict[str, Any], 
                       outcome_value: float,
                       confidence: float) -> Dict[str, Any]:
        """
        Register an observed intent and its outcome, updating weights.
        
        Args:
            intent_data: Dictionary with intent features
            outcome_value: Observed outcome/success value (0.0 to 1.0)
            confidence: Confidence in this observation (0.0 to 1.0)
            
        Returns:
            Dictionary with updated metrics
        """
        if confidence < self.confidence_threshold:
            return {
                "applied": False,
                "reason": "confidence_below_threshold",
                "confidence": confidence,
                "threshold": self.confidence_threshold
            }
        
        # Determine grid position
        position = self.compute_intent_position(intent_data)
        row, col = position
        
        # Calculate time-decay if this position was previously active
        current_time = time.time()
        time_factor = 1.0
        if position in self.last_active_timestamp:
            time_elapsed = current_time - self.last_active_timestamp[position]
            # Apply decay based on time elapsed (in hours)
            time_factor = self.decay_factor ** (time_elapsed / 3600)
        
        # Update timestamp
        self.last_active_timestamp[position] = current_time
        
        # Calculate adjustment
        current_value = self.intent_weights[row, col]
        adjustment = self.adaptive_learning_rate * confidence * (outcome_value - current_value) * time_factor
        
        # Apply adjustment
        self.intent_weights[row, col] += adjustment
        self.bias_adjustments[row, col] = adjustment
        self.confidence_scores[row, col] = confidence
        
        # Track history
        self.adjustment_history.append({
            "position": position,
            "timestamp": current_time,
            "adjustment": adjustment,
            "confidence": confidence,
            "intent_hash": hashlib.sha256(json.dumps(intent_data, sort_keys=True).encode()).hexdigest()[:16]
        })
        
        # Update adaptive learning rate (decreases with more iterations)
        self.learning_iterations += 1
        self.adaptive_learning_rate = self.learning_rate * (1.0 / (1.0 + math.log(1 + self.learning_iterations * 0.1)))
        
        return {
            "applied": True,
            "position": position,
            "adjustment": adjustment,
            "new_value": self.intent_weights[row, col],
            "confidence": confidence,
            "learning_rate": self.adaptive_learning_rate
        }
    
    def get_intent_weight(self, intent_data: Dict[str, Any]) -> Dict[str, Any]:
        """
        Retrieve the current weight for a given intent.
        
        Args:
            intent_data: Dictionary with intent features
            
        Returns:
            Dictionary with weight information
        """
        position = self.compute_intent_position(intent_data)
        row, col = position
        
        return {
            "position": position,
            "weight": self.intent_weights[row, col],
            "confidence": self.confidence_scores[row, col],
            "last_adjustment": self.bias_adjustments[row, col],
            "last_active": self.last_active_timestamp.get(position, None)
        }
    
    def apply_neighborhood_diffusion(self, 
                                    center_position: Tuple[int, int], 
                                    radius: int = 1,
                                    diffusion_strength: float = 0.5) -> int:
        """
        Apply learning diffusion to neighboring positions in the intent space.
        
        Args:
            center_position: Central position (row, col)
            radius: Area of effect radius
            diffusion_strength: Strength multiplier (0-1)
            
        Returns:
            Number of positions affected
        """
        center_row, center_col = center_position
        center_value = self.intent_weights[center_row, center_col]
        center_confidence = self.confidence_scores[center_row, center_col]
        
        affected = 0
        
        # Apply to neighborhood in square pattern
        for r in range(max(0, center_row - radius), min(self.dimensions[0], center_row + radius + 1)):
            for c in range(max(0, center_col - radius), min(self.dimensions[1], center_col + radius + 1)):
                if (r, c) != (center_row, center_col):  # Skip the center
                    # Calculate distance-based diffusion
                    distance = max(abs(r - center_row), abs(c - center_col))
                    strength = diffusion_strength * (1.0 / distance)
                    
                    # Diffuse the center value
                    adjustment = strength * center_confidence * (center_value - self.intent_weights[r, c])
                    self.intent_weights[r, c] += adjustment
                    affected += 1
        
        return affected
    
    def serialize(self) -> Dict[str, Any]:
        """
        Serialize the current state for storage.
        
        Returns:
            Dictionary representation of current state
        """
        # Convert tuple keys to strings in last_active_timestamp for JSON serialization
        serializable_timestamps = {}
        for position, timestamp in self.last_active_timestamp.items():
            # Convert tuple positions to string keys like "row,col" 
            if isinstance(position, tuple):
                key = f"{position[0]},{position[1]}"
            else:
                key = str(position)
            serializable_timestamps[key] = timestamp
        
        return {
            "dimensions": self.dimensions,
            "learning_rate": self.learning_rate,
            "adaptive_learning_rate": self.adaptive_learning_rate,
            "decay_factor": self.decay_factor,
            "confidence_threshold": self.confidence_threshold,
            "learning_iterations": self.learning_iterations,
            "intent_weights": self.intent_weights.tolist(),
            "bias_adjustments": self.bias_adjustments.tolist(),
            "confidence_scores": self.confidence_scores.tolist(),
            "last_active_timestamp": serializable_timestamps,
            # Only keep recent history to avoid excessive memory usage
            "adjustment_history": self.adjustment_history[-100:] if len(self.adjustment_history) > 100 else self.adjustment_history
        }
    
    @classmethod
    def deserialize(cls, data: Dict[str, Any]) -> 'IntentWeightBias':
        """
        Recreate an IntentWeightBias instance from serialized data.
        
        Args:
            data: Dictionary created by serialize()
            
        Returns:
            New IntentWeightBias instance
        """
        instance = cls(
            dimensions=tuple(data["dimensions"]),
            learning_rate=data["learning_rate"],
            decay_factor=data["decay_factor"],
            confidence_threshold=data["confidence_threshold"]
        )
        
        instance.adaptive_learning_rate = data["adaptive_learning_rate"]
        instance.learning_iterations = data["learning_iterations"]
        instance.intent_weights = np.array(data["intent_weights"])
        instance.bias_adjustments = np.array(data["bias_adjustments"])
        instance.confidence_scores = np.array(data["confidence_scores"])
        instance.last_active_timestamp = data["last_active_timestamp"]
        instance.adjustment_history = data["adjustment_history"]
        
        return instance
    
    def integrate_with_consensus(self, proposal: str, agent_id: str, confidence: float) -> float:
        """
        Integrate with factorial voting consensus to adjust vote weighting.
        
        Args:
            proposal: The consensus proposal string
            agent_id: Agent ID making the proposal
            confidence: Original confidence score
            
        Returns:
            Adjusted confidence score based on intent weight bias
        """
        # Create an intent signature using proposal and agent
        intent_data = {
            "proposal": proposal,
            "agent_id": agent_id
        }
        
        # Get current weight for this intent
        weight_info = self.get_intent_weight(intent_data)
        
        # Adjust confidence based on historical performance
        weight = weight_info["weight"]
        adjustment_factor = 1.0 + weight  # Adjust up or down based on weight
        
        # Ensure confidence stays within valid bounds (0-1)
        adjusted_confidence = min(1.0, max(0.0, confidence * adjustment_factor))
        
        return adjusted_confidence
    
    def integrate_with_retrograde(self, indices: Tuple[int, int], target_value: float) -> Tuple[float, float]:
        """
        Integrate with retrograde learning to adjust target values.
        
        Args:
            indices: Position in the sparse matrix
            target_value: Original target value
            
        Returns:
            Tuple of (adjusted_target_value, confidence)
        """
        # Map retrograde indices to intent space
        intent_row = indices[0] % self.dimensions[0]
        intent_col = indices[1] % self.dimensions[1]
        
        # Get current bias at this position
        weight = self.intent_weights[intent_row, intent_col]
        confidence = self.confidence_scores[intent_row, intent_col]
        
        # Adjust target value based on bias
        adjusted_value = target_value * (1.0 + weight)
        
        # Ensure value stays within valid bounds (0-1)
        adjusted_value = min(1.0, max(0.0, adjusted_value))
        
        return (adjusted_value, confidence)
    
    def generate_metrics(self) -> Dict[str, Any]:
        """
        Generate metrics about current state.
        
        Returns:
            Dictionary with metrics
        """
        avg_weight = float(np.mean(self.intent_weights))
        max_weight = float(np.max(self.intent_weights))
        min_weight = float(np.min(self.intent_weights))
        active_positions = len(self.last_active_timestamp)
        total_positions = self.dimensions[0] * self.dimensions[1]
        coverage = active_positions / total_positions
        
        return {
            "avg_weight": avg_weight,
            "max_weight": max_weight,
            "min_weight": min_weight,
            "active_positions": active_positions,
            "total_positions": total_positions,
            "coverage": coverage,
            "learning_iterations": self.learning_iterations,
            "current_learning_rate": self.adaptive_learning_rate
        }


# Example integration functions

def integrate_with_chain_protocol(chain_protocol, intent_bias):
    """
    Example function showing how to integrate IntentWeightBias with PAREChainProtocol
    """
    # Store the IntentWeightBias in the chain protocol
    chain_protocol.intent_weight_bias = intent_bias
    
    # Extend chain protocol with intent bias methods
    def register_intent_with_chain(self, block_id, intent_data, outcome_value, confidence):
        """Register intent observation with a training block"""
        # First register with IntentWeightBias
        result = self.intent_weight_bias.register_intent(intent_data, outcome_value, confidence)
        
        # Then store the result in the chain
        self.add_training_data(
            block_id=block_id,
            content=json.dumps({
                "intent_data": intent_data,
                "outcome": outcome_value,
                "confidence": confidence,
                "result": result
            }),
            data_type="intent_observation"
        )
        
        return result
    
    # Attach the method to the chain protocol
    import types
    chain_protocol.register_intent = types.MethodType(register_intent_with_chain, chain_protocol)
