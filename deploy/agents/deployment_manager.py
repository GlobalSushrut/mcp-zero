#!/usr/bin/env python3
"""
MCP-ZERO Deployment Manager
Handles agent deployment, execution, and lifecycle management
"""
import json
import logging
import os
import uuid
from datetime import datetime
from typing import Dict, List, Any, Optional

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('deployment_manager')

class DeploymentManager:
    """
    Manager for agent deployments
    Handles deployment, execution monitoring, and resource allocation
    """
    
    def __init__(self, storage_path: str = "deploy/agents/storage"):
        """
        Initialize the deployment manager
        
        Args:
            storage_path: Path to agent storage directory
        """
        self.storage_path = storage_path
        self.deployments = {}
        
        # Ensure storage directory exists
        os.makedirs(storage_path, exist_ok=True)
        
        # Load existing deployments
        self._load_deployments()
        
        logger.info(f"Deployment Manager initialized with storage path: {storage_path}")
        
    def _load_deployments(self):
        """Load existing deployments from storage"""
        try:
            index_path = os.path.join(self.storage_path, "deployments.json")
            if os.path.exists(index_path):
                with open(index_path, 'r') as f:
                    self.deployments = json.load(f)
                logger.info(f"Loaded {len(self.deployments)} existing deployments")
        except Exception as e:
            logger.error(f"Error loading deployments: {str(e)}")
            self.deployments = {}
            
    def _save_deployments(self):
        """Save deployments to storage"""
        try:
            index_path = os.path.join(self.storage_path, "deployments.json")
            with open(index_path, 'w') as f:
                json.dump(self.deployments, f, indent=2)
        except Exception as e:
            logger.error(f"Error saving deployments: {str(e)}")
            
    def deploy_agent(self, 
                    agent_config: Dict[str, Any],
                    developer_id: str,
                    plugins: List[Dict[str, Any]] = None) -> str:
        """
        Deploy a new agent
        
        Args:
            agent_config: Agent configuration dictionary
            developer_id: ID of the developer deploying the agent
            plugins: Optional list of plugins for the agent
            
        Returns:
            Deployment ID
        """
        try:
            # Generate a unique deployment ID
            deployment_id = str(uuid.uuid4())
            
            # Create deployment record
            deployment = {
                "deployment_id": deployment_id,
                "agent_name": agent_config.get("name", "Unnamed Agent"),
                "agent_version": agent_config.get("version", "1.0.0"),
                "description": agent_config.get("description", ""),
                "developer_id": developer_id,
                "created_at": datetime.now().isoformat(),
                "status": "deployed",
                "plugins": [],
                "config": agent_config,
                "metadata": {}
            }
            
            # Process plugins if provided
            if plugins:
                plugin_dir = os.path.join(self.storage_path, deployment_id, "plugins")
                os.makedirs(plugin_dir, exist_ok=True)
                
                for i, plugin in enumerate(plugins):
                    plugin_name = plugin.get("name", f"plugin_{i}.py")
                    plugin_path = os.path.join(plugin_dir, plugin_name)
                    
                    # Save plugin to file
                    with open(plugin_path, 'w') as f:
                        f.write(plugin.get("content", ""))
                        
                    deployment["plugins"].append({
                        "name": plugin_name,
                        "type": plugin.get("type", "unknown"),
                        "path": plugin_path
                    })
            
            # Save agent configuration
            agent_dir = os.path.join(self.storage_path, deployment_id)
            os.makedirs(agent_dir, exist_ok=True)
            
            config_path = os.path.join(agent_dir, "agent_config.json")
            with open(config_path, 'w') as f:
                json.dump(agent_config, f, indent=2)
                
            # Update deployments registry
            self.deployments[deployment_id] = deployment
            self._save_deployments()
            
            logger.info(f"Deployed agent '{deployment['agent_name']}' with ID: {deployment_id}")
            return deployment_id
        except Exception as e:
            logger.error(f"Error deploying agent: {str(e)}")
            return None
            
    def get_deployment(self, deployment_id: str) -> Dict[str, Any]:
        """
        Get deployment information
        
        Args:
            deployment_id: ID of the deployment to retrieve
            
        Returns:
            Deployment information or None if not found
        """
        return self.deployments.get(deployment_id)
        
    def list_deployments(self, developer_id: str = None) -> List[Dict[str, Any]]:
        """
        List deployments, optionally filtered by developer ID
        
        Args:
            developer_id: Optional developer ID to filter by
            
        Returns:
            List of deployment information dictionaries
        """
        if developer_id:
            return [d for d in self.deployments.values() if d["developer_id"] == developer_id]
        else:
            return list(self.deployments.values())
            
    def update_deployment_status(self, 
                                deployment_id: str, 
                                status: str,
                                metadata: Dict[str, Any] = None) -> bool:
        """
        Update deployment status
        
        Args:
            deployment_id: ID of the deployment to update
            status: New status (deployed, running, stopped, failed)
            metadata: Optional additional metadata to update
            
        Returns:
            True if successful, False otherwise
        """
        if deployment_id not in self.deployments:
            logger.error(f"Deployment not found: {deployment_id}")
            return False
            
        try:
            self.deployments[deployment_id]["status"] = status
            
            if metadata:
                self.deployments[deployment_id]["metadata"].update(metadata)
                
            self._save_deployments()
            
            logger.info(f"Updated deployment {deployment_id} status to: {status}")
            return True
        except Exception as e:
            logger.error(f"Error updating deployment status: {str(e)}")
            return False
