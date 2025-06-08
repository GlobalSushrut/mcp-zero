package server

import (
	"context"
	"fmt"
	"net"
	"sync"
	"time"

	"github.com/prometheus/client_golang/prometheus"
	"github.com/prometheus/client_golang/prometheus/promhttp"
	"github.com/shirou/gopsutil/cpu"
	"github.com/shirou/gopsutil/mem"
	"go.uber.org/zap"
	"google.golang.org/grpc"
	"google.golang.org/grpc/credentials"
	"google.golang.org/grpc/health"
	healthpb "google.golang.org/grpc/health/grpc_health_v1"
	"google.golang.org/grpc/reflection"
	
	"net/http"
)

// RPCServer represents the MCP-ZERO RPC server
type RPCServer struct {
	// Configuration
	config *Config
	
	// Logger
	logger *zap.Logger
	
	// gRPC server
	grpcServer *grpc.Server
	
	// Health check service
	healthServer *health.Server
	
	// Metrics server
	metricsServer *http.Server
	
	// Agent connectivity
	kernelClient KernelClient
	
	// Resource monitoring
	resourceMonitor *ResourceMonitor
	
	// Shutdown context
	ctx    context.Context
	cancel context.CancelFunc
	
	// Mutex for concurrency control
	mu sync.Mutex
	
	// Metrics
	metrics *serverMetrics
}

// KernelClient interface for communication with the kernel
type KernelClient interface {
	Connect() error
	Disconnect() error
	IsConnected() bool
	ExecuteCommand(cmd string, args map[string]interface{}) (interface{}, error)
}

// NewRPCServer creates a new RPC server
func NewRPCServer(config *Config) (*RPCServer, error) {
	// Create logger
	logger, err := config.ConfigureLogging()
	if err != nil {
		return nil, fmt.Errorf("failed to configure logging: %v", err)
	}
	
	// Create contexts for graceful shutdown
	ctx, cancel := context.WithCancel(context.Background())
	
	// Initialize metrics
	metrics := newServerMetrics()
	
	// Create resource monitor
	resourceMonitor := NewResourceMonitor(config.Hardware.MaxCPU, config.Hardware.MaxMemory, 
		time.Duration(config.Hardware.MetricInterval)*time.Second)
	
	server := &RPCServer{
		config:         config,
		logger:         logger,
		ctx:            ctx,
		cancel:         cancel,
		healthServer:   health.NewServer(),
		resourceMonitor: resourceMonitor,
		metrics:        metrics,
	}
	
	return server, nil
}

// Start starts the RPC server
func (s *RPCServer) Start() error {
	s.logger.Info("Starting MCP-ZERO RPC server",
		zap.String("host", s.config.Server.Host),
		zap.Int("port", s.config.Server.Port))
		
	// Start metrics server if enabled
	if s.config.Metrics.Enabled {
		if err := s.startMetricsServer(); err != nil {
			return fmt.Errorf("failed to start metrics server: %v", err)
		}
	}
	
	// Register Prometheus metrics
	prometheus.MustRegister(s.metrics.requestCounter)
	prometheus.MustRegister(s.metrics.requestLatency)
	prometheus.MustRegister(s.metrics.activeConnections)
	prometheus.MustRegister(s.metrics.cpuUsage)
	prometheus.MustRegister(s.metrics.memoryUsage)
	
	// Start resource monitor
	s.resourceMonitor.Start(s.ctx)
	
	// Create listener
	addr := fmt.Sprintf("%s:%d", s.config.Server.Host, s.config.Server.Port)
	lis, err := net.Listen("tcp", addr)
	if err != nil {
		return fmt.Errorf("failed to listen on %s: %v", addr, err)
	}
	
	// Create server options
	var opts []grpc.ServerOption
	
	// Configure TLS if enabled
	if s.config.Server.TLS.Enabled {
		creds, err := credentials.NewServerTLSFromFile(
			s.config.Server.TLS.CertFile,
			s.config.Server.TLS.KeyFile,
		)
		if err != nil {
			return fmt.Errorf("failed to load TLS credentials: %v", err)
		}
		opts = append(opts, grpc.Creds(creds))
	}
	
	// Add resource monitoring interceptor
	opts = append(opts, grpc.UnaryInterceptor(s.resourceInterceptor))
	
	// Create gRPC server
	s.grpcServer = grpc.NewServer(opts...)
	
	// Register services
	s.registerServices()
	
	// Register health service
	healthpb.RegisterHealthServer(s.grpcServer, s.healthServer)
	s.healthServer.SetServingStatus("mcp.MCPAgentService", healthpb.HealthCheckResponse_SERVING)
	
	// Enable reflection for grpcurl and other tools
	reflection.Register(s.grpcServer)
	
	// Start server
	s.logger.Info("Server listening", zap.String("address", addr))
	go func() {
		if err := s.grpcServer.Serve(lis); err != nil {
			s.logger.Error("Server error", zap.Error(err))
		}
	}()
	
	return nil
}

// Stop stops the RPC server
func (s *RPCServer) Stop() {
	s.logger.Info("Stopping MCP-ZERO RPC server")
	
	// Cancel context
	s.cancel()
	
	// Stop metrics server
	if s.metricsServer != nil {
		ctx, cancel := context.WithTimeout(context.Background(), 5*time.Second)
		defer cancel()
		s.metricsServer.Shutdown(ctx)
	}
	
	// Graceful stop gRPC server
	s.grpcServer.GracefulStop()
	
	s.logger.Info("Server stopped")
	
	// Sync logger
	_ = s.logger.Sync()
}

// startMetricsServer starts the Prometheus metrics server
func (s *RPCServer) startMetricsServer() error {
	metricsAddr := fmt.Sprintf("%s:%d", s.config.Server.Host, s.config.Metrics.Port)
	
	// Create HTTP handler
	mux := http.NewServeMux()
	mux.Handle("/metrics", promhttp.Handler())
	mux.HandleFunc("/health", func(w http.ResponseWriter, r *http.Request) {
		w.WriteHeader(http.StatusOK)
		w.Write([]byte("OK"))
	})
	
	// Create HTTP server
	s.metricsServer = &http.Server{
		Addr:    metricsAddr,
		Handler: mux,
	}
	
	// Start server
	go func() {
		s.logger.Info("Starting metrics server", zap.String("address", metricsAddr))
		if err := s.metricsServer.ListenAndServe(); err != http.ErrServerClosed {
			s.logger.Error("Metrics server error", zap.Error(err))
		}
	}()
	
	return nil
}

// registerServices registers all gRPC services
func (s *RPCServer) registerServices() {
	// Register services here
	// Example:
	// mcp.RegisterMCPAgentServiceServer(s.grpcServer, NewAgentService(s.kernelClient, s.logger))
	// mcp.RegisterMCPHardwareServiceServer(s.grpcServer, NewHardwareService(s.resourceMonitor, s.logger))
	// mcp.RegisterMCPPluginServiceServer(s.grpcServer, NewPluginService(s.config.Plugins.Directory, s.logger))
}

// resourceInterceptor is a gRPC interceptor for resource monitoring and limiting
func (s *RPCServer) resourceInterceptor(ctx context.Context, req interface{}, 
	info *grpc.UnaryServerInfo, handler grpc.UnaryHandler) (interface{}, error) {
	
	// Check resource limits before processing
	if !s.resourceMonitor.HasAvailableResources() {
		s.logger.Warn("Request rejected due to resource constraints",
			zap.String("method", info.FullMethod))
		return nil, fmt.Errorf("server resource limits exceeded, try again later")
	}
	
	// Increment active connections
	s.metrics.activeConnections.Inc()
	defer s.metrics.activeConnections.Dec()
	
	// Record request metrics
	s.metrics.requestCounter.WithLabelValues(info.FullMethod).Inc()
	
	// Record latency
	startTime := time.Now()
	resp, err := handler(ctx, req)
	latency := time.Since(startTime).Seconds()
	s.metrics.requestLatency.WithLabelValues(info.FullMethod).Observe(latency)
	
	// Update resource usage metrics
	cpuUsage, _ := cpu.Percent(0, false)
	memInfo, _ := mem.VirtualMemory()
	
	if len(cpuUsage) > 0 {
		s.metrics.cpuUsage.Set(cpuUsage[0])
	}
	s.metrics.memoryUsage.Set(float64(memInfo.Used) / 1024 / 1024)
	
	return resp, err
}

// serverMetrics contains Prometheus metrics
type serverMetrics struct {
	requestCounter    *prometheus.CounterVec
	requestLatency    *prometheus.HistogramVec
	activeConnections prometheus.Gauge
	cpuUsage          prometheus.Gauge
	memoryUsage       prometheus.Gauge
}

// newServerMetrics creates new server metrics
func newServerMetrics() *serverMetrics {
	return &serverMetrics{
		requestCounter: prometheus.NewCounterVec(
			prometheus.CounterOpts{
				Name: "mcp_rpc_requests_total",
				Help: "Total number of RPC requests",
			},
			[]string{"method"},
		),
		requestLatency: prometheus.NewHistogramVec(
			prometheus.HistogramOpts{
				Name:    "mcp_rpc_request_latency_seconds",
				Help:    "RPC request latency in seconds",
				Buckets: prometheus.DefBuckets,
			},
			[]string{"method"},
		),
		activeConnections: prometheus.NewGauge(
			prometheus.GaugeOpts{
				Name: "mcp_rpc_active_connections",
				Help: "Number of active connections",
			},
		),
		cpuUsage: prometheus.NewGauge(
			prometheus.GaugeOpts{
				Name: "mcp_rpc_cpu_usage_percent",
				Help: "CPU usage percentage",
			},
		),
		memoryUsage: prometheus.NewGauge(
			prometheus.GaugeOpts{
				Name: "mcp_rpc_memory_usage_mb",
				Help: "Memory usage in MB",
			},
		),
	}
}
