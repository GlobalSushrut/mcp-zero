//! Knowledge Knot Graph — topological knowledge representation.
//!
//! Facts are nodes. Relationships between facts are edges encoded as
//! **braid words** (from knot theory). This gives each relationship a
//! topological invariant that measures its complexity and type.
//!
//! Key properties:
//!   - **Writhe** of a relationship braid = directional bias (positive/negative)
//!   - **Crossing number** = relationship complexity
//!   - **Braid composition** = chaining relationships (A→B→C = braid(AB) · braid(BC))
//!   - **Knot equivalence** = two relationships are "the same kind" if their
//!     braids have the same Jones-like invariant
//!
//! Integrates with:
//!   - `KnowledgeStore` / `BinaryKnowledgeStore` for fact persistence
//!   - `NeuralEngine` for embedding-based similarity
//!   - `CHTEngine` for compressed token representations
//!   - `CategoricalAdapter` for domain-adapted traversal

use serde::{Serialize, Deserialize};
use std::collections::HashMap;
use super::trainer::BraidWord;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// A node in the knowledge knot graph.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct KnotNode {
    pub id: u64,
    pub text: String,
    pub embedding: Vec<f32>,
    pub node_type: NodeType,
    pub access_count: u64,
    pub created_at: u64,
}

/// Type of knowledge node.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum NodeType {
    Fact,
    Concept,
    Symbol,
    Intention,
    Contradiction,
}

/// A relationship edge encoded as a braid word.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct KnotEdge {
    pub source: u64,
    pub target: u64,
    pub relation: RelationType,
    pub braid: BraidWord,
    pub weight: f32,
    /// Writhe = sum of crossing signs (+1 or -1 for each generator).
    pub writhe: i32,
    /// Crossing number = length of braid word.
    pub crossing_number: usize,
}

/// Semantic relationship type.
#[derive(Clone, Debug, PartialEq, Serialize, Deserialize)]
pub enum RelationType {
    /// A implies B
    Implies,
    /// A contradicts B
    Contradicts,
    /// A is part of B
    PartOf,
    /// A is similar to B
    SimilarTo,
    /// A causes B
    Causes,
    /// A evolves into B (temporal)
    EvolvesInto,
    /// Custom relation
    Custom(String),
}

impl RelationType {
    /// Map relation type to braid strand count (topological complexity).
    fn strand_count(&self) -> usize {
        match self {
            RelationType::SimilarTo => 2,     // simplest
            RelationType::Implies => 3,
            RelationType::PartOf => 3,
            RelationType::Causes => 4,
            RelationType::Contradicts => 4,   // more complex
            RelationType::EvolvesInto => 5,   // most complex
            RelationType::Custom(_) => 3,
        }
    }

    /// Map relation type to braid length (more complex = longer braid).
    fn braid_length(&self) -> usize {
        match self {
            RelationType::SimilarTo => 2,
            RelationType::Implies => 4,
            RelationType::PartOf => 3,
            RelationType::Causes => 6,
            RelationType::Contradicts => 8,
            RelationType::EvolvesInto => 10,
            RelationType::Custom(_) => 4,
        }
    }
}

/// Result of a graph traversal / query.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct TraversalResult {
    pub path: Vec<u64>,
    pub edges: Vec<KnotEdge>,
    pub total_writhe: i32,
    pub total_crossings: usize,
    pub path_complexity: f32,
}

/// Summary statistics of the knot graph.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct KnotGraphStats {
    pub node_count: usize,
    pub edge_count: usize,
    pub avg_writhe: f32,
    pub avg_crossings: f32,
    pub connected_components: usize,
    pub node_types: HashMap<String, usize>,
    pub relation_types: HashMap<String, usize>,
}

// ---------------------------------------------------------------------------
// Knowledge Knot Graph
// ---------------------------------------------------------------------------

/// The knowledge knot graph.
pub struct KnowledgeKnotGraph {
    nodes: HashMap<u64, KnotNode>,
    edges: Vec<KnotEdge>,
    /// Adjacency: node_id → list of edge indices.
    adjacency: HashMap<u64, Vec<usize>>,
    next_id: u64,
    /// Seed for deterministic braid generation.
    braid_seed: u64,
}

impl KnowledgeKnotGraph {
    pub fn new() -> Self {
        Self {
            nodes: HashMap::new(),
            edges: Vec::new(),
            adjacency: HashMap::new(),
            next_id: 1,
            braid_seed: 0xBA07,
        }
    }

    // -----------------------------------------------------------------------
    // Node operations
    // -----------------------------------------------------------------------

    /// Add a knowledge node.
    pub fn add_node(&mut self, text: &str, embedding: Vec<f32>, node_type: NodeType) -> u64 {
        let id = self.next_id;
        self.next_id += 1;
        self.nodes.insert(id, KnotNode {
            id,
            text: text.to_string(),
            embedding,
            node_type,
            access_count: 0,
            created_at: id, // simple monotonic timestamp
        });
        self.adjacency.entry(id).or_default();
        id
    }

    /// Get a node by ID.
    pub fn get_node(&self, id: u64) -> Option<&KnotNode> {
        self.nodes.get(&id)
    }

    /// Get mutable node (increments access count).
    pub fn touch_node(&mut self, id: u64) -> Option<&KnotNode> {
        if let Some(node) = self.nodes.get_mut(&id) {
            node.access_count += 1;
            Some(node)
        } else {
            None
        }
    }

    /// Find nodes by embedding similarity (cosine).
    pub fn search_by_embedding(&self, query: &[f32], top_k: usize) -> Vec<(u64, f32)> {
        let mut scored: Vec<(u64, f32)> = self.nodes.values()
            .map(|n| (n.id, cosine_sim(&n.embedding, query)))
            .collect();
        scored.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        scored.truncate(top_k);
        scored
    }

    /// Find nodes by type.
    pub fn nodes_by_type(&self, node_type: &NodeType) -> Vec<&KnotNode> {
        self.nodes.values().filter(|n| &n.node_type == node_type).collect()
    }

    /// Total node count.
    pub fn node_count(&self) -> usize {
        self.nodes.len()
    }

    // -----------------------------------------------------------------------
    // Edge operations (knot-theoretic relationships)
    // -----------------------------------------------------------------------

    /// Add a relationship between two nodes.
    ///
    /// The relationship is encoded as a braid word whose topology reflects
    /// the semantic type and complexity of the relationship.
    pub fn add_edge(&mut self, source: u64, target: u64, relation: RelationType, weight: f32) -> Option<usize> {
        if !self.nodes.contains_key(&source) || !self.nodes.contains_key(&target) {
            return None;
        }

        // Generate braid from relation type + node pair seed
        let strands = relation.strand_count();
        let length = relation.braid_length();
        let seed = self.braid_seed
            .wrapping_add(source.wrapping_mul(0x9e3779b97f4a7c15))
            .wrapping_add(target.wrapping_mul(0x517cc1b727220a95));
        self.braid_seed = self.braid_seed.wrapping_add(1);

        let braid = BraidWord::random(strands, length, seed);
        let writhe = compute_writhe(&braid);
        let crossing_number = braid.generators.len();

        let edge_idx = self.edges.len();
        self.edges.push(KnotEdge {
            source,
            target,
            relation,
            braid,
            weight,
            writhe,
            crossing_number,
        });

        self.adjacency.entry(source).or_default().push(edge_idx);
        self.adjacency.entry(target).or_default().push(edge_idx);

        Some(edge_idx)
    }

    /// Get edges from a node.
    pub fn edges_from(&self, node_id: u64) -> Vec<&KnotEdge> {
        self.adjacency.get(&node_id)
            .map(|indices| indices.iter()
                .filter_map(|&i| self.edges.get(i))
                .filter(|e| e.source == node_id)
                .collect())
            .unwrap_or_default()
    }

    /// Get all edges connected to a node (both directions).
    pub fn edges_of(&self, node_id: u64) -> Vec<&KnotEdge> {
        self.adjacency.get(&node_id)
            .map(|indices| indices.iter()
                .filter_map(|&i| self.edges.get(i))
                .collect())
            .unwrap_or_default()
    }

    /// Total edge count.
    pub fn edge_count(&self) -> usize {
        self.edges.len()
    }

    // -----------------------------------------------------------------------
    // Graph traversal (knot-aware)
    // -----------------------------------------------------------------------

    /// Find shortest path between two nodes using BFS.
    /// Returns the path and accumulated knot properties.
    pub fn find_path(&self, from: u64, to: u64) -> Option<TraversalResult> {
        if from == to {
            return Some(TraversalResult {
                path: vec![from],
                edges: vec![],
                total_writhe: 0,
                total_crossings: 0,
                path_complexity: 0.0,
            });
        }

        // BFS
        let mut visited: HashMap<u64, (u64, usize)> = HashMap::new(); // node → (parent, edge_idx)
        let mut queue = std::collections::VecDeque::new();
        queue.push_back(from);
        visited.insert(from, (from, usize::MAX));

        while let Some(current) = queue.pop_front() {
            if current == to {
                // Reconstruct path
                let mut path = Vec::new();
                let mut edges = Vec::new();
                let mut node = to;
                while node != from {
                    path.push(node);
                    let (parent, edge_idx) = visited[&node];
                    if edge_idx != usize::MAX {
                        edges.push(self.edges[edge_idx].clone());
                    }
                    node = parent;
                }
                path.push(from);
                path.reverse();
                edges.reverse();

                let total_writhe: i32 = edges.iter().map(|e| e.writhe).sum();
                let total_crossings: usize = edges.iter().map(|e| e.crossing_number).sum();
                let path_complexity = if edges.is_empty() { 0.0 } else {
                    total_crossings as f32 / edges.len() as f32
                };

                return Some(TraversalResult {
                    path,
                    edges,
                    total_writhe,
                    total_crossings,
                    path_complexity,
                });
            }

            if let Some(adj) = self.adjacency.get(&current) {
                for &edge_idx in adj {
                    let edge = &self.edges[edge_idx];
                    let neighbor = if edge.source == current { edge.target } else { edge.source };
                    if !visited.contains_key(&neighbor) {
                        visited.insert(neighbor, (current, edge_idx));
                        queue.push_back(neighbor);
                    }
                }
            }
        }

        None // No path found
    }

    /// Get neighbors of a node, sorted by edge weight.
    pub fn neighbors(&self, node_id: u64) -> Vec<(u64, f32, &RelationType)> {
        let mut result: Vec<(u64, f32, &RelationType)> = self.edges_of(node_id)
            .into_iter()
            .map(|e| {
                let neighbor = if e.source == node_id { e.target } else { e.source };
                (neighbor, e.weight, &e.relation)
            })
            .collect();
        result.sort_by(|a, b| b.1.partial_cmp(&a.1).unwrap_or(std::cmp::Ordering::Equal));
        result
    }

    // -----------------------------------------------------------------------
    // Integration helpers
    // -----------------------------------------------------------------------

    /// Import a fact from the old KnowledgeStore into the knot graph.
    pub fn import_fact(&mut self, text: &str, embedding: Vec<f32>) -> u64 {
        self.add_node(text, embedding, NodeType::Fact)
    }

    /// Import a symbol from the Reasoner/SymbolBridge.
    pub fn import_symbol(&mut self, name: &str, embedding: Vec<f32>) -> u64 {
        self.add_node(name, embedding, NodeType::Symbol)
    }

    /// Record a contradiction between two nodes.
    pub fn record_contradiction(&mut self, node_a: u64, node_b: u64, intensity: f32) -> Option<usize> {
        self.add_edge(node_a, node_b, RelationType::Contradicts, intensity)
    }

    /// Record an implication.
    pub fn record_implication(&mut self, premise: u64, conclusion: u64, confidence: f32) -> Option<usize> {
        self.add_edge(premise, conclusion, RelationType::Implies, confidence)
    }

    /// Record similarity (auto-detected from embeddings).
    pub fn auto_link_similar(&mut self, threshold: f32) -> usize {
        let node_ids: Vec<u64> = self.nodes.keys().cloned().collect();
        let mut added = 0;

        for i in 0..node_ids.len() {
            for j in (i + 1)..node_ids.len() {
                let a = &self.nodes[&node_ids[i]];
                let b = &self.nodes[&node_ids[j]];
                let sim = cosine_sim(&a.embedding, &b.embedding);
                if sim >= threshold {
                    // Check if edge already exists
                    let exists = self.edges.iter().any(|e|
                        (e.source == node_ids[i] && e.target == node_ids[j]) ||
                        (e.source == node_ids[j] && e.target == node_ids[i])
                    );
                    if !exists {
                        self.add_edge(node_ids[i], node_ids[j], RelationType::SimilarTo, sim);
                        added += 1;
                    }
                }
            }
        }
        added
    }

    // -----------------------------------------------------------------------
    // Statistics
    // -----------------------------------------------------------------------

    /// Compute graph statistics.
    pub fn stats(&self) -> KnotGraphStats {
        let mut node_types: HashMap<String, usize> = HashMap::new();
        for n in self.nodes.values() {
            let key = format!("{:?}", n.node_type);
            *node_types.entry(key).or_default() += 1;
        }

        let mut relation_types: HashMap<String, usize> = HashMap::new();
        for e in &self.edges {
            let key = format!("{:?}", e.relation);
            *relation_types.entry(key).or_default() += 1;
        }

        let avg_writhe = if self.edges.is_empty() { 0.0 } else {
            self.edges.iter().map(|e| e.writhe as f32).sum::<f32>() / self.edges.len() as f32
        };
        let avg_crossings = if self.edges.is_empty() { 0.0 } else {
            self.edges.iter().map(|e| e.crossing_number as f32).sum::<f32>() / self.edges.len() as f32
        };

        // Simple connected components via union-find
        let components = self.count_components();

        KnotGraphStats {
            node_count: self.nodes.len(),
            edge_count: self.edges.len(),
            avg_writhe,
            avg_crossings,
            connected_components: components,
            node_types,
            relation_types,
        }
    }

    fn count_components(&self) -> usize {
        let mut visited = std::collections::HashSet::new();
        let mut components = 0;
        for &id in self.nodes.keys() {
            if !visited.contains(&id) {
                components += 1;
                // BFS from this node
                let mut queue = std::collections::VecDeque::new();
                queue.push_back(id);
                visited.insert(id);
                while let Some(current) = queue.pop_front() {
                    if let Some(adj) = self.adjacency.get(&current) {
                        for &edge_idx in adj {
                            let edge = &self.edges[edge_idx];
                            let neighbor = if edge.source == current { edge.target } else { edge.source };
                            if visited.insert(neighbor) {
                                queue.push_back(neighbor);
                            }
                        }
                    }
                }
            }
        }
        components
    }
}

// ---------------------------------------------------------------------------
// Knot invariants
// ---------------------------------------------------------------------------

/// Compute the writhe of a braid word.
/// Writhe = sum of signs of all crossings (+1 for σ_i, -1 for σ_i⁻¹).
fn compute_writhe(braid: &BraidWord) -> i32 {
    braid.generators.iter().map(|&g| if g > 0 { 1i32 } else { -1i32 }).sum()
}

fn cosine_sim(a: &[f32], b: &[f32]) -> f32 {
    if a.len() != b.len() || a.is_empty() { return 0.0; }
    let dot: f32 = a.iter().zip(b.iter()).map(|(x, y)| x * y).sum();
    let na: f32 = a.iter().map(|x| x * x).sum::<f32>().sqrt();
    let nb: f32 = b.iter().map(|x| x * x).sum::<f32>().sqrt();
    if na < 1e-10 || nb < 1e-10 { return 0.0; }
    dot / (na * nb)
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn make_embedding(seed: u64, dim: usize) -> Vec<f32> {
        let mut v = vec![0.0f32; dim];
        let mut s = seed;
        for val in v.iter_mut() {
            s = s.wrapping_mul(6364136223846793005).wrapping_add(1);
            *val = ((s >> 33) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
        }
        v
    }

    #[test]
    fn test_add_node() {
        let mut g = KnowledgeKnotGraph::new();
        let id = g.add_node("water boils at 100C", make_embedding(1, 8), NodeType::Fact);
        assert_eq!(id, 1);
        assert_eq!(g.node_count(), 1);
        assert!(g.get_node(id).is_some());
    }

    #[test]
    fn test_add_edge() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("heat", make_embedding(1, 8), NodeType::Concept);
        let b = g.add_node("boiling", make_embedding(2, 8), NodeType::Concept);
        let edge = g.add_edge(a, b, RelationType::Causes, 0.9);
        assert!(edge.is_some());
        assert_eq!(g.edge_count(), 1);
    }

    #[test]
    fn test_edge_has_knot_properties() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", make_embedding(1, 4), NodeType::Fact);
        let b = g.add_node("B", make_embedding(2, 4), NodeType::Fact);
        g.add_edge(a, b, RelationType::Contradicts, 0.8);

        let edges = g.edges_from(a);
        assert_eq!(edges.len(), 1);
        let e = &edges[0];
        assert_eq!(e.crossing_number, e.braid.generators.len());
        // Contradicts has 4 strands, 8 length
        assert_eq!(e.braid.strands, 4);
        assert_eq!(e.braid.generators.len(), 8);
    }

    #[test]
    fn test_different_relations_different_braids() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", make_embedding(1, 4), NodeType::Fact);
        let b = g.add_node("B", make_embedding(2, 4), NodeType::Fact);
        let c = g.add_node("C", make_embedding(3, 4), NodeType::Fact);

        g.add_edge(a, b, RelationType::SimilarTo, 0.9);
        g.add_edge(a, c, RelationType::Contradicts, 0.7);

        let similar_edge = &g.edges[0];
        let contra_edge = &g.edges[1];

        // Contradicts should be more complex than SimilarTo
        assert!(contra_edge.crossing_number > similar_edge.crossing_number);
    }

    #[test]
    fn test_find_path() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", make_embedding(1, 4), NodeType::Fact);
        let b = g.add_node("B", make_embedding(2, 4), NodeType::Fact);
        let c = g.add_node("C", make_embedding(3, 4), NodeType::Fact);

        g.add_edge(a, b, RelationType::Implies, 0.8);
        g.add_edge(b, c, RelationType::Implies, 0.7);

        let result = g.find_path(a, c).unwrap();
        assert_eq!(result.path, vec![a, b, c]);
        assert_eq!(result.edges.len(), 2);
        assert!(result.total_crossings > 0);
    }

    #[test]
    fn test_find_path_no_connection() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", make_embedding(1, 4), NodeType::Fact);
        let b = g.add_node("B", make_embedding(2, 4), NodeType::Fact);
        // No edge between them
        assert!(g.find_path(a, b).is_none());
    }

    #[test]
    fn test_find_path_self() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", make_embedding(1, 4), NodeType::Fact);
        let result = g.find_path(a, a).unwrap();
        assert_eq!(result.path, vec![a]);
        assert_eq!(result.total_crossings, 0);
    }

    #[test]
    fn test_search_by_embedding() {
        let mut g = KnowledgeKnotGraph::new();
        let e1 = vec![1.0, 0.0, 0.0, 0.0];
        let e2 = vec![0.0, 1.0, 0.0, 0.0];
        g.add_node("aligned", e1.clone(), NodeType::Fact);
        g.add_node("orthogonal", e2, NodeType::Fact);

        let results = g.search_by_embedding(&e1, 2);
        assert_eq!(results.len(), 2);
        assert_eq!(results[0].0, 1); // "aligned" should be first
        assert!(results[0].1 > results[1].1);
    }

    #[test]
    fn test_import_fact_and_symbol() {
        let mut g = KnowledgeKnotGraph::new();
        let f = g.import_fact("gravity pulls things down", vec![0.1, 0.2]);
        let s = g.import_symbol("gravity", vec![0.15, 0.25]);
        assert_eq!(g.get_node(f).unwrap().node_type, NodeType::Fact);
        assert_eq!(g.get_node(s).unwrap().node_type, NodeType::Symbol);
    }

    #[test]
    fn test_record_contradiction() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("earth is flat", vec![1.0, 0.0], NodeType::Fact);
        let b = g.add_node("earth is round", vec![0.0, 1.0], NodeType::Fact);
        g.record_contradiction(a, b, 0.95);
        assert_eq!(g.edge_count(), 1);
        assert_eq!(g.edges[0].relation, RelationType::Contradicts);
    }

    #[test]
    fn test_auto_link_similar() {
        let mut g = KnowledgeKnotGraph::new();
        g.add_node("cat", vec![1.0, 0.1, 0.0], NodeType::Concept);
        g.add_node("kitten", vec![0.95, 0.15, 0.0], NodeType::Concept);
        g.add_node("car", vec![0.0, 0.0, 1.0], NodeType::Concept);

        let linked = g.auto_link_similar(0.9);
        assert_eq!(linked, 1); // only cat-kitten should link
        assert_eq!(g.edge_count(), 1);
    }

    #[test]
    fn test_neighbors() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", vec![1.0], NodeType::Fact);
        let b = g.add_node("B", vec![0.5], NodeType::Fact);
        let c = g.add_node("C", vec![0.0], NodeType::Fact);
        g.add_edge(a, b, RelationType::Implies, 0.8);
        g.add_edge(a, c, RelationType::SimilarTo, 0.3);

        let neighbors = g.neighbors(a);
        assert_eq!(neighbors.len(), 2);
        assert_eq!(neighbors[0].0, b); // higher weight first
    }

    #[test]
    fn test_stats() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", vec![1.0], NodeType::Fact);
        let b = g.add_node("B", vec![0.5], NodeType::Concept);
        let c = g.add_node("C", vec![0.0], NodeType::Symbol);
        g.add_edge(a, b, RelationType::Implies, 0.8);
        g.add_edge(b, c, RelationType::Causes, 0.6);

        let stats = g.stats();
        assert_eq!(stats.node_count, 3);
        assert_eq!(stats.edge_count, 2);
        assert_eq!(stats.connected_components, 1);
        assert_eq!(stats.node_types.len(), 3);
    }

    #[test]
    fn test_connected_components() {
        let mut g = KnowledgeKnotGraph::new();
        let a = g.add_node("A", vec![1.0], NodeType::Fact);
        let b = g.add_node("B", vec![0.5], NodeType::Fact);
        let c = g.add_node("C", vec![0.0], NodeType::Fact);
        let d = g.add_node("D", vec![0.2], NodeType::Fact);
        g.add_edge(a, b, RelationType::SimilarTo, 0.9);
        g.add_edge(c, d, RelationType::SimilarTo, 0.8);
        // Two components: {a,b} and {c,d}

        let stats = g.stats();
        assert_eq!(stats.connected_components, 2);
    }

    #[test]
    fn test_touch_node() {
        let mut g = KnowledgeKnotGraph::new();
        let id = g.add_node("test", vec![1.0], NodeType::Fact);
        assert_eq!(g.get_node(id).unwrap().access_count, 0);
        g.touch_node(id);
        g.touch_node(id);
        assert_eq!(g.get_node(id).unwrap().access_count, 2);
    }

    #[test]
    fn test_writhe_computation() {
        // All positive generators → positive writhe
        let braid = BraidWord { generators: vec![1, 2, 1], strands: 3 };
        assert_eq!(compute_writhe(&braid), 3);

        // Mixed → partial cancellation
        let braid2 = BraidWord { generators: vec![1, -2, 1, -1], strands: 3 };
        assert_eq!(compute_writhe(&braid2), 0);
    }

    #[test]
    fn test_nodes_by_type() {
        let mut g = KnowledgeKnotGraph::new();
        g.add_node("f1", vec![1.0], NodeType::Fact);
        g.add_node("f2", vec![0.5], NodeType::Fact);
        g.add_node("c1", vec![0.0], NodeType::Concept);

        let facts = g.nodes_by_type(&NodeType::Fact);
        assert_eq!(facts.len(), 2);
        let concepts = g.nodes_by_type(&NodeType::Concept);
        assert_eq!(concepts.len(), 1);
    }
}
