"""
Configuration Manager for MCP Zero Editor

Provides resilient access to configuration with offline-first capability.
"""

import os
import json
import logging
import threading
from typing import Dict, Any, Optional

logger = logging.getLogger("mcp_zero.editor.config_manager")

class ConfigManager:
    """
    Configuration manager with offline-first resilience.
    
    Follows offline-first approach:
    - Always loads from local file first
    - Only attempts to connect to remote config service once
    - Permanently switches to local-only if remote service is unavailable
    """
    
    def __init__(self, config_file: str, offline_first: bool = True):
        """
        Initialize configuration manager.
        
        Args:
            config_file: Path to local configuration file
            offline_first: Whether to start in offline mode
        """
        self.config_file = config_file
        self.offline_mode = offline_first
        self._config = {}
        self._lock = threading.RLock()
        self._remote_attempt_made = False
        
        # Ensure config directory exists
        os.makedirs(os.path.dirname(config_file), exist_ok=True)
        
        # Load config
        self.load()
        
        logger.info(f"Config manager initialized in {'offline' if offline_first else 'online'} mode")
    
    def load(self) -> bool:
        """
        Load configuration from local file.
        
        Returns:
            True if configuration was loaded successfully
        """
        try:
            if os.path.exists(self.config_file):
                with open(self.config_file, 'r') as f:
                    self._config = json.load(f)
                logger.info(f"Configuration loaded from {self.config_file}")
                return True
            else:
                # Create default config
                self._config = self._get_default_config()
                self.save()
                logger.info("Default configuration created")
                return True
                
        except Exception as e:
            logger.error(f"Error loading configuration: {str(e)}")
            self._config = self._get_default_config()
            return False
    
    def save(self) -> bool:
        """
        Save configuration to local file.
        
        Returns:
            True if configuration was saved successfully
        """
        try:
            with open(self.config_file, 'w') as f:
                json.dump(self._config, f, indent=2)
            logger.info(f"Configuration saved to {self.config_file}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving configuration: {str(e)}")
            return False
    
    def get(self, key: str, default: Any = None) -> Any:
        """
        Get configuration value.
        
        Args:
            key: Configuration key
            default: Default value if key not found
            
        Returns:
            Configuration value or default
        """
        with self._lock:
            return self._config.get(key, default)
    
    def set(self, key: str, value: Any) -> None:
        """
        Set configuration value.
        
        Args:
            key: Configuration key
            value: Configuration value
        """
        with self._lock:
            self._config[key] = value
    
    def get_all(self) -> Dict[str, Any]:
        """
        Get all configuration values.
        
        Returns:
            Dictionary of all configuration values
        """
        with self._lock:
            return self._config.copy()
    
    def _sync_with_remote(self) -> bool:
        """
        Try to sync with remote configuration service.
        
        Following the pattern from Traffic Agent, this will
        only attempt once and then permanently switch to local mode.
        
        Returns:
            True if sync successful
        """
        # Skip if already attempted or in offline mode
        if self._remote_attempt_made or self.offline_mode:
            return False
            
        try:
            # Mark that we've made the attempt
            self._remote_attempt_made = True
            
            # Simulate a remote config service
            # In real implementation, this would connect to a service
            logger.info("Remote configuration sync not available, using local config only")
            return False
            
        except Exception as e:
            logger.warning(f"Failed to sync with remote configuration: {str(e)}")
            return False
    
    def is_healthy(self) -> bool:
        """
        Check if configuration manager is healthy.
        
        Returns:
            True if healthy
        """
        # Config manager is always healthy in offline mode
        return True
    
    def _get_default_config(self) -> Dict[str, Any]:
        """
        Get default configuration.
        
        Returns:
            Default configuration dictionary
        """
        return {
            "editor": {
                "font_size": 12,
                "font_family": "Courier New",
                "tab_size": 4,
                "use_spaces": True,
                "line_numbers": True,
                "syntax_highlight": True,
                "auto_save": True,
                "theme": "default"
            },
            "llm": {
                "provider": "offline",
                "model": "gpt-4",
                "temperature": 0.7,
                "max_tokens": 1000
            },
            "plugins": {
                "enabled": True,
                "autoload": True
            },
            "paths": {
                "recent_files": []
            }
        }
