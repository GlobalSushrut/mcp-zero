// MCP-ZERO Base Server 
// Compatible with Go 1.13
package main

import (
	"context"
	"log"
	"sync"
	"time"
)

// ServerConfig holds the configuration for all MCP-ZERO services
type ServerConfig struct {
	AgentPort           int
	AuditPort           int
	LLMPort             int
	ConsensusPort       int
	MetricsPort         int
	APIPort             int
	AccelerationPort    int  // Port for the Edge Runtime Booster
	ShutdownTimeoutSecs int
}

// MCPServer coordinates all MCP-ZERO services
type MCPServer struct {
	config             *ServerConfig
	shutdown           chan struct{}
	wg                 sync.WaitGroup
	ctx                context.Context
	cancel             context.CancelFunc
	eventBus           *EventBus         // Event bus for service communication
	dbService          *DBService        // Database service for agent memory persistence
	accelerationService *AccelerationService // Edge Runtime Booster service
	startTime          time.Time         // Server start time
}

// NewMCPServer creates a new MCP-ZERO server instance
func NewMCPServer(config ServerConfig) *MCPServer {
	ctx, cancel := context.WithCancel(context.Background())
	server := &MCPServer{
		config:   &config,
		ctx:      ctx,
		cancel:   cancel,
		shutdown: make(chan struct{}),
		eventBus: NewEventBus(),
	}
	
	return server
}

// Start launches all MCP-ZERO services
func (s *MCPServer) Start() error {
	log.Println("Starting MCP-ZERO server with hardware constraints: <27% CPU, <827MB RAM")
	
	// Record server start time
	s.startTime = time.Now()
	
	// Initialize the database service first
	s.startDBService()
	
	// Start each service
	s.wg.Add(5) // One for each service including acceleration
	
	go s.startAgentService()
	go s.startAuditService()
	go s.startLLMService()
	go s.startConsensusService()
	go s.startAccelerationService() // Start Edge Runtime Booster
	
	log.Println("MCP-ZERO server started with agent memory persistence and edge acceleration")
	
	return nil
}

// Shutdown gracefully stops all services
func (s *MCPServer) Shutdown() {
	log.Println("Shutting down MCP-ZERO server...")
	s.cancel()
	
	// Create timeout context for shutdown
	timeoutCtx, cancel := context.WithTimeout(context.Background(), 
		time.Duration(s.config.ShutdownTimeoutSecs)*time.Second)
	defer cancel()
	
	// Wait for all services to shut down or timeout
	done := make(chan struct{})
	go func() {
		s.wg.Wait()
		close(done)
	}()
	
	select {
	case <-done:
		log.Println("All services shutdown gracefully")
	case <-timeoutCtx.Done():
		log.Println("Shutdown timeout exceeded, some services may not have terminated properly")
	}
}
