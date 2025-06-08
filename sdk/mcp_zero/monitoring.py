"""
MCP-ZERO SDK: Resource Monitoring Module

This module provides utilities for monitoring and controlling resource usage
to ensure compliance with MCP-ZERO's strict hardware constraints:
- CPU: <27% on a single core
- Memory: <827MB peak

The monitoring system includes trend analysis and predictive throttling
to maintain resource constraints even during operation spikes.
"""

import os
import time
import logging
import threading
import gc
from typing import Dict, Any, Optional, List, Callable
import contextlib

try:
    import psutil
except ImportError:
    psutil = None

# Configure logging
logger = logging.getLogger("mcp_zero")

# Constants
DEFAULT_CPU_LIMIT = 27.0  # Default CPU limit (%)
DEFAULT_MEMORY_LIMIT = 827  # Default memory limit (MB)
CPU_WARNING_THRESHOLD = 20.0  # CPU warning threshold (%)
MEMORY_WARNING_THRESHOLD = 700  # Memory warning threshold (MB)
SAMPLING_INTERVAL = 1.0  # Resource sampling interval (seconds)
TREND_WINDOW = 5  # Number of samples to use for trend analysis
THROTTLE_FACTOR = 0.8  # Factor to reduce operations when throttling
CPU_BUDGET_REFILL_RATE = 5.0  # CPU budget refill rate per second (%)


class ResourceMonitor:
    """
    Monitors and controls resource usage to ensure compliance with
    MCP-ZERO's hardware constraints.
    
    Features:
    - Real-time CPU and memory monitoring
    - Trend analysis and predictive throttling
    - CPU budget enforcement
    - Automatic garbage collection
    - Resource usage logging
    """
    
    def __init__(self, cpu_limit: float = DEFAULT_CPU_LIMIT, memory_limit: float = DEFAULT_MEMORY_LIMIT):
        """
        Initialize the resource monitor.
        
        Args:
            cpu_limit: Maximum CPU usage percentage (0-100)
            memory_limit: Maximum memory usage in MB
        """
        self.cpu_limit = cpu_limit
        self.memory_limit = memory_limit
        self._monitoring_thread = None
        self._stop_event = threading.Event()
        self._cpu_samples: List[float] = []
        self._memory_samples: List[float] = []
        self._lock = threading.Lock()
        self._cpu_budget = 100.0  # Start with full CPU budget
        self._last_budget_update = time.time()
        self._last_gc_time = 0
        self._operation_count = 0
        
        # Check for psutil availability
        self._has_psutil = psutil is not None
        if not self._has_psutil:
            logger.warning(
                "psutil not available. Resource monitoring will be limited. "
                "Install with 'pip install mcp-zero[monitoring]'"
            )
        
        # Set process priority if possible
        self._set_process_priority()
    
    def start_monitoring(self) -> None:
        """Start the resource monitoring thread"""
        if self._monitoring_thread is not None and self._monitoring_thread.is_alive():
            return  # Already monitoring
            
        self._stop_event.clear()
        self._monitoring_thread = threading.Thread(
            target=self._monitor_resources,
            daemon=True,
            name="MCP-ResourceMonitor"
        )
        self._monitoring_thread.start()
        logger.debug("Resource monitoring started")
    
    def stop_monitoring(self) -> None:
        """Stop the resource monitoring thread"""
        if self._monitoring_thread is None or not self._monitoring_thread.is_alive():
            return  # Not monitoring
            
        self._stop_event.set()
        self._monitoring_thread.join(timeout=2.0)
        self._monitoring_thread = None
        logger.debug("Resource monitoring stopped")
    
    def get_cpu_percent(self) -> float:
        """
        Get the current CPU usage percentage.
        
        Returns:
            Current CPU usage as a percentage (0-100)
        """
        if not self._has_psutil:
            return 0.0
            
        try:
            # Get process-specific CPU usage
            process = psutil.Process(os.getpid())
            return process.cpu_percent(interval=0.1)
        except Exception as e:
            logger.warning(f"Failed to get CPU usage: {str(e)}")
            return 0.0
    
    def get_memory_mb(self) -> float:
        """
        Get the current memory usage in MB.
        
        Returns:
            Current memory usage in MB
        """
        if not self._has_psutil:
            return 0.0
            
        try:
            # Get process-specific memory usage
            process = psutil.Process(os.getpid())
            mem_info = process.memory_info()
            return mem_info.rss / (1024 * 1024)  # Convert bytes to MB
        except Exception as e:
            logger.warning(f"Failed to get memory usage: {str(e)}")
            return 0.0
    
    def check_available_resources(self) -> bool:
        """
        Check if there are enough resources available for an operation.
        
        Returns:
            True if resources are available, False otherwise
        """
        cpu_percent = self.get_cpu_percent()
        memory_mb = self.get_memory_mb()
        
        # Always allow if monitoring is not available
        if not self._has_psutil:
            return True
            
        # Check against limits
        if cpu_percent >= self.cpu_limit:
            logger.warning(
                f"CPU usage ({cpu_percent:.1f}%) exceeds limit ({self.cpu_limit:.1f}%)"
            )
            return False
            
        if memory_mb >= self.memory_limit:
            logger.warning(
                f"Memory usage ({memory_mb:.1f}MB) exceeds limit ({self.memory_limit:.1f}MB)"
            )
            return False
        
        # Check CPU budget
        with self._lock:
            if self._cpu_budget <= 0:
                logger.warning("CPU budget exhausted, need to wait for refill")
                return False
        
        return True
    
    @contextlib.contextmanager
    def track_operation(self, operation_name: str):
        """
        Context manager to track resource usage during an operation.
        
        Args:
            operation_name: Name of the operation being performed
        
        Yields:
            None
        """
        start_time = time.time()
        start_cpu = self.get_cpu_percent()
        start_memory = self.get_memory_mb()
        
        # Increment operation count
        with self._lock:
            self._operation_count += 1
        
        # Check if we need garbage collection
        self._maybe_collect_garbage()
        
        try:
            # Throttle if needed based on trend analysis
            self._maybe_throttle()
            
            # Deduct from CPU budget
            self._update_cpu_budget(-5.0)  # Deduct initial budget cost
            
            yield
            
        finally:
            # Calculate resource usage
            elapsed = time.time() - start_time
            end_cpu = self.get_cpu_percent()
            end_memory = self.get_memory_mb()
            
            cpu_change = end_cpu - start_cpu
            memory_change = end_memory - start_memory
            
            # Log resource usage
            logger.debug(
                f"Operation '{operation_name}' used {cpu_change:.1f}% CPU, "
                f"{memory_change:.1f}MB memory, took {elapsed:.3f}s"
            )
            
            # Deduct from CPU budget based on actual usage
            self._update_cpu_budget(-max(0, cpu_change))
            
            # Decrement operation count
            with self._lock:
                self._operation_count -= 1
    
    def _monitor_resources(self) -> None:
        """Background thread that monitors resource usage"""
        while not self._stop_event.is_set():
            try:
                # Get current resource usage
                cpu_percent = self.get_cpu_percent()
                memory_mb = self.get_memory_mb()
                
                # Store samples
                with self._lock:
                    self._cpu_samples.append(cpu_percent)
                    self._memory_samples.append(memory_mb)
                    
                    # Keep only the last TREND_WINDOW samples
                    if len(self._cpu_samples) > TREND_WINDOW:
                        self._cpu_samples.pop(0)
                    if len(self._memory_samples) > TREND_WINDOW:
                        self._memory_samples.pop(0)
                
                # Refill CPU budget
                self._update_cpu_budget(CPU_BUDGET_REFILL_RATE)
                
                # Log warnings if approaching limits
                if cpu_percent >= CPU_WARNING_THRESHOLD:
                    logger.warning(
                        f"CPU usage is high: {cpu_percent:.1f}% "
                        f"(limit: {self.cpu_limit:.1f}%)"
                    )
                    
                if memory_mb >= MEMORY_WARNING_THRESHOLD:
                    logger.warning(
                        f"Memory usage is high: {memory_mb:.1f}MB "
                        f"(limit: {self.memory_limit:.1f}MB)"
                    )
                    
                    # Force garbage collection if memory is high
                    self._force_garbage_collection()
                
            except Exception as e:
                logger.error(f"Error in resource monitoring: {str(e)}")
            
            # Wait for the next sampling interval
            time.sleep(SAMPLING_INTERVAL)
    
    def _update_cpu_budget(self, change: float) -> None:
        """
        Update the CPU budget.
        
        Args:
            change: Amount to change the budget (positive or negative)
        """
        with self._lock:
            current_time = time.time()
            elapsed = current_time - self._last_budget_update
            self._last_budget_update = current_time
            
            # Add refill amount based on elapsed time
            if change > 0:
                # This is a refill
                refill = change * elapsed
                self._cpu_budget = min(100.0, self._cpu_budget + refill)
            else:
                # This is a deduction
                self._cpu_budget = max(0.0, self._cpu_budget + change)
    
    def _maybe_throttle(self) -> None:
        """Apply throttling if resource trends indicate potential limits breach"""
        with self._lock:
            # Skip if not enough samples
            if len(self._cpu_samples) < 2:
                return
                
            # Calculate CPU trend
            cpu_trend = self._calculate_trend(self._cpu_samples)
            
            # If trend is increasing and approaching limit, throttle
            if cpu_trend > 0 and self._cpu_samples[-1] > 0.7 * self.cpu_limit:
                # Calculate throttle delay based on current usage and trend
                proximity_to_limit = self._cpu_samples[-1] / self.cpu_limit
                throttle_delay = proximity_to_limit * THROTTLE_FACTOR
                
                if throttle_delay > 0.01:  # Only throttle if delay is significant
                    logger.debug(
                        f"Throttling operations due to CPU trend: {cpu_trend:.2f}, "
                        f"current: {self._cpu_samples[-1]:.1f}%, "
                        f"sleeping for {throttle_delay:.2f}s"
                    )
                    time.sleep(throttle_delay)
    
    def _calculate_trend(self, samples: List[float]) -> float:
        """
        Calculate the trend in a series of samples.
        
        Args:
            samples: List of numeric samples
            
        Returns:
            Trend value (positive for increasing, negative for decreasing)
        """
        if len(samples) < 2:
            return 0.0
            
        # Simple linear trend calculation
        return (samples[-1] - samples[0]) / len(samples)
    
    def _maybe_collect_garbage(self) -> None:
        """Run garbage collection if needed"""
        now = time.time()
        
        # Check if we need to run garbage collection
        with self._lock:
            high_operation_count = self._operation_count > 10
            time_since_last_gc = now - self._last_gc_time
            
            # Run GC if many operations or it's been a while
            if high_operation_count and time_since_last_gc > 30:
                self._force_garbage_collection()
    
    def _force_garbage_collection(self) -> None:
        """Force a garbage collection cycle"""
        try:
            pre_memory = self.get_memory_mb()
            
            # Run garbage collection
            gc.collect()
            
            # Update last GC time
            with self._lock:
                self._last_gc_time = time.time()
            
            post_memory = self.get_memory_mb()
            memory_freed = max(0, pre_memory - post_memory)
            
            logger.debug(f"Garbage collection freed {memory_freed:.1f}MB")
            
        except Exception as e:
            logger.warning(f"Error during garbage collection: {str(e)}")
    
    def _set_process_priority(self) -> None:
        """Set process priority to reduce CPU contention"""
        if not self._has_psutil:
            return
            
        try:
            process = psutil.Process(os.getpid())
            
            # Set CPU affinity if possible (limit to specific cores)
            if hasattr(process, "cpu_affinity"):
                # Try to use just one CPU for minimal resource usage
                try:
                    process.cpu_affinity([0])
                    logger.debug("Set CPU affinity to core 0")
                except Exception:
                    # If setting specific core fails, don't change affinity
                    pass
                
            # Set below normal priority
            if os.name == 'nt':  # Windows
                process.nice(psutil.BELOW_NORMAL_PRIORITY_CLASS)
            else:  # Unix/Linux
                process.nice(10)  # Higher nice value = lower priority
                
            logger.debug("Set process to lower priority")
            
        except Exception as e:
            logger.warning(f"Failed to set process priority: {str(e)}")
            
    def __del__(self):
        """Cleanup when the monitor is garbage collected"""
        self.stop_monitoring()
