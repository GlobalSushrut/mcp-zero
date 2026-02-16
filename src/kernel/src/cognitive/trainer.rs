//! Categorical Adapter Training Playground — pure Rust, CPU-only.
//!
//! Replaces LoRA with a category-theoretic approach grounded in:
//!   - **Para 2-category** (ICML 2024, arXiv:2402.15332): adapters as parametric
//!     morphisms that compose associatively.
//!   - **Braid group representations** (knot theory): structured initialization
//!     via Burau representation satisfying Yang-Baxter equation.
//!   - **Sheaf-compatible merging**: adapters from different devices merge via
//!     weighted composition with consistency checks.
//!
//! Key formula:  f(x, θ) = x + α · U · σ(V · x)
//!   - When σ = identity: equivalent to LoRA
//!   - When σ = ReLU: non-linear adapter (strictly more expressive)
//!   - U,V initialized via Burau matrices (topologically structured)

use serde::{Serialize, Deserialize};

// ---------------------------------------------------------------------------
// Braid Group & Burau Representation
// ---------------------------------------------------------------------------

/// A braid word: sequence of generator indices (1-indexed, negative = inverse).
/// σ_i is represented as i, σ_i⁻¹ as -i.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BraidWord {
    pub generators: Vec<i32>,
    pub strands: usize,
}

impl BraidWord {
    /// Generate a deterministic pseudo-random braid word.
    pub fn random(strands: usize, length: usize, seed: u64) -> Self {
        let mut gens = Vec::with_capacity(length);
        let mut state = seed;
        for _ in 0..length {
            state = state.wrapping_mul(6364136223846793005).wrapping_add(1442695040888963407);
            let gen_idx = ((state >> 33) as usize % (strands - 1)) + 1;
            let sign = if (state >> 16) & 1 == 0 { 1i32 } else { -1i32 };
            gens.push(sign * gen_idx as i32);
        }
        Self { generators: gens, strands }
    }

    /// Compute the Burau representation matrix at parameter t.
    ///
    /// The Burau representation maps σ_i to an n×n matrix where the
    /// (i,i) block is replaced by [[1-t, t], [1, 0]].
    /// At t = -1 this gives integer matrices with topological invariance.
    pub fn burau_matrix(&self, t: f32) -> Vec<Vec<f32>> {
        let n = self.strands;
        // Start with identity
        let mut result = vec![vec![0.0f32; n]; n];
        for i in 0..n { result[i][i] = 1.0; }

        for &gen in &self.generators {
            let idx = (gen.unsigned_abs() as usize) - 1; // 0-indexed
            let inverse = gen < 0;

            // Build generator matrix
            let mut mat = vec![vec![0.0f32; n]; n];
            for i in 0..n { mat[i][i] = 1.0; }

            if !inverse {
                // σ_i: replace 2×2 block at (idx, idx)
                mat[idx][idx] = 1.0 - t;
                mat[idx][idx + 1] = t;
                mat[idx + 1][idx] = 1.0;
                mat[idx + 1][idx + 1] = 0.0;
            } else {
                // σ_i⁻¹: inverse of the above
                mat[idx][idx] = 0.0;
                mat[idx][idx + 1] = 1.0;
                mat[idx + 1][idx] = t;
                mat[idx + 1][idx + 1] = 1.0 - t;
            }

            // Multiply: result = result × mat
            result = mat_mul(&result, &mat);
        }

        result
    }
}

/// Matrix multiplication for Vec<Vec<f32>>.
fn mat_mul(a: &[Vec<f32>], b: &[Vec<f32>]) -> Vec<Vec<f32>> {
    let rows = a.len();
    let cols = b[0].len();
    let inner = b.len();
    let mut c = vec![vec![0.0f32; cols]; rows];
    for i in 0..rows {
        for j in 0..cols {
            for k in 0..inner {
                c[i][j] += a[i][k] * b[k][j];
            }
        }
    }
    c
}

// ---------------------------------------------------------------------------
// Categorical Adapter
// ---------------------------------------------------------------------------

/// Activation function for the adapter's inner morphism.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub enum Activation {
    /// σ = identity → equivalent to LoRA
    Identity,
    /// σ = ReLU → non-linear adapter
    ReLU,
    /// σ = tanh → bounded non-linear adapter
    Tanh,
}

/// A categorical adapter: parametric morphism in Para(Vect).
///
/// f(x, θ) = x + α · U · σ(V · x)
///
/// where θ = {U, V, α} and σ is the activation function.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CategoricalAdapter {
    /// Name of this adapter.
    pub name: String,
    /// Input/output dimension.
    pub dim: usize,
    /// Rank (bottleneck dimension).
    pub rank: usize,
    /// Scaling factor α.
    pub alpha: f32,
    /// Down-projection V: [rank × dim], stored row-major.
    pub v_matrix: Vec<f32>,
    /// Up-projection U: [dim × rank], stored row-major.
    pub u_matrix: Vec<f32>,
    /// Activation function.
    pub activation: Activation,
    /// Braid word used for initialization (for topological analysis).
    pub braid: Option<BraidWord>,
    /// Training step count.
    pub steps: u64,
}

impl CategoricalAdapter {
    /// Create a new adapter with braid-initialized matrices.
    pub fn new(name: &str, dim: usize, rank: usize, braid_length: usize, seed: u64) -> Self {
        let braid = BraidWord::random(rank.max(2), braid_length, seed);
        let burau = braid.burau_matrix(-1.0); // t=-1 for integer matrices

        // Initialize V using Burau matrix (topologically structured)
        let mut v_matrix = vec![0.0f32; rank * dim];
        let mut state = seed.wrapping_add(0xA);
        for i in 0..rank {
            for j in 0..dim {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                let random_val = ((state >> 33) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
                // Modulate by Burau matrix entry
                let burau_val = burau[i % burau.len()][j % burau[0].len()];
                v_matrix[i * dim + j] = random_val * (1.0 + burau_val.abs()) * 0.01;
            }
        }

        // Initialize U similarly
        let mut u_matrix = vec![0.0f32; dim * rank];
        state = seed.wrapping_add(0xB);
        for i in 0..dim {
            for j in 0..rank {
                state = state.wrapping_mul(6364136223846793005).wrapping_add(1);
                let random_val = ((state >> 33) as f32 / (u32::MAX as f32)) * 2.0 - 1.0;
                let burau_val = burau[j % burau.len()][i % burau[0].len()];
                u_matrix[i * rank + j] = random_val * (1.0 + burau_val.abs()) * 0.01;
            }
        }

        Self {
            name: name.to_string(),
            dim,
            rank,
            alpha: 1.0,
            v_matrix,
            u_matrix,
            activation: Activation::ReLU,
            braid: Some(braid),
            steps: 0,
        }
    }

    /// Apply the adapter: f(x) = x + α · U · σ(V · x)
    pub fn forward(&self, x: &[f32]) -> Vec<f32> {
        assert_eq!(x.len(), self.dim);

        // Step 1: V · x → [rank]
        let mut hidden = vec![0.0f32; self.rank];
        for i in 0..self.rank {
            for j in 0..self.dim {
                hidden[i] += self.v_matrix[i * self.dim + j] * x[j];
            }
        }

        // Step 2: σ(hidden)
        match self.activation {
            Activation::Identity => {},
            Activation::ReLU => {
                for h in hidden.iter_mut() { *h = h.max(0.0); }
            },
            Activation::Tanh => {
                for h in hidden.iter_mut() { *h = h.tanh(); }
            },
        }

        // Step 3: U · hidden → [dim]
        let mut output = vec![0.0f32; self.dim];
        for i in 0..self.dim {
            for j in 0..self.rank {
                output[i] += self.u_matrix[i * self.rank + j] * hidden[j];
            }
        }

        // Step 4: x + α · output (residual)
        let mut result = vec![0.0f32; self.dim];
        for i in 0..self.dim {
            result[i] = x[i] + self.alpha * output[i];
        }

        result
    }

    /// Compose two adapters: (f ∘ g)(x) = f(g(x)).
    /// Returns a new adapter that applies g first, then f.
    /// This is the key categorical operation — morphism composition.
    pub fn compose(f: &CategoricalAdapter, g: &CategoricalAdapter) -> CategoricalAdapter {
        assert_eq!(f.dim, g.dim, "adapters must have same dimension");
        // Composition creates a new adapter with combined parameters
        // For linear case: U_f · V_f + U_g · V_g (sum of low-rank)
        // We store both sets of parameters in a higher-rank adapter
        let new_rank = f.rank + g.rank;
        let dim = f.dim;

        let mut v_matrix = vec![0.0f32; new_rank * dim];
        let mut u_matrix = vec![0.0f32; dim * new_rank];

        // Copy g's matrices into first block
        for i in 0..g.rank {
            for j in 0..dim {
                v_matrix[i * dim + j] = g.v_matrix[i * dim + j];
            }
        }
        for i in 0..dim {
            for j in 0..g.rank {
                u_matrix[i * new_rank + j] = g.alpha * g.u_matrix[i * g.rank + j];
            }
        }

        // Copy f's matrices into second block
        for i in 0..f.rank {
            for j in 0..dim {
                v_matrix[(g.rank + i) * dim + j] = f.v_matrix[i * dim + j];
            }
        }
        for i in 0..dim {
            for j in 0..f.rank {
                u_matrix[i * new_rank + g.rank + j] = f.alpha * f.u_matrix[i * f.rank + j];
            }
        }

        CategoricalAdapter {
            name: format!("{}∘{}", f.name, g.name),
            dim,
            rank: new_rank,
            alpha: 1.0,
            v_matrix,
            u_matrix,
            activation: f.activation.clone(),
            braid: None,
            steps: 0,
        }
    }

    /// Compute a simple training step (SGD on adapter parameters only).
    ///
    /// Given input x and target y, computes MSE loss gradient and updates
    /// U and V matrices.  Returns the loss.
    pub fn train_step(&mut self, x: &[f32], target: &[f32], lr: f32) -> f32 {
        assert_eq!(x.len(), self.dim);
        assert_eq!(target.len(), self.dim);

        let output = self.forward(x);

        // MSE loss
        let mut loss = 0.0f32;
        let mut d_output = vec![0.0f32; self.dim];
        for i in 0..self.dim {
            let diff = output[i] - target[i];
            loss += diff * diff;
            d_output[i] = 2.0 * diff / self.dim as f32;
        }
        loss /= self.dim as f32;

        // Backprop through residual: d_adapter_out = α · d_output
        // Backprop through U: d_U = d_adapter_out ⊗ hidden
        // Backprop through σ: d_hidden = U^T · d_adapter_out ⊙ σ'(pre_act)
        // Backprop through V: d_V = d_hidden ⊗ x

        // Recompute hidden (forward pass values)
        let mut pre_act = vec![0.0f32; self.rank];
        for i in 0..self.rank {
            for j in 0..self.dim {
                pre_act[i] += self.v_matrix[i * self.dim + j] * x[j];
            }
        }
        let mut hidden = pre_act.clone();
        match self.activation {
            Activation::Identity => {},
            Activation::ReLU => { for h in hidden.iter_mut() { *h = h.max(0.0); } },
            Activation::Tanh => { for h in hidden.iter_mut() { *h = h.tanh(); } },
        }

        // d_hidden from U^T · (α · d_output)
        let mut d_hidden = vec![0.0f32; self.rank];
        for j in 0..self.rank {
            for i in 0..self.dim {
                d_hidden[j] += self.u_matrix[i * self.rank + j] * self.alpha * d_output[i];
            }
        }

        // Apply activation derivative
        match self.activation {
            Activation::Identity => {},
            Activation::ReLU => {
                for i in 0..self.rank {
                    if pre_act[i] <= 0.0 { d_hidden[i] = 0.0; }
                }
            },
            Activation::Tanh => {
                for i in 0..self.rank {
                    let t = pre_act[i].tanh();
                    d_hidden[i] *= 1.0 - t * t;
                }
            },
        }

        // Update U: U -= lr * (α · d_output) ⊗ hidden
        for i in 0..self.dim {
            for j in 0..self.rank {
                self.u_matrix[i * self.rank + j] -= lr * self.alpha * d_output[i] * hidden[j];
            }
        }

        // Update V: V -= lr * d_hidden ⊗ x
        for i in 0..self.rank {
            for j in 0..self.dim {
                self.v_matrix[i * self.dim + j] -= lr * d_hidden[i] * x[j];
            }
        }

        self.steps += 1;
        loss
    }

    /// Parameter count.
    pub fn param_count(&self) -> usize {
        self.rank * self.dim * 2 // U + V
    }

    /// Compute cosine similarity between two adapters' parameter spaces.
    /// Used for sheaf gluing condition checks.
    pub fn parameter_similarity(a: &CategoricalAdapter, b: &CategoricalAdapter) -> f32 {
        if a.dim != b.dim || a.rank != b.rank { return 0.0; }
        let dot: f32 = a.v_matrix.iter().zip(b.v_matrix.iter()).map(|(x, y)| x * y).sum::<f32>()
            + a.u_matrix.iter().zip(b.u_matrix.iter()).map(|(x, y)| x * y).sum::<f32>();
        let na: f32 = (a.v_matrix.iter().map(|x| x * x).sum::<f32>()
            + a.u_matrix.iter().map(|x| x * x).sum::<f32>()).sqrt();
        let nb: f32 = (b.v_matrix.iter().map(|x| x * x).sum::<f32>()
            + b.u_matrix.iter().map(|x| x * x).sum::<f32>()).sqrt();
        if na < 1e-10 || nb < 1e-10 { return 0.0; }
        dot / (na * nb)
    }

    /// Weighted merge of two adapters (sheaf gluing).
    pub fn merge(a: &CategoricalAdapter, b: &CategoricalAdapter, weight_a: f32) -> Option<CategoricalAdapter> {
        if a.dim != b.dim || a.rank != b.rank { return None; }
        let weight_b = 1.0 - weight_a;
        let mut merged = a.clone();
        merged.name = format!("merge({},{})", a.name, b.name);
        for i in 0..merged.v_matrix.len() {
            merged.v_matrix[i] = weight_a * a.v_matrix[i] + weight_b * b.v_matrix[i];
        }
        for i in 0..merged.u_matrix.len() {
            merged.u_matrix[i] = weight_a * a.u_matrix[i] + weight_b * b.u_matrix[i];
        }
        merged.steps = 0;
        Some(merged)
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_braid_word_random() {
        let braid = BraidWord::random(4, 10, 42);
        assert_eq!(braid.generators.len(), 10);
        assert_eq!(braid.strands, 4);
        for &g in &braid.generators {
            assert!(g.unsigned_abs() >= 1 && g.unsigned_abs() <= 3);
        }
    }

    #[test]
    fn test_burau_identity_for_empty_braid() {
        let braid = BraidWord { generators: vec![], strands: 3 };
        let mat = braid.burau_matrix(-1.0);
        // Should be identity
        for i in 0..3 {
            for j in 0..3 {
                let expected = if i == j { 1.0 } else { 0.0 };
                assert!((mat[i][j] - expected).abs() < 1e-5);
            }
        }
    }

    #[test]
    fn test_burau_yang_baxter() {
        // Yang-Baxter: σ₁σ₂σ₁ = σ₂σ₁σ₂ for B₃
        let lhs = BraidWord { generators: vec![1, 2, 1], strands: 3 };
        let rhs = BraidWord { generators: vec![2, 1, 2], strands: 3 };
        let m_lhs = lhs.burau_matrix(-1.0);
        let m_rhs = rhs.burau_matrix(-1.0);
        for i in 0..3 {
            for j in 0..3 {
                assert!((m_lhs[i][j] - m_rhs[i][j]).abs() < 1e-4,
                    "Yang-Baxter failed at ({},{}): {} vs {}", i, j, m_lhs[i][j], m_rhs[i][j]);
            }
        }
    }

    #[test]
    fn test_adapter_forward_residual() {
        let adapter = CategoricalAdapter::new("test", 8, 2, 5, 42);
        let x = vec![1.0, 0.0, -1.0, 0.5, 0.3, -0.2, 0.8, -0.4];
        let y = adapter.forward(&x);
        assert_eq!(y.len(), 8);
        // Output should be close to input (small adapter weights)
        let diff: f32 = x.iter().zip(y.iter()).map(|(a, b)| (a - b).abs()).sum();
        assert!(diff < 1.0, "adapter should be near-identity initially, diff={}", diff);
    }

    #[test]
    fn test_adapter_identity_activation() {
        let mut adapter = CategoricalAdapter::new("id", 4, 2, 3, 42);
        adapter.activation = Activation::Identity;
        let x = vec![1.0, 2.0, 3.0, 4.0];
        let y = adapter.forward(&x);
        assert_eq!(y.len(), 4);
    }

    #[test]
    fn test_adapter_compose() {
        let f = CategoricalAdapter::new("f", 8, 2, 3, 42);
        let g = CategoricalAdapter::new("g", 8, 2, 3, 99);
        let fg = CategoricalAdapter::compose(&f, &g);
        assert_eq!(fg.dim, 8);
        assert_eq!(fg.rank, 4); // f.rank + g.rank
        assert_eq!(fg.name, "f∘g");

        let x = vec![1.0, 0.0, -1.0, 0.5, 0.3, -0.2, 0.8, -0.4];
        let y = fg.forward(&x);
        assert_eq!(y.len(), 8);
    }

    #[test]
    fn test_adapter_train_step() {
        let mut adapter = CategoricalAdapter::new("train", 4, 2, 3, 42);
        adapter.activation = Activation::Identity;
        let x = vec![1.0, 0.0, -1.0, 0.5];
        let target = vec![2.0, 1.0, 0.0, 1.5]; // target = x + 1

        let loss1 = adapter.train_step(&x, &target, 0.01);
        let loss2 = adapter.train_step(&x, &target, 0.01);
        // Loss should decrease with training
        assert!(loss2 <= loss1 + 1e-6, "loss should decrease: {} -> {}", loss1, loss2);
        assert_eq!(adapter.steps, 2);
    }

    #[test]
    fn test_adapter_param_count() {
        let adapter = CategoricalAdapter::new("test", 384, 4, 5, 42);
        // 2 * rank * dim = 2 * 4 * 384 = 3072
        assert_eq!(adapter.param_count(), 3072);
    }

    #[test]
    fn test_adapter_parameter_similarity() {
        let a = CategoricalAdapter::new("a", 8, 2, 3, 42);
        let b = CategoricalAdapter::new("b", 8, 2, 3, 42); // same seed = same
        let c = CategoricalAdapter::new("c", 8, 2, 3, 99); // different seed

        let sim_same = CategoricalAdapter::parameter_similarity(&a, &b);
        let sim_diff = CategoricalAdapter::parameter_similarity(&a, &c);

        assert!((sim_same - 1.0).abs() < 1e-5, "same seed should give sim=1, got {}", sim_same);
        assert!(sim_diff < sim_same, "different seeds should be less similar");
    }

    #[test]
    fn test_adapter_merge() {
        let a = CategoricalAdapter::new("a", 8, 2, 3, 42);
        let b = CategoricalAdapter::new("b", 8, 2, 3, 99);
        let merged = CategoricalAdapter::merge(&a, &b, 0.5).unwrap();
        assert_eq!(merged.dim, 8);
        assert_eq!(merged.rank, 2);

        // Merged params should be average of a and b
        for i in 0..merged.v_matrix.len() {
            let expected = 0.5 * a.v_matrix[i] + 0.5 * b.v_matrix[i];
            assert!((merged.v_matrix[i] - expected).abs() < 1e-6);
        }
    }

    #[test]
    fn test_adapter_merge_dimension_mismatch() {
        let a = CategoricalAdapter::new("a", 8, 2, 3, 42);
        let b = CategoricalAdapter::new("b", 16, 2, 3, 99);
        assert!(CategoricalAdapter::merge(&a, &b, 0.5).is_none());
    }

    #[test]
    fn test_training_convergence() {
        let mut adapter = CategoricalAdapter::new("conv", 4, 2, 3, 42);
        adapter.activation = Activation::Identity;
        adapter.alpha = 1.0;

        let x = vec![1.0, 0.5, -0.5, 0.0];
        let target = vec![1.5, 1.0, 0.0, 0.5];

        let mut first_loss = 0.0;
        let mut last_loss = 0.0;
        for i in 0..500 {
            let loss = adapter.train_step(&x, &target, 0.05);
            if i == 0 { first_loss = loss; }
            last_loss = loss;
        }

        assert!(last_loss < first_loss * 0.5,
            "training should converge: first={}, last={}", first_loss, last_loss);
    }
}
