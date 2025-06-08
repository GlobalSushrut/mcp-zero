// MCP-ZERO Event Bus
// Provides inter-service communication channel
package main

import (
	"log"
	"sync"
)

// EventType defines different types of events in the system
type EventType string

// Event types for various operations
const (
	// Agent service events
	EventAgentSpawned      EventType = "agent.spawned"
	EventAgentPluginAttached EventType = "agent.plugin.attached"
	EventAgentIntentExecuted EventType = "agent.intent.executed"
	EventAgentSnapshotCreated EventType = "agent.snapshot.created"
	EventAgentRecovered    EventType = "agent.recovered"

	// Audit service events
	EventAuditLogCreated       EventType = "audit.log.created"
	EventAuditTraceGenerated   EventType = "audit.trace.generated"
	EventAuditTraceVerified    EventType = "audit.trace.verified"
	EventAuditLogExported      EventType = "audit.log.exported"
	EventAuditLogged           EventType = "audit.logged"
	EventAuditVerified         EventType = "audit.verified"

	// LLM service events
	EventLLMPromptProcessed EventType = "llm.prompt.processed"
	EventLLMIntentExtracted EventType = "llm.intent.extracted"
	EventLLMEvaluated       EventType = "llm.evaluated"
	EventLLMResponseVerified EventType = "llm.response.verified"
	EventLLMIntentProcessed EventType = "llm.intent.processed"

	// Consensus service events
	EventConsensusProposed  EventType = "consensus.proposed"
	EventConsensusVoted     EventType = "consensus.voted"
	EventConsensusCommitted EventType = "consensus.committed"
	EventConsensusVerified  EventType = "consensus.verified"

	// ZK-traceable events
	EventZKProofGenerated EventType = "zk.proof.generated"
	EventZKProofVerified  EventType = "zk.proof.verified"
	EventZKTracePublished EventType = "zk.trace.published"

	// Solidity agreement events
	EventSolidityAgreementCreated EventType = "solidity.agreement.created"
	EventSolidityAgreementSigned  EventType = "solidity.agreement.signed"
	EventSolidityAgreementVerified EventType = "solidity.agreement.verified"
	EventSolidityAgreementEnforced EventType = "solidity.agreement.enforced"
	EventSolidityAgreementViolation EventType = "solidity.agreement.violation"
	EventEthicsRuleEvaluated     EventType = "ethics.rule.evaluated"

	// Memory system events
	EventAgentMemoryThresholdReached EventType = "agent.memory.threshold.reached"
	EventAgentMemoryOptimized        EventType = "agent.memory.optimized"
	EventAgentMemoryCompacted        EventType = "agent.memory.compacted"
)

// EventHandler is a function that handles an event
type EventHandler func(event *Event)

// Event represents a system event with payload
type Event struct {
	Type    EventType
	Source  string
	Target  string
	Payload map[string]interface{}
}

// EventBus handles event publishing and subscription
type EventBus struct {
	subscribers map[EventType][]EventHandler
	mu          sync.RWMutex
}

// NewEventBus creates a new event bus
func NewEventBus() *EventBus {
	return &EventBus{
		subscribers: make(map[EventType][]EventHandler),
	}
}

// Subscribe registers a handler for a specific event type
func (eb *EventBus) Subscribe(eventType EventType, handler EventHandler) {
	eb.mu.Lock()
	defer eb.mu.Unlock()
	
	eb.subscribers[eventType] = append(eb.subscribers[eventType], handler)
	log.Printf("Subscriber registered for event type: %s", eventType)
}

// Publish sends an event to all subscribers
func (eb *EventBus) Publish(event *Event) {
	eb.mu.RLock()
	defer eb.mu.RUnlock()
	
	if handlers, found := eb.subscribers[event.Type]; found {
		for _, handler := range handlers {
			go handler(event)
		}
		log.Printf("Event published: %s from %s to %s", event.Type, event.Source, event.Target)
	}
}
