//! Neural Network Entropy Graph — tracks information entropy through computation layers.
//!
//! Measures Shannon entropy of activation distributions at each layer of a neural
//! network, creating an "entropy flow graph" that maps how information compresses
//! and expands through the network.
//!
//! Key concepts:
//!   - **Layer Entropy**: H(X) = -Σ p(x) log₂ p(x) for activation distributions
//!   - **Entropy Delta**: change in entropy between consecutive layers
//!   - **Information Bottleneck**: layers where entropy drops sharply (compression)
//!   - **Entropy Burst**: layers where entropy increases sharply (expansion)
//!   - **Mutual Information Estimate**: how much information is preserved between layers
//!
//! This connects to the cognitive engine's `EntropyEngine` — neural entropy feeds
//! into entropic intent fields for symbolic reasoning.

use std::collections::HashMap;
use serde::{Serialize, Deserialize};

/// Entropy measurement for a single network layer.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LayerEntropy {
    pub layer_name: String,
    pub layer_index: usize,
    /// Shannon entropy of activation distribution (bits).
    pub entropy: f64,
    /// Number of activation values measured.
    pub activation_count: usize,
    /// Mean activation value.
    pub mean_activation: f64,
    /// Variance of activations.
    pub variance: f64,
    /// Sparsity: fraction of near-zero activations (< 1e-6).
    pub sparsity: f64,
}

/// Entropy delta between two consecutive layers.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EntropyDelta {
    pub from_layer: String,
    pub to_layer: String,
    pub delta: f64,
    /// Positive = expansion (more information), negative = compression.
    pub direction: EntropyDirection,
}

#[derive(Clone, Debug, Serialize, Deserialize, PartialEq)]
pub enum EntropyDirection {
    Compression,
    Expansion,
    Stable,
}

/// A snapshot of entropy flow through the entire network.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EntropySnapshot {
    pub layers: Vec<LayerEntropy>,
    pub deltas: Vec<EntropyDelta>,
    /// Overall network entropy (mean across layers).
    pub mean_entropy: f64,
    /// Bottleneck layer (minimum entropy).
    pub bottleneck_layer: Option<String>,
    pub bottleneck_entropy: f64,
    /// Peak entropy layer.
    pub peak_layer: Option<String>,
    pub peak_entropy: f64,
    /// Total information compression ratio (input entropy / bottleneck entropy).
    pub compression_ratio: f64,
}

/// Tracks entropy through neural network layers over time.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EntropyGraph {
    /// History of entropy snapshots (bounded).
    history: Vec<EntropySnapshot>,
    max_history: usize,
    /// Running statistics per layer name.
    layer_stats: HashMap<String, LayerRunningStats>,
}

#[derive(Clone, Debug, Serialize, Deserialize)]
struct LayerRunningStats {
    count: u64,
    entropy_sum: f64,
    entropy_sq_sum: f64,
    min_entropy: f64,
    max_entropy: f64,
}

impl LayerRunningStats {
    fn new() -> Self {
        Self {
            count: 0,
            entropy_sum: 0.0,
            entropy_sq_sum: 0.0,
            min_entropy: f64::MAX,
            max_entropy: f64::MIN,
        }
    }

    fn update(&mut self, entropy: f64) {
        self.count += 1;
        self.entropy_sum += entropy;
        self.entropy_sq_sum += entropy * entropy;
        self.min_entropy = self.min_entropy.min(entropy);
        self.max_entropy = self.max_entropy.max(entropy);
    }

    fn mean(&self) -> f64 {
        if self.count == 0 { 0.0 } else { self.entropy_sum / self.count as f64 }
    }

    fn variance(&self) -> f64 {
        if self.count < 2 { return 0.0; }
        let mean = self.mean();
        self.entropy_sq_sum / self.count as f64 - mean * mean
    }
}

impl EntropyGraph {
    pub fn new(max_history: usize) -> Self {
        Self {
            history: Vec::new(),
            max_history,
            layer_stats: HashMap::new(),
        }
    }

    /// Compute Shannon entropy of a distribution of f32 activation values.
    ///
    /// Bins activations into a histogram, normalizes to probabilities,
    /// then computes H(X) = -Σ p(x) log₂ p(x).
    pub fn shannon_entropy(activations: &[f32], num_bins: usize) -> f64 {
        if activations.is_empty() || num_bins == 0 {
            return 0.0;
        }

        let min_val = activations.iter().cloned().fold(f32::INFINITY, f32::min);
        let max_val = activations.iter().cloned().fold(f32::NEG_INFINITY, f32::max);
        let range = max_val - min_val;

        if range < 1e-10 {
            return 0.0; // All values identical → zero entropy
        }

        // Build histogram
        let mut bins = vec![0u64; num_bins];
        let bin_width = range / num_bins as f32;

        for &val in activations {
            let idx = ((val - min_val) / bin_width) as usize;
            let idx = idx.min(num_bins - 1);
            bins[idx] += 1;
        }

        // Compute entropy
        let total = activations.len() as f64;
        let mut entropy = 0.0;
        for &count in &bins {
            if count > 0 {
                let p = count as f64 / total;
                entropy -= p * p.log2();
            }
        }

        entropy
    }

    /// Compute entropy for a single layer's activations.
    pub fn compute_layer_entropy(
        layer_name: &str,
        layer_index: usize,
        activations: &[f32],
    ) -> LayerEntropy {
        let n = activations.len();
        let entropy = Self::shannon_entropy(activations, 64.min(n.max(1)));

        let mean = if n > 0 {
            activations.iter().map(|&x| x as f64).sum::<f64>() / n as f64
        } else {
            0.0
        };

        let variance = if n > 1 {
            activations.iter().map(|&x| {
                let d = x as f64 - mean;
                d * d
            }).sum::<f64>() / (n - 1) as f64
        } else {
            0.0
        };

        let sparsity = if n > 0 {
            activations.iter().filter(|&&x| x.abs() < 1e-6).count() as f64 / n as f64
        } else {
            0.0
        };

        LayerEntropy {
            layer_name: layer_name.to_string(),
            layer_index,
            entropy,
            activation_count: n,
            mean_activation: mean,
            variance,
            sparsity,
        }
    }

    /// Record a full forward pass — compute entropy for each layer and build snapshot.
    ///
    /// `layers` is a list of (layer_name, activations) pairs in forward order.
    pub fn record_pass(&mut self, layers: &[(&str, &[f32])]) -> EntropySnapshot {
        let mut layer_entropies = Vec::with_capacity(layers.len());

        for (i, &(name, activations)) in layers.iter().enumerate() {
            let le = Self::compute_layer_entropy(name, i, activations);

            // Update running stats
            self.layer_stats
                .entry(name.to_string())
                .or_insert_with(LayerRunningStats::new)
                .update(le.entropy);

            layer_entropies.push(le);
        }

        // Compute deltas
        let mut deltas = Vec::new();
        for pair in layer_entropies.windows(2) {
            let delta = pair[1].entropy - pair[0].entropy;
            let direction = if delta < -0.1 {
                EntropyDirection::Compression
            } else if delta > 0.1 {
                EntropyDirection::Expansion
            } else {
                EntropyDirection::Stable
            };
            deltas.push(EntropyDelta {
                from_layer: pair[0].layer_name.clone(),
                to_layer: pair[1].layer_name.clone(),
                delta,
                direction,
            });
        }

        // Summary stats
        let mean_entropy = if layer_entropies.is_empty() {
            0.0
        } else {
            layer_entropies.iter().map(|l| l.entropy).sum::<f64>() / layer_entropies.len() as f64
        };

        let bottleneck_layer = layer_entropies.iter()
            .min_by(|a, b| a.entropy.partial_cmp(&b.entropy).unwrap())
            .map(|l| (l.layer_name.clone(), l.entropy));
        let peak_layer = layer_entropies.iter()
            .max_by(|a, b| a.entropy.partial_cmp(&b.entropy).unwrap())
            .map(|l| (l.layer_name.clone(), l.entropy));

        let bottleneck_entropy = bottleneck_layer.as_ref().map(|(_, e)| *e).unwrap_or(0.0);
        let peak_entropy = peak_layer.as_ref().map(|(_, e)| *e).unwrap_or(0.0);

        let compression_ratio = if bottleneck_entropy > 1e-10 && !layer_entropies.is_empty() {
            layer_entropies[0].entropy / bottleneck_entropy
        } else {
            1.0
        };

        let snapshot = EntropySnapshot {
            layers: layer_entropies,
            deltas,
            mean_entropy,
            bottleneck_layer: bottleneck_layer.map(|(name, _)| name),
            bottleneck_entropy,
            peak_layer: peak_layer.map(|(name, _)| name),
            peak_entropy,
            compression_ratio,
        };

        // Store in history (bounded)
        self.history.push(snapshot.clone());
        if self.history.len() > self.max_history {
            self.history.remove(0);
        }

        snapshot
    }

    /// Get the most recent entropy snapshot.
    pub fn latest(&self) -> Option<&EntropySnapshot> {
        self.history.last()
    }

    /// Get entropy trend for a specific layer (last N measurements).
    pub fn layer_trend(&self, layer_name: &str, n: usize) -> Vec<f64> {
        self.history.iter()
            .rev()
            .take(n)
            .filter_map(|snap| {
                snap.layers.iter().find(|l| l.layer_name == layer_name).map(|l| l.entropy)
            })
            .collect::<Vec<_>>()
            .into_iter()
            .rev()
            .collect()
    }

    /// Get running statistics for a layer.
    pub fn layer_stats(&self, layer_name: &str) -> Option<(f64, f64, f64, f64)> {
        self.layer_stats.get(layer_name).map(|s| {
            (s.mean(), s.variance(), s.min_entropy, s.max_entropy)
        })
    }

    /// Detect information bottleneck layers — layers where entropy drops > threshold.
    pub fn detect_bottlenecks(&self, threshold: f64) -> Vec<String> {
        let snap = match self.latest() {
            Some(s) => s,
            None => return Vec::new(),
        };
        snap.deltas.iter()
            .filter(|d| d.delta < -threshold)
            .map(|d| d.to_layer.clone())
            .collect()
    }

    /// Detect entropy burst layers — layers where entropy increases > threshold.
    pub fn detect_bursts(&self, threshold: f64) -> Vec<String> {
        let snap = match self.latest() {
            Some(s) => s,
            None => return Vec::new(),
        };
        snap.deltas.iter()
            .filter(|d| d.delta > threshold)
            .map(|d| d.to_layer.clone())
            .collect()
    }

    /// Convert the latest snapshot to a CogVec-compatible entropy vector.
    /// Each element is the entropy of the corresponding layer (padded/truncated to dim).
    pub fn to_entropy_vector(&self, dim: usize) -> Vec<f32> {
        let mut vec = vec![0.0f32; dim];
        if let Some(snap) = self.latest() {
            for (i, layer) in snap.layers.iter().enumerate() {
                if i >= dim { break; }
                vec[i] = layer.entropy as f32;
            }
        }
        vec
    }

    /// Number of recorded snapshots.
    pub fn snapshot_count(&self) -> usize {
        self.history.len()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn uniform_activations(n: usize) -> Vec<f32> {
        (0..n).map(|i| i as f32 / n as f32).collect()
    }

    fn constant_activations(n: usize, val: f32) -> Vec<f32> {
        vec![val; n]
    }

    fn sparse_activations(n: usize) -> Vec<f32> {
        let mut v = vec![0.0f32; n];
        // Only 10% non-zero
        for i in (0..n).step_by(10) {
            v[i] = 1.0;
        }
        v
    }

    #[test]
    fn test_shannon_entropy_uniform() {
        let acts = uniform_activations(1000);
        let h = EntropyGraph::shannon_entropy(&acts, 64);
        // Uniform distribution should have high entropy (close to log2(64) = 6 bits)
        assert!(h > 4.0, "Uniform entropy should be high, got {}", h);
    }

    #[test]
    fn test_shannon_entropy_constant() {
        let acts = constant_activations(1000, 0.5);
        let h = EntropyGraph::shannon_entropy(&acts, 64);
        // Constant values → zero entropy
        assert!(h < 0.01, "Constant entropy should be ~0, got {}", h);
    }

    #[test]
    fn test_shannon_entropy_sparse() {
        let acts = sparse_activations(1000);
        let h = EntropyGraph::shannon_entropy(&acts, 64);
        // Sparse should have low entropy (most values in one bin)
        assert!(h < 2.0, "Sparse entropy should be low, got {}", h);
    }

    #[test]
    fn test_shannon_entropy_empty() {
        assert_eq!(EntropyGraph::shannon_entropy(&[], 64), 0.0);
    }

    #[test]
    fn test_compute_layer_entropy() {
        let acts = uniform_activations(500);
        let le = EntropyGraph::compute_layer_entropy("layer_0", 0, &acts);
        assert_eq!(le.layer_name, "layer_0");
        assert_eq!(le.layer_index, 0);
        assert_eq!(le.activation_count, 500);
        assert!(le.entropy > 0.0);
        assert!(le.mean_activation > 0.0);
        assert!(le.variance > 0.0);
    }

    #[test]
    fn test_sparsity_measurement() {
        let acts = sparse_activations(100);
        let le = EntropyGraph::compute_layer_entropy("sparse", 0, &acts);
        assert!(le.sparsity > 0.8, "Should be >80% sparse, got {}", le.sparsity);
    }

    #[test]
    fn test_record_pass() {
        let mut graph = EntropyGraph::new(100);

        let l0 = uniform_activations(256);
        let l1 = sparse_activations(128);
        let l2 = uniform_activations(64);

        let snap = graph.record_pass(&[
            ("embedding", &l0),
            ("attention", &l1),
            ("output", &l2),
        ]);

        assert_eq!(snap.layers.len(), 3);
        assert_eq!(snap.deltas.len(), 2);
        assert!(snap.mean_entropy > 0.0);
        assert!(snap.bottleneck_layer.is_some());
        assert!(snap.peak_layer.is_some());
    }

    #[test]
    fn test_entropy_deltas() {
        let mut graph = EntropyGraph::new(100);

        // High entropy → low entropy = compression
        let high = uniform_activations(1000);
        let low = sparse_activations(1000);

        let snap = graph.record_pass(&[
            ("input", &high),
            ("bottleneck", &low),
        ]);

        assert_eq!(snap.deltas.len(), 1);
        assert!(snap.deltas[0].delta < 0.0, "Should be compression");
        assert_eq!(snap.deltas[0].direction, EntropyDirection::Compression);
    }

    #[test]
    fn test_detect_bottlenecks() {
        let mut graph = EntropyGraph::new(100);

        let high = uniform_activations(1000);
        let low = sparse_activations(1000);

        graph.record_pass(&[
            ("input", &high),
            ("bottleneck", &low),
            ("output", &high),
        ]);

        let bottlenecks = graph.detect_bottlenecks(0.5);
        assert!(!bottlenecks.is_empty());
        assert!(bottlenecks.contains(&"bottleneck".to_string()));
    }

    #[test]
    fn test_detect_bursts() {
        let mut graph = EntropyGraph::new(100);

        let low = sparse_activations(1000);
        let high = uniform_activations(1000);

        graph.record_pass(&[
            ("compressed", &low),
            ("expanded", &high),
        ]);

        let bursts = graph.detect_bursts(0.5);
        assert!(!bursts.is_empty());
    }

    #[test]
    fn test_layer_trend() {
        let mut graph = EntropyGraph::new(100);

        for seed in 0..5 {
            let acts: Vec<f32> = (0..100).map(|i| ((i + seed) as f32).sin()).collect();
            graph.record_pass(&[("layer_0", &acts)]);
        }

        let trend = graph.layer_trend("layer_0", 3);
        assert_eq!(trend.len(), 3);
    }

    #[test]
    fn test_layer_stats() {
        let mut graph = EntropyGraph::new(100);

        for _ in 0..10 {
            let acts = uniform_activations(100);
            graph.record_pass(&[("test_layer", &acts)]);
        }

        let stats = graph.layer_stats("test_layer");
        assert!(stats.is_some());
        let (mean, var, min, max) = stats.unwrap();
        assert!(mean > 0.0);
        assert!(var >= 0.0);
        assert!(min <= max);
    }

    #[test]
    fn test_to_entropy_vector() {
        let mut graph = EntropyGraph::new(100);
        let acts = uniform_activations(100);
        graph.record_pass(&[("a", &acts), ("b", &acts), ("c", &acts)]);

        let vec = graph.to_entropy_vector(8);
        assert_eq!(vec.len(), 8);
        assert!(vec[0] > 0.0); // First 3 should have entropy
        assert!(vec[1] > 0.0);
        assert!(vec[2] > 0.0);
        assert_eq!(vec[7], 0.0); // Rest padded with zeros
    }

    #[test]
    fn test_history_bounded() {
        let mut graph = EntropyGraph::new(3);
        let acts = uniform_activations(100);

        for _ in 0..10 {
            graph.record_pass(&[("layer", &acts)]);
        }

        assert_eq!(graph.snapshot_count(), 3);
    }

    #[test]
    fn test_compression_ratio() {
        let mut graph = EntropyGraph::new(100);

        let high = uniform_activations(1000);
        let low = sparse_activations(1000);

        let snap = graph.record_pass(&[
            ("input", &high),
            ("bottleneck", &low),
        ]);

        assert!(snap.compression_ratio > 1.0, "Should compress: ratio {}", snap.compression_ratio);
    }

    #[test]
    fn test_multi_layer_network_simulation() {
        let mut graph = EntropyGraph::new(100);

        // Simulate a 6-layer network: input → embed → attn → ffn → pool → output
        // Entropy should: rise at embed, stay at attn, compress at pool
        let input: Vec<f32> = (0..768).map(|i| (i as f32 * 0.01).sin()).collect();
        let embed: Vec<f32> = (0..768).map(|i| (i as f32 * 0.03).cos()).collect();
        let attn: Vec<f32> = (0..768).map(|i| (i as f32 * 0.02).sin() * 0.5).collect();
        let ffn: Vec<f32> = (0..3072).map(|i| (i as f32 * 0.01).tanh()).collect();
        let pool: Vec<f32> = (0..768).map(|i| if i % 3 == 0 { 0.8 } else { 0.0 }).collect();
        let output: Vec<f32> = (0..384).map(|i| (i as f32 / 384.0)).collect();

        let snap = graph.record_pass(&[
            ("input", &input),
            ("embedding", &embed),
            ("attention", &attn),
            ("ffn", &ffn),
            ("pooling", &pool),
            ("output", &output),
        ]);

        assert_eq!(snap.layers.len(), 6);
        assert_eq!(snap.deltas.len(), 5);
        assert!(snap.mean_entropy > 0.0);

        // Pooling should be the bottleneck (most sparse)
        let pool_entropy = snap.layers.iter().find(|l| l.layer_name == "pooling").unwrap();
        assert!(pool_entropy.sparsity > 0.5);
    }
}
