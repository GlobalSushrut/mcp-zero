#!/usr/bin/env python3
"""
MCP-ZERO Marketplace REST API
Provides HTTP endpoints for interacting with the MCP-ZERO marketplace
"""
import asyncio
import json
import logging
import os
import sys
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

import uvicorn
from fastapi import FastAPI, HTTPException, Depends, Query, Path, Body, Header
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from marketplace.marketplace import Marketplace
from marketplace.middleware.agreement import AgreementMiddleware, AgreementType, UsageMetric

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('marketplace_api')

# Initialize FastAPI app
app = FastAPI(
    title="MCP-ZERO Marketplace API",
    description="REST API for interacting with the MCP-ZERO marketplace",
    version="1.0.0"
)

# Add CORS middleware
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Initialize marketplace
marketplace = Marketplace(database_path="marketplace/data/marketplace.db")

# Initialize agreement middleware
agreement_middleware = AgreementMiddleware(storage_path="marketplace/data/agreements")

# Import billing endpoints router
from marketplace.api.billing_endpoints import router as billing_router

# Include billing router in the app
app.include_router(billing_router)

# API key verification
async def verify_api_key(x_api_key: str = Header(None)):
    """Verify the API key"""
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
        
    # TODO: Replace with actual API key validation
    valid_keys = os.environ.get("MCP_API_KEYS", "test-key").split(",")
    
    if x_api_key not in valid_keys:
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    return x_api_key

# Pydantic models for request/response
class ListingBase(BaseModel):
    """Base model for marketplace listings"""
    name: str
    description: str
    version: str = "1.0.0"
    type: str
    tags: List[str] = Field(default_factory=list)
    
class ListingCreate(ListingBase):
    """Model for creating a new listing"""
    pricing_model: str
    price: float = 0.0
    publisher_id: str
    metadata: Dict[str, Any] = Field(default_factory=dict)
    
class ListingResponse(ListingBase):
    """Model for listing response"""
    listing_id: str
    publisher_id: str
    created_at: str
    updated_at: str
    pricing_model: str
    price: float
    rating: float
    review_count: int
    metadata: Dict[str, Any]
    
class ReviewCreate(BaseModel):
    """Model for creating a review"""
    rating: int = Field(ge=1, le=5)
    comment: str
    reviewer_id: str
    
class ReviewResponse(BaseModel):
    """Model for review response"""
    review_id: str
    listing_id: str
    reviewer_id: str
    rating: int
    comment: str
    created_at: str
    
class TransactionCreate(BaseModel):
    """Model for creating a transaction"""
    consumer_id: str
    listing_id: str
    amount: float
    payment_method: str = "credit"
    
class TransactionResponse(BaseModel):
    """Model for transaction response"""
    transaction_id: str
    listing_id: str
    consumer_id: str
    provider_id: str
    amount: float
    status: str
    created_at: str
    payment_method: str
    
class AgreementCreate(BaseModel):
    """Model for creating an agreement"""
    consumer_id: str
    provider_id: str
    resource_id: str
    agreement_type: str = "free"
    terms: Dict[str, Any] = Field(default_factory=dict)
    usage_limits: Dict[str, int] = Field(default_factory=dict)
    pricing: Dict[str, Any] = Field(default_factory=dict)
    expiration_days: int = 365
    
class AgreementResponse(BaseModel):
    """Model for agreement response"""
    agreement_id: str
    consumer_id: str
    provider_id: str
    resource_id: str
    agreement_type: str
    status: str
    created_at: str
    effective_date: str
    expiration_date: Optional[str]
    
class UsageRecord(BaseModel):
    """Model for recording usage"""
    agreement_id: str
    metric: str
    quantity: float
    
# API endpoints
@app.get("/")
async def root():
    """Root endpoint"""
    return {
        "name": "MCP-ZERO Marketplace API",
        "version": "1.0.0",
        "status": "online",
        "timestamp": datetime.now().isoformat()
    }

# Listings endpoints
@app.get("/listings", response_model=List[ListingResponse])
async def get_listings(
    type: Optional[str] = None,
    tag: Optional[str] = None,
    search: Optional[str] = None,
    limit: int = 20,
    offset: int = 0
):
    """Get marketplace listings with optional filters"""
    filters = {}
    if type:
        filters["type"] = type
    if tag:
        filters["tag"] = tag
    
    listings = marketplace.search_listings(search=search, filters=filters, limit=limit, offset=offset)
    return [ListingResponse(**listing) for listing in listings]

@app.post("/listings", response_model=ListingResponse, dependencies=[Depends(verify_api_key)])
async def create_listing(listing: ListingCreate):
    """Create a new listing"""
    listing_dict = listing.dict()
    listing_id = marketplace.create_listing(
        name=listing_dict["name"],
        description=listing_dict["description"],
        version=listing_dict["version"],
        type=listing_dict["type"],
        pricing_model=listing_dict["pricing_model"],
        price=listing_dict["price"],
        publisher_id=listing_dict["publisher_id"],
        tags=listing_dict["tags"],
        metadata=listing_dict["metadata"]
    )
    
    created_listing = marketplace.get_listing(listing_id)
    if not created_listing:
        raise HTTPException(status_code=500, detail="Failed to create listing")
        
    return ListingResponse(**created_listing)

@app.get("/listings/{listing_id}", response_model=ListingResponse)
async def get_listing(listing_id: str):
    """Get a listing by ID"""
    listing = marketplace.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    return ListingResponse(**listing)

@app.delete("/listings/{listing_id}", dependencies=[Depends(verify_api_key)])
async def delete_listing(listing_id: str):
    """Delete a listing"""
    deleted = marketplace.delete_listing(listing_id)
    if not deleted:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    return {"message": "Listing deleted"}

# Reviews endpoints
@app.get("/listings/{listing_id}/reviews")
async def get_reviews(listing_id: str):
    """Get reviews for a listing"""
    reviews = marketplace.get_reviews(listing_id)
    return reviews

@app.post("/listings/{listing_id}/reviews", response_model=ReviewResponse, dependencies=[Depends(verify_api_key)])
async def add_review(listing_id: str, review: ReviewCreate):
    """Add a review to a listing"""
    listing = marketplace.get_listing(listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    review_id = marketplace.add_review(
        listing_id=listing_id,
        reviewer_id=review.reviewer_id,
        rating=review.rating,
        comment=review.comment
    )
    
    created_review = marketplace.get_review(review_id)
    if not created_review:
        raise HTTPException(status_code=500, detail="Failed to create review")
        
    return ReviewResponse(**created_review)

# Transactions endpoints
@app.post("/transactions", response_model=TransactionResponse, dependencies=[Depends(verify_api_key)])
async def create_transaction(transaction: TransactionCreate):
    """Create a new transaction"""
    listing = marketplace.get_listing(transaction.listing_id)
    if not listing:
        raise HTTPException(status_code=404, detail="Listing not found")
        
    transaction_id = marketplace.record_transaction(
        listing_id=transaction.listing_id,
        consumer_id=transaction.consumer_id,
        amount=transaction.amount,
        payment_method=transaction.payment_method
    )
    
    created_transaction = marketplace.get_transaction(transaction_id)
    if not created_transaction:
        raise HTTPException(status_code=500, detail="Failed to create transaction")
        
    return TransactionResponse(**created_transaction)

@app.get("/transactions/{transaction_id}", response_model=TransactionResponse, dependencies=[Depends(verify_api_key)])
async def get_transaction(transaction_id: str):
    """Get a transaction by ID"""
    transaction = marketplace.get_transaction(transaction_id)
    if not transaction:
        raise HTTPException(status_code=404, detail="Transaction not found")
        
    return TransactionResponse(**transaction)

# Agreement endpoints
@app.post("/agreements", response_model=AgreementResponse, dependencies=[Depends(verify_api_key)])
async def create_agreement(agreement: AgreementCreate):
    """Create a new agreement"""
    try:
        agreement_type = AgreementType(agreement.agreement_type)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid agreement type: {agreement.agreement_type}")
        
    created_agreement = agreement_middleware.create_agreement(
        consumer_id=agreement.consumer_id,
        provider_id=agreement.provider_id,
        resource_id=agreement.resource_id,
        agreement_type=agreement_type
    )
    
    # Set additional properties
    created_agreement.set_terms(agreement.terms)
    
    # Convert usage limits to enum keys
    usage_limits = {}
    for metric_name, limit in agreement.usage_limits.items():
        try:
            metric = UsageMetric(metric_name)
            usage_limits[metric] = limit
        except ValueError:
            logger.warning(f"Invalid usage metric: {metric_name}, skipping")
    
    created_agreement.set_usage_limits(usage_limits)
    created_agreement.set_pricing(agreement.pricing)
    created_agreement.set_expiration(agreement.expiration_days)
    
    # Submit the agreement
    agreement_middleware.submit_agreement(created_agreement)
    
    # Get the created agreement
    return AgreementResponse(
        agreement_id=created_agreement.agreement_id,
        consumer_id=created_agreement.consumer_id,
        provider_id=created_agreement.provider_id,
        resource_id=created_agreement.resource_id,
        agreement_type=created_agreement.agreement_type.value,
        status=created_agreement.status.value,
        created_at=created_agreement.created_at.isoformat(),
        effective_date=created_agreement.effective_date.isoformat(),
        expiration_date=created_agreement.expiration_date.isoformat() if created_agreement.expiration_date else None
    )

@app.get("/agreements/{agreement_id}", response_model=AgreementResponse, dependencies=[Depends(verify_api_key)])
async def get_agreement(agreement_id: str):
    """Get an agreement by ID"""
    agreement = agreement_middleware.get_agreement(agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
        
    return AgreementResponse(
        agreement_id=agreement.agreement_id,
        consumer_id=agreement.consumer_id,
        provider_id=agreement.provider_id,
        resource_id=agreement.resource_id,
        agreement_type=agreement.agreement_type.value,
        status=agreement.status.value,
        created_at=agreement.created_at.isoformat(),
        effective_date=agreement.effective_date.isoformat(),
        expiration_date=agreement.expiration_date.isoformat() if agreement.expiration_date else None
    )

@app.post("/agreements/{agreement_id}/sign", dependencies=[Depends(verify_api_key)])
async def sign_agreement(
    agreement_id: str,
    party_id: str = Body(..., embed=True),
    signature: str = Body(..., embed=True)
):
    """Sign an agreement"""
    agreement = agreement_middleware.get_agreement(agreement_id)
    if not agreement:
        raise HTTPException(status_code=404, detail="Agreement not found")
        
    success = agreement.sign(party_id, signature)
    if not success:
        raise HTTPException(status_code=400, detail="Failed to sign agreement")
        
    # Save the updated agreement
    agreement_middleware._save_agreement(agreement)
    
    return {"message": "Agreement signed"}

@app.post("/usage", dependencies=[Depends(verify_api_key)])
async def record_usage(usage: UsageRecord):
    """Record usage against an agreement"""
    try:
        metric = UsageMetric(usage.metric)
    except ValueError:
        raise HTTPException(status_code=400, detail=f"Invalid usage metric: {usage.metric}")
        
    result = agreement_middleware.record_usage(
        agreement_id=usage.agreement_id,
        metric=metric,
        quantity=usage.quantity
    )
    
    if not result["success"]:
        raise HTTPException(status_code=400, detail=result["reason"])
        
    return result

# Health check endpoint
@app.get("/health")
async def health_check():
    """Health check endpoint"""
    return {
        "status": "healthy",
        "timestamp": datetime.now().isoformat()
    }

# Run the API server
def start_api(host: str = "0.0.0.0", port: int = 8000):
    """Start the API server"""
    uvicorn.run(app, host=host, port=port)
    
if __name__ == "__main__":
    start_api()
