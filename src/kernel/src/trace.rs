//! Trace module for MCP-ZERO kernel
//!
//! Implements Poseidon hash-based tracing for agent execution,
//! providing cryptographic verification of execution paths.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use anyhow::{Result, Context, anyhow};
use sha3::{Digest, Sha3_256};
use serde::{Serialize, Deserialize};
use serde_json::Value;

use crate::agent::AgentId;

/// Trace ID type
pub type TraceId = String;

/// Trace entry representing a single event in an agent's execution
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct TraceEntry {
    /// Trace ID
    pub id: TraceId,
    
    /// Agent ID
    pub agent_id: AgentId,
    
    /// Event type
    pub event_type: String,
    
    /// Event data
    pub data: Value,
    
    /// Timestamp (Unix epoch)
    pub timestamp: i64,
    
    /// Previous entry hash for chaining
    pub prev_hash: Option<String>,
    
    /// Current entry hash
    pub hash: String,
}

/// Trace status
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum TraceStatus {
    /// Trace is active
    Active,
    /// Trace is completed successfully
    Completed,
    /// Trace is completed with failure
    Failed,
}

/// Active trace context
#[derive(Debug)]
struct TraceContext {
    /// Trace ID
    id: TraceId,
    
    /// Agent ID
    agent_id: AgentId,
    
    /// Intent being traced
    intent: String,
    
    /// Last hash in the chain
    last_hash: String,
    
    /// Start timestamp
    start_time: i64,
    
    /// Status
    status: TraceStatus,
}

/// Poseidon tracer implementation
pub struct PoseidonTracer {
    /// Active traces
    active_traces: Arc<RwLock<HashMap<TraceId, TraceContext>>>,
    
    /// All trace entries (in-memory cache, actual storage is done separately)
    entries: Arc<RwLock<Vec<TraceEntry>>>,
}

impl PoseidonTracer {
    /// Create a new PoseidonTracer instance
    pub fn new() -> Self {
        Self {
            active_traces: Arc::new(RwLock::new(HashMap::new())),
            entries: Arc::new(RwLock::new(Vec::new())),
        }
    }
    
    /// Begin a new trace for an agent execution
    pub fn begin_trace(&self, agent_id: &AgentId, intent: &str) -> Result<TraceId> {
        let now = chrono::Utc::now().timestamp();
        
        // Create initial hash from agent_id + intent + timestamp
        let initial_data = format!("{}:{}:{}", agent_id, intent, now);
        let initial_hash = self.compute_hash(&initial_data, None);
        
        // Generate trace ID
        let trace_id = format!("trace_{}", &initial_hash[..16]);
        
        // Create trace context
        let context = TraceContext {
            id: trace_id.clone(),
            agent_id: agent_id.clone(),
            intent: intent.to_string(),
            last_hash: initial_hash.clone(),
            start_time: now,
            status: TraceStatus::Active,
        };
        
        // Store trace context
        let mut active_traces = self.active_traces.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on active traces"))?;
        active_traces.insert(trace_id.clone(), context);
        
        // Create and store initial trace entry
        let entry = TraceEntry {
            id: trace_id.clone(),
            agent_id: agent_id.clone(),
            event_type: "trace.begin".to_string(),
            data: serde_json::json!({
                "intent": intent,
                "timestamp": now
            }),
            timestamp: now,
            prev_hash: None,
            hash: initial_hash,
        };
        
        self.store_entry(entry)?;
        
        tracing::debug!("Started trace {} for agent {}", trace_id, agent_id);
        Ok(trace_id)
    }
    
    /// End a trace
    pub fn end_trace(&self, trace_id: &TraceId, success: bool, result: Option<&Value>) -> Result<()> {
        // Get trace context
        let mut active_traces = self.active_traces.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on active traces"))?;
        
        let context = active_traces.get(trace_id)
            .ok_or_else(|| anyhow!("Trace not found: {}", trace_id))?;
        
        let agent_id = context.agent_id.clone();
        let prev_hash = context.last_hash.clone();
        let status = if success { TraceStatus::Completed } else { TraceStatus::Failed };
        
        // Create end trace entry
        let now = chrono::Utc::now().timestamp();
        let duration = now - context.start_time;
        
        let data = match result {
            Some(r) => serde_json::json!({
                "success": success,
                "duration_ms": duration * 1000,
                "result": r
            }),
            None => serde_json::json!({
                "success": success,
                "duration_ms": duration * 1000
            }),
        };
        
        // Compute hash
        let hash = self.compute_hash(&serde_json::to_string(&data).unwrap_or_default(), Some(&prev_hash));
        
        // Create and store trace entry
        let entry = TraceEntry {
            id: trace_id.clone(),
            agent_id,
            event_type: "trace.end".to_string(),
            data,
            timestamp: now,
            prev_hash: Some(prev_hash),
            hash,
        };
        
        self.store_entry(entry)?;
        
        // Update trace context
        let context = active_traces.get_mut(trace_id)
            .ok_or_else(|| anyhow!("Trace not found: {}", trace_id))?;
        context.status = status;
        
        // If trace is completed, remove from active traces
        if status != TraceStatus::Active {
            active_traces.remove(trace_id);
        }
        
        tracing::debug!("Ended trace {} with status {:?}", trace_id, status);
        Ok(())
    }
    
    /// Record an event in a trace
    pub fn record_event(&self, agent_id: &AgentId, event_type: &str, data: &Value) -> Result<()> {
        // Default to a new trace if none is active
        let trace_id = {
            let active_traces = self.active_traces.read()
                .map_err(|_| anyhow!("Failed to acquire read lock on active traces"))?;
            
            // Find an active trace for this agent
            let mut trace_id = None;
            for (id, context) in active_traces.iter() {
                if &context.agent_id == agent_id && context.status == TraceStatus::Active {
                    trace_id = Some(id.clone());
                    break;
                }
            }
            
            // If no active trace, create a new one
            match trace_id {
                Some(id) => id,
                None => {
                    drop(active_traces); // Release read lock before calling begin_trace
                    self.begin_trace(agent_id, "general")?
                }
            }
        };
        
        // Get trace context
        let mut active_traces = self.active_traces.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on active traces"))?;
        
        let context = active_traces.get_mut(&trace_id)
            .ok_or_else(|| anyhow!("Trace not found: {}", trace_id))?;
        
        let prev_hash = context.last_hash.clone();
        
        // Create event entry
        let now = chrono::Utc::now().timestamp();
        
        // Compute hash
        let hash_input = format!("{}:{}:{}", event_type, serde_json::to_string(data).unwrap_or_default(), now);
        let hash = self.compute_hash(&hash_input, Some(&prev_hash));
        
        // Create and store trace entry
        let entry = TraceEntry {
            id: trace_id.clone(),
            agent_id: agent_id.clone(),
            event_type: event_type.to_string(),
            data: data.clone(),
            timestamp: now,
            prev_hash: Some(prev_hash),
            hash: hash.clone(),
        };
        
        self.store_entry(entry)?;
        
        // Update last hash
        context.last_hash = hash;
        
        tracing::debug!("Recorded event {} in trace {} for agent {}", event_type, trace_id, agent_id);
        Ok(())
    }
    
    /// Compute a Poseidon hash (simulated with SHA3 for now)
    fn compute_hash(&self, data: &str, prev_hash: Option<&str>) -> String {
        let mut hasher = Sha3_256::new();
        
        // Include previous hash if available
        if let Some(prev) = prev_hash {
            hasher.update(prev.as_bytes());
            hasher.update(b":");
        }
        
        // Add data
        hasher.update(data.as_bytes());
        
        // Compute hash
        let result = hasher.finalize();
        format!("{:x}", result)
    }
    
    /// Store a trace entry
    fn store_entry(&self, entry: TraceEntry) -> Result<()> {
        // Store in memory cache
        let mut entries = self.entries.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on entries"))?;
        entries.push(entry.clone());
        
        // In production, would also persist to storage
        // This is a simplified implementation
        Ok(())
    }
    
    /// Export trace to a ZK-compatible format
    pub fn export_zk_proof(&self, trace_id: &TraceId) -> Result<Value> {
        // Get all entries for the trace
        let entries = self.entries.read()
            .map_err(|_| anyhow!("Failed to acquire read lock on entries"))?;
        
        let trace_entries: Vec<&TraceEntry> = entries.iter()
            .filter(|e| &e.id == trace_id)
            .collect();
        
        if trace_entries.is_empty() {
            return Err(anyhow!("No entries found for trace: {}", trace_id));
        }
        
        // Create proof structure
        // This is a simplified implementation
        let proof = serde_json::json!({
            "trace_id": trace_id,
            "agent_id": trace_entries[0].agent_id,
            "entries": trace_entries.len(),
            "root_hash": trace_entries.last().map(|e| &e.hash).unwrap_or(&String::new()),
            "timestamp": chrono::Utc::now().timestamp(),
        });
        
        Ok(proof)
    }
}

impl Default for PoseidonTracer {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_trace_lifecycle() {
        let tracer = PoseidonTracer::new();
        let agent_id = "test_agent".to_string();
        
        // Begin trace
        let trace_id = tracer.begin_trace(&agent_id, "test_intent").unwrap();
        
        // Record event
        tracer.record_event(
            &agent_id,
            "test_event",
            &serde_json::json!({"data": "test"}),
        ).unwrap();
        
        // End trace
        tracer.end_trace(
            &trace_id,
            true,
            Some(&serde_json::json!({"result": "success"})),
        ).unwrap();
        
        // Export proof
        let proof = tracer.export_zk_proof(&trace_id).unwrap();
        assert_eq!(proof["trace_id"], trace_id);
        assert_eq!(proof["agent_id"], agent_id);
        assert_eq!(proof["entries"], 3); // begin, event, end
    }
}
