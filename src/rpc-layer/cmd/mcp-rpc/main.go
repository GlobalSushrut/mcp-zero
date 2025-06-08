// MCP-ZERO RPC Server
// A lightweight implementation compatible with Go 1.13
package main

import (
	"context"
	"flag"
	"fmt"
	"log"
	"net"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"

	"github.com/mcp-zero/rpc-layer/pkg/service"
	"google.golang.org/grpc"
	"google.golang.org/grpc/reflection"
)

// MonitorHandler provides basic system monitoring information
func MonitorHandler(w http.ResponseWriter, r *http.Request) {
	w.Header().Set("Content-Type", "text/plain")
	fmt.Fprintf(w, "MCP-ZERO RPC Server\n")
	fmt.Fprintf(w, "Status: Running\n")
	fmt.Fprintf(w, "Time: %s\n", time.Now().Format(time.RFC3339))
}

func startMetricsServer(port int) {
	http.HandleFunc("/metrics", MonitorHandler)
	http.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, "healthy")
	})

	metricsAddr := fmt.Sprintf(":%d", port)
	log.Printf("Starting metrics server on %s", metricsAddr)

	go func() {
		if err := http.ListenAndServe(metricsAddr, nil); err != nil {
			log.Printf("Metrics server error: %v", err)
		}
	}()
}

func main() {
	// Parse command line flags
	port := flag.Int("port", 50051, "Port to listen on")
	metricsPort := flag.Int("metrics-port", 9090, "Port for metrics server")
	flag.Parse()

	// Start metrics server
	startMetricsServer(*metricsPort)

	// Create listener
	listener, err := net.Listen("tcp", fmt.Sprintf(":%d", *port))
	if err != nil {
		log.Fatalf("Failed to listen: %v", err)
	}

	// Create gRPC server
	server := grpc.NewServer()

	// Register agent service
	agentService := service.NewAgentService()
	// In a complete implementation, we would register the service with generated protobuf code
	// For this simplified version, we're just initializing the service
	
	// Enable reflection for easier debugging
	reflection.Register(server)

	// Setup context for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	defer cancel()

	// Handle shutdown signals
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigCh
		log.Printf("Received termination signal: %s", sig.String())
		cancel()
		server.GracefulStop()
	}()

	// Start server
	log.Printf("MCP-ZERO RPC server starting on :%d", *port)
	log.Printf("Hardware constraints: <27%% CPU, <827MB RAM")
	go func() {
		if err := server.Serve(listener); err != nil {
			log.Fatalf("Failed to serve: %v", err)
		}
	}()

	// Wait for cancellation
	<-ctx.Done()
	log.Println("MCP-ZERO RPC server shutdown complete")
}
