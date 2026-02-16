// Package main implements the MCP-ZERO HTTP gateway.
//
// Single-port HTTP server that bridges external clients to the Rust kernel
// via Unix domain socket JSON-RPC. Uses bbolt for embedded key-value storage.
//
// Architecture:
//
//	Client → HTTP :8080 → Go Gateway → Unix socket → Rust Kernel
//	                          │
//	                        bbolt DB
package main

import (
	"context"
	"flag"
	"log"
	"net/http"
	"os"
	"os/signal"
	"syscall"
	"time"
)

func main() {
	addr := flag.String("addr", ":8080", "HTTP listen address")
	dbPath := flag.String("db", "/tmp/mcp-gateway.db", "bbolt database path")
	kernelSock := flag.String("kernel", "/tmp/mcp-kernel.sock", "Kernel Unix socket path")
	flag.Parse()

	// Open bbolt store
	store, err := NewStore(*dbPath)
	if err != nil {
		log.Fatalf("Failed to open store: %v", err)
	}
	defer store.Close()

	// Create kernel bridge
	kernel := NewKernelBridge(*kernelSock)

	// Build router
	mux := NewRouter(store, kernel)

	srv := &http.Server{
		Addr:         *addr,
		Handler:      mux,
		ReadTimeout:  10 * time.Second,
		WriteTimeout: 30 * time.Second,
		IdleTimeout:  60 * time.Second,
	}

	// Graceful shutdown
	done := make(chan os.Signal, 1)
	signal.Notify(done, os.Interrupt, syscall.SIGTERM)

	go func() {
		log.Printf("MCP-ZERO gateway listening on %s", *addr)
		if err := srv.ListenAndServe(); err != nil && err != http.ErrServerClosed {
			log.Fatalf("HTTP server error: %v", err)
		}
	}()

	<-done
	log.Println("Shutting down gateway...")

	ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
	defer cancel()

	if err := srv.Shutdown(ctx); err != nil {
		log.Printf("Shutdown error: %v", err)
	}

	log.Println("MCP-ZERO gateway stopped")
}
