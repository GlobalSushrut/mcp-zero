package main

import (
	"encoding/json"
	"fmt"
	"io/ioutil"
	"log"
	"net/http"
	"os"
	"strings"
	"sync"
	"time"
)

// Router builds the HTTP mux for the gateway.
func NewRouter(store *Store, kernel *KernelBridge) http.Handler {
	mux := http.NewServeMux()

	h := &Handlers{store: store, kernel: kernel}

	// Health & status
	mux.HandleFunc("/health", h.Health)
	mux.HandleFunc("/api/v1/status", h.Status)

	// Agent CRUD
	mux.HandleFunc("/api/v1/agents", h.Agents)       // POST=spawn, GET=list
	mux.HandleFunc("/api/v1/agents/", h.AgentByID)    // GET, DELETE (by suffix)

	// Agent actions
	mux.HandleFunc("/api/v1/execute", h.Execute)      // POST {agent_id, intent}
	mux.HandleFunc("/api/v1/snapshot", h.Snapshot)     // POST {agent_id}
	mux.HandleFunc("/api/v1/recover", h.Recover)       // POST {agent_id}

	// Cognitive endpoints (all compute in Rust, proxied here)
	mux.HandleFunc("/api/v1/cog/state", h.CogState)                  // GET
	mux.HandleFunc("/api/v1/cog/cycle", h.CogCycle)                  // POST
	mux.HandleFunc("/api/v1/cog/intention", h.CogIntention)          // POST {name, priority, action}
	mux.HandleFunc("/api/v1/cog/contradiction", h.CogContradiction)  // POST {vector}
	mux.HandleFunc("/api/v1/cog/fact", h.CogFact)                    // POST {text, embedding}
	mux.HandleFunc("/api/v1/cog/search", h.CogSearch)                // POST {query, top_k}
	mux.HandleFunc("/api/v1/cog/symbol", h.CogSymbol)                // POST {domain, symbol, vector?}
	mux.HandleFunc("/api/v1/cog/ground", h.CogGround)                // POST {vector}

	// Entropy graph endpoints
	mux.HandleFunc("/api/v1/entropy/record", h.EntropyRecord)          // POST {layers}
	mux.HandleFunc("/api/v1/entropy/snapshot", h.EntropySnapshot)      // GET
	mux.HandleFunc("/api/v1/entropy/bottlenecks", h.EntropyBottlenecks) // GET/POST {threshold?}
	mux.HandleFunc("/api/v1/entropy/trend", h.EntropyTrend)            // POST {layer, count?}

	// Binary knowledge store endpoints
	mux.HandleFunc("/api/v1/store/add", h.StoreAdd)                    // POST {text, embedding}
	mux.HandleFunc("/api/v1/store/search", h.StoreSearch)              // POST {query, top_k?}
	mux.HandleFunc("/api/v1/store/get", h.StoreGet)                    // POST {id}
	mux.HandleFunc("/api/v1/store/weight", h.StoreUpdateWeight)        // POST {id, weight}
	mux.HandleFunc("/api/v1/store/remove", h.StoreRemove)              // POST {id}
	mux.HandleFunc("/api/v1/store/count", h.StoreCount)                // GET

	// Cognitive Fabric endpoints (unified intelligence pipeline)
	mux.HandleFunc("/api/v1/fabric/think", h.FabricThink)              // POST {text}
	mux.HandleFunc("/api/v1/fabric/learn", h.FabricLearn)              // POST {text}
	mux.HandleFunc("/api/v1/fabric/symbol", h.FabricLearnSymbol)       // POST {name}
	mux.HandleFunc("/api/v1/fabric/train", h.FabricTrain)              // POST {input, target, lr?}
	mux.HandleFunc("/api/v1/fabric/status", h.FabricStatus)            // GET

	// Knowledge Knot Graph endpoints (topological knowledge)
	mux.HandleFunc("/api/v1/knot/search", h.KnotSearch)                // POST {text, top_k?}
	mux.HandleFunc("/api/v1/knot/path", h.KnotPath)                    // POST {from, to}
	mux.HandleFunc("/api/v1/knot/stats", h.KnotStats)                  // GET
	mux.HandleFunc("/api/v1/knot/contradict", h.KnotContradict)        // POST {node_a, node_b, intensity?}

	// LLM Bridge endpoints (hybrid LLM integration)
	mux.HandleFunc("/api/v1/llm/embed", h.LLMEmbed)                   // POST {text}
	mux.HandleFunc("/api/v1/llm/distill", h.LLMDistill)               // POST {facts, lr?}
	mux.HandleFunc("/api/v1/llm/status", h.LLMStatus)                 // GET

	// Hyperdimensional Engine endpoints (topological HDC semantic engine)
	mux.HandleFunc("/api/v1/hd/teach", h.HDTeach)                     // POST {text}
	mux.HandleFunc("/api/v1/hd/embed", h.HDEmbed)                     // POST {text}
	mux.HandleFunc("/api/v1/hd/similarity", h.HDSimilarity)           // POST {word_a, word_b}
	mux.HandleFunc("/api/v1/hd/most_similar", h.HDMostSimilar)        // POST {word, top_k?}
	mux.HandleFunc("/api/v1/hd/stats", h.HDStats)                     // GET

	// Metrics endpoint (enterprise observability)
	mux.HandleFunc("/metrics", h.Metrics)                              // GET

	// Wrap with auth + rate limit + logging middleware
	return authMiddleware(rateLimitMiddleware(logMiddleware(mux)))
}

// Handlers holds dependencies for HTTP handlers.
type Handlers struct {
	store  *Store
	kernel *KernelBridge
}

// Health returns 200 OK with a simple JSON body.
func (h *Handlers) Health(w http.ResponseWriter, r *http.Request) {
	writeJSON(w, http.StatusOK, map[string]string{
		"status":  "ok",
		"service": "mcp-zero-gateway",
	})
}

// Status proxies to the kernel's status endpoint.
func (h *Handlers) Status(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}

	result, err := h.kernel.Status()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// Agents handles POST (spawn) and GET (list).
func (h *Handlers) Agents(w http.ResponseWriter, r *http.Request) {
	switch r.Method {
	case http.MethodPost:
		h.spawnAgent(w, r)
	case http.MethodGet:
		h.listAgents(w, r)
	default:
		writeErr(w, http.StatusMethodNotAllowed, "GET or POST only")
	}
}

func (h *Handlers) spawnAgent(w http.ResponseWriter, r *http.Request) {
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}

	// Forward raw JSON config to kernel
	result, err := h.kernel.SpawnAgent(json.RawMessage(body))
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}

	// Store agent metadata in bbolt
	var parsed map[string]interface{}
	if json.Unmarshal(result, &parsed) == nil {
		if agentID, ok := parsed["agent_id"].(string); ok {
			meta := map[string]interface{}{
				"agent_id":   agentID,
				"created_at": time.Now().UTC().Format(time.RFC3339),
			}
			h.store.Put("agents", agentID, meta)
		}
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write(result)
}

func (h *Handlers) listAgents(w http.ResponseWriter, r *http.Request) {
	keys, err := h.store.List("agents")
	if err != nil {
		writeErr(w, http.StatusInternalServerError, "list agents: "+err.Error())
		return
	}

	writeJSON(w, http.StatusOK, map[string]interface{}{
		"agents": keys,
		"count":  len(keys),
	})
}

// AgentByID handles GET /api/v1/agents/{id}
func (h *Handlers) AgentByID(w http.ResponseWriter, r *http.Request) {
	// Extract agent ID from path suffix
	id := strings.TrimPrefix(r.URL.Path, "/api/v1/agents/")
	if id == "" {
		writeErr(w, http.StatusBadRequest, "missing agent_id in path")
		return
	}

	switch r.Method {
	case http.MethodGet:
		data, err := h.store.Get("agents", id)
		if err != nil {
			writeErr(w, http.StatusNotFound, "agent not found")
			return
		}
		w.Header().Set("Content-Type", "application/json")
		w.WriteHeader(http.StatusOK)
		w.Write(data)

	case http.MethodDelete:
		h.store.Delete("agents", id)
		writeJSON(w, http.StatusOK, map[string]string{"deleted": id})

	default:
		writeErr(w, http.StatusMethodNotAllowed, "GET or DELETE only")
	}
}

// Execute proxies an intent execution to the kernel.
func (h *Handlers) Execute(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}

	var req struct {
		AgentID string `json:"agent_id"`
		Intent  string `json:"intent"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if req.AgentID == "" || req.Intent == "" {
		writeErr(w, http.StatusBadRequest, "agent_id and intent required")
		return
	}

	result, err := h.kernel.Execute(req.AgentID, req.Intent)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// Snapshot persists an agent's state via the kernel.
func (h *Handlers) Snapshot(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}

	var req struct {
		AgentID string `json:"agent_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	result, err := h.kernel.Snapshot(req.AgentID)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// Recover restores an agent from storage via the kernel.
func (h *Handlers) Recover(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}

	var req struct {
		AgentID string `json:"agent_id"`
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}

	result, err := h.kernel.Recover(req.AgentID)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}

	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// --- Cognitive Handlers ---

// CogState returns the current cognitive state from the Rust engine.
func (h *Handlers) CogState(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.CogState()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// CogCycle runs one cognitive cycle.
func (h *Handlers) CogCycle(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	if len(body) > 0 {
		json.Unmarshal(body, &params)
	}
	result, err := h.kernel.CogCycle(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// CogIntention registers or activates a cognitive intention.
func (h *Handlers) CogIntention(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	var req struct {
		Name     string  `json:"name"`
		Priority float64 `json:"priority"`
		Action   string  `json:"action"` // "register" or "activate"
	}
	if err := json.NewDecoder(r.Body).Decode(&req); err != nil {
		writeErr(w, http.StatusBadRequest, "invalid JSON: "+err.Error())
		return
	}
	if req.Name == "" {
		writeErr(w, http.StatusBadRequest, "name required")
		return
	}

	var result json.RawMessage
	var err error
	switch req.Action {
	case "activate":
		result, err = h.kernel.CogActivateIntention(req.Name)
	default: // "register" or empty
		if req.Priority == 0 {
			req.Priority = 0.5
		}
		result, err = h.kernel.CogRegisterIntention(req.Name, req.Priority)
	}
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// CogContradiction processes a contradiction vector.
func (h *Handlers) CogContradiction(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.CogContradiction(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// CogFact adds a fact to the knowledge store.
func (h *Handlers) CogFact(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.CogAddFact(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write(result)
}

// CogSearch searches the knowledge store.
func (h *Handlers) CogSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.CogSearch(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// CogSymbol registers a symbol in a domain.
func (h *Handlers) CogSymbol(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.CogRegisterSymbol(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write(result)
}

// CogGround grounds a vector to symbolic representations.
func (h *Handlers) CogGround(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.CogGround(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// Entropy Graph Handlers
// ---------------------------------------------------------------------------

// EntropyRecord records a forward pass of layer activations.
func (h *Handlers) EntropyRecord(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.EntropyRecord(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// EntropySnapshot returns the latest entropy snapshot.
func (h *Handlers) EntropySnapshot(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.EntropySnapshot()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// EntropyBottlenecks detects bottleneck and burst layers.
func (h *Handlers) EntropyBottlenecks(w http.ResponseWriter, r *http.Request) {
	var params interface{}
	if r.Method == http.MethodPost {
		body, err := ioutil.ReadAll(r.Body)
		if err != nil {
			writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
			return
		}
		json.Unmarshal(body, &params)
	} else if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET or POST")
		return
	}
	result, err := h.kernel.EntropyBottlenecks(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// EntropyTrend returns entropy trend for a specific layer.
func (h *Handlers) EntropyTrend(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.EntropyTrend(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// Binary Knowledge Store Handlers
// ---------------------------------------------------------------------------

// StoreAdd adds a fact to the binary knowledge store.
func (h *Handlers) StoreAdd(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.StoreAdd(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// StoreSearch searches the binary store by vector similarity.
func (h *Handlers) StoreSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.StoreSearch(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// StoreGet retrieves a fact by ID.
func (h *Handlers) StoreGet(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.StoreGet(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// StoreUpdateWeight updates the retrieval weight of a fact.
func (h *Handlers) StoreUpdateWeight(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.StoreUpdateWeight(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// StoreRemove removes a fact by ID.
func (h *Handlers) StoreRemove(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.StoreRemove(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// StoreCount returns the total number of facts in the binary store.
func (h *Handlers) StoreCount(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.StoreCount()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// --- Helpers ---

func writeJSON(w http.ResponseWriter, status int, v interface{}) {
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(status)
	json.NewEncoder(w).Encode(v)
}

func writeErr(w http.ResponseWriter, status int, msg string) {
	writeJSON(w, status, map[string]string{"error": msg})
}

func logMiddleware(next http.Handler) http.Handler {
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		start := time.Now()
		next.ServeHTTP(w, r)
		log.Printf("%s %s %s", r.Method, r.URL.Path, time.Since(start))
	})
}

// ---------------------------------------------------------------------------
// Cognitive Fabric Handlers
// ---------------------------------------------------------------------------

// FabricThink runs a full cognitive think cycle.
func (h *Handlers) FabricThink(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.FabricThink(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// FabricLearn teaches a fact to the cognitive fabric.
func (h *Handlers) FabricLearn(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.FabricLearn(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write(result)
}

// FabricLearnSymbol registers a symbol in the knot graph.
func (h *Handlers) FabricLearnSymbol(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.FabricLearnSymbol(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusCreated)
	w.Write(result)
}

// FabricTrain runs one adapter training step.
func (h *Handlers) FabricTrain(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.FabricTrain(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// FabricStatus returns the cognitive fabric status.
func (h *Handlers) FabricStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.FabricStatus()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// Knowledge Knot Graph Handlers
// ---------------------------------------------------------------------------

// KnotSearch searches the knot graph by text.
func (h *Handlers) KnotSearch(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.KnotSearch(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// KnotPath finds a path between two nodes.
func (h *Handlers) KnotPath(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.KnotPath(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// KnotStats returns knot graph statistics.
func (h *Handlers) KnotStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.KnotStats()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// KnotContradict records a contradiction between two nodes.
func (h *Handlers) KnotContradict(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.KnotContradict(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// LLM Bridge Handlers
// ---------------------------------------------------------------------------

// LLMEmbed gets an embedding for text.
func (h *Handlers) LLMEmbed(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.LLMEmbed(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// LLMDistill distills LLM knowledge into the knot graph.
func (h *Handlers) LLMDistill(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.LLMDistill(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// LLMStatus returns LLM bridge statistics.
func (h *Handlers) LLMStatus(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.LLMStatus()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// Hyperdimensional Engine Handlers
// ---------------------------------------------------------------------------

// HDTeach teaches text to the hyperdimensional semantic engine.
func (h *Handlers) HDTeach(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.HDTeach(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// HDEmbed embeds text using the hyperdimensional engine.
func (h *Handlers) HDEmbed(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.HDEmbed(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// HDSimilarity computes semantic similarity between two words.
func (h *Handlers) HDSimilarity(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.HDSimilarity(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// HDMostSimilar finds the most similar words to a query word.
func (h *Handlers) HDMostSimilar(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		writeErr(w, http.StatusMethodNotAllowed, "POST only")
		return
	}
	body, err := ioutil.ReadAll(r.Body)
	if err != nil {
		writeErr(w, http.StatusBadRequest, "read body: "+err.Error())
		return
	}
	var params interface{}
	json.Unmarshal(body, &params)
	result, err := h.kernel.HDMostSimilar(params)
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// HDStats returns hyperdimensional engine statistics.
func (h *Handlers) HDStats(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}
	result, err := h.kernel.HDStats()
	if err != nil {
		writeErr(w, http.StatusBadGateway, fmt.Sprintf("kernel: %v", err))
		return
	}
	w.Header().Set("Content-Type", "application/json")
	w.WriteHeader(http.StatusOK)
	w.Write(result)
}

// ---------------------------------------------------------------------------
// Metrics & Observability
// ---------------------------------------------------------------------------

// Metrics returns comprehensive system metrics.
func (h *Handlers) Metrics(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodGet {
		writeErr(w, http.StatusMethodNotAllowed, "GET only")
		return
	}

	// Collect metrics from all subsystems
	metrics := map[string]interface{}{
		"service": "mcp-zero",
		"version": "0.1.0",
	}

	// Kernel status
	if status, err := h.kernel.Status(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(status, &s) == nil {
			metrics["kernel"] = s
		}
	}

	// Fabric status
	if status, err := h.kernel.FabricStatus(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(status, &s) == nil {
			metrics["fabric"] = s
		}
	}

	// Knot graph stats
	if stats, err := h.kernel.KnotStats(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(stats, &s) == nil {
			metrics["knot_graph"] = s
		}
	}

	// LLM bridge stats
	if stats, err := h.kernel.LLMStatus(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(stats, &s) == nil {
			metrics["llm_bridge"] = s
		}
	}

	// Store count
	if count, err := h.kernel.StoreCount(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(count, &s) == nil {
			metrics["binary_store"] = s
		}
	}

	// HD engine stats
	if stats, err := h.kernel.HDStats(); err == nil {
		var s map[string]interface{}
		if json.Unmarshal(stats, &s) == nil {
			metrics["hyperdimensional"] = s
		}
	}

	writeJSON(w, http.StatusOK, metrics)
}

// ---------------------------------------------------------------------------
// Enterprise Middleware
// ---------------------------------------------------------------------------

// authMiddleware checks for API key in Authorization header.
// Set MCP_API_KEY env var to enable. If not set, auth is disabled.
func authMiddleware(next http.Handler) http.Handler {
	apiKey := os.Getenv("MCP_API_KEY")
	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip auth if no key configured or for health/metrics endpoints
		if apiKey == "" || r.URL.Path == "/health" || r.URL.Path == "/metrics" {
			next.ServeHTTP(w, r)
			return
		}

		auth := r.Header.Get("Authorization")
		if auth == "" {
			w.Header().Set("WWW-Authenticate", "Bearer")
			writeErr(w, http.StatusUnauthorized, "missing Authorization header")
			return
		}

		token := strings.TrimPrefix(auth, "Bearer ")
		if token != apiKey {
			writeErr(w, http.StatusUnauthorized, "invalid API key")
			return
		}

		next.ServeHTTP(w, r)
	})
}

// rateLimitMiddleware implements a simple token bucket rate limiter.
// 100 requests per minute per IP. Set MCP_RATE_LIMIT=0 to disable.
func rateLimitMiddleware(next http.Handler) http.Handler {
	var (
		mu      sync.Mutex
		buckets = make(map[string]*tokenBucket)
	)

	limitStr := os.Getenv("MCP_RATE_LIMIT")
	limit := 100 // default: 100 req/min
	if limitStr == "0" {
		// Rate limiting disabled
		return next
	}
	if limitStr != "" {
		if n, err := fmt.Sscanf(limitStr, "%d", &limit); n == 1 && err == nil && limit > 0 {
			// use parsed limit
		}
	}

	return http.HandlerFunc(func(w http.ResponseWriter, r *http.Request) {
		// Skip rate limit for health endpoint
		if r.URL.Path == "/health" {
			next.ServeHTTP(w, r)
			return
		}

		ip := r.RemoteAddr
		if idx := strings.LastIndex(ip, ":"); idx != -1 {
			ip = ip[:idx]
		}

		mu.Lock()
		b, ok := buckets[ip]
		if !ok {
			b = &tokenBucket{tokens: limit, max: limit, lastRefill: time.Now()}
			buckets[ip] = b
		}
		b.refill()
		allowed := b.take()
		mu.Unlock()

		if !allowed {
			w.Header().Set("Retry-After", "60")
			writeErr(w, http.StatusTooManyRequests, "rate limit exceeded")
			return
		}

		// Enforce max request body size (1MB)
		r.Body = http.MaxBytesReader(w, r.Body, 1<<20)

		next.ServeHTTP(w, r)
	})
}

// tokenBucket is a simple token bucket for rate limiting.
type tokenBucket struct {
	tokens     int
	max        int
	lastRefill time.Time
}

func (tb *tokenBucket) refill() {
	now := time.Now()
	elapsed := now.Sub(tb.lastRefill)
	if elapsed >= time.Minute {
		tb.tokens = tb.max
		tb.lastRefill = now
	}
}

func (tb *tokenBucket) take() bool {
	if tb.tokens > 0 {
		tb.tokens--
		return true
	}
	return false
}
