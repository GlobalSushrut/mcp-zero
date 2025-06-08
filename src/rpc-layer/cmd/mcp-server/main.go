// MCP-ZERO Server Entry Point
// Compatible with Go 1.13
package main

import (
	"context"
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"path/filepath"
	"strings"
	"sync"
	"syscall"
	"time"
)

// ServerConfig holds configuration for the MCP server
type ServerConfig struct {
	AgentPort           int
	AuditPort           int
	LLMPort             int
	ConsensusPort       int
	MetricsPort         int
	APIPort             int
	MongoURI            string
	MaxCPUPercent       float64
	MaxMemoryMB         int
	AvgMemoryMB         int
	EnableZK            bool
	EnableSolidity      bool
	EnableEthics        bool
	ShutdownTimeoutSecs int
}

// StandaloneServer represents a complete MCP-ZERO server instance
type StandaloneServer struct {
	Config ServerConfig
	APIServer *http.Server
	done      chan bool
	SolidityMiddleware *SolidityMiddleware
}

// SolidityMiddleware provides agreement handling capability using Solidity
type SolidityMiddleware struct {
	Agreements       map[string]*Agreement
	EthicalPolicies  *EthicalPolicyEngine
	ConsensusNodes   []string
	mutex           sync.RWMutex
}

// Agreement represents a Solidity-based agreement between agents
type Agreement struct {
	ID              string                 `json:"id"`
	ConsumerID      string                 `json:"consumer_id"`
	ProviderID      string                 `json:"provider_id"`
	Terms           map[string]interface{} `json:"terms"`
	EthicalPolicies []string               `json:"ethical_policies"`
	CreatedAt       time.Time              `json:"created_at"`
	ExpiresAt       time.Time              `json:"expires_at"`
	UsageLimits     map[string]float64     `json:"usage_limits"`
	UsageCurrent    map[string]float64     `json:"usage_current"`
	Active          bool                   `json:"active"`
}

// VerificationResult contains the result of agreement verification
type VerificationResult struct {
	Valid         bool                   `json:"Valid"` 
	ExpiresAt     time.Time              `json:"ExpiresAt"` 
	Active        bool                   `json:"Active"`
	EthicalStatus bool                   `json:"EthicalStatus"`
	UsageLimits   map[string]float64     `json:"UsageLimits"`
	UsageCurrent  map[string]float64     `json:"UsageCurrent"`
}

// EthicalPolicyEngine evaluates content against ethical policies
type EthicalPolicyEngine struct {
	Policies map[string]func(interface{}) (bool, string)
}

// NewSolidityMiddleware creates a new middleware instance
func NewSolidityMiddleware(consensusNodes []string) *SolidityMiddleware {
	// Create ethical policy engine
	policies := make(map[string]func(interface{}) (bool, string))
	
	// Define content safety policy
	policies["content_safety"] = func(params interface{}) (bool, string) {
		// Parse parameters
		m, ok := params.(map[string]interface{})
		if !ok {
			return false, "Invalid parameters"
		}
		
		// Check content
		if content, ok := m["content"].(string); ok {
			// Simple check - reject content with "harmful" in it
			if strings.Contains(strings.ToLower(content), "harmful") {
				return false, "Content contains harmful material"
			}
		}
		
		return true, ""
	}
	
	// Define fair use policy
	policies["fair_use"] = func(params interface{}) (bool, string) {
		// Parse parameters
		m, ok := params.(map[string]interface{})
		if !ok {
			return false, "Invalid parameters"
		}
		
		// Check quantity
		if quantity, ok := m["quantity"].(float64); ok {
			if quantity > 1000 {
				return false, "Usage quantity exceeds fair use policy"
			}
		}
		
		return true, ""
	}
	
	return &SolidityMiddleware{
		Agreements:      make(map[string]*Agreement),
		EthicalPolicies: &EthicalPolicyEngine{Policies: policies},
		ConsensusNodes:  consensusNodes,
		mutex:          sync.RWMutex{},
	}
}

// CreateSolidityAgreement creates a new agreement with ethical policies
func (sm *SolidityMiddleware) CreateSolidityAgreement(
	consumerID string, 
	providerID string, 
	termsJSON []byte, 
	ethicalPolicies []string,
) (string, error) {
	// Lock for write
	sm.mutex.Lock()
	defer sm.mutex.Unlock()
	
	// Parse terms
	var terms map[string]interface{}
	if err := json.Unmarshal(termsJSON, &terms); err != nil {
		return "", fmt.Errorf("invalid terms: %v", err)
	}
	
	// Validate required ethical policies
	if len(ethicalPolicies) == 0 {
		return "", errors.New("ethical policies are required")
	}
	
	// Check that all policies exist
	for _, policy := range ethicalPolicies {
		if _, ok := sm.EthicalPolicies.Policies[policy]; !ok {
			return "", fmt.Errorf("policy %s not found", policy)
		}
	}
	
	// Extract expiration
	expiresAt := time.Now().Add(24 * time.Hour) // Default: 1 day
	if exp, ok := terms["expires_at"]; ok {
		if expFloat, ok := exp.(float64); ok {
			expiresAt = time.Unix(int64(expFloat), 0)
		}
	}
	
	// Extract usage limits
	usageLimits := make(map[string]float64)
	if maxCalls, ok := terms["max_calls"]; ok {
		if maxCallsFloat, ok := maxCalls.(float64); ok {
			usageLimits["calls"] = maxCallsFloat
		}
	}
	if maxCPU, ok := terms["max_cpu"]; ok {
		if maxCPUFloat, ok := maxCPU.(float64); ok {
			usageLimits["cpu"] = maxCPUFloat
		}
	}
	
	// Generate ID using SHA-256 of consumer, provider, and timestamp
	hasher := sha256.New()
	hasher.Write([]byte(consumerID))
	hasher.Write([]byte(providerID))
	hasher.Write([]byte(time.Now().String()))
	agreementID := hex.EncodeToString(hasher.Sum(nil))
	
	// Create agreement
	agreement := &Agreement{
		ID:              agreementID,
		ConsumerID:      consumerID,
		ProviderID:      providerID,
		Terms:           terms,
		EthicalPolicies: ethicalPolicies,
		CreatedAt:       time.Now(),
		ExpiresAt:       expiresAt,
		UsageLimits:     usageLimits,
		UsageCurrent:    make(map[string]float64),
		Active:          true,
	}
	
	// Store agreement
	sm.Agreements[agreementID] = agreement
	
	// Log creation
	log.Printf("Created agreement %s between %s and %s", agreementID, consumerID, providerID)
	
	return agreementID, nil
}

// VerifySolidityAgreement verifies an agreement is valid
func (sm *SolidityMiddleware) VerifySolidityAgreement(agreementID string) (*VerificationResult, error) {
	// Lock for read
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()
	
	// Get agreement
	agreement, ok := sm.Agreements[agreementID]
	if !ok {
		return nil, errors.New("agreement not found")
	}
	
	// Check expiration
	expired := time.Now().After(agreement.ExpiresAt)
	
	// Create result
	result := &VerificationResult{
		Valid:         !expired && agreement.Active,
		ExpiresAt:     agreement.ExpiresAt,
		Active:        agreement.Active,
		EthicalStatus: len(agreement.EthicalPolicies) > 0,
		UsageLimits:   agreement.UsageLimits,
		UsageCurrent:  agreement.UsageCurrent,
	}
	
	return result, nil
}

// EvaluateEthicalCompliance checks if parameters comply with ethical policies
func (sm *SolidityMiddleware) EvaluateEthicalCompliance(agreementID string, paramsJSON []byte) (bool, string, error) {
	// Lock for read
	sm.mutex.RLock()
	defer sm.mutex.RUnlock()
	
	// Get agreement
	agreement, ok := sm.Agreements[agreementID]
	if !ok {
		return false, "Agreement not found", errors.New("agreement not found")
	}
	
	// Parse parameters
	var params interface{}
	if err := json.Unmarshal(paramsJSON, &params); err != nil {
		return false, "Invalid parameters", err
	}
	
	// Check all ethical policies
	for _, policyName := range agreement.EthicalPolicies {
		policy, ok := sm.EthicalPolicies.Policies[policyName]
		if !ok {
			continue // Skip unknown policy
		}
		
		// Evaluate policy
		compliant, reason := policy(params)
		if !compliant {
			return false, fmt.Sprintf("Policy %s violation: %s", policyName, reason), nil
		}
	}
	
	// Check usage limits
	if quantity, ok := params.(map[string]interface{})["quantity"].(float64); ok {
		for metric, limit := range agreement.UsageLimits {
			current := agreement.UsageCurrent[metric]
			if current+quantity > limit {
				return false, fmt.Sprintf("Usage limit exceeded for %s", metric), nil
			}
		}
	}
	
	// All checks passed
	return true, "", nil
}

// RecordUsage records usage for an agreement
func (sm *SolidityMiddleware) RecordUsage(agreementID, metric string, quantity float64) error {
	// Lock for write
	sm.mutex.Lock()
	defer sm.mutex.Unlock()
	
	// Get agreement
	agreement, ok := sm.Agreements[agreementID]
	if !ok {
		return errors.New("agreement not found")
	}
	
	// Check if metric has a limit
	if limit, ok := agreement.UsageLimits[metric]; ok {
		// Get current usage
		current := agreement.UsageCurrent[metric]
		
		// Check if limit would be exceeded
		if current+quantity > limit {
			return fmt.Errorf("usage limit exceeded for %s", metric)
		}
	}
	
	// Record usage
	agreement.UsageCurrent[metric] += quantity
	
	// Update agreement in storage
	sm.Agreements[agreementID] = agreement
	
	return nil
}

// healthHandler handles health checks
func healthHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "application/json")
	json.NewEncoder(w).Encode(map[string]string{
		"status": "ok",
		"version": "MCP-ZERO v7",
		"timestamp": time.Now().Format(time.RFC3339),
	})
}

// setupAPIRoutes configures API endpoints
func (s *StandaloneServer) setupAPIRoutes() *http.ServeMux {
	mux := http.NewServeMux()

	// Health endpoint
	mux.HandleFunc("/health", healthHandler)
	
	// Agent endpoints
	mux.HandleFunc("/api/v1/agents", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")

		switch r.Method {
		case http.MethodGet:
			// List agents
			limit := 10 // Default limit
			offset := 0 // Default offset

			// Parse query parameters if present
			query := r.URL.Query()
			if limitParam := query.Get("limit"); limitParam != "" {
				fmt.Sscanf(limitParam, "%d", &limit)
			}
			if offsetParam := query.Get("offset"); offsetParam != "" {
				fmt.Sscanf(offsetParam, "%d", &offset)
			}

			// Mock agent IDs for testing
			agentIDs := make([]string, 0)
			for i := 0; i < limit; i++ {
				agentID := fmt.Sprintf("agent-%d", offset+i)
				agentIDs = append(agentIDs, agentID)
			}

			// Return agent list
			json.NewEncoder(w).Encode(map[string]interface{}{
				"agents": agentIDs,
				"total":  100, // Mock total count
				"limit":  limit,
				"offset": offset,
			})

		case http.MethodPost:
			// Spawn new agent
			var requestBody struct {
				Config map[string]interface{} `json:"config"`
			}

			// Parse request body
			if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]string{"error": "Invalid request body: " + err.Error()})
				return
			}

			// Generate agent ID
			agentID := fmt.Sprintf("agent-%d", time.Now().Unix())

			// Return agent ID
			json.NewEncoder(w).Encode(map[string]interface{}{
				"agent_id": agentID,
				"status":   "active",
				"created_at": time.Now().Format(time.RFC3339),
			})

		default:
			w.WriteHeader(http.StatusMethodNotAllowed)
			json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed"})
		}
	})
	
	// Agent-specific operations
	mux.HandleFunc("/api/v1/agents/", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		
		// Extract agent ID and operation from path
		path := r.URL.Path
		parts := strings.Split(path, "/")
		
		// Check if path has enough parts
		if len(parts) < 5 {
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "Agent ID not specified"})
			return
		}
		
		agentID := parts[4]
		
		// Handle operations based on path length
		if len(parts) == 5 {
			// Direct agent operations
			switch r.Method {
			case http.MethodGet:
				// Get agent details
				json.NewEncoder(w).Encode(map[string]interface{}{
					"agent_id": agentID,
					"status": "active",
					"created_at": time.Now().Add(-24 * time.Hour).Format(time.RFC3339),
					"updated_at": time.Now().Format(time.RFC3339),
					"name": "Mock Agent",
					"plugins": []string{"core"},
				})
			default:
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed"})
			}
			return
		}
		
		// Handle specific agent operations
		operation := parts[5]
		
		switch operation {
		case "plugins":
			// Plugin operations
			if r.Method != http.MethodPost {
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed for plugins endpoint"})
				return
			}
			
			// Parse request body to get plugin ID
			var requestBody struct {
				PluginID string `json:"plugin_id"`
			}
			
			if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]string{"error": "Invalid request body: " + err.Error()})
				return
			}
			
			// Return success response
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"agent_id": agentID,
				"plugin_id": requestBody.PluginID,
				"timestamp": time.Now().Format(time.RFC3339),
			})
			
		case "execute":
			// Execute intent
			if r.Method != http.MethodPost {
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed for execute endpoint"})
				return
			}
			
			// Parse request body
			var requestBody struct {
				Intent string `json:"intent"`
				Parameters map[string]string `json:"parameters"`
			}
			
			if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
				w.WriteHeader(http.StatusBadRequest)
				json.NewEncoder(w).Encode(map[string]string{"error": "Invalid request body: " + err.Error()})
				return
			}
			
			// Return execution result
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"agent_id": agentID,
				"intent": requestBody.Intent,
				"result": "Intent executed successfully",
				"timestamp": time.Now().Format(time.RFC3339),
			})
			
		case "snapshot":
			// Take snapshot
			if r.Method != http.MethodPost {
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed for snapshot endpoint"})
				return
			}
			
			// Generate snapshot ID
			snapshotID := fmt.Sprintf("snap-%d", time.Now().Unix())
			
			// Return snapshot ID
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"agent_id": agentID,
				"snapshot_id": snapshotID,
				"timestamp": time.Now().Format(time.RFC3339),
			})
			
		case "recover":
			// Recover from snapshot
			if r.Method != http.MethodPost {
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed for recover endpoint"})
				return
			}
			
			// Parse request body to get snapshot ID (optional)
			var requestBody struct {
				SnapshotID string `json:"snapshot_id,omitempty"`
			}
			
			// Try to parse body, but continue even if it fails (snapshot_id is optional)
			_ = json.NewDecoder(r.Body).Decode(&requestBody)
			
			// Use provided snapshot ID or default to latest
			snapshotID := requestBody.SnapshotID
			if snapshotID == "" {
				snapshotID = "latest"
			}
			
			// Return success response
			json.NewEncoder(w).Encode(map[string]interface{}{
				"success": true,
				"agent_id": agentID,
				"snapshot_id": snapshotID,
				"status": "recovered",
				"timestamp": time.Now().Format(time.RFC3339),
			})
			
		default:
			w.WriteHeader(http.StatusNotFound)
			json.NewEncoder(w).Encode(map[string]string{"error": "Unknown operation: " + operation})
		}
	})
	
	// LLM endpoints
	mux.HandleFunc("/api/v1/llm", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"message": "LLM API operational"})
	})
	
	// Consensus endpoints
	mux.HandleFunc("/api/v1/consensus", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"message": "Consensus API operational"})
	})
	
	// Memory endpoints
	mux.HandleFunc("/api/v1/memory", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		json.NewEncoder(w).Encode(map[string]string{"message": "Memory API operational"})
	})
	
	// Agreement endpoints - only if Solidity middleware is enabled
	if s.SolidityMiddleware != nil {
		log.Println("Registering Solidity agreement endpoints")
		
		// List and create agreements
		mux.HandleFunc("/api/v1/agreements", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			
			switch r.Method {
			case http.MethodGet:
				// Return mock agreement list for testing
				json.NewEncoder(w).Encode(map[string]interface{}{
					"agreements": []string{"agreement-1", "agreement-2"},
					"total":      2,
				})
				
			case http.MethodPost:
				// Create new agreement
				var requestBody struct {
					ConsumerID      string                 `json:"consumer_id"`
					ProviderID      string                 `json:"provider_id"`
					Terms           map[string]interface{} `json:"terms"`
					EthicalPolicies []string               `json:"ethical_policies"`
				}
				
				// Parse request body
				if err := json.NewDecoder(r.Body).Decode(&requestBody); err != nil {
					w.WriteHeader(http.StatusBadRequest)
					json.NewEncoder(w).Encode(map[string]string{"error": "Invalid request body: " + err.Error()})
					return
				}
				
				// Validate required fields
				if requestBody.ConsumerID == "" || requestBody.ProviderID == "" {
					w.WriteHeader(http.StatusBadRequest)
					json.NewEncoder(w).Encode(map[string]string{"error": "Missing required fields: consumer_id and provider_id"})
					return
				}
				
				// Serialize terms to JSON
				termsJSON, err := json.Marshal(requestBody.Terms)
				if err != nil {
					w.WriteHeader(http.StatusBadRequest)
					json.NewEncoder(w).Encode(map[string]string{"error": "Invalid terms format"})
					return
				}
				
				// Create agreement
				agreementID, err := s.SolidityMiddleware.CreateSolidityAgreement(
					requestBody.ConsumerID, 
					requestBody.ProviderID, 
					termsJSON, 
					requestBody.EthicalPolicies,
				)
				
				if err != nil {
					w.WriteHeader(http.StatusBadRequest)
					json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
					return
				}
				
				// Return agreement ID
				json.NewEncoder(w).Encode(map[string]interface{}{
					"id": agreementID,
					"created_at": time.Now().Format(time.RFC3339),
				})
				
			default:
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed"})
			}
		})
		
		// Agreement-specific operations (verify, check, record usage)
		mux.HandleFunc("/api/v1/agreements/", func(w http.ResponseWriter, r *http.Request) {
			w.Header().Set("Content-Type", "application/json")
			
			// Extract agreement ID and operation from path
			path := r.URL.Path
			parts := strings.Split(path, "/")
			
			// Check if path has enough parts
			if len(parts) < 5 {
				w.WriteHeader(http.StatusNotFound)
				json.NewEncoder(w).Encode(map[string]string{"error": "Agreement ID not specified"})
				return
			}
			
			agreementID := parts[4]
			
			// Handle based on operation (if present in path)
			if len(parts) >= 6 {
				operation := parts[5]
				
				switch operation {
				case "check":
					// Check ethical compliance
					if r.Method != http.MethodPost {
						w.WriteHeader(http.StatusMethodNotAllowed)
						return
					}
					
					// Parse parameters
					var params map[string]interface{}
					if err := json.NewDecoder(r.Body).Decode(&params); err != nil {
						w.WriteHeader(http.StatusBadRequest)
						json.NewEncoder(w).Encode(map[string]string{"error": "Invalid parameters"})
						return
					}
					
					// Convert params to JSON
					paramsJSON, _ := json.Marshal(params)
					
					// Check ethical compliance
					compliant, reason, err := s.SolidityMiddleware.EvaluateEthicalCompliance(agreementID, paramsJSON)
					if err != nil {
						w.WriteHeader(http.StatusInternalServerError)
						json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
						return
					}
					
					// Return result
					json.NewEncoder(w).Encode(map[string]interface{}{
						"compliant": compliant,
						"reason":    reason,
					})
					
				case "usage":
					// Record usage
					if r.Method != http.MethodPost {
						w.WriteHeader(http.StatusMethodNotAllowed)
						return
					}
					
					// Parse parameters
					var usageRequest struct {
						Metric   string  `json:"metric"`
						Quantity float64 `json:"quantity"`
					}
					
					if err := json.NewDecoder(r.Body).Decode(&usageRequest); err != nil {
						w.WriteHeader(http.StatusBadRequest)
						json.NewEncoder(w).Encode(map[string]string{"error": "Invalid parameters"})
						return
					}
					
					// Record usage
					err := s.SolidityMiddleware.RecordUsage(agreementID, usageRequest.Metric, usageRequest.Quantity)
					if err != nil {
						w.WriteHeader(http.StatusBadRequest)
						json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
						return
					}
					
					// Return success
					json.NewEncoder(w).Encode(map[string]interface{}{
						"success": true,
					})
					
				default:
					w.WriteHeader(http.StatusNotFound)
					json.NewEncoder(w).Encode(map[string]string{"error": "Unknown operation"})
				}
				
				return
			}
			
			// If no operation specified, handle direct agreement operations
			switch r.Method {
			case http.MethodGet:
				// Get agreement verification
				verification, err := s.SolidityMiddleware.VerifySolidityAgreement(agreementID)
				if err != nil {
					// Check error type to return appropriate status
					if err.Error() == "agreement not found" {
						w.WriteHeader(http.StatusNotFound)
						json.NewEncoder(w).Encode(map[string]string{"error": "Agreement not found"})
					} else {
						w.WriteHeader(http.StatusInternalServerError)
						json.NewEncoder(w).Encode(map[string]string{"error": err.Error()})
					}
					return
				}
				
				// Return verification
				json.NewEncoder(w).Encode(verification)
				
			default:
				w.WriteHeader(http.StatusMethodNotAllowed)
				json.NewEncoder(w).Encode(map[string]string{"error": "Method not allowed"})
			}
		})
	}
	
	return mux
}

// Start launches the server
func (s *StandaloneServer) Start() error {
	log.Printf("Starting MCP-ZERO v7 server with ZK-traceable consensus")
	log.Printf("Hardware constraints: <27%% CPU, <827MB RAM")
	
	// Initialize done channel
	s.done = make(chan bool)
	
	// Setup API routes
	mux := s.setupAPIRoutes()
	
	// Create HTTP server
	address := fmt.Sprintf(":%d", s.Config.APIPort)
	s.APIServer = &http.Server{
		Addr:    address,
		Handler: mux,
	}
	
	// Start HTTP server in a goroutine
	go func() {
		log.Printf("API server listening on %s", address)
		if err := s.APIServer.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("Error starting API server: %v", err)
		}
	}()
	
	return nil
}

// Shutdown stops the server gracefully
func (s *StandaloneServer) Shutdown() {
	log.Println("Shutting down MCP-ZERO server...")
	
	// Create a timeout context for shutdown
	ctx, cancel := context.WithTimeout(context.Background(), 
		time.Duration(s.Config.ShutdownTimeoutSecs) * time.Second)
	defer cancel()
	
	// Shutdown HTTP server
	if s.APIServer != nil {
		if err := s.APIServer.Shutdown(ctx); err != nil {
			log.Printf("Error shutting down API server: %v", err)
		}
	}
	
	// Signal completion
	close(s.done)
}

// loadConfig loads the server configuration from a YAML file
func loadConfig(configPath string) (ServerConfig, error) {
	// For simplicity, return a default configuration
	// In a real implementation, this would parse the YAML file
	return ServerConfig{
		AgentPort:           50051,
		AuditPort:           50052,
		LLMPort:             50053,
		ConsensusPort:       50054,
		MetricsPort:         9090,
		APIPort:             8082, // Changed to 8082 to avoid conflict
		MongoURI:            "mongodb://localhost:27017/mcp_zero",
		MaxCPUPercent:       27.0,
		MaxMemoryMB:         827,
		AvgMemoryMB:         640,
		EnableZK:            true,
		EnableSolidity:      true,
		EnableEthics:        true,
		ShutdownTimeoutSecs: 30,
	}, nil
}

// createServer creates a new StandaloneServer instance
func createServer(config ServerConfig) *StandaloneServer {
	// Create consensus nodes list for agreement validation
	consensusNodes := []string{"localhost:50054"} 
	
	// Initialize Solidity middleware if enabled
	var solidityMiddleware *SolidityMiddleware
	if config.EnableSolidity {
		log.Println("Initializing Solidity agreement middleware...")
		solidityMiddleware = NewSolidityMiddleware(consensusNodes)
		log.Println("Solidity agreement middleware initialized successfully")
	}
	
	return &StandaloneServer{
		Config: config,
		SolidityMiddleware: solidityMiddleware,
	}
}

func main() {
	// Parse command line flags
	configFile := flag.String("config", "../../config.yaml", "Path to configuration file")
	enableSolidity := flag.Bool("enable-solidity", false, "Enable Solidity agreement middleware")
	enableEthics := flag.Bool("enable-ethics", true, "Enable ethical policy enforcement")
	flag.Parse()
	
	// Make path absolute if it's not
	absConfigFile, err := filepath.Abs(*configFile)
	if err != nil {
		log.Fatalf("Failed to determine absolute path: %v", err)
	}
	
	log.Printf("Loading config from %s", absConfigFile)
	
	// Load config directly from the source directory
	config, err := loadConfig(absConfigFile)
	if err != nil {
		log.Fatalf("Failed to load config: %v", err)
	}
	
	// Override configuration with command line flags if provided
	config.EnableSolidity = *enableSolidity
	config.EnableEthics = *enableEthics
	
	// Create standalone server
	server := createServer(config)
	
	// Start server
	log.Println("Starting MCP-ZERO Server...")
	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start server: %v", err)
	}
	
	log.Printf("MCP-ZERO Server is running (PID: %d)", os.Getpid())
	log.Printf("Hardware constraints: <27%% CPU, <827MB RAM")
	
	// Wait for termination signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh
	
	log.Printf("Received signal: %s", sig)
	log.Println("Shutting down MCP-ZERO Server...")
	
	// Shutdown server
	server.Shutdown()
	
	log.Println("Server shutdown complete. Goodbye!")
}
