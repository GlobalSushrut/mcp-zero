"""
MCP-ZERO SDK: Minimal Computing Protocol for AI Agents

This SDK provides the developer interface to interact with MCP-ZERO,
a production-grade AI agent infrastructure designed for 100+ year
sustainability with minimal resource usage.

Core Design Principles:
    - Resource Constraints: <27% CPU, <827MB RAM
    - Immutable Core: All upgrades via plugins
    - Ethical Governance: Built-in policy enforcement
    - Cryptographic Integrity: Secure operations
    - Sustainability: Designed for 100+ year lifespan
"""

from .version import __version__
from .agent import Agent
from .plugin import Plugin, PluginRegistry
from .exceptions import (
    MCPError, 
    ResourceLimitError,
    EthicalPolicyViolation,
    PluginError
)
from .monitoring import ResourceMonitor

__all__ = [
    'Agent',
    'Plugin',
    'PluginRegistry',
    'ResourceMonitor',
    'MCPError',
    'ResourceLimitError',
    'EthicalPolicyViolation',
    'PluginError',
    '__version__',
]
