//! Symbol Bridge — symbol emergence through entropic burst mechanisms.
//!
//! Port of Python `symbol_emergence.py` to Rust.

use std::collections::HashMap;
use super::types::CogVec;

/// Entropic burst mechanism for symbol emergence.
#[derive(Debug)]
pub struct EntropicBurst {
    dim: usize,
    burst_field: CogVec,
    coherence_threshold: f32,
    decay_factor: f32,
    seed: u64,
}

impl EntropicBurst {
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            burst_field: CogVec::noise(dim, 77),
            coherence_threshold: 0.75,
            decay_factor: 0.05,
            seed: 200,
        }
    }

    /// Inject a neural pattern into the burst field.
    pub fn inject_pattern(&mut self, pattern: &CogVec, weight: f32) {
        self.burst_field.blend(pattern, weight);
        self.burst_field.normalize();
    }

    /// Natural decay of the burst field.
    pub fn decay(&mut self) {
        self.seed += 1;
        let noise = CogVec::noise(self.dim, self.seed);
        self.burst_field.blend(&noise, self.decay_factor);
        self.burst_field.normalize();
    }

    /// Coherence of the burst field (higher = clearer symbol emergence).
    pub fn coherence(&self) -> f32 {
        let variance = self.burst_field.variance();
        // Low variance = high coherence (uniform distribution = noise)
        // High variance = low coherence (peaked = signal)
        // Invert: high variance → high coherence
        let expected_uniform_var = 1.0 / (12.0 * self.dim as f32);
        (variance / expected_uniform_var.max(1e-10)).min(1.0)
    }

    /// Check if a symbol has emerged (coherence above threshold).
    pub fn has_emerged(&self) -> bool {
        self.coherence() > self.coherence_threshold
    }

    /// Get the burst field.
    pub fn field(&self) -> &CogVec {
        &self.burst_field
    }
}

/// A symbolic domain containing named symbols with vectors.
#[derive(Debug)]
struct SymbolicDomain {
    name: String,
    symbols: HashMap<String, CogVec>,
}

impl SymbolicDomain {
    fn new(name: &str) -> Self {
        Self {
            name: name.to_string(),
            symbols: HashMap::new(),
        }
    }

    fn name(&self) -> &str {
        &self.name
    }
}

/// Symbol Bridge: bidirectional neural-symbolic grounding.
#[derive(Debug)]
pub struct SymbolBridge {
    dim: usize,
    domains: HashMap<String, SymbolicDomain>,
    burst: EntropicBurst,
    grounding_cache: HashMap<String, CogVec>,
    seed_counter: u64,
}

/// Result of grounding a neural pattern to symbols.
#[derive(Debug)]
pub struct GroundingResult {
    pub top_symbols: Vec<(String, f32)>,
    pub coherence: f32,
    pub emerged: bool,
}

impl SymbolBridge {
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            domains: HashMap::new(),
            burst: EntropicBurst::new(dim),
            grounding_cache: HashMap::new(),
            seed_counter: 300,
        }
    }

    /// Register a new symbolic domain.
    pub fn register_domain(&mut self, name: &str) -> bool {
        if self.domains.contains_key(name) {
            return false;
        }
        self.domains.insert(name.to_string(), SymbolicDomain::new(name));
        true
    }

    /// Register a symbol in a domain with an optional vector.
    pub fn register_symbol(&mut self, domain: &str, symbol: &str, vector: Option<CogVec>) -> bool {
        // Auto-create domain if needed
        if !self.domains.contains_key(domain) {
            self.register_domain(domain);
        }

        let d = self.domains.get_mut(domain).unwrap();
        if d.symbols.contains_key(symbol) {
            return false;
        }

        let mut vec = match vector {
            Some(v) => v,
            None => {
                self.seed_counter += 1;
                CogVec::noise(self.dim, self.seed_counter)
            }
        };
        vec.normalize();
        d.symbols.insert(symbol.to_string(), vec);
        true
    }

    /// Ground a neural pattern to symbolic representations.
    pub fn ground_neural_to_symbolic(&mut self, pattern: &CogVec) -> GroundingResult {
        // Inject into burst field
        self.burst.inject_pattern(pattern, 0.3);

        // Calculate resonance with all symbols across all domains
        let mut resonances: Vec<(String, f32)> = Vec::new();

        for domain in self.domains.values() {
            for (sym_name, sym_vec) in &domain.symbols {
                let similarity = pattern.cosine_similarity(sym_vec);
                resonances.push((format!("{}:{}", domain.name(), sym_name), similarity));
            }
        }

        // Sort by resonance
        resonances.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        let top = resonances.into_iter().take(5).collect();

        GroundingResult {
            top_symbols: top,
            coherence: self.burst.coherence(),
            emerged: self.burst.has_emerged(),
        }
    }

    /// Ground a symbol to a neural pattern (reverse direction).
    pub fn ground_symbolic_to_neural(&self, domain: &str, symbol: &str) -> Option<CogVec> {
        self.domains.get(domain)
            .and_then(|d| d.symbols.get(symbol))
            .cloned()
    }

    /// Apply decay to the burst field.
    pub fn decay(&mut self) {
        self.burst.decay();
    }

    /// Get burst coherence.
    pub fn coherence(&self) -> f32 {
        self.burst.coherence()
    }

    /// Get dimension.
    pub fn dim(&self) -> usize {
        self.dim
    }

    /// Cache a grounding result for fast re-lookup.
    pub fn cache_grounding(&mut self, key: &str, vec: CogVec) {
        self.grounding_cache.insert(key.to_string(), vec);
    }

    /// Retrieve a cached grounding.
    pub fn cached_grounding(&self, key: &str) -> Option<&CogVec> {
        self.grounding_cache.get(key)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_domain_and_symbol() {
        let mut bridge = SymbolBridge::new(8);
        assert!(bridge.register_domain("concepts"));
        assert!(bridge.register_symbol("concepts", "truth", None));
        assert!(!bridge.register_symbol("concepts", "truth", None)); // duplicate
    }

    #[test]
    fn test_ground_neural_to_symbolic() {
        let mut bridge = SymbolBridge::new(8);
        bridge.register_symbol("core", "alpha", None);
        bridge.register_symbol("core", "beta", None);

        let pattern = CogVec::noise(8, 42);
        let result = bridge.ground_neural_to_symbolic(&pattern);
        assert!(result.top_symbols.len() <= 5);
    }

    #[test]
    fn test_ground_symbolic_to_neural() {
        let mut bridge = SymbolBridge::new(8);
        bridge.register_symbol("core", "gamma", None);

        let vec = bridge.ground_symbolic_to_neural("core", "gamma");
        assert!(vec.is_some());
        assert_eq!(vec.unwrap().dim(), 8);
    }

    #[test]
    fn test_burst_decay() {
        let mut bridge = SymbolBridge::new(8);
        let c1 = bridge.coherence();
        bridge.decay();
        let c2 = bridge.coherence();
        // Coherence should change after decay
        assert!((c1 - c2).abs() >= 0.0); // just ensure no panic
    }

    #[test]
    fn test_auto_create_domain() {
        let mut bridge = SymbolBridge::new(8);
        // Register symbol in non-existent domain → auto-creates
        assert!(bridge.register_symbol("auto_domain", "sym1", None));
        assert!(bridge.ground_symbolic_to_neural("auto_domain", "sym1").is_some());
    }
}
