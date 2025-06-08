"""MCP-ZERO Python SDK

Provides a client interface for interacting with the MCP-ZERO AI Agent Infrastructure.

MCP-ZERO is a foundational infrastructure for AI agents with an immutable
core designed for 100+ year sustainability, adhering to strict hardware
constraints while providing ethical governance, security, and traceability.
"""

__version__ = "0.1.0"

# Core client
from .client import MCPClient

# Agent lifecycle management
from .agents import Agent, AgentConfig, AgentStatus, HardwareConstraints

# Plugin management
from .plugins import Plugin, PluginCapabilities

# Zero Knowledge Proofs
from .zkp import ZKVerifier, TraceManager

# Exceptions
from .exceptions import (
    MCPError, ConnectionError, AgentError, PluginError, 
    ExecutionError, EthicalViolationError, TraceError, 
    StorageError, ConfigError, ValidationError, IntegrityError, 
    SecurityError, ResourceError
)

# Utilities
from .utils.config import ClientConfig, load_config
from .utils.logging import setup_logger

# Public API for the entire package
__all__ = [
    # Main client
    "MCPClient",
    
    # Agent classes
    "Agent",
    "AgentConfig",
    "AgentStatus",
    "HardwareConstraints",
    
    # Plugin classes
    "Plugin",
    "PluginCapabilities",
    
    # ZKP/Tracing
    "ZKVerifier",
    "TraceManager",
    
    # Utils
    "ClientConfig",
    "load_config",
    "setup_logger",
    
    # Exceptions
    "MCPError",
    "ConnectionError",
    "AgentError",
    "PluginError",
    "ExecutionError",
    "EthicalViolationError",
    "TraceError",
    "StorageError",
    "ConfigError",
    "ValidationError",
    "IntegrityError",
    "SecurityError",
    "ResourceError",
]
