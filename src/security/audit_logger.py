"""
Resilient Security Audit Logger for MCP Zero

This module implements a resilient security audit logging system that works
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
from datetime import datetime
from typing import Dict, Any, Optional, List, Union, Callable

logger = logging.getLogger("mcp_zero.security.audit")

# Optional integrations
try:
    from src.api import telemetry_collector
    TELEMETRY_AVAILABLE = True
except ImportError:
    TELEMETRY_AVAILABLE = False

try:
    from src.api import tracing
    TRACING_AVAILABLE = True
except ImportError:
    TRACING_AVAILABLE = False


class AuditSeverity(Enum):
    """Severity levels for audit events."""
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class AuditCategory(Enum):
    """Categories of security audit events."""
    AUTHENTICATION = "authentication"
    AUTHORIZATION = "authorization"
    DATA_ACCESS = "data_access"
    CONFIGURATION = "configuration"
    PLUGIN = "plugin"
    SYSTEM = "system"
    ADMIN = "admin"
    USER = "user"


class AuditMode(Enum):
    """Operating modes for the audit logger."""
    ONLINE = "online"
    OFFLINE = "offline"


class AuditLogger:
    """
    Resilient security audit logger for MCP Zero.
    
    This logger works in both online and offline modes, following the same
    pattern used in DBMemoryTree and Traffic Agent improvements.
    """
    
    def __init__(
        self,
        service_name: str,
        audit_server: Optional[str] = None,
        offline_dir: str = "/var/lib/mcp-zero/audit",
        flush_interval_seconds: int = 5,
        max_queue_size: int = 100
    ):
        """
        Initialize the audit logger.
        
        Args:
            service_name: Name of the service generating audit events
            audit_server: URL of audit server (None for offline only)
            offline_dir: Directory to store audit logs when offline
            flush_interval_seconds: How often to flush logs in background
            max_queue_size: Maximum size of the event queue before flush
        """
        self.service_name = service_name
        self.audit_server = audit_server
        self.offline_dir = offline_dir
        self.flush_interval = flush_interval_seconds
        self.max_queue_size = max_queue_size
        
        # Ensure audit directory exists
        if not os.path.exists(offline_dir):
            os.makedirs(offline_dir, exist_ok=True)
        
        # Start in offline mode like DBMemoryTree
        self.mode = AuditMode.OFFLINE
        
        # Event queue for batch reporting
        self.event_queue = []
        self._lock = threading.RLock()
        
        # Try to connect to audit server if provided
        if audit_server:
            self._try_connect()
        
        # Start background flush thread
        self._start_flush_thread()
        
        logger.info(
            f"Audit logger initialized for {service_name} in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to audit server.
        
        Like the Traffic Agent improvement, this will only try once and
        then remain in the determined mode.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import requests
            response = requests.get(
                f"{self.audit_server}/health",
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = AuditMode.ONLINE
                logger.info(f"Connected to audit server: {self.audit_server}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to audit server: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to audit server: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def _start_flush_thread(self) -> None:
        """Start background thread for flushing audit events."""
        thread = threading.Thread(
            target=self._background_flush,
            daemon=True,
            name="audit-flush"
        )
        thread.start()
    
    def _background_flush(self) -> None:
        """Background thread that periodically flushes audit events."""
        while True:
            time.sleep(self.flush_interval)
            
            try:
                self.flush()
            except Exception as e:
                logger.error(f"Error in audit flush: {str(e)}")
    
    def log(
        self,
        event_type: str,
        category: Union[AuditCategory, str],
        severity: Union[AuditSeverity, str],
        message: str,
        resource_id: Optional[str] = None,
        user_id: Optional[str] = None,
        source_ip: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None,
    ) -> str:
        """
        Log an audit event.
        
        Args:
            event_type: Type of event (e.g., "login.attempt", "data.access")
            category: Event category
            severity: Event severity
            message: Human-readable description of the event
            resource_id: Optional ID of affected resource
            user_id: Optional ID of user performing the action
            source_ip: Optional source IP address
            metadata: Optional additional metadata
            
        Returns:
            Event ID
        """
        # Convert enums to strings if needed
        if isinstance(category, AuditCategory):
            category = category.value
        if isinstance(severity, AuditSeverity):
            severity = severity.value
        
        # Generate event ID
        event_id = str(uuid.uuid4())
        
        # Get trace context if available
        trace_id = None
        span_id = None
        
        if TRACING_AVAILABLE and tracing.default_tracer is not None:
            active_span = tracing.default_tracer._get_active_span()
            if active_span:
                trace_id = active_span.trace_id
                span_id = active_span.span_id
        
        # Create event
        event = {
            "id": event_id,
            "timestamp": time.time(),
            "iso_time": datetime.utcnow().isoformat() + "Z",
            "service": self.service_name,
            "event_type": event_type,
            "category": category,
            "severity": severity,
            "message": message,
            "resource_id": resource_id,
            "user_id": user_id,
            "source_ip": source_ip,
            "trace_id": trace_id,
            "span_id": span_id,
            "metadata": metadata or {}
        }
        
        # Add to queue
        with self._lock:
            self.event_queue.append(event)
            
            # Flush if queue is full
            if len(self.event_queue) >= self.max_queue_size:
                self.flush()
        
        # Send to telemetry if available
        if TELEMETRY_AVAILABLE and hasattr(telemetry_collector, "default_collector"):
            telemetry_collector.record("audit.event", **{
                "event_id": event_id,
                "event_type": event_type,
                "category": category,
                "severity": severity,
                "resource_id": resource_id
            })
        
        return event_id
    
    def flush(self) -> bool:
        """
        Flush queued audit events to server or local storage.
        
        Returns:
            True if flush was successful, False otherwise
        """
        with self._lock:
            if not self.event_queue:
                return True
                
            # Copy and clear queue
            events_to_flush = self.event_queue.copy()
            self.event_queue = []
        
        # Try online flush first if in online mode
        if self.mode == AuditMode.ONLINE:
            success = self._flush_online(events_to_flush)
            if success:
                return True
                
            # Fall back to offline mode if online flush fails
            self.mode = AuditMode.OFFLINE
            logger.warning("Switched to offline audit mode due to server issues")
            
        # Offline flush
        return self._flush_offline(events_to_flush)
    
    def _flush_online(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush events to online audit server.
        
        Args:
            events: List of audit events
            
        Returns:
            True if successful, False otherwise
        """
        try:
            import requests
            response = requests.post(
                f"{self.audit_server}/events",
                json={"events": events},
                timeout=5.0
            )
            
            return response.status_code == 200
                
        except Exception as e:
            logger.warning(f"Failed to flush audit logs online: {str(e)}")
            return False
    
    def _flush_offline(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush events to local storage.
        
        Args:
            events: List of audit events
            
        Returns:
            True if successful, False otherwise
        """
        try:
            # Format with ISO timestamp for easier log analysis
            timestamp = datetime.utcnow().strftime("%Y%m%d_%H%M%S")
            filename = f"{self.offline_dir}/{self.service_name}_audit_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({"events": events}, f)
                
            # Also append to daily log file for easier reviewing
            daily_log = f"{self.offline_dir}/{self.service_name}_audit_{datetime.utcnow().strftime('%Y%m%d')}.log"
            
            with open(daily_log, 'a') as f:
                for event in events:
                    # Format as single-line JSON for log processing tools
                    f.write(json.dumps(event) + "\n")
                
            return True
                
        except Exception as e:
            logger.error(f"Failed to flush audit logs offline: {str(e)}")
            # Put events back in queue to retry later
            with self._lock:
                self.event_queue = events + self.event_queue
                # Trim if too large
                if len(self.event_queue) > self.max_queue_size * 2:
                    self.event_queue = self.event_queue[:self.max_queue_size]
            return False
    
    def try_upload_cached(self) -> int:
        """
        Try to upload cached audit logs if we're in online mode.
        
        Returns:
            Number of successfully uploaded cache files
        """
        if self.mode != AuditMode.ONLINE:
            return 0
            
        count = 0
        for filename in os.listdir(self.offline_dir):
            if not filename.endswith('.json') or not filename.startswith(f"{self.service_name}_audit_"):
                continue
                
            filepath = os.path.join(self.offline_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    cached_data = json.load(f)
                    
                if self._flush_online(cached_data.get("events", [])):
                    os.remove(filepath)
                    count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing cached audit log {filepath}: {str(e)}")
                
        return count


# Global audit logger instance
default_logger = None


def init(
    service_name: str,
    audit_server: Optional[str] = None,
    **kwargs
) -> AuditLogger:
    """
    Initialize the default audit logger.
    
    Args:
        service_name: Service name
        audit_server: URL of audit server
        **kwargs: Additional arguments for AuditLogger
        
    Returns:
        Audit logger instance
    """
    global default_logger
    default_logger = AuditLogger(
        service_name=service_name,
        audit_server=audit_server,
        **kwargs
    )
    return default_logger


def log(
    event_type: str,
    category: Union[AuditCategory, str],
    severity: Union[AuditSeverity, str],
    message: str,
    **kwargs
) -> str:
    """
    Log an audit event using the default logger.
    
    Args:
        event_type: Type of event
        category: Event category
        severity: Event severity
        message: Event message
        **kwargs: Additional audit event parameters
        
    Returns:
        Event ID
    """
    if default_logger is None:
        raise RuntimeError("Audit logger not initialized")
        
    return default_logger.log(
        event_type=event_type,
        category=category,
        severity=severity,
        message=message,
        **kwargs
    )


def flush() -> bool:
    """
    Flush the default audit logger.
    
    Returns:
        True if successful, False otherwise
    """
    if default_logger is None:
        return False
        
    return default_logger.flush()


# Convenience functions for common audit events
def auth_success(user_id: str, message: str = "Authentication successful", **kwargs) -> str:
    """Log successful authentication."""
    return log(
        "auth.success",
        AuditCategory.AUTHENTICATION,
        AuditSeverity.INFO,
        message,
        user_id=user_id,
        **kwargs
    )


def auth_failure(user_id: Optional[str], message: str = "Authentication failed", **kwargs) -> str:
    """Log failed authentication."""
    return log(
        "auth.failure",
        AuditCategory.AUTHENTICATION,
        AuditSeverity.WARNING,
        message,
        user_id=user_id,
        **kwargs
    )


def access_denied(user_id: Optional[str], resource_id: str, message: str = "Access denied", **kwargs) -> str:
    """Log access denial."""
    return log(
        "access.denied",
        AuditCategory.AUTHORIZATION,
        AuditSeverity.WARNING,
        message,
        user_id=user_id,
        resource_id=resource_id,
        **kwargs
    )


def data_accessed(user_id: str, resource_id: str, message: str = "Data accessed", **kwargs) -> str:
    """Log data access."""
    return log(
        "data.access",
        AuditCategory.DATA_ACCESS,
        AuditSeverity.INFO,
        message,
        user_id=user_id,
        resource_id=resource_id,
        **kwargs
    )


def data_modified(user_id: str, resource_id: str, message: str = "Data modified", **kwargs) -> str:
    """Log data modification."""
    return log(
        "data.modify",
        AuditCategory.DATA_ACCESS,
        AuditSeverity.INFO,
        message,
        user_id=user_id,
        resource_id=resource_id,
        **kwargs
    )


def admin_action(user_id: str, message: str, **kwargs) -> str:
    """Log administrative action."""
    return log(
        "admin.action",
        AuditCategory.ADMIN,
        AuditSeverity.INFO,
        message,
        user_id=user_id,
        **kwargs
    )


def security_event(message: str, severity: AuditSeverity = AuditSeverity.WARNING, **kwargs) -> str:
    """Log security event."""
    return log(
        "security.event",
        AuditCategory.SYSTEM,
        severity,
        message,
        **kwargs
    )


def plugin_action(plugin_id: str, message: str, **kwargs) -> str:
    """Log plugin action."""
    return log(
        "plugin.action",
        AuditCategory.PLUGIN,
        AuditSeverity.INFO,
        message,
        resource_id=plugin_id,
        **kwargs
    )
