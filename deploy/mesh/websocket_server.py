#!/usr/bin/env python3
"""
WebSocket Server for MCP-ZERO Mesh Network
Enables agent communication across decentralized nodes
"""
import asyncio
import json
import logging
import ssl
import uuid
from typing import Dict, List, Set, Any, Optional

import websockets
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding
from cryptography.hazmat.primitives.asymmetric import rsa

# Local imports
from mesh_node import MeshNode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('websocket_server')

class WebSocketMeshServer(MeshNode):
    """WebSocket server for MCP-ZERO mesh network"""
    
    def __init__(self, host: str = "0.0.0.0", port: int = 8765, 
                 use_ssl: bool = False, ssl_cert: Optional[str] = None, 
                 ssl_key: Optional[str] = None):
        """Initialize WebSocket mesh server"""
        super().__init__(node_type="mesh_server")
        self.host = host
        self.port = port
        self.use_ssl = use_ssl
        self.ssl_cert = ssl_cert
        self.ssl_key = ssl_key
        self.connections: Dict[str, websockets.WebSocketServerProtocol] = {}
        self.server = None
        
        # Generate signing keys
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048
        )
        self.public_key = self.private_key.public_key()
        
        logger.info(f"WebSocket mesh server initialized at {host}:{port}")
        
    async def start(self) -> None:
        """Start the WebSocket server"""
        logger.info(f"Starting WebSocket mesh server on {self.host}:{self.port}")
        
        ssl_context = None
        if self.use_ssl and self.ssl_cert and self.ssl_key:
            ssl_context = ssl.SSLContext(ssl.PROTOCOL_TLS_SERVER)
            ssl_context.load_cert_chain(self.ssl_cert, self.ssl_key)
            
        self.server = await websockets.serve(
            self.handle_connection, self.host, self.port, ssl=ssl_context
        )
        
        await self.connect()  # Mark node as connected
        logger.info(f"WebSocket mesh server running at ws{'s' if self.use_ssl else ''}://{self.host}:{self.port}")
        
    async def stop(self) -> None:
        """Stop the WebSocket server"""
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            await self.disconnect()  # Mark node as disconnected
            logger.info("WebSocket mesh server stopped")
            
    async def handle_connection(self, websocket, path) -> None:
        """Handle incoming WebSocket connections"""
        connection_id = str(uuid.uuid4())
        ip_address = websocket.remote_address[0]
        
        logger.info(f"New connection from {ip_address}, assigned ID: {connection_id}")
        self.connections[connection_id] = websocket
        
        try:
            # Handle the connection registration
            await self.send_message(websocket, {
                "type": "connection_ack",
                "connection_id": connection_id,
                "server_id": self.node_id,
                "timestamp": self.last_heartbeat.isoformat()
            })
            
            # Process messages
            async for message in websocket:
                await self.process_message(connection_id, websocket, message)
                
        except websockets.exceptions.ConnectionClosed:
            logger.info(f"Connection {connection_id} closed")
        finally:
            # Clean up when connection is closed
            if connection_id in self.connections:
                del self.connections[connection_id]
                
    async def process_message(self, connection_id: str, websocket, message: str) -> None:
        """Process incoming WebSocket messages"""
        try:
            data = json.loads(message)
            message_type = data.get('type', '')
            
            logger.debug(f"Received '{message_type}' message from {connection_id}")
            
            if message_type == 'heartbeat':
                await self.handle_heartbeat(connection_id, websocket, data)
            elif message_type == 'agent_deploy':
                await self.handle_agent_deploy(connection_id, websocket, data)
            elif message_type == 'mesh_query':
                await self.handle_mesh_query(connection_id, websocket, data)
            else:
                await self.send_message(websocket, {
                    "type": "error",
                    "error": "Unknown message type",
                    "original_type": message_type
                })
                
        except json.JSONDecodeError:
            logger.warning(f"Received invalid JSON from {connection_id}")
            await self.send_message(websocket, {
                "type": "error",
                "error": "Invalid JSON format"
            })
            
    async def send_message(self, websocket, data: Dict[str, Any]) -> None:
        """Send a message through the WebSocket"""
        # Sign the message for integrity verification
        message_str = json.dumps(data)
        signature = self.private_key.sign(
            message_str.encode('utf-8'),
            padding.PSS(
                mgf=padding.MGF1(hashes.SHA256()),
                salt_length=padding.PSS.MAX_LENGTH
            ),
            hashes.SHA256()
        )
        
        # Add signature to the message
        data['signature'] = signature.hex()
        
        # Send the signed message
        await websocket.send(json.dumps(data))
        
    async def handle_heartbeat(self, connection_id: str, websocket, data: Dict[str, Any]) -> None:
        """Handle heartbeat messages"""
        await self.send_message(websocket, {
            "type": "heartbeat_ack",
            "server_time": self.last_heartbeat.isoformat()
        })
        
    async def handle_agent_deploy(self, connection_id: str, websocket, data: Dict[str, Any]) -> None:
        """Handle agent deployment requests"""
        agent_id = data.get('agent_id')
        config = data.get('config', {})
        
        if not agent_id:
            await self.send_message(websocket, {
                "type": "error",
                "error": "Missing agent_id in deploy request"
            })
            return
            
        logger.info(f"Processing agent deployment request for agent: {agent_id}")
        
        # TODO: Implement actual agent deployment
        # For now, just acknowledge the request
        await self.send_message(websocket, {
            "type": "deploy_ack",
            "agent_id": agent_id,
            "status": "pending",
            "message": "Deployment request received"
        })
        
    async def handle_mesh_query(self, connection_id: str, websocket, data: Dict[str, Any]) -> None:
        """Handle mesh network status queries"""
        query_type = data.get('query_type', '')
        
        if query_type == 'status':
            await self.send_message(websocket, {
                "type": "mesh_status",
                "node_id": self.node_id,
                "node_type": self.node_type,
                "connected_peers": len(self.peers),
                "active_connections": len(self.connections),
                "uptime": (self.last_heartbeat - datetime.strptime(self.metadata['created'], 
                                                               "%Y-%m-%dT%H:%M:%S.%f")).total_seconds()
            })
        else:
            await self.send_message(websocket, {
                "type": "error",
                "error": "Unknown query type",
                "original_query": query_type
            })
