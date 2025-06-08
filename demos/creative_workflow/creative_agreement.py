#!/usr/bin/env python3
"""
MCP-ZERO Creative Workflow Demo - Creative Agreement
Defines Solidity-inspired agreement for creative collaboration
"""
import json
import logging
import hashlib
import time
from typing import Dict, Any, List

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("creative_agreement")

class CreativeAgreement:
    """Solidity-inspired agreement for creative workflow"""
    
    def __init__(self, name="CreativeCollaboration"):
        self.name = name
        self.agreement_id = f"agreement-{int(time.time())}"
        self.parties = {}
        self.terms = {}
        self.usage_limits = {}
        self.timestamp = int(time.time())
        self.content_policies = []
        self.verification_functions = {}
        self.agreement_hash = None
    
    def add_party(self, role: str, agent_id: str) -> None:
        """Add a party to the agreement"""
        self.parties[role] = agent_id
        logger.info(f"Added party to agreement: {role} -> {agent_id}")
    
    def set_resource_limits(self, cpu_percent: int = 27, memory_mb: int = 827, 
                           storage_mb: int = 1000) -> None:
        """Set resource limits for the agreement"""
        self.usage_limits = {
            "cpu_percent": cpu_percent,
            "memory_mb": memory_mb,
            "storage_mb": storage_mb
        }
        logger.info(f"Set resource limits: CPU {cpu_percent}%, Memory {memory_mb}MB")
    
    def add_content_policy(self, policy_name: str, restrictions: List[str]) -> None:
        """Add a content policy to the agreement"""
        self.content_policies.append({
            "name": policy_name,
            "restrictions": restrictions
        })
        logger.info(f"Added content policy: {policy_name}")
    
    def set_quality_standards(self, resolution: str, framerate: int, audio_quality: str) -> None:
        """Set quality standards for the creative output"""
        self.terms["quality_standards"] = {
            "resolution": resolution,
            "framerate": framerate,
            "audio_quality": audio_quality
        }
        logger.info(f"Set quality standards: {resolution}, {framerate}fps, {audio_quality}")
    
    def add_verification_function(self, name: str, parameters: List[str], 
                                 conditions: List[str]) -> None:
        """Add a verification function to the agreement"""
        self.verification_functions[name] = {
            "parameters": parameters,
            "returns": "bool",
            "conditions": conditions
        }
        logger.info(f"Added verification function: {name}")
    
    def finalize(self) -> str:
        """Finalize the agreement and generate its hash"""
        # Compile the full agreement structure
        agreement = {
            "name": self.name,
            "agreement_id": self.agreement_id,
            "timestamp": self.timestamp,
            "parties": self.parties,
            "terms": self.terms,
            "usage_limits": self.usage_limits,
            "content_policies": self.content_policies,
            "functions": self.verification_functions
        }
        
        # Generate agreement hash - mimics Solidity keccak256 hash
        agreement_string = json.dumps(agreement, sort_keys=True)
        self.agreement_hash = "0x" + hashlib.sha256(agreement_string.encode()).hexdigest()
        
        logger.info(f"Agreement finalized with hash: {self.agreement_hash}")
        return self.agreement_hash
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert agreement to dictionary representation"""
        return {
            "name": self.name,
            "agreement_id": self.agreement_id,
            "timestamp": self.timestamp,
            "parties": self.parties,
            "terms": self.terms,
            "usage_limits": self.usage_limits,
            "content_policies": self.content_policies,
            "functions": self.verification_functions,
            "agreement_hash": self.agreement_hash
        }
    
    def verify_action(self, agent_id: str, action_type: str, 
                     parameters: Dict[str, Any]) -> bool:
        """
        Verify if an action complies with the agreement
        Simulates Solidity require() statements
        """
        # Check if agent is a party to the agreement
        agent_is_party = any(agent_id == party_id for party_id in self.parties.values())
        if not agent_is_party:
            logger.warning(f"Agent {agent_id} is not a party to the agreement")
            return False
        
        # Check resource usage compliance
        if "resource_usage" in parameters:
            cpu_usage = parameters["resource_usage"].get("cpu_percent", 0)
            memory_usage = parameters["resource_usage"].get("memory_mb", 0)
            
            if cpu_usage > self.usage_limits.get("cpu_percent", 27):
                logger.warning(f"CPU usage ({cpu_usage}%) exceeds limit")
                return False
                
            if memory_usage > self.usage_limits.get("memory_mb", 827):
                logger.warning(f"Memory usage ({memory_usage}MB) exceeds limit")
                return False
        
        # Check content policy compliance
        if "content" in parameters:
            content = parameters["content"]
            
            # Check against each content policy
            for policy in self.content_policies:
                for restriction in policy["restrictions"]:
                    if restriction.lower() in content.lower():
                        logger.warning(f"Content violates {policy['name']} policy")
                        return False
        
        # If all checks pass
        logger.info(f"Action '{action_type}' verified and compliant")
        return True
        
# Example usage
if __name__ == "__main__":
    # Create a creative agreement
    agreement = CreativeAgreement("VideoProductionAgreement")
    
    # Add parties
    agreement.add_party("script_writer", "agent-123456")
    agreement.add_party("visual_designer", "agent-789012")
    
    # Set resource limits
    agreement.set_resource_limits(cpu_percent=25, memory_mb=800)
    
    # Add content policies
    agreement.add_content_policy("appropriate_content", ["explicit violence", "hate speech"])
    
    # Set quality standards
    agreement.set_quality_standards("1080p", 30, "high")
    
    # Add verification function
    agreement.add_verification_function(
        "verifyContent",
        ["content_type", "content_data"],
        ["require(content_type in ['video', 'audio', 'image', 'text'])",
         "require(content_data.size <= 1000000000)"]  # 1GB size limit
    )
    
    # Finalize the agreement
    agreement.finalize()
    
    # Print the agreement
    print(json.dumps(agreement.to_dict(), indent=2))
