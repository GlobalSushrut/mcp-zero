#!/usr/bin/env python3
"""
MCP-ZERO Agreement Executor
Service responsible for executing and enforcing agreements
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from marketplace.middleware.agreement import AgreementMiddleware, AgreementStatus, AgreementType, UsageMetric
from marketplace.billing.billing_system import BillingSystem

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s'
)
logger = logging.getLogger('agreement_executor')

class AgreementExecutor:
    """Service to monitor and execute agreements"""
    
    def __init__(self, storage_path: str = "agreements/storage", 
                 billing_data_path: str = "marketplace/data"):
        """Initialize the agreement executor"""
        self.storage_path = storage_path
        self.agreement_middleware = AgreementMiddleware(storage_path=storage_path)
        self.billing_system = BillingSystem(data_dir=billing_data_path)
        self.running = False
        self.active_tasks = {}
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        logger.info(f"Agreement Executor initialized with storage path: {storage_path}")
        
    async def start(self):
        """Start the agreement executor service"""
        if self.running:
            return
            
        self.running = True
        logger.info("Starting Agreement Executor service")
        
        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(
                sig, lambda: asyncio.create_task(self.shutdown())
            )
        
        # Start background tasks
        self.active_tasks['monitor'] = asyncio.create_task(self.monitor_agreements())
        self.active_tasks['billing'] = asyncio.create_task(self.process_billing_cycles())
        self.active_tasks['cleanup'] = asyncio.create_task(self.cleanup_expired())
        
    async def shutdown(self):
        """Shutdown the agreement executor service"""
        if not self.running:
            return
            
        logger.info("Shutting down Agreement Executor service")
        self.running = False
        
        # Cancel all running tasks
        for name, task in self.active_tasks.items():
            if not task.done():
                logger.info(f"Cancelling task: {name}")
                task.cancel()
                
        # Wait for tasks to complete
        await asyncio.gather(*self.active_tasks.values(), return_exceptions=True)
        logger.info("Agreement Executor service shutdown complete")
        
    async def monitor_agreements(self):
        """Continuously monitor active agreements and enforce limits"""
        try:
            while self.running:
                logger.debug("Monitoring agreements")
                agreements = self.agreement_middleware.list_agreements(status=AgreementStatus.ACTIVE)
                
                for agreement_id in agreements:
                    try:
                        agreement = self.agreement_middleware.get_agreement(agreement_id)
                        if not agreement:
                            continue
                            
                        # Check if agreement has expired
                        if agreement.is_expired():
                            logger.info(f"Agreement {agreement_id} has expired")
                            agreement.set_status(AgreementStatus.EXPIRED)
                            self.agreement_middleware._save_agreement(agreement)
                            continue
                            
                        # Check if usage limits are reached
                        usage_status = self.agreement_middleware.check_usage_status(agreement_id)
                        
                        for metric, status in usage_status.items():
                            if status["limit_reached"]:
                                logger.warning(f"Agreement {agreement_id} has reached {metric} limit: "
                                             f"{status['current_usage']}/{status['limit']}")
                                
                                # Take appropriate action based on agreement type
                                if agreement.agreement_type == AgreementType.FREE:
                                    # For free agreements, suspend when limits are reached
                                    agreement.set_status(AgreementStatus.SUSPENDED)
                                    self.agreement_middleware._save_agreement(agreement)
                                    logger.info(f"Free agreement {agreement_id} suspended due to usage limits")
                                    break
                                elif agreement.agreement_type in [AgreementType.PERSONAL, AgreementType.BUSINESS]:
                                    # For paid agreements, record overage for billing
                                    overage = status["current_usage"] - status["limit"]
                                    self._record_billing_overage(agreement, metric, overage)
                                    logger.info(f"Recorded billing overage for agreement {agreement_id}: "
                                              f"{metric} overage of {overage}")
                    except Exception as e:
                        logger.error(f"Error processing agreement {agreement_id}: {str(e)}")
                
                # Sleep for a short time before checking again
                await asyncio.sleep(30)
        except asyncio.CancelledError:
            logger.info("Agreement monitoring task cancelled")
        except Exception as e:
            logger.error(f"Error in agreement monitoring: {str(e)}")
            
    def _record_billing_overage(self, agreement, metric, overage):
        """Record billing overage for an agreement"""
        try:
            pricing = agreement.pricing.get("overage_rates", {})
            metric_key = metric.value.lower()
            
            if metric_key in pricing:
                rate = pricing[metric_key]
                amount = rate * overage
                
                # Record the overage for billing
                self.billing_system.track_agent_usage(
                    user_id=agreement.consumer_id,
                    agent_id=agreement.resource_id,
                    usage_type=f"overage_{metric_key}",
                    quantity=overage,
                    unit=self._get_unit_for_metric(metric)
                )
                
                logger.info(f"Recorded billing overage for {agreement.agreement_id}: "
                          f"{overage} {metric_key} at rate {rate}, total {amount}")
        except Exception as e:
            logger.error(f"Error recording billing overage: {str(e)}")
            
    def _get_unit_for_metric(self, metric):
        """Get appropriate unit for a usage metric"""
        if metric == UsageMetric.API_CALLS:
            return "call"
        elif metric == UsageMetric.CPU_TIME:
            return "minute"
        elif metric == UsageMetric.MEMORY:
            return "MB"
        elif metric == UsageMetric.STORAGE:
            return "MB"
        elif metric == UsageMetric.BANDWIDTH:
            return "MB"
        else:
            return "unit"
            
    async def process_billing_cycles(self):
        """Process billing cycles for all active agreements"""
        try:
            while self.running:
                logger.debug("Processing billing cycles")
                
                # Get active agreements that need billing
                agreements = self.agreement_middleware.list_agreements(status=AgreementStatus.ACTIVE)
                now = datetime.now()
                
                for agreement_id in agreements:
                    try:
                        agreement = self.agreement_middleware.get_agreement(agreement_id)
                        if not agreement or agreement.agreement_type == AgreementType.FREE:
                            continue
                            
                        # Skip if already billed this month
                        last_billed = agreement.metadata.get("last_billed_date")
                        if last_billed:
                            last_billed_date = datetime.fromisoformat(last_billed)
                            if (now - last_billed_date).days < 30:
                                continue
                                
                        # Process monthly billing
                        if agreement.agreement_type in [AgreementType.PERSONAL, AgreementType.BUSINESS, AgreementType.ENTERPRISE]:
                            self._process_monthly_billing(agreement)
                            
                            # Update last billed date
                            agreement.metadata["last_billed_date"] = now.isoformat()
                            self.agreement_middleware._save_agreement(agreement)
                    except Exception as e:
                        logger.error(f"Error processing billing for agreement {agreement_id}: {str(e)}")
                
                # Sleep for a longer time (check once per hour)
                await asyncio.sleep(3600)
        except asyncio.CancelledError:
            logger.info("Billing cycle task cancelled")
        except Exception as e:
            logger.error(f"Error in billing cycle processing: {str(e)}")
            
    def _process_monthly_billing(self, agreement):
        """Process monthly billing for an agreement"""
        try:
            base_fee = agreement.pricing.get("base_fee", 0.0)
            
            if base_fee > 0:
                # Create a billing transaction
                transaction = self.billing_system.process_agent_purchase(
                    buyer_id=agreement.consumer_id,
                    seller_id=agreement.provider_id,
                    agent_id=agreement.resource_id,
                    amount=base_fee
                )
                
                if transaction.get("success", False):
                    logger.info(f"Processed monthly billing for agreement {agreement.agreement_id}: "
                              f"${base_fee} from {agreement.consumer_id} to {agreement.provider_id}")
                else:
                    logger.error(f"Failed to process monthly billing for agreement {agreement.agreement_id}: "
                               f"{transaction.get('error', 'Unknown error')}")
                    
                    # If payment fails, handle accordingly
                    if agreement.agreement_type != AgreementType.ENTERPRISE:
                        # For non-enterprise agreements, suspend on failed payment
                        agreement.set_status(AgreementStatus.SUSPENDED)
                        agreement.metadata["payment_failure_date"] = datetime.now().isoformat()
                        self.agreement_middleware._save_agreement(agreement)
                        logger.warning(f"Agreement {agreement.agreement_id} suspended due to payment failure")
        except Exception as e:
            logger.error(f"Error processing monthly billing: {str(e)}")
    
    async def cleanup_expired(self):
        """Clean up expired agreements"""
        try:
            while self.running:
                logger.debug("Cleaning up expired agreements")
                
                # Get expired agreements
                agreements = self.agreement_middleware.list_agreements(status=AgreementStatus.EXPIRED)
                now = datetime.now()
                
                for agreement_id in agreements:
                    try:
                        agreement = self.agreement_middleware.get_agreement(agreement_id)
                        if not agreement:
                            continue
                            
                        # Check if expired more than 90 days ago
                        if agreement.expiration_date:
                            expiration = datetime.fromisoformat(
                                agreement.expiration_date.isoformat() 
                                if hasattr(agreement.expiration_date, 'isoformat') 
                                else agreement.expiration_date
                            )
                            
                            if (now - expiration).days > 90:
                                # Archive agreement instead of deleting
                                self._archive_agreement(agreement)
                                logger.info(f"Archived expired agreement {agreement_id}")
                    except Exception as e:
                        logger.error(f"Error cleaning up agreement {agreement_id}: {str(e)}")
                
                # Sleep for a day
                await asyncio.sleep(86400)
        except asyncio.CancelledError:
            logger.info("Cleanup task cancelled")
        except Exception as e:
            logger.error(f"Error in agreement cleanup: {str(e)}")
    
    def _archive_agreement(self, agreement):
        """Archive an expired agreement"""
        try:
            # Create archives directory if it doesn't exist
            archive_dir = os.path.join(self.storage_path, "archives")
            os.makedirs(archive_dir, exist_ok=True)
            
            # Save agreement to archives
            agreement_data = agreement.to_dict()
            archive_path = os.path.join(archive_dir, f"{agreement.agreement_id}.json")
            
            with open(archive_path, 'w') as f:
                json.dump(agreement_data, f, indent=2)
                
            # Remove from active agreements
            agreement_path = os.path.join(self.storage_path, f"{agreement.agreement_id}.json")
            if os.path.exists(agreement_path):
                os.remove(agreement_path)
        except Exception as e:
            logger.error(f"Error archiving agreement: {str(e)}")

async def main():
    """Main entry point for the agreement executor service"""
    executor = AgreementExecutor()
    await executor.start()
    
    try:
        # Keep the service running
        while True:
            await asyncio.sleep(1)
    except asyncio.CancelledError:
        pass
    finally:
        await executor.shutdown()

if __name__ == "__main__":
    asyncio.run(main())
