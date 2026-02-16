use anyhow::Error;
use thiserror::Error;

#[derive(Debug, Error)]
pub enum KernelError {
    #[error("Agent not found: {0}")]
    AgentNotFound(String),
    
    #[error("Plugin not found: {0}")]
    PluginNotFound(String),
    
    #[error("Plugin incompatible: {0}")]
    PluginIncompatible(String),
    
    #[error("Execution failed: {0}")]
    ExecutionFailed(String),
    
    #[error("Ethical constraint violated: {0}")]
    EthicalConstraintViolated(String),
    
    #[error("Storage error: {0}")]
    StorageError(String),
    
    #[error("Trace error: {0}")]
    TraceError(String),
    
    #[error("Hardware constraints exceeded: {0}")]
    HardwareConstraintsExceeded(String),
    
    #[error("Internal error: {0}")]
    Internal(String),
}

// Implement From<anyhow::Error> for KernelError for easier error conversion
impl From<anyhow::Error> for KernelError {
    fn from(error: Error) -> Self {
        KernelError::Internal(error.to_string())
    }
}

// Additional From implementations for common error types
impl From<std::io::Error> for KernelError {
    fn from(error: std::io::Error) -> Self {
        KernelError::StorageError(error.to_string())
    }
}

impl From<serde_json::Error> for KernelError {
    fn from(error: serde_json::Error) -> Self {
        KernelError::Internal(format!("JSON error: {}", error))
    }
}
