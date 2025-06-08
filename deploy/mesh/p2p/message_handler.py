#!/usr/bin/env python3
"""
MCP-ZERO Mesh Network Message Handler
Handles and processes P2P mesh network messages
"""
import json
import logging
from datetime import datetime
from typing import Dict, Any

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('mesh_message_handler')

class MessageHandler:
    """
    Handler for mesh network messages
    """
    
    @staticmethod
    async def handle_discovery(node, message: Dict[str, Any], ws_conn=None):
        """
        Handle peer discovery messages
        
        Args:
            node: The MeshNode instance
            message: The discovery message
            ws_conn: WebSocket connection from the peer (if available)
        """
        sender_id = message.get('sender_id')
        data = message.get('data', {})
        
        if not sender_id or sender_id == node.node_id:
            return
            
        # Add or update peer information
        node.peers[sender_id] = {
            'ws_conn': ws_conn,
            'address': data.get('address'),
            'node_type': data.get('node_type', 'unknown'),
            'resources': data.get('resources', []),
            'last_seen': datetime.utcnow().isoformat()
        }
        
        # Send back our own discovery response if this is a new peer
        if ws_conn and not ws_conn.closed:
            await ws_conn.send(json.dumps({
                'type': 'discovery_response',
                'sender_id': node.node_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'node_type': 'full',
                    'address': f"ws://{node.host}:{node.port}",
                    'resources': list(node.resources.keys()),
                    'peers': [p for p in node.peers.keys() if p != sender_id]
                }
            }))
            
        logger.info(f"Discovered peer {sender_id} at {data.get('address')}")

    @staticmethod
    async def handle_resource_query(node, message: Dict[str, Any], ws_conn=None):
        """
        Handle resource query messages
        
        Args:
            node: The MeshNode instance
            message: The resource query message
            ws_conn: WebSocket connection from the peer (if available)
        """
        sender_id = message.get('sender_id')
        data = message.get('data', {})
        query = data.get('query', {})
        
        if not sender_id or sender_id == node.node_id:
            return
            
        # Process the resource query
        resource_type = query.get('type')
        results = {}
        
        for res_id, res_info in node.resources.items():
            if not resource_type or res_info.get('type') == resource_type:
                if query.get('filter') and not MessageHandler._match_filter(res_info, query['filter']):
                    continue
                results[res_id] = res_info
                
        # Send response if we have a connection
        if ws_conn and not ws_conn.closed:
            await ws_conn.send(json.dumps({
                'type': 'resource_query_response',
                'sender_id': node.node_id,
                'timestamp': datetime.utcnow().isoformat(),
                'data': {
                    'query_id': data.get('query_id'),
                    'results': results
                }
            }))
            
        logger.info(f"Processed resource query from {sender_id}")
    
    @staticmethod
    async def handle_resource_announcement(node, message: Dict[str, Any], ws_conn=None):
        """
        Handle resource announcement messages
        
        Args:
            node: The MeshNode instance
            message: The resource announcement message
            ws_conn: WebSocket connection from the peer (if available)
        """
        sender_id = message.get('sender_id')
        data = message.get('data', {})
        
        if not sender_id or sender_id == node.node_id:
            return
            
        # Add the resource to our directory with peer information
        resource_id = data.get('resource_id')
        if resource_id:
            node.remote_resources[resource_id] = {
                'type': data.get('resource_type'),
                'metadata': data.get('metadata', {}),
                'peer_id': sender_id,
                'announced_at': datetime.utcnow().isoformat()
            }
            
            logger.info(f"Added remote resource {resource_id} from peer {sender_id}")
    
    @staticmethod
    def _match_filter(resource_info: Dict[str, Any], filter_criteria: Dict[str, Any]) -> bool:
        """
        Check if a resource matches filter criteria
        
        Args:
            resource_info: Resource information
            filter_criteria: Filter criteria
            
        Returns:
            True if the resource matches the criteria, False otherwise
        """
        for key, value in filter_criteria.items():
            if key == 'metadata':
                for m_key, m_value in value.items():
                    if m_key not in resource_info.get('metadata', {}) or resource_info['metadata'][m_key] != m_value:
                        return False
            elif key not in resource_info or resource_info[key] != value:
                return False
                
        return True
