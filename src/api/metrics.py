"""
Resilient Metrics Collector for MCP Zero

This module implements a resilient metrics collector that can operate
in both online and offline modes, following the same pattern as the
successful DBMemoryTree and Traffic Agent improvements.
"""

import os
import time
import json
import logging
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable

logger = logging.getLogger("mcp_zero.metrics")

class MetricType(Enum):
    """Types of metrics that can be collected."""
    COUNTER = "counter"
    GAUGE = "gauge"
    HISTOGRAM = "histogram"


class MetricsMode(Enum):
    """Operating modes for metrics collection."""
    ONLINE = "online"
    OFFLINE = "offline"


class Metric:
    """Base class for metrics."""
    
    def __init__(self, name: str, description: str, metric_type: MetricType):
        """
        Initialize a metric.
        
        Args:
            name: Metric name
            description: Metric description
            metric_type: Type of metric
        """
        self.name = name
        self.description = description
        self.type = metric_type
        self.labels = {}
    
    def with_labels(self, **labels) -> 'Metric':
        """
        Create a new metric instance with the specified labels.
        
        Args:
            **labels: Label key-value pairs
            
        Returns:
            New metric instance with labels
        """
        instance = self.__class__(self.name, self.description)
        instance.labels = labels
        return instance


class Counter(Metric):
    """Counter metric that only increases."""
    
    def __init__(self, name: str, description: str):
        """Initialize counter with 0 value."""
        super().__init__(name, description, MetricType.COUNTER)
        self.value = 0
    
    def inc(self, value: float = 1.0) -> None:
        """
        Increment counter by value.
        
        Args:
            value: Amount to increment (default: 1.0)
        """
        if value < 0:
            logger.warning(f"Counter {self.name} received negative increment: {value}")
            return
            
        self.value += value


class Gauge(Metric):
    """Gauge metric that can increase or decrease."""
    
    def __init__(self, name: str, description: str):
        """Initialize gauge with 0 value."""
        super().__init__(name, description, MetricType.GAUGE)
        self.value = 0
    
    def set(self, value: float) -> None:
        """
        Set gauge to value.
        
        Args:
            value: New gauge value
        """
        self.value = value
    
    def inc(self, value: float = 1.0) -> None:
        """
        Increment gauge by value.
        
        Args:
            value: Amount to increment (default: 1.0)
        """
        self.value += value
    
    def dec(self, value: float = 1.0) -> None:
        """
        Decrement gauge by value.
        
        Args:
            value: Amount to decrement (default: 1.0)
        """
        self.value -= value


class MetricsCollector:
    """
    Resilient metrics collector that gracefully handles connection issues.
    
    This collector will start in offline mode by default and attempt to
    connect to the metrics endpoint. If connection fails, it will remain
    in offline mode, storing data locally for later transmission.
    """
    
    def __init__(
        self,
        component_name: str,
        endpoint: Optional[str] = None,
        offline_dir: str = "/var/lib/mcp-zero/metrics"
    ):
        """
        Initialize metrics collector.
        
        Args:
            component_name: Name of the component
            endpoint: Metrics endpoint URL (None for offline only)
            offline_dir: Directory for offline metrics storage
        """
        self.component_name = component_name
        self.endpoint = endpoint
        self.offline_dir = offline_dir
        self.metrics = {}
        
        # Start in offline mode by default (like DBMemoryTree)
        self.mode = MetricsMode.OFFLINE
        
        # Ensure storage directory exists
        if not os.path.exists(offline_dir):
            os.makedirs(offline_dir, exist_ok=True)
            
        # Try to connect if endpoint provided
        if endpoint:
            self._try_connect()
        
        logger.info(
            f"Metrics collector initialized for {component_name} in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to metrics endpoint.
        
        Like the Traffic Agent's acceleration server connection, this will
        only try once and then remain in the determined mode.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.endpoint:
            return False
            
        try:
            # Simple connection test
            import requests
            response = requests.get(
                f"{self.endpoint}/health",
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = MetricsMode.ONLINE
                logger.info(f"Connected to metrics endpoint: {self.endpoint}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to metrics endpoint: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to metrics endpoint: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def counter(self, name: str, description: str) -> Counter:
        """
        Create or get a counter metric.
        
        Args:
            name: Metric name
            description: Metric description
            
        Returns:
            Counter metric
        """
        full_name = f"{self.component_name}_{name}"
        
        if full_name not in self.metrics:
            self.metrics[full_name] = Counter(full_name, description)
            
        return self.metrics[full_name]
    
    def gauge(self, name: str, description: str) -> Gauge:
        """
        Create or get a gauge metric.
        
        Args:
            name: Metric name
            description: Metric description
            
        Returns:
            Gauge metric
        """
        full_name = f"{self.component_name}_{name}"
        
        if full_name not in self.metrics:
            self.metrics[full_name] = Gauge(full_name, description)
            
        return self.metrics[full_name]
            
    def collect(self) -> Dict[str, Any]:
        """
        Collect all metrics.
        
        Returns:
            Dictionary of metrics data
        """
        data = {
            "component": self.component_name,
            "timestamp": time.time(),
            "metrics": {}
        }
        
        for name, metric in self.metrics.items():
            data["metrics"][name] = {
                "type": metric.type.value,
                "description": metric.description,
                "value": metric.value,
                "labels": metric.labels
            }
            
        return data
    
    def export(self) -> bool:
        """
        Export metrics to endpoint or local storage.
        
        Returns:
            True if export successful, False otherwise
        """
        data = self.collect()
        
        if self.mode == MetricsMode.ONLINE:
            return self._export_online(data)
        else:
            return self._export_offline(data)
    
    def _export_online(self, data: Dict[str, Any]) -> bool:
        """
        Export metrics to online endpoint.
        
        Args:
            data: Metrics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            response = requests.post(
                self.endpoint,
                json=data,
                timeout=2.0
            )
            
            return response.status_code == 200
            
        except Exception as e:
            logger.warning(f"Failed to export metrics online: {str(e)}")
            # Fallback to offline mode
            self.mode = MetricsMode.OFFLINE
            return self._export_offline(data)
    
    def _export_offline(self, data: Dict[str, Any]) -> bool:
        """
        Export metrics to offline storage.
        
        Args:
            data: Metrics data
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(time.time())
            filepath = f"{self.offline_dir}/{self.component_name}_{timestamp}.json"
            
            with open(filepath, 'w') as f:
                json.dump(data, f)
                
            return True
            
        except Exception as e:
            logger.error(f"Failed to export metrics offline: {str(e)}")
            return False


# Create default metrics collector for easy import
default_collector = None


def init(component_name: str, endpoint: Optional[str] = None) -> MetricsCollector:
    """
    Initialize default metrics collector.
    
    Args:
        component_name: Component name
        endpoint: Metrics endpoint
        
    Returns:
        Metrics collector instance
    """
    global default_collector
    default_collector = MetricsCollector(component_name, endpoint)
    return default_collector


def counter(name: str, description: str) -> Counter:
    """Get a counter from the default collector."""
    if default_collector is None:
        raise RuntimeError("Metrics not initialized")
    return default_collector.counter(name, description)


def gauge(name: str, description: str) -> Gauge:
    """Get a gauge from the default collector."""
    if default_collector is None:
        raise RuntimeError("Metrics not initialized")
    return default_collector.gauge(name, description)


def export() -> bool:
    """Export metrics from the default collector."""
    if default_collector is None:
        return False
    return default_collector.export()


# Decorator for tracking function metrics
def track(metric_name: Optional[str] = None):
    """
    Decorator to track function execution metrics.
    
    Args:
        metric_name: Name of the metric (defaults to function name)
    
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if default_collector is None:
                return func(*args, **kwargs)
                
            name = metric_name or f"func_{func.__name__}"
            # Create metrics if they don't exist
            calls = default_collector.counter(
                f"{name}_calls", 
                f"Number of calls to {func.__name__}"
            )
            duration = default_collector.gauge(
                f"{name}_duration_seconds",
                f"Execution time of {func.__name__} in seconds"
            )
            
            # Track metrics
            calls.inc()
            start_time = time.time()
            
            try:
                result = func(*args, **kwargs)
                return result
            finally:
                duration.set(time.time() - start_time)
                
        return wrapper
    return decorator
