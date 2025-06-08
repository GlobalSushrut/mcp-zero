#!/usr/bin/env python3
"""
MCP-ZERO WebSocket Mesh Client
Connects agents to the MCP-ZERO mesh network via WebSocket
"""
import asyncio
import json
import logging
import os
import ssl
import sys
import time
import uuid
from typing import Dict, List, Optional, Any, Callable

import websockets
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives import hashes
from cryptography.hazmat.primitives.asymmetric import padding, rsa
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key,
    load_pem_public_key,
    Encoding,
    PrivateFormat,
    PublicFormat,
    NoEncryption,
)

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from deploy.mesh.mesh_node import MeshNode

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('websocket_client')

class WebSocketMeshClient(MeshNode):
    """Client implementation for connecting to the MCP-ZERO mesh network"""
    
    def __init__(self,
                 node_id: Optional[str] = None,
                 mesh_url: str = "ws://localhost:8765",
                 api_key: Optional[str] = None,
                 use_ssl: bool = True,
                 heartbeat_interval: int = 30):
        """Initialize the WebSocket mesh client"""
        super().__init__(node_id or f"client-{str(uuid.uuid4())[:8]}")
        self.mesh_url = mesh_url
        self.api_key = api_key
        self.use_ssl = use_ssl
        self.heartbeat_interval = heartbeat_interval
        
        # Connection state
        self.connection = None
        self.connected = False
        self.last_heartbeat = 0
        self.heartbeat_task = None
        self.message_handlers = {}
        
        # Generate or load RSA key pair for signing messages
        self.private_key = rsa.generate_private_key(
            public_exponent=65537,
            key_size=2048,
            backend=default_backend()
        )
        self.public_key = self.private_key.public_key()
        
        logger.info(f"WebSocket mesh client initialized with ID: {self.node_id}")
        
    async def connect(self) -> bool:
        """Connect to the mesh network WebSocket server"""
        if self.connected:
            logger.warning("Already connected to mesh network")
            return True
            
        logger.info(f"Connecting to mesh network at {self.mesh_url}...")
        
        try:
            # Set up SSL context if needed
            ssl_context = None
            if self.mesh_url.startswith("wss://") and self.use_ssl:
                ssl_context = ssl.create_default_context()
                
            # Connect to WebSocket server
            self.connection = await websockets.connect(
                self.mesh_url,
                ssl=ssl_context
            )
            
            # Register with the server
            await self.register()
            
            # Start heartbeat task
            self.heartbeat_task = asyncio.create_task(self.heartbeat_loop())
            
            # Start message receiver task
            asyncio.create_task(self.message_receiver())
            
            self.connected = True
            logger.info(f"Connected to mesh network as {self.node_id}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to connect to mesh network: {str(e)}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from the mesh network"""
        if not self.connected:
            return
            
        logger.info("Disconnecting from mesh network...")
        
        # Cancel heartbeat task
        if self.heartbeat_task:
            self.heartbeat_task.cancel()
            
        # Close WebSocket connection
        if self.connection:
            await self.connection.close()
            
        self.connected = False
        logger.info("Disconnected from mesh network")
        
    async def register(self) -> bool:
        """Register with the mesh network server"""
        public_key_pem = self.public_key.public_bytes(
            encoding=Encoding.PEM,
            format=PublicFormat.SubjectPublicKeyInfo
        ).decode('utf-8')
        
        registration_message = {
            "type": "register",
            "node_id": self.node_id,
            "node_type": self.metadata.get("type", "agent"),
            "capabilities": self.metadata.get("capabilities", []),
            "public_key": public_key_pem
        }
        
        if self.api_key:
            registration_message["api_key"] = self.api_key
            
        await self.send_message(registration_message)
        
        # Wait for registration acknowledgment
        try:
            response = await asyncio.wait_for(self.connection.recv(), timeout=10)
            data = json.loads(response)
            
            if data.get("type") == "register_ack" and data.get("status") == "success":
                logger.info("Registration successful")
                
                # Add peers from server response if provided
                if "peers" in data:
                    for peer_data in data["peers"]:
                        self.add_peer(
                            peer_data["node_id"],
                            peer_data.get("metadata", {})
                        )
                    logger.info(f"Added {len(data['peers'])} peers from server")
                    
                return True
            else:
                logger.error(f"Registration failed: {data.get('message', 'Unknown error')}")
                return False
                
        except asyncio.TimeoutError:
            logger.error("Registration timed out")
            return False
        except Exception as e:
            logger.error(f"Registration error: {str(e)}")
            return False
            
    async def heartbeat_loop(self) -> None:
        """Send periodic heartbeats to the server"""
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                heartbeat_message = {
                    "type": "heartbeat",
                    "node_id": self.node_id,
                    "timestamp": time.time()
                }
                
                await self.send_message(heartbeat_message)
                self.last_heartbeat = time.time()
                logger.debug("Heartbeat sent")
                
            except asyncio.CancelledError:
                break
            except Exception as e:
                logger.error(f"Heartbeat error: {str(e)}")
                
                # Try to reconnect if connection is lost
                if not self.connected:
                    logger.info("Attempting to reconnect...")
                    await self.connect()
                    
    async def message_receiver(self) -> None:
        """Receive and process messages from the mesh network"""
        while self.connected:
            try:
                message = await self.connection.recv()
                data = json.loads(message)
                
                # Process the message
                await self.process_message(data)
                
            except websockets.exceptions.ConnectionClosed:
                logger.warning("Connection to mesh network closed")
                self.connected = False
                break
            except Exception as e:
                logger.error(f"Error processing message: {str(e)}")
                
    async def process_message(self, data: Dict[str, Any]) -> None:
        """Process a received message"""
        message_type = data.get("type")
        
        if message_type == "heartbeat_ack":
            # Server acknowledged our heartbeat
            logger.debug("Heartbeat acknowledged")
            
        elif message_type == "peer_update":
            # Update about peer nodes
            if "added" in data:
                for peer_data in data["added"]:
                    self.add_peer(
                        peer_data["node_id"],
                        peer_data.get("metadata", {})
                    )
                logger.info(f"Added {len(data['added'])} new peers")
                
            if "removed" in data:
                for peer_id in data["removed"]:
                    self.remove_peer(peer_id)
                logger.info(f"Removed {len(data['removed'])} peers")
                
        elif message_type == "message":
            # Direct message from another node
            source_id = data.get("source_id")
            content = data.get("content", {})
            logger.info(f"Received message from {source_id}")
            
            # Verify signature if present
            if "signature" in data and source_id in self.peers:
                # Get peer's public key
                peer_public_key = self.peers[source_id].get("public_key")
                if peer_public_key:
                    # TODO: Implement signature verification
                    pass
                    
            # Handle message content based on its type
            content_type = content.get("type")
            
            if content_type in self.message_handlers:
                # Call the registered handler for this message type
                await self.message_handlers[content_type](content)
            else:
                logger.debug(f"No handler for message type: {content_type}")
                
        elif message_type == "deployment":
            # Deployment request or update
            deployment_id = data.get("deployment_id")
            status = data.get("status")
            agent_id = data.get("agent_id")
            
            logger.info(f"Deployment {deployment_id} for agent {agent_id}: {status}")
            
            # If there's a registered handler for deployments, call it
            if "deployment" in self.message_handlers:
                await self.message_handlers["deployment"](data)
                
        elif message_type == "error":
            # Error message from server
            error_msg = data.get("message", "Unknown error")
            logger.error(f"Error from server: {error_msg}")
            
        else:
            logger.debug(f"Unhandled message type: {message_type}")
            
    async def send_message(self, data: Dict[str, Any]) -> None:
        """Send a message to the mesh network"""
        if not self.connected:
            logger.warning("Not connected to mesh network")
            return
            
        try:
            if "type" in data and data["type"] not in ["register", "heartbeat"]:
                # Sign non-system messages
                data_str = json.dumps(data, sort_keys=True)
                signature = self.private_key.sign(
                    data_str.encode('utf-8'),
                    padding.PSS(
                        mgf=padding.MGF1(hashes.SHA256()),
                        salt_length=padding.PSS.MAX_LENGTH
                    ),
                    hashes.SHA256()
                )
                
                # Add signature to message
                data["signature"] = signature.hex()
            
            # Send the message
            await self.connection.send(json.dumps(data))
            
        except Exception as e:
            logger.error(f"Failed to send message: {str(e)}")
            
    def register_handler(self, message_type: str, handler: Callable) -> None:
        """Register a handler for a specific message type"""
        self.message_handlers[message_type] = handler
        logger.debug(f"Registered handler for message type: {message_type}")
        
    async def send_to_peer(self, peer_id: str, content: Dict[str, Any]) -> bool:
        """Send a message to a specific peer"""
        if peer_id not in self.peers:
            logger.warning(f"Unknown peer: {peer_id}")
            return False
            
        message = {
            "type": "message",
            "source_id": self.node_id,
            "target_id": peer_id,
            "content": content,
            "timestamp": time.time()
        }
        
        await self.send_message(message)
        return True
        
    async def broadcast(self, content: Dict[str, Any]) -> None:
        """Broadcast a message to all peers"""
        message = {
            "type": "broadcast",
            "source_id": self.node_id,
            "content": content,
            "timestamp": time.time()
        }
        
        await self.send_message(message)
        
    async def query_mesh(self, query_type: str, params: Dict[str, Any] = None) -> Dict[str, Any]:
        """Query information from the mesh network"""
        if not self.connected:
            logger.warning("Not connected to mesh network")
            return {"error": "Not connected to mesh network"}
            
        query_id = str(uuid.uuid4())
        query = {
            "type": "query",
            "query_id": query_id,
            "query_type": query_type,
            "params": params or {}
        }
        
        # Create a future for the query response
        response_future = asyncio.get_event_loop().create_future()
        
        # Register a one-time handler for this query response
        async def handle_query_response(data):
            if data.get("query_id") == query_id:
                response_future.set_result(data)
                
        self.register_handler(f"query_response_{query_id}", handle_query_response)
        
        # Send the query
        await self.send_message(query)
        
        try:
            # Wait for the response with timeout
            response = await asyncio.wait_for(response_future, timeout=30)
            return response
        except asyncio.TimeoutError:
            logger.error(f"Query {query_type} timed out")
            return {"error": "Query timed out"}
        finally:
            # Clean up the temporary handler
            if f"query_response_{query_id}" in self.message_handlers:
                del self.message_handlers[f"query_response_{query_id}"]
                
    async def deploy_agent(self, agent_config: Dict[str, Any]) -> Dict[str, Any]:
        """Request to deploy an agent to the mesh network"""
        if not self.connected:
            logger.warning("Not connected to mesh network")
            return {"error": "Not connected to mesh network"}
            
        agent_id = agent_config.get("id") or agent_config.get("name")
        if not agent_id:
            return {"error": "Missing agent ID or name"}
            
        deployment_request = {
            "type": "deployment_request",
            "requester_id": self.node_id,
            "agent_id": agent_id,
            "config": agent_config,
            "params": {
                "priority": "normal",
                "timestamp": time.time()
            }
        }
        
        logger.info(f"Requesting deployment of agent {agent_id}")
        
        # Create a future for the deployment acknowledgment
        deployment_future = asyncio.get_event_loop().create_future()
        
        # Register a handler for deployment acknowledgment
        async def handle_deployment_ack(data):
            if data.get("type") == "deployment_ack" and data.get("agent_id") == agent_id:
                deployment_future.set_result(data)
                
        self.register_handler("deployment_ack", handle_deployment_ack)
        
        # Send the deployment request
        await self.send_message(deployment_request)
        
        try:
            # Wait for the deployment acknowledgment
            response = await asyncio.wait_for(deployment_future, timeout=30)
            return response
        except asyncio.TimeoutError:
            logger.error("Deployment request timed out")
            return {"error": "Deployment request timed out"}
            
    def set_capability(self, capability: str, enabled: bool = True) -> None:
        """Set a node capability"""
        capabilities = self.metadata.get("capabilities", [])
        
        if enabled and capability not in capabilities:
            capabilities.append(capability)
        elif not enabled and capability in capabilities:
            capabilities.remove(capability)
            
        self.metadata["capabilities"] = capabilities
        logger.debug(f"Capabilities updated: {capabilities}")
        
    def set_node_type(self, node_type: str) -> None:
        """Set the node type"""
        self.metadata["type"] = node_type
        logger.debug(f"Node type set to: {node_type}")

async def demo():
    """Simple demo of the WebSocket mesh client"""
    # Create and connect a mesh client
    client = WebSocketMeshClient(
        node_id="demo-client",
        mesh_url="ws://localhost:8765"
    )
    
    # Set node type and capabilities
    client.set_node_type("agent")
    client.set_capability("compute")
    client.set_capability("storage")
    
    # Register a message handler
    async def handle_message(data):
        print(f"Received message: {data}")
        
    client.register_handler("message", handle_message)
    
    # Connect to the mesh network
    connected = await client.connect()
    if not connected:
        print("Failed to connect to mesh network")
        return
        
    print("Connected to mesh network")
    
    # Query the mesh network
    mesh_info = await client.query_mesh("status")
    print(f"Mesh network status: {mesh_info}")
    
    # Keep the connection alive for a while
    try:
        for i in range(5):
            await asyncio.sleep(5)
            print(f"Still connected after {(i+1)*5} seconds")
    finally:
        # Disconnect
        await client.disconnect()
        print("Disconnected from mesh network")

if __name__ == "__main__":
    asyncio.run(demo())
