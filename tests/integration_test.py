#!/usr/bin/env python3
"""
MCP-ZERO Integration Tests
Validates the integration between different components of the MCP-ZERO infrastructure
"""
import asyncio
import json
import logging
import os
import sys
import time
import unittest
from datetime import datetime
from typing import Dict, List, Any

# Add project root to path
sys.path.append(os.path.join(os.path.dirname(__file__), ".."))

from config.settings import configure, settings
from marketplace.marketplace import Marketplace
from marketplace.billing.billing_system import BillingSystem
from marketplace.middleware.agreement import AgreementMiddleware, AgreementType, UsageMetric
from deploy.agents.deployment_manager import DeploymentManager
from deploy.plugins.plugin_manager import PluginManager

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('integration_tests')

class MCPZeroIntegrationTests(unittest.TestCase):
    """Integration tests for the MCP-ZERO infrastructure"""
    
    @classmethod
    def setUpClass(cls):
        """Set up test environment"""
        # Configure with test settings
        configure("tests/test_config.json")
        
        # Test data paths
        cls.test_data_dir = "tests/data"
        os.makedirs(cls.test_data_dir, exist_ok=True)
        
        # Initialize components with test data paths
        cls.marketplace = Marketplace(database_path=f"{cls.test_data_dir}/marketplace.db")
        cls.billing_system = BillingSystem(data_dir=cls.test_data_dir)
        cls.agreement_middleware = AgreementMiddleware(storage_path=f"{cls.test_data_dir}/agreements")
        cls.deployment_manager = DeploymentManager(storage_path=f"{cls.test_data_dir}/agents")
        cls.plugin_manager = PluginManager(plugins_path=f"{cls.test_data_dir}/plugins")
        
    def setUp(self):
        """Set up before each test"""
        # Create test users
        self.platform_id = "platform"
        self.developer_id = "test_developer"
        self.consumer_id = "test_consumer"
        self.provider_id = "test_provider"
        
        # Register users with billing system
        self.billing_system.register_user(self.platform_id)
        self.billing_system.register_user(self.developer_id)
        self.billing_system.register_user(self.consumer_id)
        self.billing_system.register_user(self.provider_id)
        
        # Add funds to wallets
        dev_wallet = self.billing_system.wallet.get_wallet_by_user(self.developer_id)
        self.billing_system.wallet.deposit(dev_wallet["wallet_id"], 100.0, "Test deposit")
        
        consumer_wallet = self.billing_system.wallet.get_wallet_by_user(self.consumer_id)
        self.billing_system.wallet.deposit(consumer_wallet["wallet_id"], 200.0, "Test deposit")
        
        # Set up pricing
        self.billing_system.usage_tracker.set_price("cpu", 0.01)
        self.billing_system.usage_tracker.set_price("memory", 0.005)
        self.billing_system.usage_tracker.set_price("storage", 0.0005)
        self.billing_system.usage_tracker.set_price("api_call", 0.001)
        
        # Configure revenue sharing
        self.billing_system.revenue_sharing.set_share_configuration(
            "agent", 
            platform_share=10.0,
            developer_share=70.0,
            provider_share=20.0
        )
        
    def test_full_integration_flow(self):
        """Test the full integration flow from listing creation to billing"""
        # 1. Create marketplace listing
        listing = {
            "name": "Test Agent",
            "description": "Test agent for integration tests",
            "version": "1.0.0",
            "type": "agent",
            "tags": ["test", "integration"],
            "pricing_model": "usage",
            "price": 9.99,
            "publisher_id": self.developer_id,
            "metadata": {
                "capabilities": ["test"]
            }
        }
        
        listing_result = self.marketplace.create_listing(listing)
        self.assertTrue("listing_id" in listing_result)
        listing_id = listing_result["listing_id"]
        
        # 2. Create agreement
        agreement = self.agreement_middleware.create_agreement(
            consumer_id=self.consumer_id,
            provider_id=self.developer_id,
            resource_id=listing_id,
            agreement_type=AgreementType.BUSINESS
        )
        
        agreement.set_terms({
            "service_level": "standard",
            "support": "email"
        })
        
        agreement.set_usage_limits({
            UsageMetric.API_CALLS: 1000,
            UsageMetric.CPU_TIME: 100,
            UsageMetric.MEMORY: 1024
        })
        
        agreement.set_pricing({
            "base_fee": 9.99,
            "overage_rates": {
                "api_calls": 0.001,
                "cpu_time": 0.01,
                "memory": 0.005
            }
        })
        
        agreement.set_expiration(30)
        self.agreement_middleware.submit_agreement(agreement)
        agreement.sign(self.consumer_id, "test-signature")
        agreement.sign(self.developer_id, "test-signature")
        self.agreement_middleware._save_agreement(agreement)
        
        # 3. Deploy agent
        agent_config = {
            "name": "Test Agent",
            "version": "1.0.0",
            "description": "Test agent for integration",
            "capabilities": ["test"],
            "resource_requirements": {
                "cpu": 1,
                "memory": 512
            }
        }
        
        # Save config to file for deployment
        config_path = os.path.join(self.test_data_dir, "test_agent_config.json")
        with open(config_path, "w") as f:
            json.dump(agent_config, f)
        
        deployment_id = self.deployment_manager.deploy_agent(
            agent_config=agent_config,
            developer_id=self.developer_id
        )
        
        self.assertIsNotNone(deployment_id)
        
        # 4. Process agent purchase
        purchase = self.billing_system.process_agent_purchase(
            buyer_id=self.consumer_id,
            seller_id=self.developer_id,
            agent_id=listing_id,
            amount=9.99,
            provider_id=self.provider_id
        )
        
        self.assertTrue(purchase["success"])
        
        # 5. Track agent usage
        for i in range(5):
            self.billing_system.track_agent_usage(
                user_id=self.consumer_id,
                agent_id=listing_id,
                usage_type="api_call",
                quantity=10.0,
                unit="call"
            )
            
            self.billing_system.track_agent_usage(
                user_id=self.consumer_id,
                agent_id=listing_id,
                usage_type="cpu",
                quantity=5.0,
                unit="minute"
            )
            
            self.agreement_middleware.record_usage(
                agreement_id=agreement.agreement_id,
                metric=UsageMetric.API_CALLS,
                quantity=10.0
            )
            
            self.agreement_middleware.record_usage(
                agreement_id=agreement.agreement_id,
                metric=UsageMetric.CPU_TIME,
                quantity=5.0
            )
        
        # 6. Generate invoice
        invoice = self.billing_system.generate_invoice(self.consumer_id)
        self.assertTrue(invoice["success"])
        self.assertGreater(invoice["total_cost"], 0)
        
        # 7. Pay invoice
        payment = self.billing_system.pay_invoice(invoice["invoice_id"], self.consumer_id)
        self.assertTrue(payment["success"])
        
        # 8. Verify financial summaries
        consumer_summary = self.billing_system.get_user_financial_summary(self.consumer_id)
        developer_summary = self.billing_system.get_user_financial_summary(self.developer_id)
        provider_summary = self.billing_system.get_user_financial_summary(self.provider_id)
        platform_summary = self.billing_system.get_user_financial_summary(self.platform_id)
        
        # Consumer balance should be less than initial deposit due to payments
        self.assertLess(consumer_summary["wallet"]["balance"], 200.0)
        
        # Developer should have earned revenue
        self.assertGreater(developer_summary["wallet"]["balance"], 100.0)
        
        # Provider should have earned revenue
        self.assertGreater(provider_summary["wallet"]["balance"], 0.0)
        
        # Platform should have earned revenue
        self.assertGreater(platform_summary["wallet"]["balance"], 0.0)
        
        # 9. Verify agreement usage tracking
        usage_status = self.agreement_middleware.check_usage_status(agreement.agreement_id)
        self.assertIn(UsageMetric.API_CALLS, usage_status)
        self.assertIn(UsageMetric.CPU_TIME, usage_status)
        
        # API calls should be recorded
        self.assertEqual(usage_status[UsageMetric.API_CALLS]["current_usage"], 50.0)
        
        # CPU time should be recorded
        self.assertEqual(usage_status[UsageMetric.CPU_TIME]["current_usage"], 25.0)
        
        # 10. Test finalizing deployment
        finalization = self.billing_system.finalize_agent_deployment(
            deployment_id=deployment_id,
            agent_id=listing_id,
            user_id=self.consumer_id
        )
        
        self.assertTrue(finalization["success"])
        
    def tearDown(self):
        """Clean up after each test"""
        # No specific cleanup needed for now
        pass
    
    @classmethod
    def tearDownClass(cls):
        """Clean up test environment"""
        # Remove test data
        #import shutil
        #shutil.rmtree(cls.test_data_dir, ignore_errors=True)
        pass

class AsyncMCPZeroTests(unittest.TestCase):
    """Async tests for components that require async operation"""
    
    def setUp(self):
        """Set up before each test"""
        # Configure with test settings
        configure("tests/test_config.json")
        
        # Test data paths
        self.test_data_dir = "tests/data"
        os.makedirs(self.test_data_dir, exist_ok=True)
        
    def test_agreement_executor(self):
        """Test the agreement executor functionality"""
        # This would be implemented when the agreement executor is complete
        # It would test automatic monitoring and enforcement of agreements
        # For now, we'll mark it as a placeholder
        self.skipTest("Agreement executor tests not yet implemented")
        
    def test_mesh_interface(self):
        """Test the mesh network interface"""
        # This would be implemented when the mesh interface is complete
        # It would test peer discovery and agent announcement
        # For now, we'll mark it as a placeholder
        self.skipTest("Mesh interface tests not yet implemented")
        
    def tearDown(self):
        """Clean up after each test"""
        pass

async def run_async_tests():
    """Run the async test cases"""
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(AsyncMCPZeroTests)
    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)

def run_all_tests():
    """Run all test cases"""
    # Run sync tests
    test_loader = unittest.TestLoader()
    test_suite = test_loader.loadTestsFromTestCase(MCPZeroIntegrationTests)
    test_runner = unittest.TextTestRunner()
    test_runner.run(test_suite)
    
    # Run async tests
    asyncio.run(run_async_tests())

if __name__ == "__main__":
    # Create test config if it doesn't exist
    test_config_path = "tests/test_config.json"
    os.makedirs("tests", exist_ok=True)
    
    if not os.path.exists(test_config_path):
        test_config = {
            "api": {
                "host": "localhost",
                "port": 8000,
                "debug": True
            },
            "database": {
                "type": "sqlite",
                "path": "tests/data/test.db"
            },
            "marketplace": {
                "data_path": "tests/data",
                "platform_fee": 10.0
            },
            "agreements": {
                "storage_path": "tests/data/agreements"
            },
            "deployment": {
                "agents_path": "tests/data/agents",
                "plugins_path": "tests/data/plugins"
            },
            "mesh": {
                "enabled": False,
                "host": "localhost",
                "port": 8765
            },
            "security": {
                "jwt_secret": "test-secret",
                "api_keys": ["test-key"]
            }
        }
        
        with open(test_config_path, "w") as f:
            json.dump(test_config, f, indent=2)
    
    run_all_tests()
