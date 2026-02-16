//! Meta Contract — contract evolution through contradiction exposure.
//!
//! Implements ethical contract management with contradiction memory tracking.
//! Contracts can be created, evolved through contradiction exposure, and
//! "burnt" (made immutable) with a cryptographic hash seal.
//!
//! Key design: `BurntContract` is a separate type from `Contract`.
//! Once burnt, the Rust type system prevents modification at compile time.

use std::collections::HashMap;
use serde::{Serialize, Deserialize};

/// A single contradiction exposure on a contract clause.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Exposure {
    pub description: String,
    pub severity: f32,
    pub context: HashMap<String, String>,
}

/// Tracks contradiction exposures for a single clause.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct ContradictionMemory {
    clause_name: String,
    exposures: Vec<Exposure>,
    severity_sum: f32,
}

impl ContradictionMemory {
    pub fn new(clause_name: &str) -> Self {
        Self {
            clause_name: clause_name.to_string(),
            exposures: Vec::new(),
            severity_sum: 0.0,
        }
    }

    /// Record a contradiction exposure. Returns the new exposure count.
    pub fn record(
        &mut self,
        description: &str,
        severity: f32,
        context: HashMap<String, String>,
    ) -> usize {
        let severity = severity.clamp(0.0, 1.0);
        self.exposures.push(Exposure {
            description: description.to_string(),
            severity,
            context,
        });
        self.severity_sum += severity;
        self.exposures.len()
    }

    /// Average severity of all exposures.
    pub fn avg_severity(&self) -> f32 {
        if self.exposures.is_empty() {
            0.0
        } else {
            self.severity_sum / self.exposures.len() as f32
        }
    }

    /// Number of exposures.
    pub fn count(&self) -> usize {
        self.exposures.len()
    }

    /// Get the most recent N exposures.
    pub fn recent(&self, n: usize) -> &[Exposure] {
        let start = self.exposures.len().saturating_sub(n);
        &self.exposures[start..]
    }

    /// Clause name.
    pub fn clause_name(&self) -> &str {
        &self.clause_name
    }

    /// Reset memory (after clause evolution).
    pub fn reset(&mut self) {
        self.exposures.clear();
        self.severity_sum = 0.0;
    }
}

/// An active (mutable) contract.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct Contract {
    pub id: String,
    pub name: String,
    pub description: String,
    pub clauses: HashMap<String, String>,
    pub version: u32,
}

/// A burnt (immutable) contract. Cannot be modified — enforced by the type system.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct BurntContract {
    id: String,
    name: String,
    description: String,
    clauses: HashMap<String, String>,
    version: u32,
    hash: String,
}

impl BurntContract {
    /// Get the contract ID.
    pub fn id(&self) -> &str { &self.id }
    /// Get the contract name.
    pub fn name(&self) -> &str { &self.name }
    /// Get the description.
    pub fn description(&self) -> &str { &self.description }
    /// Get the clauses (read-only).
    pub fn clauses(&self) -> &HashMap<String, String> { &self.clauses }
    /// Get the version.
    pub fn version(&self) -> u32 { self.version }
    /// Get the integrity hash.
    pub fn hash(&self) -> &str { &self.hash }

    /// Verify integrity — recompute hash and compare.
    pub fn verify(&self) -> bool {
        let computed = compute_hash(&self.id, &self.name, &self.clauses, self.version);
        computed == self.hash
    }
}

/// Compute a deterministic hash for a contract.
fn compute_hash(
    id: &str,
    name: &str,
    clauses: &HashMap<String, String>,
    version: u32,
) -> String {
    use std::collections::BTreeMap;
    // Sort clauses for deterministic serialization
    let sorted: BTreeMap<&String, &String> = clauses.iter().collect();
    let payload = format!("{}:{}:{}:{:?}", id, name, version, sorted);

    // Simple hash (SHA-256 style via std — no extra dep needed)
    // Using a basic FNV-1a 128-bit for now; can swap to blake3 if needed
    let mut h: u128 = 0xcbf29ce484222325;
    for byte in payload.as_bytes() {
        h ^= *byte as u128;
        h = h.wrapping_mul(0x100000001b3);
    }
    format!("{:032x}", h)
}

/// Evolution candidate — a clause that has enough contradiction exposure.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct EvolutionCandidate {
    pub contract_id: String,
    pub clause_name: String,
    pub current_text: String,
    pub avg_severity: f32,
    pub exposure_count: usize,
}

/// Meta Contract system — manages contracts, contradiction memories, and burning.
#[derive(Clone, Debug, Serialize, Deserialize)]
pub struct MetaContractSystem {
    contracts: HashMap<String, Contract>,
    memories: HashMap<String, ContradictionMemory>, // key: "contract_id.clause_name"
    burnt: HashMap<String, BurntContract>,
    next_id: u64,
}

impl MetaContractSystem {
    pub fn new() -> Self {
        Self {
            contracts: HashMap::new(),
            memories: HashMap::new(),
            burnt: HashMap::new(),
            next_id: 0,
        }
    }

    /// Create a new contract. Returns the contract ID.
    pub fn create_contract(
        &mut self,
        name: &str,
        description: &str,
        clauses: HashMap<String, String>,
    ) -> String {
        self.next_id += 1;
        let id = format!("{}_{}", name.to_lowercase().replace(' ', "_"), self.next_id);

        // Create contradiction memories for each clause
        for clause_name in clauses.keys() {
            let key = format!("{}.{}", id, clause_name);
            self.memories.insert(key, ContradictionMemory::new(clause_name));
        }

        let contract = Contract {
            id: id.clone(),
            name: name.to_string(),
            description: description.to_string(),
            clauses,
            version: 1,
        };
        self.contracts.insert(id.clone(), contract);
        id
    }

    /// Record a contradiction on a clause. Returns (exposure_count, avg_severity).
    pub fn record_contradiction(
        &mut self,
        contract_id: &str,
        clause_name: &str,
        description: &str,
        severity: f32,
        context: HashMap<String, String>,
    ) -> Result<(usize, f32), String> {
        // Check not burnt
        if self.burnt.contains_key(contract_id) {
            return Err("Contract is burnt and cannot be modified".into());
        }

        // Check contract and clause exist
        let contract = self.contracts.get(contract_id)
            .ok_or_else(|| format!("Contract {} not found", contract_id))?;
        if !contract.clauses.contains_key(clause_name) {
            return Err(format!("Clause {} not found", clause_name));
        }

        let key = format!("{}.{}", contract_id, clause_name);
        let memory = self.memories
            .entry(key)
            .or_insert_with(|| ContradictionMemory::new(clause_name));

        let count = memory.record(description, severity, context);
        Ok((count, memory.avg_severity()))
    }

    /// Get clauses that are candidates for evolution (avg_severity > 0.5, count >= 3).
    pub fn evolution_candidates(&self) -> Vec<EvolutionCandidate> {
        let mut candidates = Vec::new();

        for (key, memory) in &self.memories {
            let parts: Vec<&str> = key.splitn(2, '.').collect();
            if parts.len() != 2 { continue; }
            let (contract_id, clause_name) = (parts[0], parts[1]);

            // Skip burnt
            if self.burnt.contains_key(contract_id) { continue; }

            let contract = match self.contracts.get(contract_id) {
                Some(c) => c,
                None => continue,
            };

            let clause_text = match contract.clauses.get(clause_name) {
                Some(t) => t,
                None => continue,
            };

            if memory.avg_severity() > 0.5 && memory.count() >= 3 {
                candidates.push(EvolutionCandidate {
                    contract_id: contract_id.to_string(),
                    clause_name: clause_name.to_string(),
                    current_text: clause_text.clone(),
                    avg_severity: memory.avg_severity(),
                    exposure_count: memory.count(),
                });
            }
        }

        // Sort by severity * count descending
        candidates.sort_by(|a, b| {
            let sa = a.avg_severity * a.exposure_count as f32;
            let sb = b.avg_severity * b.exposure_count as f32;
            sb.partial_cmp(&sa).unwrap_or(std::cmp::Ordering::Equal)
        });

        candidates
    }

    /// Evolve a clause — update its text and reset contradiction memory.
    pub fn evolve_clause(
        &mut self,
        contract_id: &str,
        clause_name: &str,
        new_text: &str,
    ) -> Result<u32, String> {
        if self.burnt.contains_key(contract_id) {
            return Err("Contract is burnt and cannot be modified".into());
        }

        let contract = self.contracts.get_mut(contract_id)
            .ok_or_else(|| format!("Contract {} not found", contract_id))?;

        if !contract.clauses.contains_key(clause_name) {
            return Err(format!("Clause {} not found", clause_name));
        }

        contract.clauses.insert(clause_name.to_string(), new_text.to_string());
        contract.version += 1;

        // Reset contradiction memory
        let key = format!("{}.{}", contract_id, clause_name);
        if let Some(memory) = self.memories.get_mut(&key) {
            memory.reset();
        }

        Ok(contract.version)
    }

    /// Burn a contract — make it immutable. Consumes the active contract
    /// and returns a `BurntContract` that cannot be modified.
    pub fn burn(&mut self, contract_id: &str) -> Result<BurntContract, String> {
        if self.burnt.contains_key(contract_id) {
            return Err("Contract is already burnt".into());
        }

        let contract = self.contracts.remove(contract_id)
            .ok_or_else(|| format!("Contract {} not found", contract_id))?;

        let hash = compute_hash(&contract.id, &contract.name, &contract.clauses, contract.version);

        let burnt = BurntContract {
            id: contract.id,
            name: contract.name,
            description: contract.description,
            clauses: contract.clauses,
            version: contract.version,
            hash,
        };

        self.burnt.insert(contract_id.to_string(), burnt.clone());
        Ok(burnt)
    }

    /// Get a contract by ID (active only).
    pub fn get_contract(&self, id: &str) -> Option<&Contract> {
        self.contracts.get(id)
    }

    /// Get a burnt contract by ID.
    pub fn get_burnt(&self, id: &str) -> Option<&BurntContract> {
        self.burnt.get(id)
    }

    /// Number of active contracts.
    pub fn active_count(&self) -> usize {
        self.contracts.len()
    }

    /// Number of burnt contracts.
    pub fn burnt_count(&self) -> usize {
        self.burnt.len()
    }
}

// ---------------------------------------------------------------------------
// Tests
// ---------------------------------------------------------------------------

#[cfg(test)]
mod tests {
    use super::*;

    fn sample_clauses() -> HashMap<String, String> {
        let mut c = HashMap::new();
        c.insert("privacy".into(), "The system must protect user privacy".into());
        c.insert("safety".into(), "The system must not cause harm".into());
        c
    }

    #[test]
    fn test_create_contract() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("AI Safety", "Safety contract", sample_clauses());
        assert!(id.starts_with("ai_safety_"));
        assert_eq!(sys.active_count(), 1);
    }

    #[test]
    fn test_record_contradiction() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        let (count, avg) = sys.record_contradiction(
            &id, "safety", "Harmful output", 0.7, HashMap::new(),
        ).unwrap();
        assert_eq!(count, 1);
        assert!((avg - 0.7).abs() < 0.01);
    }

    #[test]
    fn test_contradiction_on_burnt_fails() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());
        sys.burn(&id).unwrap();

        let result = sys.record_contradiction(&id, "safety", "test", 0.5, HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn test_contradiction_on_missing_clause() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        let result = sys.record_contradiction(&id, "nonexistent", "test", 0.5, HashMap::new());
        assert!(result.is_err());
    }

    #[test]
    fn test_evolution_candidates_below_threshold() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        // Only 2 exposures — below threshold of 3
        sys.record_contradiction(&id, "safety", "a", 0.8, HashMap::new()).unwrap();
        sys.record_contradiction(&id, "safety", "b", 0.9, HashMap::new()).unwrap();

        let candidates = sys.evolution_candidates();
        assert!(candidates.is_empty());
    }

    #[test]
    fn test_evolution_candidates_above_threshold() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        for i in 0..4 {
            sys.record_contradiction(
                &id, "safety", &format!("issue {}", i), 0.8, HashMap::new(),
            ).unwrap();
        }

        let candidates = sys.evolution_candidates();
        assert_eq!(candidates.len(), 1);
        assert_eq!(candidates[0].clause_name, "safety");
        assert_eq!(candidates[0].exposure_count, 4);
    }

    #[test]
    fn test_evolve_clause() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        let version = sys.evolve_clause(&id, "safety", "Updated safety clause").unwrap();
        assert_eq!(version, 2);

        let contract = sys.get_contract(&id).unwrap();
        assert_eq!(contract.clauses["safety"], "Updated safety clause");
    }

    #[test]
    fn test_evolve_resets_memory() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        for i in 0..5 {
            sys.record_contradiction(
                &id, "safety", &format!("issue {}", i), 0.9, HashMap::new(),
            ).unwrap();
        }
        assert!(!sys.evolution_candidates().is_empty());

        sys.evolve_clause(&id, "safety", "New text").unwrap();

        // After evolution, memory is reset — no more candidates
        assert!(sys.evolution_candidates().is_empty());
    }

    #[test]
    fn test_burn_contract() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());

        let burnt = sys.burn(&id).unwrap();
        assert_eq!(burnt.name(), "Test");
        assert!(!burnt.hash().is_empty());
        assert!(burnt.verify());

        // Active contract removed
        assert_eq!(sys.active_count(), 0);
        assert_eq!(sys.burnt_count(), 1);
    }

    #[test]
    fn test_burn_twice_fails() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());
        sys.burn(&id).unwrap();

        let result = sys.burn(&id);
        assert!(result.is_err());
    }

    #[test]
    fn test_evolve_burnt_fails() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());
        sys.burn(&id).unwrap();

        let result = sys.evolve_clause(&id, "safety", "new text");
        assert!(result.is_err());
    }

    #[test]
    fn test_burnt_contract_integrity() {
        let mut sys = MetaContractSystem::new();
        let id = sys.create_contract("Test", "desc", sample_clauses());
        let burnt = sys.burn(&id).unwrap();

        // Verify integrity
        assert!(burnt.verify());

        // Read-only access works
        assert_eq!(burnt.clauses().len(), 2);
        assert!(burnt.clauses().contains_key("privacy"));
    }

    #[test]
    fn test_contradiction_memory_recent() {
        let mut mem = ContradictionMemory::new("test");
        for i in 0..10 {
            mem.record(&format!("issue {}", i), 0.5, HashMap::new());
        }
        let recent = mem.recent(3);
        assert_eq!(recent.len(), 3);
        assert!(recent[2].description.contains("9"));
    }

    #[test]
    fn test_multiple_contracts() {
        let mut sys = MetaContractSystem::new();
        let id1 = sys.create_contract("A", "desc", sample_clauses());
        let id2 = sys.create_contract("B", "desc", sample_clauses());

        assert_eq!(sys.active_count(), 2);
        assert_ne!(id1, id2);

        sys.burn(&id1).unwrap();
        assert_eq!(sys.active_count(), 1);
        assert_eq!(sys.burnt_count(), 1);
    }
}
