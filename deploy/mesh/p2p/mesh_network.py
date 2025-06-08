#!/usr/bin/env python3
"""
MCP-ZERO Mesh Network
Main implementation integrating all mesh network components
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional, Set, Callable

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

# Import mesh components
from deploy.mesh.p2p.node import MeshNode
from deploy.mesh.p2p.connection_manager import ConnectionManager
from deploy.mesh.p2p.resource_directory import ResourceDirectory
from deploy.mesh.p2p.message_handler import MessageHandler

# Try to import cryptographic verification
try:
    from infrastructure.security.crypto_verifier import verify_signature
    CRYPTO_AVAILABLE = True
except ImportError:
    CRYPTO_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('mesh_network')

class MeshNetwork:
    """
    Main MCP-ZERO Mesh Network implementation
    
    Provides a decentralized network for resource discovery, 
    agreement verification, and secure communication.
    """
    
    def __init__(self, node_id: str = None, host: str = "localhost", port: int = 8765):
        """
        Initialize the mesh network
        
        Args:
            node_id: Unique identifier for this node (optional)
            host: Hostname to bind to
            port: Port to bind to
        """
        # Create a unique node ID if none provided
        self.node_id = node_id or str(uuid.uuid4())
        self.host = host
        self.port = port
        
        # Initialize components
        self.node = MeshNode(self.node_id, self.host, self.port)
        self.resource_directory = ResourceDirectory(self.node_id)
        self.connection_manager = ConnectionManager(self.node_id, self.host, self.port)
        
        # State tracking
        self.is_running = False
        self.bootstrap_peers = set()
        self.event_handlers = {}
        
        logger.info(f"Initialized mesh network node {self.node_id}")
        
    async def start(self):
        """Start the mesh network node"""
        if self.is_running:
            return
            
        self.is_running = True
        
        # Start components
        await self.node.start()
        await self.connection_manager.start()
        
        # Connect to bootstrap peers
        for peer_address in self.bootstrap_peers:
            asyncio.create_task(self.connect_to_peer(peer_address))
            
        logger.info(f"Mesh network node started at ws://{self.host}:{self.port}")
        
    async def stop(self):
        """Stop the mesh network node"""
        if not self.is_running:
            return
            
        self.is_running = False
        
        # Stop components
        await self.connection_manager.stop()
        await self.node.stop()
        
        logger.info("Mesh network node stopped")
        
    def add_bootstrap_peer(self, address: str):
        """
        Add a bootstrap peer for initial network discovery
        
        Args:
            address: WebSocket address of the peer
        """
        self.bootstrap_peers.add(address)
        
    async def connect_to_peer(self, address: str) -> bool:
        """
        Connect to another mesh node
        
        Args:
            address: WebSocket address of the peer
            
        Returns:
            True if connection successful, False otherwise
        """
        peer_id = await self.connection_manager.connect_to_peer(address)
        return peer_id is not None
        
    async def register_resource(self, resource_id: str, resource_type: str, metadata: Dict[str, Any], 
                               signature: str = None) -> bool:
        """
        Register a resource with the mesh network
        
        Args:
            resource_id: Unique ID for the resource
            resource_type: Type of resource
            metadata: Resource metadata
            signature: Cryptographic signature (optional)
            
        Returns:
            True if registration successful, False otherwise
        """
        # Verify signature if available and crypto module is loaded
        if signature and CRYPTO_AVAILABLE:
            # Create message to verify (resource_id + type + sorted metadata)
            message = resource_id + resource_type + json.dumps(metadata, sort_keys=True)
            
            if not verify_signature(message, signature):
                logger.warning(f"Invalid signature for resource {resource_id}")
                return False
                
        # Add to local resource directory
        added = self.resource_directory.add_local_resource(resource_id, resource_type, metadata)
        
        # Announce to the network if newly added
        if added:
            await self.node.register_resource(resource_id, resource_type, metadata)
            
        return True
        
    async def query_resources(self, resource_type: str = None, metadata_filter: Dict[str, Any] = None,
                             local_only: bool = False, timeout: int = 5) -> Dict[str, Dict[str, Any]]:
        """
        Query for resources in the mesh network
        
        Args:
            resource_type: Type of resources to query (optional)
            metadata_filter: Filter by metadata (optional)
            local_only: Only query local resources
            timeout: Timeout for remote queries in seconds
            
        Returns:
            Dictionary of matching resource IDs to resource info
        """
        # Query local resources first
        results = self.resource_directory.query_resources(
            resource_type=resource_type,
            metadata_filter=metadata_filter,
            include_local=True,
            include_remote=True
        )
        
        # If local_only, return just local results
        if local_only:
            return results
            
        # Query remote peers
        query_message = {
            'type': 'resource_query',
            'sender_id': self.node_id,
            'timestamp': datetime.utcnow().isoformat(),
            'data': {
                'query_id': str(uuid.uuid4()),
                'query': {
                    'type': resource_type,
                    'filter': metadata_filter
                }
            }
        }
        
        # Broadcast query and collect responses
        await self.connection_manager.broadcast_message(query_message)
        
        # Wait for responses (in a production system, we'd handle this asynchronously)
        await asyncio.sleep(timeout)
        
        # Return combined results (local + what we've collected from peers)
        return results
        
    def subscribe_to_event(self, event_type: str, handler: Callable):
        """
        Subscribe to mesh network events
        
        Args:
            event_type: Type of event to subscribe to
            handler: Handler function to call when event occurs
        """
        if event_type not in self.event_handlers:
            self.event_handlers[event_type] = []
            
        self.event_handlers[event_type].append(handler)
        logger.info(f"Added handler for event type {event_type}")
        
    async def _emit_event(self, event_type: str, data: Any):
        """
        Emit an event to all subscribed handlers
        
        Args:
            event_type: Type of event
            data: Event data
        """
        if event_type in self.event_handlers:
            for handler in self.event_handlers[event_type]:
                try:
                    if asyncio.iscoroutinefunction(handler):
                        await handler(data)
                    else:
                        handler(data)
                except Exception as e:
                    logger.error(f"Error in event handler for {event_type}: {str(e)}")
                    
    # Compatibility layer with MCP-ZERO kernel
    async def register_agent_resource(self, agent_id: str, capabilities: List[str], 
                                    constraints: Dict[str, Any]) -> bool:
        """
        Register an agent as a resource in the mesh network
        
        Args:
            agent_id: Agent ID
            capabilities: List of agent capabilities
            constraints: Hardware/resource constraints
            
        Returns:
            True if registration successful
        """
        # Check CPU/RAM constraints against MCP-ZERO limits
        if 'cpu' in constraints and constraints['cpu'] > 0.27:
            logger.warning(f"Agent {agent_id} exceeds CPU constraints (> 27%)")
            constraints['cpu'] = 0.27
            
        if 'memory' in constraints and constraints['memory'] > 827:
            logger.warning(f"Agent {agent_id} exceeds memory constraints (> 827MB)")
            constraints['memory'] = 827
            
        # Build metadata
        metadata = {
            'capabilities': capabilities,
            'constraints': constraints,
            'registered_by': self.node_id,
            'trace_enabled': True,  # Enable ZK tracing by default
        }
        
        # Register as a resource
        return await self.register_resource(
            resource_id=agent_id,
            resource_type='agent',
            metadata=metadata
        )
