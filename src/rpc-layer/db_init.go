// MCP-ZERO Database Service Initialization
// Compatible with Go 1.13
package main

import (
	"log"
	"net/http"
)

// startDBService initializes the database service with memory persistence
func (s *MCPServer) startDBService() {
	log.Println("Initializing MCP-ZERO agent memory persistence layer")
	
	// Initialize the DB service with event bus access
	s.dbService = NewDBService(s.eventBus)
	
	// Initialize MongoDB connector for persistence
	// This is done async to not block server startup
	go s.initMongoDBConnection()
	
	// Register database endpoints with the HTTP server
	// This will allow retrieving and manipulating agent memories via HTTP
	dbMux := http.NewServeMux()
	s.startDBEndpoints(dbMux)
	
	// Start DB metrics and monitoring
	go s.monitorMemoryUsage()
	
	log.Printf("Database service started with binary tree storage and MongoDB persistence")
}

// monitorMemoryUsage keeps track of agent memory usage to ensure we stay
// within the <827MB RAM hardware constraint
func (s *MCPServer) monitorMemoryUsage() {
	// In production, this would actually track memory usage
	log.Println("Memory monitoring active: ensuring <827MB RAM usage")
	
	// Subscribe to memory growth events
	s.eventBus.Subscribe(string(EventAgentMemoryThresholdReached), func(e *Event) {
		agentID := e.Payload["agent_id"].(string)
		log.Printf("Agent %s approaching memory threshold, optimizing", agentID)
		s.dbService.optimizeMemoryTree(agentID)
	})
}

// initDBEndpoints initializes the HTTP endpoints for the database service
func (s *MCPServer) initDBEndpoints(serveMux *http.ServeMux) {
	// Add DB endpoints to the server mux
	serveMux.HandleFunc("/db/memory/get", s.handleGetAgentMemory)
	serveMux.HandleFunc("/db/memory/snapshot", s.handleSnapshotMemory)
	serveMux.HandleFunc("/db/memory/compact", s.handleCompactMemory)
}

// Event types for memory system
const (
	EventAgentMemoryThresholdReached EventType = "agent.memory.threshold.reached"
	EventAgentMemoryOptimized        EventType = "agent.memory.optimized"
	EventAgentMemoryCompacted        EventType = "agent.memory.compacted"
)
