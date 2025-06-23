// MCP-ZERO Main Entry Point
// Compatible with Go 1.13
package main

import (
	"flag"
	"fmt"
	"log"
	"net/http"
	"os"
	"os/signal"
	"runtime"
	"syscall"
	"time"
)

// MetricsHandler provides basic monitoring information
func MetricsHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	w.Write([]byte("MCP-ZERO Server Status: Running\n"))
	w.Write([]byte("Version: 0.7.0\n"))
	w.Write([]byte("Hardware Constraints: <27% 1-core i3 CPU, Peak 827MB RAM\n"))
	w.Write([]byte("Core Components: Agent, Audit, LLM, Consensus\n"))
}

// HealthHandler provides a simple health check endpoint
func HealthHandler(w http.ResponseWriter, r *http.Request) {
	w.WriteHeader(http.StatusOK)
	w.Write([]byte("healthy"))
}

// startMetricsServer starts the metrics and health HTTP server
func startMetricsServer(port int) {
	mux := http.NewServeMux()
	mux.HandleFunc("/metrics", MetricsHandler)
	mux.HandleFunc("/health", HealthHandler)
	
	addr := ":9090"
	if port > 0 {
		addr = fmt.Sprintf(":%d", port)
	}
	
	go func() {
		log.Printf("Starting metrics server on %s", addr)
		if err := http.ListenAndServe(addr, mux); err != nil {
			log.Printf("Metrics server error: %v", err)
		}
	}()
}

// startAPIServer starts the HTTP API server for MCP-ZERO services
func startAPIServer(port int) {
	mux := http.NewServeMux()
	
	// Initialize base API endpoints
	mux.HandleFunc("/api/v1/health", HealthHandler)
	
	// Setup memory trace API endpoints
	InitializeMemoryTraceAPI(mux)
	
	// Start resource monitoring
	go monitorResources()
	
	// Start API server
	addr := fmt.Sprintf(":%d", port)
	log.Printf("API server listening on %s", addr)
	if err := http.ListenAndServe(addr, mux); err != nil {
		log.Fatalf("API server error: %v", err)
	}
}

// monitorResources periodically checks resource usage against MCP-ZERO constraints
func monitorResources() {
	ticker := time.NewTicker(5 * time.Second)
	defer ticker.Stop()
	
	for range ticker.C {
		var memStats runtime.MemStats
		runtime.ReadMemStats(&memStats)
		
		// Convert bytes to MB
		usedMemoryMB := float64(memStats.Alloc) / 1024 / 1024
		
		// Check if memory usage exceeds constraints
		if usedMemoryMB > 827 {
			log.Printf("WARNING: Memory usage (%.2f MB) exceeds MCP-ZERO constraints (<827 MB)", usedMemoryMB)
		}
		
		// Note: For CPU monitoring, we'd need a more sophisticated approach
		// This is a simplified version for the demo
	}
}

func main() {
	// Parse command line flags
	agentPort := flag.Int("agent-port", 50051, "Agent service port")
	auditPort := flag.Int("audit-port", 50052, "Audit service port")
	llmPort := flag.Int("llm-port", 50053, "LLM service port")
	consensusPort := flag.Int("consensus-port", 50054, "Consensus service port")
	metricsPort := flag.Int("metrics-port", 9090, "Metrics server port")
	apiPort := flag.Int("api-port", 8081, "HTTP API server port")
	accelerationPort := flag.Int("acceleration-port", 50055, "Acceleration server (Edge Runtime) port")
	shutdownTimeout := flag.Int("shutdown-timeout", 30, "Shutdown timeout in seconds")
	flag.Parse()
	
	log.Println("Starting MCP-ZERO v7 server with ZK-traceable consensus")
	log.Println("Hardware constraints: <27% CPU, <827MB RAM")
	
	// Start metrics server
	startMetricsServer(*metricsPort)
	
	// Start API server in a separate goroutine
	go startAPIServer(*apiPort)
	
	// Create server configuration
	config := ServerConfig{
		AgentPort:           *agentPort,
		AuditPort:           *auditPort,
		LLMPort:             *llmPort,
		ConsensusPort:       *consensusPort,
		MetricsPort:         *metricsPort,
		APIPort:             *apiPort,
		AccelerationPort:    *accelerationPort, // Edge Runtime Booster port
		ShutdownTimeoutSecs: *shutdownTimeout,
	}
	
	// Create and start the MCP-ZERO server
	server := NewMCPServer(config)
	if err := server.Start(); err != nil {
		log.Fatalf("Failed to start MCP-ZERO server: %v", err)
	}
	
	// Wait for termination signal
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	sig := <-sigCh
	log.Printf("Received termination signal: %s", sig)
	
	// Shutdown gracefully
	server.Shutdown()
	log.Println("MCP-ZERO server exited")
}
