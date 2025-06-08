#!/usr/bin/env python3
"""
MCP-ZERO Mesh Bridge
Connects the P2P mesh network with MCP-ZERO core infrastructure
"""
import asyncio
import json
import logging
import os
import sys
import uuid
from typing import Dict, List, Any, Optional

# Add project root to path for imports
sys.path.append(os.path.join(os.path.dirname(__file__), "../../../"))

# Import mesh network components
from deploy.mesh.p2p.mesh_network import MeshNetwork

# Import MCP-ZERO SDK adapter
try:
    from src.sdk.python.mcp_zero.http_adapter import HttpAdapter
    SDK_AVAILABLE = True
except ImportError:
    SDK_AVAILABLE = False

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('mesh_bridge')

class MeshBridge:
    """
    Connects the P2P mesh network with MCP-ZERO core infrastructure
    
    Provides bidirectional communication between the mesh network and
    the immutable core MCP-ZERO infrastructure.
    """
    
    def __init__(self, mesh_network: MeshNetwork):
        """
        Initialize the mesh bridge
        
        Args:
            mesh_network: MeshNetwork instance to bridge
        """
        self.mesh_network = mesh_network
        self.adapter = None
        self.connected_agents = {}  # agent_id -> agent_info
        
        if SDK_AVAILABLE:
            self.adapter = HttpAdapter()
            logger.info("MCP-ZERO SDK adapter initialized")
        else:
            logger.warning("MCP-ZERO SDK not available, core integration disabled")
            
        # Subscribe to mesh events
        self.mesh_network.subscribe_to_event('agent_announced', self._handle_agent_announced)
        self.mesh_network.subscribe_to_event('resource_query', self._handle_resource_query)
        
    async def connect(self):
        """Connect the bridge to MCP-ZERO core"""
        if not self.adapter:
            logger.error("Cannot connect: MCP-ZERO SDK not available")
            return False
            
        try:
            # Verify connectivity
            version = await self.adapter.get_version()
            logger.info(f"Connected to MCP-ZERO core version {version}")
            
            # Subscribe to agent events
            # Note: In a real implementation, we would register callbacks
            # for agent lifecycle events through the adapter
            
            return True
        except Exception as e:
            logger.error(f"Failed to connect to MCP-ZERO core: {str(e)}")
            return False
            
    async def bridge_agent(self, agent_id: str, capabilities: List[str], 
                          constraints: Dict[str, Any]) -> Optional[str]:
        """
        Bridge an MCP-ZERO agent to the mesh network
        
        Args:
            agent_id: Agent ID or None to create new
            capabilities: List of agent capabilities
            constraints: Hardware constraints
            
        Returns:
            Agent ID if successful, None otherwise
        """
        if not self.adapter:
            logger.error("Cannot bridge agent: MCP-ZERO SDK not available")
            return None
            
        try:
            # If no agent_id provided, spawn a new agent
            if not agent_id:
                # Convert constraints to HardwareConstraints format
                hw_constraints = {
                    "cpu_limit": constraints.get("cpu", 0.1),
                    "memory_limit": constraints.get("memory", 256)
                }
                
                # Spawn agent through MCP-ZERO core
                logger.info(f"Spawning new agent with capabilities: {capabilities}")
                agent_id = await self.adapter.spawn_agent(hw_constraints)
                
                # Attach plugins for each capability
                for capability in capabilities:
                    try:
                        await self.adapter.attach_plugin(agent_id, capability)
                    except Exception as e:
                        logger.error(f"Failed to attach plugin {capability}: {str(e)}")
                        
                logger.info(f"Created new agent: {agent_id}")
            
            # Register agent with mesh network
            await self.mesh_network.register_agent_resource(
                agent_id=agent_id,
                capabilities=capabilities,
                constraints=constraints
            )
            
            # Store agent info
            self.connected_agents[agent_id] = {
                "capabilities": capabilities,
                "constraints": constraints,
                "status": "active"
            }
            
            return agent_id
        except Exception as e:
            logger.error(f"Failed to bridge agent: {str(e)}")
            return None
            
    async def execute_remote_agent(self, agent_id: str, method: str, 
                                 params: Dict[str, Any]) -> Optional[Any]:
        """
        Execute a method on a remote agent discovered via mesh
        
        Args:
            agent_id: Agent ID
            method: Method to execute
            params: Method parameters
            
        Returns:
            Execution result if successful, None otherwise
        """
        if not self.adapter:
            logger.error("Cannot execute remote agent: MCP-ZERO SDK not available")
            return None
        
        # Check if agent is local
        if agent_id in self.connected_agents:
            # Execute locally via adapter
            try:
                result = await self.adapter.execute(agent_id, method, params)
                return result
            except Exception as e:
                logger.error(f"Failed to execute local agent {agent_id}: {str(e)}")
                return None
        
        # Query mesh network for agent
        resources = await self.mesh_network.query_resources(
            resource_type="agent",
            metadata_filter={"resource_id": agent_id}
        )
        
        if agent_id not in resources:
            logger.error(f"Agent {agent_id} not found in mesh network")
            return None
            
        # Get peer information
        agent_info = resources[agent_id]
        peer_id = agent_info.get("peer_id")
        
        if not peer_id:
            logger.error(f"No peer information for agent {agent_id}")
            return None
            
        # Send execution request to peer
        logger.info(f"Sending execution request for agent {agent_id} to peer {peer_id}")
        
        # Create execution request message
        execution_request = {
            "type": "agent_execute",
            "sender_id": self.mesh_network.node_id,
            "timestamp": self._get_timestamp(),
            "data": {
                "request_id": str(uuid.uuid4()),
                "agent_id": agent_id,
                "method": method,
                "params": params
            }
        }
        
        # Send via mesh network
        # In a real implementation, we would wait for the response from the peer
        # Here we're just demonstrating the pattern
        await self.mesh_network.node._broadcast_message(execution_request)
        
        # For now, return a placeholder
        return {
            "status": "request_sent",
            "request_id": execution_request["data"]["request_id"]
        }
            
    async def _handle_agent_announced(self, data: Dict[str, Any]):
        """Handle agent announcement events from the mesh"""
        agent_id = data.get("agent_id")
        if not agent_id:
            return
            
        logger.info(f"Agent {agent_id} announced in mesh network")
        
        # In a real implementation, we might verify the agent
        # and potentially add it to our local registry
        
    async def _handle_resource_query(self, data: Dict[str, Any]):
        """Handle resource query events from the mesh"""
        query = data.get("query", {})
        if not query:
            return
            
        # If someone is querying for agents and we have the adapter,
        # we could list our local agents and add them to the response
        
    def _get_timestamp(self) -> str:
        """Get current timestamp in ISO format"""
        from datetime import datetime
        return datetime.utcnow().isoformat()
