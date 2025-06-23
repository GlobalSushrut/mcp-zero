"""
Resilient Distributed Tracing for MCP Zero

This module implements a resilient distributed tracing system that works
in both online and offline modes, following the same pattern as the
successful DBMemoryTree and Traffic Agent improvements.
"""

import os
import time
import json
import uuid
import logging
import threading
from enum import Enum
from typing import Dict, Any, Optional, List, Union, Callable

logger = logging.getLogger("mcp_zero.tracing")

# Optional integration with telemetry collector if available
try:
    from src.api import telemetry_collector
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False


class TracerMode(Enum):
    """Operating modes for the tracer."""
    ONLINE = "online"
    OFFLINE = "offline"


class Span:
    """
    Represents a single operation within a trace.
    
    A span represents a unit of work or operation. It tracks the operation 
    timing, references to related spans, and key-value tags.
    """
    
    def __init__(
        self,
        tracer: 'Tracer',
        name: str,
        parent_id: Optional[str] = None,
        trace_id: Optional[str] = None,
    ):
        """
        Initialize a new span.
        
        Args:
            tracer: The tracer that created this span
            name: The operation name
            parent_id: Optional ID of the parent span
            trace_id: Optional trace ID for the span
        """
        self.tracer = tracer
        self.name = name
        self.trace_id = trace_id or str(uuid.uuid4())
        self.span_id = str(uuid.uuid4())
        self.parent_id = parent_id
        self.start_time = time.time()
        self.end_time = None
        self.tags = {}
        self.events = []
        self.is_active = True
        
    def set_tag(self, key: str, value: Any) -> 'Span':
        """
        Set a span tag.
        
        Args:
            key: Tag name
            value: Tag value
            
        Returns:
            Self for chaining
        """
        self.tags[key] = value
        return self
        
    def log(self, event: str, payload: Optional[Dict[str, Any]] = None) -> 'Span':
        """
        Log an event within the span.
        
        Args:
            event: Event name
            payload: Optional event data
            
        Returns:
            Self for chaining
        """
        self.events.append({
            "time": time.time(),
            "event": event,
            "payload": payload or {}
        })
        return self
        
    def finish(self) -> None:
        """Finish the span, recording end time and reporting to tracer."""
        if not self.is_active:
            return
            
        self.end_time = time.time()
        self.is_active = False
        self.tracer._report_span(self)
        
    def __enter__(self):
        """Context manager protocol for use in 'with' statements."""
        return self
        
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Exit the span context manager, finishing the span."""
        if exc_type is not None:
            # Record error information
            self.set_tag("error", True)
            self.set_tag("error.type", exc_type.__name__)
            self.set_tag("error.message", str(exc_val))
            
        self.finish()
        return False  # Don't suppress exceptions
        
    def to_dict(self) -> Dict[str, Any]:
        """
        Convert span to dictionary.
        
        Returns:
            Dictionary representation of span
        """
        return {
            "name": self.name,
            "trace_id": self.trace_id,
            "span_id": self.span_id,
            "parent_id": self.parent_id,
            "start_time": self.start_time,
            "end_time": self.end_time,
            "duration_ms": (self.end_time - self.start_time) * 1000 if self.end_time else None,
            "tags": self.tags,
            "events": self.events
        }


class Tracer:
    """
    Resilient distributed tracer for MCP Zero components.
    
    This tracer works in both online and offline modes, similar to the
    pattern used in DBMemoryTree and Traffic Agent improvements.
    """
    
    def __init__(
        self,
        service_name: str,
        collector_url: Optional[str] = None,
        offline_dir: str = "/var/lib/mcp-zero/traces",
        flush_interval_seconds: int = 10,
        max_queue_size: int = 100
    ):
        """
        Initialize the tracer.
        
        Args:
            service_name: Name of the service generating traces
            collector_url: URL of trace collector (None for offline only)
            offline_dir: Directory to store traces when offline
            flush_interval_seconds: How often to flush traces in background
            max_queue_size: Maximum size of the trace queue before flush
        """
        self.service_name = service_name
        self.collector_url = collector_url
        self.offline_dir = offline_dir
        self.flush_interval = flush_interval_seconds
        self.max_queue_size = max_queue_size
        
        # Ensure trace directory exists
        if not os.path.exists(offline_dir):
            os.makedirs(offline_dir, exist_ok=True)
            
        # Start in offline mode
        self.mode = TracerMode.OFFLINE
        
        # Span queue for batch reporting
        self.span_queue = []
        self._lock = threading.RLock()
        
        # Current active span for this thread
        self._active_spans = threading.local()
        
        # Try to connect to collector if provided
        if collector_url:
            self._try_connect()
            
        # Start background flush thread
        self._start_flush_thread()
        
        logger.info(
            f"Tracer initialized for {service_name} in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to trace collector.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.collector_url:
            return False
            
        try:
            # Simple connection test
            import requests
            response = requests.get(
                f"{self.collector_url}/health",
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = TracerMode.ONLINE
                logger.info(f"Connected to trace collector: {self.collector_url}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to trace collector: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to trace collector: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def _start_flush_thread(self) -> None:
        """Start background thread for flushing traces."""
        thread = threading.Thread(
            target=self._background_flush,
            daemon=True,
            name="trace-flush"
        )
        thread.start()
    
    def _background_flush(self) -> None:
        """Background thread that periodically flushes traces."""
        while True:
            time.sleep(self.flush_interval)
            
            try:
                self.flush()
            except Exception as e:
                logger.error(f"Error in trace flush: {str(e)}")
    
    def _get_active_span(self) -> Optional[Span]:
        """
        Get the current active span.
        
        Returns:
            Active span or None if not in a span context
        """
        if not hasattr(self._active_spans, "stack"):
            self._active_spans.stack = []
            
        if not self._active_spans.stack:
            return None
            
        return self._active_spans.stack[-1]
    
    def _push_active_span(self, span: Span) -> None:
        """
        Push a span onto the active span stack.
        
        Args:
            span: Span to push
        """
        if not hasattr(self._active_spans, "stack"):
            self._active_spans.stack = []
            
        self._active_spans.stack.append(span)
    
    def _pop_active_span(self) -> None:
        """Pop the current active span from the stack."""
        if hasattr(self._active_spans, "stack") and self._active_spans.stack:
            self._active_spans.stack.pop()
    
    def start_span(self, name: str) -> Span:
        """
        Start a new span.
        
        Args:
            name: Name of the operation
            
        Returns:
            New span
        """
        parent_span = self._get_active_span()
        
        if parent_span:
            # Create child span
            span = Span(
                tracer=self,
                name=name,
                parent_id=parent_span.span_id,
                trace_id=parent_span.trace_id
            )
        else:
            # Create root span
            span = Span(tracer=self, name=name)
            
        # Add default tags
        span.set_tag("service", self.service_name)
        
        # Push as active span
        self._push_active_span(span)
        
        # Log telemetry event if available
        if TELEMETRY_AVAILABLE and hasattr(telemetry_collector, "default_collector"):
            telemetry_collector.record(
                "span.start",
                name=name,
                trace_id=span.trace_id,
                span_id=span.span_id
            )
            
        return span
    
    def _report_span(self, span: Span) -> None:
        """
        Report a completed span.
        
        Args:
            span: Completed span
        """
        # Pop from active stack if it's the current span
        active_span = self._get_active_span()
        if active_span and active_span.span_id == span.span_id:
            self._pop_active_span()
        
        # Add to queue
        with self._lock:
            self.span_queue.append(span)
            
            # Flush if queue is full
            if len(self.span_queue) >= self.max_queue_size:
                self.flush()
                
        # Log telemetry event if available
        if TELEMETRY_AVAILABLE and hasattr(telemetry_collector, "default_collector"):
            duration_ms = (span.end_time - span.start_time) * 1000
            telemetry_collector.record(
                "span.finish",
                name=span.name,
                trace_id=span.trace_id,
                span_id=span.span_id,
                duration_ms=duration_ms,
                error=span.tags.get("error", False)
            )
    
    def flush(self) -> bool:
        """
        Flush queued spans to collector or local storage.
        
        Returns:
            True if flush was successful, False otherwise
        """
        with self._lock:
            if not self.span_queue:
                return True
                
            # Copy and clear queue
            spans_to_flush = [span.to_dict() for span in self.span_queue]
            self.span_queue = []
        
        # Try online flush first if in online mode
        if self.mode == TracerMode.ONLINE:
            success = self._flush_online(spans_to_flush)
            if success:
                return True
                
            # Fall back to offline mode if online flush fails
            self.mode = TracerMode.OFFLINE
            logger.warning("Switched to offline tracing mode due to server issues")
            
        # Offline flush
        return self._flush_offline(spans_to_flush)
    
    def _flush_online(self, spans: List[Dict[str, Any]]) -> bool:
        """
        Flush spans to online collector.
        
        Args:
            spans: List of span dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            response = requests.post(
                f"{self.collector_url}/spans",
                json={
                    "service": self.service_name,
                    "spans": spans
                },
                timeout=5.0
            )
            
            return response.status_code == 200
                
        except Exception as e:
            logger.warning(f"Failed to flush traces online: {str(e)}")
            return False
    
    def _flush_offline(self, spans: List[Dict[str, Any]]) -> bool:
        """
        Flush spans to local storage.
        
        Args:
            spans: List of span dictionaries
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(time.time())
            filename = f"{self.offline_dir}/{self.service_name}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({
                    "service": self.service_name,
                    "spans": spans
                }, f)
                
            return True
                
        except Exception as e:
            logger.error(f"Failed to flush traces offline: {str(e)}")
            return False


# Global tracer instance for easy import
default_tracer = None


def init(
    service_name: str,
    collector_url: Optional[str] = None,
    **kwargs
) -> Tracer:
    """
    Initialize the default tracer.
    
    Args:
        service_name: Service name
        collector_url: URL of trace collector
        **kwargs: Additional arguments for Tracer
        
    Returns:
        Tracer instance
    """
    global default_tracer
    default_tracer = Tracer(
        service_name=service_name,
        collector_url=collector_url,
        **kwargs
    )
    return default_tracer


def start_span(name: str) -> Span:
    """
    Start a new span using the default tracer.
    
    Args:
        name: Operation name
        
    Returns:
        New span
    """
    if default_tracer is None:
        raise RuntimeError("Tracer not initialized")
        
    return default_tracer.start_span(name)


def flush() -> bool:
    """
    Flush the default tracer.
    
    Returns:
        True if successful, False otherwise
    """
    if default_tracer is None:
        return False
        
    return default_tracer.flush()


# Decorator for tracing functions
def trace(name: Optional[str] = None):
    """
    Decorator to trace function execution.
    
    Args:
        name: Optional name for the span (defaults to function name)
        
    Returns:
        Decorated function
    """
    def decorator(func):
        def wrapper(*args, **kwargs):
            if default_tracer is None:
                return func(*args, **kwargs)
                
            span_name = name or f"{func.__module__}.{func.__name__}"
            with start_span(span_name):
                return func(*args, **kwargs)
                
        return wrapper
    return decorator
