"""
Secure Configuration Manager for MCP Zero

This module provides a resilient configuration management system that works
in both online and offline modes, following the same pattern as the successful
DBMemoryTree and Traffic Agent improvements.
"""

import os
import time
import json
import yaml
import logging
import hashlib
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable

logger = logging.getLogger("mcp_zero.config")

class ConfigMode(Enum):
    """Operating modes for configuration management."""
    ONLINE = "online"  # Configuration from central repository
    OFFLINE = "offline"  # Configuration from local files


class ConfigManager:
    """
    Secure and resilient configuration manager for MCP Zero components.
    
    This manager starts in offline mode by default and will attempt to
    connect to the configuration server once. If connection fails, it
    remains in offline mode using local configuration files.
    """
    
    def __init__(
        self,
        component_name: str,
        config_server: Optional[str] = None,
        local_dir: str = "/etc/mcp-zero/config",
        refresh_interval: int = 300
    ):
        """
        Initialize configuration manager.
        
        Args:
            component_name: Name of component
            config_server: URL of config server (None for offline only)
            local_dir: Directory for local configuration files
            refresh_interval: Seconds between config refresh checks
        """
        self.component_name = component_name
        self.config_server = config_server
        self.local_dir = local_dir
        self.refresh_interval = refresh_interval
        
        # Start in offline mode like DBMemoryTree
        self.mode = ConfigMode.OFFLINE
        
        # Config cache
        self._config = {}
        self._config_versions = {}
        self._lock = threading.RLock()
        
        # Ensure local config directory exists
        if not os.path.exists(local_dir):
            os.makedirs(local_dir, exist_ok=True)
        
        # Try to connect to config server if provided
        if config_server:
            self._try_connect()
        
        # Load initial configuration
        self._load_config()
        
        # Start background refresh thread if online
        if self.mode == ConfigMode.ONLINE:
            self._start_refresh_thread()
        
        logger.info(
            f"Config manager initialized for {component_name} in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to config server.
        
        Like the Traffic Agent improvement, this will only try once and
        then remain in the determined mode.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import requests
            response = requests.get(
                f"{self.config_server}/health",
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = ConfigMode.ONLINE
                logger.info(f"Connected to config server: {self.config_server}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to config server: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to config server: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def _load_config(self) -> None:
        """Load configuration from server or local files."""
        if self.mode == ConfigMode.ONLINE:
            self._load_online_config()
        else:
            self._load_offline_config()
    
    def _load_online_config(self) -> None:
        """Load configuration from online server."""
        try:
            import requests
            response = requests.get(
                f"{self.config_server}/config/{self.component_name}",
                timeout=5.0
            )
            
            if response.status_code == 200:
                data = response.json()
                with self._lock:
                    self._config = data.get("config", {})
                    self._config_versions = data.get("versions", {})
                    
                # Also save to local files as backup
                self._save_to_local()
                
            else:
                logger.warning(
                    f"Failed to fetch config from server: {response.status_code}"
                )
                # Fall back to offline config
                self._load_offline_config()
                
        except Exception as e:
            logger.warning(f"Error loading online config: {str(e)}")
            # Fall back to offline config
            self._load_offline_config()
            # Switch to offline mode permanently if we were online
            if self.mode == ConfigMode.ONLINE:
                self.mode = ConfigMode.OFFLINE
                logger.warning("Switched to offline config mode due to server issues")
    
    def _load_offline_config(self) -> None:
        """Load configuration from local files."""
        config = {}
        versions = {}
        
        try:
            # Load main component config
            main_config_path = os.path.join(
                self.local_dir,
                f"{self.component_name}.yaml"
            )
            
            if os.path.exists(main_config_path):
                with open(main_config_path, 'r') as f:
                    config = yaml.safe_load(f) or {}
            else:
                # Try JSON if YAML doesn't exist
                json_path = os.path.join(
                    self.local_dir,
                    f"{self.component_name}.json"
                )
                if os.path.exists(json_path):
                    with open(json_path, 'r') as f:
                        config = json.load(f)
            
            # Load versions file if it exists
            versions_path = os.path.join(
                self.local_dir,
                f"{self.component_name}.versions"
            )
            if os.path.exists(versions_path):
                with open(versions_path, 'r') as f:
                    versions = json.load(f)
            
            with self._lock:
                self._config = config
                self._config_versions = versions
                
            logger.info(
                f"Loaded configuration for {self.component_name} from local files"
            )
            
        except Exception as e:
            logger.error(f"Error loading local config: {str(e)}")
            # If we fail to load local config, start with empty config
            with self._lock:
                self._config = {}
                self._config_versions = {}
    
    def _save_to_local(self) -> bool:
        """
        Save current configuration to local files.
        
        Returns:
            True if successful, False otherwise
        """
        try:
            # Save main config to YAML
            config_path = os.path.join(
                self.local_dir,
                f"{self.component_name}.yaml"
            )
            
            with open(config_path, 'w') as f:
                yaml.dump(self._config, f, default_flow_style=False)
            
            # Save versions
            versions_path = os.path.join(
                self.local_dir,
                f"{self.component_name}.versions"
            )
            
            with open(versions_path, 'w') as f:
                json.dump(self._config_versions, f)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to save config to local files: {str(e)}")
            return False
    
    def _start_refresh_thread(self) -> None:
        """Start background thread for refreshing configuration."""
        thread = threading.Thread(
            target=self._background_refresh,
            daemon=True,
            name="config-refresh"
        )
        thread.start()
    
    def _background_refresh(self) -> None:
        """Background thread that periodically refreshes configuration."""
        while True:
            time.sleep(self.refresh_interval)
            
            try:
                self._check_for_updates()
            except Exception as e:
                logger.error(f"Error in config refresh: {str(e)}")
    
    def _check_for_updates(self) -> bool:
        """
        Check for configuration updates.
        
        Returns:
            True if updates were found and applied, False otherwise
        """
        if self.mode != ConfigMode.ONLINE:
            return False
            
        try:
            import requests
            response = requests.get(
                f"{self.config_server}/versions/{self.component_name}",
                timeout=3.0
            )
            
            if response.status_code != 200:
                return False
                
            server_versions = response.json()
            
            # Check if any config versions are different
            updates_needed = False
            for key, version in server_versions.items():
                if key not in self._config_versions or self._config_versions[key] != version:
                    updates_needed = True
                    break
            
            if updates_needed:
                logger.info("Configuration updates found, refreshing")
                self._load_online_config()
                return True
                
            return False
            
        except Exception as e:
            logger.warning(f"Failed to check for config updates: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value by key.
        
        Args:
            key: Configuration key (supports dot notation for nested keys)
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            # Handle nested keys with dot notation
            if "." in key:
                parts = key.split(".")
                current = self._config
                
                for part in parts:
                    if isinstance(current, dict) and part in current:
                        current = current[part]
                    else:
                        return default
                        
                return current
            else:
                return self._config.get(key, default)
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get complete configuration.
        
        Returns:
            Copy of current configuration
        """
        with self._lock:
            return self._config.copy()
    
    def get_secure(
        self, 
        key: str, 
        default: Any = None,
        verify_checksum: bool = True
    ) -> Any:
        """
        Get security-sensitive configuration with integrity check.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            verify_checksum: Whether to verify integrity checksum
            
        Returns:
            Configuration value or default
        """
        value = self.get(key, None)
        
        if value is None:
            return default
        
        # For secured values, we expect a dict with 'value' and 'checksum'
        if isinstance(value, dict) and 'value' in value and 'checksum' in value:
            if verify_checksum:
                # Verify checksum
                computed = self._compute_checksum(value['value'])
                if computed != value['checksum']:
                    logger.warning(
                        f"Security checksum verification failed for {key}"
                    )
                    return default
                    
            return value['value']
            
        # If not in secure format, return as is
        return value
    
    def _compute_checksum(self, value: Any) -> str:
        """
        Compute checksum for configuration value.
        
        Args:
            value: Configuration value
            
        Returns:
            Checksum string
        """
        if isinstance(value, (dict, list)):
            value = json.dumps(value, sort_keys=True)
        else:
            value = str(value)
            
        return hashlib.sha256(value.encode()).hexdigest()
    
    def reload(self) -> bool:
        """
        Force configuration reload.
        
        Returns:
            True if reload was successful, False otherwise
        """
        try:
            self._load_config()
            return True
        except Exception as e:
            logger.error(f"Failed to reload configuration: {str(e)}")
            return False


# Global config manager instance
default_manager = None


def init(
    component_name: str,
    config_server: Optional[str] = None,
    **kwargs
) -> ConfigManager:
    """
    Initialize the default configuration manager.
    
    Args:
        component_name: Component name
        config_server: Configuration server URL
        **kwargs: Additional arguments for ConfigManager
        
    Returns:
        Configuration manager instance
    """
    global default_manager
    default_manager = ConfigManager(
        component_name=component_name,
        config_server=config_server,
        **kwargs
    )
    return default_manager


def get(key: str, default: Any = None) -> Any:
    """
    Get configuration value from default manager.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    if default_manager is None:
        logger.warning("Config manager not initialized, returning default value")
        return default
        
    return default_manager.get(key, default)


def get_secure(key: str, default: Any = None) -> Any:
    """
    Get secure configuration value from default manager.
    
    Args:
        key: Configuration key
        default: Default value if key not found
        
    Returns:
        Configuration value or default
    """
    if default_manager is None:
        logger.warning("Config manager not initialized, returning default value")
        return default
        
    return default_manager.get_secure(key, default)


def get_all() -> Dict[str, Any]:
    """
    Get complete configuration from default manager.
    
    Returns:
        Copy of current configuration
    """
    if default_manager is None:
        logger.warning("Config manager not initialized, returning empty config")
        return {}
        
    return default_manager.get_all()


def reload() -> bool:
    """
    Reload configuration from default manager.
    
    Returns:
        True if successful, False otherwise
    """
    if default_manager is None:
        logger.warning("Config manager not initialized")
        return False
        
    return default_manager.reload()
