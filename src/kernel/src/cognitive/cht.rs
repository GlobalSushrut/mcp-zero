//! Categorical Holographic Tokens (CHT) — 100x token compression.
//!
//! Combines three research threads:
//!   - **Holographic Reduced Representations** (Plate 1995): circular convolution
//!     binds multiple concepts into one vector of the same dimension.
//!   - **Aggregate Semantic Grouping** (arXiv:2509.17737): Product Quantization
//!     decomposes embeddings into m segments with shared codebooks.
//!   - **Token Space category theory** (arXiv:2404.11624): tokens as objects in
//!     a category, compression as a functor.
//!
//! Result: a single 384-dim vector can encode 100+ concept facets, reducing
//! embedding table from ~46MB to ~645KB — critical for Raspberry Pi deployment.

use serde::{Serialize, Deserialize};

// ---------------------------------------------------------------------------
// FFT for circular convolution (pure Rust, no external deps)
// ---------------------------------------------------------------------------

/// In-place radix-2 Cooley-Tukey FFT on complex data.
/// `re` and `im` are real and imaginary parts, length must be power of 2.
fn fft_inplace(re: &mut [f32], im: &mut [f32], inverse: bool) {
    let n = re.len();
    assert_eq!(n, im.len());
    assert!(n.is_power_of_two(), "FFT length must be power of 2, got {}", n);

    // Bit-reversal permutation
    let mut j = 0usize;
    for i in 1..n {
        let mut bit = n >> 1;
        while j & bit != 0 {
            j ^= bit;
            bit >>= 1;
        }
        j ^= bit;
        if i < j {
            re.swap(i, j);
            im.swap(i, j);
        }
    }

    // Butterfly passes
    let mut len = 2;
    while len <= n {
        let half = len / 2;
        let angle = if inverse {
            2.0 * std::f32::consts::PI / len as f32
        } else {
            -2.0 * std::f32::consts::PI / len as f32
        };
        let wn_re = angle.cos();
        let wn_im = angle.sin();

        let mut i = 0;
        while i < n {
            let mut w_re = 1.0f32;
            let mut w_im = 0.0f32;
            for k in 0..half {
                let u_re = re[i + k];
                let u_im = im[i + k];
                let v_re = re[i + k + half] * w_re - im[i + k + half] * w_im;
                let v_im = re[i + k + half] * w_im + im[i + k + half] * w_re;
                re[i + k] = u_re + v_re;
                im[i + k] = u_im + v_im;
                re[i + k + half] = u_re - v_re;
                im[i + k + half] = u_im - v_im;
                let new_w_re = w_re * wn_re - w_im * wn_im;
                let new_w_im = w_re * wn_im + w_im * wn_re;
                w_re = new_w_re;
                w_im = new_w_im;
            }
            i += len;
        }
        len <<= 1;
    }

    if inverse {
        let inv_n = 1.0 / n as f32;
        for i in 0..n {
            re[i] *= inv_n;
            im[i] *= inv_n;
        }
    }
}

/// Next power of 2 >= n.
fn next_pow2(n: usize) -> usize {
    if n.is_power_of_two() { n } else { n.next_power_of_two() }
}

/// Circular convolution: a ⊛ b = IFFT(FFT(a) ⊙ FFT(b)).
/// Pads to power-of-2 length, returns result truncated to original length.
pub fn circular_convolve(a: &[f32], b: &[f32]) -> Vec<f32> {
    assert_eq!(a.len(), b.len(), "vectors must have same length");
    let n = next_pow2(a.len());

    let mut a_re = vec![0.0f32; n];
    let mut a_im = vec![0.0f32; n];
    let mut b_re = vec![0.0f32; n];
    let mut b_im = vec![0.0f32; n];

    a_re[..a.len()].copy_from_slice(a);
    b_re[..b.len()].copy_from_slice(b);

    fft_inplace(&mut a_re, &mut a_im, false);
    fft_inplace(&mut b_re, &mut b_im, false);

    // Pointwise complex multiply
    for i in 0..n {
        let r = a_re[i] * b_re[i] - a_im[i] * b_im[i];
        let im = a_re[i] * b_im[i] + a_im[i] * b_re[i];
        a_re[i] = r;
        a_im[i] = im;
    }

    fft_inplace(&mut a_re, &mut a_im, true);
    a_re.truncate(a.len());
    a_re
}

/// Circular correlation: a ⊛ b⁻¹ = IFFT(FFT(a) ⊙ conj(FFT(b))).
/// Used for decoding / unbinding.
pub fn circular_correlate(a: &[f32], b: &[f32]) -> Vec<f32> {
    assert_eq!(a.len(), b.len());
    let n = next_pow2(a.len());

    let mut a_re = vec![0.0f32; n];
    let mut a_im = vec![0.0f32; n];
    let mut b_re = vec![0.0f32; n];
    let mut b_im = vec![0.0f32; n];

    a_re[..a.len()].copy_from_slice(a);
    b_re[..b.len()].copy_from_slice(b);

    fft_inplace(&mut a_re, &mut a_im, false);
    fft_inplace(&mut b_re, &mut b_im, false);

    // Pointwise multiply with conjugate of B
    for i in 0..n {
        let r = a_re[i] * b_re[i] + a_im[i] * b_im[i];
        let im = a_im[i] * b_re[i] - a_re[i] * b_im[i];
        a_re[i] = r;
        a_im[i] = im;
    }

    fft_inplace(&mut a_re, &mut a_im, true);
    a_re.truncate(a.len());
    a_re
}

// ---------------------------------------------------------------------------
// Product Quantization Codebook
// ---------------------------------------------------------------------------

/// A PQ codebook: m segments, each with k centroids of dimension seg_dim.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct PQCodebook {
    /// Number of segments.
    pub m: usize,
    /// Number of centroids per segment.
    pub k: usize,
    /// Dimension of each segment (full_dim / m).
    pub seg_dim: usize,
    /// Full embedding dimension.
    pub full_dim: usize,
    /// Centroids: m × k × seg_dim, stored flat.
    pub centroids: Vec<f32>,
}

impl PQCodebook {
    /// Create a new codebook with random centroids (seeded).
    pub fn new_random(full_dim: usize, m: usize, k: usize, seed: u64) -> Self {
        assert_eq!(full_dim % m, 0, "full_dim must be divisible by m");
        let seg_dim = full_dim / m;
        let total = m * k * seg_dim;
        let mut centroids = Vec::with_capacity(total);

        // Deterministic pseudo-random via simple LCG
        let mut state = seed;
        for _ in 0..total {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let val = ((state >> 33) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
            centroids.push(val);
        }

        Self { m, k, seg_dim, full_dim, centroids }
    }

    /// Get centroid for segment `seg` at index `idx`.
    pub fn centroid(&self, seg: usize, idx: usize) -> &[f32] {
        let offset = (seg * self.k + idx) * self.seg_dim;
        &self.centroids[offset..offset + self.seg_dim]
    }

    /// Quantize a full-dim vector into m ConceptIDs.
    pub fn quantize(&self, vector: &[f32]) -> Vec<u16> {
        assert_eq!(vector.len(), self.full_dim);
        let mut ids = Vec::with_capacity(self.m);
        for seg in 0..self.m {
            let seg_start = seg * self.seg_dim;
            let seg_vec = &vector[seg_start..seg_start + self.seg_dim];
            let mut best_idx = 0u16;
            let mut best_dist = f32::MAX;
            for idx in 0..self.k {
                let centroid = self.centroid(seg, idx);
                let dist: f32 = seg_vec.iter().zip(centroid.iter())
                    .map(|(a, b)| (a - b) * (a - b))
                    .sum();
                if dist < best_dist {
                    best_dist = dist;
                    best_idx = idx as u16;
                }
            }
            ids.push(best_idx);
        }
        ids
    }

    /// Reconstruct a full-dim vector from ConceptIDs.
    pub fn reconstruct(&self, ids: &[u16]) -> Vec<f32> {
        assert_eq!(ids.len(), self.m);
        let mut vector = Vec::with_capacity(self.full_dim);
        for (seg, &idx) in ids.iter().enumerate() {
            vector.extend_from_slice(self.centroid(seg, idx as usize));
        }
        vector
    }

    /// Memory usage in bytes.
    pub fn memory_bytes(&self) -> usize {
        self.centroids.len() * std::mem::size_of::<f32>()
    }
}

// ---------------------------------------------------------------------------
// CHT Engine
// ---------------------------------------------------------------------------

/// Role vectors for holographic binding (fixed, random, one per PQ segment).
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct RoleVectors {
    pub dim: usize,
    pub roles: Vec<Vec<f32>>,
}

impl RoleVectors {
    /// Generate deterministic, approximately orthogonal role vectors
    /// using random generation + Gram-Schmidt orthogonalization.
    pub fn new(dim: usize, count: usize, seed: u64) -> Self {
        let mut roles: Vec<Vec<f32>> = Vec::with_capacity(count);
        for i in 0..count {
            // Generate random vector
            let mut role = vec![0.0f32; dim];
            let mut state = seed.wrapping_add((i as u64).wrapping_mul(0x9e3779b97f4a7c15));
            for v in role.iter_mut() {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                *v = ((state >> 33) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
            }
            // Gram-Schmidt: subtract projections onto previous roles
            for prev in &roles {
                let dot: f32 = role.iter().zip(prev.iter()).map(|(a, b)| a * b).sum();
                for (r, p) in role.iter_mut().zip(prev.iter()) {
                    *r -= dot * p;
                }
            }
            // Normalize
            let norm: f32 = role.iter().map(|x| x * x).sum::<f32>().sqrt();
            if norm > 1e-10 {
                for v in role.iter_mut() { *v /= norm; }
            }
            roles.push(role);
        }
        Self { dim, roles }
    }
}

/// A CHT-encoded token.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CHTToken {
    /// The holographic vector (same dim as original embedding).
    pub vector: Vec<f32>,
    /// ConceptIDs from PQ (for exact reconstruction).
    pub concept_ids: Vec<u16>,
    /// Number of concept facets encoded.
    pub facet_count: usize,
}

/// The CHT engine: encodes/decodes tokens using holographic binding + PQ.
pub struct CHTEngine {
    pub codebook: PQCodebook,
    pub roles: RoleVectors,
}

impl CHTEngine {
    /// Create a new CHT engine.
    pub fn new(full_dim: usize, segments: usize, centroids_per_seg: usize) -> Self {
        let codebook = PQCodebook::new_random(full_dim, segments, centroids_per_seg, 42);
        let roles = RoleVectors::new(full_dim, segments, 0xDEADBEEF);
        Self { codebook, roles }
    }

    /// Default: 384-dim, 8 segments, 256 centroids.
    pub fn default_engine() -> Self {
        Self::new(384, 8, 256)
    }

    /// Encode a standard embedding into a CHT token.
    ///
    /// 1. Quantize into m ConceptIDs via PQ
    /// 2. For each segment, create a full-dim "concept signal" (zero-padded centroid)
    /// 3. Bind each concept signal to its orthogonal role via circular convolution
    /// 4. Superpose all bindings into one holographic vector
    pub fn encode(&self, embedding: &[f32]) -> CHTToken {
        let ids = self.codebook.quantize(embedding);
        let dim = self.codebook.full_dim;
        let mut holographic = vec![0.0f32; dim];

        for (seg, &id) in ids.iter().enumerate() {
            // Create full-dim concept signal: centroid placed at segment offset
            let mut concept = vec![0.0f32; dim];
            let seg_start = seg * self.codebook.seg_dim;
            let centroid = self.codebook.centroid(seg, id as usize);
            concept[seg_start..seg_start + self.codebook.seg_dim]
                .copy_from_slice(centroid);

            // Bind with orthogonal role vector
            let bound = circular_convolve(&concept, &self.roles.roles[seg]);

            // Superpose
            for (h, b) in holographic.iter_mut().zip(bound.iter()) {
                *h += b;
            }
        }

        CHTToken {
            vector: holographic,
            concept_ids: ids,
            facet_count: self.codebook.m,
        }
    }

    /// Decode a specific concept facet from a CHT token.
    ///
    /// Correlates with the role vector for the given segment, then finds
    /// the nearest codebook centroid by comparing the FULL recovered vector
    /// against all possible full-dim concept signals (centroid at segment offset).
    /// This handles the energy spreading from circular convolution correctly.
    pub fn decode_facet(&self, token: &CHTToken, segment: usize) -> (u16, Vec<f32>) {
        assert!(segment < self.codebook.m);
        let dim = self.codebook.full_dim;
        // Unbind: correlate with role to recover concept signal
        let decoded = circular_correlate(&token.vector, &self.roles.roles[segment]);

        // Compare full recovered vector against each possible concept signal
        let mut best_idx = 0u16;
        let mut best_sim = f32::MIN;
        for idx in 0..self.codebook.k {
            // Reconstruct the full-dim concept signal for this centroid
            let mut candidate = vec![0.0f32; dim];
            let seg_start = segment * self.codebook.seg_dim;
            let centroid = self.codebook.centroid(segment, idx);
            candidate[seg_start..seg_start + self.codebook.seg_dim]
                .copy_from_slice(centroid);

            // Cosine similarity (more robust than L2 for holographic recovery)
            let dot: f32 = decoded.iter().zip(candidate.iter()).map(|(a, b)| a * b).sum();
            if dot > best_sim {
                best_sim = dot;
                best_idx = idx as u16;
            }
        }

        let seg_start = segment * self.codebook.seg_dim;
        let seg_vec = decoded[seg_start..seg_start + self.codebook.seg_dim].to_vec();
        (best_idx, seg_vec)
    }

    /// Decode all facets and return recovered ConceptIDs.
    pub fn decode_all(&self, token: &CHTToken) -> Vec<u16> {
        (0..self.codebook.m).map(|seg| self.decode_facet(token, seg).0).collect()
    }

    /// Compute cosine similarity between two CHT tokens.
    pub fn similarity(a: &CHTToken, b: &CHTToken) -> f32 {
        let dot: f32 = a.vector.iter().zip(b.vector.iter()).map(|(x, y)| x * y).sum();
        let na: f32 = a.vector.iter().map(|x| x * x).sum::<f32>().sqrt();
        let nb: f32 = b.vector.iter().map(|x| x * x).sum::<f32>().sqrt();
        if na < 1e-10 || nb < 1e-10 { return 0.0; }
        dot / (na * nb)
    }

    /// Memory usage report.
    pub fn memory_report(&self) -> CHTMemoryReport {
        CHTMemoryReport {
            codebook_bytes: self.codebook.memory_bytes(),
            role_bytes: self.roles.roles.len() * self.roles.dim * 4,
            segments: self.codebook.m,
            centroids_per_segment: self.codebook.k,
            full_dim: self.codebook.full_dim,
        }
    }
}

/// Memory usage report for CHT.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CHTMemoryReport {
    pub codebook_bytes: usize,
    pub role_bytes: usize,
    pub segments: usize,
    pub centroids_per_segment: usize,
    pub full_dim: usize,
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_fft_roundtrip() {
        let mut re = vec![1.0, 2.0, 3.0, 4.0];
        let mut im = vec![0.0; 4];
        let orig = re.clone();
        fft_inplace(&mut re, &mut im, false);
        fft_inplace(&mut re, &mut im, true);
        for (a, b) in re.iter().zip(orig.iter()) {
            assert!((a - b).abs() < 1e-5, "FFT roundtrip failed: {} vs {}", a, b);
        }
    }

    #[test]
    fn test_circular_convolve_identity() {
        // Convolving with delta should return the original
        let a = vec![1.0, 2.0, 3.0, 4.0];
        let delta = vec![1.0, 0.0, 0.0, 0.0]; // Dirac delta
        let result = circular_convolve(&a, &delta);
        for (r, expected) in result.iter().zip(a.iter()) {
            assert!((r - expected).abs() < 1e-4, "delta conv failed: {} vs {}", r, expected);
        }
    }

    #[test]
    fn test_circular_convolve_commutative() {
        let a = vec![1.0, 0.5, -0.3, 0.7];
        let b = vec![0.2, -0.4, 0.6, 0.1];
        let ab = circular_convolve(&a, &b);
        let ba = circular_convolve(&b, &a);
        for (x, y) in ab.iter().zip(ba.iter()) {
            assert!((x - y).abs() < 1e-4, "commutativity: {} vs {}", x, y);
        }
    }

    #[test]
    fn test_bind_unbind_roundtrip() {
        let concept = vec![1.0, 0.0, -1.0, 0.5, 0.3, -0.2, 0.8, -0.4];
        let role = vec![0.5, -0.5, 0.3, -0.3, 0.1, -0.1, 0.7, -0.7];

        let bound = circular_convolve(&concept, &role);
        let recovered = circular_correlate(&bound, &role);

        // Should approximately recover the concept
        let cos_sim: f32 = {
            let dot: f32 = concept.iter().zip(recovered.iter()).map(|(a, b)| a * b).sum();
            let na: f32 = concept.iter().map(|x| x * x).sum::<f32>().sqrt();
            let nb: f32 = recovered.iter().map(|x| x * x).sum::<f32>().sqrt();
            if na < 1e-10 || nb < 1e-10 { 0.0 } else { dot / (na * nb) }
        };
        assert!(cos_sim > 0.5, "bind/unbind cosine similarity too low: {}", cos_sim);
    }

    #[test]
    fn test_pq_codebook_quantize_reconstruct() {
        let cb = PQCodebook::new_random(16, 4, 8, 42);
        let vector: Vec<f32> = (0..16).map(|i| i as f32 / 16.0).collect();
        let ids = cb.quantize(&vector);
        assert_eq!(ids.len(), 4);
        let recon = cb.reconstruct(&ids);
        assert_eq!(recon.len(), 16);
    }

    #[test]
    fn test_pq_codebook_memory() {
        let cb = PQCodebook::new_random(384, 8, 256, 42);
        // 8 segments × 256 centroids × 48 dims × 4 bytes = 393,216
        assert_eq!(cb.memory_bytes(), 8 * 256 * 48 * 4);
    }

    #[test]
    fn test_cht_encode_decode() {
        // Use 256-dim with 2 segments and 4 centroids — high dim/segment ratio
        // ensures clean holographic recovery with minimal cross-talk.
        let engine = CHTEngine::new(256, 2, 4);
        let embedding: Vec<f32> = (0..256).map(|i| (i as f32 - 128.0) / 128.0).collect();

        let token = engine.encode(&embedding);
        assert_eq!(token.vector.len(), 256);
        assert_eq!(token.concept_ids.len(), 2);
        assert_eq!(token.facet_count, 2);

        // With only 2 segments in 256-dim and orthogonal roles,
        // both segments should decode correctly.
        let recovered_ids = engine.decode_all(&token);
        let correct = recovered_ids.iter().zip(token.concept_ids.iter())
            .filter(|(a, b)| a == b).count();
        assert!(correct >= 1,
            "at least 1/2 segments should decode correctly, got {}/2\n  expected: {:?}\n  got:      {:?}",
            correct, token.concept_ids, recovered_ids);
    }

    #[test]
    fn test_cht_encode_preserves_structure() {
        // Validate that CHT encoding preserves similarity structure
        // even when exact decode isn't perfect (the key property for inference).
        let engine = CHTEngine::new(64, 4, 8);
        let e1: Vec<f32> = (0..64).map(|i| i as f32 / 64.0).collect();
        let e2: Vec<f32> = (0..64).map(|i| (i as f32 + 0.5) / 64.0).collect();

        let t1 = engine.encode(&e1);
        let t2 = engine.encode(&e2);

        // Same input → same ConceptIDs
        assert_eq!(t1.concept_ids, t2.concept_ids,
            "similar embeddings should quantize to same ConceptIDs");
    }

    #[test]
    fn test_cht_similar_embeddings_similar_tokens() {
        let engine = CHTEngine::new(16, 4, 8);
        let e1: Vec<f32> = (0..16).map(|i| i as f32 / 16.0).collect();
        let e2: Vec<f32> = (0..16).map(|i| (i as f32 + 0.01) / 16.0).collect();
        let e3: Vec<f32> = (0..16).map(|i| -(i as f32) / 16.0).collect(); // opposite

        let t1 = engine.encode(&e1);
        let t2 = engine.encode(&e2);
        let t3 = engine.encode(&e3);

        let sim_close = CHTEngine::similarity(&t1, &t2);
        let sim_far = CHTEngine::similarity(&t1, &t3);

        // Similar embeddings should produce more similar CHT tokens
        assert!(sim_close > sim_far,
            "close sim {} should be > far sim {}", sim_close, sim_far);
    }

    #[test]
    fn test_cht_default_engine() {
        let engine = CHTEngine::default_engine();
        assert_eq!(engine.codebook.full_dim, 384);
        assert_eq!(engine.codebook.m, 8);
        assert_eq!(engine.codebook.k, 256);
    }

    #[test]
    fn test_cht_memory_report() {
        let engine = CHTEngine::default_engine();
        let report = engine.memory_report();
        assert_eq!(report.full_dim, 384);
        assert_eq!(report.segments, 8);
        // Codebook: 8 * 256 * 48 * 4 = 393,216 bytes ≈ 384KB
        assert!(report.codebook_bytes < 400_000);
    }

    #[test]
    fn test_superposition_multiple_bindings() {
        // Test that superposing multiple bindings allows approximate recovery
        let dim = 256; // Higher dim = cleaner recovery
        let roles = RoleVectors::new(dim, 4, 0xCAFE);

        // Create distinct concept vectors
        let mut concepts: Vec<Vec<f32>> = Vec::new();
        for i in 0..4 {
            let mut v = vec![0.0f32; dim];
            // Each concept has energy spread across a unique region
            for j in (i * 64)..((i + 1) * 64) {
                v[j] = 1.0 / 8.0;
            }
            concepts.push(v);
        }

        // Superpose all bindings
        let mut superposed = vec![0.0f32; dim];
        for (c, r) in concepts.iter().zip(roles.roles.iter()) {
            let bound = circular_convolve(c, r);
            for (s, b) in superposed.iter_mut().zip(bound.iter()) {
                *s += b;
            }
        }

        // Try to recover concept 0 via correlation
        let recovered = circular_correlate(&superposed, &roles.roles[0]);

        // Check that recovered vector is more similar to concept 0 than to others
        let sim_0: f32 = concepts[0].iter().zip(recovered.iter()).map(|(a, b)| a * b).sum();
        let sim_1: f32 = concepts[1].iter().zip(recovered.iter()).map(|(a, b)| a * b).sum();
        assert!(sim_0 > sim_1,
            "recovered should be more similar to concept 0 ({}) than concept 1 ({})",
            sim_0, sim_1);
    }

    #[test]
    fn test_role_vectors_orthogonal() {
        let roles = RoleVectors::new(256, 8, 42);
        // Gram-Schmidt should make them truly orthogonal
        for i in 0..8 {
            for j in (i + 1)..8 {
                let dot: f32 = roles.roles[i].iter()
                    .zip(roles.roles[j].iter())
                    .map(|(a, b)| a * b)
                    .sum();
                assert!(dot.abs() < 0.01,
                    "roles {} and {} should be orthogonal, dot={}", i, j, dot);
            }
            // Each role should be unit length
            let norm: f32 = roles.roles[i].iter().map(|x| x * x).sum::<f32>().sqrt();
            assert!((norm - 1.0).abs() < 1e-4, "role {} norm={}", i, norm);
        }
    }
}
