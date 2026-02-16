//! Topos Distribution Layer — sheaf-theoretic distributed intelligence.
//!
//! Implements distributed inference across Raspberry Pi-class devices using:
//!   - **Sheaf theory**: each device holds a local section (model state + knowledge).
//!   - **Gossip protocol**: devices exchange LoRA/adapter deltas periodically.
//!   - **Gluing condition**: merged sections must agree on overlaps (H¹ = 0).
//!   - **Cohomology check**: H¹ ≠ 0 detects device divergence → contradiction.
//!
//! Works offline — syncs when network is available.

use serde::{Serialize, Deserialize};
use std::collections::HashMap;

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

/// Unique identifier for a device in the topos network.
pub type DeviceId = String;

/// A local section: the state held by one device.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct LocalSection {
    /// Device that owns this section.
    pub device_id: DeviceId,
    /// Adapter parameter snapshot (flattened f32 vector).
    pub adapter_params: Vec<f32>,
    /// Knowledge fact count at time of snapshot.
    pub fact_count: u64,
    /// Entropy state hash (for quick divergence detection).
    pub entropy_hash: u64,
    /// Logical timestamp (Lamport clock).
    pub timestamp: u64,
    /// Number of training steps since last sync.
    pub steps_since_sync: u64,
}

/// A delta: the difference between two sections (for gossip).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct SectionDelta {
    pub device_id: DeviceId,
    pub param_delta: Vec<f32>,
    pub new_facts: Vec<String>,
    pub timestamp: u64,
    pub steps: u64,
}

/// Result of a sheaf consistency check.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CohomologyResult {
    /// H⁰: dimension of global sections (parameters all agree on).
    pub h0_dim: usize,
    /// H¹: dimension of obstructions (disagreements).
    pub h1_dim: usize,
    /// Whether gluing is possible (H¹ = 0).
    pub gluable: bool,
    /// Per-pair similarity scores.
    pub pair_similarities: Vec<(DeviceId, DeviceId, f32)>,
    /// Detected contradictions (pairs with low similarity).
    pub contradictions: Vec<(DeviceId, DeviceId)>,
}

/// Result of merging sections.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct GluingResult {
    pub merged_params: Vec<f32>,
    pub contributing_devices: Vec<DeviceId>,
    pub weights: Vec<f32>,
    pub residual_h1: f32,
}

// ---------------------------------------------------------------------------
// Topos Network
// ---------------------------------------------------------------------------

/// The topos network: manages local sections and distributed consistency.
pub struct ToposNetwork {
    /// This device's ID.
    pub local_id: DeviceId,
    /// Known sections from all devices (including self).
    sections: HashMap<DeviceId, LocalSection>,
    /// Pending deltas received but not yet applied.
    pending_deltas: Vec<SectionDelta>,
    /// Gluing threshold: minimum cosine similarity for sections to be compatible.
    gluing_threshold: f32,
    /// Lamport clock.
    clock: u64,
}

impl ToposNetwork {
    /// Create a new topos network for this device.
    pub fn new(local_id: &str, gluing_threshold: f32) -> Self {
        Self {
            local_id: local_id.to_string(),
            sections: HashMap::new(),
            pending_deltas: Vec::new(),
            gluing_threshold,
            clock: 0,
        }
    }

    /// Default with threshold 0.5.
    pub fn default_network(local_id: &str) -> Self {
        Self::new(local_id, 0.5)
    }

    /// Record the local device's current state as a section.
    pub fn update_local_section(&mut self, adapter_params: Vec<f32>, fact_count: u64, entropy_hash: u64) {
        self.clock += 1;
        let section = LocalSection {
            device_id: self.local_id.clone(),
            adapter_params,
            fact_count,
            entropy_hash,
            timestamp: self.clock,
            steps_since_sync: 0,
        };
        self.sections.insert(self.local_id.clone(), section);
    }

    /// Compute a delta from the local section to send to peers.
    pub fn compute_delta(&self, new_facts: Vec<String>) -> Option<SectionDelta> {
        let section = self.sections.get(&self.local_id)?;
        Some(SectionDelta {
            device_id: self.local_id.clone(),
            param_delta: section.adapter_params.clone(),
            new_facts,
            timestamp: section.timestamp,
            steps: section.steps_since_sync,
        })
    }

    /// Receive a delta from a peer device.
    pub fn receive_delta(&mut self, delta: SectionDelta) {
        // Update Lamport clock
        self.clock = self.clock.max(delta.timestamp) + 1;

        // Store as a section snapshot
        let section = LocalSection {
            device_id: delta.device_id.clone(),
            adapter_params: delta.param_delta.clone(),
            fact_count: 0,
            entropy_hash: 0,
            timestamp: delta.timestamp,
            steps_since_sync: delta.steps,
        };
        self.sections.insert(delta.device_id.clone(), section);
        self.pending_deltas.push(delta);
    }

    /// Number of known devices.
    pub fn device_count(&self) -> usize {
        self.sections.len()
    }

    /// Get all known device IDs.
    pub fn device_ids(&self) -> Vec<DeviceId> {
        self.sections.keys().cloned().collect()
    }

    // -----------------------------------------------------------------------
    // Sheaf Cohomology
    // -----------------------------------------------------------------------

    /// Compute sheaf cohomology: check consistency across all known sections.
    ///
    /// H⁰ = global sections (parameters all devices agree on)
    /// H¹ = obstructions to gluing (disagreements)
    pub fn check_cohomology(&self) -> CohomologyResult {
        let device_ids: Vec<&DeviceId> = self.sections.keys().collect();
        let n = device_ids.len();

        if n < 2 {
            return CohomologyResult {
                h0_dim: self.sections.values().next().map(|s| s.adapter_params.len()).unwrap_or(0),
                h1_dim: 0,
                gluable: true,
                pair_similarities: vec![],
                contradictions: vec![],
            };
        }

        let mut pair_sims = Vec::new();
        let mut contradictions = Vec::new();
        let mut total_agreement = 0usize;
        let mut total_pairs = 0usize;

        for i in 0..n {
            for j in (i + 1)..n {
                let a = &self.sections[device_ids[i]];
                let b = &self.sections[device_ids[j]];
                let sim = cosine_similarity(&a.adapter_params, &b.adapter_params);

                pair_sims.push((device_ids[i].clone(), device_ids[j].clone(), sim));

                if sim >= self.gluing_threshold {
                    total_agreement += 1;
                } else {
                    contradictions.push((device_ids[i].clone(), device_ids[j].clone()));
                }
                total_pairs += 1;
            }
        }

        // H⁰ ≈ parameter dimensions where all agree
        // H¹ ≈ number of contradicting pairs (obstruction dimension)
        let param_dim = self.sections.values().next().map(|s| s.adapter_params.len()).unwrap_or(0);
        let agreement_ratio = if total_pairs > 0 { total_agreement as f32 / total_pairs as f32 } else { 1.0 };
        let h0 = (param_dim as f32 * agreement_ratio) as usize;
        let h1 = contradictions.len();

        CohomologyResult {
            h0_dim: h0,
            h1_dim: h1,
            gluable: h1 == 0,
            pair_similarities: pair_sims,
            contradictions,
        }
    }

    /// Attempt to glue all compatible sections into a global section.
    ///
    /// Uses weighted average where weights are proportional to training steps.
    pub fn glue(&self) -> Option<GluingResult> {
        let cohomology = self.check_cohomology();

        if self.sections.is_empty() { return None; }

        let param_dim = self.sections.values().next()?.adapter_params.len();
        if param_dim == 0 { return None; }

        // Compute weights proportional to steps_since_sync (more training = more weight)
        let total_steps: f32 = self.sections.values()
            .map(|s| (s.steps_since_sync as f32).max(1.0))
            .sum();

        let mut merged = vec![0.0f32; param_dim];
        let mut weights = Vec::new();
        let mut devices = Vec::new();

        for (id, section) in &self.sections {
            if section.adapter_params.len() != param_dim { continue; }
            let w = (section.steps_since_sync as f32).max(1.0) / total_steps;
            weights.push(w);
            devices.push(id.clone());
            for (m, &p) in merged.iter_mut().zip(section.adapter_params.iter()) {
                *m += w * p;
            }
        }

        // Compute residual H¹ as average disagreement
        let residual = if cohomology.pair_similarities.is_empty() {
            0.0
        } else {
            let avg_sim: f32 = cohomology.pair_similarities.iter().map(|(_, _, s)| s).sum::<f32>()
                / cohomology.pair_similarities.len() as f32;
            1.0 - avg_sim
        };

        Some(GluingResult {
            merged_params: merged,
            contributing_devices: devices,
            weights,
            residual_h1: residual,
        })
    }

    /// Drain pending deltas.
    pub fn drain_pending(&mut self) -> Vec<SectionDelta> {
        std::mem::take(&mut self.pending_deltas)
    }
}

// ---------------------------------------------------------------------------
// Helpers
// ---------------------------------------------------------------------------

fn cosine_similarity(a: &[f32], b: &[f32]) -> f32 {
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

    #[test]
    fn test_new_network() {
        let net = ToposNetwork::default_network("device_a");
        assert_eq!(net.local_id, "device_a");
        assert_eq!(net.device_count(), 0);
    }

    #[test]
    fn test_update_local_section() {
        let mut net = ToposNetwork::default_network("a");
        net.update_local_section(vec![1.0, 2.0, 3.0], 10, 42);
        assert_eq!(net.device_count(), 1);
        assert!(net.device_ids().contains(&"a".to_string()));
    }

    #[test]
    fn test_compute_delta() {
        let mut net = ToposNetwork::default_network("a");
        net.update_local_section(vec![1.0, 2.0], 5, 0);
        let delta = net.compute_delta(vec!["fact1".to_string()]).unwrap();
        assert_eq!(delta.device_id, "a");
        assert_eq!(delta.new_facts.len(), 1);
    }

    #[test]
    fn test_receive_delta() {
        let mut net = ToposNetwork::default_network("a");
        net.update_local_section(vec![1.0, 2.0], 5, 0);

        let delta = SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![1.1, 2.1],
            new_facts: vec![],
            timestamp: 5,
            steps: 10,
        };
        net.receive_delta(delta);
        assert_eq!(net.device_count(), 2);
        assert!(net.device_ids().contains(&"b".to_string()));
    }

    #[test]
    fn test_cohomology_single_device() {
        let mut net = ToposNetwork::default_network("a");
        net.update_local_section(vec![1.0, 0.0, 0.0], 5, 0);
        let coh = net.check_cohomology();
        assert!(coh.gluable);
        assert_eq!(coh.h1_dim, 0);
        assert_eq!(coh.h0_dim, 3);
    }

    #[test]
    fn test_cohomology_agreeing_devices() {
        let mut net = ToposNetwork::new("a", 0.5);
        net.update_local_section(vec![1.0, 0.0, 0.0], 5, 0);
        net.receive_delta(SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![0.9, 0.1, 0.0], // similar to a
            new_facts: vec![],
            timestamp: 1,
            steps: 5,
        });

        let coh = net.check_cohomology();
        assert!(coh.gluable, "similar devices should be gluable");
        assert_eq!(coh.h1_dim, 0);
        assert_eq!(coh.contradictions.len(), 0);
    }

    #[test]
    fn test_cohomology_contradicting_devices() {
        let mut net = ToposNetwork::new("a", 0.8);
        net.update_local_section(vec![1.0, 0.0, 0.0], 5, 0);
        net.receive_delta(SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![-1.0, 0.0, 0.0], // opposite direction
            new_facts: vec![],
            timestamp: 1,
            steps: 5,
        });

        let coh = net.check_cohomology();
        assert!(!coh.gluable, "opposite devices should not be gluable");
        assert!(coh.h1_dim > 0);
        assert_eq!(coh.contradictions.len(), 1);
    }

    #[test]
    fn test_glue_weighted() {
        let mut net = ToposNetwork::default_network("a");
        // Device a: 10 steps of training
        let section_a = LocalSection {
            device_id: "a".to_string(),
            adapter_params: vec![2.0, 0.0],
            fact_count: 10,
            entropy_hash: 0,
            timestamp: 1,
            steps_since_sync: 10,
        };
        net.sections.insert("a".to_string(), section_a);

        // Device b: 10 steps of training
        let section_b = LocalSection {
            device_id: "b".to_string(),
            adapter_params: vec![0.0, 2.0],
            fact_count: 5,
            entropy_hash: 0,
            timestamp: 2,
            steps_since_sync: 10,
        };
        net.sections.insert("b".to_string(), section_b);

        let result = net.glue().unwrap();
        assert_eq!(result.contributing_devices.len(), 2);
        // Equal weights (both 10 steps) → average
        assert!((result.merged_params[0] - 1.0).abs() < 1e-5);
        assert!((result.merged_params[1] - 1.0).abs() < 1e-5);
    }

    #[test]
    fn test_glue_unequal_weights() {
        let mut net = ToposNetwork::default_network("a");
        let section_a = LocalSection {
            device_id: "a".to_string(),
            adapter_params: vec![10.0],
            fact_count: 0,
            entropy_hash: 0,
            timestamp: 1,
            steps_since_sync: 90, // 90% weight
        };
        net.sections.insert("a".to_string(), section_a);

        let section_b = LocalSection {
            device_id: "b".to_string(),
            adapter_params: vec![0.0],
            fact_count: 0,
            entropy_hash: 0,
            timestamp: 2,
            steps_since_sync: 10, // 10% weight
        };
        net.sections.insert("b".to_string(), section_b);

        let result = net.glue().unwrap();
        // 90/100 * 10.0 + 10/100 * 0.0 = 9.0
        assert!((result.merged_params[0] - 9.0).abs() < 1e-4,
            "weighted merge: expected 9.0, got {}", result.merged_params[0]);
    }

    #[test]
    fn test_lamport_clock() {
        let mut net = ToposNetwork::default_network("a");
        net.update_local_section(vec![1.0], 0, 0);
        assert_eq!(net.clock, 1);

        net.receive_delta(SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![1.0],
            new_facts: vec![],
            timestamp: 100, // far ahead
            steps: 0,
        });
        // Clock should jump ahead
        assert!(net.clock > 100, "clock should be > 100, got {}", net.clock);
    }

    #[test]
    fn test_drain_pending() {
        let mut net = ToposNetwork::default_network("a");
        net.receive_delta(SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![1.0],
            new_facts: vec!["fact".to_string()],
            timestamp: 1,
            steps: 0,
        });
        let pending = net.drain_pending();
        assert_eq!(pending.len(), 1);
        assert_eq!(net.drain_pending().len(), 0); // drained
    }

    #[test]
    fn test_three_device_cohomology() {
        let mut net = ToposNetwork::new("a", 0.5);
        net.update_local_section(vec![1.0, 0.0, 0.0], 0, 0);
        net.receive_delta(SectionDelta {
            device_id: "b".to_string(),
            param_delta: vec![0.8, 0.2, 0.0],
            new_facts: vec![],
            timestamp: 1,
            steps: 5,
        });
        net.receive_delta(SectionDelta {
            device_id: "c".to_string(),
            param_delta: vec![0.9, 0.1, 0.0],
            new_facts: vec![],
            timestamp: 2,
            steps: 3,
        });

        let coh = net.check_cohomology();
        assert_eq!(coh.pair_similarities.len(), 3); // 3 pairs: ab, ac, bc
        assert!(coh.gluable, "all similar devices should be gluable");
    }

    #[test]
    fn test_cosine_similarity_fn() {
        let a = vec![1.0, 0.0, 0.0];
        let b = vec![1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &b) - 1.0).abs() < 1e-5);

        let c = vec![-1.0, 0.0, 0.0];
        assert!((cosine_similarity(&a, &c) + 1.0).abs() < 1e-5);

        let d = vec![0.0, 1.0, 0.0];
        assert!(cosine_similarity(&a, &d).abs() < 1e-5);
    }
}
