#!/usr/bin/env python3
"""
MCP-ZERO Mesh Network Agreement Validator
Validates agreements and enforces billing across the mesh network
"""
import asyncio
import json
import logging
import os
import sys
from datetime import datetime
from typing import Dict, Any, Optional, List

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

# Import agreement components
try:
    from agreements.execution.agreement_executor import AgreementExecutor
    from agreements.templates.standard_agreement import StandardAgreementTemplate
    from marketplace.billing.billing_system import BillingSystem
    AGREEMENT_LIBS_AVAILABLE = True
except ImportError:
    AGREEMENT_LIBS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('agreement_validator')

class AgreementValidator:
    """
    Validates agreements and enforces billing across the mesh network
    
    Connects the P2P mesh network with agreement execution and billing systems
    to ensure that resources are used according to valid agreements.
    """
    
    def __init__(self, node_id: str, mesh_network=None):
        """
        Initialize the agreement validator
        
        Args:
            node_id: ID of the local node
            mesh_network: MeshNetwork instance (optional)
        """
        self.node_id = node_id
        self.mesh_network = mesh_network
        self.agreement_executor = None
        self.billing_system = None
        self.active_agreements = {}  # agreement_id -> agreement_data
        
        # Initialize components if available
        if AGREEMENT_LIBS_AVAILABLE:
            storage_path = os.path.join(os.path.dirname(__file__), "../../../agreements/storage")
            self.agreement_executor = AgreementExecutor(storage_path=storage_path)
            
            billing_path = os.path.join(os.path.dirname(__file__), "../../../marketplace/data")
            self.billing_system = BillingSystem(data_dir=billing_path)
            
            logger.info("Agreement validation components initialized")
        else:
            logger.warning("Agreement libraries not available, validation disabled")
            
    async def start(self):
        """Start the agreement validator"""
        if not AGREEMENT_LIBS_AVAILABLE:
            logger.warning("Cannot start agreement validator: libraries not available")
            return False
            
        try:
            # Load active agreements
            await self.refresh_agreements()
            
            # Start agreement executor
            if self.agreement_executor:
                asyncio.create_task(self.agreement_executor.start_monitoring())
                
            # Subscribe to mesh events if mesh network is available
            if self.mesh_network:
                self.mesh_network.subscribe_to_event('resource_usage', self._handle_resource_usage)
                self.mesh_network.subscribe_to_event('agreement_validation', self._handle_agreement_validation)
                
            logger.info("Agreement validator started")
            return True
        except Exception as e:
            logger.error(f"Error starting agreement validator: {str(e)}")
            return False
            
    async def stop(self):
        """Stop the agreement validator"""
        if self.agreement_executor:
            await self.agreement_executor.stop_monitoring()
            
        logger.info("Agreement validator stopped")
        
    async def refresh_agreements(self):
        """Refresh the list of active agreements"""
        if not self.agreement_executor:
            return
            
        try:
            # Get all active agreements
            agreements = self.agreement_executor.get_active_agreements()
            
            # Update local cache
            self.active_agreements = {}
            for agreement in agreements:
                self.active_agreements[agreement.agreement_id] = {
                    "consumer_id": agreement.consumer_id,
                    "provider_id": agreement.provider_id,
                    "resource_id": agreement.resource_id,
                    "status": agreement.status,
                    "usage_limits": agreement.usage_limits,
                    "current_usage": agreement.current_usage,
                    "expires_at": agreement.expires_at.isoformat() if agreement.expires_at else None
                }
                
            logger.info(f"Refreshed {len(agreements)} active agreements")
        except Exception as e:
            logger.error(f"Error refreshing agreements: {str(e)}")
            
    async def validate_agreement(self, agreement_id: str, resource_id: str, 
                              consumer_id: str) -> Dict[str, Any]:
        """
        Validate an agreement for resource access
        
        Args:
            agreement_id: Agreement ID
            resource_id: Resource ID
            consumer_id: Consumer ID
            
        Returns:
            Validation result with status and details
        """
        if not self.agreement_executor:
            return {"valid": False, "reason": "Agreement validator not available"}
            
        try:
            # Refresh agreements if needed
            if agreement_id not in self.active_agreements:
                await self.refresh_agreements()
                
            # Check if agreement exists and is active
            if agreement_id not in self.active_agreements:
                return {
                    "valid": False, 
                    "reason": "Agreement not found or not active"
                }
                
            agreement = self.active_agreements[agreement_id]
            
            # Check consumer ID
            if agreement["consumer_id"] != consumer_id:
                return {
                    "valid": False, 
                    "reason": "Consumer ID mismatch"
                }
                
            # Check resource ID
            if agreement["resource_id"] != resource_id:
                return {
                    "valid": False, 
                    "reason": "Resource ID mismatch"
                }
                
            # Check agreement status
            if agreement["status"] != "active":
                return {
                    "valid": False, 
                    "reason": f"Agreement status is {agreement['status']}"
                }
                
            # Check expiration
            if agreement["expires_at"]:
                expiry = datetime.fromisoformat(agreement["expires_at"])
                if datetime.utcnow() > expiry:
                    return {
                        "valid": False, 
                        "reason": "Agreement expired"
                    }
                    
            return {
                "valid": True,
                "agreement": agreement
            }
        except Exception as e:
            logger.error(f"Error validating agreement {agreement_id}: {str(e)}")
            return {
                "valid": False,
                "reason": f"Validation error: {str(e)}"
            }
            
    async def record_usage(self, agreement_id: str, metric: str, 
                         quantity: float) -> Dict[str, Any]:
        """
        Record resource usage for an agreement
        
        Args:
            agreement_id: Agreement ID
            metric: Usage metric (e.g., 'api_calls', 'cpu_time')
            quantity: Usage quantity
            
        Returns:
            Recording result with status
        """
        if not self.agreement_executor:
            return {"success": False, "reason": "Agreement validator not available"}
            
        try:
            # Record usage in the agreement executor
            result = self.agreement_executor.record_usage(
                agreement_id=agreement_id,
                metric=metric,
                quantity=quantity
            )
            
            # Check if we exceeded limits
            exceeded = False
            if result.get("status") == "recorded":
                agreement = self.active_agreements.get(agreement_id, {})
                usage_limits = agreement.get("usage_limits", {})
                current_usage = result.get("current_usage", {})
                
                if metric in usage_limits and metric in current_usage:
                    if current_usage[metric] > usage_limits[metric]:
                        exceeded = True
                        
                        # Handle overage billing if billing system is available
                        if self.billing_system and agreement:
                            await self._process_overage_billing(
                                agreement_id=agreement_id,
                                metric=metric,
                                quantity=current_usage[metric] - usage_limits[metric],
                                consumer_id=agreement.get("consumer_id"),
                                provider_id=agreement.get("provider_id")
                            )
            
            return {
                "success": True,
                "limit_exceeded": exceeded,
                "current_usage": result.get("current_usage", {})
            }
        except Exception as e:
            logger.error(f"Error recording usage for agreement {agreement_id}: {str(e)}")
            return {
                "success": False,
                "reason": f"Recording error: {str(e)}"
            }
            
    async def create_agreement_from_template(self, template_type: str, consumer_id: str,
                                          provider_id: str, resource_id: str,
                                          custom_terms: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Create a new agreement from a template
        
        Args:
            template_type: Type of template (free, personal, business, enterprise)
            consumer_id: Consumer ID
            provider_id: Provider ID
            resource_id: Resource ID
            custom_terms: Custom terms to override template defaults
            
        Returns:
            Agreement creation result with status and agreement ID
        """
        if not AGREEMENT_LIBS_AVAILABLE:
            return {"success": False, "reason": "Agreement libraries not available"}
            
        try:
            # Create agreement from template
            template = StandardAgreementTemplate()
            agreement = template.create_agreement(
                template_type=template_type,
                consumer_id=consumer_id,
                provider_id=provider_id,
                resource_id=resource_id,
                custom_terms=custom_terms
            )
            
            # Submit agreement
            self.agreement_executor._save_agreement(agreement)
            
            # Add to local cache
            self.active_agreements[agreement.agreement_id] = {
                "consumer_id": agreement.consumer_id,
                "provider_id": agreement.provider_id,
                "resource_id": agreement.resource_id,
                "status": agreement.status,
                "usage_limits": agreement.usage_limits,
                "current_usage": agreement.current_usage,
                "expires_at": agreement.expires_at.isoformat() if agreement.expires_at else None
            }
            
            logger.info(f"Created new {template_type} agreement {agreement.agreement_id}")
            
            return {
                "success": True,
                "agreement_id": agreement.agreement_id,
                "agreement": self.active_agreements[agreement.agreement_id]
            }
        except Exception as e:
            logger.error(f"Error creating agreement: {str(e)}")
            return {
                "success": False,
                "reason": f"Creation error: {str(e)}"
            }
            
    async def _process_overage_billing(self, agreement_id: str, metric: str,
                                     quantity: float, consumer_id: str,
                                     provider_id: str):
        """
        Process overage billing for an agreement
        
        Args:
            agreement_id: Agreement ID
            metric: Usage metric
            quantity: Overage quantity
            consumer_id: Consumer ID
            provider_id: Provider ID
        """
        if not self.billing_system:
            return
            
        try:
            # Get agreement pricing for overages
            agreement = self.agreement_executor.get_agreement(agreement_id)
            if not agreement or not agreement.pricing:
                logger.warning(f"No pricing info for agreement {agreement_id}")
                return
                
            # Calculate overage cost
            overage_rates = agreement.pricing.get("overage_rates", {})
            if metric not in overage_rates:
                logger.warning(f"No overage rate for metric {metric} in agreement {agreement_id}")
                return
                
            rate = overage_rates[metric]
            cost = rate * quantity
            
            # Record overage in billing system
            self.billing_system.record_agreement_overage(
                agreement_id=agreement_id,
                consumer_id=consumer_id,
                provider_id=provider_id,
                metric=metric,
                quantity=quantity,
                cost=cost
            )
            
            logger.info(f"Recorded overage for agreement {agreement_id}: {quantity} {metric} at ${rate}/unit = ${cost}")
        except Exception as e:
            logger.error(f"Error processing overage billing: {str(e)}")
            
    async def _handle_resource_usage(self, data: Dict[str, Any]):
        """Handle resource usage events from the mesh"""
        agreement_id = data.get("agreement_id")
        resource_id = data.get("resource_id")
        metric = data.get("metric")
        quantity = data.get("quantity")
        
        if not agreement_id or not resource_id or not metric or quantity is None:
            logger.warning("Incomplete resource usage data received")
            return
            
        # Record the usage
        await self.record_usage(agreement_id, metric, quantity)
        
    async def _handle_agreement_validation(self, data: Dict[str, Any]):
        """Handle agreement validation requests from the mesh"""
        agreement_id = data.get("agreement_id")
        resource_id = data.get("resource_id")
        consumer_id = data.get("consumer_id")
        
        if not agreement_id or not resource_id or not consumer_id:
            logger.warning("Incomplete agreement validation data received")
            return
            
        # Validate the agreement
        result = await self.validate_agreement(agreement_id, resource_id, consumer_id)
        
        # Send response if mesh network is available
        if self.mesh_network and data.get("request_id"):
            response = {
                "type": "agreement_validation_response",
                "sender_id": self.node_id,
                "timestamp": datetime.utcnow().isoformat(),
                "data": {
                    "request_id": data.get("request_id"),
                    "result": result
                }
            }
            
            await self.mesh_network.node._broadcast_message(response)
