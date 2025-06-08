#!/usr/bin/env python3
"""
MCP-ZERO Wallet Module
Manages user balances and transactions for the marketplace
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
logger = logging.getLogger('wallet')

class Wallet:
    """Digital wallet for MCP-ZERO marketplace"""
    
    def __init__(self, database_path: str = "marketplace/data/wallet.db"):
        """Initialize the wallet system"""
        self.database_path = database_path
        self._ensure_database()
        logger.info(f"Wallet system initialized with database at {database_path}")
        
    def _ensure_database(self) -> None:
        """Ensure the database exists and has the required tables"""
        os.makedirs(os.path.dirname(self.database_path), exist_ok=True)
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        # Create wallets table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS wallets (
            wallet_id TEXT PRIMARY KEY,
            user_id TEXT NOT NULL,
            balance REAL DEFAULT 0.0,
            created_at TEXT NOT NULL,
            updated_at TEXT NOT NULL
        )
        ''')
        
        # Create transactions table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            transaction_id TEXT PRIMARY KEY,
            wallet_id TEXT NOT NULL,
            amount REAL NOT NULL,
            type TEXT NOT NULL,
            status TEXT NOT NULL,
            description TEXT,
            reference_id TEXT,
            created_at TEXT NOT NULL,
            FOREIGN KEY (wallet_id) REFERENCES wallets (wallet_id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_wallet(self, user_id: str) -> Dict[str, Any]:
        """Create a new wallet for a user"""
        wallet_id = str(uuid.uuid4())
        now = datetime.now().isoformat()
        
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "INSERT INTO wallets (wallet_id, user_id, balance, created_at, updated_at) VALUES (?, ?, ?, ?, ?)",
                (wallet_id, user_id, 0.0, now, now)
            )
            conn.commit()
            
            logger.info(f"Created wallet {wallet_id} for user {user_id}")
            
            return {
                "wallet_id": wallet_id,
                "user_id": user_id,
                "balance": 0.0,
                "created_at": now
            }
        except Exception as e:
            logger.error(f"Failed to create wallet for user {user_id}: {e}")
            return {
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_wallet(self, wallet_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet information by wallet ID"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT wallet_id, user_id, balance, created_at, updated_at FROM wallets WHERE wallet_id = ?",
                (wallet_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                "wallet_id": row[0],
                "user_id": row[1],
                "balance": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
        finally:
            conn.close()
            
    def get_wallet_by_user(self, user_id: str) -> Optional[Dict[str, Any]]:
        """Get wallet information by user ID"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT wallet_id, user_id, balance, created_at, updated_at FROM wallets WHERE user_id = ?",
                (user_id,)
            )
            
            row = cursor.fetchone()
            if not row:
                return None
                
            return {
                "wallet_id": row[0],
                "user_id": row[1],
                "balance": row[2],
                "created_at": row[3],
                "updated_at": row[4]
            }
        finally:
            conn.close()
            
    def deposit(self, wallet_id: str, amount: float, reference_id: str = None, description: str = None) -> Dict[str, Any]:
        """Add funds to a wallet"""
        if amount <= 0:
            return {
                "success": False,
                "error": "Deposit amount must be positive"
            }
            
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Check if wallet exists
            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = ?", (wallet_id,))
            wallet_row = cursor.fetchone()
            
            if not wallet_row:
                conn.rollback()
                return {
                    "success": False,
                    "error": f"Wallet {wallet_id} not found"
                }
                
            current_balance = wallet_row[0]
            new_balance = current_balance + amount
            
            # Update wallet balance
            cursor.execute(
                "UPDATE wallets SET balance = ?, updated_at = ? WHERE wallet_id = ?",
                (new_balance, datetime.now().isoformat(), wallet_id)
            )
            
            # Record transaction
            transaction_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO transactions (transaction_id, wallet_id, amount, type, status, description, reference_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    transaction_id,
                    wallet_id,
                    amount,
                    "deposit",
                    "completed",
                    description or "Deposit",
                    reference_id,
                    datetime.now().isoformat()
                )
            )
            
            # Commit transaction
            conn.commit()
            
            logger.info(f"Deposited {amount} to wallet {wallet_id}, new balance: {new_balance}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "wallet_id": wallet_id,
                "amount": amount,
                "new_balance": new_balance
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to deposit to wallet {wallet_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def withdraw(self, wallet_id: str, amount: float, reference_id: str = None, description: str = None) -> Dict[str, Any]:
        """Withdraw funds from a wallet"""
        if amount <= 0:
            return {
                "success": False,
                "error": "Withdrawal amount must be positive"
            }
            
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            # Begin transaction
            conn.execute("BEGIN TRANSACTION")
            
            # Check if wallet exists and has sufficient funds
            cursor.execute("SELECT balance FROM wallets WHERE wallet_id = ?", (wallet_id,))
            wallet_row = cursor.fetchone()
            
            if not wallet_row:
                conn.rollback()
                return {
                    "success": False,
                    "error": f"Wallet {wallet_id} not found"
                }
                
            current_balance = wallet_row[0]
            
            if current_balance < amount:
                conn.rollback()
                return {
                    "success": False,
                    "error": "Insufficient funds"
                }
                
            new_balance = current_balance - amount
            
            # Update wallet balance
            cursor.execute(
                "UPDATE wallets SET balance = ?, updated_at = ? WHERE wallet_id = ?",
                (new_balance, datetime.now().isoformat(), wallet_id)
            )
            
            # Record transaction
            transaction_id = str(uuid.uuid4())
            cursor.execute(
                "INSERT INTO transactions (transaction_id, wallet_id, amount, type, status, description, reference_id, created_at) "
                "VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    transaction_id,
                    wallet_id,
                    -amount,  # Store as negative amount for withdrawals
                    "withdraw",
                    "completed",
                    description or "Withdrawal",
                    reference_id,
                    datetime.now().isoformat()
                )
            )
            
            # Commit transaction
            conn.commit()
            
            logger.info(f"Withdrew {amount} from wallet {wallet_id}, new balance: {new_balance}")
            
            return {
                "success": True,
                "transaction_id": transaction_id,
                "wallet_id": wallet_id,
                "amount": amount,
                "new_balance": new_balance
            }
        except Exception as e:
            conn.rollback()
            logger.error(f"Failed to withdraw from wallet {wallet_id}: {e}")
            return {
                "success": False,
                "error": str(e)
            }
        finally:
            conn.close()
            
    def get_transactions(self, wallet_id: str, limit: int = 20, offset: int = 0) -> List[Dict[str, Any]]:
        """Get transaction history for a wallet"""
        conn = sqlite3.connect(self.database_path)
        cursor = conn.cursor()
        
        try:
            cursor.execute(
                "SELECT transaction_id, amount, type, status, description, reference_id, created_at "
                "FROM transactions WHERE wallet_id = ? ORDER BY created_at DESC LIMIT ? OFFSET ?",
                (wallet_id, limit, offset)
            )
            
            transactions = []
            for row in cursor.fetchall():
                transactions.append({
                    "transaction_id": row[0],
                    "amount": row[1],
                    "type": row[2],
                    "status": row[3],
                    "description": row[4],
                    "reference_id": row[5],
                    "created_at": row[6]
                })
                
            return transactions
        finally:
            conn.close()
