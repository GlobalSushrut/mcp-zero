//! Agent module for MCP-ZERO kernel
//!
//! Provides agent management functionality including creation, state management,
//! plugin attachment, and execution.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use anyhow::{Result, Context, anyhow};
use blake3;
use serde::{Serialize, Deserialize};

use crate::plugin::{Plugin, PluginId};

/// Agent ID type - based on Poseidon hash of pubkey + intent tree
pub type AgentId = String;

/// Status of an agent
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AgentStatus {
    /// Agent is active and ready
    Active,
    /// Agent was recovered from storage
    Recovered,
    /// Agent is paused
    Paused,
    /// Agent is terminated
    Terminated,
}

/// Agent configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentConfig {
    /// Name of the agent
    pub name: String,
    
    /// Entry plugin for the agent
    pub entry: Option<String>,
    
    /// Available intents
    pub intents: Vec<String>,
    
    /// Hardware constraints
    #[serde(default)]
    pub hm: HardwareConstraints,
    
    /// Additional metadata
    #[serde(default)]
    pub metadata: HashMap<String, serde_json::Value>,
}

impl Default for AgentConfig {
    fn default() -> Self {
        Self {
            name: "default_agent".to_string(),
            entry: None,
            intents: vec![],
            hm: HardwareConstraints::default(),
            metadata: HashMap::new(),
        }
    }
}

/// Hardware constraints for an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareConstraints {
    /// CPU usage cap in percentage
    pub cpu: Option<f32>,
    
    /// RAM usage cap in MB
    pub ram: Option<u32>,
}

impl Default for HardwareConstraints {
    fn default() -> Self {
        Self {
            cpu: Some(10.0),  // Default 10% CPU limit
            ram: Some(100),   // Default 100MB RAM limit
        }
    }
}

/// Agent implementation
#[derive(Debug, Serialize, Deserialize)]
pub struct Agent {
    /// Agent ID
    id: AgentId,
    
    /// Agent configuration
    config: AgentConfig,
    
    /// Current status
    status: AgentStatus,
    
    /// Attached plugins
    #[serde(skip)]
    plugins: Arc<RwLock<HashMap<PluginId, Arc<Plugin>>>>,
    
    /// Agent state storage for persistence
    state: HashMap<String, serde_json::Value>,
    
    /// Creation timestamp
    created_at: i64,
    
    /// Last updated timestamp
    updated_at: i64,
}

impl Agent {
    /// Create a new Agent instance
    pub fn new(id: AgentId, config: AgentConfig) -> Self {
        let now = chrono::Utc::now().timestamp();
        
        Self {
            id,
            config,
            status: AgentStatus::Active,
            plugins: Arc::new(RwLock::new(HashMap::new())),
            state: HashMap::new(),
            created_at: now,
            updated_at: now,
        }
    }
    
    /// Get agent ID
    pub fn id(&self) -> &AgentId {
        &self.id
    }
    
    /// Get agent configuration
    pub fn config(&self) -> &AgentConfig {
        &self.config
    }
    
    /// Get agent status
    pub fn status(&self) -> AgentStatus {
        self.status
    }
    
    /// Set agent status
    pub fn set_status(&mut self, status: AgentStatus) {
        self.status = status;
        self.updated_at = chrono::Utc::now().timestamp();
    }
    
    /// Attach a plugin to the agent
    pub fn attach_plugin(&self, plugin_id: &PluginId) -> Result<()> {
        let mut plugins = self.plugins.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on plugins"))?;
        
        // Plugin instance will be loaded later when executed
        plugins.insert(plugin_id.clone(), Arc::new(Plugin::placeholder(plugin_id)));
        
        Ok(())
    }
    
    /// Execute an intent
    pub fn execute(&self, intent: &str) -> Result<serde_json::Value> {
        // Check if the agent is active
        match self.status {
            AgentStatus::Active | AgentStatus::Recovered => {},
            _ => return Err(anyhow!("Agent is not active")),
        }
        
        // Check if the intent is allowed
        if !self.config.intents.contains(&intent.to_string()) {
            return Err(anyhow!("Intent '{}' not allowed for this agent", intent));
        }
        
        // Get the entry plugin
        let entry_plugin = match &self.config.entry {
            Some(entry) => {
                let plugins = self.plugins.read()
                    .map_err(|_| anyhow!("Failed to acquire read lock on plugins"))?;
                
                plugins.get(entry).cloned()
                    .ok_or_else(|| anyhow!("Entry plugin '{}' not attached", entry))
            },
            None => Err(anyhow!("No entry plugin defined for agent")),
        }?;
        
        // Execute intent through the entry plugin
        let result = entry_plugin.execute(intent, self.id(), &self.state)?;
        
        Ok(result)
    }
    
    /// Get agent state
    pub fn state(&self) -> &HashMap<String, serde_json::Value> {
        &self.state
    }
    
    /// Set agent state value
    pub fn set_state(&mut self, key: &str, value: serde_json::Value) {
        self.state.insert(key.to_string(), value);
        self.updated_at = chrono::Utc::now().timestamp();
    }
}

/// Generate an agent ID from config
pub fn generate_agent_id(config: &AgentConfig) -> AgentId {
    // Serialize the config to JSON for hashing
    let config_json = serde_json::to_string(config).unwrap_or_default();
    
    // Generate a deterministic hash using BLAKE3 (faster than SHA3 for this purpose)
    let hash = blake3::hash(config_json.as_bytes());
    
    // Format as hex string for readability
    format!("agent_{}", hash.to_hex().chars().take(16).collect::<String>())
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_agent_id_generation() {
        let config = AgentConfig {
            name: "test_agent".to_string(),
            entry: Some("test_plugin".to_string()),
            intents: vec!["greet".to_string()],
            hm: HardwareConstraints::default(),
            metadata: HashMap::new(),
        };
        
        let id = generate_agent_id(&config);
        assert!(id.starts_with("agent_"));
        assert_eq!(id.len(), 22); // "agent_" + 16 hex chars
    }
}
