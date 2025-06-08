// MCP-ZERO Agent Service
// Compatible with Go 1.13
package main

import (
	"context"
	"fmt"
	"log"
	"net"
	"net/http"
	"time"
)

// AgentService handles agent lifecycle operations (spawn, execute, snapshot, etc.)
func (s *MCPServer) startAgentService() {
	defer s.wg.Done()
	
	addr := fmt.Sprintf(":%d", s.config.AgentPort)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		log.Printf("Failed to start Agent Service: %v", err)
		return
	}
	defer listener.Close()
	
	log.Printf("Agent Service listening on %s", addr)
	
	// Create a context for the service
	ctx, cancel := context.WithCancel(s.ctx)
	defer cancel()
	
	// Setup HTTP endpoints for agent operations
	mux := http.NewServeMux()
	
	// Agent lifecycle operations
	mux.HandleFunc("/agent/spawn", s.handleAgentSpawn)
	mux.HandleFunc("/agent/attachPlugin", s.handleAttachPlugin)
	mux.HandleFunc("/agent/execute", s.handleExecuteIntent)
	mux.HandleFunc("/agent/snapshot", s.handleAgentSnapshot)
	mux.HandleFunc("/agent/recover", s.handleAgentRecover)
	
	// Create HTTP server
	server := &http.Server{
		Addr:    addr,
		Handler: mux,
	}
	
	// Handle shutdown
	go func() {
		<-ctx.Done()
		shutdownCtx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		server.Shutdown(shutdownCtx)
	}()
	
	// Start the server
	if err := server.Serve(listener); err != http.ErrServerClosed {
		log.Printf("Agent Service error: %v", err)
	}
	
	log.Println("Agent Service shutdown complete")
}

// Handler functions for agent operations

func (s *MCPServer) handleAgentSpawn(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// In a real implementation, this would validate the request and call the kernel API
	log.Println("Spawning new agent")
	
	// Generate a unique agent ID
	agentID := fmt.Sprintf("agent-%d", time.Now().UnixNano())
	
	// Publish agent spawned event
	s.eventBus.Publish(&Event{
		Type:   EventAgentSpawned,
		Source: "agent-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id": agentID,
			"timestamp": time.Now().Unix(),
		},
	})
	
	// Return agent ID and status
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"agent_id":"%s","status":"active"}`, agentID)
}

func (s *MCPServer) handleAttachPlugin(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract agent ID and plugin path from request
	agentID := r.URL.Query().Get("agent_id")
	pluginPath := r.URL.Query().Get("plugin_path")
	
	if agentID == "" || pluginPath == "" {
		http.Error(w, "Missing required parameters: agent_id and plugin_path", http.StatusBadRequest)
		return
	}
	
	log.Printf("Attaching plugin %s to agent %s", pluginPath, agentID)
	
	// In a real implementation, this would call the kernel to attach the plugin
	// and perform ethical governance checks on the plugin
	
	// Generate plugin ID
	pluginID := fmt.Sprintf("plugin-%d", time.Now().UnixNano())
	
	// Publish plugin attached event
	s.eventBus.Publish(&Event{
		Type:   EventAgentPluginAttached,
		Source: "agent-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id": agentID,
			"plugin_id": pluginID,
			"plugin_path": pluginPath,
			"timestamp": time.Now().Unix(),
		},
	})
	
	// Return plugin ID and status
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"plugin_id":"%s","status":"attached"}`, pluginID)
}

func (s *MCPServer) handleExecuteIntent(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract agent ID and intent from request
	agentID := r.URL.Query().Get("agent_id")
	intent := r.URL.Query().Get("intent")
	
	if agentID == "" || intent == "" {
		http.Error(w, "Missing required parameters: agent_id and intent", http.StatusBadRequest)
		return
	}
	
	log.Printf("Executing intent '%s' on agent %s", intent, agentID)
	
	// In a real implementation, this would call the kernel to execute the intent
	// and perform ethical governance checks
	
	// Generate execution ID
	executionID := fmt.Sprintf("exec-%d", time.Now().UnixNano())
	
	// Publish agent executed event
	s.eventBus.Publish(&Event{
		Type:   EventAgentExecuted,
		Source: "agent-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id": agentID,
			"execution_id": executionID,
			"intent": intent,
			"timestamp": time.Now().Unix(),
		},
	})
	
	// Return execution ID and status
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"execution_id":"%s","status":"completed"}`, executionID)
}

func (s *MCPServer) handleAgentSnapshot(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract agent ID from request
	agentID := r.URL.Query().Get("agent_id")
	if agentID == "" {
		http.Error(w, "Missing required parameter: agent_id", http.StatusBadRequest)
		return
	}
	
	log.Printf("Taking snapshot of agent %s", agentID)
	
	// Generate snapshot ID
	snapshotID := fmt.Sprintf("snapshot-%d", time.Now().UnixNano())
	
	// Publish agent snapshot event
	s.eventBus.Publish(&Event{
		Type:   EventAgentSnapshotted,
		Source: "agent-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id": agentID,
			"snapshot_id": snapshotID,
			"timestamp": time.Now().Unix(),
		},
	})
	
	// Return snapshot ID and status
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"snapshot_id":"%s","status":"completed"}`, snapshotID)
}

func (s *MCPServer) handleAgentRecover(w http.ResponseWriter, r *http.Request) {
	if r.Method != http.MethodPost {
		http.Error(w, "Method not allowed", http.StatusMethodNotAllowed)
		return
	}
	
	// Extract snapshot ID from request
	snapshotID := r.URL.Query().Get("snapshot_id")
	if snapshotID == "" {
		http.Error(w, "Missing required parameter: snapshot_id", http.StatusBadRequest)
		return
	}
	
	log.Printf("Recovering agent from snapshot %s", snapshotID)
	
	// In a real implementation, this would call the kernel to recover an agent
	
	// Generate a new agent ID for the recovered agent
	agentID := fmt.Sprintf("agent-%d", time.Now().UnixNano())
	
	// Publish agent recovered event
	s.eventBus.Publish(&Event{
		Type:   EventAgentRecovered,
		Source: "agent-service",
		Target: "*",
		Payload: map[string]interface{}{
			"agent_id": agentID,
			"snapshot_id": snapshotID,
			"timestamp": time.Now().Unix(),
		},
	})
	
	// Return agent ID and status
	w.Header().Set("Content-Type", "application/json")
	fmt.Fprintf(w, `{"agent_id":"%s","status":"recovered"}`, agentID)
}
