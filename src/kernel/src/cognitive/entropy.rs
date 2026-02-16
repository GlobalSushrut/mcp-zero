//! Entropy Engine — entropic intent fields, delta injection, collapse detection.
//!
//! Port of Python `entropy_engine.py` to Rust.

use std::collections::HashMap;
use super::types::CogVec;

/// An entropic intent field that evolves through delta injections.
#[derive(Debug)]
pub struct EntropicIntent {
    pub name: String,
    dim: usize,
    field: CogVec,
    delta_history: Vec<DeltaRecord>,
    collapse_threshold: f32,
}

#[derive(Debug, Clone)]
struct DeltaRecord {
    magnitude: f32,
    change: f32,
}

impl EntropicIntent {
    pub fn new(name: &str, dim: usize) -> Self {
        Self {
            name: name.to_string(),
            dim,
            field: CogVec::noise(dim, name.len() as u64 * 7 + 1),
            delta_history: Vec::new(),
            collapse_threshold: 0.85,
        }
    }

    /// Inject a delta into the intent field with weighted blending.
    pub fn inject_delta(&mut self, delta: &CogVec, weight: f32) {
        let prev_field = self.field.clone();
        self.field.blend(delta, weight);

        let change = self.field.sub(&prev_field).norm();
        self.delta_history.push(DeltaRecord {
            magnitude: delta.norm(),
            change,
        });
    }

    /// Check if intent has collapsed (reached stability).
    pub fn is_collapsed(&self) -> bool {
        if self.delta_history.len() < 5 {
            return false;
        }
        let recent: Vec<f32> = self.delta_history[self.delta_history.len() - 5..]
            .iter()
            .map(|d| d.change)
            .collect();
        let avg_change: f32 = recent.iter().sum::<f32>() / recent.len() as f32;
        avg_change < (1.0 - self.collapse_threshold)
    }

    /// Get current field.
    pub fn field(&self) -> &CogVec {
        &self.field
    }

    /// Get delta history length.
    pub fn history_len(&self) -> usize {
        self.delta_history.len()
    }

    /// Get dimension.
    pub fn dim(&self) -> usize {
        self.dim
    }

    /// Average magnitude of recent deltas.
    pub fn avg_magnitude(&self, n: usize) -> f32 {
        if self.delta_history.is_empty() {
            return 0.0;
        }
        let start = self.delta_history.len().saturating_sub(n);
        let slice = &self.delta_history[start..];
        slice.iter().map(|d| d.magnitude).sum::<f32>() / slice.len() as f32
    }
}

/// Entropy Engine manages multiple entropic intent fields.
#[derive(Debug)]
pub struct EntropyEngine {
    dim: usize,
    intents: HashMap<String, EntropicIntent>,
}

impl EntropyEngine {
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            intents: HashMap::new(),
        }
    }

    /// Register a new intent field.
    pub fn register_intent(&mut self, name: &str) -> bool {
        if self.intents.contains_key(name) {
            return false;
        }
        self.intents.insert(name.to_string(), EntropicIntent::new(name, self.dim));
        true
    }

    /// Inject a delta into a named intent.
    pub fn inject_delta(&mut self, name: &str, delta: &CogVec, weight: f32) -> bool {
        if let Some(intent) = self.intents.get_mut(name) {
            intent.inject_delta(delta, weight);
            true
        } else {
            false
        }
    }

    /// Check if a named intent has collapsed.
    pub fn is_collapsed(&self, name: &str) -> Option<bool> {
        self.intents.get(name).map(|i| i.is_collapsed())
    }

    /// Get the field of a named intent.
    pub fn get_field(&self, name: &str) -> Option<&CogVec> {
        self.intents.get(name).map(|i| i.field())
    }

    /// Get all intent names.
    pub fn intent_names(&self) -> Vec<String> {
        self.intents.keys().cloned().collect()
    }

    /// Get dimension.
    pub fn dim(&self) -> usize {
        self.dim
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_intent() {
        let mut engine = EntropyEngine::new(8);
        assert!(engine.register_intent("goal_a"));
        assert!(!engine.register_intent("goal_a")); // duplicate
        assert_eq!(engine.intent_names().len(), 1);
    }

    #[test]
    fn test_inject_delta() {
        let mut engine = EntropyEngine::new(8);
        engine.register_intent("test");
        let delta = CogVec::from_slice(&[1.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0, 0.0]);
        assert!(engine.inject_delta("test", &delta, 0.3));
        assert!(!engine.inject_delta("nonexistent", &delta, 0.3));
    }

    #[test]
    fn test_collapse_detection() {
        let mut engine = EntropyEngine::new(4);
        engine.register_intent("stable");

        // Inject the same tiny delta many times → should collapse
        let delta = CogVec::from_slice(&[0.01, 0.01, 0.01, 0.01]);
        for _ in 0..20 {
            engine.inject_delta("stable", &delta, 0.01);
        }
        assert_eq!(engine.is_collapsed("stable"), Some(true));
    }

    #[test]
    fn test_not_collapsed_early() {
        let mut engine = EntropyEngine::new(4);
        engine.register_intent("new");
        // Less than 5 deltas → never collapsed
        let delta = CogVec::from_slice(&[1.0, 0.0, 0.0, 0.0]);
        engine.inject_delta("new", &delta, 0.5);
        assert_eq!(engine.is_collapsed("new"), Some(false));
    }
}
