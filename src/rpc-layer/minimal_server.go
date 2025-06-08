// Minimal MCP-ZERO RPC Server
// Compatible with Go 1.13, with minimal dependencies
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
	"sync"
	"syscall"
	"time"
)

// HealthServer provides basic health check and metrics endpoints
func runHealthServer(port int, wg *sync.WaitGroup) {
	defer wg.Done()

	mux := http.NewServeMux()
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		fmt.Fprint(w, "healthy")
	})

	mux.HandleFunc("/metrics", func(w http.ResponseWriter, r *http.Request) {
		w.Header().Set("Content-Type", "text/plain")
		fmt.Fprintf(w, "# MCP-ZERO RPC Server Metrics\n")
		fmt.Fprintf(w, "mcp_server_uptime_seconds %d\n", time.Now().Unix()-startTime)
		fmt.Fprintf(w, "mcp_server_version 0.1.0\n")
	})

	addr := fmt.Sprintf(":%d", port)
	log.Printf("Starting health server on %s", addr)
	
	server := &http.Server{
		Addr:    addr,
		Handler: mux,
	}
	
	go func() {
		<-shutdownCh
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		server.Shutdown(ctx)
	}()
	
	if err := server.ListenAndServe(); err != http.ErrServerClosed {
		log.Printf("Health server error: %v", err)
	}
}

// RPCServer provides a TCP-based RPC service
func runRPCServer(port int, wg *sync.WaitGroup) {
	defer wg.Done()
	
	addr := fmt.Sprintf(":%d", port)
	listener, err := net.Listen("tcp", addr)
	if err != nil {
		log.Fatalf("Failed to listen on %s: %v", addr, err)
	}
	defer listener.Close()
	
	log.Printf("RPC server listening on %s", addr)
	
	conns := make(map[net.Conn]struct{})
	var mu sync.Mutex
	
	go func() {
		<-shutdownCh
		mu.Lock()
		for conn := range conns {
			conn.Close()
		}
		mu.Unlock()
		listener.Close()
	}()
	
	for {
		conn, err := listener.Accept()
		if err != nil {
			select {
			case <-shutdownCh:
				return
			default:
				log.Printf("Error accepting connection: %v", err)
				continue
			}
		}
		
		mu.Lock()
		conns[conn] = struct{}{}
		mu.Unlock()
		
		go handleConnection(conn, &mu, conns)
	}
}

// handleConnection processes incoming RPC requests
func handleConnection(conn net.Conn, mu *sync.Mutex, conns map[net.Conn]struct{}) {
	defer func() {
		conn.Close()
		mu.Lock()
		delete(conns, conn)
		mu.Unlock()
	}()
	
	// In a real implementation, this would handle protocol parsing and dispatch
	// to the appropriate service methods
	
	// For now, just echo a simple response
	buffer := make([]byte, 1024)
	n, err := conn.Read(buffer)
	if err != nil {
		log.Printf("Error reading from connection: %v", err)
		return
	}
	
	// Simple protocol: first byte indicates the operation
	// 1 = spawn agent, 2 = attach plugin, etc.
	if n > 0 {
		op := buffer[0]
		log.Printf("Received operation: %d", op)
		
		// Send a simple response
		resp := []byte{op, 0, 1} // operation, status=success, payload size
		_, err = conn.Write(resp)
		if err != nil {
			log.Printf("Error writing response: %v", err)
		}
	}
}

// Global variables
var (
	startTime  int64
	shutdownCh = make(chan struct{})
)

func main() {
	// Parse command line flags
	rpcPort := flag.Int("port", 50051, "Port for RPC server")
	healthPort := flag.Int("health-port", 9090, "Port for health/metrics server")
	flag.Parse()
	
	startTime = time.Now().Unix()
	
	// Handle graceful shutdown
	sigCh := make(chan os.Signal, 1)
	signal.Notify(sigCh, syscall.SIGINT, syscall.SIGTERM)
	go func() {
		sig := <-sigCh
		log.Printf("Received termination signal: %s", sig)
		close(shutdownCh)
	}()
	
	log.Printf("Starting MCP-ZERO Minimal RPC Server")
	log.Printf("Hardware constraints: <27%% CPU, <827MB RAM")
	
	// Start servers
	var wg sync.WaitGroup
	wg.Add(2)
	
	go runHealthServer(*healthPort, &wg)
	go runRPCServer(*rpcPort, &wg)
	
	// Wait for all servers to shut down
	wg.Wait()
	log.Println("MCP-ZERO RPC server shutdown complete")
}
