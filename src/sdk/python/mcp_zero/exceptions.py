"""
MCP-ZERO Exception Module

Defines exceptions used throughout the MCP-ZERO SDK.
"""

class MCPError(Exception):
    """Base exception for all MCP-ZERO errors."""
    pass


class ConnectionError(MCPError):
    """Error connecting to MCP-ZERO infrastructure."""
    pass


class ResourceError(MCPError):
    """Error related to resource constraints."""
    pass


class AgentError(MCPError):
    """Error related to agent operations."""
    pass


class PluginError(MCPError):
    """Error related to plugin operations."""
    pass


class ExecutionError(MCPError):
    """Error during intent execution."""
    pass


class EthicalViolationError(MCPError):
    """Error when an operation violates ethical constraints."""
    pass


class TraceError(MCPError):
    """Error related to execution tracing."""
    pass


class StorageError(MCPError):
    """Error related to agent storage."""
    pass


class ConfigError(MCPError):
    """Error related to configuration."""
    pass


class ValidationError(MCPError):
    """Error during input validation."""
    pass


class IntegrityError(MCPError):
    """Error related to cryptographic integrity."""
    pass


class SecurityError(MCPError):
    """Error related to security constraints."""
    pass
