#!/usr/bin/env python3
"""
MCP-ZERO Standard Agreement Templates
Pre-defined templates for common agreement types
"""
import json
import logging
import os
from datetime import datetime, timedelta
from typing import Dict, Any, List, Optional

from marketplace.middleware.agreement import AgreementMiddleware, AgreementType, UsageMetric

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('agreement_templates')

class AgreementTemplates:
    """
    Standard agreement templates for MCP-ZERO
    Provides predefined templates for different usage levels
    """
    
    @staticmethod
    def free_tier_template(consumer_id: str, provider_id: str, resource_id: str) -> Dict[str, Any]:
        """
        Free tier agreement template with basic usage limits
        
        Args:
            consumer_id: ID of the consumer party
            provider_id: ID of the provider party
            resource_id: ID of the resource being accessed
            
        Returns:
            Complete agreement template as dictionary
        """
        return {
            "consumer_id": consumer_id,
            "provider_id": provider_id,
            "resource_id": resource_id,
            "agreement_type": "free",
            "terms": {
                "service_level": "basic",
                "support": "community",
                "updates": "security only",
                "termination_notice": "none"
            },
            "usage_limits": {
                "API_CALLS": 100,
                "CPU_TIME": 10,
                "MEMORY": 256,
                "STORAGE": 100,
                "BANDWIDTH": 1000
            },
            "pricing": {
                "base_fee": 0.0,
                "overage_rates": {}
            },
            "expiration_days": 30
        }
    
    @staticmethod
    def personal_tier_template(consumer_id: str, provider_id: str, resource_id: str) -> Dict[str, Any]:
        """
        Personal tier agreement template with moderate usage limits
        
        Args:
            consumer_id: ID of the consumer party
            provider_id: ID of the provider party
            resource_id: ID of the resource being accessed
            
        Returns:
            Complete agreement template as dictionary
        """
        return {
            "consumer_id": consumer_id,
            "provider_id": provider_id,
            "resource_id": resource_id,
            "agreement_type": "personal",
            "terms": {
                "service_level": "standard",
                "support": "email",
                "updates": "feature and security",
                "termination_notice": "7 days"
            },
            "usage_limits": {
                "API_CALLS": 1000,
                "CPU_TIME": 60,
                "MEMORY": 1024,
                "STORAGE": 1000,
                "BANDWIDTH": 5000
            },
            "pricing": {
                "base_fee": 9.99,
                "overage_rates": {
                    "api_calls": 0.001,
                    "cpu_time": 0.01,
                    "memory": 0.005,
                    "storage": 0.0005,
                    "bandwidth": 0.0001
                }
            },
            "expiration_days": 30
        }
    
    @staticmethod
    def business_tier_template(consumer_id: str, provider_id: str, resource_id: str) -> Dict[str, Any]:
        """
        Business tier agreement template with high usage limits
        
        Args:
            consumer_id: ID of the consumer party
            provider_id: ID of the provider party
            resource_id: ID of the resource being accessed
            
        Returns:
            Complete agreement template as dictionary
        """
        return {
            "consumer_id": consumer_id,
            "provider_id": provider_id,
            "resource_id": resource_id,
            "agreement_type": "business",
            "terms": {
                "service_level": "premium",
                "support": "priority",
                "updates": "feature and security",
                "termination_notice": "30 days",
                "sla": {
                    "uptime": 99.9,
                    "response_time": "4 hours"
                }
            },
            "usage_limits": {
                "API_CALLS": 10000,
                "CPU_TIME": 600,
                "MEMORY": 4096,
                "STORAGE": 10000,
                "BANDWIDTH": 50000
            },
            "pricing": {
                "base_fee": 49.99,
                "overage_rates": {
                    "api_calls": 0.0008,
                    "cpu_time": 0.008,
                    "memory": 0.004,
                    "storage": 0.0004,
                    "bandwidth": 0.00008
                }
            },
            "expiration_days": 365
        }
    
    @staticmethod
    def enterprise_tier_template(consumer_id: str, provider_id: str, resource_id: str) -> Dict[str, Any]:
        """
        Enterprise tier agreement template with very high usage limits
        
        Args:
            consumer_id: ID of the consumer party
            provider_id: ID of the provider party
            resource_id: ID of the resource being accessed
            
        Returns:
            Complete agreement template as dictionary
        """
        return {
            "consumer_id": consumer_id,
            "provider_id": provider_id,
            "resource_id": resource_id,
            "agreement_type": "enterprise",
            "terms": {
                "service_level": "enterprise",
                "support": "dedicated",
                "updates": "feature and security",
                "termination_notice": "90 days",
                "sla": {
                    "uptime": 99.99,
                    "response_time": "1 hour"
                },
                "custom_integration": True,
                "white_label": True
            },
            "usage_limits": {
                "API_CALLS": 1000000,
                "CPU_TIME": 10000,
                "MEMORY": 32768,
                "STORAGE": 100000,
                "BANDWIDTH": 500000
            },
            "pricing": {
                "base_fee": 499.99,
                "overage_rates": {
                    "api_calls": 0.0005,
                    "cpu_time": 0.005,
                    "memory": 0.0025,
                    "storage": 0.0002,
                    "bandwidth": 0.00005
                },
                "custom_pricing": True
            },
            "expiration_days": 365
        }
    
    @staticmethod
    def create_from_template(template_data: Dict[str, Any], agreement_middleware: AgreementMiddleware) -> str:
        """
        Create an agreement from template data
        
        Args:
            template_data: Agreement template dictionary
            agreement_middleware: AgreementMiddleware instance
            
        Returns:
            Agreement ID
        """
        try:
            # Extract key fields
            consumer_id = template_data["consumer_id"]
            provider_id = template_data["provider_id"]
            resource_id = template_data["resource_id"]
            agreement_type_str = template_data["agreement_type"]
            
            # Map string to enum
            agreement_type = AgreementType(agreement_type_str.upper())
            
            # Create the agreement
            agreement = agreement_middleware.create_agreement(
                consumer_id=consumer_id,
                provider_id=provider_id,
                resource_id=resource_id,
                agreement_type=agreement_type
            )
            
            # Set terms
            if "terms" in template_data:
                agreement.set_terms(template_data["terms"])
            
            # Set usage limits
            if "usage_limits" in template_data:
                usage_limits = {}
                for metric_name, limit in template_data["usage_limits"].items():
                    try:
                        metric = UsageMetric[metric_name]
                        usage_limits[metric] = limit
                    except (KeyError, ValueError):
                        logger.warning(f"Invalid usage metric: {metric_name}, skipping")
                
                agreement.set_usage_limits(usage_limits)
            
            # Set pricing
            if "pricing" in template_data:
                agreement.set_pricing(template_data["pricing"])
            
            # Set expiration
            if "expiration_days" in template_data:
                agreement.set_expiration(template_data["expiration_days"])
            
            # Submit the agreement
            agreement_middleware.submit_agreement(agreement)
            
            logger.info(f"Created agreement from template: {agreement.agreement_id}")
            return agreement.agreement_id
            
        except Exception as e:
            logger.error(f"Error creating agreement from template: {str(e)}")
            raise
