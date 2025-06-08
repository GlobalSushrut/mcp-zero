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
	"syscall"
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

func main() {
	// Parse command line flags
	agentPort := flag.Int("agent-port", 50051, "Agent service port")
	auditPort := flag.Int("audit-port", 50052, "Audit service port")
	llmPort := flag.Int("llm-port", 50053, "LLM service port")
	consensusPort := flag.Int("consensus-port", 50054, "Consensus service port")
	metricsPort := flag.Int("metrics-port", 9090, "Metrics server port")
	shutdownTimeout := flag.Int("shutdown-timeout", 30, "Shutdown timeout in seconds")
	flag.Parse()
	
	// Start metrics server
	startMetricsServer(*metricsPort)
	
	// Create server configuration
	config := ServerConfig{
		AgentPort:           *agentPort,
		AuditPort:           *auditPort,
		LLMPort:             *llmPort,
		ConsensusPort:       *consensusPort,
		MetricsPort:         *metricsPort,
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
