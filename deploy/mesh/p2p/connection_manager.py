#!/usr/bin/env python3
"""
MCP-ZERO Mesh Network Connection Manager
Manages P2P connections in the mesh network
"""
import asyncio
import json
import logging
from datetime import datetime
from typing import Dict, Set, Any, Optional

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('connection_manager')

class ConnectionManager:
    """
    Manages connections to other nodes in the mesh network
    """
    
    def __init__(self, node_id: str, host: str, port: int):
        """
        Initialize the connection manager
        
        Args:
            node_id: ID of the local node
            host: Hostname of the local node
            port: Port of the local node
        """
        self.node_id = node_id
        self.host = host
        self.port = port
        self.connections: Dict[str, Any] = {}  # peer_id -> connection info
        self.discovery_addresses: Set[str] = set()  # Known peer addresses
        self.is_running = False
        
    async def start(self):
        """Start the connection manager"""
        self.is_running = True
        # Start the connection maintenance task
        asyncio.create_task(self._maintain_connections())
        logger.info("Connection manager started")
        
    async def stop(self):
        """Stop the connection manager"""
        self.is_running = False
        # Close all connections
        for peer_id, conn_info in list(self.connections.items()):
            if 'ws_conn' in conn_info and not conn_info['ws_conn'].closed:
                await conn_info['ws_conn'].close()
        logger.info("Connection manager stopped")
        
    async def connect_to_peer(self, address: str) -> Optional[str]:
        """
        Connect to a peer at the given address
        
        Args:
            address: WebSocket address (ws://host:port)
            
        Returns:
            Peer node ID if successful, None otherwise
        """
        try:
            # Connect to the peer
            ws_conn = await websockets.connect(address)
            
            # Send discovery message
            await ws_conn.send(json.dumps({
                'type': 'discovery',
                'sender_id': self.node_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'node_type': 'full',
                    'address': f"ws://{self.host}:{self.port}"
                }
            }))
            
            # Wait for response to get peer ID
            response = await asyncio.wait_for(ws_conn.recv(), 5.0)
            message = json.loads(response)
            
            if message.get('type') in ['discovery', 'discovery_response']:
                peer_id = message.get('sender_id')
                if peer_id and peer_id != self.node_id:
                    # Store the connection
                    self.connections[peer_id] = {
                        'ws_conn': ws_conn,
                        'address': address,
                        'connected_at': datetime.utcnow().isoformat(),
                        'last_seen': datetime.utcnow().isoformat()
                    }
                    
                    # Add to discovery addresses
                    self.discovery_addresses.add(address)
                    
                    logger.info(f"Connected to peer {peer_id} at {address}")
                    return peer_id
                    
            await ws_conn.close()
            return None
        except Exception as e:
            logger.error(f"Error connecting to peer at {address}: {str(e)}")
            return None
            
    async def broadcast_message(self, message: Dict[str, Any]):
        """
        Broadcast a message to all connected peers
        
        Args:
            message: Message to broadcast
        """
        message_json = json.dumps(message)
        
        for peer_id, conn_info in list(self.connections.items()):
            ws_conn = conn_info.get('ws_conn')
            if ws_conn and not ws_conn.closed:
                try:
                    await ws_conn.send(message_json)
                except Exception as e:
                    logger.error(f"Error sending message to peer {peer_id}: {str(e)}")
                    # Close and remove failed connection
                    await ws_conn.close()
                    self.connections.pop(peer_id, None)
    
    async def _maintain_connections(self):
        """Periodically check and maintain connections"""
        while self.is_running:
            try:
                # Check existing connections
                for peer_id, conn_info in list(self.connections.items()):
                    ws_conn = conn_info.get('ws_conn')
                    if not ws_conn or ws_conn.closed:
                        logger.info(f"Connection to peer {peer_id} lost, removing")
                        self.connections.pop(peer_id, None)
                        
                # Sleep for a while
                await asyncio.sleep(30)
            except Exception as e:
                logger.error(f"Error in connection maintenance: {str(e)}")
                await asyncio.sleep(5)
