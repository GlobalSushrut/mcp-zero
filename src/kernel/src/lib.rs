//! MCP-ZERO Kernel - Core Runtime
//! 
//! An ultra-lightweight, blockchain-inspired AI infrastructure orchestration layer
//! designed to operate under 1GB RAM and <30% of an i3 CPU.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use anyhow::{Result, Context};
use thiserror::Error;
use dashmap::DashMap;
use serde::{Serialize, Deserialize};

mod agent;
mod plugin;
mod trace;
mod ethical;
mod config;
mod storage;

pub use agent::{Agent, AgentId, AgentConfig, AgentStatus};
pub use plugin::{Plugin, PluginId, PluginManager};
pub use trace::PoseidonTracer;
pub use ethical::EthicalBinaryTree;

/// Error types for the MCP-ZERO kernel
#[derive(Error, Debug)]
pub enum KernelError {
    #[error("Agent not found: {0}")]
    AgentNotFound(String),
    
    #[error("Plugin not found: {0}")]
    PluginNotFound(String),
    
    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),
    
    #[error("Permission denied: {0}")]
    PermissionDenied(String),
    
    #[error("Invalid configuration: {0}")]
    InvalidConfiguration(String),
    
    #[error("Storage error: {0}")]
    StorageError(String),
    
    #[error("Execution error: {0}")]
    ExecutionError(String),
    
    #[error("Ethical constraint violated: {0}")]
    EthicalConstraintViolated(String),
    
    #[error("Trace error: {0}")]
    TraceError(String),
    
    #[error("Internal error: {0}")]
    Internal(String),
}

impl From<anyhow::Error> for KernelError {
    fn from(error: anyhow::Error) -> Self {
        KernelError::Internal(error.to_string())
    }
}

/// Core MCPKernel structure representing the main runtime
pub struct MCPKernel {
    /// Manages WASM plugins
    plugin_manager: PluginManager,
    
    /// Traces execution paths with Poseidon hashes
    trace_engine: PoseidonTracer,
    
    /// Stores agent data
    agent_store: DashMap<AgentId, Agent>,
    
    /// Manages ethical decision tree
    ethical_engine: EthicalBinaryTree,
    
    /// Configuration
    config: config::KernelConfig,
}

impl MCPKernel {
    /// Create a new MCPKernel instance with default configuration
    pub fn new() -> Self {
        let config = config::KernelConfig::default();
        Self::with_config(config)
    }
    
    /// Create a new MCPKernel instance with custom configuration
    pub fn with_config(config: config::KernelConfig) -> Self {
        // Initialize tracing
        if config.enable_tracing {
            tracing_subscriber::fmt::init();
        }
        
        MCPKernel {
            plugin_manager: PluginManager::new(config.plugin_directory.clone()),
            trace_engine: PoseidonTracer::new(),
            agent_store: DashMap::new(),
            ethical_engine: EthicalBinaryTree::new(),
            config,
        }
    }
    
    /// Spawns a new agent with the given configuration
    pub fn spawn_agent(&self, config: AgentConfig) -> Result<AgentId, KernelError> {
        // Create agent ID using Poseidon hash
        let agent_id = agent::generate_agent_id(&config);
        
        // Check ethical constraints for this spawn
        if let Err(reason) = self.ethical_engine.validate_spawn(&config) {
            return Err(KernelError::EthicalConstraintViolated(reason.to_string()));
        }
        
        // Create agent instance
        let agent = Agent::new(agent_id.clone(), config);
        
        // Store agent
        self.agent_store.insert(agent_id.clone(), agent);
        
        // Trace agent creation
        self.trace_engine.record_event(
            &agent_id,
            "agent.spawn",
            &serde_json::json!({"timestamp": chrono::Utc::now().timestamp()})
        )
        .map_err(|e| KernelError::TraceError(e.to_string()))?;
        
        tracing::info!("Agent spawned: {}", agent_id);
        Ok(agent_id)
    }
    
    /// Attaches a plugin to an agent
    pub fn attach_plugin(&self, agent_id: &AgentId, plugin_id: &PluginId) -> Result<(), KernelError> {
        // Verify agent exists
        let agent = self.agent_store.get(agent_id)
            .ok_or_else(|| KernelError::AgentNotFound(agent_id.clone()))?;
        
        // Load plugin
        let plugin = self.plugin_manager.load_plugin(plugin_id)
            .map_err(|e| KernelError::PluginNotFound(e.to_string()))?;
        
        // Check ethical constraints for plugin attachment
        if let Err(reason) = self.ethical_engine.validate_plugin(&plugin) {
            return Err(KernelError::EthicalConstraintViolated(reason.to_string()));
        }
        
        // Attach plugin to agent
        agent.attach_plugin(plugin_id)
            .map_err(|e| KernelError::ExecutionError(e.to_string()))?;
        
        // Trace plugin attachment
        self.trace_engine.record_event(
            agent_id,
            "agent.attach_plugin",
            &serde_json::json!({
                "plugin_id": plugin_id,
                "timestamp": chrono::Utc::now().timestamp()
            })
        )
        .map_err(|e| KernelError::TraceError(e.to_string()))?;
        
        tracing::info!("Plugin {} attached to agent {}", plugin_id, agent_id);
        Ok(())
    }
    
    /// Executes an intent for an agent
    pub fn execute(&self, agent_id: &AgentId, intent: &str) -> Result<serde_json::Value, KernelError> {
        // Get agent
        let agent = self.agent_store.get(agent_id)
            .ok_or_else(|| KernelError::AgentNotFound(agent_id.clone()))?;
        
        // Check ethical constraints for this execution
        if let Err(reason) = self.ethical_engine.validate_execution(agent_id, intent) {
            return Err(KernelError::EthicalConstraintViolated(reason.to_string()));
        }
        
        // Begin execution trace
        let trace_id = self.trace_engine.begin_trace(agent_id, intent)
            .map_err(|e| KernelError::TraceError(e.to_string()))?;
        
        // Execute the intent
        let result = agent.execute(intent)
            .map_err(|e| KernelError::ExecutionError(e.to_string()));
        
        // Complete trace
        match &result {
            Ok(value) => {
                self.trace_engine.end_trace(&trace_id, true, Some(value))
                    .map_err(|e| KernelError::TraceError(e.to_string()))?;
            },
            Err(e) => {
                self.trace_engine.end_trace(
                    &trace_id, 
                    false, 
                    Some(&serde_json::json!({"error": e.to_string()}))
                ).map_err(|e| KernelError::TraceError(e.to_string()))?;
            }
        }
        
        result
    }
    
    /// Recovers an agent from storage
    pub fn recover(&self, agent_id: &AgentId) -> Result<AgentStatus, KernelError> {
        // Check if agent is already loaded
        if self.agent_store.contains_key(agent_id) {
            return Ok(AgentStatus::Active);
        }
        
        // Attempt to load from storage
        match storage::load_agent(agent_id) {
            Ok(agent) => {
                // Check ethical constraints
                if let Err(reason) = self.ethical_engine.validate_recovery(agent_id) {
                    return Err(KernelError::EthicalConstraintViolated(reason.to_string()));
                }
                
                // Store the recovered agent
                self.agent_store.insert(agent_id.clone(), agent);
                
                // Trace recovery
                self.trace_engine.record_event(
                    agent_id,
                    "agent.recover",
                    &serde_json::json!({
                        "timestamp": chrono::Utc::now().timestamp(),
                        "status": "success"
                    })
                ).map_err(|e| KernelError::TraceError(e.to_string()))?;
                
                tracing::info!("Agent recovered: {}", agent_id);
                Ok(AgentStatus::Recovered)
            },
            Err(e) => {
                tracing::error!("Failed to recover agent {}: {}", agent_id, e);
                Err(KernelError::StorageError(format!("Failed to recover agent: {}", e)))
            }
        }
    }
    
    /// Takes a snapshot of an agent's state
    pub fn snapshot(&self, agent_id: &AgentId) -> Result<(), KernelError> {
        // Get agent
        let agent = self.agent_store.get(agent_id)
            .ok_or_else(|| KernelError::AgentNotFound(agent_id.clone()))?;
        
        // Take snapshot
        storage::save_agent(agent_id, &agent)
            .map_err(|e| KernelError::StorageError(format!("Failed to save snapshot: {}", e)))?;
        
        // Trace snapshot
        self.trace_engine.record_event(
            agent_id,
            "agent.snapshot",
            &serde_json::json!({
                "timestamp": chrono::Utc::now().timestamp()
            })
        ).map_err(|e| KernelError::TraceError(e.to_string()))?;
        
        tracing::info!("Agent snapshot taken: {}", agent_id);
        Ok(())
    }
}

impl Drop for MCPKernel {
    fn drop(&mut self) {
        // Attempt to snapshot all agents before shutdown
        for agent_ref in self.agent_store.iter() {
            let agent_id = agent_ref.key();
            if let Err(e) = storage::save_agent(agent_id, &agent_ref.value()) {
                tracing::error!("Failed to snapshot agent {} during shutdown: {}", agent_id, e);
            }
        }
        
        tracing::info!("MCP Kernel shutting down");
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_kernel_init() {
        let kernel = MCPKernel::new();
        assert!(kernel.agent_store.is_empty());
    }
}
