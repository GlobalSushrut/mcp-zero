//! Ethical Binary Tree for MCP-ZERO kernel
//!
//! Implements a decision tree for ethical governance of agent actions,
//! providing verifiable and traceable ethical decision-making.

use std::collections::HashMap;
use std::sync::{Arc, RwLock};
use anyhow::{Result, anyhow};
use serde::{Serialize, Deserialize};

use crate::agent::{AgentId, AgentConfig};
use crate::plugin::Plugin;

/// Node ID for the binary tree
type NodeId = String;

/// Decision outcome
#[derive(Debug, Clone, Copy, PartialEq, Eq, Serialize, Deserialize)]
pub enum Decision {
    /// Action is allowed
    Allow,
    /// Action is denied
    Deny,
}

/// Node in the ethical binary tree
#[derive(Debug, Clone, Serialize, Deserialize)]
struct EthicalNode {
    /// Node ID
    id: NodeId,
    
    /// Decision rule
    rule: String,
    
    /// Parent node ID
    parent: Option<NodeId>,
    
    /// Left child (false branch)
    left: Option<NodeId>,
    
    /// Right child (true branch)
    right: Option<NodeId>,
    
    /// Terminal decision if this is a leaf node
    decision: Option<Decision>,
}

/// Ethical Binary Tree implementation
pub struct EthicalBinaryTree {
    /// Nodes in the tree
    nodes: Arc<RwLock<HashMap<NodeId, EthicalNode>>>,
    
    /// Root node ID
    root: NodeId,
}

impl EthicalBinaryTree {
    /// Create a new EthicalBinaryTree with default rules
    pub fn new() -> Self {
        let root_id = "root".to_string();
        
        // Create default tree
        let mut nodes = HashMap::new();
        
        // Root node: general ethical consideration
        nodes.insert(
            root_id.clone(),
            EthicalNode {
                id: root_id.clone(),
                rule: "is_harmful".to_string(),
                parent: None,
                left: Some("allow".to_string()),  // not harmful -> allow
                right: Some("harmful".to_string()), // harmful -> check more
                decision: None,
            },
        );
        
        // Allow node (leaf)
        nodes.insert(
            "allow".to_string(),
            EthicalNode {
                id: "allow".to_string(),
                rule: "allow".to_string(),
                parent: Some(root_id.clone()),
                left: None,
                right: None,
                decision: Some(Decision::Allow),
            },
        );
        
        // Harmful actions - check for consent
        nodes.insert(
            "harmful".to_string(),
            EthicalNode {
                id: "harmful".to_string(),
                rule: "has_consent".to_string(),
                parent: Some(root_id.clone()),
                left: Some("deny".to_string()),   // no consent -> deny
                right: Some("check_legal".to_string()), // has consent -> check legal
                decision: None,
            },
        );
        
        // Deny node (leaf)
        nodes.insert(
            "deny".to_string(),
            EthicalNode {
                id: "deny".to_string(),
                rule: "deny".to_string(),
                parent: Some("harmful".to_string()),
                left: None,
                right: None,
                decision: Some(Decision::Deny),
            },
        );
        
        // Check legal status
        nodes.insert(
            "check_legal".to_string(),
            EthicalNode {
                id: "check_legal".to_string(),
                rule: "is_legal".to_string(),
                parent: Some("harmful".to_string()),
                left: Some("deny_illegal".to_string()),  // not legal -> deny
                right: Some("allow_legal".to_string()),  // legal -> allow
                decision: None,
            },
        );
        
        // Deny illegal (leaf)
        nodes.insert(
            "deny_illegal".to_string(),
            EthicalNode {
                id: "deny_illegal".to_string(),
                rule: "deny_illegal".to_string(),
                parent: Some("check_legal".to_string()),
                left: None,
                right: None,
                decision: Some(Decision::Deny),
            },
        );
        
        // Allow legal (leaf)
        nodes.insert(
            "allow_legal".to_string(),
            EthicalNode {
                id: "allow_legal".to_string(),
                rule: "allow_legal".to_string(),
                parent: Some("check_legal".to_string()),
                left: None,
                right: None,
                decision: Some(Decision::Allow),
            },
        );
        
        Self {
            nodes: Arc::new(RwLock::new(nodes)),
            root: root_id,
        }
    }
    
    /// Validate agent spawn
    pub fn validate_spawn(&self, config: &AgentConfig) -> Result<()> {
        // Check if agent name contains prohibited terms
        let prohibited_terms = ["malware", "exploit", "hack", "attack", "virus"];
        let name_lower = config.name.to_lowercase();
        
        for term in prohibited_terms {
            if name_lower.contains(term) {
                return Err(anyhow!("Agent name contains prohibited term: {}", term));
            }
        }
        
        // Evaluate using the ethical tree
        let eval_result = self.evaluate(
            "agent_spawn",
            &serde_json::json!({
                "name": config.name,
                "intents": config.intents,
            }),
        );
        
        match eval_result {
            Decision::Allow => Ok(()),
            Decision::Deny => Err(anyhow!("Ethical constraints prohibit this agent configuration")),
        }
    }
    
    /// Validate plugin
    pub fn validate_plugin(&self, plugin: &Plugin) -> Result<()> {
        // Check capabilities
        let capabilities = plugin.capabilities();
        
        // External access is a higher risk
        let risk_level = if capabilities.external_access {
            "high"
        } else if capabilities.plugin_call {
            "medium"
        } else {
            "low"
        };
        
        // Evaluate using the ethical tree
        let eval_result = self.evaluate(
            "plugin_validation",
            &serde_json::json!({
                "id": plugin.id(),
                "risk_level": risk_level,
                "external_access": capabilities.external_access,
                "plugin_call": capabilities.plugin_call,
            }),
        );
        
        match eval_result {
            Decision::Allow => Ok(()),
            Decision::Deny => Err(anyhow!("Plugin capabilities violate ethical constraints")),
        }
    }
    
    /// Validate execution
    pub fn validate_execution(&self, agent_id: &AgentId, intent: &str) -> Result<()> {
        // Check intent for prohibited actions
        let prohibited_actions = ["delete_all", "format", "wipe", "destroy"];
        let intent_lower = intent.to_lowercase();
        
        for action in prohibited_actions {
            if intent_lower.contains(action) {
                return Err(anyhow!("Intent contains prohibited action: {}", action));
            }
        }
        
        // Evaluate using the ethical tree
        let eval_result = self.evaluate(
            "execution_validation",
            &serde_json::json!({
                "agent_id": agent_id,
                "intent": intent,
            }),
        );
        
        match eval_result {
            Decision::Allow => Ok(()),
            Decision::Deny => Err(anyhow!("Intent violates ethical constraints")),
        }
    }
    
    /// Validate agent recovery
    pub fn validate_recovery(&self, _agent_id: &AgentId) -> Result<()> {
        // Always allow recovery for now
        // In a real implementation, would check recovery policies
        Ok(())
    }
    
    /// Evaluate a decision using the ethical tree
    pub fn evaluate(&self, context: &str, data: &serde_json::Value) -> Decision {
        let nodes = match self.nodes.read() {
            Ok(guard) => guard,
            Err(_) => return Decision::Deny, // Default to deny on error
        };
        
        // Start at root
        let mut current_id = &self.root;
        
        // Traverse tree
        loop {
            // Get current node
            let node = match nodes.get(current_id) {
                Some(n) => n,
                None => return Decision::Deny, // Default to deny on error
            };
            
            // Check if it's a leaf node with decision
            if let Some(decision) = node.decision {
                return decision;
            }
            
            // Evaluate rule
            let rule_result = self.evaluate_rule(&node.rule, context, data);
            
            // Choose branch
            current_id = if rule_result {
                // True branch
                match &node.right {
                    Some(id) => id,
                    None => return Decision::Deny, // Default to deny on error
                }
            } else {
                // False branch
                match &node.left {
                    Some(id) => id,
                    None => return Decision::Allow, // Default to allow on error
                }
            };
        }
    }
    
    /// Evaluate a rule
    fn evaluate_rule(&self, rule: &str, context: &str, data: &serde_json::Value) -> bool {
        // Simple rule evaluation
        match (rule, context) {
            // Specific rules first for agent spawn
            ("is_harmful", "agent_spawn") => {
                // Check agent configuration for harmful patterns
                if let Some(intents) = data.get("intents").and_then(|v| v.as_array()) {
                    // Check for harmful intents
                    for intent in intents {
                        if let Some(intent_str) = intent.as_str() {
                            let intent_lower = intent_str.to_lowercase();
                            if intent_lower.contains("harm") || 
                               intent_lower.contains("attack") || 
                               intent_lower.contains("exploit") {
                                return true; // Intent is potentially harmful
                            }
                        }
                    }
                }
                false // Not harmful
            },
            
            // General rules
            ("is_harmful", _) => {
                // Check for harmful patterns
                false // Default to not harmful
            },
            
            ("has_consent", _) => {
                // Check for consent
                true // Default to having consent
            },
            
            ("is_legal", _) => {
                // Check for legality
                true // Default to legal
            },
            
            // Plugin validation rules
            (_, "plugin_validation") => {
                // Check plugin risk level
                if let Some(risk) = data.get("risk_level").and_then(|v| v.as_str()) {
                    if risk == "high" {
                        if rule == "has_consent" {
                            // High-risk plugins require explicit consent
                            return false; // Default to no consent for high-risk plugins
                        }
                    }
                }
                false // Default to not violating rules
            },
            
            // Default
            _ => false,
        }
    }
    
    /// Add a custom ethical rule
    pub fn add_rule(&self, parent_id: &NodeId, rule_id: &str, rule: &str, decision: Option<Decision>) -> Result<()> {
        let mut nodes = self.nodes.write()
            .map_err(|_| anyhow!("Failed to acquire write lock on nodes"))?;
        
        // Check if parent exists
        if !nodes.contains_key(parent_id) {
            return Err(anyhow!("Parent node not found: {}", parent_id));
        }
        
        // Create new node
        let node = EthicalNode {
            id: rule_id.to_string(),
            rule: rule.to_string(),
            parent: Some(parent_id.clone()),
            left: None,
            right: None,
            decision,
        };
        
        // Update parent node
        let parent = nodes.get_mut(parent_id)
            .ok_or_else(|| anyhow!("Parent node not found: {}", parent_id))?;
        
        // Attach new node to parent
        parent.left = Some(rule_id.to_string());
        
        // Add new node
        nodes.insert(rule_id.to_string(), node);
        
        Ok(())
    }
}

impl Default for EthicalBinaryTree {
    fn default() -> Self {
        Self::new()
    }
}

#[cfg(test)]
mod tests {
    use super::*;
    
    #[test]
    fn test_ethical_tree() {
        let tree = EthicalBinaryTree::new();
        
        // Test allow decision
        let allow_result = tree.evaluate(
            "test",
            &serde_json::json!({
                "action": "benign"
            }),
        );
        assert_eq!(allow_result, Decision::Allow);
        
        // Test agent validation
        let config = AgentConfig {
            name: "test_agent".to_string(),
            entry: None,
            intents: vec!["greet".to_string()],
            hm: Default::default(),
            metadata: Default::default(),
        };
        
        assert!(tree.validate_spawn(&config).is_ok());
        
        // Test malicious agent rejection
        let malicious_config = AgentConfig {
            name: "malware_agent".to_string(),
            entry: None,
            intents: vec!["harm".to_string()],
            hm: Default::default(),
            metadata: Default::default(),
        };
        
        assert!(tree.validate_spawn(&malicious_config).is_err());
    }
}
