#!/usr/bin/env python3
"""
MCP-ZERO Configuration System
Provides centralized configuration for all MCP-ZERO components
"""
import os
import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

# Configure logging
logging.basicConfig(level=logging.INFO, format='%(asctime)s [%(levelname)s] %(name)s: %(message)s')
logger = logging.getLogger('config')

class Settings:
    """
    Centralized configuration system for MCP-ZERO infrastructure
    Loads settings from environment variables and configuration files
    """
    
    def __init__(self, config_path: str = None):
        """
        Initialize the configuration system
        
        Args:
            config_path: Path to configuration file (optional)
        """
        self.config = {}
        
        # Default configuration
        self.config.update(self._get_defaults())
        
        # Load from configuration file if provided
        if config_path:
            self.config.update(self._load_config_file(config_path))
            
        # Override with environment variables
        self.config.update(self._load_from_env())
        
        logger.info(f"Initialized configuration settings")
        
    def _get_defaults(self) -> Dict[str, Any]:
        """Get default configuration values"""
        return {
            # API settings
            "api": {
                "host": "0.0.0.0",
                "port": 8000,
                "debug": False,
                "cors_origins": ["*"],
                "api_keys_enabled": True
            },
            
            # Database settings
            "database": {
                "type": "sqlite",  # sqlite, postgres, etc.
                "path": "data/mcp_zero.db",
                "host": "localhost",
                "port": 5432,
                "name": "mcp_zero",
                "user": "",
                "password": ""
            },
            
            # Marketplace settings
            "marketplace": {
                "data_path": "marketplace/data",
                "storage_path": "marketplace/data/storage",
                "platform_fee": 10.0  # % platform fee
            },
            
            # Agreements settings
            "agreements": {
                "storage_path": "agreements/storage",
                "templates_path": "agreements/templates"
            },
            
            # Deployment settings
            "deployment": {
                "agents_path": "deploy/agents",
                "plugins_path": "deploy/plugins",
                "cloud_url": "https://api.mcp-zero.cloud",
                "max_agents": 100
            },
            
            # Mesh network settings
            "mesh": {
                "enabled": False,
                "host": "localhost",
                "port": 8765,
                "heartbeat_interval": 30,  # seconds
                "discovery_interval": 300  # seconds
            },
            
            # Security settings
            "security": {
                "jwt_secret": "",
                "jwt_algorithm": "HS256",
                "jwt_expiry": 86400,  # seconds (1 day)
                "ssl_enabled": False,
                "ssl_cert": "",
                "ssl_key": ""
            },
            
            # Logging settings
            "logging": {
                "level": "INFO",
                "file_path": "logs/mcp_zero.log",
                "rotation": "1 day",
                "retention": "30 days"
            }
        }
        
    def _load_config_file(self, config_path: str) -> Dict[str, Any]:
        """Load configuration from file"""
        try:
            path = Path(config_path)
            
            if not path.exists():
                logger.warning(f"Configuration file not found: {config_path}")
                return {}
                
            with open(path, 'r') as f:
                if path.suffix.lower() in ['.yml', '.yaml']:
                    import yaml
                    config = yaml.safe_load(f)
                elif path.suffix.lower() == '.json':
                    config = json.load(f)
                else:
                    logger.warning(f"Unsupported configuration file format: {path.suffix}")
                    return {}
                    
            logger.info(f"Loaded configuration from {config_path}")
            return config
        except Exception as e:
            logger.error(f"Error loading configuration file: {str(e)}")
            return {}
            
    def _load_from_env(self) -> Dict[str, Any]:
        """Load configuration from environment variables"""
        env_config = {}
        
        # API settings
        if "MCP_API_HOST" in os.environ:
            self._set_nested(env_config, ["api", "host"], os.environ["MCP_API_HOST"])
            
        if "MCP_API_PORT" in os.environ:
            self._set_nested(env_config, ["api", "port"], int(os.environ["MCP_API_PORT"]))
            
        if "MCP_API_DEBUG" in os.environ:
            self._set_nested(env_config, ["api", "debug"], os.environ["MCP_API_DEBUG"].lower() == "true")
            
        # Database settings
        if "MCP_DB_TYPE" in os.environ:
            self._set_nested(env_config, ["database", "type"], os.environ["MCP_DB_TYPE"])
            
        if "MCP_DB_PATH" in os.environ:
            self._set_nested(env_config, ["database", "path"], os.environ["MCP_DB_PATH"])
            
        if "MCP_DB_HOST" in os.environ:
            self._set_nested(env_config, ["database", "host"], os.environ["MCP_DB_HOST"])
            
        if "MCP_DB_PORT" in os.environ:
            self._set_nested(env_config, ["database", "port"], int(os.environ["MCP_DB_PORT"]))
            
        if "MCP_DB_NAME" in os.environ:
            self._set_nested(env_config, ["database", "name"], os.environ["MCP_DB_NAME"])
            
        if "MCP_DB_USER" in os.environ:
            self._set_nested(env_config, ["database", "user"], os.environ["MCP_DB_USER"])
            
        if "MCP_DB_PASSWORD" in os.environ:
            self._set_nested(env_config, ["database", "password"], os.environ["MCP_DB_PASSWORD"])
            
        # Security settings
        if "MCP_JWT_SECRET" in os.environ:
            self._set_nested(env_config, ["security", "jwt_secret"], os.environ["MCP_JWT_SECRET"])
            
        if "MCP_API_KEYS" in os.environ:
            self._set_nested(env_config, ["security", "api_keys"], os.environ["MCP_API_KEYS"].split(","))
            
        # Mesh settings
        if "MCP_MESH_ENABLED" in os.environ:
            self._set_nested(env_config, ["mesh", "enabled"], os.environ["MCP_MESH_ENABLED"].lower() == "true")
            
        if "MCP_MESH_HOST" in os.environ:
            self._set_nested(env_config, ["mesh", "host"], os.environ["MCP_MESH_HOST"])
            
        if "MCP_MESH_PORT" in os.environ:
            self._set_nested(env_config, ["mesh", "port"], int(os.environ["MCP_MESH_PORT"]))
            
        # Logging settings
        if "MCP_LOG_LEVEL" in os.environ:
            self._set_nested(env_config, ["logging", "level"], os.environ["MCP_LOG_LEVEL"])
            
        if "MCP_LOG_PATH" in os.environ:
            self._set_nested(env_config, ["logging", "file_path"], os.environ["MCP_LOG_PATH"])
            
        return env_config
        
    def _set_nested(self, config: Dict[str, Any], path: list, value: Any):
        """Set a nested configuration value"""
        current = config
        for key in path[:-1]:
            if key not in current:
                current[key] = {}
            current = current[key]
        current[path[-1]] = value
        
    def get(self, path: str, default: Any = None) -> Any:
        """
        Get a configuration value by path
        
        Args:
            path: Dot-separated path to the configuration value
            default: Default value if not found
            
        Returns:
            Configuration value
        """
        parts = path.split('.')
        current = self.config
        
        for part in parts:
            if isinstance(current, dict) and part in current:
                current = current[part]
            else:
                return default
                
        return current
        
    def set(self, path: str, value: Any):
        """
        Set a configuration value by path
        
        Args:
            path: Dot-separated path to the configuration value
            value: Value to set
        """
        parts = path.split('.')
        self._set_nested(self.config, parts, value)
        
    def get_all(self) -> Dict[str, Any]:
        """
        Get the entire configuration
        
        Returns:
            Complete configuration dictionary
        """
        return self.config
        
    def save(self, file_path: str):
        """
        Save the current configuration to a file
        
        Args:
            file_path: Path to save the configuration
        """
        try:
            path = Path(file_path)
            
            # Create parent directory if it doesn't exist
            path.parent.mkdir(parents=True, exist_ok=True)
            
            with open(path, 'w') as f:
                if file_path.endswith(('.yml', '.yaml')):
                    import yaml
                    yaml.dump(self.config, f, default_flow_style=False)
                else:
                    json.dump(self.config, f, indent=2)
                    
            logger.info(f"Saved configuration to {file_path}")
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")

# Create global settings instance with default configuration
settings = Settings()

def configure(config_path: str = None):
    """
    Configure the global settings instance
    
    Args:
        config_path: Path to configuration file
    """
    global settings
    settings = Settings(config_path)
