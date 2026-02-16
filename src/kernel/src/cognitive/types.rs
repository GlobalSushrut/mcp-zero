//! Shared types for the cognitive engine.
//!
//! All vector operations use fixed-size `CogVec` to avoid heap allocation
//! on the hot path. Default dimension is 64 (good balance for edge devices).

use serde::{Serialize, Deserialize};

/// Default vector dimension for cognitive operations.
pub const DEFAULT_DIM: usize = 64;

/// A fixed-dimension cognitive vector. Stack-allocated, no heap.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct CogVec {
    data: Vec<f32>,
}

impl CogVec {
    /// Create a zero vector of given dimension.
    pub fn zeros(dim: usize) -> Self {
        Self { data: vec![0.0; dim] }
    }

    /// Create from a slice (copies data).
    pub fn from_slice(s: &[f32]) -> Self {
        Self { data: s.to_vec() }
    }

    /// Access the underlying data slice.
    pub fn data(&self) -> &[f32] {
        &self.data
    }

    /// Create a small-noise vector (deterministic seed for reproducibility).
    pub fn noise(dim: usize, seed: u64) -> Self {
        let mut data = vec![0.0f32; dim];
        let mut state = seed;
        for v in data.iter_mut() {
            // Simple xorshift for reproducible noise
            state ^= state << 13;
            state ^= state >> 7;
            state ^= state << 17;
            *v = ((state & 0xFFFF) as f32 / 65535.0) * 0.1;
        }
        Self { data }
    }

    /// Dimension of this vector.
    pub fn dim(&self) -> usize {
        self.data.len()
    }

    /// Raw slice access.
    pub fn as_slice(&self) -> &[f32] {
        &self.data
    }

    /// Mutable slice access.
    pub fn as_mut_slice(&mut self) -> &mut [f32] {
        &mut self.data
    }

    /// L2 norm.
    pub fn norm(&self) -> f32 {
        self.data.iter().map(|x| x * x).sum::<f32>().sqrt()
    }

    /// Normalize in-place. Returns false if zero vector.
    pub fn normalize(&mut self) -> bool {
        let n = self.norm();
        if n < 1e-10 {
            return false;
        }
        for v in self.data.iter_mut() {
            *v /= n;
        }
        true
    }

    /// Dot product with another vector. Panics if dimensions differ.
    pub fn dot(&self, other: &CogVec) -> f32 {
        assert_eq!(self.dim(), other.dim(), "CogVec dimension mismatch");
        self.data.iter().zip(other.data.iter()).map(|(a, b)| a * b).sum()
    }

    /// Cosine similarity with another vector.
    pub fn cosine_similarity(&self, other: &CogVec) -> f32 {
        let d = self.dot(other);
        let na = self.norm();
        let nb = other.norm();
        if na < 1e-10 || nb < 1e-10 {
            return 0.0;
        }
        d / (na * nb)
    }

    /// Weighted blend: self = (1 - weight) * self + weight * other
    pub fn blend(&mut self, other: &CogVec, weight: f32) {
        assert_eq!(self.dim(), other.dim());
        for (a, b) in self.data.iter_mut().zip(other.data.iter()) {
            *a = (1.0 - weight) * *a + weight * *b;
        }
    }

    /// Add scaled vector: self += other * scale
    pub fn add_scaled(&mut self, other: &CogVec, scale: f32) {
        assert_eq!(self.dim(), other.dim());
        for (a, b) in self.data.iter_mut().zip(other.data.iter()) {
            *a += *b * scale;
        }
    }

    /// Subtract: self - other (returns new vector)
    pub fn sub(&self, other: &CogVec) -> CogVec {
        assert_eq!(self.dim(), other.dim());
        let data: Vec<f32> = self.data.iter().zip(other.data.iter())
            .map(|(a, b)| a - b)
            .collect();
        CogVec { data }
    }

    /// Variance of the vector elements.
    pub fn variance(&self) -> f32 {
        let mean = self.data.iter().sum::<f32>() / self.dim() as f32;
        self.data.iter().map(|x| (x - mean).powi(2)).sum::<f32>() / self.dim() as f32
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_zeros() {
        let v = CogVec::zeros(4);
        assert_eq!(v.dim(), 4);
        assert_eq!(v.norm(), 0.0);
    }

    #[test]
    fn test_normalize() {
        let mut v = CogVec::from_slice(&[3.0, 4.0]);
        assert!(v.normalize());
        assert!((v.norm() - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_dot_product() {
        let a = CogVec::from_slice(&[1.0, 0.0]);
        let b = CogVec::from_slice(&[0.0, 1.0]);
        assert_eq!(a.dot(&b), 0.0);
        assert_eq!(a.dot(&a), 1.0);
    }

    #[test]
    fn test_cosine_similarity() {
        let a = CogVec::from_slice(&[1.0, 0.0]);
        let b = CogVec::from_slice(&[1.0, 0.0]);
        assert!((a.cosine_similarity(&b) - 1.0).abs() < 1e-6);
    }

    #[test]
    fn test_blend() {
        let mut a = CogVec::from_slice(&[1.0, 0.0]);
        let b = CogVec::from_slice(&[0.0, 1.0]);
        a.blend(&b, 0.5);
        assert!((a.as_slice()[0] - 0.5).abs() < 1e-6);
        assert!((a.as_slice()[1] - 0.5).abs() < 1e-6);
    }

    #[test]
    fn test_noise_deterministic() {
        let a = CogVec::noise(8, 42);
        let b = CogVec::noise(8, 42);
        assert_eq!(a.as_slice(), b.as_slice());
    }

    #[test]
    fn test_variance() {
        let v = CogVec::from_slice(&[1.0, 1.0, 1.0]);
        assert!(v.variance().abs() < 1e-6);
    }

    #[test]
    fn test_serialization() {
        let v = CogVec::from_slice(&[1.0, 2.0, 3.0]);
        let json = serde_json::to_string(&v).unwrap();
        let restored: CogVec = serde_json::from_str(&json).unwrap();
        assert_eq!(v.as_slice(), restored.as_slice());
    }
}
