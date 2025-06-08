#!/usr/bin/env python3
"""
MCP-ZERO Usage Tracking System
Monitors and records agent resource usage for billing purposes
"""
import json
import logging
import os
import sqlite3
import time
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any
import uuid

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('usage_tracker')

class UsageTracker:
    """Tracks and records agent resource consumption"""
    
    def __init__(self, database_path: str = "marketplace/data/usage.db"):
        """Initialize the usage tracking system"""
        self.database_path = database_path
        self._ensure_database()
        logger.info(f"Usage tracker initialized with database at {database_path}")
        
    def _ensure_database(self) -> None:
        """Ensure the database exists and has the required tables"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create usage records table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_records (
            record_id TEXT PRIMARY KEY,
            agent_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            usage_type TEXT NOT NULL,
            quantity REAL NOT NULL,
            unit TEXT NOT NULL,
            timestamp TEXT NOT NULL,
            billed BOOLEAN DEFAULT FALSE
        )
        ''')
        
        # Create billing cycle table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS billing_cycles (
            cycle_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            start_date TEXT NOT NULL,
            end_date TEXT NOT NULL,
            status TEXT NOT NULL,
            invoice_id TEXT,
            created_at TEXT NOT NULL
        )
        ''')
        
        # Create usage pricing table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS usage_pricing (
            pricing_id TEXT PRIMARY KEY,
            usage_type TEXT NOT NULL,
            price_per_unit REAL NOT NULL,
            tier_start REAL,
            tier_end REAL,
            effective_date TEXT NOT NULL,
            created_at TEXT NOT NULL
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def record_usage(self, 
                    agent_id: str, 
                    user_id: str, 
                    usage_type: str, 
                    quantity: float, 
                    unit: str) -> Dict[str, Any]:
        """Record resource usage for an agent"""
        record_id = str(uuid.uuid4())
        timestamp = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO usage_records (record_id, agent_id, user_id, usage_type, quantity, unit, timestamp, billed) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (record_id, agent_id, user_id, usage_type, quantity, unit, timestamp, False)
            )
            
            conn.commit()
            
            logger.debug(f"Recorded {quantity} {unit} of {usage_type} for agent {agent_id}")
            
            return {
                "record_id": record_id,
                "agent_id": agent_id,
                "user_id": user_id,
                "usage_type": usage_type,
                "quantity": quantity,
                "unit": unit,
                "timestamp": timestamp
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to record usage: {e}")
            return {
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_usage(self, 
                 user_id: str = None, 
                 agent_id: str = None, 
                 usage_type: str = None,
                 start_time: str = None,
                 end_time: str = None,
                 include_billed: bool = True) -> List[Dict[str, Any]]:
        """Query usage records with optional filters"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        query = "SELECT record_id, agent_id, user_id, usage_type, quantity, unit, timestamp, billed FROM usage_records WHERE 1=1"
        params = []
        
        if user_id:
            query += " AND user_id = ?"
            params.append(user_id)
            
        if agent_id:
            query += " AND agent_id = ?"
            params.append(agent_id)
            
        if usage_type:
            query += " AND usage_type = ?"
            params.append(usage_type)
            
        if start_time:
            query += " AND timestamp >= ?"
            params.append(start_time)
            
        if end_time:
            query += " AND timestamp <= ?"
            params.append(end_time)
            
        if not include_billed:
            query += " AND billed = 0"
            
        query += " ORDER BY timestamp DESC"
        
        try:
            cursor.execute(query, params)
            
            records = []
            for row in cursor.fetchall():
                records.append({
                    "record_id": row[0],
                    "agent_id": row[1],
                    "user_id": row[2],
                    "usage_type": row[3],
                    "quantity": row[4],
                    "unit": row[5],
                    "timestamp": row[6],
                    "billed": bool(row[7])
                })
                
            return records
        finally:
            conn.close()
            
    def set_price(self, 
                 usage_type: str, 
                 price_per_unit: float, 
                 tier_start: float = None,
                 tier_end: float = None) -> Dict[str, Any]:
        """Set pricing for a usage type"""
        if price_per_unit < 0:
            return {
                "success": False,
                "error": "Price per unit cannot be negative"
            }
            
        pricing_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO usage_pricing (pricing_id, usage_type, price_per_unit, tier_start, tier_end, effective_date, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?)",
                (pricing_id, usage_type, price_per_unit, tier_start, tier_end, now, now)
            )
            
            conn.commit()
            
            logger.info(f"Set price for {usage_type} at {price_per_unit} per unit")
            
            return {
                "success": True,
                "pricing_id": pricing_id,
                "usage_type": usage_type,
                "price_per_unit": price_per_unit,
                "tier_start": tier_start,
                "tier_end": tier_end,
                "effective_date": now
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to set pricing: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_pricing(self, usage_type: str) -> List[Dict[str, Any]]:
        """Get current pricing for a usage type"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT pricing_id, usage_type, price_per_unit, tier_start, tier_end, effective_date "
                "FROM usage_pricing WHERE usage_type = ? ORDER BY effective_date DESC, tier_start ASC",
                (usage_type,)
            )
            
            pricing_tiers = []
            for row in cursor.fetchall():
                pricing_tiers.append({
                    "pricing_id": row[0],
                    "usage_type": row[1],
                    "price_per_unit": row[2],
                    "tier_start": row[3],
                    "tier_end": row[4],
                    "effective_date": row[5]
                })
                
            return pricing_tiers
        finally:
            conn.close()
            
    def start_billing_cycle(self, user_id: str) -> Dict[str, Any]:
        """Start a new billing cycle for a user"""
        now = datetime.now()
        cycle_id = str(uuid.uuid4())
        start_date = now.isoformat()
        end_date = (now + timedelta(days=30)).isoformat()  # Default 30-day cycle
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Check if there's an active cycle
            cursor.execute(
                "SELECT cycle_id FROM billing_cycles WHERE user_id = ? AND status = 'active'",
                (user_id,)
            )
            
            existing = cursor.fetchone()
            if existing:
                return {
                    "success": False,
                    "error": f"User {user_id} already has an active billing cycle"
                }
                
            # Create new billing cycle
            cursor.execute(
                "INSERT INTO billing_cycles (cycle_id, user_id, start_date, end_date, status, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?)",
                (cycle_id, user_id, start_date, end_date, "active", now.isoformat())
            )
            
            conn.commit()
            
            logger.info(f"Started billing cycle {cycle_id} for user {user_id}")
            
            return {
                "success": True,
                "cycle_id": cycle_id,
                "user_id": user_id,
                "start_date": start_date,
                "end_date": end_date,
                "status": "active"
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to start billing cycle: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def close_billing_cycle(self, cycle_id: str, invoice_id: str = None) -> Dict[str, Any]:
        """Close a billing cycle and mark as ready for invoicing"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Check if cycle exists
            cursor.execute(
                "SELECT user_id, start_date, end_date FROM billing_cycles WHERE cycle_id = ? AND status = 'active'",
                (cycle_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return {
                    "success": False,
                    "error": f"No active billing cycle found with ID {cycle_id}"
                }
                
            user_id, start_date, end_date = row
            
            # Mark cycle as closed
            cursor.execute(
                "UPDATE billing_cycles SET status = ?, invoice_id = ? WHERE cycle_id = ?",
                ("closed", invoice_id, cycle_id)
            )
            
            # Mark usage records as billed
            cursor.execute(
                "UPDATE usage_records SET billed = 1 "
                "WHERE user_id = ? AND timestamp >= ? AND timestamp <= ? AND billed = 0",
                (user_id, start_date, end_date)
            )
            
            conn.commit()
            
            logger.info(f"Closed billing cycle {cycle_id} for user {user_id}")
            
            return {
                "success": True,
                "cycle_id": cycle_id,
                "user_id": user_id,
                "invoice_id": invoice_id,
                "status": "closed"
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to close billing cycle: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def calculate_usage_cost(self, 
                           user_id: str, 
                           start_time: str = None, 
                           end_time: str = None) -> Dict[str, Any]:
        """Calculate the cost of usage for a given period"""
        if not start_time:
            # Default to last 30 days
            start_time = (datetime.now() - timedelta(days=30)).isoformat()
            
        if not end_time:
            end_time = datetime.now().isoformat()
            
        # Get usage records
        usage_records = self.get_usage(
            user_id=user_id,
            start_time=start_time,
            end_time=end_time
        )
        
        # Group by usage type
        usage_by_type = {}
        for record in usage_records:
            usage_type = record["usage_type"]
            if usage_type not in usage_by_type:
                usage_by_type[usage_type] = []
                
            usage_by_type[usage_type].append(record)
        
        total_cost = 0.0
        usage_summary = []
        
        # Calculate cost for each usage type
        for usage_type, records in usage_by_type.items():
            # Get pricing tiers for this usage type
            pricing_tiers = self.get_pricing(usage_type)
            if not pricing_tiers:
                # Skip if no pricing available
                continue
                
            # Use the most recent pricing
            pricing = pricing_tiers[0]
            
            # Sum up quantity
            total_quantity = sum(record["quantity"] for record in records)
            
            # Calculate cost
            cost = total_quantity * pricing["price_per_unit"]
            total_cost += cost
            
            usage_summary.append({
                "usage_type": usage_type,
                "total_quantity": total_quantity,
                "unit": records[0]["unit"],  # Assume consistent units
                "price_per_unit": pricing["price_per_unit"],
                "cost": cost
            })
        
        return {
            "user_id": user_id,
            "start_time": start_time,
            "end_time": end_time,
            "total_cost": total_cost,
            "usage_summary": usage_summary
        }
