// MCP-ZERO Database API Endpoints
// Compatible with Go 1.13
package main

import (
	"encoding/json"
	"log"
	"net/http"
	"time"
)

// startDBEndpoints sets up HTTP endpoints for DB operations
func (s *MCPServer) startDBEndpoints(mux *http.ServeMux) {
	// Memory retrieval endpoint
	mux.HandleFunc("/db/memory/get", s.handleGetAgentMemory)
	
	// Memory snapshot operations
	mux.HandleFunc("/db/memory/snapshot", s.handleSnapshotMemory)
	
	// Memory optimization for hardware constraints
	mux.HandleFunc("/db/memory/compact", s.handleCompactMemory)
}

// handleGetAgentMemory retrieves agent memories based on parameters
func (s *MCPServer) handleGetAgentMemory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract parameters
	agentID := r.URL.Query().Get("agent_id")
	keyPrefix := r.URL.Query().Get("prefix")
	limit := r.URL.Query().Get("limit")
	
	if agentID == "" {
		http.Error(w, "Missing required parameter: agent_id", http.StatusBadRequest)
		return
	}
	
	// Retrieve memories from binary tree
	memories := s.dbService.getAgentMemory(agentID, keyPrefix)
	if memories == nil {
		memories = []*MemoryNode{} // Return empty array not null
	}
	
	// Convert to JSON-serializable format
	result := make([]map[string]interface{}, 0, len(memories))
	for _, node := range memories {
		memory := map[string]interface{}{
			"key":       node.Key,
			"value":     node.Value,
			"hash":      node.Hash,
			"timestamp": node.Timestamp,
		}
		result = append(result, memory)
	}
	
	// Return memories
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"agent_id":  agentID,
		"memories":  result,
		"count":     len(result),
		"timestamp": time.Now().Unix(),
	})
}

// handleSnapshotMemory creates a memory snapshot for an agent
func (s *MCPServer) handleSnapshotMemory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract parameters
	agentID := r.URL.Query().Get("agent_id")
	
	if agentID == "" {
		http.Error(w, "Missing required parameter: agent_id", http.StatusBadRequest)
		return
	}
	
	// Ensure agent memory exists
	s.dbService.initializeAgentMemory(agentID)
	
	// Generate snapshot ID
	snapshotID := generateSnapshotID(agentID)
	
	// Persist current memory state to MongoDB
	if s.dbService.mongoConnector != nil {
		// Get the memory tree
		s.dbService.mu.RLock()
		tree := s.dbService.agentMemory[agentID]
		s.dbService.mu.RUnlock()
		
		// Persist the tree
		err := s.dbService.mongoConnector.PersistMemoryTree(agentID, tree)
		if err != nil {
			log.Printf("Failed to create memory snapshot for agent %s: %v", agentID, err)
			http.Error(w, "Failed to create memory snapshot", http.StatusInternalServerError)
			return
		}
	}
	
	// Publish snapshot event
	s.eventBus.Publish(&Event{
		Type:   EventAgentSnapshotCreated,
		Source: "db-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id":    agentID,
			"snapshot_id": snapshotID,
			"timestamp":   time.Now().Unix(),
			"node_count":  s.dbService.getNodeCount(agentID),
		},
	})
	
	// Return snapshot ID
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"agent_id":    agentID,
		"snapshot_id": snapshotID,
		"timestamp":   time.Now().Unix(),
		"status":      "success",
	})
}

// handleCompactMemory optimizes memory usage for hardware constraints
func (s *MCPServer) handleCompactMemory(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract parameters
	agentID := r.URL.Query().Get("agent_id")
	
	if agentID == "" {
		http.Error(w, "Missing required parameter: agent_id", http.StatusBadRequest)
		return
	}
	
	// Perform memory compaction to stay within hardware limits
	nodesBefore := s.dbService.getNodeCount(agentID)
	
	// In production, this would do actual tree balancing and optimization
	s.dbService.optimizeMemoryTree(agentID)
	
	// If MongoDB connector is available, compact in the database too
	if s.dbService.mongoConnector != nil {
		err := s.dbService.mongoConnector.CompactMemoryTree(agentID)
		if err != nil {
			log.Printf("Warning: Failed to compact MongoDB memory for agent %s: %v", agentID, err)
		}
	}
	
	nodesAfter := s.dbService.getNodeCount(agentID)
	
	// Return compaction results
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]interface{}{
		"agent_id":      agentID,
		"nodes_before":  nodesBefore,
		"nodes_after":   nodesAfter,
		"optimization":  nodesBefore - nodesAfter,
		"timestamp":     time.Now().Unix(),
		"ram_estimate":  (nodesAfter * 256) / (1024 * 1024), // Rough MB estimate
		"status":        "success",
	})
}

// Helper function

// generateSnapshotID creates a unique snapshot ID
func generateSnapshotID(agentID string) string {
	return "snap-" + agentID[:4] + "-" + time.Now().Format("20060102-150405")
}
