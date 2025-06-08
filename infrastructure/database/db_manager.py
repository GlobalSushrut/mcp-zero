#!/usr/bin/env python3
"""
MCP-ZERO Database Manager
Provides database abstraction layer to support multiple database backends
"""
import logging
import os
from typing import Dict, Any, List, Optional, Union
import json
from pathlib import Path
from datetime import datetime
import inspect

# For SQLite/SQLAlchemy
import sqlalchemy
from sqlalchemy import create_engine, Column, Integer, String, Float, Boolean, DateTime, Text, ForeignKey, MetaData
from sqlalchemy.ext.declarative import declarative_base
from sqlalchemy.orm import sessionmaker, relationship, scoped_session
from sqlalchemy.sql import text

# For MongoDB support (optional)
try:
    import pymongo
    from pymongo import MongoClient
    MONGODB_AVAILABLE = True
except ImportError:
    MONGODB_AVAILABLE = False

# For Redis support
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('db_manager')

# Import settings if available
try:
    from config.settings import settings
    SETTINGS_AVAILABLE = True
except ImportError:
    SETTINGS_AVAILABLE = False
    logger.warning("Settings module not found, using default configuration")

# Base for SQLAlchemy models
Base = declarative_base()

class DatabaseManager:
    """
    Database abstraction layer to support multiple database backends
    
    Supports:
    - SQLite (default)
    - PostgreSQL
    - MongoDB (optional)
    - Redis (optional, for caching)
    """
    
    def __init__(
        self, 
        db_type: str = None, 
        connection_string: str = None,
        db_path: str = None,
        db_name: str = None,
        db_user: str = None,
        db_password: str = None,
        db_host: str = None,
        db_port: int = None,
        use_cache: bool = True
    ):
        """
        Initialize the database manager
        
        Args:
            db_type: Type of database (sqlite, postgres, mongodb)
            connection_string: Direct connection string (overrides other parameters)
            db_path: Path to database file (for SQLite)
            db_name: Database name
            db_user: Database username
            db_password: Database password
            db_host: Database host
            db_port: Database port
            use_cache: Whether to use Redis caching if available
        """
        # Use settings if available and parameters not provided
        if SETTINGS_AVAILABLE:
            db_type = db_type or settings.get('database.type')
            db_path = db_path or settings.get('database.path')
            db_name = db_name or settings.get('database.name')
            db_user = db_user or settings.get('database.user')
            db_password = db_password or settings.get('database.password')
            db_host = db_host or settings.get('database.host')
            db_port = db_port or settings.get('database.port')
            use_cache = use_cache if use_cache is not None else settings.get('database.use_cache', True)
            
        # Use environment variables if parameters still not provided
        db_type = db_type or os.environ.get('MCP_DB_TYPE', 'sqlite')
        db_path = db_path or os.environ.get('MCP_DB_PATH', 'data/mcp_zero.db')
        db_name = db_name or os.environ.get('MCP_DB_NAME', 'mcp_zero')
        db_user = db_user or os.environ.get('MCP_DB_USER', '')
        db_password = db_password or os.environ.get('MCP_DB_PASSWORD', '')
        db_host = db_host or os.environ.get('MCP_DB_HOST', 'localhost')
        db_port = db_port or int(os.environ.get('MCP_DB_PORT', '5432'))
        
        # Store configuration
        self.db_type = db_type.lower()
        self.db_path = db_path
        self.db_name = db_name
        self.db_user = db_user
        self.db_password = db_password
        self.db_host = db_host
        self.db_port = db_port
        self.use_cache = use_cache
        self.connection_string = connection_string
        
        # Initialize connections
        self.engine = None
        self.session_factory = None
        self.mongo_client = None
        self.mongo_db = None
        self.redis_client = None
        
        # Connect to the database
        self._connect()
        
    def _connect(self):
        """Connect to the database based on the specified type"""
        if self.connection_string:
            # Use direct connection string if provided
            logger.info(f"Connecting to database using connection string")
            self._connect_with_string(self.connection_string)
        elif self.db_type == 'sqlite':
            # Connect to SQLite database
            self._connect_sqlite()
        elif self.db_type in ['postgres', 'postgresql']:
            # Connect to PostgreSQL database
            self._connect_postgres()
        elif self.db_type == 'mongodb' and MONGODB_AVAILABLE:
            # Connect to MongoDB database
            self._connect_mongodb()
        else:
            # Default to SQLite
            logger.warning(f"Unknown database type '{self.db_type}', defaulting to SQLite")
            self._connect_sqlite()
            
        # Initialize Redis cache if enabled
        if self.use_cache and REDIS_AVAILABLE:
            self._connect_redis()
            
    def _connect_with_string(self, connection_string):
        """Connect using a direct connection string"""
        try:
            self.engine = create_engine(connection_string)
            self.session_factory = scoped_session(sessionmaker(bind=self.engine))
            logger.info("Connected to database using connection string")
        except Exception as e:
            logger.error(f"Error connecting to database with connection string: {str(e)}")
            raise
            
    def _connect_sqlite(self):
        """Connect to SQLite database"""
        try:
            # Ensure directory exists
            db_path = Path(self.db_path)
            db_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Create connection string
            conn_str = f"sqlite:///{db_path}"
            
            # Create engine and session factory
            self.engine = create_engine(conn_str)
            self.session_factory = scoped_session(sessionmaker(bind=self.engine))
            
            logger.info(f"Connected to SQLite database at {db_path}")
        except Exception as e:
            logger.error(f"Error connecting to SQLite database: {str(e)}")
            raise
            
    def _connect_postgres(self):
        """Connect to PostgreSQL database"""
        try:
            # Create connection string
            conn_str = f"postgresql://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/{self.db_name}"
            
            # Create engine and session factory
            self.engine = create_engine(conn_str)
            self.session_factory = scoped_session(sessionmaker(bind=self.engine))
            
            logger.info(f"Connected to PostgreSQL database at {self.db_host}:{self.db_port}/{self.db_name}")
        except Exception as e:
            logger.error(f"Error connecting to PostgreSQL database: {str(e)}")
            raise
            
    def _connect_mongodb(self):
        """Connect to MongoDB database"""
        try:
            if self.db_user and self.db_password:
                uri = f"mongodb://{self.db_user}:{self.db_password}@{self.db_host}:{self.db_port}/?authSource=admin"
            else:
                uri = f"mongodb://{self.db_host}:{self.db_port}/"
                
            self.mongo_client = MongoClient(uri)
            self.mongo_db = self.mongo_client[self.db_name]
            
            logger.info(f"Connected to MongoDB database at {self.db_host}:{self.db_port}/{self.db_name}")
        except Exception as e:
            logger.error(f"Error connecting to MongoDB database: {str(e)}")
            raise
            
    def _connect_redis(self):
        """Connect to Redis for caching"""
        try:
            self.redis_client = redis.Redis(
                host=os.environ.get('REDIS_HOST', 'localhost'),
                port=int(os.environ.get('REDIS_PORT', '6379')),
                db=int(os.environ.get('REDIS_DB', '0')),
                password=os.environ.get('REDIS_PASSWORD', None)
            )
            
            # Test connection
            self.redis_client.ping()
            logger.info(f"Connected to Redis cache")
        except Exception as e:
            logger.warning(f"Error connecting to Redis cache, caching will be disabled: {str(e)}")
            self.redis_client = None
            
    def create_tables(self):
        """Create all tables defined in the models"""
        if self.engine:
            Base.metadata.create_all(self.engine)
            logger.info("Created all database tables")
            
    def drop_tables(self):
        """Drop all tables defined in the models"""
        if self.engine:
            Base.metadata.drop_all(self.engine)
            logger.info("Dropped all database tables")
            
    def get_session(self):
        """Get a database session"""
        if not self.session_factory:
            raise ValueError("Database connection not initialized")
        return self.session_factory()
        
    def close(self):
        """Close all database connections"""
        if self.session_factory:
            self.session_factory.remove()
            
        if self.engine:
            self.engine.dispose()
            
        if self.mongo_client:
            self.mongo_client.close()
            
        if self.redis_client:
            self.redis_client.close()
            
        logger.info("Closed all database connections")
        
    # SQLAlchemy-based operations (SQL databases)
    
    def execute_query(self, query, params=None):
        """Execute a raw SQL query"""
        if not self.engine:
            raise ValueError("SQL database connection not initialized")
            
        with self.engine.connect() as conn:
            if params:
                result = conn.execute(text(query), params)
            else:
                result = conn.execute(text(query))
                
            if result.returns_rows:
                return [dict(row) for row in result]
            return None
            
    # MongoDB-based operations
    
    def collection(self, name):
        """Get a MongoDB collection"""
        if not self.mongo_db:
            raise ValueError("MongoDB connection not initialized")
        return self.mongo_db[name]
        
    def insert_document(self, collection_name, document):
        """Insert a document into MongoDB"""
        if not self.mongo_db:
            raise ValueError("MongoDB connection not initialized")
            
        collection = self.mongo_db[collection_name]
        result = collection.insert_one(document)
        return str(result.inserted_id)
        
    def find_documents(self, collection_name, query=None, limit=0, skip=0, sort=None):
        """Find documents in MongoDB"""
        if not self.mongo_db:
            raise ValueError("MongoDB connection not initialized")
            
        collection = self.mongo_db[collection_name]
        cursor = collection.find(query or {})
        
        if skip:
            cursor = cursor.skip(skip)
            
        if limit:
            cursor = cursor.limit(limit)
            
        if sort:
            cursor = cursor.sort(sort)
            
        return list(cursor)
        
    # Redis cache operations
    
    def cache_set(self, key, value, expire=3600):
        """Set a value in the Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            if isinstance(value, (dict, list)):
                value = json.dumps(value)
                
            self.redis_client.set(key, value, ex=expire)
            return True
        except Exception as e:
            logger.warning(f"Error setting cache key {key}: {str(e)}")
            return False
            
    def cache_get(self, key):
        """Get a value from the Redis cache"""
        if not self.redis_client:
            return None
            
        try:
            value = self.redis_client.get(key)
            
            if value is None:
                return None
                
            # Try to decode as JSON
            try:
                return json.loads(value)
            except (TypeError, json.JSONDecodeError):
                return value.decode('utf-8') if isinstance(value, bytes) else value
        except Exception as e:
            logger.warning(f"Error getting cache key {key}: {str(e)}")
            return None
            
    def cache_delete(self, key):
        """Delete a value from the Redis cache"""
        if not self.redis_client:
            return False
            
        try:
            self.redis_client.delete(key)
            return True
        except Exception as e:
            logger.warning(f"Error deleting cache key {key}: {str(e)}")
            return False
            
# Common database models

class User(Base):
    """User model for authentication and billing"""
    __tablename__ = 'users'
    
    id = Column(String(36), primary_key=True)
    username = Column(String(64), unique=True, nullable=False)
    email = Column(String(256), unique=True, nullable=False)
    password_hash = Column(String(256), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    is_active = Column(Boolean, default=True)
    is_admin = Column(Boolean, default=False)
    metadata = Column(Text, nullable=True)
    
    def __repr__(self):
        return f"<User {self.username}>"
        
class ApiKey(Base):
    """API key model for authentication"""
    __tablename__ = 'api_keys'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    key = Column(String(64), unique=True, nullable=False)
    name = Column(String(64), nullable=False)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    expires_at = Column(DateTime, nullable=True)
    is_active = Column(Boolean, default=True)
    scopes = Column(Text, nullable=True)
    
    user = relationship("User", backref="api_keys")
    
    def __repr__(self):
        return f"<ApiKey {self.name}>"
        
class Wallet(Base):
    """Wallet model for billing"""
    __tablename__ = 'wallets'
    
    id = Column(String(36), primary_key=True)
    user_id = Column(String(36), ForeignKey('users.id'), nullable=False)
    balance = Column(Float, nullable=False, default=0.0)
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    updated_at = Column(DateTime, nullable=False, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    user = relationship("User", backref="wallet")
    
    def __repr__(self):
        return f"<Wallet {self.id} - {self.balance}>"
        
class Transaction(Base):
    """Transaction model for billing"""
    __tablename__ = 'transactions'
    
    id = Column(String(36), primary_key=True)
    wallet_id = Column(String(36), ForeignKey('wallets.id'), nullable=False)
    amount = Column(Float, nullable=False)
    description = Column(Text, nullable=True)
    transaction_type = Column(String(32), nullable=False)  # deposit, withdrawal, payment, refund
    reference_id = Column(String(36), nullable=True)  # e.g., invoice_id, agreement_id
    created_at = Column(DateTime, nullable=False, default=datetime.utcnow)
    
    wallet = relationship("Wallet", backref="transactions")
    
    def __repr__(self):
        return f"<Transaction {self.id} - {self.amount}>"
        
# Create a global instance for convenience
db_manager = None

def initialize_db():
    """Initialize the global database manager"""
    global db_manager
    
    if db_manager is not None:
        return db_manager
        
    # Create database manager
    db_manager = DatabaseManager()
    
    # Create tables
    db_manager.create_tables()
    
    return db_manager

def get_db_manager():
    """Get the global database manager"""
    if db_manager is None:
        return initialize_db()
    return db_manager
