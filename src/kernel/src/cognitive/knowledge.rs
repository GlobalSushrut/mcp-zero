//! Knowledge Store — file-backed fact storage with cosine similarity search.
//!
//! Each fact is a text string with an associated embedding vector.
//! Facts are persisted as JSON-lines (one JSON object per line).
//! Search uses cosine similarity over embeddings.

use std::collections::HashMap;
use std::path::{Path, PathBuf};
use std::fs;
use std::io::{BufRead, Write};
use anyhow::{Result, Context};
use serde::{Serialize, Deserialize};
use super::types::CogVec;

/// A single fact in the knowledge store.
#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Fact {
    pub id: String,
    pub text: String,
    pub embedding: CogVec,
    pub weight: f32,
    pub access_count: u32,
}

/// Knowledge Store: file-backed, cosine-similarity searchable fact store.
#[derive(Debug)]
pub struct KnowledgeStore {
    facts: HashMap<String, Fact>,
    file_path: Option<PathBuf>,
    next_id: u64,
}

/// Search result from the knowledge store.
#[derive(Debug, Serialize)]
pub struct SearchResult {
    pub id: String,
    pub text: String,
    pub similarity: f32,
    pub weight: f32,
    pub score: f32,
}

impl KnowledgeStore {
    /// Create an in-memory knowledge store (no persistence).
    pub fn new() -> Self {
        Self {
            facts: HashMap::new(),
            file_path: None,
            next_id: 1,
        }
    }

    /// Create a knowledge store backed by a file.
    pub fn with_file<P: AsRef<Path>>(path: P) -> Result<Self> {
        let path = path.as_ref().to_path_buf();
        let mut store = Self {
            facts: HashMap::new(),
            file_path: Some(path.clone()),
            next_id: 1,
        };

        // Load existing facts if file exists
        if path.exists() {
            store.load_from_file()?;
        }

        Ok(store)
    }

    /// Add a fact with its embedding vector.
    pub fn add_fact(&mut self, text: &str, embedding: CogVec) -> Result<String> {
        let id = format!("fact_{}", self.next_id);
        self.next_id += 1;

        let fact = Fact {
            id: id.clone(),
            text: text.to_string(),
            embedding,
            weight: 1.0,
            access_count: 0,
        };

        self.facts.insert(id.clone(), fact);

        // Persist if file-backed
        if self.file_path.is_some() {
            self.save_to_file()?;
        }

        Ok(id)
    }

    /// Search for facts by cosine similarity to a query embedding.
    pub fn search(&mut self, query: &CogVec, top_k: usize) -> Vec<SearchResult> {
        let mut results: Vec<SearchResult> = self.facts.values_mut().map(|fact| {
            let similarity = query.cosine_similarity(&fact.embedding);
            fact.access_count += 1;
            let score = similarity * fact.weight;

            SearchResult {
                id: fact.id.clone(),
                text: fact.text.clone(),
                similarity,
                weight: fact.weight,
                score,
            }
        }).collect();

        results.sort_by(|a, b| b.score.partial_cmp(&a.score).unwrap_or(std::cmp::Ordering::Equal));
        results.truncate(top_k);
        results
    }

    /// Update the weight of a fact.
    pub fn update_weight(&mut self, fact_id: &str, new_weight: f32) -> bool {
        if let Some(fact) = self.facts.get_mut(fact_id) {
            fact.weight = new_weight.max(0.0).min(10.0);
            true
        } else {
            false
        }
    }

    /// Get fact count.
    pub fn len(&self) -> usize {
        self.facts.len()
    }

    /// Check if empty.
    pub fn is_empty(&self) -> bool {
        self.facts.is_empty()
    }

    /// Remove a fact by ID.
    pub fn remove(&mut self, fact_id: &str) -> bool {
        self.facts.remove(fact_id).is_some()
    }

    /// Load facts from the backing file.
    fn load_from_file(&mut self) -> Result<()> {
        let path = self.file_path.as_ref().unwrap();
        let file = fs::File::open(path)
            .with_context(|| format!("open knowledge file: {}", path.display()))?;
        let reader = std::io::BufReader::new(file);

        for line in reader.lines() {
            let line = line?;
            if line.trim().is_empty() {
                continue;
            }
            let fact: Fact = serde_json::from_str(&line)
                .with_context(|| "parse fact line")?;

            // Track max ID
            if let Some(num_str) = fact.id.strip_prefix("fact_") {
                if let Ok(num) = num_str.parse::<u64>() {
                    self.next_id = self.next_id.max(num + 1);
                }
            }

            self.facts.insert(fact.id.clone(), fact);
        }

        Ok(())
    }

    /// Save all facts to the backing file (full rewrite).
    fn save_to_file(&self) -> Result<()> {
        let path = self.file_path.as_ref().unwrap();

        if let Some(parent) = path.parent() {
            fs::create_dir_all(parent)?;
        }

        let mut file = fs::File::create(path)
            .with_context(|| format!("create knowledge file: {}", path.display()))?;

        for fact in self.facts.values() {
            let line = serde_json::to_string(fact)?;
            writeln!(file, "{}", line)?;
        }

        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn test_add_and_search() {
        let mut store = KnowledgeStore::new();

        let v1 = CogVec::from_slice(&[1.0, 0.0, 0.0, 0.0]);
        let v2 = CogVec::from_slice(&[0.0, 1.0, 0.0, 0.0]);
        let v3 = CogVec::from_slice(&[0.9, 0.1, 0.0, 0.0]);

        store.add_fact("fact about X", v1).unwrap();
        store.add_fact("fact about Y", v2).unwrap();

        // Search with v3 (close to v1)
        let results = store.search(&v3, 2);
        assert_eq!(results.len(), 2);
        assert!(results[0].text.contains("X"), "X should rank first");
    }

    #[test]
    fn test_weight_affects_ranking() {
        let mut store = KnowledgeStore::new();

        let v1 = CogVec::from_slice(&[1.0, 0.0]);
        let v2 = CogVec::from_slice(&[0.9, 0.1]);

        let id1 = store.add_fact("low weight", v1).unwrap();
        let _id2 = store.add_fact("high weight", v2).unwrap();

        // Lower weight on id1
        store.update_weight(&id1, 0.1);

        let query = CogVec::from_slice(&[1.0, 0.0]);
        let results = store.search(&query, 2);
        // "high weight" should rank first despite slightly lower similarity
        assert!(results[0].text.contains("high weight"));
    }

    #[test]
    fn test_remove_fact() {
        let mut store = KnowledgeStore::new();
        let v = CogVec::from_slice(&[1.0, 0.0]);
        let id = store.add_fact("removable", v).unwrap();
        assert_eq!(store.len(), 1);
        assert!(store.remove(&id));
        assert_eq!(store.len(), 0);
    }

    #[test]
    fn test_file_persistence() {
        let path = format!("/tmp/mcp_test_knowledge_{}.jsonl", std::process::id());
        let _ = fs::remove_file(&path);

        // Write
        {
            let mut store = KnowledgeStore::with_file(&path).unwrap();
            let v = CogVec::from_slice(&[1.0, 2.0, 3.0]);
            store.add_fact("persisted fact", v).unwrap();
        }

        // Read back
        {
            let mut store = KnowledgeStore::with_file(&path).unwrap();
            assert_eq!(store.len(), 1);
            let query = CogVec::from_slice(&[1.0, 2.0, 3.0]);
            let results = store.search(&query, 1);
            assert_eq!(results[0].text, "persisted fact");
        }

        let _ = fs::remove_file(&path);
    }
}
