#!/usr/bin/env python3
"""
MCP-ZERO Integrated Agent Demo
Demonstrates a full-stack agent using all MCP-ZERO infrastructure components

Hardware constraints: <27% CPU, <827MB RAM
"""

import os
import sys
import json
import time
import logging
import requests
from typing import Dict, Any, Optional, List

# Import MCP-ZERO client components
from mcp_rpc_client import RPCClient
from mcp_db_client import DBClient
from mcp_llm_client import LLMClient
from mcp_agreement_client import AgreementClient

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s'
)
logger = logging.getLogger("mcp_zero_demo")

# Constants
RPC_SERVER_URL = "http://localhost:8081"
DB_SERVER_URL = "http://localhost:8082"
LLM_SERVER_URL = "http://localhost:8083" 
CONSENSUS_SERVER_URL = "http://localhost:8084"
AGREEMENT_SERVER_URL = "http://localhost:8085"

# Hardware constraints
CPU_LIMIT = 27.0  # <27% CPU usage
MEM_LIMIT = 827.0  # <827MB RAM usage

def get_resource_usage():
    """Monitor resource usage to ensure we stay within hardware constraints"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        
        # Get CPU usage (short interval for quick measurement)
        cpu_percent = process.cpu_percent(interval=0.1)
        
        # Get memory usage in MB
        memory_mb = process.memory_info().rss / (1024 * 1024)
        
        return cpu_percent, memory_mb
    except ImportError:
        logger.warning("psutil not available, resource monitoring disabled")
        return 0.0, 0.0

def check_constraints():
    """Check if we're within hardware constraints"""
    cpu, mem = get_resource_usage()
    logger.info(f"Resource usage: CPU {cpu:.1f}%, Memory {mem:.1f}MB")
    
    if cpu > CPU_LIMIT:
        logger.warning(f"CPU usage exceeds limit: {cpu:.1f}% > {CPU_LIMIT}%")
    
    if mem > MEM_LIMIT:
        logger.warning(f"Memory usage exceeds limit: {mem:.1f}MB > {MEM_LIMIT}MB")
        
    return cpu <= CPU_LIMIT and mem <= MEM_LIMIT

class IntegratedAgent:
    """Integrated MCP-ZERO Agent using all infrastructure components"""
    
    def __init__(self, name: str):
        """Initialize the integrated agent"""
        self.name = name
        self.agent_id = None
        self.agreement_id = None
        
        # Initialize all clients
        self.rpc = RPCClient(RPC_SERVER_URL)
        self.db = DBClient(DB_SERVER_URL)
        self.llm = LLMClient(LLM_SERVER_URL)
        self.agreement = AgreementClient(AGREEMENT_SERVER_URL, CONSENSUS_SERVER_URL)
        
        logger.info(f"Initialized IntegratedAgent '{name}'")
        check_constraints()
    
    def setup(self) -> bool:
        """Set up the agent with all components"""
        try:
            # Step 1: Spawn agent through RPC server
            logger.info("Step 1: Spawning agent through RPC server...")
            self.agent_id = self.rpc.spawn_agent(self.name)
            check_constraints()
            
            # Step 2: Create ethical policy agreement
            logger.info("Step 2: Creating ethical policy agreement...")
            policy_rules = [
                {"rule": "no_harmful_content", "level": "strict"},
                {"rule": "maintain_privacy", "level": "high"},
                {"rule": "respect_user_boundaries", "level": "required"}
            ]
            self.agreement_id = self.agreement.create_agreement(self.agent_id, policy_rules)
            check_constraints()
            
            # Step 3: Register agent state in database
            logger.info("Step 3: Registering agent state in database...")
            initial_state = {
                "name": self.name,
                "agent_id": self.agent_id,
                "agreement_id": self.agreement_id,
                "created_at": time.time(),
                "status": "active"
            }
            self.db.store_agent_state(self.agent_id, initial_state)
            check_constraints()
            
            # Step 4: Attach required plugins
            logger.info("Step 4: Attaching required plugins...")
            plugins = ["document-analyzer", "ethics-validator", "nlp-processor"]
            
            for plugin_id in plugins:
                # Verify plugin against ethical agreement
                verification = self.agreement.verify_action(
                    self.agent_id, 
                    "attach_plugin", 
                    {"plugin_id": plugin_id}
                )
                
                if verification.get("approved", False):
                    # Record consensus
                    self.agreement.record_consensus(
                        self.agreement_id, 
                        verification.get("action_hash", "")
                    )
                    
                    # Attach plugin via RPC server
                    self.rpc.attach_plugin(self.agent_id, plugin_id)
                    
                    logger.info(f"Successfully attached and verified plugin: {plugin_id}")
                else:
                    logger.warning(f"Plugin {plugin_id} failed ethical verification")
            
            check_constraints()
            return True
            
        except Exception as e:
            logger.error(f"Agent setup failed: {str(e)}")
            return False
    
    def process_document(self, document: str) -> Dict[str, Any]:
        """Process a document using the integrated agent"""
        logger.info(f"Processing document: '{document[:30]}...'")
        results = {}
        
        try:
            # Step 1: Verify action with ethical agreement
            verification = self.agreement.verify_action(
                self.agent_id,
                "process_document",
                {"document": document[:100]}
            )
            
            if not verification.get("approved", False):
                logger.warning("Document processing not approved by ethical agreement")
                return {"error": "Action not approved by ethical agreement"}
            
            # Record consensus
            self.agreement.record_consensus(
                self.agreement_id,
                verification.get("action_hash", "")
            )
            
            # Step 2: Use LLM to analyze document content
            logger.info("Analyzing document with LLM...")
            llm_analysis = self.llm.analyze_document(
                document,
                task="summarize_and_extract_key_points"
            )
            results["llm_analysis"] = llm_analysis
            check_constraints()
            
            # Step 3: Extract entities using LLM
            logger.info("Extracting entities from document...")
            entities = self.llm.extract_entities(document)
            results["entities"] = entities
            check_constraints()
            
            # Step 4: Execute intent on RPC server
            logger.info("Executing document analysis intent via RPC...")
            execution_result = self.rpc.execute_intent(
                self.agent_id,
                "analyze_document",
                {"text": document, "entities": entities}
            )
            results["execution_result"] = execution_result
            check_constraints()
            
            # Step 5: Store results in database
            logger.info("Storing analysis results in database...")
            trace_id = self.db.store_execution_trace(
                self.agent_id,
                "process_document",
                {
                    "document_hash": self._hash_text(document),
                    "results": results,
                    "timestamp": time.time()
                }
            )
            results["trace_id"] = trace_id
            check_constraints()
            
            return results
            
        except Exception as e:
            logger.error(f"Document processing error: {str(e)}")
            return {"error": str(e)}
    
    def _hash_text(self, text: str) -> str:
        """Create a hash of text for privacy preservation"""
        import hashlib
        return hashlib.sha256(text.encode('utf-8')).hexdigest()


def run_consensus_validation():
    """Run a separate consensus validation on the agreement server"""
    logger.info("Running Solidity agreement consensus validation")
    try:
        # Initialize consensus client
        consensus = AgreementClient(AGREEMENT_SERVER_URL, CONSENSUS_SERVER_URL)
        
        # Example policy validation
        policy_rules = [
            {"rule": "no_harmful_content", "level": "strict"},
            {"rule": "respect_intellectual_property", "level": "high"}
        ]
        
        # Create mock agreement for validation
        agreement_id = consensus.create_agreement("test-agent-id", policy_rules)
        
        # Test action verification
        verification = consensus.verify_action(
            "test-agent-id",
            "process_text",
            {"content": "This is a test document for consensus validation."}
        )
        
        # Record consensus
        if verification.get("approved", False):
            success = consensus.record_consensus(
                agreement_id,
                verification.get("action_hash", "")
            )
            logger.info(f"Consensus validation {'succeeded' if success else 'failed'}")
        
        check_constraints()
        return True
    except Exception as e:
        logger.error(f"Consensus validation failed: {str(e)}")
        return False


def main():
    """Main function to run the integrated agent demo"""
    start_time = time.time()
    logger.info("-" * 80)
    logger.info("MCP-ZERO INTEGRATED AGENT DEMO")
    logger.info("-" * 80)
    
    initial_cpu, initial_mem = get_resource_usage()
    logger.info(f"Initial resource usage: CPU {initial_cpu:.1f}%, Memory {initial_mem:.1f}MB")
    
    try:
        # 1. Create and setup integrated agent
        agent = IntegratedAgent("mcp-zero-demo-agent")
        
        if not agent.setup():
            logger.error("Agent setup failed, exiting")
            return 1
        
        logger.info("Agent setup completed successfully")
        logger.info(f"Agent ID: {agent.agent_id}")
        logger.info(f"Agreement ID: {agent.agreement_id}")
        
        # 2. Run independent Solidity agreement consensus validation
        if not run_consensus_validation():
            logger.warning("Solidity consensus validation failed, continuing with demo")
        
        # 3. Process a sample document
        sample_document = """
        MCP-ZERO is an AI agent infrastructure designed for 100+ year sustainability.
        It features a plugin-based architecture with ethical governance built-in. 
        The system operates under strict hardware constraints: <27% CPU usage and <827MB RAM.
        All agent actions are traceable and verifiable through cryptographic mechanisms.
        """
        
        logger.info("Processing sample document...")
        results = agent.process_document(sample_document)
        
        logger.info("Document processing results:")
        logger.info(json.dumps(results, indent=2))
        
        # 4. Verify agent state in database
        logger.info("Verifying agent state in database...")
        agent_state = agent.db.retrieve_agent_state(agent.agent_id)
        logger.info(f"Retrieved agent state: {agent_state}")
        
        # 5. Measure final resource usage
        final_cpu, final_mem = get_resource_usage()
        logger.info(f"Final resource usage: CPU {final_cpu:.1f}%, Memory {final_mem:.1f}MB")
        
        # 6. Report execution time
        total_time = time.time() - start_time
        logger.info(f"Total execution time: {total_time:.2f} seconds")
        
        # 7. Verify constraints were met
        if final_cpu <= CPU_LIMIT and final_mem <= MEM_LIMIT:
            logger.info("✅ All hardware constraints satisfied!")
        else:
            logger.warning("❌ Some hardware constraints were exceeded")
        
        return 0
    
    except Exception as e:
        logger.error(f"Demo failed with error: {str(e)}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
