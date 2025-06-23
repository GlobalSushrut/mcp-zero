#!/usr/bin/env python3
"""
PARE Protocol IntentWeightBias Demo

This script demonstrates the integration of IntentWeightBias with the PARE Network Chain Protocol.
It shows how adaptive learning works with both the consensus mechanism and retrograde learning.
"""

import os
import sys
import time
import json
import argparse
import random
from typing import Dict, Any

# Add parent directory to path for imports
parent_dir = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
if parent_dir not in sys.path:
    sys.path.append(parent_dir)

from pare_protocol.chain_protocol import PAREChainProtocol
from pare_protocol.intent_weight_bias import IntentWeightBias
from pare_protocol.intent_consensus import IntentAwareConsensus
from pare_protocol.retrograde_learning import RetrogradeLearner
import numpy as np


def visualize_intent_grid(intent_bias):
    """
    Visualize the IntentWeightBias memory grid state as a heat map in the terminal.
    
    Args:
        intent_bias: The IntentWeightBias instance to visualize
    """
    # Get the grid dimensions and weights
    grid = intent_bias.intent_weights
    rows, cols = grid.shape
    
    # Find min and max for scaling
    min_val = np.min(grid)
    max_val = np.max(grid)
    
    # If no variance in grid, avoid division by zero
    if max_val == min_val:
        normalized_grid = np.zeros_like(grid)
    else:
        # Normalize to 0-1 range
        normalized_grid = (grid - min_val) / (max_val - min_val)
    
    # Define ASCII characters for heat map intensity
    # From least intense to most intense
    intensity_chars = ' .:-=+*#%@'
    
    # Color codes for terminal
    RESET = '\033[0m'
    BLUE = '\033[34m'
    CYAN = '\033[36m'
    GREEN = '\033[32m'
    YELLOW = '\033[33m'
    RED = '\033[31m'
    
    # Print column indices
    print('    ', end='')
    for j in range(cols):
        print(f'{j}', end=' ')
    print('\n    +'+ '-' * (cols * 2 - 1) + '+')
    
    # Print the grid
    for i in range(rows):
        print(f'{i:2d} | ', end='')
        for j in range(cols):
            # Get normalized value and map to character
            val = normalized_grid[i, j]
            char_idx = min(int(val * len(intensity_chars)), len(intensity_chars) - 1)
            char = intensity_chars[char_idx]
            
            # Color based on value
            if val == 0:
                color = RESET
            elif val < 0.25:
                color = BLUE
            elif val < 0.5:
                color = CYAN
            elif val < 0.75:
                color = GREEN
            elif val < 0.9:
                color = YELLOW
            else:
                color = RED
                
            # Print colored character
            print(f'{color}{char}{RESET}', end=' ')
        print('|')
    
    # Print bottom border
    print('    +'+ '-' * (cols * 2 - 1) + '+')
    
    # Print legend
    print(f"    Legend: {BLUE}■{RESET} Low, {CYAN}■{RESET} Medium, {GREEN}■{RESET} High, {YELLOW}■{RESET} Very High, {RED}■{RESET} Extreme")
    print(f"    Value Range: [{min_val:.4f}, {max_val:.4f}]")
    print(f"    Active Cells: {np.count_nonzero(grid)}/{rows*cols}")


def run_intent_demo(db_path: str, rpc_url: str):
    """
    Run a demonstration of IntentWeightBias with PARE protocol.
    
    Args:
        db_path: Path to SQLite database for memory storage
        rpc_url: URL to the MCP-ZERO RPC server
    """
    print("\n🧠 PARE Network Chain Protocol with IntentWeightBias Demo 🧠\n")
    print(f"Database Path: {db_path}")
    print(f"RPC Server URL: {rpc_url}\n")
    
    # Initialize PARE Chain Protocol
    protocol = PAREChainProtocol(db_path=db_path, rpc_url=rpc_url)
    print("✅ PAREChainProtocol initialized")
    
    # Initialize IntentWeightBias
    intent_bias = IntentWeightBias(
        dimensions=(8, 8),
        learning_rate=0.1,
        decay_factor=0.95
    )
    print("✅ IntentWeightBias initialized with 8x8 grid")
    
    # Initialize IntentAwareConsensus
    consensus = IntentAwareConsensus(
        consensus_threshold=0.66,
        mining_difficulty=1,
        intent_dimensions=(8, 8),
        learning_rate=0.1
    )
    print("✅ IntentAwareConsensus initialized")
    
    # Create agent IDs
    agents = ["agent-1", "agent-2", "agent-3", "agent-4", "agent-5"]
    
    # Register voters with initial weights
    for i, agent_id in enumerate(agents):
        weight = 1.0 - (i * 0.1)  # Gradually decreasing weights
        consensus.register_voter(agent_id, weight)
    
    print(f"✅ Registered {len(agents)} voters with consensus mechanism")
    
    # Create a root training block
    root_block = protocol.create_training_block(
        agent_id="root-agent",
        block_type="intent_adaptive",
        metadata={"purpose": "IntentWeightBias demonstration"}
    )
    print(f"✅ Created root training block: {root_block}")
    
    # Add children blocks for different agents
    agent_blocks = {}
    for agent_id in agents:
        block_id = protocol.add_child_block(
            parent_id=root_block,
            agent_id=agent_id,
            block_type="intent_learning"
        )
        agent_blocks[agent_id] = block_id
        print(f"✅ Created child block for {agent_id}: {block_id}")
    
    # Create RetrogradeLearner for learning integration
    learner = RetrogradeLearner(
        dimensions=(8, 8),
        geometry="hyperbolic",
        learning_rate=0.15
    )
    print("✅ Created RetrogradeLearner with 8x8 hyperbolic geometry")
    
    # Simulation parameters
    num_rounds = 5
    proposals = ["object_type_A", "object_type_B", "object_type_C", "object_type_D"]
    
    print("\n🔄 Starting adaptive learning simulation over multiple rounds...\n")
    
    # Run multiple rounds of voting and learning
    for round_num in range(1, num_rounds + 1):
        print(f"\n--- Round {round_num}/{num_rounds} ---")
        
        # Reset consensus for this round
        consensus = IntentAwareConsensus(
            consensus_threshold=0.66,
            mining_difficulty=1,
            intent_dimensions=(8, 8),
            learning_rate=0.1
        )
        
        # Register voters (weights will now be influenced by intent bias)
        for agent_id in agents:
            consensus.register_voter(agent_id, 1.0)  # Base weight
        
        # In each round, agents submit votes
        print("Agents submitting votes...")
        for agent_id in agents:
            # For demonstration, use some patterns in voting behavior
            if agent_id == "agent-1":
                proposal = proposals[0]  # Always votes for first option
            elif agent_id == "agent-2":
                proposal = proposals[1]  # Always votes for second option
            elif agent_id == "agent-5":
                proposal = proposals[-1]  # Always votes for last option
            else:
                proposal = random.choice(proposals)  # Random vote
            
            # Generate confidence based on round number (increasing confidence over time)
            base_confidence = 0.7 + (round_num * 0.05)
            confidence = min(0.95, base_confidence + random.uniform(-0.1, 0.1))
            
            # Submit vote with intent bias adjustment
            result = consensus.submit_vote(
                agent_id=agent_id,
                proposal=proposal,
                confidence=confidence
            )
            
            print(f"  {agent_id} voted for {proposal} with confidence {confidence:.2f} " +
                  f"→ adjusted to {result['intent_adjustment']['adjusted_confidence']:.2f}")
            
            # Add voting record to chain
            protocol.add_training_data(
                block_id=agent_blocks[agent_id],
                data_content=json.dumps({
                    "round": round_num,
                    "vote": proposal,
                    "confidence": confidence,
                    "adjusted_confidence": result["intent_adjustment"]["adjusted_confidence"]
                }),
                data_type="vote_record"
            )
        
        # Get consensus status
        status = consensus.get_consensus_status()
        print(f"\nConsensus Status after voting:")
        print(f"  Votes Received: {status['vote_count']}")
        print(f"  Top Proposal: {status['consensus_result']}")
        print(f"  Consensus Reached: {status['consensus_reached']}")
        # Support level is not directly available, will use consensus_details
        details = status.get('consensus_details', {})
        support_str = f"{details.get('support_percentage', 0)*100:.1f}%" if details else "N/A"
        print(f"  Support Level: {support_str}")
        
        # Helper function for processing intent learning
        def process_intent_learning(agent_id, vote_data, outcome_multiplier=1.0):
            nonlocal position  # This will be used later for retrograde learning metrics
            
            # Each vote in processed_votes is a dictionary
            voted_proposal = vote_data["proposal"]
            voted_confidence = vote_data.get("confidence", 0.7)  # Default if missing
            
            # Create intent data
            intent_data = {
                "agent_id": agent_id,
                "proposal": voted_proposal,
                "round": round_num
            }
            
            # Determine base outcome value
            base_outcome = 0.5  # Neutral starting point
            
            # Adjust outcome based on whether this was consensus winner or not
            # For consensus failure, we'll learn from the disagreement patterns
            if "consensus_result" in result:
                top_proposal = result["consensus_result"]
                # Scale outcome based on alignment with top proposal
                if voted_proposal == top_proposal:
                    base_outcome = 0.7  # Slightly positive for aligning with top proposal
                else:
                    base_outcome = 0.3  # Slightly negative for opposing top proposal
            
            # Apply the outcome multiplier (used for consensus vs non-consensus)
            outcome_value = base_outcome * outcome_multiplier
            
            # Register intent with bias system
            bias_result = intent_bias.register_intent(
                intent_data=intent_data,
                outcome_value=outcome_value,
                confidence=voted_confidence 
            )
            
            # Apply to retrograde learner at the same position
            position = intent_bias.compute_intent_position(intent_data)
            adjusted_value, confidence = intent_bias.integrate_with_retrograde(
                position, outcome_value
            )
            
            # Update retrograde learning with stronger backpropagation for disagreements
            learner.backpropagate(
                indices=position,
                target_value=adjusted_value,
                propagation_depth=3  # Deeper propagation to enhance learning
            )
            
            return position, bias_result
            
        # Finalize consensus
        result = consensus.finalize_consensus()
        
        print(f"\nConsensus Result:")
        if result["consensus_reached"]:
            print(f"  ✓ Consensus reached: {result['consensus_result']}")
            print(f"  ✓ Support: {result['support_percentage']*100:.1f}%")
            
            # Record consensus result in chain
            protocol.add_llm_call(
                block_id=root_block,
                prompt=f"Consensus round {round_num}",
                result=json.dumps(result)
            )
            
            # Get votes from processed_votes dictionary
            winning_proposal = result['consensus_result']
            learning_positions = []
            
            # Process learning with successful consensus (higher outcome values)
            for agent_id, vote_data in consensus.processed_votes.items():
                # Higher outcome multiplier (1.2) for successful consensus learning
                pos, res = process_intent_learning(agent_id, vote_data, outcome_multiplier=1.2)
                learning_positions.append(pos)
                
            # Record learning in chain
            protocol.add_training_data(
                block_id=root_block,
                data_content=json.dumps({
                    "round": round_num,
                    "consensus": result['consensus_result'],
                    "learning_applied": True,
                    "positions_updated": len(learning_positions)
                }),
                data_type="intent_learning"
            )
        else:
            print(f"  ✗ No consensus reached")
            # Safety check for when consensus is not reached and support_percentage might not be available
            if 'support_percentage' in result:
                print(f"  ✗ Support for top proposal: {result['support_percentage']*100:.1f}%")
            else:
                # Try to extract from consensus details if available
                details = result.get('consensus_details', {})
                ratio = details.get('consensus_ratio', 0) if isinstance(details, dict) else 0
                print(f"  ✗ Support for top proposal: {ratio*100:.1f}%")
            
            # CRITICAL FIX: Apply learning even when consensus fails
            # This is where the learning was missing before
            learning_positions = []
            
            # Process disagreement learning (with lower outcome multiplier)
            # We still want the system to learn from failures, but more gently
            for agent_id, vote_data in consensus.processed_votes.items():
                # Lower outcome multiplier (0.8) to be more conservative with disagreement learning
                pos, res = process_intent_learning(agent_id, vote_data, outcome_multiplier=0.8)
                learning_positions.append(pos)
            
            # Increase learning rate slightly when consensus fails to accelerate adaptation
            intent_bias.adaptive_learning_rate = min(0.2, intent_bias.adaptive_learning_rate * 1.05)
            
            # Record learning from disagreement in chain
            protocol.add_training_data(
                block_id=root_block,
                data_content=json.dumps({
                    "round": round_num,
                    "consensus_failed": True,
                    "learning_applied": True,
                    "positions_updated": len(learning_positions),
                    "learning_rate_adjusted": True,
                    "new_learning_rate": intent_bias.adaptive_learning_rate
                }),
                data_type="intent_learning_disagreement"
            )
        
        # Generate and show metrics
        intent_metrics = intent_bias.generate_metrics()
        print("\nIntent Learning Metrics:")
        print(f"  Learning Iterations: {intent_metrics['learning_iterations']}")
        print(f"  Average Weight: {intent_metrics['avg_weight']:.4f}")
        print(f"  Active Positions: {intent_metrics['active_positions']}/{intent_metrics['total_positions']}")
        print(f"  Current Learning Rate: {intent_metrics['current_learning_rate']:.4f}")
        
        # Visualize the 8x8 intent grid
        print("\nIntent Grid State (8x8):")
        visualize_intent_grid(intent_bias)
        
        # Define a default position if none was set during consensus
        # (This happens when no consensus is reached)
        try:
            position
        except NameError:
            # Create a default position when no consensus was reached
            position = (4, 4)  # Center of the grid as a reasonable default
            
        # Show some retrograde learning metrics
        recall = learner.recall(position)
        print("\nRetrograde Learning Status:")
        print(f"  Last Position: {position}")
        print(f"  Recall Value: {recall['value']:.4f}")
        print(f"  Recall Confidence: {recall['recall_confidence']:.4f}")
        print(f"  Memory Efficiency: {learner.get_memory_efficiency():.2f}")  # Note: not a percentage
        
        # Pause between rounds
        if round_num < num_rounds:
            print("\nPreparing for next round...\n")
            time.sleep(1)
    
    # Verify the integrity of our memory chain
    print("\n🔒 Verifying memory chain integrity...")
    integrity_result = protocol.verify_chain_integrity(root_block)
    
    if integrity_result[0]:
        print("✅ Memory chain integrity verified!")
        print(f"   Chain depth: {len(integrity_result[1])}")
    else:
        print("❌ Memory chain integrity check failed!")
    
    # Store final state of intent bias to memory
    protocol.add_training_data(
        block_id=root_block,
        data_content=json.dumps(intent_bias.serialize()),
        data_type="intent_bias_snapshot"
    )
    
    print("\n🎉 IntentWeightBias demonstration completed!")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PARE Protocol IntentWeightBias Demo")
    parser.add_argument("--db", default="memory_trace.db", help="Path to SQLite database")
    parser.add_argument("--rpc", default="http://localhost:8081", help="MCP-ZERO RPC server URL")
    
    args = parser.parse_args()
    run_intent_demo(args.db, args.rpc)
