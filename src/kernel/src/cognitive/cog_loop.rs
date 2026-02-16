//! Cognitive Loop — orchestrates the intention-entropy-contradiction cycle.
//!
//! Port of Python `cog_loop.py` to Rust. This is the main cognitive engine
//! that ties together the reasoner, entropy engine, and symbol bridge.

use std::collections::HashMap;
use serde::Serialize;
use super::types::CogVec;
use super::reasoner::Reasoner;
use super::entropy::EntropyEngine;
use super::symbols::SymbolBridge;
use super::knowledge::KnowledgeStore;

/// A cognitive intention with activation and priority.
#[derive(Debug)]
struct Intention {
    name: String,
    vector: CogVec,
    activation: f32,
    priority: f32,
    cycle_count: u64,
}

impl Intention {
    fn new(name: &str, dim: usize, priority: f32) -> Self {
        Self {
            name: name.to_string(),
            vector: CogVec::noise(dim, name.len() as u64 * 13 + 1),
            activation: 0.0,
            priority,
            cycle_count: 0,
        }
    }

    fn set_activation(&mut self, level: f32) {
        self.activation = level.max(0.0).min(1.0);
        if self.activation > 0.5 {
            self.cycle_count += 1;
        }
    }

    fn is_active(&self) -> bool {
        self.activation > 0.5
    }
}

/// Current cognitive state snapshot.
#[derive(Debug, Clone, Serialize)]
pub struct CognitiveState {
    pub field: CogVec,
    pub contradiction_level: f32,
    pub dominant_symbols: Vec<(String, f32)>,
    pub active_intentions: Vec<String>,
    pub cycle: u64,
}

/// Result of a cognitive cycle.
#[derive(Debug, Serialize)]
pub struct CycleResult {
    pub state: CognitiveState,
    pub collapsed_intents: Vec<String>,
    pub emerged_symbols: bool,
}

/// The main cognitive loop engine.
pub struct CogLoop {
    dim: usize,
    pub reasoner: Reasoner,
    pub entropy: EntropyEngine,
    pub symbols: SymbolBridge,
    pub knowledge: KnowledgeStore,
    intentions: HashMap<String, Intention>,
    current_field: CogVec,
    cycle_counter: u64,
    contradiction_threshold: f32,
    max_active_intentions: usize,
}

impl CogLoop {
    /// Create a new cognitive loop with given dimension.
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            reasoner: Reasoner::new(dim),
            entropy: EntropyEngine::new(dim),
            symbols: SymbolBridge::new(dim),
            knowledge: KnowledgeStore::new(),
            intentions: HashMap::new(),
            current_field: CogVec::zeros(dim),
            cycle_counter: 0,
            contradiction_threshold: 0.7,
            max_active_intentions: 3,
        }
    }

    /// Create with a file-backed knowledge store.
    pub fn with_knowledge_file(dim: usize, path: &str) -> anyhow::Result<Self> {
        Ok(Self {
            dim,
            reasoner: Reasoner::new(dim),
            entropy: EntropyEngine::new(dim),
            symbols: SymbolBridge::new(dim),
            knowledge: KnowledgeStore::with_file(path)?,
            intentions: HashMap::new(),
            current_field: CogVec::zeros(dim),
            cycle_counter: 0,
            contradiction_threshold: 0.7,
            max_active_intentions: 3,
        })
    }

    /// Register a cognitive intention.
    pub fn register_intention(&mut self, name: &str, priority: f32) -> bool {
        if self.intentions.contains_key(name) {
            return false;
        }
        self.intentions.insert(
            name.to_string(),
            Intention::new(name, self.dim, priority),
        );
        self.entropy.register_intent(name);
        true
    }

    /// Activate an intention for the current cycle.
    pub fn activate_intention(&mut self, name: &str) -> bool {
        if let Some(intention) = self.intentions.get_mut(name) {
            intention.set_activation(1.0);

            // Enforce max active intentions
            let active: Vec<String> = self.intentions.values()
                .filter(|i| i.is_active())
                .map(|i| i.name.clone())
                .collect();

            if active.len() > self.max_active_intentions {
                // Deactivate lowest-priority active intention
                let mut lowest_name = None;
                let mut lowest_priority = f32::MAX;
                for a in &active {
                    if a == name { continue; }
                    if let Some(i) = self.intentions.get(a) {
                        if i.priority < lowest_priority {
                            lowest_priority = i.priority;
                            lowest_name = Some(a.clone());
                        }
                    }
                }
                if let Some(ln) = lowest_name {
                    if let Some(i) = self.intentions.get_mut(&ln) {
                        i.set_activation(0.2);
                    }
                }
            }
            true
        } else {
            false
        }
    }

    /// Process a contradiction vector through the cognitive system.
    pub fn process_contradiction(&mut self, contradiction: &CogVec) -> CognitiveState {
        // Get active symbols for reasoning
        let grounding = self.symbols.ground_neural_to_symbolic(&self.current_field);
        let symbol_names: Vec<String> = grounding.top_symbols.iter()
            .map(|(s, _)| s.clone())
            .collect();
        let sym_refs: Vec<&str> = symbol_names.iter().map(|s| s.as_str()).collect();

        // Reason with contradiction
        let result = self.reasoner.reason(contradiction, &sym_refs);

        // Only apply if contradiction exceeds threshold
        if result.contradiction_level > self.contradiction_threshold {
            self.current_field = self.reasoner.entropic_collapse(&self.current_field, Some(contradiction));
        } else {
            // Mild blend for sub-threshold contradictions
            self.current_field.blend(contradiction, 0.1);
            self.current_field.normalize();
        }

        self.snapshot_state(result.contradiction_level, result.dominant_symbols)
    }

    /// Run one full cognitive cycle.
    pub fn cycle(&mut self, input: Option<&CogVec>) -> CycleResult {
        self.cycle_counter += 1;

        // 1. Blend input into current field if provided
        if let Some(inp) = input {
            self.current_field.blend(inp, 0.3);
        }

        // 2. Inject current field into active entropy intents
        let active_names: Vec<String> = self.intentions.values()
            .filter(|i| i.is_active())
            .map(|i| i.name.clone())
            .collect();

        for name in &active_names {
            self.entropy.inject_delta(name, &self.current_field, 0.2);
        }

        // 3. Check for collapsed intents
        let mut collapsed = Vec::new();
        for name in &active_names {
            if self.entropy.is_collapsed(name) == Some(true) {
                collapsed.push(name.clone());
            }
        }

        // 4. Run reasoning
        let grounding = self.symbols.ground_neural_to_symbolic(&self.current_field);
        let symbol_names: Vec<String> = grounding.top_symbols.iter()
            .map(|(s, _)| s.clone())
            .collect();
        let sym_refs: Vec<&str> = symbol_names.iter().map(|s| s.as_str()).collect();

        let reason_result = self.reasoner.reason(&self.current_field, &sym_refs);

        // 5. Update field via entropic collapse
        let active_intention_vecs: Vec<CogVec> = active_names.iter()
            .filter_map(|n| self.intentions.get(n))
            .map(|i| i.vector.clone())
            .collect();

        if let Some(first_intent) = active_intention_vecs.first() {
            self.current_field = self.reasoner.entropic_collapse(&self.current_field, Some(first_intent));
        }

        // 6. Apply symbol decay
        self.symbols.decay();

        // 7. Build state
        let state = self.snapshot_state(
            reason_result.contradiction_level,
            reason_result.dominant_symbols,
        );

        CycleResult {
            state,
            collapsed_intents: collapsed,
            emerged_symbols: grounding.emerged,
        }
    }

    /// Get current cognitive state.
    pub fn state(&self) -> CognitiveState {
        let active: Vec<String> = self.intentions.values()
            .filter(|i| i.is_active())
            .map(|i| i.name.clone())
            .collect();

        CognitiveState {
            field: self.current_field.clone(),
            contradiction_level: 0.0,
            dominant_symbols: Vec::new(),
            active_intentions: active,
            cycle: self.cycle_counter,
        }
    }

    /// Get dimension.
    pub fn dim(&self) -> usize {
        self.dim
    }

    /// Get cycle count.
    pub fn cycle_count(&self) -> u64 {
        self.cycle_counter
    }

    fn snapshot_state(&self, contradiction_level: f32, dominant_symbols: Vec<(String, f32)>) -> CognitiveState {
        let active: Vec<String> = self.intentions.values()
            .filter(|i| i.is_active())
            .map(|i| i.name.clone())
            .collect();

        CognitiveState {
            field: self.current_field.clone(),
            contradiction_level,
            dominant_symbols,
            active_intentions: active,
            cycle: self.cycle_counter,
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_register_intention() {
        let mut cog = CogLoop::new(8);
        assert!(cog.register_intention("explore", 0.8));
        assert!(!cog.register_intention("explore", 0.8)); // duplicate
    }

    #[test]
    fn test_activate_intention() {
        let mut cog = CogLoop::new(8);
        cog.register_intention("goal_a", 0.5);
        assert!(cog.activate_intention("goal_a"));
        assert!(!cog.activate_intention("nonexistent"));
    }

    #[test]
    fn test_cognitive_cycle() {
        let mut cog = CogLoop::new(8);
        cog.register_intention("learn", 0.7);
        cog.activate_intention("learn");

        // Register some symbols
        cog.symbols.register_symbol("core", "knowledge", None);
        cog.symbols.register_symbol("core", "pattern", None);

        let input = CogVec::noise(8, 42);
        let result = cog.cycle(Some(&input));

        assert_eq!(result.state.cycle, 1);
        assert!(!result.state.active_intentions.is_empty());
    }

    #[test]
    fn test_multiple_cycles() {
        let mut cog = CogLoop::new(8);
        cog.register_intention("observe", 0.6);
        cog.activate_intention("observe");

        for i in 0..10 {
            let input = CogVec::noise(8, i + 100);
            cog.cycle(Some(&input));
        }

        assert_eq!(cog.cycle_count(), 10);
    }

    #[test]
    fn test_process_contradiction() {
        let mut cog = CogLoop::new(8);
        cog.symbols.register_symbol("core", "truth", None);
        cog.symbols.register_symbol("core", "lie", None);

        let contradiction = CogVec::noise(8, 99);
        let state = cog.process_contradiction(&contradiction);
        assert!(state.contradiction_level >= 0.0);
    }

    #[test]
    fn test_max_active_intentions() {
        let mut cog = CogLoop::new(8);
        cog.register_intention("a", 0.1);
        cog.register_intention("b", 0.5);
        cog.register_intention("c", 0.9);
        cog.register_intention("d", 0.3);

        cog.activate_intention("a");
        cog.activate_intention("b");
        cog.activate_intention("c");
        cog.activate_intention("d"); // should deactivate lowest priority ("a")

        let state = cog.state();
        assert!(state.active_intentions.len() <= 3);
    }

    #[test]
    fn test_knowledge_integration() {
        let mut cog = CogLoop::new(4);
        let v = CogVec::from_slice(&[1.0, 0.0, 0.0, 0.0]);
        let _id = cog.knowledge.add_fact("test fact", v).unwrap();
        assert_eq!(cog.knowledge.len(), 1);

        let query = CogVec::from_slice(&[0.9, 0.1, 0.0, 0.0]);
        let results = cog.knowledge.search(&query, 1);
        assert_eq!(results[0].text, "test fact");
    }
}
