//! MCP-ZERO Hardware Manager (HM)
//! 
//! Responsible for monitoring and enforcing the strict hardware constraints:
//! - Less than 1 GB RAM usage
//! - Under 30% CPU usage on i3 processor
//! - Efficient resource allocation to agents

use std::collections::HashMap;
use std::sync::{Arc, Mutex, RwLock};
use std::time::{Duration, Instant};
use anyhow::{Result, Context, anyhow};
use serde::{Serialize, Deserialize};
use sysinfo::{System, SystemExt, ProcessExt, CpuExt};
use metrics::{gauge, histogram};
use dashmap::DashMap;
use thiserror::Error;

mod config;
mod resource;
mod alert;

pub use config::HMConfig;
pub use resource::{ResourceStats, ResourceLimit, ResourceType};
pub use alert::{Alert, AlertLevel, AlertHandler, ConsoleAlertHandler, FileAlertHandler};

/// Error types for the Hardware Manager
#[derive(Error, Debug)]
pub enum HMError {
    #[error("Resource limit exceeded: {0}")]
    ResourceLimitExceeded(String),
    
    #[error("Failed to monitor resources: {0}")]
    MonitoringError(String),
    
    #[error("Configuration error: {0}")]
    ConfigError(String),
    
    #[error("System error: {0}")]
    SystemError(String),
}

/// Resource allocation for an agent
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct AgentAllocation {
    /// Agent ID
    pub agent_id: String,
    
    /// CPU allocation (percentage)
    pub cpu_percent: f32,
    
    /// Memory allocation (MB)
    pub memory_mb: u32,
    
    /// Priority level (higher = more important)
    pub priority: u8,
}

/// Hardware Manager implementation
pub struct HardwareManager {
    /// Global resource limits
    limits: ResourceLimit,
    
    /// Current resource stats
    stats: Arc<Mutex<ResourceStats>>,
    
    /// Agent allocations
    allocations: Arc<RwLock<HashMap<String, AgentAllocation>>>,
    
    /// System information collector
    system: Arc<Mutex<System>>,
    
    /// Alert handlers
    alert_handlers: Vec<Box<dyn AlertHandler>>,
    
    /// Process ID
    process_id: u32,
    
    /// Last update time
    last_update: Arc<Mutex<Instant>>,
    
    /// Configuration
    config: HMConfig,
}

impl HardwareManager {
    /// Create a new HardwareManager with the given configuration
    pub fn new(config: HMConfig) -> Self {
        let mut system = System::new_all();
        system.refresh_all();
        
        // Get own process ID
        let process_id = std::process::id();
        
        Self {
            limits: ResourceLimit {
                cpu_percent: config.max_cpu_percent,
                memory_mb: config.max_memory_mb,
            },
            stats: Arc::new(Mutex::new(ResourceStats {
                cpu_percent: 0.0,
                memory_mb: 0,
                timestamp: chrono::Utc::now(),
            })),
            allocations: Arc::new(RwLock::new(HashMap::new())),
            system: Arc::new(Mutex::new(system)),
            alert_handlers: Vec::new(),
            process_id,
            last_update: Arc::new(Mutex::new(Instant::now())),
            config,
        }
    }
    
    /// Start the hardware monitoring loop
    pub fn start_monitoring(&self) -> Result<()> {
        let stats = self.stats.clone();
        let system = self.system.clone();
        let process_id = self.process_id;
        let limits = self.limits.clone();
        let last_update = self.last_update.clone();
        let interval = self.config.refresh_interval_ms;
        
        // Spawn monitoring thread
        std::thread::spawn(move || {
            loop {
                // Sleep for the refresh interval
                std::thread::sleep(Duration::from_millis(interval));
                
                // Update last check time
                {
                    let mut last = last_update.lock().unwrap();
                    *last = Instant::now();
                }
                
                // Update system stats
                {
                    let mut sys = system.lock().unwrap();
                    sys.refresh_all();
                    
                    // Get process info
                    if let Some(process) = sys.process(sysinfo::Pid::from(process_id as usize)) {
                        let cpu_usage = process.cpu_usage();
                        let memory_usage = process.memory() / (1024 * 1024); // Convert to MB
                        
                        // Update stats
                        let mut current_stats = stats.lock().unwrap();
                        current_stats.cpu_percent = cpu_usage;
                        current_stats.memory_mb = memory_usage as u32;
                        current_stats.timestamp = chrono::Utc::now();
                        
                        // Export metrics
                        gauge!("mcp.hm.cpu_usage", cpu_usage as f64); // Convert f32 to f64
                        gauge!("mcp.hm.memory_usage", memory_usage as f64);
                        
                        // Check limits
                        if cpu_usage > limits.cpu_percent {
                            tracing::warn!("CPU usage exceeded limit: {:.2}% > {:.2}%", 
                                         cpu_usage, limits.cpu_percent);
                            // In a real implementation, would trigger alerts and take action
                        }
                        
                        if memory_usage as u32 > limits.memory_mb {
                            tracing::warn!("Memory usage exceeded limit: {} MB > {} MB", 
                                         memory_usage, limits.memory_mb);
                            // In a real implementation, would trigger alerts and take action
                        }
                    }
                }
            }
        });
        
        Ok(())
    }
    
    /// Get current resource stats
    pub fn get_stats(&self) -> ResourceStats {
        let stats = self.stats.lock().unwrap();
        stats.clone()
    }
    
    /// Check if within resource limits
    pub fn check_limits(&self) -> Result<(), HMError> {
        let stats = self.stats.lock().unwrap();
        
        if stats.cpu_percent > self.limits.cpu_percent {
            return Err(HMError::ResourceLimitExceeded(
                format!("CPU usage exceeded limit: {:.2}% > {:.2}%", 
                      stats.cpu_percent, self.limits.cpu_percent)
            ));
        }
        
        if stats.memory_mb > self.limits.memory_mb {
            return Err(HMError::ResourceLimitExceeded(
                format!("Memory usage exceeded limit: {} MB > {} MB", 
                      stats.memory_mb, self.limits.memory_mb)
            ));
        }
        
        Ok(())
    }
    
    /// Allocate resources to an agent
    pub fn allocate_resources(&self, allocation: AgentAllocation) -> Result<(), HMError> {
        // Check if allocation is within limits
        {
            let allocations = self.allocations.read().unwrap();
            
            let mut total_cpu = allocation.cpu_percent;
            let mut total_memory = allocation.memory_mb;
            
            for (id, alloc) in allocations.iter() {
                if id != &allocation.agent_id {
                    total_cpu += alloc.cpu_percent;
                    total_memory += alloc.memory_mb;
                }
            }
            
            if total_cpu > self.limits.cpu_percent {
                return Err(HMError::ResourceLimitExceeded(
                    format!("Total CPU allocation would exceed limit: {:.2}% > {:.2}%", 
                          total_cpu, self.limits.cpu_percent)
                ));
            }
            
            if total_memory > self.limits.memory_mb {
                return Err(HMError::ResourceLimitExceeded(
                    format!("Total memory allocation would exceed limit: {} MB > {} MB", 
                          total_memory, self.limits.memory_mb)
                ));
            }
        }
        
        // Store allocation
        let mut allocations = self.allocations.write().unwrap();
        allocations.insert(allocation.agent_id.clone(), allocation);
        
        Ok(())
    }
    
    /// Release resources allocated to an agent
    pub fn release_resources(&self, agent_id: &str) -> Result<(), HMError> {
        let mut allocations = self.allocations.write().unwrap();
        
        if allocations.remove(agent_id).is_some() {
            tracing::info!("Resources released for agent {}", agent_id);
            Ok(())
        } else {
            Err(HMError::ConfigError(format!("No allocation found for agent {}", agent_id)))
        }
    }
    
    /// Add an alert handler
    pub fn add_alert_handler(&mut self, handler: Box<dyn AlertHandler>) {
        self.alert_handlers.push(handler);
    }
    
    /// Generate a resource report
    pub fn generate_report(&self) -> serde_json::Value {
        // Clone the data to avoid RwLockReadGuard serialization issues
        let stats = self.stats.lock().unwrap().clone();
        let allocations = self.allocations.read().unwrap();
        
        // Clone the allocations into a new HashMap that can be serialized
        let allocation_map = allocations.iter().map(|(k, v)| (k.clone(), v.clone())).collect::<std::collections::HashMap<_, _>>();
        
        let total_allocated_cpu: f32 = allocations.values().map(|a| a.cpu_percent).sum();
        let total_allocated_memory: u32 = allocations.values().map(|a| a.memory_mb).sum();
        
        serde_json::json!({
            "timestamp": stats.timestamp.to_rfc3339(),
            "system": {
                "cpu_percent": stats.cpu_percent,
                "memory_mb": stats.memory_mb,
            },
            "limits": {
                "cpu_percent": self.limits.cpu_percent,
                "memory_mb": self.limits.memory_mb,
            },
            "allocations": {
                "count": allocations.len(),
                "total_cpu_percent": total_allocated_cpu,
                "total_memory_mb": total_allocated_memory,
                "details": allocation_map,
            }
        })
    }
}

// Implementation for AgentAllocation
impl AgentAllocation {
    /// Create a new agent allocation
    pub fn new(agent_id: &str, cpu_percent: f32, memory_mb: u32, priority: u8) -> Self {
        Self {
            agent_id: agent_id.to_string(),
            cpu_percent,
            memory_mb,
            priority,
        }
    }
}
