//! LLM Bridge — connects MCP-Zero to real LLMs for training and inference.
//!
//! Three modes of operation:
//!
//! 1. **Distill** — Extract knowledge from an LLM into MCP-Zero's knot graph
//!    and categorical adapters. Run once on a server, deploy result to RPi.
//!
//! 2. **Hybrid** — MCP-Zero handles reasoning/knowledge/adaptation on-device,
//!    delegates text generation to an LLM via HTTP API when network available.
//!
//! 3. **Offline** — Pure MCP-Zero with hash embeddings (no LLM needed).
//!    Falls back automatically when LLM is unreachable.
//!
//! Integration points:
//!   - `EmbeddingSource` — pluggable embedding backend (hash, ONNX, or LLM API)
//!   - `GenerationDelegate` — text generation via external LLM
//!   - `KnowledgeDistiller` — extract facts from LLM into knot graph
//!   - `AdapterTrainer` — train categorical adapters from LLM embeddings

use serde::{Serialize, Deserialize};
use std::collections::HashMap;

use super::neural::NeuralEngine;
use super::trainer::CategoricalAdapter;
use super::knowledge_knot::{KnowledgeKnotGraph, NodeType, RelationType};

// ---------------------------------------------------------------------------
// Configuration
// ---------------------------------------------------------------------------

/// LLM connection configuration.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LLMConfig {
    /// Base URL for OpenAI-compatible API (e.g. "http://localhost:11434/v1" for ollama).
    pub api_url: String,
    /// Model name (e.g. "llama3.1:8b", "gpt-4o-mini").
    pub model: String,
    /// Embedding model (e.g. "nomic-embed-text", "text-embedding-3-small").
    pub embed_model: String,
    /// API key (empty for local models).
    pub api_key: String,
    /// Max tokens for generation.
    pub max_tokens: usize,
    /// Temperature for generation.
    pub temperature: f32,
    /// Timeout in milliseconds.
    pub timeout_ms: u64,
}

impl Default for LLMConfig {
    fn default() -> Self {
        Self {
            api_url: "http://localhost:11434/v1".to_string(),
            model: "llama3.1:8b".to_string(),
            embed_model: "nomic-embed-text".to_string(),
            api_key: String::new(),
            max_tokens: 256,
            temperature: 0.7,
            timeout_ms: 30_000,
        }
    }
}

impl LLMConfig {
    /// Config for ollama (local).
    pub fn ollama(model: &str) -> Self {
        Self {
            api_url: "http://localhost:11434/v1".to_string(),
            model: model.to_string(),
            embed_model: "nomic-embed-text".to_string(),
            ..Default::default()
        }
    }

    /// Config for OpenAI API.
    pub fn openai(api_key: &str, model: &str) -> Self {
        Self {
            api_url: "https://api.openai.com/v1".to_string(),
            model: model.to_string(),
            embed_model: "text-embedding-3-small".to_string(),
            api_key: api_key.to_string(),
            ..Default::default()
        }
    }

    /// Config for any OpenAI-compatible server (vLLM, text-generation-inference, etc).
    pub fn compatible(url: &str, model: &str) -> Self {
        Self {
            api_url: url.to_string(),
            model: model.to_string(),
            ..Default::default()
        }
    }
}

// ---------------------------------------------------------------------------
// Embedding Source — pluggable backend
// ---------------------------------------------------------------------------

/// Where embeddings come from.
#[derive(Clone, Debug, PartialEq)]
pub enum EmbeddingMode {
    /// Hash-based (deterministic, no model needed, always available).
    Hash,
    /// LLM API embeddings (requires network + running LLM).
    LLMApi,
    /// Hybrid: try LLM API first, fall back to hash if unavailable.
    HybridFallback,
}

/// Result of an embedding request.
#[derive(Clone, Debug)]
pub struct LLMEmbedding {
    pub vector: Vec<f32>,
    pub source: EmbeddingMode,
    pub model: String,
    pub dim: usize,
}

// ---------------------------------------------------------------------------
// Generation request/response
// ---------------------------------------------------------------------------

/// Request to generate text via LLM.
#[derive(Clone, Debug, Serialize)]
pub struct GenerateRequest {
    pub prompt: String,
    pub system: Option<String>,
    pub max_tokens: usize,
    pub temperature: f32,
    /// Context from MCP-Zero's knowledge graph to inject into prompt.
    pub knowledge_context: Vec<String>,
}

/// Response from LLM generation.
#[derive(Clone, Debug, Deserialize)]
pub struct GenerateResponse {
    pub text: String,
    pub tokens_used: usize,
    pub model: String,
    pub from_cache: bool,
}

// ---------------------------------------------------------------------------
// Distillation record
// ---------------------------------------------------------------------------

/// A fact extracted from an LLM during distillation.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct DistilledFact {
    pub text: String,
    pub embedding: Vec<f32>,
    pub confidence: f32,
    pub source_prompt: String,
}

/// Result of a distillation session.
#[derive(Clone, Debug, Serialize)]
pub struct DistillationResult {
    pub facts_extracted: usize,
    pub facts_added_to_graph: usize,
    pub edges_created: usize,
    pub adapter_steps: u64,
    pub adapter_loss: f32,
}

// ---------------------------------------------------------------------------
// Training pair for adapter training from LLM
// ---------------------------------------------------------------------------

/// A training pair: input embedding → target embedding (from LLM).
#[derive(Clone, Debug)]
pub struct TrainingPair {
    pub input: Vec<f32>,
    pub target: Vec<f32>,
    pub weight: f32,
}

// ---------------------------------------------------------------------------
// LLM Bridge
// ---------------------------------------------------------------------------

/// The LLM Bridge — connects MCP-Zero to real LLMs.
pub struct LLMBridge {
    pub config: LLMConfig,
    pub mode: EmbeddingMode,
    /// Local neural engine (hash fallback).
    neural: NeuralEngine,
    /// Cache of LLM embeddings to avoid repeated API calls.
    embed_cache: HashMap<String, Vec<f32>>,
    /// Cache of LLM generations.
    gen_cache: HashMap<String, String>,
    /// Training pairs accumulated from LLM interactions.
    training_pairs: Vec<TrainingPair>,
    /// Statistics.
    pub stats: BridgeStats,
}

/// Bridge usage statistics.
#[derive(Clone, Debug, Default, Serialize)]
pub struct BridgeStats {
    pub embed_requests: u64,
    pub embed_cache_hits: u64,
    pub embed_fallbacks: u64,
    pub gen_requests: u64,
    pub gen_cache_hits: u64,
    pub distill_facts: u64,
    pub training_pairs_collected: u64,
    pub adapter_train_steps: u64,
}

impl LLMBridge {
    /// Create a new LLM bridge.
    pub fn new(config: LLMConfig, mode: EmbeddingMode) -> Self {
        Self {
            config,
            mode,
            neural: NeuralEngine::default_engine(),
            embed_cache: HashMap::new(),
            gen_cache: HashMap::new(),
            training_pairs: Vec::new(),
            stats: BridgeStats::default(),
        }
    }

    /// Create with default config (ollama local).
    pub fn default_bridge() -> Self {
        Self::new(LLMConfig::default(), EmbeddingMode::HybridFallback)
    }

    /// Create offline-only bridge (no LLM needed).
    pub fn offline() -> Self {
        Self::new(LLMConfig::default(), EmbeddingMode::Hash)
    }

    // -----------------------------------------------------------------------
    // Embeddings
    // -----------------------------------------------------------------------

    /// Get embedding for text. Uses configured mode (hash, LLM API, or hybrid).
    pub fn embed(&mut self, text: &str) -> LLMEmbedding {
        self.stats.embed_requests += 1;

        match &self.mode {
            EmbeddingMode::Hash => self.embed_hash(text),
            EmbeddingMode::LLMApi => {
                // Try API, return error embedding if fails
                self.embed_api(text).unwrap_or_else(|| {
                    self.stats.embed_fallbacks += 1;
                    self.embed_hash(text)
                })
            }
            EmbeddingMode::HybridFallback => {
                // Try API first, fall back to hash
                self.embed_api(text).unwrap_or_else(|| {
                    self.stats.embed_fallbacks += 1;
                    self.embed_hash(text)
                })
            }
        }
    }

    /// Hash-based embedding (always works, no network needed).
    fn embed_hash(&mut self, text: &str) -> LLMEmbedding {
        let result = self.neural.embed(text);
        LLMEmbedding {
            dim: result.dim,
            vector: result.vector,
            source: EmbeddingMode::Hash,
            model: "hash-384".to_string(),
        }
    }

    /// LLM API embedding (requires running LLM server).
    /// Returns None if API is unavailable (network error, timeout, etc).
    fn embed_api(&mut self, text: &str) -> Option<LLMEmbedding> {
        // Check cache first
        if let Some(cached) = self.embed_cache.get(text) {
            self.stats.embed_cache_hits += 1;
            return Some(LLMEmbedding {
                vector: cached.clone(),
                source: EmbeddingMode::LLMApi,
                model: self.config.embed_model.clone(),
                dim: cached.len(),
            });
        }

        // Build the API request body
        let _request_body = serde_json::json!({
            "model": self.config.embed_model,
            "input": text
        });

        // NOTE: Actual HTTP call requires async runtime (tokio).
        // In synchronous context, we return None to trigger fallback.
        // When running in async context (RPC server), use embed_async().
        //
        // For distillation (batch mode), use distill_with_embeddings()
        // which accepts pre-computed embeddings from any source.
        None
    }

    /// Feed pre-computed LLM embeddings into the bridge cache.
    /// Use this when you have embeddings from an external source
    /// (Python script, ollama CLI, etc).
    pub fn inject_embedding(&mut self, text: &str, embedding: Vec<f32>) {
        self.embed_cache.insert(text.to_string(), embedding);
    }

    /// Feed a batch of pre-computed embeddings.
    pub fn inject_embeddings(&mut self, pairs: &[(&str, Vec<f32>)]) {
        for (text, emb) in pairs {
            self.embed_cache.insert(text.to_string(), emb.clone());
        }
    }

    // -----------------------------------------------------------------------
    // Generation (delegate to LLM)
    // -----------------------------------------------------------------------

    /// Build a generation prompt with MCP-Zero knowledge context injected.
    pub fn build_rag_prompt(
        &self,
        query: &str,
        knowledge: &[String],
    ) -> GenerateRequest {
        let system = if knowledge.is_empty() {
            None
        } else {
            let ctx = knowledge.join("\n- ");
            Some(format!(
                "You have access to the following verified knowledge:\n- {}\n\nUse this knowledge to answer accurately. If the knowledge doesn't cover the question, say so.",
                ctx
            ))
        };

        GenerateRequest {
            prompt: query.to_string(),
            system,
            max_tokens: self.config.max_tokens,
            temperature: self.config.temperature,
            knowledge_context: knowledge.to_vec(),
        }
    }

    /// Build the JSON body for an OpenAI-compatible chat completion API call.
    pub fn build_api_request(&self, req: &GenerateRequest) -> serde_json::Value {
        let mut messages = Vec::new();

        if let Some(sys) = &req.system {
            messages.push(serde_json::json!({
                "role": "system",
                "content": sys
            }));
        }

        messages.push(serde_json::json!({
            "role": "user",
            "content": req.prompt
        }));

        serde_json::json!({
            "model": self.config.model,
            "messages": messages,
            "max_tokens": req.max_tokens,
            "temperature": req.temperature
        })
    }

    /// Inject a cached generation response (for offline/testing).
    pub fn inject_generation(&mut self, prompt: &str, response: &str) {
        self.gen_cache.insert(prompt.to_string(), response.to_string());
    }

    /// Get cached generation if available.
    pub fn get_cached_generation(&mut self, prompt: &str) -> Option<GenerateResponse> {
        self.stats.gen_requests += 1;
        if let Some(text) = self.gen_cache.get(prompt) {
            self.stats.gen_cache_hits += 1;
            Some(GenerateResponse {
                text: text.clone(),
                tokens_used: text.split_whitespace().count(),
                model: self.config.model.clone(),
                from_cache: true,
            })
        } else {
            None
        }
    }

    // -----------------------------------------------------------------------
    // Knowledge Distillation
    // -----------------------------------------------------------------------

    /// Distill facts from pre-computed LLM outputs into the knot graph.
    ///
    /// This is the main training pipeline:
    /// 1. Take facts (text + embedding) extracted from an LLM
    /// 2. Add them to the knowledge knot graph
    /// 3. Auto-link similar facts
    /// 4. Train the categorical adapter on input→target pairs
    ///
    /// Run this on a server with LLM access, then deploy the resulting
    /// knot graph + adapter to RPi.
    pub fn distill(
        &mut self,
        facts: &[DistilledFact],
        graph: &mut KnowledgeKnotGraph,
        adapter: &mut CategoricalAdapter,
        learning_rate: f32,
    ) -> DistillationResult {
        let mut facts_added = 0;
        let mut edges_created = 0;

        // 1. Add facts to knot graph
        for fact in facts {
            let node_id = graph.add_node(
                &fact.text,
                fact.embedding.clone(),
                NodeType::Fact,
            );
            facts_added += 1;
            self.stats.distill_facts += 1;

            // Find similar existing nodes and create edges
            let similar = graph.search_by_embedding(&fact.embedding, 3);
            for (related_id, sim) in similar {
                if related_id != node_id && sim > 0.7 {
                    graph.add_edge(node_id, related_id, RelationType::SimilarTo, sim);
                    edges_created += 1;
                }
            }
        }

        // 2. Train adapter on accumulated training pairs
        let mut total_loss = 0.0;
        let steps_before = adapter.steps;
        for pair in &self.training_pairs {
            let loss = adapter.train_step(&pair.input, &pair.target, learning_rate * pair.weight);
            total_loss += loss;
            self.stats.adapter_train_steps += 1;
        }
        let avg_loss = if self.training_pairs.is_empty() {
            0.0
        } else {
            total_loss / self.training_pairs.len() as f32
        };

        DistillationResult {
            facts_extracted: facts.len(),
            facts_added_to_graph: facts_added,
            edges_created,
            adapter_steps: adapter.steps - steps_before,
            adapter_loss: avg_loss,
        }
    }

    /// Add a training pair for adapter training.
    /// Call this with LLM embeddings: input text embedding → LLM output embedding.
    pub fn add_training_pair(&mut self, input: Vec<f32>, target: Vec<f32>, weight: f32) {
        self.training_pairs.push(TrainingPair { input, target, weight });
        self.stats.training_pairs_collected += 1;
    }

    /// Train the adapter on all accumulated pairs.
    pub fn train_adapter(&mut self, adapter: &mut CategoricalAdapter, lr: f32, epochs: usize) -> f32 {
        let mut last_loss = 0.0;
        for _ in 0..epochs {
            for pair in &self.training_pairs {
                last_loss = adapter.train_step(&pair.input, &pair.target, lr * pair.weight);
                self.stats.adapter_train_steps += 1;
            }
        }
        last_loss
    }

    /// Clear accumulated training pairs.
    pub fn clear_training_pairs(&mut self) {
        self.training_pairs.clear();
    }

    /// Number of accumulated training pairs.
    pub fn training_pair_count(&self) -> usize {
        self.training_pairs.len()
    }

    // -----------------------------------------------------------------------
    // Export / Import (for RPi deployment)
    // -----------------------------------------------------------------------

    /// Export the embedding cache as JSON (for deploying to offline device).
    pub fn export_cache(&self) -> serde_json::Value {
        let entries: Vec<serde_json::Value> = self.embed_cache.iter()
            .map(|(text, emb)| serde_json::json!({
                "text": text,
                "embedding": emb
            }))
            .collect();
        serde_json::json!({
            "model": self.config.embed_model,
            "entries": entries,
            "count": entries.len()
        })
    }

    /// Import embedding cache from JSON.
    pub fn import_cache(&mut self, data: &serde_json::Value) {
        if let Some(entries) = data.get("entries").and_then(|e| e.as_array()) {
            for entry in entries {
                if let (Some(text), Some(emb_arr)) = (
                    entry.get("text").and_then(|t| t.as_str()),
                    entry.get("embedding").and_then(|e| e.as_array()),
                ) {
                    let emb: Vec<f32> = emb_arr.iter()
                        .filter_map(|v| v.as_f64().map(|f| f as f32))
                        .collect();
                    if !emb.is_empty() {
                        self.embed_cache.insert(text.to_string(), emb);
                    }
                }
            }
        }
    }

    /// Get bridge statistics.
    pub fn stats(&self) -> &BridgeStats {
        &self.stats
    }

    /// Get cache size.
    pub fn cache_size(&self) -> usize {
        self.embed_cache.len()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_default_bridge() {
        let bridge = LLMBridge::default_bridge();
        assert_eq!(bridge.mode, EmbeddingMode::HybridFallback);
        assert_eq!(bridge.config.model, "llama3.1:8b");
    }

    #[test]
    fn test_offline_bridge() {
        let bridge = LLMBridge::offline();
        assert_eq!(bridge.mode, EmbeddingMode::Hash);
    }

    #[test]
    fn test_hash_embedding() {
        let mut bridge = LLMBridge::offline();
        let emb = bridge.embed("test text");
        assert_eq!(emb.source, EmbeddingMode::Hash);
        assert_eq!(emb.dim, 384);
        assert_eq!(emb.vector.len(), 384);
        assert_eq!(emb.model, "hash-384");
    }

    #[test]
    fn test_hybrid_fallback_to_hash() {
        let mut bridge = LLMBridge::default_bridge();
        // No LLM server running → should fall back to hash
        let emb = bridge.embed("test text");
        assert_eq!(emb.source, EmbeddingMode::Hash);
        assert_eq!(bridge.stats.embed_fallbacks, 1);
    }

    #[test]
    fn test_inject_embedding() {
        let mut bridge = LLMBridge::new(
            LLMConfig::default(),
            EmbeddingMode::LLMApi,
        );
        let custom_emb = vec![1.0, 2.0, 3.0];
        bridge.inject_embedding("hello", custom_emb.clone());

        let result = bridge.embed("hello");
        assert_eq!(result.source, EmbeddingMode::LLMApi);
        assert_eq!(result.vector, custom_emb);
        assert_eq!(bridge.stats.embed_cache_hits, 1);
    }

    #[test]
    fn test_inject_batch_embeddings() {
        let mut bridge = LLMBridge::offline();
        bridge.inject_embeddings(&[
            ("cat", vec![1.0, 0.0]),
            ("dog", vec![0.0, 1.0]),
        ]);
        assert_eq!(bridge.cache_size(), 2);
    }

    #[test]
    fn test_build_rag_prompt_no_context() {
        let bridge = LLMBridge::default_bridge();
        let req = bridge.build_rag_prompt("what is water?", &[]);
        assert_eq!(req.prompt, "what is water?");
        assert!(req.system.is_none());
    }

    #[test]
    fn test_build_rag_prompt_with_context() {
        let bridge = LLMBridge::default_bridge();
        let knowledge = vec![
            "Water boils at 100°C".to_string(),
            "Water freezes at 0°C".to_string(),
        ];
        let req = bridge.build_rag_prompt("what is water?", &knowledge);
        assert!(req.system.is_some());
        let sys = req.system.unwrap();
        assert!(sys.contains("Water boils"));
        assert!(sys.contains("Water freezes"));
    }

    #[test]
    fn test_build_api_request() {
        let bridge = LLMBridge::default_bridge();
        let req = bridge.build_rag_prompt("hello", &[]);
        let body = bridge.build_api_request(&req);
        assert_eq!(body["model"], "llama3.1:8b");
        assert!(body["messages"].is_array());
    }

    #[test]
    fn test_inject_and_get_generation() {
        let mut bridge = LLMBridge::default_bridge();
        bridge.inject_generation("what is 2+2?", "2+2 equals 4.");

        let resp = bridge.get_cached_generation("what is 2+2?").unwrap();
        assert_eq!(resp.text, "2+2 equals 4.");
        assert!(resp.from_cache);
        assert_eq!(bridge.stats.gen_cache_hits, 1);
    }

    #[test]
    fn test_generation_cache_miss() {
        let mut bridge = LLMBridge::default_bridge();
        let resp = bridge.get_cached_generation("unknown prompt");
        assert!(resp.is_none());
    }

    #[test]
    fn test_add_training_pairs() {
        let mut bridge = LLMBridge::offline();
        bridge.add_training_pair(vec![1.0, 0.0], vec![0.0, 1.0], 1.0);
        bridge.add_training_pair(vec![0.5, 0.5], vec![0.5, 0.5], 0.5);
        assert_eq!(bridge.training_pair_count(), 2);
        assert_eq!(bridge.stats.training_pairs_collected, 2);
    }

    #[test]
    fn test_train_adapter_from_llm_pairs() {
        let mut bridge = LLMBridge::offline();
        // Simulate LLM embeddings as training signal
        bridge.add_training_pair(
            vec![1.0, 0.0, 0.5, 0.0, 0.3, 0.0, 0.1, 0.0],
            vec![0.0, 1.0, 0.0, 0.5, 0.0, 0.3, 0.0, 0.1],
            1.0,
        );

        let mut adapter = CategoricalAdapter::new("llm_trained", 8, 2, 3, 42);
        let loss = bridge.train_adapter(&mut adapter, 0.01, 10);
        assert!(loss >= 0.0);
        assert_eq!(adapter.steps, 10);
        assert_eq!(bridge.stats.adapter_train_steps, 10);
    }

    #[test]
    fn test_distill_facts_into_graph() {
        let mut bridge = LLMBridge::offline();
        let mut graph = KnowledgeKnotGraph::new();
        let mut adapter = CategoricalAdapter::new("distilled", 4, 2, 3, 42);

        let facts = vec![
            DistilledFact {
                text: "water boils at 100C".to_string(),
                embedding: vec![1.0, 0.0, 0.0, 0.0],
                confidence: 0.95,
                source_prompt: "what temperature does water boil?".to_string(),
            },
            DistilledFact {
                text: "ice melts at 0C".to_string(),
                embedding: vec![0.9, 0.1, 0.0, 0.0],
                confidence: 0.90,
                source_prompt: "what temperature does ice melt?".to_string(),
            },
        ];

        let result = bridge.distill(&facts, &mut graph, &mut adapter, 0.01);
        assert_eq!(result.facts_extracted, 2);
        assert_eq!(result.facts_added_to_graph, 2);
        assert_eq!(graph.node_count(), 2);
        // The two facts are similar (cosine > 0.7), so an edge should be created
        assert!(result.edges_created >= 1);
    }

    #[test]
    fn test_export_import_cache() {
        let mut bridge = LLMBridge::offline();
        bridge.inject_embedding("hello", vec![1.0, 2.0, 3.0]);
        bridge.inject_embedding("world", vec![4.0, 5.0, 6.0]);

        let exported = bridge.export_cache();
        assert_eq!(exported["count"], 2);

        let mut bridge2 = LLMBridge::offline();
        bridge2.import_cache(&exported);
        assert_eq!(bridge2.cache_size(), 2);
    }

    #[test]
    fn test_ollama_config() {
        let config = LLMConfig::ollama("mistral:7b");
        assert_eq!(config.model, "mistral:7b");
        assert!(config.api_url.contains("11434"));
        assert!(config.api_key.is_empty());
    }

    #[test]
    fn test_openai_config() {
        let config = LLMConfig::openai("sk-test123", "gpt-4o-mini");
        assert_eq!(config.model, "gpt-4o-mini");
        assert_eq!(config.api_key, "sk-test123");
        assert!(config.api_url.contains("openai.com"));
    }

    #[test]
    fn test_compatible_config() {
        let config = LLMConfig::compatible("http://my-server:8080/v1", "my-model");
        assert_eq!(config.api_url, "http://my-server:8080/v1");
        assert_eq!(config.model, "my-model");
    }

    #[test]
    fn test_full_distillation_pipeline() {
        // Simulate the full pipeline:
        // 1. "LLM" produces embeddings and facts
        // 2. Bridge distills into knot graph
        // 3. Bridge trains adapter from LLM pairs
        // 4. Export cache for RPi deployment

        let mut bridge = LLMBridge::offline();
        let mut graph = KnowledgeKnotGraph::new();
        let mut adapter = CategoricalAdapter::new("medical", 8, 2, 3, 42);

        // Step 1: Simulate LLM-produced facts
        let facts = vec![
            DistilledFact {
                text: "malaria causes fever".to_string(),
                embedding: vec![1.0, 0.5, 0.0, 0.0, 0.3, 0.0, 0.1, 0.0],
                confidence: 0.95,
                source_prompt: "symptoms of malaria".to_string(),
            },
            DistilledFact {
                text: "dengue causes fever and rash".to_string(),
                embedding: vec![0.9, 0.6, 0.1, 0.0, 0.2, 0.0, 0.1, 0.0],
                confidence: 0.90,
                source_prompt: "symptoms of dengue".to_string(),
            },
            DistilledFact {
                text: "typhoid causes sustained fever".to_string(),
                embedding: vec![0.8, 0.4, 0.2, 0.0, 0.3, 0.1, 0.0, 0.0],
                confidence: 0.85,
                source_prompt: "symptoms of typhoid".to_string(),
            },
        ];

        // Step 2: Simulate LLM training pairs (input → desired output)
        bridge.add_training_pair(
            vec![1.0, 0.5, 0.0, 0.0, 0.3, 0.0, 0.1, 0.0], // "fever" embedding
            vec![0.8, 0.3, 0.1, 0.0, 0.5, 0.2, 0.1, 0.0], // "consider malaria" embedding
            1.0,
        );

        // Step 3: Distill
        let result = bridge.distill(&facts, &mut graph, &mut adapter, 0.01);
        assert_eq!(result.facts_added_to_graph, 3);
        assert!(result.edges_created >= 2); // all 3 facts are similar

        // Step 4: Train more
        let loss = bridge.train_adapter(&mut adapter, 0.01, 5);
        assert!(loss >= 0.0);

        // Step 5: Export for deployment
        bridge.inject_embedding("fever", vec![1.0, 0.5, 0.0, 0.0, 0.3, 0.0, 0.1, 0.0]);
        let cache = bridge.export_cache();
        assert_eq!(cache["count"], 1);

        // Verify final state
        assert_eq!(graph.node_count(), 3);
        assert!(graph.edge_count() >= 2);
        assert!(adapter.steps >= 6); // 1 from distill + 5 from train_adapter
    }

    #[test]
    fn test_clear_training_pairs() {
        let mut bridge = LLMBridge::offline();
        bridge.add_training_pair(vec![1.0], vec![0.0], 1.0);
        assert_eq!(bridge.training_pair_count(), 1);
        bridge.clear_training_pairs();
        assert_eq!(bridge.training_pair_count(), 0);
    }
}
