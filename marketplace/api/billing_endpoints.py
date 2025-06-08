#!/usr/bin/env python3
"""
MCP-ZERO Marketplace API - Billing Endpoints
REST API endpoints for the MCP-ZERO billing system
"""
import os
import logging
from typing import List, Dict, Optional, Any
from fastapi import APIRouter, HTTPException, Depends, Header, Query
from pydantic import BaseModel, Field

from marketplace.billing.billing_system import BillingSystem
from marketplace.api.auth import verify_api_key

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('billing_api')

# Initialize router
router = APIRouter(prefix="/billing", tags=["billing"])

# Initialize billing system
billing_system = BillingSystem()

# ----- Pydantic Models -----

class WalletCreate(BaseModel):
    user_id: str

class WalletResponse(BaseModel):
    wallet_id: str
    user_id: str
    balance: float
    created_at: str

class DepositRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None

class WithdrawRequest(BaseModel):
    amount: float = Field(..., gt=0)
    description: Optional[str] = None
    reference_id: Optional[str] = None

class TransactionResponse(BaseModel):
    success: bool
    transaction_id: Optional[str] = None
    wallet_id: Optional[str] = None
    amount: Optional[float] = None
    new_balance: Optional[float] = None
    error: Optional[str] = None

class UsageRecord(BaseModel):
    agent_id: str
    usage_type: str
    quantity: float = Field(..., gt=0)
    unit: str

class PriceConfig(BaseModel):
    usage_type: str
    price_per_unit: float = Field(..., ge=0)
    tier_start: Optional[float] = None
    tier_end: Optional[float] = None

class RevenueShareConfig(BaseModel):
    resource_type: str
    platform_share: float = Field(..., ge=0, le=100)
    developer_share: float = Field(..., ge=0, le=100)
    provider_share: float = Field(..., ge=0, le=100)
    resource_id: Optional[str] = None

class AgentPurchaseRequest(BaseModel):
    buyer_id: str
    seller_id: str
    agent_id: str
    amount: float = Field(..., gt=0)
    provider_id: Optional[str] = None

class InvoiceResponse(BaseModel):
    success: bool
    invoice_id: Optional[str] = None
    user_id: Optional[str] = None
    total_cost: Optional[float] = None
    error: Optional[str] = None

# ----- API Endpoints -----

@router.post("/wallets", response_model=WalletResponse, status_code=201)
async def create_wallet(request: WalletCreate, api_key: str = Depends(verify_api_key)):
    """Create a new wallet for a user"""
    result = billing_system.wallet.create_wallet(request.user_id)
    
    if "error" in result:
        raise HTTPException(status_code=400, detail=result["error"])
        
    return result

@router.get("/wallets/{wallet_id}", response_model=WalletResponse)
async def get_wallet(wallet_id: str, api_key: str = Depends(verify_api_key)):
    """Get wallet information"""
    result = billing_system.wallet.get_wallet(wallet_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Wallet {wallet_id} not found")
        
    return result

@router.get("/wallets/by-user/{user_id}", response_model=WalletResponse)
async def get_user_wallet(user_id: str, api_key: str = Depends(verify_api_key)):
    """Get wallet by user ID"""
    result = billing_system.wallet.get_wallet_by_user(user_id)
    
    if not result:
        raise HTTPException(status_code=404, detail=f"Wallet for user {user_id} not found")
        
    return result

@router.post("/wallets/{wallet_id}/deposit", response_model=TransactionResponse)
async def deposit_funds(wallet_id: str, request: DepositRequest, api_key: str = Depends(verify_api_key)):
    """Add funds to a wallet"""
    result = billing_system.wallet.deposit(
        wallet_id,
        request.amount,
        reference_id=request.reference_id,
        description=request.description
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Deposit failed"))
        
    return result

@router.post("/wallets/{wallet_id}/withdraw", response_model=TransactionResponse)
async def withdraw_funds(wallet_id: str, request: WithdrawRequest, api_key: str = Depends(verify_api_key)):
    """Withdraw funds from a wallet"""
    result = billing_system.wallet.withdraw(
        wallet_id,
        request.amount,
        reference_id=request.reference_id,
        description=request.description
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Withdrawal failed"))
        
    return result

@router.get("/wallets/{wallet_id}/transactions")
async def get_transactions(wallet_id: str, limit: int = 20, offset: int = 0, api_key: str = Depends(verify_api_key)):
    """Get transaction history for a wallet"""
    transactions = billing_system.wallet.get_transactions(wallet_id, limit=limit, offset=offset)
    return {"wallet_id": wallet_id, "transactions": transactions}

@router.post("/usage/record")
async def record_usage(record: UsageRecord, api_key: str = Depends(verify_api_key)):
    """Record agent usage for billing"""
    result = billing_system.track_agent_usage(
        record.agent_id,
        record.agent_id,  # Using agent_id as user_id for simplicity
        record.usage_type,
        record.quantity,
        record.unit
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to record usage"))
        
    return result

@router.get("/usage/{user_id}")
async def get_usage(
    user_id: str, 
    agent_id: str = None, 
    usage_type: str = None, 
    start_time: str = None, 
    end_time: str = None, 
    include_billed: bool = True,
    api_key: str = Depends(verify_api_key)
):
    """Get usage records for a user"""
    records = billing_system.usage_tracker.get_usage(
        user_id=user_id,
        agent_id=agent_id,
        usage_type=usage_type,
        start_time=start_time,
        end_time=end_time,
        include_billed=include_billed
    )
    
    return {"user_id": user_id, "records": records}

@router.post("/pricing")
async def set_pricing(price: PriceConfig, api_key: str = Depends(verify_api_key)):
    """Set pricing for a usage type"""
    result = billing_system.usage_tracker.set_price(
        price.usage_type,
        price.price_per_unit,
        tier_start=price.tier_start,
        tier_end=price.tier_end
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to set pricing"))
        
    return result

@router.get("/pricing/{usage_type}")
async def get_pricing(usage_type: str, api_key: str = Depends(verify_api_key)):
    """Get current pricing for a usage type"""
    pricing = billing_system.usage_tracker.get_pricing(usage_type)
    return {"usage_type": usage_type, "pricing_tiers": pricing}

@router.post("/revenue/shares")
async def set_revenue_shares(config: RevenueShareConfig, api_key: str = Depends(verify_api_key)):
    """Set revenue sharing configuration"""
    result = billing_system.revenue_sharing.set_share_configuration(
        config.resource_type,
        config.platform_share,
        config.developer_share,
        config.provider_share,
        resource_id=config.resource_id
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to set revenue shares"))
        
    return result

@router.get("/revenue/shares/{resource_type}")
async def get_revenue_shares(resource_type: str, resource_id: str = None, api_key: str = Depends(verify_api_key)):
    """Get revenue sharing configuration"""
    shares = billing_system.revenue_sharing.get_share_configuration(resource_type, resource_id)
    return shares

@router.post("/revenue/earnings/{user_id}")
async def get_user_earnings(user_id: str, api_key: str = Depends(verify_api_key)):
    """Get earnings information for a user"""
    earnings = billing_system.revenue_sharing.get_user_earnings(user_id)
    return earnings

@router.post("/transactions/purchase")
async def process_purchase(purchase: AgentPurchaseRequest, api_key: str = Depends(verify_api_key)):
    """Process an agent purchase transaction"""
    result = billing_system.process_agent_purchase(
        purchase.buyer_id,
        purchase.seller_id,
        purchase.agent_id,
        purchase.amount,
        provider_id=purchase.provider_id
    )
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Purchase failed"))
        
    return result

@router.post("/invoices/generate/{user_id}", response_model=InvoiceResponse)
async def generate_invoice(user_id: str, api_key: str = Depends(verify_api_key)):
    """Generate an invoice for the current billing cycle"""
    result = billing_system.generate_invoice(user_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to generate invoice"))
        
    return result

@router.post("/invoices/{invoice_id}/pay")
async def pay_invoice(invoice_id: str, user_id: str, api_key: str = Depends(verify_api_key)):
    """Pay an invoice from the user's wallet"""
    result = billing_system.pay_invoice(invoice_id, user_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Payment failed"))
        
    return result

@router.get("/summary/{user_id}")
async def get_financial_summary(user_id: str, api_key: str = Depends(verify_api_key)):
    """Get complete financial summary for a user"""
    result = billing_system.get_user_financial_summary(user_id)
    
    if not result.get("success", False):
        raise HTTPException(status_code=400, detail=result.get("error", "Failed to get summary"))
        
    return result
