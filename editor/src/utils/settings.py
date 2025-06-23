"""
Settings Manager for MCP Zero Editor

Manages user settings with offline-first resilience pattern.
"""

import os
import json
import logging
import threading
import time
from typing import Any, Dict, Optional, List, Union

# Initialize logger
logger = logging.getLogger("mcp_zero.editor.settings")

class SettingsManager:
    """
    Manages editor settings with offline-first resilience.
    
    - Starts in offline mode with local settings
    - Only attempts to sync settings once to avoid cascading failures
    - Falls back to local settings permanently if sync fails
    """
    
    DEFAULT_SETTINGS = {
        "editor": {
            "font_family": "Consolas",
            "font_size": 12,
            "tab_size": 4,
            "use_spaces": True,
            "show_line_numbers": True,
            "word_wrap": False,
            "theme": "default",
            "auto_indent": True,
            "auto_save": True,
            "auto_save_interval": 60  # seconds
        },
        "llm": {
            "provider": "openai",
            "model": "gpt-3.5-turbo",
            "temperature": 0.7,
            "max_tokens": 1000,
            "offline_mode": True,  # Default to offline mode
            "api_host": "https://api.openai.com"
        },
        "ui": {
            "show_toolbar": True,
            "show_statusbar": True,
            "window_width": 1200,
            "window_height": 800,
            "panel_ratio": 0.7  # Main panel to assistant panel ratio
        },
        "plugins": {
            "enabled": [],
            "disabled": []
        },
        "paths": {
            "recent_files": [],
            "custom_plugin_dirs": []
        }
    }
    
    def __init__(self, settings_dir: Optional[str] = None):
        """
        Initialize settings manager.
        
        Args:
            settings_dir: Directory for storing settings (None for default)
        """
        # Set up settings directory
        if settings_dir:
            self.settings_dir = settings_dir
        else:
            self.settings_dir = os.path.join(
                os.path.expanduser("~"), 
                ".mcp_zero", 
                "editor", 
                "settings"
            )
            
        # Create settings directory if it doesn't exist
        os.makedirs(self.settings_dir, exist_ok=True)
            
        self.settings_file = os.path.join(self.settings_dir, "settings.json")
        
        # Sync status
        self.sync_attempted = False
        self.sync_succeeded = False
        
        # Thread safety
        self._lock = threading.RLock()
        
        # Load settings
        self.settings = self._load_settings()
        
        logger.info(f"Settings manager initialized. Settings dir: {self.settings_dir}")
    
    def _load_settings(self) -> Dict[str, Any]:
        """
        Load settings from file or create default.
        
        Returns:
            Dictionary containing settings
        """
        with self._lock:
            try:
                if os.path.exists(self.settings_file):
                    with open(self.settings_file, 'r', encoding='utf-8') as f:
                        settings = json.load(f)
                        
                    # Merge with defaults for any missing settings
                    merged_settings = self._merge_with_defaults(settings)
                    return merged_settings
                else:
                    # Create default settings file
                    logger.info("No settings file found, creating defaults")
                    self._save_settings(self.DEFAULT_SETTINGS)
                    return self.DEFAULT_SETTINGS.copy()
                    
            except Exception as e:
                logger.error(f"Error loading settings: {str(e)}")
                # Fall back to defaults on error
                return self.DEFAULT_SETTINGS.copy()
    
    def _merge_with_defaults(self, settings: Dict[str, Any]) -> Dict[str, Any]:
        """
        Merge user settings with defaults to ensure all required settings exist.
        
        Args:
            settings: User settings to merge
            
        Returns:
            Complete settings with defaults applied where needed
        """
        merged = self.DEFAULT_SETTINGS.copy()
        
        # Helper for deep merge
        def deep_merge(target, source):
            for key, value in source.items():
                if key in target and isinstance(target[key], dict) and isinstance(value, dict):
                    deep_merge(target[key], value)
                else:
                    target[key] = value
        
        deep_merge(merged, settings)
        return merged
    
    def _save_settings(self, settings: Dict[str, Any]) -> bool:
        """
        Save settings to file.
        
        Args:
            settings: Settings to save
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            try:
                with open(self.settings_file, 'w', encoding='utf-8') as f:
                    json.dump(settings, f, indent=2)
                return True
            except Exception as e:
                logger.error(f"Error saving settings: {str(e)}")
                return False
    
    def get(self, section: str, key: Optional[str] = None, default: Any = None) -> Any:
        """
        Get setting value.
        
        Args:
            section: Settings section name
            key: Setting key (None to get entire section)
            default: Default value if setting doesn't exist
            
        Returns:
            Setting value or default
        """
        with self._lock:
            if section not in self.settings:
                return default
            
            if key is None:
                return self.settings[section]
            
            return self.settings[section].get(key, default)
    
    def set(self, section: str, key: str, value: Any) -> bool:
        """
        Set setting value.
        
        Args:
            section: Settings section name
            key: Setting key
            value: Setting value
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            # Create section if it doesn't exist
            if section not in self.settings:
                self.settings[section] = {}
                
            # Update setting
            self.settings[section][key] = value
            
            # Save settings
            return self._save_settings(self.settings)
    
    def update_section(self, section: str, values: Dict[str, Any]) -> bool:
        """
        Update multiple settings in a section.
        
        Args:
            section: Section to update
            values: Dictionary of key-value pairs to update
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            # Create section if it doesn't exist
            if section not in self.settings:
                self.settings[section] = {}
                
            # Update settings
            self.settings[section].update(values)
            
            # Save settings
            return self._save_settings(self.settings)
    
    def add_recent_file(self, filepath: str, max_files: int = 10) -> bool:
        """
        Add a file to recent files list.
        
        Args:
            filepath: Path to add
            max_files: Maximum number of recent files to keep
            
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            recent = self.get("paths", "recent_files", [])
            
            # Remove if already in list
            if filepath in recent:
                recent.remove(filepath)
                
            # Add to front of list
            recent.insert(0, filepath)
            
            # Trim list
            if len(recent) > max_files:
                recent = recent[:max_files]
                
            # Save
            return self.set("paths", "recent_files", recent)
    
    def sync_settings(self) -> bool:
        """
        Sync settings with remote storage (if configured).
        
        This follows our offline-first resilience pattern:
        - Only attempts to sync once
        - Falls back to local settings if sync fails
        
        Returns:
            True if sync successful, False otherwise
        """
        with self._lock:
            # Only attempt to sync once
            if self.sync_attempted:
                logger.debug("Sync already attempted, using local settings")
                return self.sync_succeeded
                
            self.sync_attempted = True
            
            # Check if remote sync is enabled
            sync_url = os.environ.get("MCP_ZERO_SETTINGS_SYNC")
            
            if not sync_url:
                logger.info("Remote settings sync not configured")
                return False
                
            try:
                # This would implement the actual sync logic
                # For now, we just simulate the offline-first pattern
                
                # Simulate sync attempt
                logger.info("Attempting to sync settings with remote storage")
                
                # If we were to implement this, we would:
                # 1. Try to connect to remote sync service once
                # 2. If successful, merge remote and local settings
                # 3. If failed, continue with local settings
                
                # For demo, always "fail" to sync
                self.sync_succeeded = False
                
                logger.info("Settings sync failed, using local settings")
                return False
                
            except Exception as e:
                logger.error(f"Error syncing settings: {str(e)}")
                return False
    
    def reset_to_defaults(self) -> bool:
        """
        Reset settings to default values.
        
        Returns:
            True if successful, False otherwise
        """
        with self._lock:
            self.settings = self.DEFAULT_SETTINGS.copy()
            return self._save_settings(self.settings)


# Global settings instance for easy access
def get_settings(settings_dir: Optional[str] = None) -> SettingsManager:
    """
    Get or create global settings manager instance.
    
    Args:
        settings_dir: Optional settings directory
        
    Returns:
        Settings manager instance
    """
    global _settings_instance
    
    if '_settings_instance' not in globals():
        _settings_instance = SettingsManager(settings_dir)
        
    return _settings_instance
