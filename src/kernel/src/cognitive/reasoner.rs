//! Reasoner — symbol mapping, contradiction injection, entropic collapse.
//!
//! Port of Python `mock_reasoner.py` to Rust. All vector math is zero-copy
//! and stack-friendly. No numpy, no GC, no Python overhead.

use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use super::types::CogVec;

/// A recorded contradiction between two symbols.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Contradiction {
    pub source: String,
    pub target: String,
    pub intensity: f32,
    pub timestamp_ms: u64,
}

/// Reasoner: symbol-vector mapping + contradiction-based reasoning.
#[derive(Debug)]
pub struct Reasoner {
    dim: usize,
    mock_tensor: CogVec,
    intent_layer: CogVec,
    contradiction_layer: CogVec,
    symbols: HashMap<String, CogVec>,
    symbol_weights: HashMap<String, f32>,
    contradictions: Vec<Contradiction>,
    bindings: HashMap<String, CogVec>,
    contradiction_threshold: f32,
    seed_counter: u64,
}

/// Result of a reasoning operation.
#[derive(Debug, Serialize)]
pub struct ReasonResult {
    pub dominant_symbols: Vec<(String, f32)>,
    pub contradiction_level: f32,
}

impl Reasoner {
    /// Create a new reasoner with given vector dimension.
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            mock_tensor: CogVec::noise(dim, 1),
            intent_layer: CogVec::zeros(dim),
            contradiction_layer: CogVec::zeros(dim),
            symbols: HashMap::new(),
            symbol_weights: HashMap::new(),
            contradictions: Vec::new(),
            bindings: HashMap::new(),
            contradiction_threshold: 0.3,
            seed_counter: 100,
        }
    }

    /// Map a symbol to a vector. If no vector given, generates deterministic one.
    pub fn map_symbol(&mut self, symbol: &str, vector: Option<CogVec>) -> CogVec {
        let mut vec = match vector {
            Some(v) => {
                assert_eq!(v.dim(), self.dim);
                v
            }
            None => {
                self.seed_counter += 1;
                CogVec::noise(self.dim, self.seed_counter)
            }
        };
        vec.normalize();
        self.symbols.insert(symbol.to_string(), vec.clone());
        self.symbol_weights.entry(symbol.to_string()).or_insert(0.5);
        vec
    }

    /// Inject a contradiction between two symbols.
    pub fn inject_contradiction(&mut self, source: &str, target: &str, intensity: f32) -> usize {
        // Auto-map symbols if needed
        if !self.symbols.contains_key(source) {
            self.map_symbol(source, None);
        }
        if !self.symbols.contains_key(target) {
            self.map_symbol(target, None);
        }

        let source_vec = self.symbols[source].clone();
        let target_vec = self.symbols[target].clone();

        // contradiction_vector = (source - target) * intensity
        let diff = source_vec.sub(&target_vec);
        self.contradiction_layer.add_scaled(&diff, intensity * 0.3);

        let now = std::time::SystemTime::now()
            .duration_since(std::time::UNIX_EPOCH)
            .unwrap_or_default()
            .as_millis() as u64;

        self.contradictions.push(Contradiction {
            source: source.to_string(),
            target: target.to_string(),
            intensity,
            timestamp_ms: now,
        });

        // Update weights
        let sw = self.symbol_weights.entry(source.to_string()).or_insert(0.5);
        *sw = (*sw - intensity * 0.2).max(0.1);
        let tw = self.symbol_weights.entry(target.to_string()).or_insert(0.5);
        *tw = (*tw + intensity * 0.2).min(0.9);

        self.contradictions.len()
    }

    /// Entropic collapse: blend field with mock tensor, intent, and contradiction layers.
    pub fn entropic_collapse(&self, field: &CogVec, intention: Option<&CogVec>) -> CogVec {
        let intent = intention.unwrap_or(&self.intent_layer);
        let mut result = field.clone();

        // result += mock_tensor * 0.2 + intent * 0.3
        result.add_scaled(&self.mock_tensor, 0.2);
        result.add_scaled(intent, 0.3);

        // Apply contradiction layer if significant
        if self.contradiction_layer.norm() > self.contradiction_threshold {
            let mut norm_c = self.contradiction_layer.clone();
            norm_c.normalize();
            result.add_scaled(&norm_c, 0.4);
        }

        result.normalize();
        result
    }

    /// Bind a field to a symbol for symbolic anchoring.
    pub fn symbolic_binding(&mut self, field: &CogVec, symbol: &str) -> CogVec {
        if !self.symbols.contains_key(symbol) {
            self.map_symbol(symbol, None);
        }
        let symbol_vec = self.symbols[symbol].clone();

        let mut binding = field.clone();
        // binding = field * 0.7 + symbol * 0.3
        for (a, b) in binding.as_mut_slice().iter_mut().zip(symbol_vec.as_slice()) {
            *a = *a * 0.7 + *b * 0.3;
        }
        binding.normalize();
        self.bindings.insert(symbol.to_string(), binding.clone());
        binding
    }

    /// Calculate resonance between a field and a list of symbols.
    pub fn calculate_resonance(&mut self, field: &CogVec, symbols: &[&str]) -> Vec<(String, f32)> {
        let mut resonances: Vec<(String, f32)> = symbols.iter().map(|&sym| {
            if !self.symbols.contains_key(sym) {
                self.map_symbol(sym, None);
            }
            let sym_vec = &self.symbols[sym];
            let dot = field.dot(sym_vec);
            let weight = *self.symbol_weights.get(sym).unwrap_or(&0.5);
            (sym.to_string(), dot * weight)
        }).collect();

        resonances.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        resonances
    }

    /// Main reasoning: collapse → resonance → result.
    pub fn reason(&mut self, input_field: &CogVec, symbols: &[&str]) -> ReasonResult {
        let collapsed = self.entropic_collapse(input_field, None);
        let resonances = self.calculate_resonance(&collapsed, symbols);
        let dominant = resonances.into_iter().take(3).collect();
        let contradiction_level = self.contradiction_layer.norm();

        ReasonResult {
            dominant_symbols: dominant,
            contradiction_level,
        }
    }

    /// Set the intent layer directly.
    pub fn set_intent(&mut self, intent: CogVec) {
        self.intent_layer = intent;
    }

    /// Get contradiction count.
    pub fn contradiction_count(&self) -> usize {
        self.contradictions.len()
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
    fn test_map_symbol() {
        let mut r = Reasoner::new(8);
        let v = r.map_symbol("hello", None);
        assert_eq!(v.dim(), 8);
        assert!((v.norm() - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_inject_contradiction() {
        let mut r = Reasoner::new(8);
        r.map_symbol("truth", None);
        r.map_symbol("lie", None);
        let count = r.inject_contradiction("truth", "lie", 0.8);
        assert_eq!(count, 1);
        assert!(r.contradiction_layer.norm() > 0.0);
    }

    #[test]
    fn test_entropic_collapse_normalizes() {
        let r = Reasoner::new(8);
        let field = CogVec::noise(8, 99);
        let result = r.entropic_collapse(&field, None);
        assert!((result.norm() - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_reason_returns_top3() {
        let mut r = Reasoner::new(8);
        let symbols: Vec<&str> = vec!["a", "b", "c", "d", "e"];
        let field = CogVec::noise(8, 42);
        let result = r.reason(&field, &symbols);
        assert!(result.dominant_symbols.len() <= 3);
    }

    #[test]
    fn test_symbolic_binding() {
        let mut r = Reasoner::new(8);
        let field = CogVec::noise(8, 10);
        let bound = r.symbolic_binding(&field, "anchor");
        assert!((bound.norm() - 1.0).abs() < 1e-5);
    }
}
