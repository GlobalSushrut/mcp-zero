#!/usr/bin/env python3
"""
MCP-ZERO Mesh Network Resource Directory
Manages resources available in the mesh network
"""
import json
import logging
from datetime import datetime, timedelta
from typing import Dict, List, Any, Optional, Set

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('resource_directory')

class ResourceDirectory:
    """
    Manages and indexes resources in the mesh network
    """
    
    def __init__(self, node_id: str):
        """
        Initialize the resource directory
        
        Args:
            node_id: ID of the local node
        """
        self.node_id = node_id
        self.local_resources: Dict[str, Dict[str, Any]] = {}  # resource_id -> resource info
        self.remote_resources: Dict[str, Dict[str, Any]] = {}  # resource_id -> resource info with peer info
        self.resource_types: Set[str] = set()  # Set of known resource types
        
    def add_local_resource(self, resource_id: str, resource_type: str, metadata: Dict[str, Any]) -> bool:
        """
        Add a local resource to the directory
        
        Args:
            resource_id: Unique ID for the resource
            resource_type: Type of resource
            metadata: Resource metadata
            
        Returns:
            True if added, False if already exists
        """
        if resource_id in self.local_resources:
            # Update existing resource
            self.local_resources[resource_id].update({
                'type': resource_type,
                'metadata': metadata,
                'updated_at': datetime.utcnow().isoformat()
            })
            logger.info(f"Updated local resource {resource_id}")
            return False
        
        # Add new resource
        self.local_resources[resource_id] = {
            'type': resource_type,
            'metadata': metadata,
            'registered_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        self.resource_types.add(resource_type)
        logger.info(f"Added local resource {resource_id} of type {resource_type}")
        return True
        
    def add_remote_resource(self, resource_id: str, resource_type: str, metadata: Dict[str, Any], peer_id: str) -> bool:
        """
        Add a remote resource to the directory
        
        Args:
            resource_id: Unique ID for the resource
            resource_type: Type of resource
            metadata: Resource metadata
            peer_id: ID of the peer that has this resource
            
        Returns:
            True if added, False if already exists
        """
        if resource_id in self.remote_resources:
            # Update existing resource
            self.remote_resources[resource_id].update({
                'type': resource_type,
                'metadata': metadata,
                'peer_id': peer_id,
                'updated_at': datetime.utcnow().isoformat()
            })
            logger.info(f"Updated remote resource {resource_id} from peer {peer_id}")
            return False
        
        # Add new resource
        self.remote_resources[resource_id] = {
            'type': resource_type,
            'metadata': metadata,
            'peer_id': peer_id,
            'discovered_at': datetime.utcnow().isoformat(),
            'updated_at': datetime.utcnow().isoformat()
        }
        self.resource_types.add(resource_type)
        logger.info(f"Added remote resource {resource_id} of type {resource_type} from peer {peer_id}")
        return True
        
    def remove_local_resource(self, resource_id: str) -> bool:
        """
        Remove a local resource from the directory
        
        Args:
            resource_id: ID of the resource to remove
            
        Returns:
            True if removed, False if not found
        """
        if resource_id in self.local_resources:
            resource_type = self.local_resources[resource_id]['type']
            del self.local_resources[resource_id]
            logger.info(f"Removed local resource {resource_id}")
            
            # Update resource types
            self._update_resource_types()
            return True
        return False
        
    def remove_remote_resource(self, resource_id: str) -> bool:
        """
        Remove a remote resource from the directory
        
        Args:
            resource_id: ID of the resource to remove
            
        Returns:
            True if removed, False if not found
        """
        if resource_id in self.remote_resources:
            resource_type = self.remote_resources[resource_id]['type']
            del self.remote_resources[resource_id]
            logger.info(f"Removed remote resource {resource_id}")
            
            # Update resource types
            self._update_resource_types()
            return True
        return False
        
    def remove_peer_resources(self, peer_id: str) -> int:
        """
        Remove all resources from a specific peer
        
        Args:
            peer_id: ID of the peer
            
        Returns:
            Number of resources removed
        """
        count = 0
        for resource_id, info in list(self.remote_resources.items()):
            if info.get('peer_id') == peer_id:
                del self.remote_resources[resource_id]
                count += 1
                
        if count > 0:
            logger.info(f"Removed {count} resources from peer {peer_id}")
            self._update_resource_types()
            
        return count
        
    def query_resources(self, resource_type: str = None, metadata_filter: Dict[str, Any] = None,
                         include_local: bool = True, include_remote: bool = True) -> Dict[str, Dict[str, Any]]:
        """
        Query resources by type and metadata
        
        Args:
            resource_type: Type of resources to query (optional)
            metadata_filter: Filter by metadata key-value pairs (optional)
            include_local: Include local resources
            include_remote: Include remote resources
            
        Returns:
            Dictionary of matching resource IDs to resource info
        """
        results = {}
        
        # Check local resources
        if include_local:
            for res_id, res_info in self.local_resources.items():
                if self._match_resource(res_info, resource_type, metadata_filter):
                    results[res_id] = {**res_info, 'location': 'local'}
                    
        # Check remote resources
        if include_remote:
            for res_id, res_info in self.remote_resources.items():
                if self._match_resource(res_info, resource_type, metadata_filter):
                    results[res_id] = {**res_info, 'location': 'remote'}
                    
        return results
        
    def get_resource_types(self) -> List[str]:
        """
        Get all known resource types
        
        Returns:
            List of resource types
        """
        return list(self.resource_types)
        
    def serialize(self) -> Dict[str, Any]:
        """
        Serialize the directory for transmission
        
        Returns:
            Dictionary representation of the directory
        """
        return {
            'local_resources': self.local_resources,
            'remote_resources': self.remote_resources,
            'resource_types': list(self.resource_types)
        }
        
    def _update_resource_types(self):
        """Update the set of resource types"""
        types = set()
        
        for res_info in self.local_resources.values():
            if 'type' in res_info:
                types.add(res_info['type'])
                
        for res_info in self.remote_resources.values():
            if 'type' in res_info:
                types.add(res_info['type'])
                
        self.resource_types = types
        
    @staticmethod
    def _match_resource(res_info: Dict[str, Any], resource_type: Optional[str], 
                        metadata_filter: Optional[Dict[str, Any]]) -> bool:
        """
        Check if a resource matches the query criteria
        
        Args:
            res_info: Resource information
            resource_type: Type to match (optional)
            metadata_filter: Metadata filter (optional)
            
        Returns:
            True if the resource matches, False otherwise
        """
        # Check resource type
        if resource_type and res_info.get('type') != resource_type:
            return False
            
        # Check metadata filter
        if metadata_filter:
            res_metadata = res_info.get('metadata', {})
            for key, value in metadata_filter.items():
                if key not in res_metadata or res_metadata[key] != value:
                    return False
                    
        return True
