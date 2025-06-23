#!/usr/bin/env python3
"""
PARE Network Chain Protocol Demonstration
Shows agent training with block-child hierarchy, retrograde learning, and consensus
"""

import os
import sys
import time
import logging
import argparse

# Add parent directory to import path
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from pare_protocol.chain_protocol import PAREChainProtocol
from pare_protocol.retrograde_learning import RetrogradeLearner
from pare_protocol.heap_consensus import FactorialVotingConsensus
from memory_trace.db.memory_tree import DBMemoryTree

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s - %(name)s - %(levelname)s - %(message)s')
logger = logging.getLogger("PAREDemo")


def run_demo(db_path="pare_demo.db", rpc_url="http://localhost:8081"):
    """Run PARE protocol demonstration"""
    logger.info("Starting PARE Network Chain Protocol demonstration")
    
    # Initialize protocol
    protocol = PAREChainProtocol(db_path=db_path, rpc_url=rpc_url)
    
    # Create agent IDs
    agent_ids = [f"agent-{i}" for i in range(3)]
    
    # Create training blocks
    logger.info("Creating training block hierarchy")
    root_id = protocol.create_training_block(
        agent_ids[0], 
        "perception",
        metadata={"task": "image_recognition"}
    )
    
    # Add child blocks (binary tree structure)
    child1_id = protocol.add_child_block(
        root_id, 
        agent_ids[0],
        "feature_extraction"
    )
    
    child2_id = protocol.add_child_block(
        root_id, 
        agent_ids[1],
        "pattern_matching"
    )
    
    # Add training data to blocks
    logger.info("Adding training data")
    protocol.add_training_data(
        child1_id,
        "Feature vector [0.2, 0.8, 0.3, 0.9] extracted from input",
        "feature_vector"
    )
    
    # Demonstrate LLM call recording
    protocol.add_llm_call(
        child2_id,
        "Analyze the pattern in feature vector [0.2, 0.8, 0.3, 0.9]",
        "The vector indicates a high activation in dimensions 2 and 4, suggesting object type B."
    )
    
    # Initialize retrograde learner
    logger.info("Initializing retrograde learner")
    learner = RetrogradeLearner(dimensions=[10, 10], geometry="hyperbolic")
    
    # Perform learning updates
    logger.info("Performing retrograde learning")
    learner.backpropagate((2, 4), 0.9, propagation_depth=2)
    learner.backpropagate((2, 5), 0.7, propagation_depth=1)
    
    # Recall learned values
    recall_result = learner.recall((2, 4))
    logger.info(f"Recall result: value={recall_result['value']:.2f}, "
                f"confidence={recall_result['recall_confidence']:.2f}")
    
    # Demonstrate heap consensus
    logger.info("Demonstrating factorial voting consensus")
    consensus = FactorialVotingConsensus(consensus_threshold=0.6, mining_difficulty=1)
    
    # Register voters with weights
    for i, agent_id in enumerate(agent_ids):
        consensus.register_voter(agent_id, weight=1.0 / (i + 1))
    
    # Submit votes
    vote_proposals = ["object_type_B", "object_type_A", "object_type_B"]
    vote_confidences = [0.9, 0.7, 0.85]
    
    for i, agent_id in enumerate(agent_ids):
        success, msg = consensus.submit_vote(
            agent_id, 
            vote_proposals[i], 
            vote_confidences[i]
        )
        logger.info(f"Vote from {agent_id}: {msg}")
    
    # Check consensus result
    status = consensus.get_consensus_status()
    logger.info(f"Consensus reached: {status['consensus_reached']}")
    if status['consensus_reached']:
        logger.info(f"Result: {status['consensus_result']} with " 
                   f"{status['consensus_details']['consensus_ratio']:.1%} support")
    
    # Register consensus report in memory tree
    if status['consensus_reached']:
        protocol.register_consensus_report(
            root_id,
            f"Consensus achieved: {status['consensus_result']}",
            consensus.get_top_votes()
        )
    
    # Verify chain integrity
    is_valid, memory_path = protocol.verify_chain_integrity(child2_id)
    logger.info(f"Memory chain verification: {'Valid' if is_valid else 'Invalid'}")
    logger.info(f"Memory path length: {len(memory_path)}")
    
    # Clean up
    protocol.memory_tree.close()
    logger.info("PARE demonstration completed")


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="PARE Protocol Demo")
    parser.add_argument("--db", default="pare_demo.db", help="Database path")
    parser.add_argument("--rpc", default="http://localhost:8081", help="RPC server URL")
    args = parser.parse_args()
    
    run_demo(args.db, args.rpc)
