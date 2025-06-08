//! Configuration module for MCP-ZERO Hardware Manager
//!
//! Defines configuration structures and loading mechanisms for the hardware manager.

use std::path::{Path, PathBuf};
use serde::{Serialize, Deserialize};
use anyhow::{Result, Context};

/// Hardware Manager configuration
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct HMConfig {
    /// Maximum CPU percentage (0-100)
    #[serde(default = "default_max_cpu")]
    pub max_cpu_percent: f32,
    
    /// Maximum memory in MB
    #[serde(default = "default_max_memory")]
    pub max_memory_mb: u32,
    
    /// Refresh interval in milliseconds
    #[serde(default = "default_refresh_interval")]
    pub refresh_interval_ms: u64,
    
    /// Alert threshold as percentage of limit (0.0-1.0)
    #[serde(default = "default_alert_threshold")]
    pub alert_threshold: f32,
    
    /// Whether to enable graceful degradation
    #[serde(default)]
    pub enable_graceful_degradation: bool,
    
    /// Whether to enable detailed metrics
    #[serde(default)]
    pub enable_detailed_metrics: bool,
    
    /// History retention time in minutes
    #[serde(default = "default_history_minutes")]
    pub history_minutes: u32,
}

fn default_max_cpu() -> f32 {
    30.0 // 30% CPU limit
}

fn default_max_memory() -> u32 {
    800 // 800 MB memory limit
}

fn default_refresh_interval() -> u64 {
    1000 // 1 second refresh interval
}

fn default_alert_threshold() -> f32 {
    0.8 // 80% threshold
}

fn default_history_minutes() -> u32 {
    60 // 1 hour
}

impl Default for HMConfig {
    fn default() -> Self {
        Self {
            max_cpu_percent: default_max_cpu(),
            max_memory_mb: default_max_memory(),
            refresh_interval_ms: default_refresh_interval(),
            alert_threshold: default_alert_threshold(),
            enable_graceful_degradation: true,
            enable_detailed_metrics: true,
            history_minutes: default_history_minutes(),
        }
    }
}

impl HMConfig {
    /// Load configuration from YAML file
    pub fn from_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let content = std::fs::read_to_string(path.as_ref())
            .with_context(|| format!("Failed to read config file: {}", path.as_ref().display()))?;
        
        let config: Self = serde_yaml::from_str(&content)
            .with_context(|| "Failed to parse config file as YAML")?;
        
        Ok(config)
    }
    
    /// Save configuration to YAML file
    pub fn save_to_file<P: AsRef<Path>>(&self, path: P) -> Result<()> {
        let yaml = serde_yaml::to_string(self)
            .with_context(|| "Failed to serialize config to YAML")?;
        
        std::fs::write(path.as_ref(), yaml)
            .with_context(|| format!("Failed to write config to file: {}", path.as_ref().display()))?;
        
        Ok(())
    }
    
    /// Load configuration from environment variables
    pub fn from_env() -> Self {
        let mut config = Self::default();
        
        // Override with environment variables
        if let Ok(max_cpu) = std::env::var("MCP_HM_MAX_CPU")
            .and_then(|v| v.parse::<f32>().map_err(|_| std::env::VarError::NotPresent)) {
            config.max_cpu_percent = max_cpu;
        }
        
        if let Ok(max_memory) = std::env::var("MCP_HM_MAX_MEMORY")
            .and_then(|v| v.parse::<u32>().map_err(|_| std::env::VarError::NotPresent)) {
            config.max_memory_mb = max_memory;
        }
        
        if let Ok(refresh) = std::env::var("MCP_HM_REFRESH_INTERVAL")
            .and_then(|v| v.parse::<u64>().map_err(|_| std::env::VarError::NotPresent)) {
            config.refresh_interval_ms = refresh;
        }
        
        if let Ok(threshold) = std::env::var("MCP_HM_ALERT_THRESHOLD")
            .and_then(|v| v.parse::<f32>().map_err(|_| std::env::VarError::NotPresent)) {
            config.alert_threshold = threshold;
        }
        
        if let Ok(value) = std::env::var("MCP_HM_ENABLE_GRACEFUL_DEGRADATION") {
            config.enable_graceful_degradation = value.to_lowercase() == "true";
        }
        
        if let Ok(value) = std::env::var("MCP_HM_ENABLE_DETAILED_METRICS") {
            config.enable_detailed_metrics = value.to_lowercase() == "true";
        }
        
        if let Ok(minutes) = std::env::var("MCP_HM_HISTORY_MINUTES")
            .and_then(|v| v.parse::<u32>().map_err(|_| std::env::VarError::NotPresent)) {
            config.history_minutes = minutes;
        }
        
        config
    }
    
    /// Validate configuration
    pub fn validate(&self) -> Result<()> {
        // Check CPU percentage
        if self.max_cpu_percent <= 0.0 || self.max_cpu_percent > 100.0 {
            return Err(anyhow::anyhow!("Invalid CPU percentage: must be between 0 and 100"));
        }
        
        // Check memory
        if self.max_memory_mb == 0 {
            return Err(anyhow::anyhow!("Invalid memory limit: must be greater than 0"));
        }
        
        // Check refresh interval
        if self.refresh_interval_ms == 0 {
            return Err(anyhow::anyhow!("Invalid refresh interval: must be greater than 0"));
        }
        
        // Check alert threshold
        if self.alert_threshold <= 0.0 || self.alert_threshold > 1.0 {
            return Err(anyhow::anyhow!("Invalid alert threshold: must be between 0 and 1"));
        }
        
        Ok(())
    }
}
