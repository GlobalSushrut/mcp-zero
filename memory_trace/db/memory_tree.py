"""
MCP-ZERO Memory Tree Trace Module
Provides database-backed persistent memory traces for AI agents
"""

import json
import time
import uuid
import hashlib
import sqlite3
import logging
import requests
from typing import Dict, List, Any, Optional, Union, Tuple


class MemoryNode:
    """Represents a single node in the memory tree"""
    
    def __init__(self, 
                 content: str, 
                 node_type: str,
                 metadata: Optional[Dict[str, Any]] = None,
                 parent_id: Optional[str] = None):
        self.node_id = str(uuid.uuid4())
        self.content = content
        self.node_type = node_type
        self.metadata = metadata or {}
        self.parent_id = parent_id
        self.timestamp = time.time()
        self.hash = self._calculate_hash()
        
    def _calculate_hash(self) -> str:
        """Calculate a cryptographic hash of this memory node"""
        content_str = f"{self.node_id}:{self.content}:{self.node_type}:{json.dumps(self.metadata)}:{self.parent_id}:{self.timestamp}"
        return hashlib.sha256(content_str.encode()).hexdigest()
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert node to dictionary representation"""
        return {
            "node_id": self.node_id,
            "content": self.content,
            "node_type": self.node_type,
            "metadata": self.metadata,
            "parent_id": self.parent_id,
            "timestamp": self.timestamp,
            "hash": self.hash
        }
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'MemoryNode':
        """Create a MemoryNode from dictionary representation"""
        node = cls(
            content=data["content"],
            node_type=data["node_type"],
            metadata=data["metadata"],
            parent_id=data["parent_id"]
        )
        node.node_id = data["node_id"]
        node.timestamp = data["timestamp"]
        node.hash = data["hash"]
        return node


class DBMemoryTree:
    """Database-backed implementation of agent memory tree"""
    
    def __init__(self, db_path: str = ":memory:", rpc_url: str = "http://localhost:8081", offline_mode: bool = True):
        self.db_path = db_path
        self.rpc_url = rpc_url
        self.conn = self._init_db()
        self.logger = logging.getLogger("DBMemoryTree")
        self.offline_mode = offline_mode
        
        if self.offline_mode:
            self.logger.info("Starting in offline mode - memory traces will be local only")
        
    def _init_db(self) -> sqlite3.Connection:
        """Initialize the SQLite database with required schema"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        
        # Create memory nodes table
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS memory_nodes (
            node_id TEXT PRIMARY KEY,
            content TEXT NOT NULL,
            node_type TEXT NOT NULL,
            metadata TEXT,
            parent_id TEXT,
            timestamp REAL,
            hash TEXT,
            FOREIGN KEY (parent_id) REFERENCES memory_nodes (node_id)
        )
        ''')
        
        # Create index on parent_id for faster traversal
        cursor.execute('CREATE INDEX IF NOT EXISTS idx_parent_id ON memory_nodes(parent_id)')
        
        # Create agents table to track which agent owns which memories
        cursor.execute('''
        CREATE TABLE IF NOT EXISTS agent_memories (
            agent_id TEXT,
            node_id TEXT,
            PRIMARY KEY (agent_id, node_id),
            FOREIGN KEY (node_id) REFERENCES memory_nodes (node_id)
        )
        ''')
        
        conn.commit()
        return conn
    
    def add_memory(self, 
                   agent_id: str, 
                   content: str, 
                   node_type: str,
                   metadata: Optional[Dict[str, Any]] = None, 
                   parent_id: Optional[str] = None) -> str:
        """
        Add a new memory node to the tree and associate it with an agent
        
        Returns:
            str: The ID of the newly created memory node
        """
        # Create new memory node
        node = MemoryNode(content, node_type, metadata, parent_id)
        
        # Serialize metadata to JSON
        metadata_json = json.dumps(node.metadata)
        
        # Insert into database
        cursor = self.conn.cursor()
        cursor.execute(
            "INSERT INTO memory_nodes VALUES (?, ?, ?, ?, ?, ?, ?)",
            (node.node_id, node.content, node.node_type, metadata_json, 
             node.parent_id, node.timestamp, node.hash)
        )
        
        # Associate with agent
        cursor.execute(
            "INSERT INTO agent_memories VALUES (?, ?)",
            (agent_id, node.node_id)
        )
        
        self.conn.commit()
        
        # Register with MCP-ZERO RPC server
        self._register_memory_with_rpc(agent_id, node)
        
        return node.node_id
    
    def get_memory(self, node_id: str) -> Optional[Dict[str, Any]]:
        """Retrieve a specific memory node by ID"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT node_id, content, node_type, metadata, parent_id, timestamp, hash "
            "FROM memory_nodes WHERE node_id = ?",
            (node_id,)
        )
        
        row = cursor.fetchone()
        if not row:
            return None
        
        return {
            "node_id": row[0],
            "content": row[1],
            "node_type": row[2],
            "metadata": json.loads(row[3]),
            "parent_id": row[4],
            "timestamp": row[5],
            "hash": row[6]
        }
    
    def get_agent_memories(self, agent_id: str) -> List[Dict[str, Any]]:
        """Get all memory nodes for a specific agent"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT n.node_id, n.content, n.node_type, n.metadata, n.parent_id, n.timestamp, n.hash "
            "FROM memory_nodes n "
            "JOIN agent_memories a ON n.node_id = a.node_id "
            "WHERE a.agent_id = ? "
            "ORDER BY n.timestamp",
            (agent_id,)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "node_id": row[0],
                "content": row[1],
                "node_type": row[2],
                "metadata": json.loads(row[3]),
                "parent_id": row[4],
                "timestamp": row[5],
                "hash": row[6]
            })
            
        return results
    
    def get_memory_path(self, node_id: str) -> List[Dict[str, Any]]:
        """Get the full path from root to the specified node"""
        path = []
        current_id = node_id
        
        while current_id:
            node = self.get_memory(current_id)
            if not node:
                break
                
            path.insert(0, node)  # Add to beginning of list
            current_id = node["parent_id"]
            
        return path
    
    def get_children(self, parent_id: str) -> List[Dict[str, Any]]:
        """Get all child nodes for a specific parent node"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT node_id, content, node_type, metadata, parent_id, timestamp, hash "
            "FROM memory_nodes WHERE parent_id = ? "
            "ORDER BY timestamp",
            (parent_id,)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "node_id": row[0],
                "content": row[1],
                "node_type": row[2],
                "metadata": json.loads(row[3]),
                "parent_id": row[4],
                "timestamp": row[5],
                "hash": row[6]
            })
            
        return results
    
    def search_memories(self, query: str) -> List[Dict[str, Any]]:
        """Search for memory nodes containing the query string"""
        cursor = self.conn.cursor()
        cursor.execute(
            "SELECT node_id, content, node_type, metadata, parent_id, timestamp, hash "
            "FROM memory_nodes WHERE content LIKE ? "
            "ORDER BY timestamp DESC LIMIT 100",
            (f"%{query}%",)
        )
        
        results = []
        for row in cursor.fetchall():
            results.append({
                "node_id": row[0],
                "content": row[1],
                "node_type": row[2],
                "metadata": json.loads(row[3]),
                "parent_id": row[4],
                "timestamp": row[5],
                "hash": row[6]
            })
            
        return results
    
    def _register_memory_with_rpc(self, agent_id: str, node: MemoryNode) -> bool:
        """Register memory node with the MCP-ZERO RPC server for ZK tracing"""
        
        # Skip RPC registration if offline mode is enabled
        if getattr(self, "offline_mode", False):
            return True
            
        try:
            payload = {
                "agent_id": agent_id,
                "memory_node": node.to_dict(),
                "timestamp": time.time(),
                "signature": self._sign_memory(agent_id, node)
            }
            
            response = requests.post(
                f"{self.rpc_url}/api/v1/memory/register",
                json=payload
            )
            
            if response.status_code != 200:
                self.logger.error(f"Failed to register memory with RPC server: {response.text}")
                self.offline_mode = True  # Switch to offline mode after failure
                self.logger.warning("Switched to offline mode - memory traces will be local only")
                return True  # Still return success for local operations
                
            return True
        except Exception as e:
            self.logger.error(f"Error registering memory with RPC server: {str(e)}")
            self.offline_mode = True  # Switch to offline mode
            self.logger.warning("Switched to offline mode - memory traces will be local only")
            return True  # Still return success for local operations
    
    def _sign_memory(self, agent_id: str, node: MemoryNode) -> str:
        """Create a cryptographic signature for the memory node"""
        # In a real implementation, this would use proper crypto
        # For now, we'll create a simple hash-based signature
        content = f"{agent_id}:{node.node_id}:{node.hash}"
        return hashlib.sha256(content.encode()).hexdigest()
    
    def verify_memory_trace(self, memory_path: List[Dict[str, Any]]) -> bool:
        """Verify the integrity of a memory trace path"""
        for i, node in enumerate(memory_path):
            # Skip root node parent verification
            if i > 0:
                # Verify parent reference is correct
                if node["parent_id"] != memory_path[i-1]["node_id"]:
                    return False
            
            # Recreate node to verify hash
            reconstructed = MemoryNode(
                content=node["content"],
                node_type=node["node_type"],
                metadata=node["metadata"],
                parent_id=node["parent_id"]
            )
            reconstructed.node_id = node["node_id"]
            reconstructed.timestamp = node["timestamp"]
            
            # Verify hash integrity
            if reconstructed._calculate_hash() != node["hash"]:
                return False
                
        return True
    
    def close(self):
        """Close database connection"""
        if self.conn:
            self.conn.close()
            
    def __del__(self):
        """Destructor to ensure connection is closed"""
        self.close()
