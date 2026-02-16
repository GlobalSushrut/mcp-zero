//! Modality Fold — multimodal perception through entropy folding.
//!
//! Handles cross-modal understanding through entropic signatures.
//! Each modality (visual, auditory, sensor, etc.) maintains a signature
//! vector that evolves with incoming perception data.

use std::collections::HashMap;
use serde::{Serialize, Deserialize};
use super::types::CogVec;

/// Entropic signature for a perception modality.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ModalitySignature {
    name: String,
    signature: CogVec,
    stability: f32,
    update_count: u64,
}

impl ModalitySignature {
    /// Create a new modality signature with small noise.
    pub fn new(name: &str, dim: usize, seed: u64) -> Self {
        Self {
            name: name.to_string(),
            signature: CogVec::noise(dim, seed),
            stability: 0.1,
            update_count: 0,
        }
    }

    /// Update signature with new input vector.
    /// Returns the difference (L2 norm of delta).
    pub fn update(&mut self, input: &CogVec, weight: f32) -> f32 {
        let diff_vec = self.signature.sub(input);
        let diff = diff_vec.norm();

        // Blend: signature = (1 - weight) * signature + weight * input
        self.signature.blend(input, weight);

        // Normalize
        self.signature.normalize();

        // Update stability — lower diff means higher stability
        let stability_delta = (1.0 - diff.min(1.0)) * 0.1;
        self.stability = (self.stability + stability_delta).min(0.95);

        self.update_count += 1;
        diff
    }

    /// Get current stability (no time decay in Rust — edge devices don't need wall-clock decay).
    pub fn stability(&self) -> f32 {
        self.stability
    }

    /// Get the signature vector.
    pub fn vector(&self) -> &CogVec {
        &self.signature
    }

    /// Get the modality name.
    pub fn name(&self) -> &str {
        &self.name
    }

    /// Get update count.
    pub fn update_count(&self) -> u64 {
        self.update_count
    }
}

/// Result of a modality fold operation.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct FoldResult {
    pub folded: CogVec,
    pub weights: HashMap<String, f32>,
    pub modalities: Vec<String>,
}

/// Result of cross-modal grounding.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GroundResult {
    pub similarity: f32,
    pub cross_modal_coherence: HashMap<String, f32>,
}

/// Multimodal perception through entropic signatures.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ModalityFold {
    dim: usize,
    modalities: HashMap<String, ModalitySignature>,
    /// Cache of cross-modal coherence values.
    coherence_cache: HashMap<(String, String), f32>,
    /// Stored fold patterns for grounding.
    patterns: HashMap<String, FoldResult>,
    next_seed: u64,
}

impl ModalityFold {
    /// Create a new ModalityFold with given vector dimension.
    pub fn new(dim: usize) -> Self {
        Self {
            dim,
            modalities: HashMap::new(),
            coherence_cache: HashMap::new(),
            patterns: HashMap::new(),
            next_seed: 42,
        }
    }

    /// Register a new perception modality. Returns false if already registered.
    pub fn register_modality(&mut self, name: &str) -> bool {
        if self.modalities.contains_key(name) {
            return false;
        }
        self.next_seed = self.next_seed.wrapping_add(7);
        self.modalities.insert(
            name.to_string(),
            ModalitySignature::new(name, self.dim, self.next_seed),
        );
        self.coherence_cache.clear();
        true
    }

    /// Update a modality with new perception data.
    /// Returns (difference, stability, update_count) or None if modality not found.
    pub fn update_perception(&mut self, modality: &str, input: &CogVec) -> Option<(f32, f32, u64)> {
        // Invalidate cache entries for this modality
        self.coherence_cache.retain(|k, _| k.0 != modality && k.1 != modality);

        let sig = self.modalities.get_mut(modality)?;
        let diff = sig.update(input, 0.3);
        Some((diff, sig.stability(), sig.update_count()))
    }

    /// Fold multiple modalities into a combined perception vector.
    /// Weights are proportional to each modality's stability.
    pub fn fold(&mut self, modality_names: &[&str]) -> Option<FoldResult> {
        // Verify all exist
        for name in modality_names {
            if !self.modalities.contains_key(*name) {
                return None;
            }
        }

        // Calculate stability-based weights
        let mut weights = HashMap::new();
        let mut total: f32 = 0.0;
        for &name in modality_names {
            let s = self.modalities[name].stability();
            weights.insert(name.to_string(), s);
            total += s;
        }
        if total > 0.0 {
            for w in weights.values_mut() {
                *w /= total;
            }
        }

        // Weighted sum of signatures
        let mut folded = CogVec::zeros(self.dim);
        for &name in modality_names {
            let sig = &self.modalities[name];
            let w = weights[name];
            folded.add_scaled(sig.vector(), w);
        }
        folded.normalize();

        let result = FoldResult {
            folded,
            weights,
            modalities: modality_names.iter().map(|s| s.to_string()).collect(),
        };

        // Store pattern
        let pattern_id = format!(
            "fold_{}_{}",
            modality_names.join("_"),
            self.patterns.len()
        );
        self.patterns.insert(pattern_id, result.clone());

        Some(result)
    }

    /// Calculate cross-modal coherence between two modalities.
    pub fn cross_modal_coherence(&mut self, m1: &str, m2: &str) -> Option<f32> {
        if !self.modalities.contains_key(m1) || !self.modalities.contains_key(m2) {
            return None;
        }

        let key = if m1 < m2 {
            (m1.to_string(), m2.to_string())
        } else {
            (m2.to_string(), m1.to_string())
        };

        if let Some(&cached) = self.coherence_cache.get(&key) {
            return Some(cached);
        }

        let sig1 = &self.modalities[m1];
        let sig2 = &self.modalities[m2];
        let dot = sig1.vector().cosine_similarity(sig2.vector());
        let coherence = dot * sig1.stability() * sig2.stability();

        self.coherence_cache.insert(key, coherence);
        Some(coherence)
    }

    /// Ground a stored fold pattern against a target modality.
    pub fn ground_pattern(&mut self, pattern_id: &str, target: &str) -> Option<GroundResult> {
        let pattern = self.patterns.get(pattern_id)?.clone();
        let target_sig = self.modalities.get(target)?;

        let similarity = pattern.folded.cosine_similarity(target_sig.vector());

        let mut cross = HashMap::new();
        for m in &pattern.modalities {
            if m != target {
                if let Some(c) = self.cross_modal_coherence(m, target) {
                    cross.insert(m.clone(), c);
                }
            }
        }

        Some(GroundResult {
            similarity,
            cross_modal_coherence: cross,
        })
    }

    /// Get stability map for all modalities.
    pub fn stability_map(&self) -> HashMap<String, f32> {
        self.modalities
            .iter()
            .map(|(k, v)| (k.clone(), v.stability()))
            .collect()
    }

    /// Get the number of registered modalities.
    pub fn modality_count(&self) -> usize {
        self.modalities.len()
    }

    /// Get the number of stored patterns.
    pub fn pattern_count(&self) -> usize {
        self.patterns.len()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;
    use crate::cognitive::types::DEFAULT_DIM;

    #[test]
    fn test_register_modality() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        assert!(mf.register_modality("visual"));
        assert!(mf.register_modality("auditory"));
        assert!(!mf.register_modality("visual")); // duplicate
        assert_eq!(mf.modality_count(), 2);
    }

    #[test]
    fn test_update_perception() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("sensor");

        let input = CogVec::noise(DEFAULT_DIM, 99);
        let result = mf.update_perception("sensor", &input);
        assert!(result.is_some());

        let (diff, stability, count) = result.unwrap();
        assert!(diff > 0.0);
        assert!(stability > 0.1);
        assert_eq!(count, 1);
    }

    #[test]
    fn test_update_unknown_modality() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        let input = CogVec::noise(DEFAULT_DIM, 1);
        assert!(mf.update_perception("nonexistent", &input).is_none());
    }

    #[test]
    fn test_stability_increases_with_consistent_input() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("temp");

        let input = CogVec::noise(DEFAULT_DIM, 42);
        let mut prev_stability = 0.0;
        for _ in 0..10 {
            let (_, stability, _) = mf.update_perception("temp", &input).unwrap();
            assert!(stability >= prev_stability);
            prev_stability = stability;
        }
        assert!(prev_stability > 0.3);
    }

    #[test]
    fn test_fold_two_modalities() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("visual");
        mf.register_modality("auditory");

        let v = CogVec::noise(DEFAULT_DIM, 10);
        let a = CogVec::noise(DEFAULT_DIM, 20);
        mf.update_perception("visual", &v);
        mf.update_perception("auditory", &a);

        let result = mf.fold(&["visual", "auditory"]);
        assert!(result.is_some());

        let fold = result.unwrap();
        assert_eq!(fold.modalities.len(), 2);
        assert_eq!(fold.weights.len(), 2);
        // Folded vector should be normalized
        let norm = fold.folded.norm();
        assert!((norm - 1.0).abs() < 0.01);
    }

    #[test]
    fn test_fold_missing_modality() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("visual");
        assert!(mf.fold(&["visual", "nonexistent"]).is_none());
    }

    #[test]
    fn test_cross_modal_coherence() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("a");
        mf.register_modality("b");

        // Same input → high coherence
        let input = CogVec::noise(DEFAULT_DIM, 42);
        mf.update_perception("a", &input);
        mf.update_perception("b", &input);

        let coherence = mf.cross_modal_coherence("a", "b").unwrap();
        assert!(coherence > 0.0);
    }

    #[test]
    fn test_coherence_cache() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("x");
        mf.register_modality("y");

        let input = CogVec::noise(DEFAULT_DIM, 7);
        mf.update_perception("x", &input);
        mf.update_perception("y", &input);

        let c1 = mf.cross_modal_coherence("x", "y").unwrap();
        let c2 = mf.cross_modal_coherence("y", "x").unwrap(); // reversed order
        assert!((c1 - c2).abs() < 1e-6);
    }

    #[test]
    fn test_ground_pattern() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("visual");
        mf.register_modality("auditory");
        mf.register_modality("tactile");

        let v = CogVec::noise(DEFAULT_DIM, 1);
        let a = CogVec::noise(DEFAULT_DIM, 2);
        let t = CogVec::noise(DEFAULT_DIM, 3);
        mf.update_perception("visual", &v);
        mf.update_perception("auditory", &a);
        mf.update_perception("tactile", &t);

        mf.fold(&["visual", "auditory"]);

        // Ground against tactile
        let pattern_id = "fold_visual_auditory_0";
        let result = mf.ground_pattern(pattern_id, "tactile");
        assert!(result.is_some());

        let ground = result.unwrap();
        assert!(ground.similarity.abs() <= 1.0);
        assert!(ground.cross_modal_coherence.contains_key("visual"));
        assert!(ground.cross_modal_coherence.contains_key("auditory"));
    }

    #[test]
    fn test_stability_map() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("a");
        mf.register_modality("b");

        let map = mf.stability_map();
        assert_eq!(map.len(), 2);
        assert!(map.contains_key("a"));
        assert!(map.contains_key("b"));
    }

    #[test]
    fn test_pattern_stored_after_fold() {
        let mut mf = ModalityFold::new(DEFAULT_DIM);
        mf.register_modality("x");
        mf.register_modality("y");

        let input = CogVec::noise(DEFAULT_DIM, 5);
        mf.update_perception("x", &input);
        mf.update_perception("y", &input);

        assert_eq!(mf.pattern_count(), 0);
        mf.fold(&["x", "y"]);
        assert_eq!(mf.pattern_count(), 1);
    }
}
