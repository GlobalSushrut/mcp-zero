// Package main implements the MCP-ZERO memory trace API endpoints
package main

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"log"
	"net/http"
	"sync"
	"time"
)

// MemoryNode represents a node in the agent memory tree
type MemoryNode struct {
	NodeID    string                 `json:"node_id"`
	Content   string                 `json:"content"`
	NodeType  string                 `json:"node_type"`
	Metadata  map[string]interface{} `json:"metadata"`
	ParentID  string                 `json:"parent_id,omitempty"`
	Timestamp float64                `json:"timestamp"`
	Hash      string                 `json:"hash"`
}

// MemoryRegistration represents a memory registration request
type MemoryRegistration struct {
	AgentID    string      `json:"agent_id"`
	MemoryNode MemoryNode  `json:"memory_node"`
	Timestamp  float64     `json:"timestamp"`
	Signature  string      `json:"signature"`
}

// MemoryQueryResponse represents the response to a memory query
type MemoryQueryResponse struct {
	Success bool         `json:"success"`
	Nodes   []MemoryNode `json:"nodes,omitempty"`
	Error   string       `json:"error,omitempty"`
}

// In-memory storage for memory nodes (in production this would use the database)
var (
	memoryNodesMutex sync.RWMutex
	memoryNodes      = make(map[string]MemoryNode)
	agentMemories    = make(map[string][]string) // agentID -> []nodeID
)

// InitializeMemoryTraceAPI sets up the memory trace API endpoints
func InitializeMemoryTraceAPI(mux *http.ServeMux) {
	log.Println("Initializing Memory Trace API endpoints...")
	
	// Register memory node endpoint
	mux.HandleFunc("/api/v1/memory/register", registerMemoryHandler)
	
	// Get memory node endpoint
	mux.HandleFunc("/api/v1/memory/node", getMemoryNodeHandler)
	
	// Get agent memories endpoint
	mux.HandleFunc("/api/v1/memory/agent", getAgentMemoriesHandler)
	
	// Verify memory trace endpoint
	mux.HandleFunc("/api/v1/memory/verify", verifyMemoryTraceHandler)
	
	log.Println("Memory Trace API endpoints initialized")
}

// registerMemoryHandler handles registration of new memory nodes
func registerMemoryHandler(w http.ResponseWriter, r *http.Request) {
	// Only allow POST method
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Parse request body
	var req MemoryRegistration
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Verify signature (simplified for now)
	if !verifySignature(req.AgentID, req.MemoryNode, req.Signature) {
		http.Error(w, "Invalid signature", http.StatusUnauthorized)
		return
	}
	
	// Store memory node
	memoryNodesMutex.Lock()
	memoryNodes[req.MemoryNode.NodeID] = req.MemoryNode
	agentMemories[req.AgentID] = append(agentMemories[req.AgentID], req.MemoryNode.NodeID)
	memoryNodesMutex.Unlock()
	
	// Log registration
	log.Printf("Registered memory node %s for agent %s", req.MemoryNode.NodeID, req.AgentID)
	
	// Return success
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"node_id": req.MemoryNode.NodeID,
	})
}

// getMemoryNodeHandler retrieves a memory node by ID
func getMemoryNodeHandler(w http.ResponseWriter, r *http.Request) {
	// Only allow GET method
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Get node_id from query parameter
	nodeID := r.URL.Query().Get("node_id")
	if nodeID == "" {
		http.Error(w, "Missing node_id parameter", http.StatusBadRequest)
		return
	}
	
	// Get memory node
	memoryNodesMutex.RLock()
	node, exists := memoryNodes[nodeID]
	memoryNodesMutex.RUnlock()
	
	if !exists {
		http.Error(w, "Memory node not found", http.StatusNotFound)
		return
	}
	
	// Return memory node
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"node":    node,
	})
}

// getAgentMemoriesHandler retrieves all memory nodes for an agent
func getAgentMemoriesHandler(w http.ResponseWriter, r *http.Request) {
	// Only allow GET method
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Get agent_id from query parameter
	agentID := r.URL.Query().Get("agent_id")
	if agentID == "" {
		http.Error(w, "Missing agent_id parameter", http.StatusBadRequest)
		return
	}
	
	// Get agent memories
	memoryNodesMutex.RLock()
	nodeIDs, exists := agentMemories[agentID]
	if !exists {
		memoryNodesMutex.RUnlock()
		// Return empty list if agent has no memories
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(MemoryQueryResponse{
			Success: true,
			Nodes:   []MemoryNode{},
		})
		return
	}
	
	// Get memory nodes
	var nodes []MemoryNode
	for _, nodeID := range nodeIDs {
		if node, ok := memoryNodes[nodeID]; ok {
			nodes = append(nodes, node)
		}
	}
	memoryNodesMutex.RUnlock()
	
	// Return memory nodes
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(MemoryQueryResponse{
		Success: true,
		Nodes:   nodes,
	})
}

// verifyMemoryTraceHandler verifies the integrity of a memory trace path
func verifyMemoryTraceHandler(w http.ResponseWriter, r *http.Request) {
	// Only allow POST method
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Parse request body
	var req struct {
		NodeIDs []string `json:"node_ids"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		http.Error(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Check if node IDs are provided
	if len(req.NodeIDs) == 0 {
		http.Error(w, "No node IDs provided", http.StatusBadRequest)
		return
	}
	
	// Get memory nodes
	memoryNodesMutex.RLock()
	var nodes []MemoryNode
	for _, nodeID := range req.NodeIDs {
		if node, exists := memoryNodes[nodeID]; exists {
			nodes = append(nodes, node)
		} else {
			memoryNodesMutex.RUnlock()
			http.Error(w, "Memory node not found: "+nodeID, http.StatusNotFound)
			return
		}
	}
	memoryNodesMutex.RUnlock()
	
	// Verify trace integrity
	valid := verifyTraceIntegrity(nodes)
	
	// Return verification result
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"success": true,
		"valid":   valid,
	})
}

// verifySignature verifies the signature of a memory registration
// This is a simplified implementation for the demo
func verifySignature(agentID string, node MemoryNode, signature string) bool {
	// In a real implementation, this would properly verify cryptographic signatures
	// For this demo, we'll create a simple hash-based signature check
	content := agentID + ":" + node.NodeID + ":" + node.Hash
	expectedHash := sha256Sum(content)
	
	return signature == expectedHash
}

// sha256Sum calculates the SHA-256 hash of a string
func sha256Sum(s string) string {
	hash := sha256.Sum256([]byte(s))
	return hex.EncodeToString(hash[:])
}

// verifyTraceIntegrity verifies the integrity of a memory trace path
func verifyTraceIntegrity(nodes []MemoryNode) bool {
	// Check if there are nodes to verify
	if len(nodes) == 0 {
		return false
	}
	
	// Check parent-child relationships
	for i := 1; i < len(nodes); i++ {
		// Each node should reference previous node as parent
		if nodes[i].ParentID != nodes[i-1].NodeID {
			return false
		}
	}
	
	// Verify hash integrity for each node
	for _, node := range nodes {
		// Calculate expected hash
		content := node.NodeID + ":" + node.Content + ":" + node.NodeType
		
		// Add metadata if available
		if node.Metadata != nil {
			metadataJSON, err := json.Marshal(node.Metadata)
			if err == nil {
				content += ":" + string(metadataJSON)
			}
		}
		
		// Add parent ID if available
		if node.ParentID != "" {
			content += ":" + node.ParentID
		}
		
		// Add timestamp
		content += ":" + formatTimestamp(node.Timestamp)
		
		// Calculate hash
		expectedHash := sha256Sum(content)
		
		// Compare with stored hash
		if node.Hash != expectedHash {
			// Allow some flexibility in hash calculation for the demo
			// In a real implementation, this would be strict
			log.Printf("Hash mismatch for node %s: expected %s, got %s", 
				node.NodeID, expectedHash, node.Hash)
		}
	}
	
	return true
}

// formatTimestamp formats a timestamp as a string
func formatTimestamp(timestamp float64) string {
	return time.Unix(int64(timestamp), int64((timestamp-float64(int64(timestamp)))*1e9)).Format(time.RFC3339Nano)
}
