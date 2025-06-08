#!/usr/bin/env python3
"""
MCP-ZERO Internal Agreement System Demo
Demonstrates how MCP-ZERO uses Solidity-inspired agreements internally for agent consensus
"""
import json
import logging
import requests
import time
import hashlib
import sys
import os
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("agreement_demo")

# Server URLs - RPC server is the single point of access
RPC_URL = "http://localhost:8082"

class SolidityAgreementDemo:
    """
    Demonstrates MCP-ZERO's internal Solidity-inspired agreement system
    """
    
    def __init__(self):
        self.demo_id = int(time.time())
        self.agent_ids = {}
        self.agreement_id = None
    
    def create_agreement_template(self) -> Dict[str, Any]:
        """
        Create a Solidity-inspired agreement template in MCP-ZERO's internal format
        """
        logger.info("Creating Solidity-inspired agreement template...")
        
        # This mimics Solidity contract structure but is purely internal to MCP-ZERO
        agreement_template = {
            "name": "AgentConsensusAgreement",
            "version": "1.0.0",
            "timestamp": int(time.time()),
            "parties": {
                "provider": self.agent_ids.get("provider", "provider-default"),
                "consumer": self.agent_ids.get("consumer", "consumer-default")
            },
            "terms": {
                "ethical_constraints": [
                    {"id": "data_privacy", "level": "strict"},
                    {"id": "resource_efficiency", "level": "moderate"},
                    {"id": "harm_prevention", "level": "required"}
                ],
                "operational_limits": {
                    "max_cpu_percent": 27,
                    "max_memory_mb": 827,
                    "max_daily_api_calls": 10000
                }
            },
            "functions": {
                "verify_action": {
                    "parameters": ["action_type", "parameters"],
                    "returns": "bool",
                    "conditions": [
                        "require(parameters.data_source != 'personal_information' || parameters.consent == true)",
                        "require(parameters.purpose != 'surveillance')",
                        "require(getResourceUsage() <= operational_limits.max_cpu_percent)"
                    ]
                },
                "log_action": {
                    "parameters": ["action_type", "parameters", "result"],
                    "returns": "bytes32",
                    "implementation": "return keccak256(abi.encodePacked(action_type, parameters, result, block.timestamp));"
                }
            }
        }
        
        logger.info(f"Created agreement template: {json.dumps(agreement_template, indent=2)}")
        return agreement_template
    
    def create_agents(self):
        """Create agents for the agreement demonstration"""
        logger.info("Creating agents for the agreement demo...")
        
        for role in ["provider", "consumer"]:
            try:
                response = requests.post(
                    f"{RPC_URL}/api/v1/agents", 
                    json={"name": f"{role}-agent-{self.demo_id}"},
                    timeout=3
                )
                agent_id = response.json().get("agent_id")
                self.agent_ids[role] = agent_id
                logger.info(f"Created {role} agent with ID: {agent_id}")
                
            except Exception as e:
                logger.error(f"Error creating {role} agent: {str(e)}")
                self.agent_ids[role] = f"{role}-agent-{self.demo_id}"
        
        return self.agent_ids
    
    def register_agreement(self, template: Dict[str, Any]):
        """
        Register the Solidity-inspired agreement in MCP-ZERO's internal consensus system
        """
        logger.info("Registering agreement in MCP-ZERO consensus system...")
        
        try:
            # MCP-ZERO would internally convert this to a Solidity-like structure
            # but it stays within the infrastructure
            provider_id = self.agent_ids.get("provider")
            
            # Request format follows MCP-ZERO intent system
            response = requests.post(
                f"{RPC_URL}/api/v1/agents/{provider_id}/execute",
                json={
                    "intent": "register_agreement",
                    "inputs": {
                        "template": template,
                        "consumer_id": self.agent_ids.get("consumer"),
                        "verification_level": "strict"
                    }
                },
                timeout=5
            )
            
            result = response.json()
            
            if result.get("success", False):
                # In a real system, this would return the ID of the registered agreement
                # For now, simulate it
                self.agreement_id = f"agreement-{self.demo_id}"
                logger.info(f"Agreement registered successfully with ID: {self.agreement_id}")
            else:
                logger.warning(f"Agreement registration failed: {result.get('error', 'Unknown error')}")
                # Create fallback ID for testing
                self.agreement_id = f"agreement-{self.demo_id}"
            
            return self.agreement_id
            
        except Exception as e:
            logger.error(f"Error registering agreement: {str(e)}")
            # Create fallback ID for testing
            self.agreement_id = f"agreement-{self.demo_id}"
            return self.agreement_id
    
    def verify_action_against_agreement(self, action_type: str, parameters: Dict[str, Any]):
        """
        Verify an action against the internal Solidity-inspired agreement
        """
        logger.info(f"Verifying action '{action_type}' against agreement {self.agreement_id}...")
        
        try:
            consumer_id = self.agent_ids.get("consumer")
            
            # This would internally go through MCP-ZERO's verification system
            # using the Solidity-inspired agreement rules
            response = requests.post(
                f"{RPC_URL}/api/v1/agents/{consumer_id}/execute",
                json={
                    "intent": "verify_action",
                    "inputs": {
                        "agreement_id": self.agreement_id,
                        "action_type": action_type,
                        "parameters": parameters
                    }
                },
                timeout=3
            )
            
            result = response.json()
            
            # Log the result
            if result.get("success", False):
                logger.info(f"Action verification succeeded: {action_type}")
                # In a real system, this would include verification details
                self.log_action(action_type, parameters, "approved")
            else:
                logger.warning(f"Action verification failed: {action_type}")
                self.log_action(action_type, parameters, "rejected")
                
            return result
            
        except Exception as e:
            logger.error(f"Error during action verification: {str(e)}")
            return {"success": False, "error": str(e)}
    
    def log_action(self, action_type: str, parameters: Dict[str, Any], result: str):
        """
        Log the action using MCP-ZERO's internal ZK-traceable audit system
        This mimics the Solidity log_action function
        """
        # Generate a hash of the action for auditability
        # In a real Solidity system, this would be keccak256
        action_string = json.dumps({
            "action": action_type,
            "params": parameters,
            "result": result,
            "timestamp": time.time()
        })
        
        action_hash = hashlib.sha256(action_string.encode()).hexdigest()
        
        logger.info(f"Action logged with hash: 0x{action_hash}")
        
        # In real MCP-ZERO, this would be stored in the trace engine
        return f"0x{action_hash}"
    
    def run_demo(self):
        """Run the complete internal Solidity agreement demo"""
        start_time = time.time()
        logger.info("=" * 60)
        logger.info("MCP-ZERO INTERNAL SOLIDITY AGREEMENT DEMO")
        logger.info("=" * 60)
        
        try:
            # Create the necessary agents
            self.create_agents()
            
            # Create a Solidity-inspired agreement template
            agreement = self.create_agreement_template()
            
            # Register the agreement in MCP-ZERO's consensus system
            self.register_agreement(agreement)
            
            # Test a compliant action that should be approved
            compliant_action = {
                "data_source": "anonymized_data",
                "purpose": "research",
                "consent": True,
                "resource_request": {
                    "cpu_percent": 15,
                    "memory_mb": 500
                }
            }
            compliant_result = self.verify_action_against_agreement(
                "process_data", compliant_action
            )
            logger.info(f"Compliant action result: {json.dumps(compliant_result, indent=2)}")
            
            # Test a non-compliant action that should be rejected
            non_compliant_action = {
                "data_source": "personal_information",
                "purpose": "surveillance",
                "consent": False,
                "resource_request": {
                    "cpu_percent": 30,  # Exceeds limit
                    "memory_mb": 900    # Exceeds limit
                }
            }
            non_compliant_result = self.verify_action_against_agreement(
                "process_data", non_compliant_action
            )
            logger.info(f"Non-compliant action result: {json.dumps(non_compliant_result, indent=2)}")
            
            demo_time = time.time() - start_time
            logger.info(f"Demo completed in {demo_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Demo failed with error: {str(e)}")
            return False
            
        return True

if __name__ == "__main__":
    demo = SolidityAgreementDemo()
    success = demo.run_demo()
    sys.exit(0 if success else 1)
