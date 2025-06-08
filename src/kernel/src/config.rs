//! Configuration module for MCP-ZERO kernel
//!
//! Provides configuration management for the kernel, including loading from
//! YAML files and environment variables.

use std::path::{Path, PathBuf};
use serde::{Serialize, Deserialize};
use anyhow::{Result, Context};

/// Kernel configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct KernelConfig {
    /// Plugin directory path
    pub plugin_directory: PathBuf,
    
    /// Storage directory path
    pub storage_directory: PathBuf,
    
    /// Whether to enable tracing
    #[serde(default = "default_enable_tracing")]
    pub enable_tracing: bool,
    
    /// Whether to enable ZK-proofs
    #[serde(default)]
    pub enable_zk_proofs: bool,
    
    /// Maximum number of agents
    #[serde(default = "default_max_agents")]
    pub max_agents: usize,
    
    /// Maximum number of plugins per agent
    #[serde(default = "default_max_plugins_per_agent")]
    pub max_plugins_per_agent: usize,
    
    /// Hardware constraints
    #[serde(default)]
    pub hardware: HardwareConfig,
}

fn default_enable_tracing() -> bool {
    true
}

fn default_max_agents() -> usize {
    100
}

fn default_max_plugins_per_agent() -> usize {
    10
}

/// Hardware configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HardwareConfig {
    /// Maximum CPU usage as percentage (0-100)
    #[serde(default = "default_max_cpu")]
    pub max_cpu: f32,
    
    /// Maximum memory usage in MB
    #[serde(default = "default_max_memory")]
    pub max_memory: u32,
    
    /// Check interval in milliseconds
    #[serde(default = "default_check_interval")]
    pub check_interval: u64,
}

fn default_max_cpu() -> f32 {
    30.0 // 30% CPU limit
}

fn default_max_memory() -> u32 {
    800 // 800MB memory limit
}

fn default_check_interval() -> u64 {
    5000 // 5 seconds
}

impl Default for HardwareConfig {
    fn default() -> Self {
        Self {
            max_cpu: default_max_cpu(),
            max_memory: default_max_memory(),
            check_interval: default_check_interval(),
        }
    }
}

impl Default for KernelConfig {
    fn default() -> Self {
        Self {
            plugin_directory: PathBuf::from("./plugins"),
            storage_directory: PathBuf::from("./storage"),
            enable_tracing: default_enable_tracing(),
            enable_zk_proofs: false,
            max_agents: default_max_agents(),
            max_plugins_per_agent: default_max_plugins_per_agent(),
            hardware: HardwareConfig::default(),
        }
    }
}

impl KernelConfig {
    /// Load configuration from file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = std::fs::read_to_string(path.as_ref())
            .with_context(|| format!("Failed to read config file: {}", path.as_ref().display()))?;
        
        let config: Self = serde_yaml::from_str(&content)
            .with_context(|| "Failed to parse config file as YAML")?;
        
        Ok(config)
    }
    
    /// Save configuration to file
    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let yaml = serde_yaml::to_string(self)
            .with_context(|| "Failed to serialize config to YAML")?;
        
        std::fs::write(path.as_ref(), yaml)
            .with_context(|| format!("Failed to write config to file: {}", path.as_ref().display()))?;
        
        Ok(())
    }
    
    /// Load configuration from environment
    pub fn from_env() -> Self {
        let mut config = Self::default();
        
        // Override configuration from environment variables
        if let Ok(plugin_dir) = std::env::var("MCP_PLUGIN_DIRECTORY") {
            config.plugin_directory = PathBuf::from(plugin_dir);
        }
        
        if let Ok(storage_dir) = std::env::var("MCP_STORAGE_DIRECTORY") {
            config.storage_directory = PathBuf::from(storage_dir);
        }
        
        if let Ok(enable_tracing) = std::env::var("MCP_ENABLE_TRACING") {
            config.enable_tracing = enable_tracing.to_lowercase() == "true";
        }
        
        if let Ok(enable_zk) = std::env::var("MCP_ENABLE_ZK_PROOFS") {
            config.enable_zk_proofs = enable_zk.to_lowercase() == "true";
        }
        
        if let Ok(var) = std::env::var("MCP_MAX_AGENTS") {
            if let Ok(max_agents) = var.parse() {
                config.max_agents = max_agents;
            }
        }
        
        if let Ok(var) = std::env::var("MCP_MAX_PLUGINS_PER_AGENT") {
            if let Ok(max_plugins) = var.parse() {
                config.max_plugins_per_agent = max_plugins;
            }
        }
        
        // Hardware constraints
        if let Ok(var) = std::env::var("MCP_MAX_CPU") {
            if let Ok(max_cpu) = var.parse() {
                config.hardware.max_cpu = max_cpu;
            }
        }
        
        if let Ok(var) = std::env::var("MCP_MAX_MEMORY") {
            if let Ok(max_memory) = var.parse() {
                config.hardware.max_memory = max_memory;
            }
        }
        
        config
    }
}
