"""
MCP-ZERO Logging Utilities

Logging configuration for the MCP-ZERO SDK.
"""

import os
import sys
import logging
from typing import Optional, Dict, Any, Union


def setup_logger(
    level: Union[int, str] = "INFO",
    log_file: Optional[str] = None,
    log_format: Optional[str] = None,
    name: str = "mcp_zero"
) -> logging.Logger:
    """
    Setup the MCP-ZERO logger.
    
    Args:
        level: Logging level (string or int).
        log_file: Optional file path for logging.
        log_format: Optional log format string.
        name: Logger name.
        
    Returns:
        Configured logger.
    """
    # Convert string level to int if needed
    if isinstance(level, str):
        level = getattr(logging, level.upper(), logging.INFO)
    
    # Create logger
    logger = logging.getLogger(name)
    logger.setLevel(level)
    
    # Clear existing handlers
    if logger.hasHandlers():
        logger.handlers.clear()
    
    # Default format
    if log_format is None:
        log_format = "[%(asctime)s] [%(levelname)s] [%(name)s] %(message)s"
    
    formatter = logging.Formatter(log_format)
    
    # Console handler
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setFormatter(formatter)
    logger.addHandler(console_handler)
    
    # File handler if specified
    if log_file:
        # Create directory if it doesn't exist
        log_dir = os.path.dirname(os.path.abspath(log_file))
        os.makedirs(log_dir, exist_ok=True)
        
        file_handler = logging.FileHandler(log_file)
        file_handler.setFormatter(formatter)
        logger.addHandler(file_handler)
    
    return logger


def get_log_level(level_str: str) -> int:
    """
    Convert string log level to logging constant.
    
    Args:
        level_str: Log level string.
        
    Returns:
        Logging level constant.
    """
    level_map = {
        "debug": logging.DEBUG,
        "info": logging.INFO,
        "warning": logging.WARNING,
        "warn": logging.WARNING,
        "error": logging.ERROR,
        "critical": logging.CRITICAL,
    }
    
    return level_map.get(level_str.lower(), logging.INFO)


class LogCapture:
    """
    Capture logs for testing or debugging.
    
    Usage:
        with LogCapture() as logs:
            # do something
            print(logs.records)  # access captured records
    """
    
    def __init__(self, logger_name: str = "mcp_zero", level: int = logging.DEBUG):
        self.logger_name = logger_name
        self.level = level
        self.records = []
        self.handler = None
    
    def __enter__(self):
        logger = logging.getLogger(self.logger_name)
        
        class Handler(logging.Handler):
            def __init__(self, records):
                super().__init__()
                self.records = records
            
            def emit(self, record):
                self.records.append(record)
        
        self.handler = Handler(self.records)
        self.handler.setLevel(self.level)
        logger.addHandler(self.handler)
        
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        if self.handler:
            logger = logging.getLogger(self.logger_name)
            logger.removeHandler(self.handler)
            self.handler = None
    
    def get_messages(self) -> list:
        """Get plain text messages from captured records."""
        return [record.getMessage() for record in self.records]
    
    def get_formatted(self) -> list:
        """Get formatted messages from captured records."""
        formatter = logging.Formatter("[%(levelname)s] %(message)s")
        return [formatter.format(record) for record in self.records]
