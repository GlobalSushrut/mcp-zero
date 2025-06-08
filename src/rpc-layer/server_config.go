// MCP-ZERO Server Configuration
// Compatible with Go 1.13
package main

import (
	"fmt"
	"io/ioutil"
	"log"

	"gopkg.in/yaml.v2"
)

// ServerConfig holds the configuration for the MCP-ZERO server
type ServerConfig struct {
	// Service ports
	AgentPort     int `yaml:"agent_port"`
	AuditPort     int `yaml:"audit_port"`
	LLMPort       int `yaml:"llm_port"`
	ConsensusPort int `yaml:"consensus_port"`
	MetricsPort   int `yaml:"metrics_port"`
	APIPort       int `yaml:"api_port"`
	
	// Database configuration
	MongoURI string `yaml:"mongo_uri"`
	
	// Hardware constraints
	MaxCPUPercent    float64 `yaml:"max_cpu_percent"`
	MaxMemoryMB      int     `yaml:"max_memory_mb"`
	AvgMemoryMB      int     `yaml:"avg_memory_mb"`
	
	// Security settings
	EnableTLS            bool   `yaml:"enable_tls"`
	TLSCertPath          string `yaml:"tls_cert_path"`
	TLSKeyPath           string `yaml:"tls_key_path"`
	EnableAuthentication bool   `yaml:"enable_authentication"`
	AuthSecret           string `yaml:"auth_secret"`
	
	// ZK and Solidity settings
	EnableZK             bool `yaml:"enable_zk"`
	EnableSolidity       bool `yaml:"enable_solidity"`
	EnableEthicsChecking bool `yaml:"enable_ethics_checking"`
	
	// Operational settings
	ShutdownTimeoutSecs int `yaml:"shutdown_timeout_secs"`
}

// DefaultConfig provides a default configuration
func DefaultConfig() ServerConfig {
	return ServerConfig{
		AgentPort:     50051,
		AuditPort:     50052,
		LLMPort:       50053,
		ConsensusPort: 50054,
		MetricsPort:   9090,
		APIPort:       8080,
		
		MongoURI: "mongodb://localhost:27017/mcp_zero",
		
		MaxCPUPercent: 27.0,
		MaxMemoryMB:   827,
		AvgMemoryMB:   640,
		
		EnableTLS:            false,
		EnableAuthentication: false,
		
		EnableZK:             true,
		EnableSolidity:       true,
		EnableEthicsChecking: true,
		
		ShutdownTimeoutSecs: 30,
	}
}

// LoadConfig loads configuration from a YAML file
func LoadConfig(configPath string) (ServerConfig, error) {
	config := DefaultConfig()
	
	// Read config file
	data, err := ioutil.ReadFile(configPath)
	if err != nil {
		log.Printf("Warning: Could not read config file: %v", err)
		log.Println("Using default configuration")
		return config, nil
	}
	
	// Parse YAML
	if err := yaml.Unmarshal(data, &config); err != nil {
		return config, fmt.Errorf("error parsing config file: %v", err)
	}
	
	// Enforce hardware constraints
	if config.MaxCPUPercent > 27.0 {
		log.Println("Warning: CPU usage constrained to 27% as per MCP-ZERO v7 specifications")
		config.MaxCPUPercent = 27.0
	}
	
	if config.MaxMemoryMB > 827 {
		log.Println("Warning: Memory usage constrained to 827MB as per MCP-ZERO v7 specifications")
		config.MaxMemoryMB = 827
	}
	
	return config, nil
}
