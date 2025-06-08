"""
MCP-ZERO SDK: Exceptions Module

This module defines the exception classes used in the MCP-ZERO SDK.
"""


class MCPError(Exception):
    """Base exception class for all MCP-ZERO errors"""
    pass


class ResourceLimitError(MCPError):
    """Raised when an operation would exceed resource constraints"""
    pass


class EthicalPolicyViolation(MCPError):
    """Raised when an operation would violate ethical policies"""
    pass


class PluginError(MCPError):
    """Raised when there is an error with a plugin"""
    pass


class CryptographicError(MCPError):
    """Raised when a cryptographic operation fails"""
    pass


class APIError(MCPError):
    """Raised when an API request fails"""
    
    def __init__(self, message, status_code=None, response=None):
        self.status_code = status_code
        self.response = response
        super().__init__(message)


class AuthenticationError(APIError):
    """Raised when authentication fails"""
    pass


class AgreementError(MCPError):
    """Raised when an agreement operation fails"""
    pass


class SnapshotError(MCPError):
    """Raised when a snapshot operation fails"""
    pass
