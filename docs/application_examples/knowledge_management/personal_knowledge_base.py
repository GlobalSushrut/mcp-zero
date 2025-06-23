"""
Example: Personal Knowledge Base with Offline-First Resilience
Application Category: Knowledge Management Systems
"""

import os
import time
from typing import Dict, List, Optional, Any
from dataclasses import dataclass
from enum import Enum

# Import MCP Zero components
from mcp_zero.knowledge.store import KnowledgeStore
from mcp_zero.indexing.local_index import LocalSearchIndex
from mcp_zero.indexing.vector_index import VectorSearchIndex
from mcp_zero.connectivity import ConnectionStatus


class ServiceMode(Enum):
    """Operating modes for knowledge services."""
    OFFLINE = "offline"
    ONLINE = "online"


@dataclass
class Document:
    """Document structure for knowledge base."""
    id: str
    title: str
    content: str
    tags: List[str]
    created_at: float
    updated_at: float


class PersonalKnowledgeBase:
    """
    Personal Knowledge Base with offline-first resilience pattern.
    Stores and retrieves knowledge with local indexing and optional enhanced search.
    """
    
    def __init__(
        self,
        storage_path: str,
        user_name: str,
        api_key: Optional[str] = None,
        api_endpoint: Optional[str] = None
    ):
        # Initialize in offline mode by default (offline-first principle)
        self.mode = ServiceMode.OFFLINE
        self.user_name = user_name
        
        # Initialize the storage component
        self.storage = KnowledgeStore(storage_path=storage_path)
        
        # Initialize both indexing engines
        self.local_index = LocalSearchIndex(storage_path=f"{storage_path}/local_index")
        self.vector_index = VectorSearchIndex(
            storage_path=f"{storage_path}/vector_index",
            api_key=api_key,
            api_endpoint=api_endpoint
        )
        
        # Connection status tracking
        self.last_connection_attempt = 0
        
        # Try to connect once if API key is provided
        if api_key:
            self._try_connect_once()
    
    def _try_connect_once(self) -> None:
        """
        Try to connect to the vector service exactly once.
        If successful, switch to online mode.
        If not, remain in offline mode permanently.
        No retry attempts under any circumstances.
        """
        try:
            # Record connection attempt time
            self.last_connection_attempt = time.time()
            
            # Attempt connection with short timeout
            status = self.vector_index.test_connection(timeout_seconds=2)
            
            if status == ConnectionStatus.CONNECTED:
                self.mode = ServiceMode.ONLINE
                print(f"Connected to vector service, operating in enhanced mode")
            else:
                print(f"Vector service unavailable, operating in local mode only")
        except Exception as e:
            print(f"Connection error: {str(e)}. Operating in local mode only.")
            # No retry attempts - remain in offline mode permanently
    
    def add_document(self, doc: Document) -> str:
        """
        Add a document to the knowledge base with offline resilience.
        Always stores locally, and also indexes in vector DB if online.
        """
        # Always save to local storage
        doc_id = self.storage.store_document(doc)
        
        # Always index in local search index
        self.local_index.index_document(doc)
        
        # Additionally use vector index if in online mode
        if self.mode == ServiceMode.ONLINE:
            try:
                self.vector_index.index_document(doc)
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = ServiceMode.OFFLINE
                print(f"Vector indexing failed: {str(e)}. "
                      f"Switching permanently to local indexing only.")
                # No need to do anything else - document is already indexed locally
        
        return doc_id
    
    def search(self, query: str, limit: int = 5) -> List[Document]:
        """
        Search the knowledge base with offline resilience.
        Uses vector search if online, otherwise falls back to local search.
        """
        if self.mode == ServiceMode.ONLINE:
            try:
                # Try vector search
                results = self.vector_index.search(query, limit=limit)
                if results:
                    return results
                # Fall back to local search if vector search returns empty
                return self.local_index.search(query, limit=limit)
            except Exception as e:
                # Permanently fall back to offline mode on failure
                self.mode = ServiceMode.OFFLINE
                print(f"Vector search failed: {str(e)}. "
                      f"Switching permanently to local search.")
                # Continue with local search
        
        # Use local search (either as default or after fallback)
        return self.local_index.search(query, limit=limit)
    
    def get_status(self) -> Dict[str, Any]:
        """Get current status of the knowledge base."""
        return {
            "mode": self.mode.value,
            "document_count": self.storage.count_documents(),
            "last_connection_attempt": self.last_connection_attempt,
            "local_index_size": self.local_index.get_size(),
            "vector_index_available": self.mode == ServiceMode.ONLINE
        }


# Example usage
if __name__ == "__main__":
    # Create knowledge base with offline-first resilience
    kb = PersonalKnowledgeBase(
        storage_path="./knowledge_data",
        user_name="researcher_1",
        api_key=os.environ.get("VECTOR_API_KEY"),
        api_endpoint=os.environ.get("VECTOR_API_ENDPOINT")
    )
    
    # Add a document - works regardless of connectivity
    doc = Document(
        id="note-1",
        title="Offline-First Resilience Pattern",
        content="The offline-first resilience pattern ensures applications work without connectivity...",
        tags=["pattern", "resilience", "offline-first"],
        created_at=time.time(),
        updated_at=time.time()
    )
    kb.add_document(doc)
    
    # Search always works - enhanced if online, basic if offline
    results = kb.search("resilience pattern")
    print(f"Found {len(results)} results in {kb.mode.value} mode")
    
    # System status
    status = kb.get_status()
    print(f"Knowledge base status: {status}")
