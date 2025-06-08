// MCP-ZERO Database Service
// Minimal MongoDB + HeapBT implementation
package main

import (
	"context"
	"fmt"
	"log"
	"sync"
	"time"
)

// MemoryNode represents a node in the binary memory tree
type MemoryNode struct {
	Key       string                 `json:"key"`
	Value     map[string]interface{} `json:"value"`
	Hash      string                 `json:"hash"`
	Timestamp int64                  `json:"timestamp"`
	Left      *MemoryNode            `json:"-"`
	Right     *MemoryNode            `json:"-"`
}

// HeapBT is a memory-efficient binary tree for agent memory
type HeapBT struct {
	Root      *MemoryNode
	NodeCount int
	mu        sync.RWMutex
}

// DBService provides database operations for agent memory
type DBService struct {
	// In-memory binary tree storage
	agentMemory map[string]*HeapBT // Maps agent ID to its memory tree
	
	// MongoDB connection for persistence
	mongoConnector *MongoConnector
	
	// Synchronization
	mu          sync.RWMutex
	eventBus    *EventBus
}

// NewDBService creates a new database service
func NewDBService(eventBus *EventBus) *DBService {
	service := &DBService{
		agentMemory: make(map[string]*HeapBT),
		eventBus:    eventBus,
	}
	
	// Subscribe to agent events
	service.subscribeToEvents()
	
	return service
}

// subscribeToEvents registers for relevant agent events
func (db *DBService) subscribeToEvents() {
	// Subscribe to agent creation events
	db.eventBus.Subscribe(string(EventAgentSpawned), func(e *Event) {
		agentID := e.Payload["agent_id"].(string)
		db.initializeAgentMemory(agentID)
	})
	
	// Subscribe to agent memory access events
	memoryEvents := []EventType{
		EventAgentIntentExecuted,
		EventAgentSnapshotCreated,
		EventAgentRecovered,
		EventLLMPromptProcessed,
	}
	
	for _, eventType := range memoryEvents {
		et := eventType // Avoid closure problems
		db.eventBus.Subscribe(string(et), func(e *Event) {
			if agentID, ok := e.Payload["agent_id"].(string); ok {
				// Persist event to agent memory
				db.storeAgentMemory(agentID, string(et), e.Payload)
			}
		})
	}
}

// initializeAgentMemory creates a new memory tree for an agent
func (db *DBService) initializeAgentMemory(agentID string) {
	db.mu.Lock()
	defer db.mu.Unlock()
	
	if _, exists := db.agentMemory[agentID]; !exists {
		db.agentMemory[agentID] = &HeapBT{
			Root:      nil,
			NodeCount: 0,
		}
		log.Printf("Initialized memory tree for agent %s", agentID)
	}
}

// storeAgentMemory adds a memory node to the agent's tree
func (db *DBService) storeAgentMemory(agentID, key string, data map[string]interface{}) {
	db.mu.Lock()
	defer db.mu.Unlock()
	
	// Ensure agent memory exists
	if _, exists := db.agentMemory[agentID]; !exists {
		db.initializeAgentMemory(agentID)
	}
	
	// Create memory node
	node := &MemoryNode{
		Key:       key,
		Value:     data,
		Hash:      generateSimpleHash(data),
		Timestamp: time.Now().Unix(),
	}
	
	// Add to binary tree
	tree := db.agentMemory[agentID]
	tree.mu.Lock()
	defer tree.mu.Unlock()
	
	tree.Root = insertNode(tree.Root, node)
	tree.NodeCount++
	
	// In production: Would also persist to MongoDB here
	log.Printf("Stored memory for agent %s: %s", agentID, key)
}

// getAgentMemory retrieves memories for an agent based on a key prefix
func (db *DBService) getAgentMemory(agentID, keyPrefix string) []*MemoryNode {
	db.mu.RLock()
	defer db.mu.RUnlock()
	
	tree, exists := db.agentMemory[agentID]
	if !exists {
		return nil
	}
	
	tree.mu.RLock()
	defer tree.mu.RUnlock()
	
	result := make([]*MemoryNode, 0)
	findNodesWithPrefix(tree.Root, keyPrefix, &result)
	return result
}

// startDBService initializes the database service within the MCP server
func (s *MCPServer) startDBService() {
	s.dbService = NewDBService(s.eventBus)
	log.Println("Database Service started")
}

// Helper functions for binary tree operations

// insertNode adds a node to the binary tree
func insertNode(root, node *MemoryNode) *MemoryNode {
	if root == nil {
		return node
	}
	
	if node.Key < root.Key {
		root.Left = insertNode(root.Left, node)
	} else {
		root.Right = insertNode(root.Right, node)
	}
	
	return root
}

// findNodesWithPrefix searches for nodes with a key prefix
func findNodesWithPrefix(root *MemoryNode, prefix string, result *[]*MemoryNode) {
	if root == nil {
		return
	}
	
	// Check if current node matches prefix
	if len(root.Key) >= len(prefix) && root.Key[:len(prefix)] == prefix {
		*result = append(*result, root)
	}
	
	// Search both subtrees
	findNodesWithPrefix(root.Left, prefix, result)
	findNodesWithPrefix(root.Right, prefix, result)
}

// generateSimpleHash creates a simple hash for demo purposes
// In production, would use proper cryptographic hashing
func generateSimpleHash(data map[string]interface{}) string {
	return fmt.Sprintf("hash-%d", time.Now().UnixNano())
}

// getNodeCount returns the number of nodes in an agent's memory tree
func (db *DBService) getNodeCount(agentID string) int {
	db.mu.RLock()
	defer db.mu.RUnlock()
	
	if tree, exists := db.agentMemory[agentID]; exists {
		tree.mu.RLock()
		defer tree.mu.RUnlock()
		return tree.NodeCount
	}
	
	return 0
}

// optimizeMemoryTree balances and optimizes the binary tree
// This helps stay within the <827MB RAM constraint
func (db *DBService) optimizeMemoryTree(agentID string) {
	db.mu.Lock()
	defer db.mu.Unlock()
	
	tree, exists := db.agentMemory[agentID]
	if !exists {
		return
	}
	
	tree.mu.Lock()
	defer tree.mu.Unlock()
	
	// In a real implementation, this would balance the tree
	// and optimize memory usage
	log.Printf("Optimized memory tree for agent %s", agentID)
	
	// For simulation, we'll just log that we did it
	// In reality, this would rebuild a balanced binary tree
}
