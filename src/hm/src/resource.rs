//! Resource management for MCP-ZERO Hardware Manager
//!
//! Handles resource tracking, limits, and allocation strategies for
//! maintaining strict hardware constraints.

use std::time::Duration;
use serde::{Serialize, Deserialize};

/// Resource type enum
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum ResourceType {
    /// CPU resource
    CPU,
    /// Memory resource
    Memory,
    /// Storage resource
    Storage,
    /// Network bandwidth
    Network,
}

/// Resource statistics
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceStats {
    /// CPU usage percentage (0-100)
    pub cpu_percent: f32,
    
    /// Memory usage in MB
    pub memory_mb: u32,
    
    /// Timestamp when stats were collected
    pub timestamp: chrono::DateTime<chrono::Utc>,
}

/// Resource limits
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct ResourceLimit {
    /// Maximum CPU percentage (0-100)
    pub cpu_percent: f32,
    
    /// Maximum memory in MB
    pub memory_mb: u32,
}

/// Resource allocation strategy
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum AllocationStrategy {
    /// Even distribution
    Even,
    /// Priority-based (higher priority gets more)
    PriorityBased,
    /// First-come, first-served
    FCFS,
}

/// Resource allocator
pub struct ResourceAllocator {
    /// Maximum resources available
    limits: ResourceLimit,
    
    /// Allocation strategy
    strategy: AllocationStrategy,
    
    /// Minimum guaranteed CPU per agent (%)
    min_cpu_per_agent: f32,
    
    /// Minimum guaranteed memory per agent (MB)
    min_memory_per_agent: u32,
}

impl ResourceAllocator {
    /// Create a new resource allocator
    pub fn new(limits: ResourceLimit, strategy: AllocationStrategy) -> Self {
        Self {
            limits,
            strategy,
            min_cpu_per_agent: 1.0,  // 1% CPU minimum
            min_memory_per_agent: 10, // 10MB memory minimum
        }
    }
    
    /// Calculate resource allocation for an agent based on priority
    pub fn calculate_allocation(&self, priority: u8, agent_count: usize) -> (f32, u32) {
        // Default to minimum values
        let mut cpu = self.min_cpu_per_agent;
        let mut memory = self.min_memory_per_agent;
        
        match self.strategy {
            AllocationStrategy::Even => {
                // Even distribution among agents
                if agent_count > 0 {
                    cpu = (self.limits.cpu_percent * 0.9) / agent_count as f32; 
                    memory = (self.limits.memory_mb * 9 / 10) / agent_count as u32;
                }
            },
            
            AllocationStrategy::PriorityBased => {
                // Priority-based allocation (0-10 scale)
                let priority_factor = priority as f32 / 10.0;
                
                // Allocate based on priority but ensure minimum
                cpu = self.min_cpu_per_agent + 
                      (self.limits.cpu_percent - (self.min_cpu_per_agent * agent_count as f32)) * 
                      priority_factor / (agent_count as f32);
                
                memory = self.min_memory_per_agent +
                         (self.limits.memory_mb - (self.min_memory_per_agent * agent_count as u32)) *
                         (priority as u32) / (10 * agent_count as u32);
            },
            
            AllocationStrategy::FCFS => {
                // First-come first-served - just return minimum for now
                // In production would track available resources and allocate them in order
                cpu = self.min_cpu_per_agent;
                memory = self.min_memory_per_agent;
            },
        }
        
        // Ensure we don't allocate more than available
        cpu = cpu.min(self.limits.cpu_percent);
        memory = memory.min(self.limits.memory_mb);
        
        (cpu, memory)
    }
    
    /// Set minimum resource guarantees
    pub fn set_minimums(&mut self, min_cpu: f32, min_memory: u32) {
        self.min_cpu_per_agent = min_cpu;
        self.min_memory_per_agent = min_memory;
    }
}

/// Resource usage tracker
pub struct ResourceTracker {
    /// Historical CPU usage (timestamp, percentage)
    cpu_history: Vec<(chrono::DateTime<chrono::Utc>, f32)>,
    
    /// Historical memory usage (timestamp, MB)
    memory_history: Vec<(chrono::DateTime<chrono::Utc>, u32)>,
    
    /// Maximum history length
    max_history: usize,
    
    /// Last warning time for throttling alerts
    last_warning: Option<chrono::DateTime<chrono::Utc>>,
    
    /// Warning threshold (percentage of limit)
    warning_threshold: f32,
}

impl ResourceTracker {
    /// Create a new resource tracker
    pub fn new(max_history: usize) -> Self {
        Self {
            cpu_history: Vec::with_capacity(max_history),
            memory_history: Vec::with_capacity(max_history),
            max_history,
            last_warning: None,
            warning_threshold: 0.8, // 80% of limit
        }
    }
    
    /// Add resource stats to history
    pub fn add_stats(&mut self, stats: &ResourceStats) {
        // Add CPU usage
        self.cpu_history.push((stats.timestamp, stats.cpu_percent));
        if self.cpu_history.len() > self.max_history {
            self.cpu_history.remove(0);
        }
        
        // Add memory usage
        self.memory_history.push((stats.timestamp, stats.memory_mb));
        if self.memory_history.len() > self.max_history {
            self.memory_history.remove(0);
        }
    }
    
    /// Check if resources are exceeding threshold and should trigger warning
    pub fn should_warn(&mut self, limits: &ResourceLimit) -> Option<(ResourceType, f32)> {
        // Get latest stats
        if self.cpu_history.is_empty() || self.memory_history.is_empty() {
            return None;
        }
        
        let &(_, cpu_usage) = self.cpu_history.last().unwrap();
        let &(_, memory_usage) = self.memory_history.last().unwrap();
        
        // Calculate percentages of limits
        let cpu_percent_of_limit = cpu_usage / limits.cpu_percent;
        let memory_percent_of_limit = memory_usage as f32 / limits.memory_mb as f32;
        
        // Check if we should warn and throttle warnings
        let now = chrono::Utc::now();
        let should_throttle = match self.last_warning {
            Some(last) => now.signed_duration_since(last).num_seconds() < 60, // 1 minute throttling
            None => false,
        };
        
        if !should_throttle {
            // Check CPU
            if cpu_percent_of_limit >= self.warning_threshold {
                self.last_warning = Some(now);
                return Some((ResourceType::CPU, cpu_percent_of_limit));
            }
            
            // Check Memory
            if memory_percent_of_limit >= self.warning_threshold {
                self.last_warning = Some(now);
                return Some((ResourceType::Memory, memory_percent_of_limit));
            }
        }
        
        None
    }
    
    /// Get average usage over the tracked history
    pub fn get_average_usage(&self) -> (f32, u32) {
        if self.cpu_history.is_empty() || self.memory_history.is_empty() {
            return (0.0, 0);
        }
        
        // Calculate averages
        let avg_cpu = self.cpu_history.iter().map(|&(_, cpu)| cpu).sum::<f32>() / self.cpu_history.len() as f32;
        let avg_memory = self.memory_history.iter().map(|&(_, mem)| mem).sum::<u32>() / self.memory_history.len() as u32;
        
        (avg_cpu, avg_memory)
    }
    
    /// Get maximum usage over the tracked history
    pub fn get_max_usage(&self) -> (f32, u32) {
        if self.cpu_history.is_empty() || self.memory_history.is_empty() {
            return (0.0, 0);
        }
        
        // Find maximums
        let max_cpu = self.cpu_history.iter().map(|&(_, cpu)| cpu).fold(0.0, f32::max);
        let max_memory = self.memory_history.iter().map(|&(_, mem)| mem).fold(0, u32::max);
        
        (max_cpu, max_memory)
    }
}
