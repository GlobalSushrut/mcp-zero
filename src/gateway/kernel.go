package main

import (
	"bufio"
	"encoding/json"
	"fmt"
	"net"
	"sync"
	"sync/atomic"
)

// KernelBridge communicates with the Rust kernel over a Unix domain socket
// using newline-delimited JSON-RPC 2.0.
type KernelBridge struct {
	socketPath string
	nextID     uint64
	mu         sync.Mutex
}

// rpcRequest is a JSON-RPC 2.0 request.
type rpcRequest struct {
	JSONRPC string      `json:"jsonrpc"`
	Method  string      `json:"method"`
	Params  interface{} `json:"params"`
	ID      uint64      `json:"id"`
}

// rpcResponse is a JSON-RPC 2.0 response.
type rpcResponse struct {
	JSONRPC string           `json:"jsonrpc"`
	Result  json.RawMessage  `json:"result,omitempty"`
	Error   *rpcError        `json:"error,omitempty"`
	ID      uint64           `json:"id"`
}

// rpcError is a JSON-RPC 2.0 error object.
type rpcError struct {
	Code    int    `json:"code"`
	Message string `json:"message"`
}

// NewKernelBridge creates a new bridge to the Rust kernel.
func NewKernelBridge(socketPath string) *KernelBridge {
	return &KernelBridge{
		socketPath: socketPath,
	}
}

// Call sends a JSON-RPC request to the kernel and returns the result.
// Each call opens a fresh connection (simple, no pool needed at edge scale).
func (kb *KernelBridge) Call(method string, params interface{}) (json.RawMessage, error) {
	id := atomic.AddUint64(&kb.nextID, 1)

	req := rpcRequest{
		JSONRPC: "2.0",
		Method:  method,
		Params:  params,
		ID:      id,
	}

	reqBytes, err := json.Marshal(req)
	if err != nil {
		return nil, fmt.Errorf("marshal request: %w", err)
	}
	reqBytes = append(reqBytes, '\n')

	// Connect to kernel
	conn, err := net.Dial("unix", kb.socketPath)
	if err != nil {
		return nil, fmt.Errorf("connect to kernel at %s: %w", kb.socketPath, err)
	}
	defer conn.Close()

	// Send request
	if _, err := conn.Write(reqBytes); err != nil {
		return nil, fmt.Errorf("write to kernel: %w", err)
	}

	// Read response (single line)
	scanner := bufio.NewScanner(conn)
	if !scanner.Scan() {
		if err := scanner.Err(); err != nil {
			return nil, fmt.Errorf("read from kernel: %w", err)
		}
		return nil, fmt.Errorf("kernel closed connection without response")
	}

	var resp rpcResponse
	if err := json.Unmarshal(scanner.Bytes(), &resp); err != nil {
		return nil, fmt.Errorf("unmarshal response: %w", err)
	}

	if resp.Error != nil {
		return nil, fmt.Errorf("kernel error %d: %s", resp.Error.Code, resp.Error.Message)
	}

	return resp.Result, nil
}

// SpawnAgent asks the kernel to create a new agent.
func (kb *KernelBridge) SpawnAgent(config json.RawMessage) (json.RawMessage, error) {
	return kb.Call("kernel.spawn_agent", config)
}

// Execute asks the kernel to run an intent for an agent.
func (kb *KernelBridge) Execute(agentID, intent string) (json.RawMessage, error) {
	return kb.Call("kernel.execute", map[string]string{
		"agent_id": agentID,
		"intent":   intent,
	})
}

// Snapshot asks the kernel to persist an agent's state.
func (kb *KernelBridge) Snapshot(agentID string) (json.RawMessage, error) {
	return kb.Call("kernel.snapshot", map[string]string{
		"agent_id": agentID,
	})
}

// Recover asks the kernel to restore an agent from storage.
func (kb *KernelBridge) Recover(agentID string) (json.RawMessage, error) {
	return kb.Call("kernel.recover", map[string]string{
		"agent_id": agentID,
	})
}

// Status asks the kernel for its current status.
func (kb *KernelBridge) Status() (json.RawMessage, error) {
	return kb.Call("kernel.status", nil)
}

// --- Cognitive bridge methods ---

// CogState returns the current cognitive state.
func (kb *KernelBridge) CogState() (json.RawMessage, error) {
	return kb.Call("cog.state", nil)
}

// CogCycle runs one cognitive cycle with optional input vector.
func (kb *KernelBridge) CogCycle(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.cycle", params)
}

// CogRegisterIntention registers a cognitive intention.
func (kb *KernelBridge) CogRegisterIntention(name string, priority float64) (json.RawMessage, error) {
	return kb.Call("cog.register_intention", map[string]interface{}{
		"name":     name,
		"priority": priority,
	})
}

// CogActivateIntention activates a cognitive intention.
func (kb *KernelBridge) CogActivateIntention(name string) (json.RawMessage, error) {
	return kb.Call("cog.activate_intention", map[string]string{
		"name": name,
	})
}

// CogContradiction processes a contradiction vector.
func (kb *KernelBridge) CogContradiction(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.process_contradiction", params)
}

// CogAddFact adds a fact to the knowledge store.
func (kb *KernelBridge) CogAddFact(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.add_fact", params)
}

// CogSearch searches the knowledge store.
func (kb *KernelBridge) CogSearch(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.search", params)
}

// CogRegisterSymbol registers a symbol in a domain.
func (kb *KernelBridge) CogRegisterSymbol(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.register_symbol", params)
}

// CogGround grounds a vector to symbolic representations.
func (kb *KernelBridge) CogGround(params interface{}) (json.RawMessage, error) {
	return kb.Call("cog.ground", params)
}

// --- Entropy graph bridge methods ---

// EntropyRecord records a forward pass of layer activations.
func (kb *KernelBridge) EntropyRecord(params interface{}) (json.RawMessage, error) {
	return kb.Call("entropy.record", params)
}

// EntropySnapshot returns the latest entropy snapshot.
func (kb *KernelBridge) EntropySnapshot() (json.RawMessage, error) {
	return kb.Call("entropy.snapshot", nil)
}

// EntropyBottlenecks detects bottleneck and burst layers.
func (kb *KernelBridge) EntropyBottlenecks(params interface{}) (json.RawMessage, error) {
	return kb.Call("entropy.bottlenecks", params)
}

// EntropyTrend returns entropy trend for a layer.
func (kb *KernelBridge) EntropyTrend(params interface{}) (json.RawMessage, error) {
	return kb.Call("entropy.trend", params)
}

// --- Binary knowledge store bridge methods ---

// StoreAdd adds a fact to the binary store.
func (kb *KernelBridge) StoreAdd(params interface{}) (json.RawMessage, error) {
	return kb.Call("store.add", params)
}

// StoreSearch searches the binary store by vector similarity.
func (kb *KernelBridge) StoreSearch(params interface{}) (json.RawMessage, error) {
	return kb.Call("store.search", params)
}

// StoreGet retrieves a fact by ID.
func (kb *KernelBridge) StoreGet(params interface{}) (json.RawMessage, error) {
	return kb.Call("store.get", params)
}

// StoreUpdateWeight updates the retrieval weight of a fact.
func (kb *KernelBridge) StoreUpdateWeight(params interface{}) (json.RawMessage, error) {
	return kb.Call("store.update_weight", params)
}

// StoreRemove removes a fact by ID.
func (kb *KernelBridge) StoreRemove(params interface{}) (json.RawMessage, error) {
	return kb.Call("store.remove", params)
}

// StoreCount returns the total number of facts.
func (kb *KernelBridge) StoreCount() (json.RawMessage, error) {
	return kb.Call("store.count", nil)
}

// --- Cognitive Fabric bridge methods ---

// FabricThink runs a full cognitive think cycle on text input.
func (kb *KernelBridge) FabricThink(params interface{}) (json.RawMessage, error) {
	return kb.Call("fabric.think", params)
}

// FabricLearn teaches a fact to the cognitive fabric.
func (kb *KernelBridge) FabricLearn(params interface{}) (json.RawMessage, error) {
	return kb.Call("fabric.learn", params)
}

// FabricLearnSymbol registers a symbol in the knot graph.
func (kb *KernelBridge) FabricLearnSymbol(params interface{}) (json.RawMessage, error) {
	return kb.Call("fabric.learn_symbol", params)
}

// FabricTrain runs one adapter training step.
func (kb *KernelBridge) FabricTrain(params interface{}) (json.RawMessage, error) {
	return kb.Call("fabric.train", params)
}

// FabricStatus returns the cognitive fabric status.
func (kb *KernelBridge) FabricStatus() (json.RawMessage, error) {
	return kb.Call("fabric.status", nil)
}

// --- Knowledge Knot Graph bridge methods ---

// KnotSearch searches the knot graph by text.
func (kb *KernelBridge) KnotSearch(params interface{}) (json.RawMessage, error) {
	return kb.Call("knot.search", params)
}

// KnotPath finds a path between two nodes in the knot graph.
func (kb *KernelBridge) KnotPath(params interface{}) (json.RawMessage, error) {
	return kb.Call("knot.path", params)
}

// KnotStats returns knot graph statistics.
func (kb *KernelBridge) KnotStats() (json.RawMessage, error) {
	return kb.Call("knot.stats", nil)
}

// KnotContradict records a contradiction between two nodes.
func (kb *KernelBridge) KnotContradict(params interface{}) (json.RawMessage, error) {
	return kb.Call("knot.contradict", params)
}

// --- LLM Bridge methods ---

// LLMEmbed gets an embedding for text via the LLM bridge.
func (kb *KernelBridge) LLMEmbed(params interface{}) (json.RawMessage, error) {
	return kb.Call("llm.embed", params)
}

// LLMDistill distills LLM knowledge into the knot graph.
func (kb *KernelBridge) LLMDistill(params interface{}) (json.RawMessage, error) {
	return kb.Call("llm.distill", params)
}

// LLMStatus returns LLM bridge statistics.
func (kb *KernelBridge) LLMStatus() (json.RawMessage, error) {
	return kb.Call("llm.status", nil)
}

// --- Hyperdimensional Engine bridge methods ---

// HDTeach teaches text to the hyperdimensional semantic engine.
func (kb *KernelBridge) HDTeach(params interface{}) (json.RawMessage, error) {
	return kb.Call("hd.teach", params)
}

// HDEmbed embeds text using the hyperdimensional engine.
func (kb *KernelBridge) HDEmbed(params interface{}) (json.RawMessage, error) {
	return kb.Call("hd.embed", params)
}

// HDSimilarity computes semantic similarity between two words.
func (kb *KernelBridge) HDSimilarity(params interface{}) (json.RawMessage, error) {
	return kb.Call("hd.similarity", params)
}

// HDMostSimilar finds the most similar words to a query word.
func (kb *KernelBridge) HDMostSimilar(params interface{}) (json.RawMessage, error) {
	return kb.Call("hd.most_similar", params)
}

// HDStats returns hyperdimensional engine statistics.
func (kb *KernelBridge) HDStats() (json.RawMessage, error) {
	return kb.Call("hd.stats", nil)
}
