#!/usr/bin/env python3
"""
MCP-ZERO P2P Mesh Network Node
Implements a single node in the MCP-ZERO mesh network
"""
import asyncio
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Set, Any, Optional, Callable

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('mesh_node')

class MeshNode:
    """
    A node in the MCP-ZERO P2P mesh network
    
    Handles peer discovery, resource querying, and message broadcasting
    """
    
    def __init__(self, node_id: str = None, host: str = "localhost", port: int = 8765):
        """
        Initialize a mesh node
        
        Args:
            node_id: Unique identifier for this node (optional, will be generated if not provided)
            host: Hostname to bind to
            port: Port to bind to
        """
        self.node_id = node_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        
        self.is_running = False
        self.server = None
        self.peers: Dict[str, Dict[str, Any]] = {}  # node_id -> {ws_conn, address, last_seen, etc.}
        self.resources: Dict[str, Dict[str, Any]] = {}  # resource_id -> {type, metadata, etc.}
        self.message_handlers: Dict[str, List[Callable]] = {}
        self.discovery_peers: Set[str] = set()  # Bootstrap peers for discovery
        
        # Subscribe to default message types
        self._subscribe('discovery', self._handle_discovery)
        self._subscribe('resource_query', self._handle_resource_query)
        self._subscribe('resource_announcement', self._handle_resource_announcement)
        
        logger.info(f"Initialized mesh node with ID: {self.node_id}")
        
    async def start(self):
        """Start the mesh node server"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start WebSocket server
        self.server = await websockets.serve(
            self._handle_connection,
            self.host,
            self.port
        )
        
        logger.info(f"Mesh node server started at ws://{self.host}:{self.port}")
        
        # Start periodic tasks
        asyncio.create_task(self._periodic_discovery())
        asyncio.create_task(self._periodic_heartbeat())
        
        # Keep the server running
        await self.server.wait_closed()
        
    async def stop(self):
        """Stop the mesh node server"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Close all peer connections
        for peer_id, peer_info in self.peers.items():
            if 'ws_conn' in peer_info and not peer_info['ws_conn'].closed:
                await peer_info['ws_conn'].close()
                
        # Close server if running
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        logger.info("Mesh node server stopped")
        
    async def connect_to_peer(self, address: str) -> bool:
        """
        Connect to another mesh node
        
        Args:
            address: WebSocket address of the peer node (ws://host:port)
            
        Returns:
            True if connection successful, False otherwise
        """
        try:
            # Connect to peer
            ws_conn = await websockets.connect(address)
            
            # Send discovery message
            await ws_conn.send(json.dumps({
                'type': 'discovery',
                'sender_id': self.node_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'node_type': 'full',
                    'address': f"ws://{self.host}:{self.port}",
                    'resources': list(self.resources.keys())
                }
            }))
            
            # Add to discovery peers
            self.discovery_peers.add(address)
            
            logger.info(f"Connected to peer at {address}")
            return True
        except Exception as e:
            logger.error(f"Error connecting to peer at {address}: {str(e)}")
            return False
            
    async def register_resource(self, resource_id: str, resource_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Register a resource with this node
        
        Args:
            resource_id: Unique identifier for the resource
            resource_type: Type of resource (agent, plugin, service, etc.)
            metadata: Additional metadata for the resource
            
        Returns:
            True if registration successful, False otherwise
        """
        try:
            # Register resource locally
            self.resources[resource_id] = {
                'type': resource_type,
                'metadata': metadata,
                'registered_at': datetime.utcnow().isoformat()
            }
            
            # Announce resource to peers
            await self._broadcast_message({
                'type': 'resource_announcement',
                'sender_id': self.node_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'resource_id': resource_id,
                    'resource_type': resource_type,
                    'metadata': metadata
                }
            })
            
            logger.info(f"Registered resource {resource_id} of type {resource_type}")
            return True
        except Exception as e:
            logger.error(f"Error registering resource {resource_id}: {str(e)}")
            return False
