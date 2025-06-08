#!/usr/bin/env python3
"""
Cloud Connector for MCP-ZERO
Bridges local agents with cloud resources in the mesh network
"""
import asyncio
import json
import logging
import os
import ssl
import time
from typing import Dict, List, Optional, Any

import websockets

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('cloud_connector')

class CloudConnector:
    """Connects local MCP-ZERO agents to cloud resources"""
    
    def __init__(self, 
                 connector_id: Optional[str] = None,
                 mesh_url: str = "ws://localhost:8765",
                 api_key: Optional[str] = None,
                 use_ssl: bool = True):
        """Initialize the cloud connector with configuration"""
        self.connector_id = connector_id or f"connector-{int(time.time())}"
        self.mesh_url = mesh_url
        self.api_key = api_key or os.environ.get("MCP_CLOUD_API_KEY", "")
        self.use_ssl = use_ssl
        
        self.websocket = None
        self.connected = False
        self.heartbeat_interval = 30  # seconds
        self.reconnect_attempts = 0
        self.max_reconnect_attempts = 5
        
        # Cloud services catalog - available cloud resources
        self.services_catalog = {
            "storage": {
                "available": True,
                "quota": 10737418240,  # 10 GB in bytes
                "used": 0
            },
            "compute": {
                "available": True,
                "max_instances": 5,
                "active_instances": 0
            },
            "network": {
                "available": True,
                "bandwidth_limit": 100000000,  # 100 Mbps
                "current_usage": 0
            }
        }
        
        logger.info(f"Cloud connector initialized with ID: {self.connector_id}")
        
    async def connect(self) -> bool:
        """Connect to the mesh network"""
        try:
            # Create SSL context if needed
            ssl_context = None
            if self.use_ssl and self.mesh_url.startswith("wss://"):
                ssl_context = ssl.create_default_context()
            
            # Connect to the mesh WebSocket server
            logger.info(f"Connecting to mesh network at {self.mesh_url}")
            self.websocket = await websockets.connect(
                self.mesh_url, 
                ssl=ssl_context
            )
            
            # Send registration message
            await self.websocket.send(json.dumps({
                "type": "register",
                "connector_id": self.connector_id,
                "connector_type": "cloud",
                "api_key": self.api_key,
                "services": list(self.services_catalog.keys()),
                "timestamp": int(time.time())
            }))
            
            # Wait for registration acknowledgment
            response = await self.websocket.recv()
            data = json.loads(response)
            
            if data.get("type") == "register_ack" and data.get("status") == "success":
                self.connected = True
                self.reconnect_attempts = 0
                logger.info(f"Successfully connected to mesh network as {self.connector_id}")
                
                # Start heartbeat
                asyncio.create_task(self._heartbeat_loop())
                return True
            else:
                logger.error(f"Registration failed: {data.get('message', 'Unknown error')}")
                return False
                
        except Exception as e:
            logger.error(f"Failed to connect to mesh network: {str(e)}")
            return False
            
    async def disconnect(self) -> None:
        """Disconnect from the mesh network"""
        if self.websocket and self.connected:
            try:
                await self.websocket.send(json.dumps({
                    "type": "unregister",
                    "connector_id": self.connector_id,
                    "timestamp": int(time.time())
                }))
                await self.websocket.close()
                logger.info(f"Disconnected from mesh network")
            except Exception as e:
                logger.warning(f"Error during disconnect: {str(e)}")
            finally:
                self.connected = False
                self.websocket = None
                
    async def _heartbeat_loop(self) -> None:
        """Send periodic heartbeats to maintain connection"""
        while self.connected:
            try:
                await asyncio.sleep(self.heartbeat_interval)
                
                if self.websocket and self.connected:
                    await self.websocket.send(json.dumps({
                        "type": "heartbeat",
                        "connector_id": self.connector_id,
                        "timestamp": int(time.time()),
                        "status": "active"
                    }))
                    logger.debug(f"Sent heartbeat at {time.time()}")
            except Exception as e:
                logger.warning(f"Heartbeat failed: {str(e)}")
                await self._attempt_reconnect()
                
    async def _attempt_reconnect(self) -> None:
        """Attempt to reconnect to the mesh network"""
        if self.reconnect_attempts >= self.max_reconnect_attempts:
            logger.error("Maximum reconnection attempts reached. Giving up.")
            return
            
        self.reconnect_attempts += 1
        backoff = 2 ** self.reconnect_attempts  # Exponential backoff
        
        logger.info(f"Connection lost. Attempting reconnect in {backoff} seconds (attempt {self.reconnect_attempts})")
        await asyncio.sleep(backoff)
        
        success = await self.connect()
        if not success:
            await self._attempt_reconnect()
            
    async def request_cloud_resource(self, 
                                    resource_type: str, 
                                    params: Dict[str, Any]) -> Dict[str, Any]:
        """Request a cloud resource through the mesh network"""
        if not self.connected or not self.websocket:
            return {
                "status": "error",
                "message": "Not connected to mesh network",
                "resource_type": resource_type
            }
        
        # Check if the requested resource is available
        if resource_type not in self.services_catalog:
            return {
                "status": "error",
                "message": f"Resource type '{resource_type}' not available",
                "resource_type": resource_type
            }
            
        # Prepare the resource request
        request = {
            "type": "resource_request",
            "connector_id": self.connector_id,
            "resource_type": resource_type,
            "parameters": params,
            "timestamp": int(time.time())
        }
        
        try:
            # Send the request
            await self.websocket.send(json.dumps(request))
            
            # Wait for response
            response = await self.websocket.recv()
            data = json.loads(response)
            
            logger.info(f"Resource request response for {resource_type}: {data.get('status', 'unknown')}")
            return data
            
        except Exception as e:
            logger.error(f"Error requesting cloud resource: {str(e)}")
            return {
                "status": "error",
                "message": f"Request failed: {str(e)}",
                "resource_type": resource_type
            }
            
    async def deploy_agent_to_cloud(self, agent_id: str, config: Dict[str, Any]) -> Dict[str, Any]:
        """Deploy an agent to the cloud infrastructure"""
        return await self.request_cloud_resource("compute", {
            "action": "deploy_agent",
            "agent_id": agent_id,
            "config": config
        })
        
    async def store_data(self, key: str, data: Any) -> Dict[str, Any]:
        """Store data in cloud storage"""
        return await self.request_cloud_resource("storage", {
            "action": "store",
            "key": key,
            "data": data
        })
        
    async def retrieve_data(self, key: str) -> Dict[str, Any]:
        """Retrieve data from cloud storage"""
        return await self.request_cloud_resource("storage", {
            "action": "retrieve",
            "key": key
        })
