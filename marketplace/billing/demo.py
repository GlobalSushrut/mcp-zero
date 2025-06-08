#!/usr/bin/env python3
"""
MCP-ZERO Billing System Demo
Demonstrates the integrated billing workflow with marketplace and deployment
"""
import asyncio
import json
import logging
import os
import sys
import time
from datetime import datetime, timedelta

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from marketplace.billing.billing_system import BillingSystem
from marketplace.middleware.agreement import AgreementMiddleware, AgreementType, UsageMetric
from marketplace.marketplace import Marketplace

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler()
    ]
)
logger = logging.getLogger('billing_demo')

async def run_demo():
    """Run the billing system demonstration"""
    logger.info("Starting MCP-ZERO billing system demo")
    
    # Initialize components
    billing = BillingSystem(data_dir="marketplace/data")
    marketplace = Marketplace(database_path="marketplace/data/marketplace.db")
    agreement_middleware = AgreementMiddleware(storage_path="marketplace/data/agreements")
    
    # Step 1: Create test users
    logger.info("Creating test users and wallets")
    platform_user = billing.register_user("platform")
    developer = billing.register_user("developer1")
    consumer = billing.register_user("consumer1")
    provider = billing.register_user("provider1")
    
    # Step 2: Add funds to wallets
    logger.info("Adding funds to wallets")
    dev_wallet = billing.wallet.get_wallet_by_user("developer1")
    billing.wallet.deposit(dev_wallet["wallet_id"], 100.0, description="Initial deposit")
    
    consumer_wallet = billing.wallet.get_wallet_by_user("consumer1")
    billing.wallet.deposit(consumer_wallet["wallet_id"], 200.0, description="Initial deposit")
    
    provider_wallet = billing.wallet.get_wallet_by_user("provider1")
    billing.wallet.deposit(provider_wallet["wallet_id"], 50.0, description="Initial deposit")
    
    # Step 3: Set up pricing for different resource types
    logger.info("Setting up resource pricing")
    billing.usage_tracker.set_price("cpu", 0.01)  # $0.01 per CPU minute
    billing.usage_tracker.set_price("memory", 0.005)  # $0.005 per MB
    billing.usage_tracker.set_price("storage", 0.0005)  # $0.0005 per MB
    billing.usage_tracker.set_price("api_call", 0.001)  # $0.001 per API call
    
    # Step 4: Configure revenue sharing
    logger.info("Configuring revenue sharing")
    billing.revenue_sharing.set_share_configuration(
        "agent", 
        platform_share=10.0,   # 10% to platform
        developer_share=70.0,  # 70% to developer
        provider_share=20.0    # 20% to infrastructure provider
    )
    
    # Step 5: Create a marketplace listing for an agent
    logger.info("Creating marketplace listing")
    listing = {
        "name": "Image Generation Agent",
        "description": "AI agent for generating and editing images",
        "version": "1.0.0",
        "type": "agent",
        "tags": ["image", "generation", "creative"],
        "pricing_model": "usage",
        "price": 9.99,
        "publisher_id": "developer1",
        "metadata": {
            "capabilities": ["image_generation", "image_editing", "style_transfer"],
            "model": "stable-diffusion-xl"
        }
    }
    listing_id = marketplace.create_listing(listing)["listing_id"]
    logger.info(f"Created listing with ID: {listing_id}")
    
    # Step 6: Create a commercial agreement
    logger.info("Creating commercial agreement")
    agreement = agreement_middleware.create_agreement(
        consumer_id="consumer1",
        provider_id="developer1",
        resource_id=listing_id,
        agreement_type=AgreementType.BUSINESS
    )
    
    # Set terms and limits
    agreement.set_terms({
        "service_level": "standard",
        "support": "email",
        "termination_notice": "30 days"
    })
    
    agreement.set_usage_limits({
        UsageMetric.API_CALLS: 1000,
        UsageMetric.CPU_TIME: 500,
        UsageMetric.MEMORY: 2048
    })
    
    agreement.set_pricing({
        "base_fee": 9.99,
        "overage_rates": {
            "api_calls": 0.001,
            "cpu_time": 0.01,
            "memory": 0.005
        }
    })
    
    agreement.set_expiration(30)  # 30 days
    
    # Submit and sign the agreement
    agreement_middleware.submit_agreement(agreement)
    agreement.sign("consumer1", "consumer-signature")
    agreement.sign("developer1", "developer-signature")
    agreement_middleware._save_agreement(agreement)
    logger.info(f"Created and signed agreement with ID: {agreement.agreement_id}")
    
    # Step 7: Process an agent purchase
    logger.info("Processing agent purchase")
    purchase = billing.process_agent_purchase(
        buyer_id="consumer1",
        seller_id="developer1",
        agent_id=listing_id,
        amount=9.99,
        provider_id="provider1"
    )
    
    if purchase["success"]:
        logger.info(f"Purchase successful: {purchase['transaction_id']}")
    else:
        logger.error(f"Purchase failed: {purchase.get('error')}")
    
    # Step 8: Record agent usage
    logger.info("Recording agent usage")
    for i in range(5):
        # Simulate multiple API calls
        billing.track_agent_usage(
            user_id="consumer1",
            agent_id=listing_id,
            usage_type="api_call",
            quantity=10.0,
            unit="call"
        )
        
        # Simulate CPU usage
        billing.track_agent_usage(
            user_id="consumer1",
            agent_id=listing_id,
            usage_type="cpu",
            quantity=5.0,
            unit="minute"
        )
        
        # Simulate memory usage
        billing.track_agent_usage(
            user_id="consumer1",
            agent_id=listing_id,
            usage_type="memory",
            quantity=200.0,
            unit="MB"
        )
        
        # Simulate storage usage
        billing.track_agent_usage(
            user_id="consumer1",
            agent_id=listing_id,
            usage_type="storage",
            quantity=50.0,
            unit="MB"
        )
        
        # Record via agreement middleware as well
        agreement_middleware.record_usage(
            agreement_id=agreement.agreement_id,
            metric=UsageMetric.API_CALLS,
            quantity=10.0
        )
        
        agreement_middleware.record_usage(
            agreement_id=agreement.agreement_id,
            metric=UsageMetric.CPU_TIME,
            quantity=5.0
        )
        
        logger.info(f"Recorded usage batch {i+1}/5")
        time.sleep(0.5)  # Small delay between records
    
    # Step 9: Generate an invoice
    logger.info("Generating invoice")
    invoice = billing.generate_invoice("consumer1")
    
    if invoice["success"]:
        logger.info(f"Invoice generated: {invoice['invoice_id']}")
        logger.info(f"Total cost: ${invoice['total_cost']:.2f}")
        
        for usage_type in invoice["usage_summary"]:
            logger.info(f"  {usage_type['usage_type']}: {usage_type['total_quantity']} {usage_type['unit']} " +
                      f"at ${usage_type['price_per_unit']:.4f} each = ${usage_type['cost']:.2f}")
    else:
        logger.error(f"Invoice generation failed: {invoice.get('error')}")
    
    # Step 10: Pay the invoice
    logger.info("Paying invoice")
    if invoice["success"]:
        payment = billing.pay_invoice(invoice["invoice_id"], "consumer1")
        
        if payment["success"]:
            logger.info(f"Payment successful: ${payment['amount']:.2f}")
            logger.info(f"New balance: ${payment['new_balance']:.2f}")
        else:
            logger.error(f"Payment failed: {payment.get('error')}")
    
    # Step 11: Get financial summaries
    logger.info("Getting financial summaries")
    consumer_summary = billing.get_user_financial_summary("consumer1")
    developer_summary = billing.get_user_financial_summary("developer1")
    
    logger.info(f"Consumer balance: ${consumer_summary['wallet']['balance']:.2f}")
    logger.info(f"Developer balance: ${developer_summary['wallet']['balance']:.2f}")
    
    # Step 12: Finalize an agent deployment
    logger.info("Simulating agent deployment")
    deployment = billing.finalize_agent_deployment(
        deployment_id="deploy123",
        agent_id=listing_id,
        user_id="consumer1"
    )
    
    if deployment["success"]:
        logger.info(f"Deployment successful: {deployment['deployment_id']}")
    else:
        logger.error(f"Deployment failed: {deployment.get('error')}")
    
    logger.info("Billing system demo completed")

if __name__ == "__main__":
    asyncio.run(run_demo())
