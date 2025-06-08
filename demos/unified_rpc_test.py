#!/usr/bin/env python3
"""
MCP-ZERO Unified RPC Test Script
Tests all functionality through the unified RPC server interface
"""
import json
import logging
import requests
import time
import os
import hashlib

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("mcp_zero_test")

# Single RPC server handles all functionality
RPC_URL = "http://localhost:8081"

class MCPZeroTest:
    """Tests all MCP-ZERO functionality via RPC server"""
    
    def __init__(self):
        self.test_id = int(time.time())
        self.agent_id = None
        self.agreement_id = None
        self.memory_id = None
        
        logger.info("=" * 40)
        logger.info(" MCP-ZERO UNIFIED RPC TEST")
        logger.info("=" * 40)
    
    def test_agent_lifecycle(self):
        """Test agent lifecycle operations"""
        logger.info("Testing agent lifecycle...")
        
        # Create agent
        logger.info("Creating agent...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents",
            json={"name": f"test-agent-{self.test_id}"},
            timeout=3
        )
        agent_data = response.json()
        self.agent_id = agent_data.get("agent_id")
        logger.info(f"Created agent: {self.agent_id}")
        
        # Get agent details
        logger.info("Getting agent details...")
        response = requests.get(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}",
            timeout=3
        )
        details = response.json()
        logger.info(f"Agent details: {json.dumps(details, indent=2)}")
        
        return True
    
    def test_plugin_system(self):
        """Test plugin attachment and management"""
        logger.info("Testing plugin system...")
        
        plugins = ["core", "document-analyzer", "llm-processor", "memory-store"]
        results = {}
        
        for plugin in plugins:
            logger.info(f"Attaching plugin: {plugin}")
            response = requests.post(
                f"{RPC_URL}/api/v1/agents/{self.agent_id}/plugins",
                json={"plugin_id": plugin},
                timeout=3
            )
            result = response.json()
            success = result.get("success", False)
            results[plugin] = success
            logger.info(f"Plugin {plugin} attachment: {success}")
        
        return all(results.values())
    
    def test_agreement_system(self):
        """Test agreement/consensus functionality"""
        logger.info("Testing agreement system...")
        
        # Create agreement via RPC
        agreement_data = {
            "intent": "create_agreement",
            "inputs": {
                "name": "StandardAgreement",
                "policies": [
                    {"id": "ethical_ai", "level": "strict"},
                    {"id": "data_privacy", "level": "high"}
                ]
            }
        }
        
        logger.info("Creating agreement...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=agreement_data,
            timeout=3
        )
        result = response.json()
        
        # Extract agreement ID from result
        if result.get("success", False):
            # In a real system, the agreement ID would be in the result
            # For mock, we'll generate one
            self.agreement_id = f"agreement-{self.test_id}"
            logger.info(f"Agreement created: {self.agreement_id}")
        else:
            logger.warning("Agreement creation failed")
            return False
            
        # Test consensus verification
        verification_data = {
            "intent": "verify_action",
            "inputs": {
                "agreement_id": self.agreement_id,
                "action": "process_data",
                "parameters": {"data_source": "public", "processing_type": "analytics"}
            }
        }
        
        logger.info("Verifying action against agreement...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=verification_data,
            timeout=3
        )
        verification = response.json()
        logger.info(f"Verification result: {json.dumps(verification, indent=2)}")
        
        return verification.get("success", False)
    
    def test_llm_functionality(self):
        """Test LLM functionality"""
        logger.info("Testing LLM functionality...")
        
        # LLM request via agent intent
        llm_request = {
            "intent": "generate_text",
            "inputs": {
                "prompt": "Explain MCP-ZERO in one sentence.",
                "max_tokens": 30
            }
        }
        
        logger.info("Generating text via LLM...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=llm_request,
            timeout=5
        )
        result = response.json()
        logger.info(f"LLM result: {json.dumps(result, indent=2)}")
        
        return result.get("success", False)
    
    def test_memory_operations(self):
        """Test memory storage and retrieval"""
        logger.info("Testing memory operations...")
        
        # Memory data to store
        memory_data = {
            "task_id": f"task-{self.test_id}",
            "status": "completed",
            "results": {
                "analysis": "Success",
                "metrics": {
                    "energy_efficiency": 98.5,
                    "compute_utilization": 22.3
                }
            },
            "timestamp": time.time()
        }
        
        # Generate hash for traceability
        memory_hash = hashlib.sha256(json.dumps(memory_data).encode()).hexdigest()
        
        # Store memory
        store_request = {
            "intent": "store_memory",
            "inputs": {
                "memory_data": memory_data,
                "memory_hash": memory_hash
            }
        }
        
        logger.info("Storing memory...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=store_request,
            timeout=3
        )
        store_result = response.json()
        logger.info(f"Memory storage result: {json.dumps(store_result, indent=2)}")
        
        # Retrieve memory
        retrieve_request = {
            "intent": "retrieve_memory",
            "inputs": {
                "memory_hash": memory_hash
            }
        }
        
        logger.info("Retrieving memory...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=retrieve_request,
            timeout=3
        )
        retrieve_result = response.json()
        logger.info(f"Memory retrieval result: {json.dumps(retrieve_result, indent=2)}")
        
        return store_result.get("success", False) and retrieve_result.get("success", False)
    
    def test_agent_interaction(self):
        """Test agent-to-agent interaction"""
        logger.info("Testing agent-to-agent interaction...")
        
        # Create second agent
        logger.info("Creating second agent...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents",
            json={"name": f"target-agent-{self.test_id}"},
            timeout=3
        )
        target_agent_data = response.json()
        target_agent_id = target_agent_data.get("agent_id")
        logger.info(f"Created target agent: {target_agent_id}")
        
        # Send message between agents
        message_request = {
            "intent": "send_message",
            "inputs": {
                "target_agent_id": target_agent_id,
                "message": {
                    "content": "Request for sustainability analysis",
                    "priority": "high"
                }
            }
        }
        
        logger.info(f"Sending message from {self.agent_id} to {target_agent_id}...")
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{self.agent_id}/execute",
            json=message_request,
            timeout=3
        )
        result = response.json()
        logger.info(f"Message delivery result: {json.dumps(result, indent=2)}")
        
        return result.get("success", False)
    
    def run_all_tests(self):
        """Run all tests in sequence"""
        start_time = time.time()
        results = {}
        
        try:
            # Test agent creation and lifecycle
            results["agent_lifecycle"] = self.test_agent_lifecycle()
            
            # Test plugin system
            results["plugin_system"] = self.test_plugin_system()
            
            # Test agreement system
            results["agreement_system"] = self.test_agreement_system()
            
            # Test LLM functionality
            results["llm_functionality"] = self.test_llm_functionality()
            
            # Test memory operations
            results["memory_operations"] = self.test_memory_operations()
            
            # Test agent interaction
            results["agent_interaction"] = self.test_agent_interaction()
            
        except Exception as e:
            logger.error(f"Test error: {str(e)}")
            return False
        
        # Report results
        logger.info("=" * 40)
        logger.info(" TEST RESULTS")
        logger.info("=" * 40)
        
        all_passed = True
        for test_name, passed in results.items():
            status = "✅ PASSED" if passed else "❌ FAILED"
            logger.info(f"{test_name}: {status}")
            all_passed = all_passed and passed
        
        test_time = time.time() - start_time
        logger.info(f"Test completed in {test_time:.2f} seconds")
        
        if all_passed:
            logger.info("✅ All tests PASSED")
        else:
            logger.info("❌ Some tests FAILED")
        
        return all_passed

if __name__ == "__main__":
    test = MCPZeroTest()
    success = test.run_all_tests()
    # Exit with status code based on test results
    exit(0 if success else 1)
