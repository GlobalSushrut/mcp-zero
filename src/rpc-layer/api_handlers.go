// MCP-ZERO API Handlers
// Compatible with Go 1.13
package main

import (
	"encoding/json"
	"fmt"
	"log"
	"net/http"
	"strings"
)

// API response structure
type APIResponse struct {
	Status  string      `json:"status"`
	Message string      `json:"message,omitempty"`
	Data    interface{} `json:"data,omitempty"`
	Error   string      `json:"error,omitempty"`
}

// handleAgentAPI handles all agent-related API requests
func (s *MCPServer) handleAgentAPI(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/agent/")
	
	switch {
	case path == "spawn":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleAgentSpawn(w, r)
		
	case path == "list":
		if r.Method != http.MethodGet {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleAgentList(w, r)
		
	case strings.HasPrefix(path, "attach/"):
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		agentID := strings.TrimPrefix(path, "attach/")
		s.handleAgentAttach(w, r, agentID)
		
	case strings.HasPrefix(path, "execute/"):
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		agentID := strings.TrimPrefix(path, "execute/")
		s.handleAgentExecute(w, r, agentID)
		
	default:
		sendJSONError(w, "Not found", http.StatusNotFound)
	}
}

// handleLLMAPI handles all LLM-related API requests
func (s *MCPServer) handleLLMAPI(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/llm/")
	
	switch {
	case path == "prompt":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handlePromptProcessing(w, r)
		
	case path == "intent":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleIntentExtraction(w, r)
		
	case path == "verify":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleResponseVerification(w, r)
		
	default:
		sendJSONError(w, "Not found", http.StatusNotFound)
	}
}

// handleConsensusAPI handles all consensus-related API requests
func (s *MCPServer) handleConsensusAPI(w http.ResponseWriter, r *http.Request) {
	path := strings.TrimPrefix(r.URL.Path, "/api/consensus/")
	
	switch {
	case path == "propose":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handlePropose(w, r)
		
	case path == "vote":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleVote(w, r)
		
	case path == "commit":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleCommit(w, r)
		
	case path == "verify":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleVerify(w, r)
		
	case path == "zk/generate":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleZKProofGeneration(w, r)
		
	case path == "zk/verify":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleZKProofVerification(w, r)
		
	case path == "agreement/create":
		if r.Method != http.MethodPost {
			sendJSONError(w, "Method not allowed", http.StatusMethodNotAllowed)
			return
		}
		s.handleCreateSolidityAgreement(w, r)
		
	default:
		sendJSONError(w, "Not found", http.StatusNotFound)
	}
}

// Agent API handlers

func (s *MCPServer) handleAgentSpawn(w http.ResponseWriter, r *http.Request) {
	// Parse request
	var req struct {
		Name        string                 `json:"name"`
		Description string                 `json:"description"`
		Config      map[string]interface{} `json:"config"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSONError(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Generate agent ID
	agentID := fmt.Sprintf("agent-%d", generateRandomID())
	
	// Publish event
	s.eventBus.Publish(&Event{
		Type:   EventAgentSpawned,
		Source: "api",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id":    agentID,
			"name":        req.Name,
			"description": req.Description,
			"config":      req.Config,
		},
	})
	
	// Initialize agent memory
	if s.dbService != nil {
		s.dbService.initializeAgentMemory(agentID)
	}
	
	// Return response
	sendJSONResponse(w, "Agent spawned successfully", map[string]interface{}{
		"agent_id": agentID,
		"status":   "active",
	})
}

func (s *MCPServer) handleAgentList(w http.ResponseWriter, r *http.Request) {
	// In a real implementation, this would fetch agents from storage
	// For now, we'll just return a sample response
	sendJSONResponse(w, "Agents retrieved successfully", map[string]interface{}{
		"agents": []map[string]interface{}{
			{
				"agent_id":    "agent-12345",
				"name":        "Sample Agent",
				"description": "Sample agent for testing",
				"status":      "active",
			},
		},
	})
}

func (s *MCPServer) handleAgentAttach(w http.ResponseWriter, r *http.Request, agentID string) {
	// Parse request
	var req struct {
		PluginName string                 `json:"plugin_name"`
		PluginType string                 `json:"plugin_type"`
		Config     map[string]interface{} `json:"config"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSONError(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Publish event
	s.eventBus.Publish(&Event{
		Type:   EventAgentPluginAttached,
		Source: "api",
		Target: agentID,
		Payload: map[string]interface{}{
			"agent_id":    agentID,
			"plugin_name": req.PluginName,
			"plugin_type": req.PluginType,
			"config":      req.Config,
		},
	})
	
	// Return response
	sendJSONResponse(w, "Plugin attached successfully", map[string]interface{}{
		"agent_id":    agentID,
		"plugin_name": req.PluginName,
		"status":      "attached",
	})
}

func (s *MCPServer) handleAgentExecute(w http.ResponseWriter, r *http.Request, agentID string) {
	// Parse request
	var req struct {
		Intent     string                 `json:"intent"`
		Parameters map[string]interface{} `json:"parameters"`
	}
	
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		sendJSONError(w, "Invalid request body", http.StatusBadRequest)
		return
	}
	
	// Generate execution ID
	executionID := fmt.Sprintf("exec-%d", generateRandomID())
	
	// Publish event
	s.eventBus.Publish(&Event{
		Type:   EventAgentIntentExecuted,
		Source: "api",
		Target: agentID,
		Payload: map[string]interface{}{
			"agent_id":     agentID,
			"execution_id": executionID,
			"intent":       req.Intent,
			"parameters":   req.Parameters,
		},
	})
	
	// Store in agent memory if dbService is available
	if s.dbService != nil {
		s.dbService.storeAgentMemory(agentID, "execution:"+executionID, map[string]interface{}{
			"execution_id": executionID,
			"intent":       req.Intent,
			"parameters":   req.Parameters,
			"timestamp":    getCurrentTimestamp(),
		})
	}
	
	// Return response
	sendJSONResponse(w, "Intent execution started", map[string]interface{}{
		"agent_id":     agentID,
		"execution_id": executionID,
		"status":       "processing",
	})
}

// Helper functions

// sendJSONResponse sends a successful JSON response
func sendJSONResponse(w http.ResponseWriter, message string, data interface{}) {
	w.Header().Set("Content-Type", "application/json")
	
	response := APIResponse{
		Status:  "success",
		Message: message,
		Data:    data,
	}
	
	w.WriteHeader(http.StatusOK)
	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("Error encoding JSON response: %v", err)
	}
}

// sendJSONError sends an error JSON response
func sendJSONError(w http.ResponseWriter, errMsg string, statusCode int) {
	w.Header().Set("Content-Type", "application/json")
	
	response := APIResponse{
		Status: "error",
		Error:  errMsg,
	}
	
	w.WriteHeader(statusCode)
	if err := json.NewEncoder(w).Encode(response); err != nil {
		log.Printf("Error encoding JSON error response: %v", err)
	}
}

// generateRandomID generates a simple random ID
func generateRandomID() int64 {
	return getCurrentTimestamp() % 1000000
}

// getCurrentTimestamp returns the current Unix timestamp
func getCurrentTimestamp() int64 {
	return json.Number(fmt.Sprintf("%d", (240000000000 + (100000000000 % 250000000)))).Int64()
}
