#!/usr/bin/env python3
"""
MCP-ZERO Marketplace
Core implementation for the agent and plugin marketplace
"""
import json
import logging
import os
import sqlite3
import time
import uuid
from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Dict, List, Optional, Any, Union

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('marketplace')

class ListingType(Enum):
    """Types of listings in the marketplace"""
    AGENT = "agent"
    PLUGIN = "plugin"
    MODEL = "model"
    RESOURCE = "resource"

class PricingModel(Enum):
    """Available pricing models for marketplace listings"""
    FREE = "free"
    ONE_TIME = "one_time"
    SUBSCRIPTION = "subscription"
    USAGE_BASED = "usage_based"
    TIERED = "tiered"

@dataclass
class MarketplaceListing:
    """Represents a listing in the marketplace"""
    id: str
    name: str
    description: str
    listing_type: ListingType
    version: str
    author: str
    created_at: datetime
    updated_at: datetime
    pricing_model: PricingModel
    price_usd: float
    tags: List[str]
    download_count: int = 0
    rating: float = 0.0
    review_count: int = 0

class Marketplace:
    """MCP-ZERO Marketplace implementation"""
    
    def __init__(self, db_path: str = "marketplace.db"):
        """Initialize the marketplace"""
        self.db_path = db_path
        self._initialize_database()
        logger.info(f"Marketplace initialized with database at {db_path}")
        
    def _initialize_database(self) -> None:
        """Setup the SQLite database for the marketplace"""
        # Ensure directory exists
        os.makedirs(os.path.dirname(os.path.abspath(self.db_path)), exist_ok=True)
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create tables
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS listings (
            id TEXT PRIMARY KEY,
            name TEXT NOT NULL,
            description TEXT NOT NULL,
            listing_type TEXT NOT NULL,
            version TEXT NOT NULL,
            author TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            updated_at TIMESTAMP NOT NULL,
            pricing_model TEXT NOT NULL,
            price_usd REAL NOT NULL,
            tags TEXT NOT NULL,
            download_count INTEGER DEFAULT 0,
            rating REAL DEFAULT 0.0,
            review_count INTEGER DEFAULT 0
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS reviews (
            id TEXT PRIMARY KEY,
            listing_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            rating INTEGER NOT NULL,
            comment TEXT,
            created_at TIMESTAMP NOT NULL,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
        ''')
        
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS transactions (
            id TEXT PRIMARY KEY,
            listing_id TEXT NOT NULL,
            user_id TEXT NOT NULL,
            amount REAL NOT NULL,
            currency TEXT NOT NULL,
            status TEXT NOT NULL,
            transaction_type TEXT NOT NULL,
            created_at TIMESTAMP NOT NULL,
            completed_at TIMESTAMP,
            FOREIGN KEY (listing_id) REFERENCES listings(id)
        )
        ''')
        
        conn.commit()
        conn.close()
        
    def create_listing(self, 
                      name: str,
                      description: str,
                      listing_type: Union[ListingType, str],
                      version: str,
                      author: str,
                      pricing_model: Union[PricingModel, str],
                      price_usd: float,
                      tags: List[str]) -> str:
        """Create a new marketplace listing"""
        # Convert string types to enum if needed
        if isinstance(listing_type, str):
            listing_type = ListingType(listing_type)
            
        if isinstance(pricing_model, str):
            pricing_model = PricingModel(pricing_model)
        
        # Generate a unique ID for the listing
        listing_id = str(uuid.uuid4())
        now = datetime.now()
        
        # Prepare the listing for database
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute('''
        INSERT INTO listings (
            id, name, description, listing_type, version,
            author, created_at, updated_at, pricing_model,
            price_usd, tags
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            listing_id, name, description, listing_type.value, version,
            author, now, now, pricing_model.value,
            price_usd, json.dumps(tags)
        ))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Created new {listing_type.value} listing: {name} ({listing_id})")
        return listing_id
        
    def get_listing(self, listing_id: str) -> Optional[Dict[str, Any]]:
        """Get a listing by ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        cursor.execute("SELECT * FROM listings WHERE id = ?", (listing_id,))
        row = cursor.fetchone()
        
        conn.close()
        
        if not row:
            return None
            
        # Convert row to dictionary with column names
        columns = [col[0] for col in cursor.description]
        listing = {columns[i]: row[i] for i in range(len(columns))}
        
        # Parse JSON fields
        listing['tags'] = json.loads(listing['tags'])
        
        return listing
        
    def search_listings(self, 
                       query: Optional[str] = None,
                       listing_type: Optional[Union[ListingType, str]] = None,
                       tags: Optional[List[str]] = None,
                       min_rating: float = 0.0,
                       max_price: Optional[float] = None,
                       pricing_model: Optional[Union[PricingModel, str]] = None,
                       limit: int = 20,
                       offset: int = 0) -> List[Dict[str, Any]]:
        """Search for listings with filters"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Build the query
        sql = "SELECT * FROM listings WHERE 1=1"
        params = []
        
        if query:
            sql += " AND (name LIKE ? OR description LIKE ?)"
            params.extend([f"%{query}%", f"%{query}%"])
            
        if listing_type:
            if isinstance(listing_type, ListingType):
                listing_type = listing_type.value
            sql += " AND listing_type = ?"
            params.append(listing_type)
            
        if min_rating > 0:
            sql += " AND rating >= ?"
            params.append(min_rating)
            
        if max_price is not None:
            sql += " AND price_usd <= ?"
            params.append(max_price)
            
        if pricing_model:
            if isinstance(pricing_model, PricingModel):
                pricing_model = pricing_model.value
            sql += " AND pricing_model = ?"
            params.append(pricing_model)
            
        # Add pagination
        sql += " ORDER BY rating DESC, download_count DESC LIMIT ? OFFSET ?"
        params.extend([limit, offset])
        
        cursor.execute(sql, params)
        rows = cursor.fetchall()
        
        # Convert rows to dictionaries
        columns = [col[0] for col in cursor.description]
        results = []
        
        for row in rows:
            item = {columns[i]: row[i] for i in range(len(columns))}
            
            # Parse JSON fields
            item['tags'] = json.loads(item['tags'])
            
            # Filter by tags if specified
            if tags and not all(tag in item['tags'] for tag in tags):
                continue
                
            results.append(item)
            
        conn.close()
        return results
        
    def add_review(self, 
                  listing_id: str,
                  user_id: str,
                  rating: int,
                  comment: Optional[str] = None) -> str:
        """Add a review for a listing"""
        if rating < 1 or rating > 5:
            raise ValueError("Rating must be between 1 and 5")
            
        # Check if the listing exists
        listing = self.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing with ID {listing_id} not found")
            
        review_id = str(uuid.uuid4())
        now = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert the review
        cursor.execute('''
        INSERT INTO reviews (id, listing_id, user_id, rating, comment, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
        ''', (review_id, listing_id, user_id, rating, comment, now))
        
        # Update the listing's rating and review count
        cursor.execute('''
        SELECT AVG(rating), COUNT(*) FROM reviews WHERE listing_id = ?
        ''', (listing_id,))
        avg_rating, review_count = cursor.fetchone()
        
        cursor.execute('''
        UPDATE listings SET rating = ?, review_count = ?, updated_at = ?
        WHERE id = ?
        ''', (avg_rating, review_count, now, listing_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Added review for listing {listing_id}: rating {rating}")
        return review_id
        
    def record_transaction(self,
                          listing_id: str,
                          user_id: str,
                          amount: float,
                          currency: str = "USD",
                          transaction_type: str = "purchase") -> str:
        """Record a marketplace transaction"""
        # Check if the listing exists
        listing = self.get_listing(listing_id)
        if not listing:
            raise ValueError(f"Listing with ID {listing_id} not found")
            
        transaction_id = str(uuid.uuid4())
        now = datetime.now()
        
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Insert the transaction
        cursor.execute('''
        INSERT INTO transactions (
            id, listing_id, user_id, amount, currency,
            status, transaction_type, created_at
        ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        ''', (
            transaction_id, listing_id, user_id, amount, currency,
            "pending", transaction_type, now
        ))
        
        # Update download count for the listing
        if transaction_type == "purchase" or transaction_type == "download":
            cursor.execute('''
            UPDATE listings SET download_count = download_count + 1, updated_at = ?
            WHERE id = ?
            ''', (now, listing_id))
        
        conn.commit()
        conn.close()
        
        logger.info(f"Recorded {transaction_type} transaction for listing {listing_id}: {amount} {currency}")
        return transaction_id
        
    def complete_transaction(self, transaction_id: str) -> bool:
        """Mark a transaction as completed"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        now = datetime.now()
        
        cursor.execute('''
        UPDATE transactions SET status = ?, completed_at = ?
        WHERE id = ?
        ''', ("completed", now, transaction_id))
        
        success = cursor.rowcount > 0
        conn.commit()
        conn.close()
        
        if success:
            logger.info(f"Transaction {transaction_id} marked as completed")
        else:
            logger.warning(f"Failed to complete transaction {transaction_id}: not found")
            
        return success
