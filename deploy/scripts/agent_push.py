#!/usr/bin/env python3
"""
MCP-ZERO Agent Push Tool
Allows developers to push and deploy agents to the MCP-ZERO mesh network
"""
import argparse
import hashlib
import json
import logging
import os
import sys
import time
import yaml
from typing import Dict, List, Optional, Any

sys.path.append(os.path.join(os.path.dirname(__file__), "..", ".."))
from deploy.mesh.zksync_verifier import ZKSyncVerifier
from deploy.cloud.cloud_connector import CloudConnector

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(message)s')
logger = logging.getLogger('agent_push')

class AgentPushTool:
    """Tool for pushing agents to MCP-ZERO mesh network"""
    
    def __init__(self, 
                mesh_url: str = "ws://localhost:8765",
                api_key: Optional[str] = None,
                use_ssl: bool = True):
        """Initialize the agent push tool"""
        self.mesh_url = mesh_url
        self.api_key = api_key or os.environ.get("MCP_API_KEY", "")
        self.use_ssl = use_ssl
        
        # Initialize cloud connector
        self.cloud = CloudConnector(
            mesh_url=mesh_url,
            api_key=self.api_key,
            use_ssl=self.use_ssl
        )
        
        # Initialize ZKSync verifier for signed deployments
        self.verifier = ZKSyncVerifier()
        
    async def push_agent(self, config_path: str, plugins_dir: str) -> Dict[str, Any]:
        """Push an agent to the MCP-ZERO mesh network"""
        # 1. Validate the agent configuration
        try:
            with open(config_path, 'r') as f:
                if config_path.endswith('.yaml') or config_path.endswith('.yml'):
                    config = yaml.safe_load(f)
                elif config_path.endswith('.json'):
                    config = json.load(f)
                else:
                    raise ValueError(f"Unsupported config file format: {config_path}")
        except Exception as e:
            return {
                "status": "error",
                "message": f"Failed to load agent configuration: {str(e)}",
                "config_path": config_path
            }
            
        # 2. Validate required configuration fields
        required_fields = ["name", "entry_plugin", "intents"]
        missing_fields = [field for field in required_fields if field not in config]
        if missing_fields:
            return {
                "status": "error",
                "message": f"Missing required fields in configuration: {', '.join(missing_fields)}",
                "config_path": config_path
            }
            
        # 3. Collect plugin files
        plugins = []
        for plugin_name in config.get("plugins", []):
            plugin_path = os.path.join(plugins_dir, f"{plugin_name}.py")
            if not os.path.exists(plugin_path):
                return {
                    "status": "error",
                    "message": f"Plugin not found: {plugin_name}",
                    "plugin_path": plugin_path
                }
                
            # Read plugin content
            with open(plugin_path, 'r') as f:
                plugin_content = f.read()
                
            plugins.append({
                "name": plugin_name,
                "content_hash": hashlib.sha256(plugin_content.encode()).hexdigest(),
                "path": plugin_path
            })
            
        # 4. Connect to the mesh network
        logger.info(f"Connecting to mesh network at {self.mesh_url}...")
        await self.cloud.connect()
        if not self.cloud.connected:
            return {
                "status": "error",
                "message": "Failed to connect to mesh network",
                "mesh_url": self.mesh_url
            }
            
        # 5. Create a signed deployment record
        logger.info("Creating signed deployment record...")
        deployment_record = self.verifier.sign_deployment(
            config.get("name"),
            config
        )
        
        # 6. Deploy the agent to the cloud
        logger.info(f"Deploying agent {config.get('name')} to cloud...")
        deployment = await self.cloud.deploy_agent_to_cloud(
            config.get("name"),
            {
                "config": config,
                "plugins": [p["name"] for p in plugins],
                "deployment_record": deployment_record
            }
        )
        
        # 7. Upload plugin files
        if deployment.get("status") == "success":
            agent_id = deployment.get("agent_id")
            logger.info(f"Agent deployed with ID: {agent_id}")
            
            for plugin in plugins:
                logger.info(f"Uploading plugin: {plugin['name']}...")
                
                # Upload the plugin file content
                with open(plugin["path"], 'r') as f:
                    plugin_content = f.read()
                    
                await self.cloud.store_data(
                    f"plugins/{agent_id}/{plugin['name']}", 
                    plugin_content
                )
        
        # 8. Disconnect from the mesh network
        await self.cloud.disconnect()
        
        return deployment
        
async def main():
    """Main entry point for the agent push tool"""
    parser = argparse.ArgumentParser(description='Push an agent to MCP-ZERO mesh network')
    parser.add_argument('config', help='Path to agent configuration file (.yaml or .json)')
    parser.add_argument('--plugins-dir', default='./plugins', help='Directory containing plugin files')
    parser.add_argument('--mesh-url', default='ws://localhost:8765', help='Mesh network WebSocket URL')
    parser.add_argument('--api-key', help='API key (defaults to MCP_API_KEY environment variable)')
    parser.add_argument('--no-ssl', action='store_true', help='Disable SSL for WebSocket connection')
    
    args = parser.parse_args()
    
    # Create and use the agent push tool
    push_tool = AgentPushTool(
        mesh_url=args.mesh_url,
        api_key=args.api_key,
        use_ssl=not args.no_ssl
    )
    
    result = await push_tool.push_agent(args.config, args.plugins_dir)
    
    if result.get("status") == "success":
        logger.info(f"Agent successfully pushed and deployed!")
        logger.info(f"Agent ID: {result.get('agent_id')}")
        sys.exit(0)
    else:
        logger.error(f"Failed to push agent: {result.get('message')}")
        sys.exit(1)
        
if __name__ == "__main__":
    import asyncio
    asyncio.run(main())
