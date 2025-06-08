#!/usr/bin/env python3
"""
MCP-ZERO Mesh Deployment Controller
Handles deployment of agents across the mesh network
"""
import asyncio
import json
import logging
import os
import signal
import sys
import time
import uuid
from typing import Dict, List, Optional, Any, Set

import websockets

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from deploy.mesh.zksync_verifier import ZKSyncVerifier

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('deploy_controller')

class DeployController:
    """Controls deployment of agents across the mesh network"""
    
    def __init__(self,
                controller_id: Optional[str] = None,
                host: str = "0.0.0.0",
                port: int = 8766,
                max_concurrent: int = 5):
        """Initialize the deployment controller"""
        self.controller_id = controller_id or f"deploy-{str(uuid.uuid4())[:8]}"
        self.host = host
        self.port = port
        self.max_concurrent = max_concurrent
        
        self.active_deployments = {}
        self.deployment_queue = []
        self.connected_nodes = set()
        self.server = None
        self.running = False
        
        # Initialize ZKSync verifier
        self.verifier = ZKSyncVerifier()
        
        logger.info(f"Deployment controller initialized with ID: {self.controller_id}")
        
    async def start(self) -> None:
        """Start the deployment controller WebSocket server"""
        self.running = True
        
        # Start WebSocket server
        logger.info(f"Starting deployment controller on {self.host}:{self.port}")
        self.server = await websockets.serve(
            self.handle_connection, self.host, self.port
        )
        
        # Start deployment processor
        asyncio.create_task(self.process_deployment_queue())
        
        # Register signal handlers for graceful shutdown
        for sig in (signal.SIGINT, signal.SIGTERM):
            asyncio.get_event_loop().add_signal_handler(sig, lambda: asyncio.create_task(self.stop()))
        
    async def stop(self) -> None:
        """Stop the deployment controller"""
        logger.info("Stopping deployment controller...")
        self.running = False
        
        # Cancel active deployments
        for deployment_id, deployment in list(self.active_deployments.items()):
            await self.cancel_deployment(deployment_id, "Controller shutdown")
            
        # Close WebSocket server
        if self.server:
            self.server.close()
            await self.server.wait_closed()
            
        logger.info("Deployment controller stopped")
        
    async def handle_connection(self, websocket, path) -> None:
        """Handle incoming WebSocket connections"""
        node_id = None
        try:
            # Perform handshake
            async for message in websocket:
                try:
                    data = json.loads(message)
                    if data.get("type") == "register":
                        # Handle node registration
                        node_id = data.get("node_id")
                        node_type = data.get("node_type", "unknown")
                        
                        if not node_id:
                            await self.send_message(websocket, {
                                "type": "error",
                                "message": "Missing node_id in registration"
                            })
                            continue
                            
                        # Add to connected nodes
                        self.connected_nodes.add(node_id)
                        logger.info(f"Node {node_id} ({node_type}) connected")
                        
                        # Send acknowledgement
                        await self.send_message(websocket, {
                            "type": "register_ack",
                            "controller_id": self.controller_id,
                            "status": "success"
                        })
                    elif data.get("type") == "deployment_request":
                        # Handle deployment request
                        await self.handle_deployment_request(websocket, data)
                    elif data.get("type") == "deployment_status":
                        # Handle deployment status update
                        await self.handle_deployment_status(websocket, data)
                    else:
                        await self.send_message(websocket, {
                            "type": "error",
                            "message": f"Unknown message type: {data.get('type')}"
                        })
                except json.JSONDecodeError:
                    await self.send_message(websocket, {
                        "type": "error",
                        "message": "Invalid JSON format"
                    })
        finally:
            # Clean up on disconnect
            if node_id and node_id in self.connected_nodes:
                self.connected_nodes.remove(node_id)
                logger.info(f"Node {node_id} disconnected")
                
    async def handle_deployment_request(self, websocket, data: Dict[str, Any]) -> None:
        """Handle a request to deploy an agent"""
        agent_id = data.get("agent_id")
        agent_config = data.get("config", {})
        deployment_params = data.get("params", {})
        requester_id = data.get("requester_id")
        
        if not agent_id or not agent_config:
            await self.send_message(websocket, {
                "type": "error",
                "message": "Missing required fields in deployment request"
            })
            return
            
        # Create a deployment ID
        deployment_id = str(uuid.uuid4())
        
        # Create signed deployment record
        deployment_record = self.verifier.sign_deployment(agent_id, agent_config)
        
        # Create deployment object
        deployment = {
            "id": deployment_id,
            "agent_id": agent_id,
            "config": agent_config,
            "params": deployment_params,
            "requester_id": requester_id,
            "status": "queued",
            "created_at": time.time(),
            "updated_at": time.time(),
            "deployment_record": deployment_record
        }
        
        # Add to queue
        self.deployment_queue.append(deployment)
        logger.info(f"Deployment request for agent {agent_id} queued with ID {deployment_id}")
        
        # Send acknowledgement
        await self.send_message(websocket, {
            "type": "deployment_ack",
            "deployment_id": deployment_id,
            "status": "queued",
            "position": len(self.deployment_queue)
        })
        
    async def handle_deployment_status(self, websocket, data: Dict[str, Any]) -> None:
        """Handle a deployment status update"""
        deployment_id = data.get("deployment_id")
        status = data.get("status")
        message = data.get("message", "")
        
        if not deployment_id or not status:
            await self.send_message(websocket, {
                "type": "error",
                "message": "Missing required fields in status update"
            })
            return
            
        if deployment_id not in self.active_deployments:
            await self.send_message(websocket, {
                "type": "error",
                "message": f"Unknown deployment ID: {deployment_id}"
            })
            return
            
        # Update deployment status
        self.active_deployments[deployment_id]["status"] = status
        self.active_deployments[deployment_id]["updated_at"] = time.time()
        
        if status == "completed" or status == "failed":
            # Deployment is finished
            logger.info(f"Deployment {deployment_id} {status}: {message}")
            
            # Remove from active deployments
            deployment = self.active_deployments.pop(deployment_id)
            
            # Log the completion details
            log_path = os.path.join("logs", "deployments", f"{deployment_id}.json")
            os.makedirs(os.path.dirname(log_path), exist_ok=True)
            
            with open(log_path, "w") as f:
                json.dump(deployment, f, indent=2)
        else:
            # Still in progress
            logger.info(f"Deployment {deployment_id} status update: {status}")
            
        # Send acknowledgement
        await self.send_message(websocket, {
            "type": "status_ack",
            "deployment_id": deployment_id
        })
        
    async def process_deployment_queue(self) -> None:
        """Process the deployment queue"""
        while self.running:
            # Check if we can start more deployments
            while (len(self.active_deployments) < self.max_concurrent and
                   self.deployment_queue):
                # Get next deployment from the queue
                deployment = self.deployment_queue.pop(0)
                
                # Start deployment
                await self.start_deployment(deployment)
                
            # Wait before checking again
            await asyncio.sleep(1)
            
    async def start_deployment(self, deployment: Dict[str, Any]) -> None:
        """Start a deployment"""
        deployment_id = deployment["id"]
        agent_id = deployment["agent_id"]
        
        logger.info(f"Starting deployment {deployment_id} for agent {agent_id}")
        
        # Update status
        deployment["status"] = "in_progress"
        deployment["updated_at"] = time.time()
        
        # Add to active deployments
        self.active_deployments[deployment_id] = deployment
        
        # Create deployment process
        asyncio.create_task(self.execute_deployment(deployment_id))
        
    async def execute_deployment(self, deployment_id: str) -> None:
        """Execute a deployment"""
        if deployment_id not in self.active_deployments:
            logger.warning(f"Deployment {deployment_id} not found")
            return
            
        deployment = self.active_deployments[deployment_id]
        agent_id = deployment["agent_id"]
        
        try:
            # Simulate deployment steps
            logger.info(f"Deploying agent {agent_id} (deployment {deployment_id})...")
            
            # Step 1: Verify agent configuration
            await asyncio.sleep(1)
            logger.info(f"Step 1: Verifying agent configuration")
            
            # Step 2: Prepare deployment environment
            await asyncio.sleep(1)
            logger.info(f"Step 2: Preparing deployment environment")
            
            # Step 3: Deploy agent
            await asyncio.sleep(2)
            logger.info(f"Step 3: Deploying agent")
            
            # Step 4: Verify deployment
            await asyncio.sleep(1)
            logger.info(f"Step 4: Verifying deployment")
            
            # Mark deployment as completed
            deployment["status"] = "completed"
            deployment["updated_at"] = time.time()
            logger.info(f"Deployment {deployment_id} completed successfully")
            
        except Exception as e:
            # Handle deployment failure
            deployment["status"] = "failed"
            deployment["error"] = str(e)
            deployment["updated_at"] = time.time()
            logger.error(f"Deployment {deployment_id} failed: {e}")
        
    async def cancel_deployment(self, deployment_id: str, reason: str) -> bool:
        """Cancel an active deployment"""
        if deployment_id not in self.active_deployments:
            logger.warning(f"Cannot cancel deployment {deployment_id}: not found")
            return False
            
        deployment = self.active_deployments[deployment_id]
        deployment["status"] = "cancelled"
        deployment["cancellation_reason"] = reason
        deployment["updated_at"] = time.time()
        
        # Remove from active deployments
        self.active_deployments.pop(deployment_id)
        
        logger.info(f"Deployment {deployment_id} cancelled: {reason}")
        return True
        
    async def send_message(self, websocket, data: Dict[str, Any]) -> None:
        """Send a message through the WebSocket"""
        await websocket.send(json.dumps(data))
        
    def get_deployment_stats(self) -> Dict[str, Any]:
        """Get statistics about deployments"""
        return {
            "active_deployments": len(self.active_deployments),
            "queued_deployments": len(self.deployment_queue),
            "connected_nodes": len(self.connected_nodes),
            "total_capacity": self.max_concurrent
        }
        
async def main():
    """Main entry point for the deployment controller"""
    controller = DeployController()
    await controller.start()
    
    try:
        # Keep running until stopped
        while controller.running:
            await asyncio.sleep(60)
            stats = controller.get_deployment_stats()
            logger.info(f"Deployment stats: {stats}")
    except KeyboardInterrupt:
        pass
    finally:
        await controller.stop()
        
if __name__ == "__main__":
    asyncio.run(main())
