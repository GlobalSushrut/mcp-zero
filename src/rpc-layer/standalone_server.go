// MCP-ZERO Standalone RPC Server
// Compatible with Go 1.13
package main

import (
	"context"
	"log"
	"net"
	"net/http"
	"os"
	"time"
)

// StandaloneServer provides a self-contained RPC server
// This server integrates all MCP-ZERO components for easy deployment
type StandaloneServer struct {
	mcpServer *MCPServer
	httpServer *http.Server
	grpcListener net.Listener
	dbConnected bool
}

// NewStandaloneServer creates a new standalone server instance
func NewStandaloneServer(config ServerConfig) *StandaloneServer {
	return &StandaloneServer{
		mcpServer: NewMCPServer(config),
	}
}

// Start launches the standalone server
func (s *StandaloneServer) Start() error {
	log.Println("Starting MCP-ZERO standalone server")
	
	// Start the main MCP server
	if err := s.mcpServer.Start(); err != nil {
		return err
	}
	
	// Set up HTTP server for API endpoints
	mux := http.NewServeMux()
	
	// Register API handlers
	s.registerAPIHandlers(mux)
	
	// Start HTTP server
	s.httpServer = &http.Server{
		Addr:    ":8080",
		Handler: mux,
	}
	
	go func() {
		log.Println("HTTP API server listening on :8080")
		if err := s.httpServer.ListenAndServe(); err != http.ErrServerClosed {
			log.Printf("HTTP server error: %v", err)
			os.Exit(1)
		}
	}()
	
	return nil
}

// Shutdown gracefully stops the standalone server
func (s *StandaloneServer) Shutdown() {
	log.Println("Shutting down standalone server")
	
	// Shutdown HTTP server
	ctx, cancel := context.WithTimeout(context.Background(), 10*time.Second)
	defer cancel()
	
	if s.httpServer != nil {
		s.httpServer.Shutdown(ctx)
	}
	
	// Shutdown MCP server
	if s.mcpServer != nil {
		s.mcpServer.Shutdown()
	}
	
	log.Println("Standalone server shutdown complete")
}

// registerAPIHandlers sets up HTTP API endpoints
func (s *StandaloneServer) registerAPIHandlers(mux *http.ServeMux) {
	// Health check endpoint
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("healthy"))
	})
	
	// Version endpoint
	mux.HandleFunc("/version", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "application/json")
		w.Write([]byte(`{"version":"0.7.0","build":"2025.06.07"}`))
	})
	
	// Add database endpoints
	s.mcpServer.initDBEndpoints(mux)
	
	// Add other API endpoints
	mux.HandleFunc("/api/agent/", s.mcpServer.handleAgentAPI)
	mux.HandleFunc("/api/llm/", s.mcpServer.handleLLMAPI)
	mux.HandleFunc("/api/consensus/", s.mcpServer.handleConsensusAPI)
	
	log.Println("API endpoints registered")
}