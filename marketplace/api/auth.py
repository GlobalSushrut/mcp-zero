#!/usr/bin/env python3
"""
MCP-ZERO Marketplace API - Authentication Module
Handles API key verification and authentication
"""
import os
import logging
from fastapi import HTTPException, Header

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('auth')

async def verify_api_key(x_api_key: str = Header(None)):
    """
    Verify the API key provided in the request header
    
    Args:
        x_api_key: API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing or invalid
    """
    if not x_api_key:
        raise HTTPException(status_code=401, detail="API key is required")
        
    # Get valid API keys from environment variable
    valid_keys = os.environ.get("MCP_API_KEYS", "test-key").split(",")
    
    if x_api_key not in valid_keys:
        logger.warning(f"Invalid API key attempt: {x_api_key[:5]}...")
        raise HTTPException(status_code=401, detail="Invalid API key")
        
    return x_api_key

def get_role_from_api_key(api_key: str) -> str:
    """
    Get user role from API key
    
    Args:
        api_key: The validated API key
        
    Returns:
        Role associated with the API key (admin, developer, user)
    """
    # In a production system, this would query a database
    # For now, we use a simple mapping in environment variables
    admin_keys = os.environ.get("MCP_ADMIN_KEYS", "admin-key").split(",")
    developer_keys = os.environ.get("MCP_DEVELOPER_KEYS", "dev-key").split(",")
    
    if api_key in admin_keys:
        return "admin"
    elif api_key in developer_keys:
        return "developer"
    else:
        return "user"

async def require_admin(x_api_key: str = Header(None)):
    """
    Verify the API key and ensure it has admin privileges
    
    Args:
        x_api_key: API key from the X-API-Key header
        
    Returns:
        The validated API key
        
    Raises:
        HTTPException: If API key is missing, invalid, or lacks admin privileges
    """
    api_key = await verify_api_key(x_api_key)
    role = get_role_from_api_key(api_key)
    
    if role != "admin":
        raise HTTPException(status_code=403, detail="Admin privileges required")
        
    return api_key
