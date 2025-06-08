#!/usr/bin/env python3
"""
MCP-ZERO Mesh Node - Base class for mesh network nodes
"""
import asyncio
import json
import logging
import uuid
from datetime import datetime
from typing import Dict, List, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('mesh_node')

class MeshNode:
    """Base class for all mesh network nodes"""
    
    def __init__(self, node_id: Optional[str] = None, node_type: str = "standard"):
        """Initialize the mesh node with optional ID and type"""
        self.node_id = node_id or str(uuid.uuid4())
        self.node_type = node_type
        self.peers: Set[str] = set()
        self.connected = False
        self.heartbeat_interval = 30  # seconds
        self.last_heartbeat = datetime.now()
        self.metadata = {
            "created": datetime.now().isoformat(),
            "version": "v7.0.0",
            "type": node_type
        }
        logger.info(f"MeshNode initialized with ID: {self.node_id}")
        
    async def connect(self) -> bool:
        """Connect node to the mesh network"""
        self.connected = True
        logger.info(f"Node {self.node_id} connected to mesh network")
        return True
        
    async def disconnect(self) -> bool:
        """Disconnect node from the mesh network"""
        self.connected = False
        logger.info(f"Node {self.node_id} disconnected from mesh network")
        return True
        
    async def send_heartbeat(self) -> None:
        """Send heartbeat to peers"""
        if not self.connected:
            return
            
        self.last_heartbeat = datetime.now()
        logger.debug(f"Node {self.node_id} sent heartbeat at {self.last_heartbeat}")
        
    async def add_peer(self, peer_id: str) -> bool:
        """Add peer to the node's peer list"""
        if peer_id not in self.peers:
            self.peers.add(peer_id)
            logger.info(f"Node {self.node_id} added peer: {peer_id}")
            return True
        return False
        
    async def remove_peer(self, peer_id: str) -> bool:
        """Remove peer from the node's peer list"""
        if peer_id in self.peers:
            self.peers.remove(peer_id)
            logger.info(f"Node {self.node_id} removed peer: {peer_id}")
            return True
        return False
        
    def to_dict(self) -> Dict:
        """Return node information as a dictionary"""
        return {
            "id": self.node_id,
            "type": self.node_type,
            "connected": self.connected,
            "peer_count": len(self.peers),
            "last_heartbeat": self.last_heartbeat.isoformat(),
            "metadata": self.metadata
        }
