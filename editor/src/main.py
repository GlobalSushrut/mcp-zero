"""
MCP Zero Editor

A lightweight but powerful code editor built on MCP Zero's resilient infrastructure patterns.
Integrates with LLM APIs for AI assistance while maintaining offline-first capability.
"""

import os
import sys
import logging
from typing import Optional
import argparse
import json
from threading import Timer


# Add parent directory to path to import MCP Zero components
sys.path.append(os.path.abspath(os.path.join(os.path.dirname(__file__), '../..')))

# We need to adjust imports based on how the module is being run
try:
    # Try direct imports first (when running as script)
    from api.config_manager import ConfigManager
    from api.telemetry_collector import TelemetryCollector
    from api.health_checker import HealthChecker
    from security.rate_limiter import RateLimiter
    
    from api.llm_service import LLMService
    from ui.editor import EditorApp
    from ui.syntax import apply_to_editor
    from plugins import PluginManager
    from utils.settings import get_settings
    
    logger = logging.getLogger("mcp_zero.editor.main")
    logger.debug("Using relative imports")
    
except ImportError:
    # Fall back to package imports (when running as module)
    from editor.src.api.config_manager import ConfigManager
    from editor.src.api.telemetry_collector import TelemetryCollector
    from editor.src.api.health_checker import HealthChecker
    from editor.src.security.rate_limiter import RateLimiter
    
    from editor.src.api.llm_service import LLMService
    from editor.src.ui.editor import EditorApp
    from editor.src.ui.syntax import apply_to_editor
    from editor.src.plugins import PluginManager
    from editor.src.utils.settings import get_settings
    
    logger = logging.getLogger("mcp_zero.editor.main")
    logger.debug("Using absolute imports")

# Ensure directories exist
def ensure_dirs():
    """Ensure required directories exist."""
    base_dir = os.path.join(os.path.expanduser("~"), ".mcp_zero", "editor")
    dirs = ["logs", "config", "telemetry", "cache", "plugins"]
    
    for dirname in dirs:
        os.makedirs(os.path.join(base_dir, dirname), exist_ok=True)
    
    return os.path.join(base_dir, "logs")

# Configure logging
log_dir = ensure_dirs()
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(os.path.join(log_dir, "editor.log"), mode='a')
    ]
)

logger = logging.getLogger("mcp_zero.editor")


class EditorApplication:
    """Main application class for MCP Zero Editor."""
    
    def __init__(self, file_to_open=None, config_path=None, verbose=False):
        """Initialize the editor application."""
        self.file_to_open = file_to_open
        
        # Set up logging level based on verbosity
        if verbose:
            logging.getLogger().setLevel(logging.DEBUG)
        
        # Base directories
        self.base_dir = os.path.join(os.path.expanduser("~"), ".mcp_zero", "editor")
        self.config_dir = os.path.join(self.base_dir, "config")
        self.cache_dir = os.path.join(self.base_dir, "cache")
        self.telemetry_dir = os.path.join(self.base_dir, "telemetry")
        
        # Components
        self.config = None
        self.telemetry = None
        self.health_checker = None
        self.rate_limiter = None
        self.llm_service = None
        self.plugin_manager = None
        self.settings = None
        self.editor_app = None
        
        # Config file path
        self.config_file = config_path if config_path else os.path.join(self.config_dir, "config.json")
        
        logger.info("MCP Zero Editor initializing")
    
    def initialize_components(self):
        """Initialize all editor components following offline-first pattern."""
        try:
            # Load settings first
            logger.info("Loading editor settings")
            self.settings = get_settings()  # Uses singleton pattern
            
            # Initialize config manager
            logger.info("Initializing configuration")
            self.config = ConfigManager(self.config_file, offline_first=True)
            
            # Initialize telemetry collector
            logger.info("Initializing telemetry")
            self.telemetry = TelemetryCollector(self.telemetry_dir, offline_first=True)
            self.telemetry.record("editor.start")
            
            # Initialize rate limiter
            logger.info("Initializing rate limiter")
            self.rate_limiter = RateLimiter(cache_dir=self.cache_dir, offline_first=True)
            
            # Initialize health checker
            logger.info("Initializing health checker")
            self.health_checker = HealthChecker(offline_first=True)
            
            # Register component health checks
            self.health_checker.register_check("config", self.config.is_healthy)
            self.health_checker.register_check("telemetry", self.telemetry.is_healthy)
            self.health_checker.register_check("rate_limiter", self.rate_limiter.is_healthy)
            
            # Start health checker
            self.health_checker.start()
            
            # Initialize LLM service
            logger.info("Initializing LLM service")
            self.llm_service = LLMService(
                cache_dir=self.cache_dir,
                config=self.config,
                telemetry=self.telemetry,
                rate_limiter=self.rate_limiter
            )
            
            # Add LLM health check
            self.health_checker.register_check("llm_service", self.llm_service.is_healthy)
            
            # Initialize plugin manager
            logger.info("Initializing plugin system")
            self.plugin_manager = PluginManager(health_checker=self.health_checker)
            
            return True
            
        except Exception as e:
            logger.error(f"Error initializing components: {str(e)}")
            return False
    
    def start_editor(self):
        """Start the editor UI."""
        try:
            logger.info("Starting editor UI")
            
            # Create editor instance
            self.editor_app = EditorApp(llm_service=self.llm_service)
            
            # Apply syntax highlighting
            apply_to_editor(self.editor_app.editor)
            
            # Load plugins
            logger.info("Loading editor plugins")
            self.plugin_manager.load_plugins(self.editor_app)
            
            # Schedule periodic telemetry flush
            def schedule_telemetry_flush():
                self.telemetry.flush()
                Timer(60, schedule_telemetry_flush).start()
            
            # Start telemetry flush timer
            Timer(60, schedule_telemetry_flush).start()
            
            # Open file if specified
            if self.file_to_open and os.path.exists(self.file_to_open):
                logger.info(f"Opening file: {self.file_to_open}")
                self.editor_app.open_file(self.file_to_open)
            
            # Run editor
            self.editor_app.run()
            
        except Exception as e:
            logger.error(f"Error starting editor: {str(e)}")
            self.cleanup()
    
    def cleanup(self):
        """Clean up resources on exit."""
        logger.info("Cleaning up resources")
        
        # Stop health checker
        if self.health_checker:
            self.health_checker.stop()
        
        # Shutdown plugins
        if self.plugin_manager:
            self.plugin_manager.shutdown()
        
        # Flush telemetry
        if self.telemetry:
            self.telemetry.flush()
        
        logger.info("MCP Zero Editor shutdown complete")
    
    def run(self):
        """Run the editor application."""
        if self.initialize_components():
            try:
                self.start_editor()
            finally:
                self.cleanup()
        else:
            logger.error("Failed to initialize editor components")


def main():
    """Main entry point for the MCP Zero Editor application."""
    # Parse command line arguments
    parser = argparse.ArgumentParser(description="MCP Zero Editor - A lightweight but powerful code editor")
    parser.add_argument("-f", "--file", help="File to open")
    parser.add_argument("-c", "--config", help="Path to configuration file")
    parser.add_argument("-v", "--verbose", action="store_true", help="Enable verbose logging")
    args = parser.parse_args()
    
    # Create and run editor application
    app = EditorApplication(
        file_to_open=args.file,
        config_path=args.config,
        verbose=args.verbose
    )
    
    # Run the application with proper offline-first resilience
    # Following the same pattern as Traffic Agent: only attempt connecting once
    # and permanently switch to local processing if services are unavailable
    app.run()


if __name__ == "__main__":
    main()
