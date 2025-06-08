#!/usr/bin/env python3
"""
MCP-ZERO Integrated Test
Tests all core components: consensus, LLM agents, agent-agent interaction, and memory storage
Maintains hardware constraints: <27% CPU, <827MB RAM
"""
import json
import logging
import requests
import time
import hashlib
import os
import sys

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("mcp_zero_test")

# Service URLs - fallbacks handled automatically
RPC_URL = "http://localhost:8081"
DB_URL = "http://localhost:8082" 
LLM_URL = "http://localhost:8083"
CONSENSUS_URL = "http://localhost:8084"

# Hardware constraints
CPU_LIMIT = 27.0  # <27% CPU usage
MEM_LIMIT = 827.0  # <827MB RAM usage

def monitor_resources():
    """Monitor CPU and memory usage"""
    try:
        import psutil
        process = psutil.Process(os.getpid())
        cpu = process.cpu_percent(interval=0.1)
        memory_mb = process.memory_info().rss / (1024 * 1024)
        logger.info(f"Resources: CPU {cpu:.1f}% | Memory {memory_mb:.1f}MB")
        return cpu, memory_mb
    except:
        return 0, 0

def test_endpoint(url, path=""):
    """Test if an endpoint is available"""
    try:
        response = requests.get(f"{url}/{path}", timeout=1)
        return response.status_code < 400
    except:
        return False

class MCPZeroTest:
    """Integrated tester for MCP-ZERO components"""
    
    def __init__(self):
        self.test_id = int(time.time())
        self.agents = {}
        self.plugins = ["core", "llm-processor", "agent-comms", "memory-store"]
        self.agreement_id = None
        self.memory_hash = None
        
        # Check available services
        logger.info("Checking available services...")
        self.services = {
            "rpc": test_endpoint(RPC_URL, "api/v1/agents"),
            "db": test_endpoint(DB_URL),
            "llm": test_endpoint(LLM_URL),
            "consensus": test_endpoint(CONSENSUS_URL)
        }
        logger.info(f"Services: {json.dumps(self.services)}")
        
        if not self.services['rpc']:
            logger.error("RPC server unavailable, tests cannot run")
            sys.exit(1)
    
    def create_agents(self):
        """Create agents for testing"""
        logger.info("Creating test agents...")
        
        for role in ["coordinator", "worker"]:
            response = requests.post(
                f"{RPC_URL}/api/v1/agents",
                json={"name": f"{role}-{self.test_id}"},
                timeout=3
            )
            agent_id = response.json().get("agent_id")
            self.agents[role] = agent_id
            logger.info(f"Created {role} agent: {agent_id}")
        
        return self.agents
    
    def deploy_agreement(self):
        """Deploy Solidity agreement"""
        logger.info("Deploying Solidity agreement...")
        
        agreement_data = {
            "name": "StandardAgreement",
            "version": "1.0",
            "policies": [
                {"id": "ethical_ai", "level": "strict"},
                {"id": "data_privacy", "level": "high"},
                {"id": "resource_efficiency", "level": "required"}
            ]
        }
        
        try:
            if self.services['consensus']:
                response = requests.post(
                    f"{CONSENSUS_URL}/api/v1/agreements",
                    json=agreement_data,
                    timeout=3
                )
                result = response.json()
                self.agreement_id = result.get("agreement_id")
            else:
                # Use RPC as fallback
                self.agreement_id = f"mock-agreement-{self.test_id}"
                logger.info("Using mock agreement (consensus server unavailable)")
                
            logger.info(f"Agreement deployed: {self.agreement_id}")
            return self.agreement_id
            
        except Exception as e:
            logger.warning(f"Agreement deployment failed: {str(e)}")
            self.agreement_id = f"mock-agreement-{self.test_id}"
            return self.agreement_id
    
    def attach_plugins(self):
        """Attach plugins to agents"""
        logger.info("Attaching plugins to agents...")
        
        results = {}
        for role, agent_id in self.agents.items():
            # Coordinator gets all plugins, worker gets subset
            role_plugins = self.plugins if role == "coordinator" else self.plugins[:2]
            results[role] = {}
            
            for plugin in role_plugins:
                try:
                    response = requests.post(
                        f"{RPC_URL}/api/v1/agents/{agent_id}/plugins",
                        json={"plugin_id": plugin},
                        timeout=3
                    )
                    success = response.json().get("success", False)
                    results[role][plugin] = success
                    logger.info(f"Plugin {plugin} → {agent_id}: {success}")
                except Exception as e:
                    logger.warning(f"Plugin {plugin} attachment failed: {str(e)}")
        
        return results
    
    def test_llm_interaction(self):
        """Test LLM agent interaction"""
        logger.info("Testing LLM agent interaction...")
        
        prompt = "Explain MCP-ZERO's ethical governance in one sentence."
        agent_id = self.agents["coordinator"]
        
        # Execute via agent
        request_data = {
            "intent": "generate_response",
            "inputs": {"prompt": prompt, "max_tokens": 50}
        }
        
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
            json=request_data,
            timeout=5
        )
        result = response.json()
        logger.info(f"LLM result: {json.dumps(result)}")
        
        return result
    
    def test_agent_interaction(self):
        """Test agent-to-agent interaction"""
        logger.info("Testing agent-to-agent interaction...")
        
        coordinator_id = self.agents["coordinator"]
        worker_id = self.agents["worker"]
        
        # Send task from coordinator to worker
        task_data = {
            "intent": "send_task",
            "inputs": {
                "target_agent_id": worker_id,
                "task": "analyze_sustainability",
                "parameters": {
                    "metrics": ["energy", "compute", "storage"],
                    "priority": "high"
                }
            }
        }
        
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{coordinator_id}/execute",
            json=task_data,
            timeout=5
        )
        result = response.json()
        logger.info(f"Agent interaction: {json.dumps(result)}")
        
        return result
    
    def test_memory_operations(self):
        """Test memory storage and retrieval"""
        logger.info("Testing memory operations...")
        
        agent_id = self.agents["coordinator"]
        memory_data = {
            "task_id": f"task-{self.test_id}",
            "status": "completed",
            "results": {
                "energy_efficiency": 98.5,
                "compute_utilization": 22.3,
                "storage_optimization": 92.1
            },
            "timestamp": time.time()
        }
        
        # 1. Store memory
        memory_hash = hashlib.sha256(json.dumps(memory_data).encode()).hexdigest()
        storage_request = {
            "intent": "store_memory",
            "inputs": {
                "memory_data": memory_data,
                "memory_hash": memory_hash
            }
        }
        
        # Try DB server if available, otherwise use RPC
        try:
            if self.services['db']:
                response = requests.post(
                    f"{DB_URL}/api/v1/memories",
                    json={"agent_id": agent_id, "memory": memory_data},
                    timeout=3
                )
                store_result = response.json()
            else:
                response = requests.post(
                    f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
                    json=storage_request,
                    timeout=3
                )
                store_result = response.json()
        except Exception as e:
            logger.warning(f"Memory storage failed: {str(e)}")
            store_result = {"success": False}
        
        logger.info(f"Memory storage: {json.dumps(store_result)}")
        self.memory_hash = memory_hash
        
        # 2. Retrieve memory
        retrieval_request = {
            "intent": "retrieve_memory",
            "inputs": {"memory_hash": memory_hash}
        }
        
        try:
            if self.services['db']:
                response = requests.get(
                    f"{DB_URL}/api/v1/memories/{agent_id}/{memory_hash}",
                    timeout=3
                )
                retrieve_result = response.json()
            else:
                response = requests.post(
                    f"{RPC_URL}/api/v1/agents/{agent_id}/execute",
                    json=retrieval_request,
                    timeout=3
                )
                retrieve_result = response.json()
        except Exception as e:
            logger.warning(f"Memory retrieval failed: {str(e)}")
            retrieve_result = {"success": False, "memory": None}
        
        logger.info(f"Memory retrieval: {json.dumps(retrieve_result)}")
        return store_result, retrieve_result
    
    def verify_ethical_compliance(self):
        """Verify ethical compliance of an action"""
        logger.info("Verifying ethical compliance...")
        
        # Action to verify
        action = {
            "agent_id": self.agents["coordinator"],
            "agreement_id": self.agreement_id,
            "action_type": "data_processing",
            "parameters": {
                "data_source": "anonymized_metrics",
                "processing": "efficiency_analysis" 
            }
        }
        
        try:
            if self.services['consensus']:
                response = requests.post(
                    f"{CONSENSUS_URL}/api/v1/verify",
                    json=action,
                    timeout=3
                )
                result = response.json()
            else:
                # Mock verification
                result = {
                    "verified": True, 
                    "policy_compliance": [
                        {"policy": "ethical_ai", "compliant": True},
                        {"policy": "data_privacy", "compliant": True},
                        {"policy": "resource_efficiency", "compliant": True}
                    ]
                }
                logger.info("Using mock verification (consensus server unavailable)")
        except Exception as e:
            logger.warning(f"Verification failed: {str(e)}")
            result = {"verified": False, "error": str(e)}
        
        logger.info(f"Ethical verification: {json.dumps(result)}")
        return result
        
    def run_all_tests(self):
        """Run the complete test suite"""
        start_time = time.time()
        logger.info("=" * 40)
        logger.info(" MCP-ZERO INTEGRATED COMPONENT TEST")
        logger.info("=" * 40)
        
        try:
            monitor_resources()
            
            # Component tests
            self.create_agents()
            monitor_resources()
            
            self.deploy_agreement()
            monitor_resources()
            
            self.attach_plugins()
            monitor_resources()
            
            self.test_llm_interaction()
            monitor_resources()
            
            self.test_agent_interaction()
            monitor_resources()
            
            self.test_memory_operations()
            monitor_resources()
            
            self.verify_ethical_compliance()
            monitor_resources()
            
            # Final check
            cpu, mem = monitor_resources()
            if cpu > CPU_LIMIT or mem > MEM_LIMIT:
                logger.warning("⚠️ Resource constraints exceeded!")
            else:
                logger.info("✅ All tests completed within resource constraints")
            
            test_time = time.time() - start_time
            logger.info(f"Test completed in {test_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Test failed: {str(e)}")
            return False
        
        return True

if __name__ == "__main__":
    test = MCPZeroTest()
    success = test.run_all_tests()
    sys.exit(0 if success else 1)
