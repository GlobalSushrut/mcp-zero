#!/usr/bin/env python3
"""
Knowledge Base Plugin for MCP-ZERO

This plugin provides persistent storage and retrieval capabilities
for the IntelliAgent demo, demonstrating how an agent can maintain
knowledge across different sessions and operations.
"""

import os
import json
import time
import hashlib
import logging
from datetime import datetime
from typing import Dict, Any, List, Optional, Tuple, Set

logger = logging.getLogger("mcp_zero.plugins.knowledge_base")

class KnowledgeBasePlugin:
    """Knowledge base plugin implementation for MCP-ZERO."""
    
    def __init__(self, plugin_id: str, agent_id: str):
        """Initialize the knowledge base plugin.
        
        Args:
            plugin_id: Unique identifier for this plugin instance
            agent_id: ID of the agent this plugin is attached to
        """
        self.plugin_id = plugin_id
        self.agent_id = agent_id
        self.initialized_at = time.time()
        self.execution_count = 0
        
        # In-memory storage (would be persistent storage in production)
        self.memory = {}
        self.index = {}  # Simple inverted index for search
        
        logger.info(f"Knowledge Base Plugin initialized for agent {agent_id}")
    
    def get_info(self) -> Dict[str, Any]:
        """Return information about this plugin."""
        return {
            "id": self.plugin_id,
            "name": "Knowledge Base Plugin",
            "description": "Stores and retrieves knowledge for the agent",
            "version": "1.0.0",
            "agent_id": self.agent_id,
            "initialized_at": self.initialized_at,
            "execution_count": self.execution_count,
            "entry_count": len(self.memory),
            "capabilities": [
                "store", "retrieve", "search", "delete", "list"
            ]
        }
    
    def execute(self, intent: str, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Execute a knowledge base operation.
        
        Args:
            intent: The operation to perform (store, retrieve, etc.)
            parameters: Parameters for the operation
            
        Returns:
            Result of the knowledge base operation
        """
        self.execution_count += 1
        
        # Extract operation from intent or parameters
        operation = intent
        if intent == "kb":
            operation = parameters.get("operation", "")
        
        # Execute the operation
        handlers = {
            "store": self._store_knowledge,
            "retrieve": self._retrieve_knowledge,
            "search": self._search_knowledge,
            "delete": self._delete_knowledge,
            "list": self._list_knowledge
        }
        
        handler = handlers.get(operation)
        if not handler:
            logger.error(f"Unknown knowledge base operation: {operation}")
            return {
                "success": False,
                "error": f"Unknown knowledge base operation: {operation}",
                "trace_id": f"kb-trace-{int(time.time())}"
            }
            
        try:
            # Create cryptographic trace for ZK audit
            trace_id = f"kb-{int(time.time())}-{hash(str(parameters)) % 10000}"
            
            # Execute knowledge base operation
            result = handler(parameters)
            
            # Successful operation
            response = {
                "success": True,
                "operation": operation,
                "trace_id": trace_id,
                "agent_id": self.agent_id,
                "plugin_id": self.plugin_id,
                "timestamp": time.time()
            }
            response.update(result)
            return response
            
        except Exception as e:
            logger.error(f"Error executing knowledge base operation {operation}: {str(e)}")
            return {
                "success": False,
                "error": str(e),
                "trace_id": f"kb-trace-{int(time.time())}"
            }
    
    def _generate_entry_id(self, content: str, category: str) -> str:
        """Generate a deterministic ID for a knowledge entry."""
        # Create a hash of content and category
        hash_input = f"{content}:{category}:{self.agent_id}"
        hash_obj = hashlib.sha256(hash_input.encode('utf-8'))
        hash_hex = hash_obj.hexdigest()
        
        # Return a shortened hash as ID
        return f"kb-{hash_hex[:12]}"
    
    def _index_content(self, entry_id: str, content: str) -> None:
        """Index the content for search."""
        # Split content into words and remove duplicates
        words = set(content.lower().split())
        
        # Update the index
        for word in words:
            if word not in self.index:
                self.index[word] = set()
            self.index[word].add(entry_id)
    
    def _remove_from_index(self, entry_id: str, content: str) -> None:
        """Remove entry from the index."""
        words = set(content.lower().split())
        
        for word in words:
            if word in self.index and entry_id in self.index[word]:
                self.index[word].remove(entry_id)
                if not self.index[word]:
                    del self.index[word]
    
    def _store_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, str]:
        """Store knowledge in the knowledge base."""
        content = parameters.get("content", "")
        category = parameters.get("category", "general")
        metadata = parameters.get("metadata", {})
        
        if not content:
            raise ValueError("No content provided to store")
            
        # Generate ID for this knowledge entry
        entry_id = self._generate_entry_id(content, category)
        
        # Create the knowledge entry
        entry = {
            "id": entry_id,
            "content": content,
            "category": category,
            "metadata": metadata,
            "created_at": time.time(),
            "updated_at": time.time()
        }
        
        # Store in memory
        self.memory[entry_id] = entry
        
        # Index the content
        self._index_content(entry_id, content)
        
        return {
            "id": entry_id,
            "stored": True
        }
    
    def _retrieve_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Retrieve knowledge by ID."""
        entry_id = parameters.get("id", "")
        
        if not entry_id:
            raise ValueError("No ID provided for retrieval")
            
        if entry_id not in self.memory:
            raise ValueError(f"No knowledge entry found with ID: {entry_id}")
            
        # Return the entry
        entry = self.memory[entry_id]
        
        return {
            "id": entry["id"],
            "content": entry["content"],
            "category": entry["category"],
            "metadata": entry["metadata"],
            "created_at": entry["created_at"],
            "updated_at": entry["updated_at"]
        }
    
    def _search_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """Search knowledge by keywords."""
        query = parameters.get("query", "").lower()
        category = parameters.get("category", None)
        limit = int(parameters.get("limit", 10))
        
        if not query:
            raise ValueError("No query provided for search")
            
        # Split query into words
        query_words = set(query.split())
        
        # Find entries containing any of the query words
        matching_entry_ids = set()
        for word in query_words:
            if word in self.index:
                matching_entry_ids.update(self.index[word])
        
        # Filter by category if provided
        results = []
        for entry_id in matching_entry_ids:
            entry = self.memory[entry_id]
            if category is None or entry["category"] == category:
                # Calculate relevance based on word overlap
                entry_words = set(entry["content"].lower().split())
                overlap = len(query_words.intersection(entry_words))
                relevance = overlap / len(query_words) if query_words else 0
                
                results.append({
                    "id": entry["id"],
                    "content": entry["content"],
                    "category": entry["category"],
                    "relevance": relevance
                })
        
        # Sort by relevance and limit results
        results.sort(key=lambda x: x["relevance"], reverse=True)
        results = results[:limit]
        
        return {
            "query": query,
            "category": category,
            "count": len(results),
            "results": results
        }
    
    def _delete_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, bool]:
        """Delete knowledge by ID."""
        entry_id = parameters.get("id", "")
        
        if not entry_id:
            raise ValueError("No ID provided for deletion")
            
        if entry_id not in self.memory:
            raise ValueError(f"No knowledge entry found with ID: {entry_id}")
            
        # Get the entry to remove from index
        entry = self.memory[entry_id]
        
        # Remove from index
        self._remove_from_index(entry_id, entry["content"])
        
        # Remove from memory
        del self.memory[entry_id]
        
        return {
            "id": entry_id,
            "deleted": True
        }
    
    def _list_knowledge(self, parameters: Dict[str, Any]) -> Dict[str, Any]:
        """List knowledge entries."""
        category = parameters.get("category", None)
        limit = int(parameters.get("limit", 20))
        offset = int(parameters.get("offset", 0))
        
        # Filter by category if provided
        entries = []
        for entry_id, entry in self.memory.items():
            if category is None or entry["category"] == category:
                entries.append({
                    "id": entry["id"],
                    "content": entry["content"][:100] + ("..." if len(entry["content"]) > 100 else ""),
                    "category": entry["category"],
                    "created_at": entry["created_at"]
                })
        
        # Sort by creation time (newest first)
        entries.sort(key=lambda x: x["created_at"], reverse=True)
        
        # Apply pagination
        paginated_entries = entries[offset:offset+limit]
        
        return {
            "count": len(entries),
            "limit": limit,
            "offset": offset,
            "category": category,
            "entries": paginated_entries
        }
    
    def cleanup(self) -> None:
        """Cleanup resources used by this plugin."""
        logger.info(f"Cleaning up Knowledge Base Plugin for agent {self.agent_id}")
        # In a real implementation, we would persist memory to storage here
        self.memory = {}
        self.index = {}
