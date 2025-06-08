#!/usr/bin/env python3
"""
MCP-ZERO Revenue Sharing System
Handles revenue allocation between platform, developers, and resource providers
"""
import json
import logging
import os
import sqlite3
import time
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('revenue_sharing')

class RevenueSharing:
    """Revenue sharing system for MCP-ZERO marketplace"""
    
    def __init__(self, database_path: str = "marketplace/data/revenue.db"):
        """Initialize the revenue sharing system"""
        self.database_path = database_path
        self._ensure_database()
        
        # Default revenue share percentages
        self.default_shares = {
            "platform": 10.0,      # 10% to platform
            "developer": 70.0,     # 70% to agent/plugin developer
            "provider": 20.0       # 20% to infrastructure/resource provider
        }
        
        logger.info(f"Revenue sharing system initialized with database at {database_path}")
        
    def _ensure_database(self) -> None:
        """Ensure the database exists and has the required tables"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create revenue share configurations table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS share_configurations (
            config_id TEXT PRIMARY KEY,
            resource_type TEXT NOT NULL,
            resource_id TEXT,
            platform_share REAL NOT NULL,
            developer_share REAL NOT NULL,
            provider_share REAL NOT NULL,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create revenue distribution records table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS revenue_distributions (
            distribution_id TEXT PRIMARY KEY,
            transaction_id TEXT NOT NULL,
            resource_id TEXT NOT NULL,
            total_amount REAL NOT NULL,
            platform_amount REAL NOT NULL,
            developer_amount REAL NOT NULL,
            provider_amount REAL NOT NULL,
            platform_id TEXT,
            developer_id TEXT,
            provider_id TEXT,
            status TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def set_share_configuration(self,
                              resource_type: str,
                              platform_share: float,
                              developer_share: float,
                              provider_share: float,
                              resource_id: str = None) -> Dict[str, Any]:
        """Set or update a revenue share configuration"""
        # Validate that shares sum to 100%
        total = platform_share + developer_share + provider_share
        if abs(total - 100.0) > 0.01:
            return {
                "success": False,
                "error": f"Share percentages must sum to 100% (got {total}%)"
            }
            
        config_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Check if configuration already exists for this resource
            if resource_id:
                cursor.execute(
                    "SELECT config_id FROM share_configurations WHERE resource_id = ?",
                    (resource_id,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing configuration
                    config_id = existing[0]
                    cursor.execute(
                        "UPDATE share_configurations SET platform_share = ?, developer_share = ?, "
                        "provider_share = ?, updated_at = ? WHERE config_id = ?",
                        (platform_share, developer_share, provider_share, now, config_id)
                    )
                else:
                    # Create new configuration
                    cursor.execute(
                        "INSERT INTO share_configurations (config_id, resource_type, resource_id, "
                        "platform_share, developer_share, provider_share, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (config_id, resource_type, resource_id, platform_share, developer_share, 
                         provider_share, now, now)
                    )
            else:
                # Create type-wide configuration (no specific resource)
                cursor.execute(
                    "SELECT config_id FROM share_configurations WHERE resource_type = ? AND resource_id IS NULL",
                    (resource_type,)
                )
                existing = cursor.fetchone()
                
                if existing:
                    # Update existing configuration
                    config_id = existing[0]
                    cursor.execute(
                        "UPDATE share_configurations SET platform_share = ?, developer_share = ?, "
                        "provider_share = ?, updated_at = ? WHERE config_id = ?",
                        (platform_share, developer_share, provider_share, now, config_id)
                    )
                else:
                    # Create new configuration
                    cursor.execute(
                        "INSERT INTO share_configurations (config_id, resource_type, resource_id, "
                        "platform_share, developer_share, provider_share, created_at, updated_at) "
                        "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                        (config_id, resource_type, None, platform_share, developer_share, 
                         provider_share, now, now)
                    )
            
            conn.commit()
            
            logger.info(f"Set revenue share configuration for {resource_type}" +
                      (f" resource {resource_id}" if resource_id else ""))
                      
            return {
                "success": True,
                "config_id": config_id,
                "resource_type": resource_type,
                "resource_id": resource_id,
                "platform_share": platform_share,
                "developer_share": developer_share,
                "provider_share": provider_share
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set share configuration: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_share_configuration(self, resource_type: str, resource_id: str = None) -> Dict[str, Any]:
        """Get revenue share configuration for a resource"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Try to get resource-specific configuration
            if resource_id:
                cursor.execute(
                    "SELECT platform_share, developer_share, provider_share FROM share_configurations "
                    "WHERE resource_id = ?",
                    (resource_id,)
                )
                row = cursor.fetchone()
                
                if row:
                    return {
                        "platform_share": row[0],
                        "developer_share": row[1],
                        "provider_share": row[2],
                        "resource_specific": True
                    }
            
            # Try to get resource-type configuration
            cursor.execute(
                "SELECT platform_share, developer_share, provider_share FROM share_configurations "
                "WHERE resource_type = ? AND resource_id IS NULL",
                (resource_type,)
            )
            row = cursor.fetchone()
            
            if row:
                return {
                    "platform_share": row[0],
                    "developer_share": row[1],
                    "provider_share": row[2],
                    "resource_specific": False
                }
                
            # Return default configuration if none found
            return {
                "platform_share": self.default_shares["platform"],
                "developer_share": self.default_shares["developer"],
                "provider_share": self.default_shares["provider"],
                "resource_specific": False
            }
        finally:
            conn.close()
            
    def distribute_revenue(self,
                          transaction_id: str,
                          resource_id: str,
                          resource_type: str,
                          amount: float,
                          platform_id: str,
                          developer_id: str,
                          provider_id: str = None) -> Dict[str, Any]:
        """Split revenue from a transaction according to share configuration"""
        if amount <= 0:
            return {
                "success": False,
                "error": "Amount must be positive"
            }
            
        # Get share configuration
        shares = self.get_share_configuration(resource_type, resource_id)
        
        # Calculate share amounts
        platform_amount = amount * (shares["platform_share"] / 100.0)
        developer_amount = amount * (shares["developer_share"] / 100.0)
        provider_amount = amount * (shares["provider_share"] / 100.0)
        
        distribution_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Record distribution
            cursor.execute(
                "INSERT INTO revenue_distributions (distribution_id, transaction_id, resource_id, "
                "total_amount, platform_amount, developer_amount, provider_amount, "
                "platform_id, developer_id, provider_id, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    distribution_id,
                    transaction_id,
                    resource_id,
                    amount,
                    platform_amount,
                    developer_amount,
                    provider_amount,
                    platform_id,
                    developer_id,
                    provider_id,
                    "pending",
                    now
                )
            )
            
            conn.commit()
            
            logger.info(f"Created revenue distribution {distribution_id} for transaction {transaction_id}")
            
            return {
                "success": True,
                "distribution_id": distribution_id,
                "transaction_id": transaction_id,
                "platform_amount": platform_amount,
                "developer_amount": developer_amount,
                "provider_amount": provider_amount,
                "status": "pending"
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to create revenue distribution: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def process_distribution(self, distribution_id: str, wallet_manager: Any) -> Dict[str, Any]:
        """Process a pending revenue distribution by transferring funds to wallets"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Get distribution details
            cursor.execute(
                "SELECT platform_amount, developer_amount, provider_amount, "
                "platform_id, developer_id, provider_id, status "
                "FROM revenue_distributions WHERE distribution_id = ?",
                (distribution_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return {
                    "success": False,
                    "error": f"Distribution {distribution_id} not found"
                }
                
            platform_amount, developer_amount, provider_amount, platform_id, developer_id, provider_id, status = row
            
            if status != "pending":
                return {
                    "success": False,
                    "error": f"Distribution {distribution_id} is not pending (status: {status})"
                }
                
            # Transfer funds to platform wallet
            if platform_id and platform_amount > 0:
                platform_wallet = wallet_manager.get_wallet_by_user(platform_id)
                if platform_wallet:
                    wallet_manager.deposit(
                        platform_wallet["wallet_id"],
                        platform_amount,
                        reference_id=distribution_id,
                        description="Platform revenue share"
                    )
            
            # Transfer funds to developer wallet
            if developer_id and developer_amount > 0:
                developer_wallet = wallet_manager.get_wallet_by_user(developer_id)
                if developer_wallet:
                    wallet_manager.deposit(
                        developer_wallet["wallet_id"],
                        developer_amount,
                        reference_id=distribution_id,
                        description="Developer revenue share"
                    )
            
            # Transfer funds to provider wallet
            if provider_id and provider_amount > 0:
                provider_wallet = wallet_manager.get_wallet_by_user(provider_id)
                if provider_wallet:
                    wallet_manager.deposit(
                        provider_wallet["wallet_id"],
                        provider_amount,
                        reference_id=distribution_id,
                        description="Provider revenue share"
                    )
            
            # Mark distribution as completed
            cursor.execute(
                "UPDATE revenue_distributions SET status = ? WHERE distribution_id = ?",
                ("completed", distribution_id)
            )
            
            conn.commit()
            
            logger.info(f"Processed revenue distribution {distribution_id}")
            
            return {
                "success": True,
                "distribution_id": distribution_id,
                "status": "completed"
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to process revenue distribution {distribution_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_distribution(self, distribution_id: str) -> Optional[Dict[str, Any]]:
        """Get details of a revenue distribution"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT distribution_id, transaction_id, resource_id, total_amount, "
                "platform_amount, developer_amount, provider_amount, "
                "platform_id, developer_id, provider_id, status, created_at "
                "FROM revenue_distributions WHERE distribution_id = ?",
                (distribution_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                "distribution_id": row[0],
                "transaction_id": row[1],
                "resource_id": row[2],
                "total_amount": row[3],
                "platform_amount": row[4],
                "developer_amount": row[5],
                "provider_amount": row[6],
                "platform_id": row[7],
                "developer_id": row[8],
                "provider_id": row[9],
                "status": row[10],
                "created_at": row[11]
            }
        finally:
            conn.close()
            
    def get_user_earnings(self, user_id: str, limit: int = 20, offset: int = 0) -> Dict[str, Any]:
        """Get earnings summary for a user"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Get platform earnings
            cursor.execute(
                "SELECT SUM(platform_amount) FROM revenue_distributions "
                "WHERE platform_id = ? AND status = 'completed'",
                (user_id,)
            )
            platform_earnings = cursor.fetchone()[0] or 0
            
            # Get developer earnings
            cursor.execute(
                "SELECT SUM(developer_amount) FROM revenue_distributions "
                "WHERE developer_id = ? AND status = 'completed'",
                (user_id,)
            )
            developer_earnings = cursor.fetchone()[0] or 0
            
            # Get provider earnings
            cursor.execute(
                "SELECT SUM(provider_amount) FROM revenue_distributions "
                "WHERE provider_id = ? AND status = 'completed'",
                (user_id,)
            )
            provider_earnings = cursor.fetchone()[0] or 0
            
            # Get recent distributions
            cursor.execute(
                "SELECT distribution_id, transaction_id, resource_id, "
                "CASE WHEN platform_id = ? THEN platform_amount ELSE 0 END + "
                "CASE WHEN developer_id = ? THEN developer_amount ELSE 0 END + "
                "CASE WHEN provider_id = ? THEN provider_amount ELSE 0 END as amount, "
                "status, created_at "
                "FROM revenue_distributions "
                "WHERE platform_id = ? OR developer_id = ? OR provider_id = ? "
                "ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (user_id, user_id, user_id, user_id, user_id, user_id, limit, offset)
            )
            
            distributions = []
            for row in cursor.fetchall():
                distributions.append({
                    "distribution_id": row[0],
                    "transaction_id": row[1],
                    "resource_id": row[2],
                    "amount": row[3],
                    "status": row[4],
                    "created_at": row[5]
                })
                
            return {
                "user_id": user_id,
                "total_earnings": platform_earnings + developer_earnings + provider_earnings,
                "platform_earnings": platform_earnings,
                "developer_earnings": developer_earnings,
                "provider_earnings": provider_earnings,
                "recent_distributions": distributions
            }
        finally:
            conn.close()
