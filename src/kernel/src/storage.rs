//! Storage module for MCP-ZERO kernel
//!
//! Provides agent state persistence, optimized for minimal memory usage
//! and disk footprint.

use std::path::{Path, PathBuf};
use std::fs;
use std::sync::OnceLock;
use anyhow::{Result, Context, anyhow};

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

// Global storage using safe OnceLock (no unsafe)

/// Global storage instance
static STORAGE: OnceLock<StorageManager> = OnceLock::new();

/// Initialize global storage
pub fn init_storage<P: AsRef<Path>>(storage_dir: P) -> Result<()> {
    let storage = StorageManager::new(storage_dir)?;
    STORAGE.set(storage)
        .map_err(|_| anyhow!("Storage already initialized"))?;
    Ok(())
}

fn get_storage() -> Result<&'static StorageManager> {
    STORAGE.get().ok_or_else(|| anyhow!("Storage not initialized"))
}

/// Save agent to storage
pub fn save_agent(agent_id: &AgentId, agent: &Agent) -> Result<()> {
    get_storage()?.save_agent(agent_id, agent)
}

/// Load agent from storage
pub fn load_agent(agent_id: &AgentId) -> Result<Agent> {
    get_storage()?.load_agent(agent_id)
}

/// List all agents in storage
pub fn list_agents() -> Result<Vec<AgentId>> {
    get_storage()?.list_agents()
}

/// Delete agent from storage
pub fn delete_agent(agent_id: &AgentId) -> Result<()> {
    get_storage()?.delete_agent(agent_id)
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::agent::{Agent, AgentConfig};
    use std::fs;
    
    use std::sync::atomic::{AtomicU64, Ordering};
    static TEST_COUNTER: AtomicU64 = AtomicU64::new(0);
    
    fn temp_storage() -> (StorageManager, PathBuf) {
        let n = TEST_COUNTER.fetch_add(1, Ordering::SeqCst);
        let dir = std::env::temp_dir().join(format!(
            "mcp_test_{}_{}", std::process::id(), n
        ));
        let _ = fs::remove_dir_all(&dir);
        let mgr = StorageManager::new(&dir).expect("create storage");
        (mgr, dir)
    }
    
    #[test]
    fn test_storage_save_load_roundtrip() {
        let (mgr, dir) = temp_storage();
        let agent_id = "agent_test_001".to_string();
        let mut agent = Agent::new(agent_id.clone(), AgentConfig::default());
        agent.set_state("sensor", serde_json::json!(42.5));
        
        mgr.save_agent(&agent_id, &agent).expect("save");
        let loaded = mgr.load_agent(&agent_id).expect("load");
        
        assert_eq!(loaded.id(), &agent_id);
        assert_eq!(loaded.state()["sensor"], serde_json::json!(42.5));
        
        let _ = fs::remove_dir_all(&dir);
    }
    
    #[test]
    fn test_storage_list_agents() {
        let (mgr, dir) = temp_storage();
        
        assert!(mgr.list_agents().unwrap().is_empty());
        
        for i in 0..3 {
            let id = format!("agent_{}", i);
            let agent = Agent::new(id.clone(), AgentConfig::default());
            mgr.save_agent(&id, &agent).unwrap();
        }
        
        let mut agents = mgr.list_agents().unwrap();
        agents.sort();
        assert_eq!(agents.len(), 3);
        assert_eq!(agents, vec!["agent_0", "agent_1", "agent_2"]);
        
        let _ = fs::remove_dir_all(&dir);
    }
    
    #[test]
    fn test_storage_delete_agent() {
        let (mgr, dir) = temp_storage();
        let agent_id = "agent_del".to_string();
        let agent = Agent::new(agent_id.clone(), AgentConfig::default());
        
        mgr.save_agent(&agent_id, &agent).unwrap();
        assert_eq!(mgr.list_agents().unwrap().len(), 1);
        
        mgr.delete_agent(&agent_id).unwrap();
        assert!(mgr.list_agents().unwrap().is_empty());
        
        let _ = fs::remove_dir_all(&dir);
    }
    
    #[test]
    fn test_storage_load_missing_agent() {
        let (mgr, dir) = temp_storage();
        let result = mgr.load_agent(&"nonexistent".to_string());
        assert!(result.is_err());
        let _ = fs::remove_dir_all(&dir);
    }
    
    #[test]
    fn test_storage_delete_missing_agent() {
        let (mgr, dir) = temp_storage();
        let result = mgr.delete_agent(&"nonexistent".to_string());
        assert!(result.is_err());
        let _ = fs::remove_dir_all(&dir);
    }
    
    #[test]
    fn test_storage_overwrite_agent() {
        let (mgr, dir) = temp_storage();
        let agent_id = "agent_ow".to_string();
        
        let mut agent = Agent::new(agent_id.clone(), AgentConfig::default());
        agent.set_state("v", serde_json::json!(1));
        mgr.save_agent(&agent_id, &agent).unwrap();
        
        agent.set_state("v", serde_json::json!(2));
        mgr.save_agent(&agent_id, &agent).unwrap();
        
        let loaded = mgr.load_agent(&agent_id).unwrap();
        assert_eq!(loaded.state()["v"], serde_json::json!(2));
        
        let _ = fs::remove_dir_all(&dir);
    }
}
