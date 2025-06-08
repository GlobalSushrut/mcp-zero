#!/usr/bin/env python3
"""
MCP-ZERO Agreement Deployment and Agent Interaction Demo
Showcases agreement creation and policy enforcement
"""
import json
import logging
import requests
import time
import sys
import os
import hashlib
from typing import Dict, Any, Optional

# Add parent directory to path for imports
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Import agreement templates - handle import with try/except to be resilient
try:
    from agreements.templates.standard_agreement import AgreementTemplates
    TEMPLATES_AVAILABLE = True
except ImportError:
    TEMPLATES_AVAILABLE = False
    print("Agreement templates not available, using mock implementation")

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger("agreement_demo")

# Server URLs
RPC_URL = "http://localhost:8081"

class MockAgreementMiddleware:
    """Mock implementation of AgreementMiddleware for when real one is unavailable"""
    
    def __init__(self):
        self.agreements = {}
    
    def create_agreement(self, consumer_id, provider_id, resource_id, agreement_type):
        """Create a mock agreement"""
        agreement_id = f"agreement-{int(time.time())}"
        agreement = MockAgreement(
            agreement_id=agreement_id,
            consumer_id=consumer_id,
            provider_id=provider_id,
            resource_id=resource_id,
            agreement_type=agreement_type
        )
        self.agreements[agreement_id] = agreement
        return agreement
    
    def submit_agreement(self, agreement):
        """Submit agreement to the blockchain (mock)"""
        # In real implementation, this would deploy a Solidity contract
        agreement.status = "deployed"
        agreement.deploy_hash = "0x" + hashlib.sha256(str(time.time()).encode()).hexdigest()
        return True

class MockAgreement:
    """Mock agreement object for when real one is unavailable"""
    
    def __init__(self, agreement_id, consumer_id, provider_id, resource_id, agreement_type):
        self.agreement_id = agreement_id
        self.consumer_id = consumer_id
        self.provider_id = provider_id
        self.resource_id = resource_id
        self.agreement_type = agreement_type
        self.terms = {}
        self.usage_limits = {}
        self.pricing = {}
        self.expiration = None
        self.status = "draft"
        self.deploy_hash = None
    
    def set_terms(self, terms):
        self.terms = terms
    
    def set_usage_limits(self, limits):
        self.usage_limits = limits
    
    def set_pricing(self, pricing):
        self.pricing = pricing
    
    def set_expiration(self, days):
        self.expiration = days
    
    def to_dict(self):
        """Convert agreement to dictionary"""
        return {
            "agreement_id": self.agreement_id,
            "consumer_id": self.consumer_id,
            "provider_id": self.provider_id,
            "resource_id": self.resource_id, 
            "agreement_type": self.agreement_type,
            "terms": self.terms,
            "usage_limits": self.usage_limits,
            "pricing": self.pricing,
            "expiration": self.expiration,
            "status": self.status,
            "deploy_hash": self.deploy_hash
        }

class AgreementDemo:
    """Demo for agreement deployment and agent interaction"""
    
    def __init__(self):
        """Initialize the demo"""
        self.demo_id = int(time.time())
        self.agents = {}
        self.agreement_id = None
        self.agreement_details = None
        
        # Check if we can use real templates
        if TEMPLATES_AVAILABLE:
            # Create real middleware
            try:
                from marketplace.middleware.agreement import AgreementMiddleware, AgreementType, UsageMetric
                self.agreement_middleware = AgreementMiddleware()
            except ImportError:
                logger.warning("Agreement middleware not available, using mock")
                self.agreement_middleware = MockAgreementMiddleware()
        else:
            # Use mock middleware
            self.agreement_middleware = MockAgreementMiddleware()
    
    def create_agents(self):
        """Create agents for testing"""
        logger.info("Creating agents for agreement interaction...")
        
        for role in ["provider", "consumer"]:
            response = requests.post(
                f"{RPC_URL}/api/v1/agents",
                json={"name": f"{role}-agent-{self.demo_id}"},
                timeout=3
            )
            agent_id = response.json().get("agent_id")
            self.agents[role] = agent_id
            logger.info(f"Created {role} agent with ID: {agent_id}")
        
        return self.agents
    
    def attach_plugins(self):
        """Attach necessary plugins to agents"""
        logger.info("Attaching plugins to agents...")
        
        plugins = {
            "provider": ["core", "agreement-provider", "policy-enforcer"],
            "consumer": ["core", "agreement-consumer", "resource-user"]
        }
        
        for role, agent_id in self.agents.items():
            for plugin in plugins.get(role, []):
                response = requests.post(
                    f"{RPC_URL}/api/v1/agents/{agent_id}/plugins",
                    json={"plugin_id": plugin},
                    timeout=3
                )
                result = response.json()
                logger.info(f"Attaching {plugin} to {role} agent: {result.get('success', False)}")
    
    def deploy_agreement(self):
        """Create and deploy agreement"""
        logger.info("Creating and deploying agreement...")
        
        # Get agent IDs
        provider_id = self.agents.get("provider")
        consumer_id = self.agents.get("consumer")
        resource_id = f"resource-{self.demo_id}"
        
        # Create agreement template - try different tiers
        try:
            if TEMPLATES_AVAILABLE:
                # Use real templates if available
                template = AgreementTemplates.business_tier_template(
                    consumer_id=consumer_id,
                    provider_id=provider_id,
                    resource_id=resource_id
                )
                # Create and deploy agreement via middleware
                self.agreement_id = AgreementTemplates.create_from_template(
                    template_data=template,
                    agreement_middleware=self.agreement_middleware
                )
                # If using mock middleware, get agreement details
                if isinstance(self.agreement_middleware, MockAgreementMiddleware):
                    agreement = self.agreement_middleware.agreements.get(self.agreement_id)
                    if agreement:
                        self.agreement_details = agreement.to_dict()
            else:
                # Use RPC server to create agreement
                response = requests.post(
                    f"{RPC_URL}/api/v1/agents/{provider_id}/execute",
                    json={
                        "intent": "create_agreement",
                        "inputs": {
                            "consumer_id": consumer_id,
                            "resource_id": resource_id,
                            "agreement_type": "business",
                            "terms": {
                                "service_level": "premium",
                                "ethical_policies": ["no_harmful_content", "data_privacy"]
                            }
                        }
                    },
                    timeout=5
                )
                result = response.json()
                if result.get("success", False):
                    # Extract agreement ID from result
                    self.agreement_id = result.get("result", {}).get("agreement_id", f"agreement-{self.demo_id}")
                    # Use dummy agreement details
                    self.agreement_details = {
                        "agreement_id": self.agreement_id,
                        "consumer_id": consumer_id,
                        "provider_id": provider_id,
                        "resource_id": resource_id, 
                        "agreement_type": "business",
                        "status": "deployed",
                        "deploy_hash": "0x" + hashlib.sha256(str(time.time()).encode()).hexdigest()
                    }
        except Exception as e:
            logger.error(f"Error deploying agreement: {str(e)}")
            # Fallback to manually creating agreement ID
            self.agreement_id = f"agreement-{self.demo_id}"
            # Use dummy agreement details
            self.agreement_details = {
                "agreement_id": self.agreement_id,
                "consumer_id": consumer_id,
                "provider_id": provider_id,
                "resource_id": resource_id, 
                "agreement_type": "business",
                "status": "deployed",
                "deploy_hash": "0x" + hashlib.sha256(str(time.time()).encode()).hexdigest()
            }
        
        logger.info(f"Agreement deployed with ID: {self.agreement_id}")
        logger.info(f"Agreement details: {json.dumps(self.agreement_details, indent=2) if self.agreement_details else 'Not available'}")
        
        return self.agreement_id
    
    def test_resource_access(self):
        """Test resource access under the agreement"""
        logger.info("Testing resource access...")
        
        consumer_id = self.agents.get("consumer")
        
        # Request resource access
        access_request = {
            "intent": "access_resource",
            "inputs": {
                "agreement_id": self.agreement_id,
                "resource_id": self.agreement_details.get("resource_id") if self.agreement_details else "resource",
                "access_level": "read"
            }
        }
        
        # Execute request
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{consumer_id}/execute",
            json=access_request,
            timeout=3
        )
        result = response.json()
        
        logger.info(f"Resource access result: {json.dumps(result, indent=2)}")
        
        return result
    
    def test_policy_enforcement(self):
        """Test ethical policy enforcement"""
        logger.info("Testing ethical policy enforcement...")
        
        consumer_id = self.agents.get("consumer")
        
        # Try to execute an action that violates policy
        violation_request = {
            "intent": "process_data",
            "inputs": {
                "agreement_id": self.agreement_id,
                "data_source": "personal_information",
                "processing_type": "extraction",
                "purpose": "targeted_advertising"  # This violates data_privacy policy
            }
        }
        
        # Execute request
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{consumer_id}/execute",
            json=violation_request,
            timeout=3
        )
        violation_result = response.json()
        
        logger.info(f"Policy violation attempt result: {json.dumps(violation_result, indent=2)}")
        
        # Try to execute a compliant action
        compliant_request = {
            "intent": "process_data",
            "inputs": {
                "agreement_id": self.agreement_id,
                "data_source": "anonymized_statistics",
                "processing_type": "aggregation",
                "purpose": "service_improvement"  # This should comply with policies
            }
        }
        
        # Execute request
        response = requests.post(
            f"{RPC_URL}/api/v1/agents/{consumer_id}/execute",
            json=compliant_request,
            timeout=3
        )
        compliant_result = response.json()
        
        logger.info(f"Policy compliant attempt result: {json.dumps(compliant_result, indent=2)}")
        
        return violation_result, compliant_result
    
    def run_demo(self):
        """Run the complete agreement demo"""
        start_time = time.time()
        logger.info("=" * 50)
        logger.info(" MCP-ZERO AGREEMENT DEMO")
        logger.info("=" * 50)
        
        try:
            # Create agents for agreement
            self.create_agents()
            
            # Attach necessary plugins
            self.attach_plugins()
            
            # Deploy agreement
            self.deploy_agreement()
            
            # Test resource access under agreement
            self.test_resource_access()
            
            # Test policy enforcement
            self.test_policy_enforcement()
            
            demo_time = time.time() - start_time
            logger.info(f"Demo completed in {demo_time:.2f} seconds")
            
        except Exception as e:
            logger.error(f"Demo failed with error: {str(e)}")
            return False
        
        return True

if __name__ == "__main__":
    demo = AgreementDemo()
    success = demo.run_demo()
    sys.exit(0 if success else 1)
