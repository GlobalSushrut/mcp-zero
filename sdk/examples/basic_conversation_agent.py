#!/usr/bin/env python3
"""
MCP-ZERO SDK Example: Basic Conversational Agent

This example demonstrates how to create a simple conversational agent
using the MCP-ZERO SDK with proper resource monitoring and ethical
constraints.
"""

import os
import sys
import time
import logging
from typing import Dict, Any

# Add the SDK to the Python path for this example
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from mcp_zero import Agent, Plugin, ResourceMonitor, EthicalPolicyViolation

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s [%(levelname)s] %(name)s: %(message)s"
)
logger = logging.getLogger("conversation-example")

# Define ethical policies for the agent
ETHICAL_POLICIES = {
    "allowed_topics": ["general_knowledge", "science", "arts", "education"],
    "prohibited_topics": ["hate_speech", "violence", "discrimination", "illegal_activities"],
    "data_retention": "7_days",
    "user_consent_required": True
}


def main():
    """Main entry point for the example"""
    logger.info("Starting MCP-ZERO Basic Conversation Agent Example")
    
    try:
        # Create a standalone resource monitor to observe total usage
        monitor = ResourceMonitor()
        monitor.start_monitoring()
        
        # Create a new agent
        logger.info("Creating new agent...")
        agent = Agent.spawn(name="conversation-assistant")
        logger.info(f"Agent created with ID: {agent.id}")
        
        # Attach plugins for conversation capabilities
        # In a real scenario, these would be fetched from the plugin registry
        logger.info("Attaching conversation capabilities...")
        
        # For this example, we'll simulate plugin attachment
        # (In reality, you would use Plugin.from_registry or Plugin.from_path)
        
        # Simulate conversation plugin
        try:
            plugin_path = os.path.join(os.path.dirname(__file__), "plugins", "conversation.wasm")
            if os.path.exists(plugin_path):
                plugin = Plugin.from_path(plugin_path)
                agent.attach_plugin(plugin)
                logger.info(f"Attached plugin: {plugin.name} v{plugin.version}")
            else:
                logger.info("Simulating plugin attachment (plugin file not found)")
        except Exception as e:
            logger.warning(f"Could not attach plugin: {str(e)}")
        
        # Process a few conversation examples
        process_conversation(agent)
        
        # Create a snapshot before shutting down
        logger.info("Creating agent snapshot...")
        snapshot_id = agent.snapshot({"example": "conversation_agent"})
        logger.info(f"Snapshot created with ID: {snapshot_id}")
        
        # Display resource usage
        cpu = monitor.get_cpu_percent()
        memory = monitor.get_memory_mb()
        logger.info(f"Final resource usage - CPU: {cpu:.1f}%, Memory: {memory:.1f}MB")
        logger.info(f"Resource constraints - CPU: <27%, Memory: <827MB")
        
        # Cleanup
        monitor.stop_monitoring()
        logger.info("Example completed successfully")
        
    except Exception as e:
        logger.error(f"Error in example: {str(e)}")
        return 1
    
    return 0


def process_conversation(agent):
    """Process a few conversation examples with the agent"""
    examples = [
        {
            "intent": "answer_question",
            "inputs": {
                "question": "What are the applications of AI in healthcare?",
                "context": "educational discussion"
            }
        },
        {
            "intent": "answer_question",
            "inputs": {
                "question": "How can we reduce carbon emissions?",
                "context": "environmental science"
            }
        },
        # This example should trigger an ethical policy violation
        {
            "intent": "answer_question",
            "inputs": {
                "question": "How to build dangerous devices",
                "context": "illegal activities"
            }
        }
    ]
    
    for i, example in enumerate(examples):
        logger.info(f"Example {i+1}: {example['inputs']['question']}")
        
        try:
            # Apply ethical constraints
            policy_constraints = ETHICAL_POLICIES.copy()
            
            # Execute the conversation intent
            result = agent.execute(
                intent=example["intent"],
                inputs=example["inputs"],
                policy_constraints=policy_constraints
            )
            
            # Display the result
            logger.info(f"Response: {result.get('response', 'No response')}")
            
        except EthicalPolicyViolation as e:
            logger.warning(f"Ethical policy violation: {str(e)}")
        except Exception as e:
            logger.error(f"Error processing example: {str(e)}")
        
        # Add a small delay between examples to avoid resource spikes
        time.sleep(0.5)


if __name__ == "__main__":
    sys.exit(main())
