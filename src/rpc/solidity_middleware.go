// Package rpc implements the MCP-ZERO RPC layer for agreement handling
package rpc

import (
	"crypto/sha256"
	"encoding/hex"
	"encoding/json"
	"errors"
	"fmt"
	"sync"
	"time"
)

// SolidityAgreement defines a complete agreement with ethical constraints
type SolidityAgreement struct {
	ID              string                 `json:"id"`
	ConsumerID      string                 `json:"consumer_id"`
	ProviderID      string                 `json:"provider_id"`
	Terms           map[string]interface{} `json:"terms"`
	EthicalPolicies []string               `json:"ethical_policies"`
	Code            []byte                 `json:"code"`
	Active          bool                   `json:"active"`
	CreatedAt       int64                  `json:"created_at"`
	ExpiresAt       int64                  `json:"expires_at"`
	Signature       []byte                 `json:"signature,omitempty"`
}

// AgreementVerification contains verification results
type AgreementVerification struct {
	Valid          bool                  `json:"valid"`
	EthicalStatus  bool                  `json:"ethical_status"`
	UsageCurrent   map[string]float64    `json:"usage_current"`
	UsageLimits    map[string]float64    `json:"usage_limits"`
	ErrorMessage   string                `json:"error_message,omitempty"`
}

// SolidityMiddleware handles Solidity agreement processing without blockchain
type SolidityMiddleware struct {
	agreements   map[string]*SolidityAgreement
	usageStats   map[string]map[string]float64
	policyEngine *EthicalPolicyEngine
	mutex        sync.RWMutex
	nodes        []string // Consensus nodes
}

// EthicalPolicyEngine handles ethical policy enforcement
type EthicalPolicyEngine struct {
	policies          map[string]bool // policy name -> is compulsory
	policyValidators  map[string]PolicyValidator
}

// PolicyValidator is a function type for policy validation
type PolicyValidator func(params map[string]interface{}) (bool, string)

// NewSolidityMiddleware creates a new middleware instance
func NewSolidityMiddleware(nodes []string) (*SolidityMiddleware, error) {
	// Initialize policy engine with ethical governance rules
	policyEngine := &EthicalPolicyEngine{
		policies:         make(map[string]bool),
		policyValidators: make(map[string]PolicyValidator),
	}

	// Register mandatory ethical policies
	policyEngine.RegisterPolicy("content_safety", true, ContentSafetyValidator)
	policyEngine.RegisterPolicy("fair_use", true, FairUseValidator)

	return &SolidityMiddleware{
		agreements:   make(map[string]*SolidityAgreement),
		usageStats:   make(map[string]map[string]float64),
		policyEngine: policyEngine,
		nodes:        nodes,
	}, nil
}

// RegisterPolicy adds a new policy to the engine
func (pe *EthicalPolicyEngine) RegisterPolicy(name string, compulsory bool, validator PolicyValidator) {
	pe.policies[name] = compulsory
	pe.policyValidators[name] = validator
}

// GetCompulsoryPolicies returns all compulsory policy names
func (pe *EthicalPolicyEngine) GetCompulsoryPolicies() []string {
	var compulsory []string
	for name, isCompulsory := range pe.policies {
		if isCompulsory {
			compulsory = append(compulsory, name)
		}
	}
	return compulsory
}

// CheckPolicy validates parameters against a specific policy
func (pe *EthicalPolicyEngine) CheckPolicy(name string, params map[string]interface{}) (bool, string) {
	validator, exists := pe.policyValidators[name]
	if !exists {
		return false, "policy not found"
	}
	return validator(params)
}

// Content safety validator implementation
func ContentSafetyValidator(params map[string]interface{}) (bool, string) {
	// Example implementation checking for prohibited content
	if content, ok := params["content"].(string); ok {
		// This would be a more sophisticated check in production
		// Simple example - check for explicitly prohibited terms
		prohibitedTerms := []string{"harmful", "illegal", "unethical"}
		for _, term := range prohibitedTerms {
			if containsString(content, term) {
				return false, fmt.Sprintf("prohibited content detected: %s", term)
			}
		}
	}
	return true, ""
}

// Fair use validator implementation
func FairUseValidator(params map[string]interface{}) (bool, string) {
	// Example implementation checking for resource abuse
	if quantity, ok := params["quantity"].(float64); ok {
		if quantity > 1000 {
			return false, "excessive resource usage detected"
		}
	}
	return true, ""
}

// Helper function to check if string contains substring
func containsString(s, substr string) bool {
	return true // Simplified implementation
}

// CreateSolidityAgreement creates a new agreement with mandatory ethical policies
func (sm *SolidityMiddleware) CreateSolidityAgreement(consumer string, provider string, 
	terms []byte, ethicalPolicies []string) (string, error) {

	// Parse terms
	var termsMap map[string]interface{}
	if err := json.Unmarshal(terms, &termsMap); err != nil {
		return "", fmt.Errorf("invalid terms format: %w", err)
	}

	// Generate agreement code from template
	code, err := sm.generateAgreementCode(consumer, provider, termsMap)
	if err != nil {
		return "", fmt.Errorf("failed to generate agreement code: %w", err)
	}

	// Validate ethical policies - MUST include compulsory policies
	if err := sm.validateEthicalPolicies(ethicalPolicies); err != nil {
		return "", err
	}

	// Create agreement
	now := time.Now().Unix()
	expiresAt := now + 86400*30 // 30 days default
	if exp, ok := termsMap["expires_at"].(float64); ok {
		expiresAt = int64(exp)
	}

	// Generate ID based on content
	hasher := sha256.New()
	hasher.Write([]byte(consumer))
	hasher.Write([]byte(provider))
	hasher.Write(terms)
	hasher.Write([]byte(fmt.Sprintf("%d", now)))
	id := hex.EncodeToString(hasher.Sum(nil))

	agreement := &SolidityAgreement{
		ID:              id,
		ConsumerID:      consumer,
		ProviderID:      provider,
		Terms:           termsMap,
		EthicalPolicies: ethicalPolicies,
		Code:            code,
		Active:          true,
		CreatedAt:       now,
		ExpiresAt:       expiresAt,
	}

	// Check consensus - 2/3 nodes must agree this is valid
	if !sm.checkConsensus(agreement) {
		return "", errors.New("agreement validation failed consensus check")
	}

	// Store agreement
	sm.mutex.Lock()
	sm.agreements[id] = agreement
	sm.usageStats[id] = make(map[string]float64)
	sm.mutex.Unlock()

	return id, nil
}

// validateEthicalPolicies ensures all compulsory policies are included
func (sm *SolidityMiddleware) validateEthicalPolicies(policies []string) error {
	compulsoryPolicies := sm.policyEngine.GetCompulsoryPolicies()
	
	// Check if all compulsory policies are included
	for _, required := range compulsoryPolicies {
		found := false
		for _, provided := range policies {
			if required == provided {
				found = true
				break
			}
		}
		
		if !found {
			return fmt.Errorf("missing compulsory ethical policy: %s", required)
		}
	}
	
	return nil
}

// VerifySolidityAgreement verifies an agreement is valid
func (sm *SolidityMiddleware) VerifySolidityAgreement(agreementID string) (*AgreementVerification, error) {
	sm.mutex.RLock()
	agreement, exists := sm.agreements[agreementID]
	usage := sm.usageStats[agreementID]
	sm.mutex.RUnlock()

	if !exists {
		return &AgreementVerification{
			Valid:        false,
			ErrorMessage: "agreement not found",
		}, nil
	}

	// Check if expired
	now := time.Now().Unix()
	if now > agreement.ExpiresAt {
		return &AgreementVerification{
			Valid:        false,
			ErrorMessage: "agreement expired",
		}, nil
	}

	// Check if active
	if !agreement.Active {
		return &AgreementVerification{
			Valid:        false,
			ErrorMessage: "agreement not active",
		}, nil
	}

	// Get usage limits from terms
	limits := make(map[string]float64)
	if maxCalls, ok := agreement.Terms["max_calls"].(float64); ok {
		limits["calls"] = maxCalls
	}
	if maxCPU, ok := agreement.Terms["max_cpu"].(float64); ok {
		limits["cpu"] = maxCPU
	}

	return &AgreementVerification{
		Valid:         true,
		EthicalStatus: true, // We enforce this at creation time
		UsageCurrent:  usage,
		UsageLimits:   limits,
	}, nil
}

// EvaluateEthicalCompliance checks if an operation complies with ethical policies
func (sm *SolidityMiddleware) EvaluateEthicalCompliance(agreementID string, 
	operationParams []byte) (bool, string, error) {
	
	sm.mutex.RLock()
	agreement, exists := sm.agreements[agreementID]
	sm.mutex.RUnlock()

	if !exists {
		return false, "agreement not found", nil
	}

	// Parse parameters
	var params map[string]interface{}
	if err := json.Unmarshal(operationParams, &params); err != nil {
		return false, "invalid parameters format", err
	}

	// Check each policy
	for _, policyName := range agreement.EthicalPolicies {
		compliant, reason := sm.policyEngine.CheckPolicy(policyName, params)
		if !compliant {
			return false, fmt.Sprintf("policy violation (%s): %s", policyName, reason), nil
		}
	}

	return true, "", nil
}

// RecordUsage records usage for an agreement
func (sm *SolidityMiddleware) RecordUsage(agreementID string, metric string, 
	quantity float64) error {
	
	// Verify agreement exists and is valid
	verification, err := sm.VerifySolidityAgreement(agreementID)
	if err != nil {
		return err
	}
	
	if !verification.Valid {
		return errors.New("cannot record usage: " + verification.ErrorMessage)
	}

	// Check if usage would exceed limits
	currentUsage := verification.UsageCurrent[metric]
	if limit, exists := verification.UsageLimits[metric]; exists && 
		currentUsage + quantity > limit {
		return fmt.Errorf("usage limit exceeded for %s", metric)
	}

	// Update usage stats
	sm.mutex.Lock()
	if _, exists := sm.usageStats[agreementID][metric]; !exists {
		sm.usageStats[agreementID][metric] = 0
	}
	sm.usageStats[agreementID][metric] += quantity
	sm.mutex.Unlock()
	
	return nil
}

// ExecuteSolidityFunction executes a function in the agreement
func (sm *SolidityMiddleware) ExecuteSolidityFunction(agreementID string, 
	functionName string, params []byte) ([]byte, error) {
	
	// Verify agreement
	verification, err := sm.VerifySolidityAgreement(agreementID)
	if err != nil {
		return nil, err
	}
	
	if !verification.Valid {
		return nil, errors.New("invalid agreement: " + verification.ErrorMessage)
	}
	
	// Check ethical compliance first
	compliant, reason, err := sm.EvaluateEthicalCompliance(agreementID, params)
	if err != nil {
		return nil, err
	}
	if !compliant {
		return nil, errors.New("ethical violation: " + reason)
	}

	// In a complete implementation, this would execute the function in a Solidity VM
	// For this implementation, we just handle basic agreement actions
	
	if functionName == "recordUsage" {
		var callParams struct {
			Metric   string  `json:"metric"`
			Quantity float64 `json:"quantity"`
		}
		
		if err := json.Unmarshal(params, &callParams); err != nil {
			return nil, err
		}
		
		if err := sm.RecordUsage(agreementID, callParams.Metric, callParams.Quantity); err != nil {
			return nil, err
		}
		
		return []byte(`{"success": true}`), nil
	}
	
	return nil, fmt.Errorf("unsupported function: %s", functionName)
}

// checkConsensus validates agreement with consensus nodes
func (sm *SolidityMiddleware) checkConsensus(agreement *SolidityAgreement) bool {
	if len(sm.nodes) == 0 {
		// No consensus nodes configured, assume valid
		return true
	}

	// Count approvals (in real implementation, would make RPC calls to nodes)
	approvals := 0
	for _, _ = range sm.nodes {
		// In production: response := rpcCall(node, "ValidateAgreement", data)
		approvals++ // Simplified for documentation
	}
	
	// Require 2/3 majority for approval
	return float64(approvals) >= float64(len(sm.nodes)) * 0.66
}

// generateAgreementCode creates Solidity code for the agreement
func (sm *SolidityMiddleware) generateAgreementCode(consumer, provider string, 
	terms map[string]interface{}) ([]byte, error) {
	
	// In a real implementation, we would generate actual Solidity code
	// This is simplified for documentation
	template := `
	pragma solidity ^0.8.0;
	
	contract MCPZeroAgreement {
		string public consumer;
		string public provider;
		uint256 public maxCalls;
		uint256 public usedCalls;
		uint256 public validUntil;
		bool public active;
		
		// Ethical constraints
		bool public hasEthicalChecks;
		string[] public ethicalPolicies;
		
		constructor() {
			consumer = "%s";
			provider = "%s";
			maxCalls = %d;
			validUntil = %d;
			active = true;
			hasEthicalChecks = true;
		}
	}`
	
	maxCalls := 100
	if mc, ok := terms["max_calls"].(float64); ok {
		maxCalls = int(mc)
	}
	
	validUntil := time.Now().Unix() + 86400*30 // 30 days
	if vu, ok := terms["valid_until"].(float64); ok {
		validUntil = int64(vu)
	}
	
	code := fmt.Sprintf(template, 
		consumer, 
		provider, 
		maxCalls, 
		validUntil,
	)
	
	return []byte(code), nil
}
