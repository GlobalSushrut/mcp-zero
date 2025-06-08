package server

import (
	"context"
	"sync"
	"time"

	"github.com/shirou/gopsutil/v3/cpu"
	"github.com/shirou/gopsutil/v3/mem"
	"github.com/shirou/gopsutil/v3/process"
	"go.uber.org/zap"
)

// ResourceMonitor monitors and enforces resource constraints
type ResourceMonitor struct {
	// Logger
	logger *zap.Logger

	// Maximum resource limits
	maxCPUPercent float32
	maxMemoryMB   uint32

	// Current resource usage
	currentCPUPercent float64
	currentMemoryMB   uint64

	// Mutex for synchronization
	mu sync.RWMutex

	// Channel for alerts
	alertCh chan ResourceAlert

	// Resource tracking window
	usageHistory []ResourceUsage

	// Monitor interval
	interval time.Duration

	// Last update timestamp
	lastUpdate time.Time
}

// ResourceUsage represents a point-in-time resource usage snapshot
type ResourceUsage struct {
	Timestamp   time.Time
	CPUPercent  float64
	MemoryUsage uint64
}

// ResourceAlert represents a resource constraint violation alert
type ResourceAlert struct {
	Type         string
	CurrentValue float64
	MaxValue     float64
	Message      string
	Timestamp    time.Time
}

// NewResourceMonitor creates a new resource monitor
func NewResourceMonitor(maxCPU float32, maxMemMB uint32, interval time.Duration) *ResourceMonitor {
	// Create logger
	logger, _ := zap.NewProduction()

	return &ResourceMonitor{
		logger:        logger,
		maxCPUPercent: maxCPU,
		maxMemoryMB:   maxMemMB,
		interval:      interval,
		alertCh:       make(chan ResourceAlert, 100),
		usageHistory:  make([]ResourceUsage, 0, 60), // Keep history for 60 intervals
		lastUpdate:    time.Now(),
	}
}

// Start begins resource monitoring
func (r *ResourceMonitor) Start(ctx context.Context) {
	r.logger.Info("Starting resource monitor",
		zap.Float32("maxCPU", r.maxCPUPercent),
		zap.Uint32("maxMemoryMB", r.maxMemoryMB))

	// Update resource usage immediately
	r.updateResourceUsage()

	// Start monitoring goroutine
	go r.monitorResources(ctx)

	// Start alert handler
	go r.handleAlerts(ctx)
}

// HasAvailableResources checks if resources are available
func (r *ResourceMonitor) HasAvailableResources() bool {
	r.mu.RLock()
	defer r.mu.RUnlock()

	// If it's been too long since the last update, update now
	if time.Since(r.lastUpdate) > r.interval*2 {
		r.mu.RUnlock()
		r.updateResourceUsage()
		r.mu.RLock()
	}

	return r.currentCPUPercent < float64(r.maxCPUPercent) &&
		r.currentMemoryMB < uint64(r.maxMemoryMB)
}

// GetUsage returns current resource usage
func (r *ResourceMonitor) GetUsage() (float64, uint64) {
	r.mu.RLock()
	defer r.mu.RUnlock()
	return r.currentCPUPercent, r.currentMemoryMB
}

// GetAverageUsage returns average resource usage over time
func (r *ResourceMonitor) GetAverageUsage(duration time.Duration) (float64, uint64) {
	r.mu.RLock()
	defer r.mu.RUnlock()

	// Calculate window based on duration
	cutoff := time.Now().Add(-duration)
	
	var cpuSum float64
	var memSum uint64
	var count int
	
	for i := len(r.usageHistory) - 1; i >= 0; i-- {
		usage := r.usageHistory[i]
		if usage.Timestamp.Before(cutoff) {
			break
		}
		
		cpuSum += usage.CPUPercent
		memSum += usage.MemoryUsage
		count++
	}
	
	if count == 0 {
		return r.currentCPUPercent, r.currentMemoryMB
	}
	
	return cpuSum / float64(count), memSum / uint64(count)
}

// MonitorResources continuously monitors system resources
func (r *ResourceMonitor) monitorResources(ctx context.Context) {
	ticker := time.NewTicker(r.interval)
	defer ticker.Stop()

	for {
		select {
		case <-ctx.Done():
			r.logger.Info("Stopping resource monitor")
			return
		case <-ticker.C:
			r.updateResourceUsage()
		}
	}
}

// updateResourceUsage updates current resource usage
func (r *ResourceMonitor) updateResourceUsage() {
	// Get current process
	proc, err := process.NewProcess(int32(process.GetCurrentPid()))
	if err != nil {
		r.logger.Error("Failed to get current process", zap.Error(err))
		return
	}

	// Get CPU usage
	cpuPercent, err := proc.CPUPercent()
	if err != nil {
		r.logger.Error("Failed to get CPU usage", zap.Error(err))
		return
	}

	// Get memory usage
	memInfo, err := proc.MemoryInfo()
	if err != nil {
		r.logger.Error("Failed to get memory usage", zap.Error(err))
		return
	}

	// Convert memory to MB
	memoryMB := memInfo.RSS / 1024 / 1024

	// Update state
	r.mu.Lock()
	r.currentCPUPercent = cpuPercent
	r.currentMemoryMB = memoryMB
	r.lastUpdate = time.Now()

	// Add to history
	r.usageHistory = append(r.usageHistory, ResourceUsage{
		Timestamp:   time.Now(),
		CPUPercent:  cpuPercent,
		MemoryUsage: memoryMB,
	})

	// Keep history limited to 60 entries
	if len(r.usageHistory) > 60 {
		r.usageHistory = r.usageHistory[len(r.usageHistory)-60:]
	}
	r.mu.Unlock()

	// Check for threshold violations
	r.checkThresholds(cpuPercent, memoryMB)
}

// CheckThresholds checks for resource threshold violations
func (r *ResourceMonitor) checkThresholds(cpuPercent float64, memoryMB uint64) {
	// Check CPU usage
	if cpuPercent > float64(r.maxCPUPercent) {
		r.alertCh <- ResourceAlert{
			Type:         "CPU",
			CurrentValue: cpuPercent,
			MaxValue:     float64(r.maxCPUPercent),
			Message:      "CPU usage exceeded threshold",
			Timestamp:    time.Now(),
		}
	}

	// Check memory usage
	if memoryMB > uint64(r.maxMemoryMB) {
		r.alertCh <- ResourceAlert{
			Type:         "Memory",
			CurrentValue: float64(memoryMB),
			MaxValue:     float64(r.maxMemoryMB),
			Message:      "Memory usage exceeded threshold",
			Timestamp:    time.Now(),
		}
	}
}

// handleAlerts processes resource alerts
func (r *ResourceMonitor) handleAlerts(ctx context.Context) {
	for {
		select {
		case <-ctx.Done():
			return
		case alert := <-r.alertCh:
			r.logger.Warn("Resource threshold exceeded",
				zap.String("type", alert.Type),
				zap.Float64("current", alert.CurrentValue),
				zap.Float64("max", alert.MaxValue),
				zap.String("message", alert.Message))

			// In a more comprehensive implementation, we could trigger
			// resource reduction strategies here, such as:
			// 1. Pausing non-essential agents
			// 2. Reducing resource allocations for lower priority tasks
			// 3. Triggering garbage collection
			// 4. Notifying external monitoring systems
		}
	}
}

// GenerateReport generates a resource usage report
func (r *ResourceMonitor) GenerateReport() map[string]interface{} {
	r.mu.RLock()
	defer r.mu.RUnlock()

	// Get system-wide stats as well
	cpuPercent, _ := cpu.Percent(0, false)
	memInfo, _ := mem.VirtualMemory()

	// Calculate averages
	cpuAvg, memAvgMB := r.GetAverageUsage(5 * time.Minute)

	// Build report
	report := map[string]interface{}{
		"timestamp": time.Now().Format(time.RFC3339),
		"process": map[string]interface{}{
			"cpu_percent":    r.currentCPUPercent,
			"memory_mb":      r.currentMemoryMB,
			"cpu_avg_5m":     cpuAvg,
			"memory_avg_5m":  memAvgMB,
			"cpu_limit":      r.maxCPUPercent,
			"memory_limit":   r.maxMemoryMB,
			"cpu_percent_of_limit": r.currentCPUPercent / float64(r.maxCPUPercent) * 100,
			"memory_percent_of_limit": float64(r.currentMemoryMB) / float64(r.maxMemoryMB) * 100,
		},
		"system": map[string]interface{}{
			"total_cpu_percent": 0.0,
			"total_memory_mb":   memInfo.Total / 1024 / 1024,
			"used_memory_mb":    memInfo.Used / 1024 / 1024,
			"memory_percent":    memInfo.UsedPercent,
		},
	}

	// Add system CPU if available
	if len(cpuPercent) > 0 {
		report["system"].(map[string]interface{})["total_cpu_percent"] = cpuPercent[0]
	}

	return report
}
