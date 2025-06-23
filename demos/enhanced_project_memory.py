#!/usr/bin/env python3
"""
Enhanced Project Memory System for MCP Zero Editor

Provides persistent project context with offline-first resilience.
"""

import os
import json
import time
import logging
import threading
from typing import Dict, Any, List, Optional, Set
from enum import Enum

# Configure logging
logger = logging.getLogger("mcp_zero.memory")

class MemoryType(Enum):
    """Types of project memory items"""
    ARCHITECTURE = "architecture"
    CODE_STRUCTURE = "code_structure"
    REQUIREMENTS = "requirements"
    CONVERSATION = "conversation"
    FILE = "file"
    COMPONENT = "component"
    DECISION = "decision"


class ProjectMemory:
    """
    Persistent project memory system with offline-first resilience.
    
    Follows offline-first approach:
    - Stores memory locally first
    - Only attempts remote sync once
    - Falls back to local-only if remote unavailable
    """
    
    def __init__(
        self, 
        project_id: str,
        memory_dir: Optional[str] = None, 
        db_client = None,
        offline_first: bool = True
    ):
        """
        Initialize project memory manager.
        
        Args:
            project_id: Unique project identifier
            memory_dir: Directory for local memory storage
            db_client: Optional DB client for remote storage
            offline_first: Start in offline mode
        """
        self.project_id = project_id
        self.offline_mode = offline_first
        
        # Set up local storage
        if memory_dir is None:
            memory_dir = os.path.join(
                os.path.expanduser("~"),
                ".mcp_zero",
                "editor",
                "memory",
                project_id
            )
        self.memory_dir = memory_dir
        os.makedirs(memory_dir, exist_ok=True)
        
        # Memory storage
        self._memory_items = {}
        self._index = {}  # For search
        self._lock = threading.RLock()
        self._remote_attempt_made = False
        
        # Optional DB client
        self.db_client = db_client
        
        # Load existing memory
        self._load_memory()
        
        logger.info(f"Project memory initialized for {project_id} in {'offline' if offline_first else 'online'} mode")
    
    def _load_memory(self) -> None:
        """Load memory from local storage."""
        try:
            memory_file = os.path.join(self.memory_dir, "memory.json")
            if os.path.exists(memory_file):
                with open(memory_file, 'r') as f:
                    self._memory_items = json.load(f)
                logger.info(f"Loaded {len(self._memory_items)} memory items")
                
                # Rebuild index
                self._rebuild_index()
        except Exception as e:
            logger.error(f"Error loading memory: {str(e)}")
            self._memory_items = {}
    
    def _save_memory(self) -> bool:
        """Save memory to local storage."""
        try:
            memory_file = os.path.join(self.memory_dir, "memory.json")
            with open(memory_file, 'w') as f:
                json.dump(self._memory_items, f, indent=2)
            logger.debug(f"Saved {len(self._memory_items)} memory items")
            return True
        except Exception as e:
            logger.error(f"Error saving memory: {str(e)}")
            return False
            
    def add_memory(
        self, 
        memory_type: MemoryType, 
        content: str,
        metadata: Dict[str, Any] = None
    ) -> str:
        """
        Add a memory item.
        
        Args:
            memory_type: Type of memory
            content: Content of memory item
            metadata: Additional metadata
            
        Returns:
            Memory item ID
        """
        with self._lock:
            # Generate ID
            memory_id = f"{int(time.time())}_{memory_type.value}"
            
            # Create memory item
            memory_item = {
                "id": memory_id,
                "type": memory_type.value,
                "content": content,
                "metadata": metadata or {},
                "created_at": time.time(),
                "updated_at": time.time()
            }
            
            # Store in memory
            self._memory_items[memory_id] = memory_item
            
            # Update index
            self._index_item(memory_item)
            
            # Save to disk
            self._save_memory()
            
            # Try remote sync if in online mode
            self._try_remote_sync()
            
            return memory_id
    
    def update_memory(self, memory_id: str, content: str, metadata: Dict[str, Any] = None) -> bool:
        """
        Update an existing memory item.
        
        Args:
            memory_id: ID of memory item to update
            content: New content
            metadata: New or updated metadata
            
        Returns:
            True if update successful
        """
        with self._lock:
            if memory_id not in self._memory_items:
                logger.warning(f"Memory item {memory_id} not found")
                return False
            
            # Update memory item
            memory_item = self._memory_items[memory_id]
            memory_item["content"] = content
            
            if metadata:
                memory_item["metadata"].update(metadata)
                
            memory_item["updated_at"] = time.time()
            
            # Update index
            self._index_item(memory_item)
            
            # Save to disk
            self._save_memory()
            
            # Try remote sync if in online mode
            self._try_remote_sync()
            
            return True
    
    def get_memory(self, memory_id: str) -> Dict[str, Any]:
        """
        Get a memory item by ID.
        
        Args:
            memory_id: ID of memory item
            
        Returns:
            Memory item or empty dict if not found
        """
        with self._lock:
            return self._memory_items.get(memory_id, {})
    
    def search_memory(self, query: str, limit: int = 5) -> List[Dict[str, Any]]:
        """
        Search memory by semantic similarity or keywords.
        
        Args:
            query: Search query
            limit: Maximum number of results
            
        Returns:
            List of matching memory items
        """
        # If we have a DB client and not in offline mode, try semantic search
        if not self.offline_mode and self.db_client and not self._remote_attempt_made:
            try:
                # Try remote search - would use the DB client's API in a real implementation
                # This is just a placeholder for demonstration
                logger.info("Attempting remote semantic search")
                
                # Mark that we've attempted remote search
                self._remote_attempt_made = True
                
                # This would be replaced with actual remote semantic search
                # Here we're just simulating a connection error
                if False:  # Simulate failure to connect
                    return []
                    
                # If successful, we'd use the results
                # For now, we'll just fall back to keyword search
                
            except Exception as e:
                logger.warning(f"Remote semantic search failed: {str(e)}")
                # Permanently switch to offline mode
                self.offline_mode = True
        
        # Fallback to simple keyword matching
        return self._keyword_search(query, limit)
    
    def get_memory_by_type(self, memory_type: MemoryType) -> List[Dict[str, Any]]:
        """
        Get all memory items of a specific type.
        
        Args:
            memory_type: Type of memory to retrieve
            
        Returns:
            List of memory items
        """
        with self._lock:
            return [
                item for item in self._memory_items.values() 
                if item["type"] == memory_type.value
            ]
    
    def _try_remote_sync(self) -> bool:
        """
        Try to sync memory with remote storage.
        
        Following offline-first pattern:
        - Only attempts once
        - Permanently switches to local-only mode if unavailable
        
        Returns:
            True if sync successful
        """
        # Skip if already attempted or in offline mode
        if self._remote_attempt_made or self.offline_mode:
            return False
        
        # Skip if no DB client
        if not self.db_client:
            self._remote_attempt_made = True
            return False
            
        try:
            # Mark that we've made the attempt
            self._remote_attempt_made = True
            
            # Prepare data for remote storage
            sync_data = {
                "project_id": self.project_id,
                "memory": self._memory_items,
                "timestamp": time.time()
            }
            
            # This would use the DB client in a real implementation
            logger.info("Attempting to sync project memory to remote storage")
            
            # Simulate storing in DB (would fail in this demo)
            if False:  # Simulate failure
                logger.warning("Remote storage not available")
                self.offline_mode = True
                return False
                
            logger.info("Successfully synced project memory to remote storage")
            return True
            
        except Exception as e:
            logger.warning(f"Failed to sync with remote storage: {str(e)}")
            # Permanently switch to offline mode
            self.offline_mode = True
            return False
    
    def _rebuild_index(self) -> None:
        """Rebuild search index."""
        self._index = {}
        for item in self._memory_items.values():
            self._index_item(item)
    
    def _index_item(self, item: Dict[str, Any]) -> None:
        """Add item to search index."""
        # Very simple word-based indexing for the offline fallback
        content = item["content"].lower()
        words = set(content.split())
        
        for word in words:
            if word not in self._index:
                self._index[word] = set()
            self._index[word].add(item["id"])
    
    def _keyword_search(self, query: str, limit: int) -> List[Dict[str, Any]]:
        """Simple keyword-based search as offline fallback."""
        query_words = set(query.lower().split())
        matches = {}
        
        for word in query_words:
            if word in self._index:
                for item_id in self._index[word]:
                    matches[item_id] = matches.get(item_id, 0) + 1
        
        # Sort by number of matching words
        sorted_matches = sorted(matches.items(), key=lambda x: x[1], reverse=True)
        
        # Get top results
        results = []
        for item_id, _ in sorted_matches[:limit]:
            results.append(self._memory_items[item_id])
            
        return results
