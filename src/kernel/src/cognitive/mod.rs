//! Cognitive Engine — Rust-native symbolic cognition
//!
//! Replaces the Python cognitive layer with zero-copy vector math in Rust.
//! Python is only used as a thin LLM inference wrapper.
//!
//! Components:
//!   - `Reasoner` — symbol mapping, contradiction injection, entropic collapse
//!   - `EntropyEngine` — entropic intent fields, delta injection, collapse detection
//!   - `SymbolBridge` — symbol emergence through entropic burst mechanisms
//!   - `KnowledgeStore` — file-backed fact storage with cosine similarity search
//!   - `CogLoop` — orchestrates the intention-entropy-contradiction cycle
//!   - `ModalityFold` — multimodal perception through entropic signatures
//!   - `MetaContractSystem` — contract evolution through contradiction exposure
//!   - `EntropyGraph` — neural network entropy tracking through computation layers
//!   - `BinaryKnowledgeStore` — redb + bincode binary knowledge storage
//!   - `NeuralEngine` — Rust-native inference (hash fallback + tract ONNX)
//!   - `CHTEngine` — Categorical Holographic Tokens (100x token compression)
//!   - `CategoricalAdapter` — Para 2-category adapter with braid init (replaces LoRA)
//!   - `ToposNetwork` — sheaf-theoretic distributed intelligence
//!   - `KnowledgeKnotGraph` — knot-theoretic knowledge graph (facts as nodes, braids as edges)
//!   - `CognitiveFabric` — unified orchestrator wiring all 14+ modules together
//!   - `HyperdimensionalEngine` — topological HDC semantic engine (replaces hash embeddings)

pub mod types;
pub mod reasoner;
pub mod entropy;
pub mod symbols;
pub mod knowledge;
pub mod cog_loop;
pub mod modality;
pub mod contract;
pub mod entropy_graph;
pub mod binary_store;
pub mod neural;
pub mod cht;
pub mod trainer;
pub mod topos;
pub mod knowledge_knot;
pub mod cognitive_fabric;
pub mod benchmark;
pub mod llm_bridge;
pub mod hyperdimensional;

pub use types::CogVec;
pub use reasoner::Reasoner;
pub use entropy::EntropyEngine;
pub use symbols::SymbolBridge;
pub use knowledge::KnowledgeStore;
pub use cog_loop::CogLoop;
pub use modality::ModalityFold;
pub use contract::MetaContractSystem;
pub use entropy_graph::EntropyGraph;
pub use binary_store::BinaryKnowledgeStore;
pub use neural::NeuralEngine;
pub use cht::CHTEngine;
pub use trainer::CategoricalAdapter;
pub use topos::ToposNetwork;
pub use knowledge_knot::KnowledgeKnotGraph;
pub use cognitive_fabric::CognitiveFabric;
pub use llm_bridge::LLMBridge;
pub use hyperdimensional::HyperdimensionalEngine;
