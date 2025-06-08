"""
MCP-ZERO Config Utilities

Configuration management for the MCP-ZERO SDK.
"""

import os
import logging
from typing import Dict, Any, Optional

import yaml

from ..exceptions import ConfigError

# Setup logger
logger = logging.getLogger("mcp_zero.utils.config")


class ClientConfig:
    """
    MCP-ZERO client configuration.
    
    Attrs:
        host: Server hostname or IP.
        port: Server port.
        timeout: Default timeout for operations.
        log_level: Logging level.
        log_file: Log file path.
    """
    
    def __init__(
        self,
        host: str = "localhost",
        port: int = 50051,
        timeout: float = 10.0,
        log_level: str = "INFO",
        log_file: Optional[str] = None,
    ):
        self.host = host
        self.port = port
        self.timeout = timeout
        self.log_level = log_level
        self.log_file = log_file
    
    def update(self, config: Dict[str, Any]) -> None:
        """Update config from dictionary."""
        if not isinstance(config, dict):
            return
        
        for key, value in config.items():
            if hasattr(self, key):
                setattr(self, key, value)
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary."""
        return {
            "host": self.host,
            "port": self.port,
            "timeout": self.timeout,
            "log_level": self.log_level,
            "log_file": self.log_file,
        }


def load_config_from_file(path: str) -> Dict[str, Any]:
    """
    Load configuration from a YAML file.
    
    Args:
        path: Path to YAML configuration file.
        
    Returns:
        Configuration dictionary.
        
    Raises:
        ConfigError: If file not found or invalid.
    """
    try:
        if not os.path.exists(path):
            raise ConfigError(f"Config file not found: {path}")
        
        with open(path, "r") as f:
            config = yaml.safe_load(f)
        
        if not isinstance(config, dict):
            raise ConfigError("Invalid configuration format")
        
        return config
    except Exception as e:
        if isinstance(e, ConfigError):
            raise
        raise ConfigError(f"Failed to load config: {e}")


def save_config_to_file(config: Dict[str, Any], path: str) -> None:
    """
    Save configuration to a YAML file.
    
    Args:
        config: Configuration dictionary.
        path: Path to save YAML file.
        
    Raises:
        ConfigError: If saving fails.
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(os.path.abspath(path)), exist_ok=True)
        
        with open(path, "w") as f:
            yaml.dump(config, f, default_flow_style=False)
    except Exception as e:
        raise ConfigError(f"Failed to save config: {e}")


def get_config_paths() -> Dict[str, str]:
    """
    Get standard configuration file paths.
    
    Returns:
        Dictionary of config paths:
        - system: System-wide config path
        - user: User config path
        - project: Current project config path
    """
    # System config path
    system_config = "/etc/mcp-zero/config.yaml"
    
    # User config path
    user_config = os.path.expanduser("~/.config/mcp-zero/config.yaml")
    
    # Project config path
    project_config = os.path.join(os.getcwd(), "mcp-zero.yaml")
    
    return {
        "system": system_config,
        "user": user_config,
        "project": project_config,
    }


def load_config() -> Dict[str, Any]:
    """
    Load configuration from standard paths.
    
    Loads and merges configuration from system, user, and project paths.
    
    Returns:
        Merged configuration dictionary.
    """
    config = {}
    paths = get_config_paths()
    
    # Load system config if it exists
    if os.path.exists(paths["system"]):
        try:
            system_config = load_config_from_file(paths["system"])
            config.update(system_config)
        except ConfigError as e:
            logger.warning(f"Failed to load system config: {e}")
    
    # Load user config if it exists
    if os.path.exists(paths["user"]):
        try:
            user_config = load_config_from_file(paths["user"])
            config.update(user_config)
        except ConfigError as e:
            logger.warning(f"Failed to load user config: {e}")
    
    # Load project config if it exists
    if os.path.exists(paths["project"]):
        try:
            project_config = load_config_from_file(paths["project"])
            config.update(project_config)
        except ConfigError as e:
            logger.warning(f"Failed to load project config: {e}")
    
    # Override with environment variables
    env_prefix = "MCP_"
    for key, value in os.environ.items():
        if key.startswith(env_prefix):
            config_key = key[len(env_prefix):].lower()
            
            # Convert numeric values
            if value.isdigit():
                value = int(value)
            elif value.replace(".", "", 1).isdigit():
                value = float(value)
            elif value.lower() in ("true", "false"):
                value = value.lower() == "true"
            
            config[config_key] = value
    
    return config
