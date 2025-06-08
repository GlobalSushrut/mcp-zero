#!/usr/bin/env python3
"""
MCP-ZERO Marketplace Agreement Middleware
Handles commercial agreements and licensing for MCP-ZERO agents and plugins
"""
import json
import logging
import os
import time
import uuid
from datetime import datetime, timedelta
from enum import Enum
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('agreement_middleware')

class AgreementType(Enum):
    """Types of marketplace agreements"""
    FREE = "free"
    PERSONAL = "personal"
    BUSINESS = "business"
    ENTERPRISE = "enterprise"
    CUSTOM = "custom"

class AgreementStatus(Enum):
    """Possible statuses for agreements"""
    DRAFT = "draft"
    PENDING = "pending"
    ACTIVE = "active"
    SUSPENDED = "suspended"
    TERMINATED = "terminated"
    EXPIRED = "expired"

class UsageMetric(Enum):
    """Metrics for measuring agent/plugin usage"""
    EXECUTION_COUNT = "execution_count"
    CPU_TIME = "cpu_time"
    MEMORY_USAGE = "memory_usage"
    API_CALLS = "api_calls"
    STORAGE = "storage"
    BANDWIDTH = "bandwidth"
    CUSTOM = "custom"

class Agreement:
    """Represents a commercial agreement between parties"""
    
    def __init__(self,
                agreement_id: Optional[str] = None,
                consumer_id: str = "",
                provider_id: str = "",
                resource_id: str = "",
                agreement_type: AgreementType = AgreementType.FREE,
                status: AgreementStatus = AgreementStatus.DRAFT):
        """Initialize a new agreement"""
        self.agreement_id = agreement_id or str(uuid.uuid4())
        self.consumer_id = consumer_id
        self.provider_id = provider_id
        self.resource_id = resource_id
        self.agreement_type = agreement_type
        self.status = status
        self.created_at = datetime.now()
        self.updated_at = self.created_at
        self.effective_date = self.created_at
        self.expiration_date = None
        self.terms = {}
        self.usage_limits = {}
        self.pricing = {}
        self.signatures = {}
        self.audit_trail = []
        
        # Add initial audit entry
        self._add_audit_entry("created", "Agreement created")
        
    def _add_audit_entry(self, action: str, message: str, details: Optional[Dict] = None) -> None:
        """Add an entry to the audit trail"""
        self.audit_trail.append({
            "timestamp": datetime.now().isoformat(),
            "action": action,
            "message": message,
            "details": details or {}
        })
        self.updated_at = datetime.now()
        
    def set_terms(self, terms: Dict[str, Any]) -> None:
        """Set the agreement terms"""
        self.terms = terms
        self._add_audit_entry("terms_updated", "Agreement terms updated")
        
    def set_usage_limits(self, metrics: Dict[UsageMetric, int]) -> None:
        """Set usage limits for the agreement"""
        self.usage_limits = {metric.value: limit for metric, limit in metrics.items()}
        self._add_audit_entry("limits_updated", "Usage limits updated")
        
    def set_pricing(self, pricing_data: Dict[str, Any]) -> None:
        """Set pricing details for the agreement"""
        self.pricing = pricing_data
        self._add_audit_entry("pricing_updated", "Pricing information updated")
        
    def set_expiration(self, days: int) -> None:
        """Set the agreement expiration date"""
        self.expiration_date = self.effective_date + timedelta(days=days)
        self._add_audit_entry("expiration_set", f"Expiration date set to {self.expiration_date}")
        
    def sign(self, party_id: str, signature: str) -> bool:
        """Add a signature to the agreement"""
        if party_id not in [self.consumer_id, self.provider_id]:
            return False
            
        self.signatures[party_id] = {
            "signature": signature,
            "timestamp": datetime.now().isoformat()
        }
        
        self._add_audit_entry("signed", f"Agreement signed by {party_id}")
        
        # If both parties have signed, activate the agreement
        if len(self.signatures) == 2:
            self.activate()
            
        return True
        
    def activate(self) -> bool:
        """Activate the agreement"""
        if self.status != AgreementStatus.PENDING:
            return False
            
        self.status = AgreementStatus.ACTIVE
        self.effective_date = datetime.now()
        if not self.expiration_date:
            # Default to 1 year if not specified
            self.expiration_date = self.effective_date + timedelta(days=365)
            
        self._add_audit_entry("activated", "Agreement activated")
        return True
        
    def suspend(self, reason: str) -> bool:
        """Suspend the agreement"""
        if self.status != AgreementStatus.ACTIVE:
            return False
            
        self.status = AgreementStatus.SUSPENDED
        self._add_audit_entry("suspended", f"Agreement suspended: {reason}")
        return True
        
    def terminate(self, reason: str) -> bool:
        """Terminate the agreement"""
        if self.status in [AgreementStatus.TERMINATED, AgreementStatus.EXPIRED]:
            return False
            
        self.status = AgreementStatus.TERMINATED
        self._add_audit_entry("terminated", f"Agreement terminated: {reason}")
        return True
        
    def check_expiration(self) -> bool:
        """Check if the agreement has expired"""
        if self.status != AgreementStatus.ACTIVE:
            return False
            
        if self.expiration_date and datetime.now() > self.expiration_date:
            self.status = AgreementStatus.EXPIRED
            self._add_audit_entry("expired", "Agreement expired")
            return True
            
        return False
        
    def to_dict(self) -> Dict[str, Any]:
        """Convert agreement to dictionary representation"""
        return {
            "agreement_id": self.agreement_id,
            "consumer_id": self.consumer_id,
            "provider_id": self.provider_id,
            "resource_id": self.resource_id,
            "agreement_type": self.agreement_type.value,
            "status": self.status.value,
            "created_at": self.created_at.isoformat(),
            "updated_at": self.updated_at.isoformat(),
            "effective_date": self.effective_date.isoformat(),
            "expiration_date": self.expiration_date.isoformat() if self.expiration_date else None,
            "terms": self.terms,
            "usage_limits": self.usage_limits,
            "pricing": self.pricing,
            "signatures": self.signatures,
            "audit_trail": self.audit_trail
        }
        
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Agreement':
        """Create agreement from dictionary representation"""
        agreement = cls(
            agreement_id=data.get("agreement_id"),
            consumer_id=data.get("consumer_id", ""),
            provider_id=data.get("provider_id", ""),
            resource_id=data.get("resource_id", ""),
            agreement_type=AgreementType(data.get("agreement_type", "free")),
            status=AgreementStatus(data.get("status", "draft"))
        )
        
        # Set attributes from data
        agreement.created_at = datetime.fromisoformat(data.get("created_at", datetime.now().isoformat()))
        agreement.updated_at = datetime.fromisoformat(data.get("updated_at", datetime.now().isoformat()))
        agreement.effective_date = datetime.fromisoformat(data.get("effective_date", datetime.now().isoformat()))
        
        if data.get("expiration_date"):
            agreement.expiration_date = datetime.fromisoformat(data["expiration_date"])
            
        agreement.terms = data.get("terms", {})
        agreement.usage_limits = data.get("usage_limits", {})
        agreement.pricing = data.get("pricing", {})
        agreement.signatures = data.get("signatures", {})
        agreement.audit_trail = data.get("audit_trail", [])
        
        return agreement


class AgreementMiddleware:
    """Middleware for managing commercial agreements in MCP-ZERO marketplace"""
    
    def __init__(self, storage_path: str = "agreements"):
        """Initialize the agreement middleware"""
        self.storage_path = storage_path
        os.makedirs(self.storage_path, exist_ok=True)
        logger.info(f"Agreement middleware initialized with storage at {storage_path}")
        
    def create_agreement(self,
                        consumer_id: str,
                        provider_id: str,
                        resource_id: str,
                        agreement_type: AgreementType = AgreementType.FREE) -> Agreement:
        """Create a new agreement between parties"""
        agreement = Agreement(
            consumer_id=consumer_id,
            provider_id=provider_id,
            resource_id=resource_id,
            agreement_type=agreement_type,
            status=AgreementStatus.DRAFT
        )
        
        # Save the agreement
        self._save_agreement(agreement)
        
        logger.info(f"Created agreement {agreement.agreement_id} between {consumer_id} and {provider_id}")
        return agreement
        
    def get_agreement(self, agreement_id: str) -> Optional[Agreement]:
        """Get an agreement by ID"""
        agreement_path = os.path.join(self.storage_path, f"{agreement_id}.json")
        
        if not os.path.exists(agreement_path):
            return None
            
        try:
            with open(agreement_path, 'r') as f:
                data = json.load(f)
                return Agreement.from_dict(data)
        except Exception as e:
            logger.error(f"Failed to load agreement {agreement_id}: {e}")
            return None
            
    def _save_agreement(self, agreement: Agreement) -> bool:
        """Save an agreement to storage"""
        agreement_path = os.path.join(self.storage_path, f"{agreement.agreement_id}.json")
        
        try:
            with open(agreement_path, 'w') as f:
                json.dump(agreement.to_dict(), f, indent=2)
            return True
        except Exception as e:
            logger.error(f"Failed to save agreement {agreement.agreement_id}: {e}")
            return False
            
    def submit_agreement(self, agreement: Agreement) -> bool:
        """Submit an agreement for review/approval"""
        if agreement.status != AgreementStatus.DRAFT:
            logger.warning(f"Cannot submit agreement {agreement.agreement_id}: not in draft status")
            return False
            
        agreement.status = AgreementStatus.PENDING
        agreement._add_audit_entry("submitted", "Agreement submitted for approval")
        
        return self._save_agreement(agreement)
        
    def check_agreement_validity(self, agreement_id: str, resource_id: str) -> Dict[str, Any]:
        """Check if an agreement is valid for a specific resource"""
        agreement = self.get_agreement(agreement_id)
        
        if not agreement:
            return {
                "valid": False,
                "reason": "Agreement not found"
            }
            
        # Check resource match
        if agreement.resource_id != resource_id:
            return {
                "valid": False,
                "reason": "Resource mismatch"
            }
            
        # Check status
        if agreement.status != AgreementStatus.ACTIVE:
            return {
                "valid": False,
                "reason": f"Agreement not active (status: {agreement.status.value})"
            }
            
        # Check expiration
        if agreement.check_expiration():
            return {
                "valid": False,
                "reason": "Agreement expired"
            }
            
        return {
            "valid": True,
            "agreement_type": agreement.agreement_type.value,
            "consumer_id": agreement.consumer_id,
            "provider_id": agreement.provider_id
        }
        
    def record_usage(self, 
                    agreement_id: str, 
                    metric: UsageMetric, 
                    quantity: float) -> Dict[str, Any]:
        """Record usage against an agreement"""
        agreement = self.get_agreement(agreement_id)
        
        if not agreement:
            return {
                "success": False,
                "reason": "Agreement not found"
            }
            
        if agreement.status != AgreementStatus.ACTIVE:
            return {
                "success": False,
                "reason": f"Agreement not active (status: {agreement.status.value})"
            }
            
        # Check against limits
        metric_key = metric.value
        current_limit = agreement.usage_limits.get(metric_key, float('inf'))
        
        # Add to audit trail
        agreement._add_audit_entry(
            "usage_recorded", 
            f"Recorded {quantity} units of {metric_key}",
            {"metric": metric_key, "quantity": quantity}
        )
        
        # Save the updated agreement
        self._save_agreement(agreement)
        
        # Check if usage exceeds limits
        if current_limit != float('inf') and quantity > current_limit:
            return {
                "success": True,
                "warning": "Usage exceeds agreement limits",
                "limit": current_limit,
                "usage": quantity
            }
            
        return {
            "success": True
        }
