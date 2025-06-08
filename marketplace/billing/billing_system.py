#!/usr/bin/env python3
"""
MCP-ZERO Billing System
Integrates wallet, revenue sharing, and usage tracking components
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any

from marketplace.billing.wallet import Wallet
from marketplace.billing.revenue_sharing import RevenueSharing
from marketplace.billing.usage_tracker import UsageTracker

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('billing_system')

class BillingSystem:
    """Main billing system for the MCP-ZERO marketplace"""
    
    def __init__(self, data_dir: str = "marketplace/data"):
        """Initialize the billing system components"""
        self.data_dir = data_dir
        os.makedirs(data_dir, exist_ok=True)
        
        # Initialize component subsystems
        self.wallet = Wallet(os.path.join(data_dir, "wallet.db"))
        self.revenue_sharing = RevenueSharing(os.path.join(data_dir, "revenue.db"))
        self.usage_tracker = UsageTracker(os.path.join(data_dir, "usage.db"))
        
        logger.info(f"Billing system initialized with data directory at {data_dir}")
        
    def register_user(self, user_id: str) -> Dict[str, Any]:
        """Register a new user with the billing system"""
        try:
            # Create user wallet
            wallet = self.wallet.create_wallet(user_id)
            
            # Start billing cycle
            billing_cycle = self.usage_tracker.start_billing_cycle(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "wallet": wallet,
                "billing_cycle": billing_cycle
            }
        except Exception as e:
            logger.error(f"Failed to register user {user_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def process_agent_purchase(self, 
                              buyer_id: str, 
                              seller_id: str,
                              agent_id: str,
                              amount: float,
                              provider_id: str = None) -> Dict[str, Any]:
        """Process the purchase of an agent or plugin"""
        try:
            # 1. Get buyer wallet
            buyer_wallet = self.wallet.get_wallet_by_user(buyer_id)
            if not buyer_wallet:
                return {
                    "success": False,
                    "error": f"Buyer {buyer_id} does not have a wallet"
                }
                
            # 2. Withdraw funds from buyer
            withdrawal = self.wallet.withdraw(
                buyer_wallet["wallet_id"],
                amount,
                description=f"Purchase of agent {agent_id}"
            )
            
            if not withdrawal.get("success", False):
                return {
                    "success": False,
                    "error": withdrawal.get("error", "Failed to withdraw funds")
                }
                
            # 3. Create revenue distribution
            distribution = self.revenue_sharing.distribute_revenue(
                transaction_id=withdrawal["transaction_id"],
                resource_id=agent_id,
                resource_type="agent",
                amount=amount,
                platform_id="platform",  # Hardcoded platform ID
                developer_id=seller_id,
                provider_id=provider_id
            )
            
            if not distribution.get("success", False):
                # If distribution fails, refund the buyer
                self.wallet.deposit(
                    buyer_wallet["wallet_id"],
                    amount,
                    description=f"Refund for failed purchase of agent {agent_id}"
                )
                
                return {
                    "success": False,
                    "error": distribution.get("error", "Failed to distribute revenue")
                }
                
            # 4. Process the distribution (transfer funds to seller and platform)
            process_result = self.revenue_sharing.process_distribution(
                distribution["distribution_id"],
                self.wallet
            )
            
            if not process_result.get("success", False):
                # If processing fails, refund the buyer
                self.wallet.deposit(
                    buyer_wallet["wallet_id"],
                    amount,
                    description=f"Refund for failed purchase of agent {agent_id}"
                )
                
                return {
                    "success": False,
                    "error": process_result.get("error", "Failed to process revenue distribution")
                }
                
            # Success!
            return {
                "success": True,
                "transaction_id": withdrawal["transaction_id"],
                "distribution_id": distribution["distribution_id"],
                "amount": amount,
                "agent_id": agent_id,
                "buyer_id": buyer_id,
                "seller_id": seller_id
            }
        except Exception as e:
            logger.error(f"Failed to process agent purchase: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def track_agent_usage(self,
                        user_id: str,
                        agent_id: str,
                        usage_type: str,
                        quantity: float,
                        unit: str) -> Dict[str, Any]:
        """Track agent resource usage for billing"""
        try:
            # Record the usage
            record = self.usage_tracker.record_usage(
                agent_id=agent_id,
                user_id=user_id,
                usage_type=usage_type,
                quantity=quantity,
                unit=unit
            )
            
            return {
                "success": True,
                "record_id": record.get("record_id"),
                "user_id": user_id,
                "agent_id": agent_id,
                "usage_type": usage_type,
                "quantity": quantity,
                "unit": unit
            }
        except Exception as e:
            logger.error(f"Failed to track agent usage: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def generate_invoice(self, user_id: str) -> Dict[str, Any]:
        """Generate an invoice for the current billing cycle"""
        try:
            # Find active billing cycle
            conn = self.usage_tracker._ensure_database()
            if hasattr(conn, 'cursor'):
                cursor = conn.cursor()
                cursor.execute(
                    "SELECT cycle_id, start_date, end_date FROM billing_cycles "
                    "WHERE user_id = ? AND status = 'active'",
                    (user_id,)
                )
                
                row = cursor.fetchone()
                if not row:
                    return {
                        "success": False,
                        "error": f"No active billing cycle found for user {user_id}"
                    }
                    
                cycle_id, start_date, end_date = row
            else:
                # Fallback if database access is different
                return {
                    "success": False,
                    "error": "Could not access billing cycle information"
                }
                
            # Calculate usage costs
            costs = self.usage_tracker.calculate_usage_cost(
                user_id=user_id,
                start_time=start_date,
                end_time=end_date
            )
            
            # Generate invoice ID
            invoice_id = str(uuid.uuid4())
            
            # Close billing cycle
            cycle_closed = self.usage_tracker.close_billing_cycle(
                cycle_id=cycle_id,
                invoice_id=invoice_id
            )
            
            if not cycle_closed.get("success", False):
                return {
                    "success": False,
                    "error": cycle_closed.get("error", "Failed to close billing cycle")
                }
                
            # Start new billing cycle
            new_cycle = self.usage_tracker.start_billing_cycle(user_id)
            
            # Get wallet info
            wallet = self.wallet.get_wallet_by_user(user_id)
            
            return {
                "success": True,
                "invoice_id": invoice_id,
                "user_id": user_id,
                "cycle_id": cycle_id,
                "start_date": start_date,
                "end_date": end_date,
                "total_cost": costs["total_cost"],
                "usage_summary": costs["usage_summary"],
                "wallet_balance": wallet["balance"] if wallet else 0.0,
                "new_cycle_id": new_cycle.get("cycle_id") if new_cycle.get("success", False) else None
            }
        except Exception as e:
            logger.error(f"Failed to generate invoice: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def pay_invoice(self, invoice_id: str, user_id: str) -> Dict[str, Any]:
        """Pay an invoice from the user's wallet"""
        try:
            # Get invoice data (this would be stored somewhere)
            # For this example, we'll mock the invoice lookup
            # In a real system, you'd query the invoice from a database
            
            # Get current wallet balance
            wallet = self.wallet.get_wallet_by_user(user_id)
            if not wallet:
                return {
                    "success": False,
                    "error": f"User {user_id} does not have a wallet"
                }
                
            # Mock invoice amount
            # In a real system, you would retrieve this from the database
            invoice_amount = 50.0  # Example amount
            
            # Check if wallet has sufficient balance
            if wallet["balance"] < invoice_amount:
                return {
                    "success": False,
                    "error": "Insufficient funds in wallet",
                    "balance": wallet["balance"],
                    "invoice_amount": invoice_amount
                }
                
            # Withdraw funds from user's wallet
            withdrawal = self.wallet.withdraw(
                wallet["wallet_id"],
                invoice_amount,
                description=f"Payment for invoice {invoice_id}"
            )
            
            if not withdrawal.get("success", False):
                return {
                    "success": False,
                    "error": withdrawal.get("error", "Failed to withdraw funds")
                }
                
            # Transfer to platform account
            platform_wallet = self.wallet.get_wallet_by_user("platform")
            if platform_wallet:
                self.wallet.deposit(
                    platform_wallet["wallet_id"],
                    invoice_amount,
                    description=f"Payment for invoice {invoice_id} from user {user_id}"
                )
                
            return {
                "success": True,
                "invoice_id": invoice_id,
                "user_id": user_id,
                "amount": invoice_amount,
                "transaction_id": withdrawal["transaction_id"],
                "new_balance": withdrawal["new_balance"]
            }
        except Exception as e:
            logger.error(f"Failed to pay invoice: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def get_user_financial_summary(self, user_id: str) -> Dict[str, Any]:
        """Get a complete financial summary for a user"""
        try:
            # Get wallet info
            wallet = self.wallet.get_wallet_by_user(user_id)
            
            # Get transactions
            transactions = []
            if wallet:
                transactions = self.wallet.get_transactions(wallet["wallet_id"], limit=10)
                
            # Get earnings from revenue sharing
            earnings = self.revenue_sharing.get_user_earnings(user_id)
            
            # Get current usage costs
            current_costs = self.usage_tracker.calculate_usage_cost(user_id)
            
            return {
                "success": True,
                "user_id": user_id,
                "wallet": wallet,
                "recent_transactions": transactions,
                "earnings": earnings,
                "current_usage_costs": current_costs,
                "net_balance": (wallet["balance"] if wallet else 0.0)
            }
        except Exception as e:
            logger.error(f"Failed to get financial summary: {e}")
            return {
                "success": False,
                "error": str(e)
            }
            
    def finalize_agent_deployment(self, 
                                 deployment_id: str,
                                 agent_id: str,
                                 user_id: str) -> Dict[str, Any]:
        """Process billing for an agent deployment"""
        try:
            # Record deployment setup fee
            self.track_agent_usage(
                user_id=user_id,
                agent_id=agent_id,
                usage_type="deployment",
                quantity=1.0,
                unit="deployment"
            )
            
            # For this example, we'll mock the deployment cost
            # In a real system, this would be calculated based on pricing
            deployment_cost = 5.0  # Example cost
            
            # Charge user's wallet
            wallet = self.wallet.get_wallet_by_user(user_id)
            if not wallet:
                return {
                    "success": False,
                    "error": f"User {user_id} does not have a wallet"
                }
                
            withdrawal = self.wallet.withdraw(
                wallet["wallet_id"],
                deployment_cost,
                reference_id=deployment_id,
                description=f"Deployment fee for agent {agent_id}"
            )
            
            if not withdrawal.get("success", False):
                return {
                    "success": False,
                    "error": withdrawal.get("error", "Failed to withdraw deployment fee")
                }
                
            # Distribute revenue
            distribution = self.revenue_sharing.distribute_revenue(
                transaction_id=withdrawal["transaction_id"],
                resource_id=agent_id,
                resource_type="deployment",
                amount=deployment_cost,
                platform_id="platform",
                developer_id=user_id,  # In deployments, user is usually the developer
                provider_id="cloud_provider"  # Example provider ID
            )
            
            # Process the distribution
            if distribution.get("success", False):
                self.revenue_sharing.process_distribution(
                    distribution["distribution_id"],
                    self.wallet
                )
                
            return {
                "success": True,
                "deployment_id": deployment_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "cost": deployment_cost,
                "transaction_id": withdrawal.get("transaction_id")
            }
        except Exception as e:
            logger.error(f"Failed to finalize agent deployment: {e}")
            return {
                "success": False,
                "error": str(e)
            }


# Example usage
if __name__ == "__main__":
    # Initialize billing system
    billing = BillingSystem()
    
    # Register users
    user1 = billing.register_user("user1")
    user2 = billing.register_user("user2")
    platform = billing.register_user("platform")
    provider = billing.register_user("cloud_provider")
    
    # Add funds to user1's wallet
    user1_wallet = billing.wallet.get_wallet_by_user("user1")
    billing.wallet.deposit(user1_wallet["wallet_id"], 100.0)
    
    # Set pricing for CPU usage
    billing.usage_tracker.set_price("cpu", 0.01)  # $0.01 per CPU minute
    
    # Record some usage
    billing.track_agent_usage("user1", "agent123", "cpu", 10.0, "minute")
    
    # Process an agent purchase
    purchase = billing.process_agent_purchase(
        buyer_id="user1",
        seller_id="user2",
        agent_id="agent456",
        amount=25.0
    )
    
    # Get financial summary
    summary = billing.get_user_financial_summary("user1")
    
    print(json.dumps(summary, indent=2))
