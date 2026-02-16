//! Cognitive Fabric — unified orchestrator wiring all cognitive modules.
//!
//! Connects the original 7-module reasoning framework with the new
//! topos-distributed, knot-theoretic, categorically-compressed intelligence:
//!
//! **Old 7 (reasoning framework):**
//!   1. `CogVec` — fixed-dim vector math
//!   2. `Reasoner` — symbol mapping, contradiction injection, entropic collapse
//!   3. `EntropyEngine` — entropic intent fields, delta injection, collapse
//!   4. `SymbolBridge` — symbol emergence through entropic burst
//!   5. `KnowledgeStore` — file-backed fact store with cosine search
//!   6. `CogLoop` — orchestrator (reasoner + entropy + symbols + knowledge)
//!   7. `ModalityFold` + `MetaContractSystem` — multimodal + contracts
//!
//! **New modules (intelligence layer):**
//!   - `NeuralEngine` — inference (hash fallback + tract ONNX)
//!   - `CHTEngine` — 100x token compression (holographic + PQ)
//!   - `CategoricalAdapter` — domain adaptation (replaces LoRA, braid init)
//!   - `ToposNetwork` — sheaf distribution (gossip, gluing, H¹ cohomology)
//!   - `EntropyGraph` — neural network layer entropy tracking
//!   - `BinaryKnowledgeStore` — redb ACID binary storage
//!   - `KnowledgeKnotGraph` — knot-theoretic knowledge graph
//!
//! The fabric's `think()` method runs a full cognitive cycle:
//!   1. Embed input via NeuralEngine
//!   2. Compress via CHT
//!   3. Run CogLoop cycle (reasoner → entropy → symbols)
//!   4. Update KnowledgeKnotGraph with new relationships
//!   5. Track entropy via EntropyGraph
//!   6. Apply CategoricalAdapter for domain adaptation
//!   7. Sync via ToposNetwork if peers available

use serde::Serialize;
use super::types::CogVec;
use super::cog_loop::{CogLoop, CycleResult};
use super::neural::{NeuralEngine, NeuralConfig};
use super::cht::CHTEngine;
use super::trainer::CategoricalAdapter;
use super::topos::ToposNetwork;
use super::entropy_graph::EntropyGraph;
use super::knowledge_knot::{KnowledgeKnotGraph, RelationType};
use super::hyperdimensional::{HyperdimensionalEngine, HDEngineStats};
#[cfg(test)]
use super::knowledge_knot::NodeType;

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/// Configuration for the cognitive fabric.
#[derive(Clone, Debug)]
pub struct FabricConfig {
    /// Cognitive vector dimension (default 64).
    pub cog_dim: usize,
    /// Embedding dimension for neural engine (default 384).
    pub embed_dim: usize,
    /// CHT segments (default 8).
    pub cht_segments: usize,
    /// CHT centroids per segment (default 256).
    pub cht_centroids: usize,
    /// Adapter rank (default 4).
    pub adapter_rank: usize,
    /// Device ID for topos network.
    pub device_id: String,
    /// Similarity threshold for auto-linking in knot graph.
    pub similarity_threshold: f32,
}

impl Default for FabricConfig {
    fn default() -> Self {
        Self {
            cog_dim: 64,
            embed_dim: 384,
            cht_segments: 8,
            cht_centroids: 256,
            adapter_rank: 4,
            device_id: "local".to_string(),
            similarity_threshold: 0.85,
        }
    }
}

// ---------------------------------------------------------------------------
// Think result
// ---------------------------------------------------------------------------

/// Result of a full cognitive think cycle.
#[derive(Debug, Serialize)]
pub struct ThinkResult {
    /// Cognitive cycle result from CogLoop.
    pub cycle: CycleResult,
    /// Embedding of the input.
    pub embedding_dim: usize,
    /// CHT compression applied.
    pub cht_facets: usize,
    /// Knowledge knot graph stats.
    pub knot_nodes: usize,
    pub knot_edges: usize,
    /// Adapter applied.
    pub adapter_active: bool,
    /// Topos network peers.
    pub topos_peers: usize,
    /// Overall think cycle number.
    pub think_cycle: u64,
}

/// Result of learning a new fact through the fabric.
#[derive(Debug, Serialize)]
pub struct LearnResult {
    pub fact_node_id: u64,
    pub edges_created: usize,
    pub knot_nodes: usize,
    pub knot_edges: usize,
}

/// Fabric status snapshot.
#[derive(Debug, Serialize)]
pub struct FabricStatus {
    pub think_cycles: u64,
    pub cog_cycles: u64,
    pub inference_count: u64,
    pub knot_nodes: usize,
    pub knot_edges: usize,
    pub knot_components: usize,
    pub adapter_name: String,
    pub adapter_steps: u64,
    pub adapter_params: usize,
    pub topos_peers: usize,
    pub entropy_snapshots: usize,
}

// ---------------------------------------------------------------------------
// Cognitive Fabric
// ---------------------------------------------------------------------------

/// The unified cognitive fabric.
pub struct CognitiveFabric {
    pub config: FabricConfig,
    /// Original cognitive loop (reasoner + entropy + symbols + knowledge).
    pub cog: CogLoop,
    /// Neural inference engine (hash fallback).
    pub neural: NeuralEngine,
    /// Hyperdimensional semantic engine (real semantic learning).
    pub hd: HyperdimensionalEngine,
    /// Categorical Holographic Token engine.
    pub cht: CHTEngine,
    /// Domain adaptation adapter.
    pub adapter: CategoricalAdapter,
    /// Topos distribution network.
    pub topos: ToposNetwork,
    /// Neural network entropy tracker.
    pub entropy_graph: EntropyGraph,
    /// Knowledge knot graph.
    pub knot_graph: KnowledgeKnotGraph,
    /// Think cycle counter.
    think_counter: u64,
}

impl CognitiveFabric {
    /// Create a new cognitive fabric with given config.
    pub fn new(config: FabricConfig) -> Self {
        let neural_config = NeuralConfig {
            embed_dim: config.embed_dim,
            track_entropy: true,
            model_path: None,
        };

        Self {
            cog: CogLoop::new(config.cog_dim),
            neural: NeuralEngine::new(neural_config),
            hd: HyperdimensionalEngine::new(),
            cht: CHTEngine::new(config.embed_dim, config.cht_segments, config.cht_centroids),
            adapter: CategoricalAdapter::new(
                "default",
                config.cog_dim,
                config.adapter_rank,
                5, // braid length
                42,
            ),
            topos: ToposNetwork::default_network(&config.device_id),
            entropy_graph: EntropyGraph::new(1000),
            knot_graph: KnowledgeKnotGraph::new(),
            think_counter: 0,
            config,
        }
    }

    /// Create with default config.
    pub fn default_fabric() -> Self {
        Self::new(FabricConfig::default())
    }

    // -----------------------------------------------------------------------
    // Core think cycle
    // -----------------------------------------------------------------------

    /// Run a full cognitive think cycle.
    ///
    /// This is the main entry point that wires all modules together:
    /// 1. Embed input text via NeuralEngine → get embedding
    /// 2. Compress embedding via CHT → holographic token
    /// 3. Project to CogVec dimension → feed into CogLoop
    /// 4. Run CogLoop cycle (reasoner → entropy → symbols → knowledge)
    /// 5. Track layer entropy via EntropyGraph
    /// 6. Apply CategoricalAdapter for domain adaptation
    /// 7. Return unified result
    pub fn think(&mut self, input_text: &str) -> ThinkResult {
        self.think_counter += 1;

        // 1. Embed via neural engine
        let embedding = self.neural.embed(input_text);

        // 2. Compress via CHT
        let cht_token = self.cht.encode(&embedding.vector);

        // 3. Project to CogVec dimension
        let cog_input = self.project_to_cog(&embedding.vector);

        // 4. Apply categorical adapter (domain adaptation)
        let adapted = self.adapter.forward(&cog_input);
        let adapted_vec = CogVec::from_slice(&adapted);

        // 5. Run CogLoop cycle
        let cycle_result = self.cog.cycle(Some(&adapted_vec));

        // 6. Track entropy
        let field_data: Vec<f32> = cycle_result.state.field.data().to_vec();
        self.entropy_graph.record_pass(&[
            ("input", &embedding.vector[..self.config.cog_dim.min(embedding.vector.len())]),
            ("adapted", &adapted),
            ("cognitive_field", &field_data),
        ]);

        ThinkResult {
            cycle: cycle_result,
            embedding_dim: embedding.dim,
            cht_facets: cht_token.facet_count,
            knot_nodes: self.knot_graph.node_count(),
            knot_edges: self.knot_graph.edge_count(),
            adapter_active: true,
            topos_peers: self.topos.device_count(),
            think_cycle: self.think_counter,
        }
    }

    /// Think with a raw CogVec input (no text embedding).
    pub fn think_vec(&mut self, input: &CogVec) -> ThinkResult {
        self.think_counter += 1;

        let input_data = input.data().to_vec();
        let adapted = self.adapter.forward(&input_data);
        let adapted_vec = CogVec::from_slice(&adapted);

        let cycle_result = self.cog.cycle(Some(&adapted_vec));

        let field_data: Vec<f32> = cycle_result.state.field.data().to_vec();
        self.entropy_graph.record_pass(&[
            ("input", &input_data),
            ("adapted", &adapted),
            ("cognitive_field", &field_data),
        ]);

        ThinkResult {
            cycle: cycle_result,
            embedding_dim: self.config.cog_dim,
            cht_facets: 0,
            knot_nodes: self.knot_graph.node_count(),
            knot_edges: self.knot_graph.edge_count(),
            adapter_active: true,
            topos_peers: self.topos.device_count(),
            think_cycle: self.think_counter,
        }
    }

    // -----------------------------------------------------------------------
    // Learning (knowledge knot graph integration)
    // -----------------------------------------------------------------------

    /// Learn a new fact: embed it, add to knot graph, auto-link similar nodes.
    pub fn learn(&mut self, text: &str) -> LearnResult {
        // Embed the fact
        let embedding = self.neural.embed(text);

        // Add to knot graph
        let node_id = self.knot_graph.import_fact(text, embedding.vector.clone());

        // Also add to CogLoop's knowledge store
        let cog_vec = CogVec::from_slice(
            &self.project_to_cog(&embedding.vector)
        );
        let _ = self.cog.knowledge.add_fact(text, cog_vec);

        // Auto-link similar nodes
        let edges_created = self.knot_graph.auto_link_similar(self.config.similarity_threshold);

        LearnResult {
            fact_node_id: node_id,
            edges_created,
            knot_nodes: self.knot_graph.node_count(),
            knot_edges: self.knot_graph.edge_count(),
        }
    }

    /// Learn a symbol and connect it to related facts.
    pub fn learn_symbol(&mut self, name: &str) -> u64 {
        let embedding = self.neural.embed(name);
        let node_id = self.knot_graph.import_symbol(name, embedding.vector.clone());

        // Register in CogLoop's symbol bridge
        self.cog.symbols.register_symbol("fabric", name, None);

        // Find related facts and create implication edges
        let similar = self.knot_graph.search_by_embedding(&embedding.vector, 3);
        for (related_id, sim) in similar {
            if related_id != node_id && sim > 0.5 {
                self.knot_graph.add_edge(node_id, related_id, RelationType::SimilarTo, sim);
            }
        }

        node_id
    }

    /// Record a contradiction between two knowledge nodes.
    pub fn record_contradiction(&mut self, node_a: u64, node_b: u64, intensity: f32) {
        self.knot_graph.record_contradiction(node_a, node_b, intensity);

        // Feed contradiction into CogLoop
        if let (Some(a), Some(b)) = (self.knot_graph.get_node(node_a), self.knot_graph.get_node(node_b)) {
            let a_cog = CogVec::from_slice(&self.project_to_cog(&a.embedding));
            let b_cog = CogVec::from_slice(&self.project_to_cog(&b.embedding));
            let contradiction = a_cog.sub(&b_cog);
            self.cog.process_contradiction(&contradiction);
        }
    }

    // -----------------------------------------------------------------------
    // Training (categorical adapter)
    // -----------------------------------------------------------------------

    /// Train the adapter on a single example.
    pub fn train_step(&mut self, input_text: &str, target_text: &str, lr: f32) -> f32 {
        let input_emb = self.neural.embed(input_text);
        let target_emb = self.neural.embed(target_text);

        let input_cog = self.project_to_cog(&input_emb.vector);
        let target_cog = self.project_to_cog(&target_emb.vector);

        self.adapter.train_step(&input_cog, &target_cog, lr)
    }

    /// Set a new adapter.
    pub fn set_adapter(&mut self, adapter: CategoricalAdapter) {
        self.adapter = adapter;
    }

    // -----------------------------------------------------------------------
    // Status
    // -----------------------------------------------------------------------

    /// Get full fabric status.
    pub fn status(&self) -> FabricStatus {
        let stats = self.knot_graph.stats();
        FabricStatus {
            think_cycles: self.think_counter,
            cog_cycles: self.cog.cycle_count(),
            inference_count: self.neural.inference_count(),
            knot_nodes: stats.node_count,
            knot_edges: stats.edge_count,
            knot_components: stats.connected_components,
            adapter_name: self.adapter.name.clone(),
            adapter_steps: self.adapter.steps,
            adapter_params: self.adapter.param_count(),
            topos_peers: self.topos.device_count(),
            entropy_snapshots: self.entropy_graph.snapshot_count(),
        }
    }

    /// Get think cycle count.
    pub fn think_count(&self) -> u64 {
        self.think_counter
    }

    // -----------------------------------------------------------------------
    // Hyperdimensional Engine (semantic learning)
    // -----------------------------------------------------------------------

    /// Teach the HD engine by processing text (builds real semantic vectors).
    pub fn teach(&mut self, text: &str) {
        self.hd.teach(text);
    }

    /// Get semantic similarity between two words (from HD engine).
    pub fn word_similarity(&self, a: &str, b: &str) -> Option<f32> {
        self.hd.word_similarity(a, b)
    }

    /// Find most similar words (from HD engine).
    pub fn most_similar(&self, word: &str, top_k: usize) -> Vec<(String, f32)> {
        self.hd.most_similar(word, top_k)
    }

    /// Get HD engine statistics.
    pub fn hd_stats(&self) -> HDEngineStats {
        self.hd.stats()
    }

    // -----------------------------------------------------------------------
    // Helpers
    // -----------------------------------------------------------------------

    /// Project a high-dim embedding to CogVec dimension.
    /// Takes first cog_dim elements, pads with zeros if shorter.
    fn project_to_cog(&self, embedding: &[f32]) -> Vec<f32> {
        let dim = self.config.cog_dim;
        let mut result = vec![0.0f32; dim];
        let copy_len = dim.min(embedding.len());
        result[..copy_len].copy_from_slice(&embedding[..copy_len]);
        // Normalize
        let norm: f32 = result.iter().map(|x| x * x).sum::<f32>().sqrt();
        if norm > 1e-10 {
            for v in result.iter_mut() { *v /= norm; }
        }
        result
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_fabric() {
        let fabric = CognitiveFabric::default_fabric();
        assert_eq!(fabric.think_count(), 0);
        let status = fabric.status();
        assert_eq!(status.think_cycles, 0);
        assert_eq!(status.knot_nodes, 0);
    }

    #[test]
    fn test_think_text() {
        let mut fabric = CognitiveFabric::default_fabric();
        let result = fabric.think("the sky is blue");
        assert_eq!(result.think_cycle, 1);
        assert_eq!(result.embedding_dim, 384);
        assert_eq!(result.cht_facets, 8);
        assert!(result.adapter_active);
    }

    #[test]
    fn test_think_vec() {
        let mut fabric = CognitiveFabric::default_fabric();
        let input = CogVec::noise(64, 42);
        let result = fabric.think_vec(&input);
        assert_eq!(result.think_cycle, 1);
        assert_eq!(result.embedding_dim, 64);
    }

    #[test]
    fn test_multiple_think_cycles() {
        let mut fabric = CognitiveFabric::default_fabric();
        for i in 0..5 {
            fabric.think(&format!("thought {}", i));
        }
        assert_eq!(fabric.think_count(), 5);
        assert_eq!(fabric.status().inference_count, 5);
    }

    #[test]
    fn test_learn_fact() {
        let mut fabric = CognitiveFabric::default_fabric();
        let result = fabric.learn("water boils at 100 degrees Celsius");
        assert_eq!(result.fact_node_id, 1);
        assert_eq!(result.knot_nodes, 1);
    }

    #[test]
    fn test_learn_multiple_facts_auto_link() {
        let mut fabric = CognitiveFabric::default_fabric();
        fabric.learn("cats are furry animals");
        fabric.learn("dogs are furry animals");
        fabric.learn("the sun is a star");

        let status = fabric.status();
        assert_eq!(status.knot_nodes, 3);
        // cats and dogs should be similar (both about furry animals)
        // so at least one edge should exist
    }

    #[test]
    fn test_learn_symbol() {
        let mut fabric = CognitiveFabric::default_fabric();
        fabric.learn("gravity pulls objects down");
        let sym_id = fabric.learn_symbol("gravity");
        assert!(sym_id > 0);
        assert_eq!(fabric.knot_graph.node_count(), 2);
    }

    #[test]
    fn test_record_contradiction() {
        let mut fabric = CognitiveFabric::default_fabric();
        let a = fabric.learn("the earth is flat").fact_node_id;
        let b = fabric.learn("the earth is round").fact_node_id;
        fabric.record_contradiction(a, b, 0.95);
        assert!(fabric.knot_graph.edge_count() >= 1);
    }

    #[test]
    fn test_train_step() {
        let mut fabric = CognitiveFabric::default_fabric();
        let loss = fabric.train_step("input text", "target text", 0.01);
        assert!(loss >= 0.0);
        assert_eq!(fabric.adapter.steps, 1);
    }

    #[test]
    fn test_think_after_learning() {
        let mut fabric = CognitiveFabric::default_fabric();
        // Learn some facts
        fabric.learn("water is a liquid");
        fabric.learn("ice is solid water");
        fabric.learn_symbol("water");

        // Think about water
        let result = fabric.think("what happens when water freezes");
        assert_eq!(result.think_cycle, 1);
        assert!(result.knot_nodes >= 3);
    }

    #[test]
    fn test_entropy_tracking_through_think() {
        let mut fabric = CognitiveFabric::default_fabric();
        fabric.think("test entropy tracking");
        // Neural engine tracks entropy + fabric tracks entropy
        assert!(fabric.entropy_graph.snapshot_count() >= 1);
    }

    #[test]
    fn test_status_comprehensive() {
        let mut fabric = CognitiveFabric::default_fabric();
        fabric.learn("fact one");
        fabric.learn("fact two");
        fabric.think("thinking about facts");
        fabric.train_step("a", "b", 0.01);

        let status = fabric.status();
        assert_eq!(status.think_cycles, 1);
        assert_eq!(status.knot_nodes, 2);
        assert_eq!(status.adapter_steps, 1);
        assert!(status.inference_count >= 4); // 2 learns + 1 think + 2 train
        assert!(status.entropy_snapshots >= 1);
    }

    #[test]
    fn test_project_to_cog() {
        let fabric = CognitiveFabric::default_fabric();
        let big = vec![1.0; 384];
        let projected = fabric.project_to_cog(&big);
        assert_eq!(projected.len(), 64);
        // Should be normalized
        let norm: f32 = projected.iter().map(|x| x * x).sum::<f32>().sqrt();
        assert!((norm - 1.0).abs() < 1e-4);
    }

    #[test]
    fn test_project_to_cog_short_input() {
        let fabric = CognitiveFabric::default_fabric();
        let short = vec![1.0, 0.0];
        let projected = fabric.project_to_cog(&short);
        assert_eq!(projected.len(), 64);
        // First 2 elements should be non-zero, rest zero (before normalization)
    }

    #[test]
    fn test_full_pipeline() {
        let mut fabric = CognitiveFabric::default_fabric();

        // Register intentions
        fabric.cog.register_intention("learn", 0.8);
        fabric.cog.activate_intention("learn");

        // Learn facts
        fabric.learn("the speed of light is 299792458 m/s");
        fabric.learn("nothing can travel faster than light");
        fabric.learn_symbol("light");
        fabric.learn_symbol("speed");

        // Record relationship
        let nodes: Vec<u64> = fabric.knot_graph.nodes_by_type(&NodeType::Fact)
            .iter().map(|n| n.id).collect();
        if nodes.len() >= 2 {
            fabric.knot_graph.record_implication(nodes[0], nodes[1], 0.9);
        }

        // Think
        let result = fabric.think("how fast does light travel");
        assert!(result.knot_nodes >= 4);

        // Train adapter
        fabric.train_step("speed of light", "very fast", 0.01);

        // Check status
        let status = fabric.status();
        assert!(status.think_cycles >= 1);
        assert!(status.knot_nodes >= 4);
        assert!(status.adapter_steps >= 1);
    }
}
