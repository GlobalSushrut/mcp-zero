//! Storage module for MCP-ZERO kernel
//!
//! Provides agent state persistence, optimized for minimal memory usage
//! and disk footprint.

use std::path::{Path, PathBuf};
use std::fs;
use std::collections::HashMap;
use anyhow::{Result, Context, anyhow};
use serde::{Serialize, Deserialize};

use crate::agent::{Agent, AgentId};

/// Storage manager for agent persistence
#[derive(Debug)]
pub struct StorageManager {
    /// Storage directory
    storage_dir: PathBuf,
}

impl StorageManager {
    /// Create a new StorageManager
    pub fn new<P: AsRef<Path>>(storage_dir: P) -> Result<Self> {
        let dir = storage_dir.as_ref().to_path_buf();
        
        // Create directory if it doesn't exist
        if !dir.exists() {
            fs::create_dir_all(&dir)
                .with_context(|| format!("Failed to create storage directory: {}", dir.display()))?;
        }
        
        Ok(Self { storage_dir: dir })
    }
    
    /// Save agent to storage
    pub fn save_agent(&self, agent_id: &AgentId, agent: &Agent) -> Result<()> {
        // Create agent directory
        let agent_dir = self.storage_dir.join(agent_id);
        if !agent_dir.exists() {
            fs::create_dir_all(&agent_dir)
                .with_context(|| format!("Failed to create agent directory: {}", agent_dir.display()))?;
        }
        
        // Serialize agent
        let agent_data = serde_json::to_string(agent)
            .with_context(|| format!("Failed to serialize agent: {}", agent_id))?;
        
        // Write to file
        let agent_file = agent_dir.join("agent.json");
        fs::write(&agent_file, agent_data)
            .with_context(|| format!("Failed to write agent data to file: {}", agent_file.display()))?;
        
        Ok(())
    }
    
    /// Load agent from storage
    pub fn load_agent(&self, agent_id: &AgentId) -> Result<Agent> {
        // Get agent file
        let agent_file = self.storage_dir.join(agent_id).join("agent.json");
        
        // Check if file exists
        if !agent_file.exists() {
            return Err(anyhow!("Agent not found in storage: {}", agent_id));
        }
        
        // Read file
        let agent_data = fs::read_to_string(&agent_file)
            .with_context(|| format!("Failed to read agent data from file: {}", agent_file.display()))?;
        
        // Deserialize agent
        let agent: Agent = serde_json::from_str(&agent_data)
            .with_context(|| format!("Failed to deserialize agent: {}", agent_id))?;
        
        Ok(agent)
    }
    
    /// List all agents in storage
    pub fn list_agents(&self) -> Result<Vec<AgentId>> {
        let mut agents = Vec::new();
        
        // Check if storage directory exists
        if !self.storage_dir.exists() {
            return Ok(agents);
        }
        
        // Read directory
        let entries = fs::read_dir(&self.storage_dir)
            .with_context(|| format!("Failed to read storage directory: {}", self.storage_dir.display()))?;
        
        // Process entries
        for entry in entries {
            let entry = entry?;
            let path = entry.path();
            
            // Check if it's a directory
            if path.is_dir() {
                // Check if agent.json exists
                let agent_file = path.join("agent.json");
                if agent_file.exists() {
                    // Add agent ID
                    if let Some(agent_id) = path.file_name().and_then(|n| n.to_str()) {
                        agents.push(agent_id.to_string());
                    }
                }
            }
        }
        
        Ok(agents)
    }
    
    /// Delete agent from storage
    pub fn delete_agent(&self, agent_id: &AgentId) -> Result<()> {
        // Get agent directory
        let agent_dir = self.storage_dir.join(agent_id);
        
        // Check if directory exists
        if !agent_dir.exists() {
            return Err(anyhow!("Agent not found in storage: {}", agent_id));
        }
        
        // Remove directory recursively
        fs::remove_dir_all(&agent_dir)
            .with_context(|| format!("Failed to delete agent directory: {}", agent_dir.display()))?;
        
        Ok(())
    }
}

// Global storage functions for easier access

/// Global storage instance
static mut STORAGE: Option<StorageManager> = None;

/// Initialize global storage
pub fn init_storage<P: AsRef<Path>>(storage_dir: P) -> Result<()> {
    let storage = StorageManager::new(storage_dir)?;
    
    // Set global storage
    unsafe {
        STORAGE = Some(storage);
    }
    
    Ok(())
}

/// Save agent to storage
pub fn save_agent(agent_id: &AgentId, agent: &Agent) -> Result<()> {
    // Get global storage
    let storage = unsafe {
        match &STORAGE {
            Some(s) => s,
            None => return Err(anyhow!("Storage not initialized")),
        }
    };
    
    storage.save_agent(agent_id, agent)
}

/// Load agent from storage
pub fn load_agent(agent_id: &AgentId) -> Result<Agent> {
    // Get global storage
    let storage = unsafe {
        match &STORAGE {
            Some(s) => s,
            None => return Err(anyhow!("Storage not initialized")),
        }
    };
    
    storage.load_agent(agent_id)
}

/// List all agents in storage
pub fn list_agents() -> Result<Vec<AgentId>> {
    // Get global storage
    let storage = unsafe {
        match &STORAGE {
            Some(s) => s,
            None => return Err(anyhow!("Storage not initialized")),
        }
    };
    
    storage.list_agents()
}

/// Delete agent from storage
pub fn delete_agent(agent_id: &AgentId) -> Result<()> {
    // Get global storage
    let storage = unsafe {
        match &STORAGE {
            Some(s) => s,
            None => return Err(anyhow!("Storage not initialized")),
        }
    };
    
    storage.delete_agent(agent_id)
}
