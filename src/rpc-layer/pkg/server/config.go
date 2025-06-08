package server

import (
	"fmt"
	"io/ioutil"
	"os"
	"path/filepath"
	"time"

	"go.uber.org/zap"
	"gopkg.in/yaml.v2" // Changed from yaml.v3 to yaml.v2 for better Go 1.13 compatibility
)

// Config defines the configuration for the MCP-ZERO RPC server
type Config struct {
	// Server configuration
	Server struct {
		// Host to bind to
		Host string `yaml:"host" default:"localhost"`
		// Port to listen on
		Port int `yaml:"port" default:"50051"`
		// Maximum concurrency (number of simultaneous requests)
		MaxConcurrency int `yaml:"maxConcurrency" default:"100"`
		// TLS configuration
		TLS struct {
			// Whether to enable TLS
			Enabled bool `yaml:"enabled" default:"false"`
			// Certificate file path
			CertFile string `yaml:"certFile"`
			// Key file path
			KeyFile string `yaml:"keyFile"`
		} `yaml:"tls"`
	} `yaml:"server"`

	// Hardware constraints
	Hardware struct {
		// Maximum CPU usage (percentage)
		MaxCPU float32 `yaml:"maxCpu" default:"30.0"`
		// Maximum memory usage (MB)
		MaxMemory uint32 `yaml:"maxMemory" default:"800"`
		// Metric reporting interval (seconds)
		MetricInterval int `yaml:"metricInterval" default:"5"`
	} `yaml:"hardware"`

	// Kernel configuration
	Kernel struct {
		// Path to kernel socket or IPC endpoint
		Endpoint string `yaml:"endpoint" default:"/tmp/mcp-kernel.sock"`
		// Connection timeout (milliseconds)
		Timeout int `yaml:"timeout" default:"5000"`
		// Maximum message size (bytes)
		MaxMessageSize int `yaml:"maxMessageSize" default:"4194304"` // 4MB
	} `yaml:"kernel"`

	// Logging configuration
	Logging struct {
		// Log level (debug, info, warn, error)
		Level string `yaml:"level" default:"info"`
		// Log file path (empty for stdout)
		File string `yaml:"file"`
		// Whether to use JSON format
		JSON bool `yaml:"json" default:"false"`
	} `yaml:"logging"`

	// Metrics configuration
	Metrics struct {
		// Whether to enable metrics
		Enabled bool `yaml:"enabled" default:"true"`
		// Port for Prometheus metrics
		Port int `yaml:"port" default:"9091"`
	} `yaml:"metrics"`

	// Plugin configuration
	Plugins struct {
		// Directory for plugin files
		Directory string `yaml:"directory" default:"./plugins"`
		// Whether to validate plugin signatures
		ValidateSignatures bool `yaml:"validateSignatures" default:"true"`
	} `yaml:"plugins"`
}

// LoadConfig loads configuration from a YAML file
func LoadConfig(path string) (*Config, error) {
	config := &Config{}

	// Set defaults
	config.Server.Host = "localhost"
	config.Server.Port = 50051
	config.Server.MaxConcurrency = 100
	config.Server.TLS.Enabled = false

	config.Hardware.MaxCPU = 30.0
	config.Hardware.MaxMemory = 800
	config.Hardware.MetricInterval = 5

	config.Kernel.Endpoint = "/tmp/mcp-kernel.sock"
	config.Kernel.Timeout = 5000
	config.Kernel.MaxMessageSize = 4194304 // 4MB

	config.Logging.Level = "info"
	config.Logging.JSON = false

	config.Metrics.Enabled = true
	config.Metrics.Port = 9091

	config.Plugins.Directory = "./plugins"
	config.Plugins.ValidateSignatures = true

	if path != "" {
		// Check if file exists
		if _, err := os.Stat(path); os.IsNotExist(err) {
			return nil, fmt.Errorf("config file not found: %s", path)
		}

		// Read file
		data, err := ioutil.ReadFile(path)
		if err != nil {
			return nil, fmt.Errorf("failed to read config file: %v", err)
		}

		// Parse YAML
		if err := yaml.Unmarshal(data, config); err != nil {
			return nil, fmt.Errorf("failed to parse config file: %v", err)
		}
	}

	// Override with environment variables
	if host := os.Getenv("MCP_RPC_HOST"); host != "" {
		config.Server.Host = host
	}

	if portStr := os.Getenv("MCP_RPC_PORT"); portStr != "" {
		if port, err := fmt.Sscanf(portStr, "%d", &config.Server.Port); err != nil {
			return nil, fmt.Errorf("invalid port: %s", portStr)
		} else if port < 0 || port > 65535 {
			return nil, fmt.Errorf("port out of range: %d", port)
		}
	}

	if cpuStr := os.Getenv("MCP_MAX_CPU"); cpuStr != "" {
		if _, err := fmt.Sscanf(cpuStr, "%f", &config.Hardware.MaxCPU); err != nil {
			return nil, fmt.Errorf("invalid CPU limit: %s", cpuStr)
		}
	}

	if memStr := os.Getenv("MCP_MAX_MEMORY"); memStr != "" {
		if _, err := fmt.Sscanf(memStr, "%d", &config.Hardware.MaxMemory); err != nil {
			return nil, fmt.Errorf("invalid memory limit: %s", memStr)
		}
	}

	if logLevel := os.Getenv("MCP_LOG_LEVEL"); logLevel != "" {
		config.Logging.Level = logLevel
	}

	// Create directories if they don't exist
	if config.Plugins.Directory != "" {
		if err := os.MkdirAll(config.Plugins.Directory, 0755); err != nil {
			return nil, fmt.Errorf("failed to create plugins directory: %v", err)
		}
	}

	return config, nil
}

// SaveConfig saves configuration to a YAML file
func (c *Config) SaveConfig(path string) error {
	// Create directory if it doesn't exist
	dir := filepath.Dir(path)
	if err := os.MkdirAll(dir, 0755); err != nil {
		return fmt.Errorf("failed to create directory: %v", err)
	}

	// Marshal to YAML
	data, err := yaml.Marshal(c)
	if err != nil {
		return fmt.Errorf("failed to marshal config: %v", err)
	}

	// Write to file
	if err := ioutil.WriteFile(path, data, 0644); err != nil {
		return fmt.Errorf("failed to write config file: %v", err)
	}

	return nil
}

// Configure logging based on configuration
func (c *Config) ConfigureLogging() (*zap.Logger, error) {
	// Create a logger configuration
	var cfg zap.Config
	if c.Logging.JSON {
		cfg = zap.NewProductionConfig()
	} else {
		cfg = zap.NewDevelopmentConfig()
	}

	// Set log level
	switch c.Logging.Level {
	case "debug":
		cfg.Level = zap.NewAtomicLevelAt(zap.DebugLevel)
	case "info":
		cfg.Level = zap.NewAtomicLevelAt(zap.InfoLevel)
	case "warn":
		cfg.Level = zap.NewAtomicLevelAt(zap.WarnLevel)
	case "error":
		cfg.Level = zap.NewAtomicLevelAt(zap.ErrorLevel)
	default:
		cfg.Level = zap.NewAtomicLevelAt(zap.InfoLevel)
	}

	// Set output file if specified
	if c.Logging.File != "" {
		cfg.OutputPaths = []string{c.Logging.File}
		cfg.ErrorOutputPaths = []string{c.Logging.File}
	}

	// Build logger
	logger, err := cfg.Build()
	if err != nil {
		return nil, fmt.Errorf("failed to build logger: %v", err)
	}

	// Add version and build info
	logger = logger.With(
		zap.String("version", "0.1.0"),
		zap.String("build_time", time.Now().Format(time.RFC3339)),
	)

	return logger, nil
}
