"""
Telemetry Collector for MCP Zero Editor

Provides resilient telemetry collection with offline-first capability.
"""

import os
import time
import json
import logging
import threading
from typing import Dict, Any, List, Optional

logger = logging.getLogger("mcp_zero.editor.telemetry_collector")

class TelemetryCollector:
    """
    Telemetry collector with offline-first resilience.
    
    Follows offline-first approach:
    - Always saves telemetry locally first
    - Only attempts to connect to telemetry service once 
    - Permanently switches to local-only if service unavailable
    """
    
    def __init__(self, telemetry_dir: str, offline_first: bool = True):
        """
        Initialize telemetry collector.
        
        Args:
            telemetry_dir: Directory for local telemetry storage
            offline_first: Whether to start in offline mode
        """
        self.telemetry_dir = telemetry_dir
        self.offline_mode = offline_first
        self._events = []
        self._lock = threading.RLock()
        self._remote_attempt_made = False
        
        # Ensure telemetry directory exists
        os.makedirs(telemetry_dir, exist_ok=True)
        
        # Generate telemetry file path with timestamp
        self.telemetry_file = os.path.join(
            self.telemetry_dir, 
            f"telemetry_{int(time.time())}.jsonl"
        )
        
        logger.info(f"Telemetry collector initialized in {'offline' if offline_first else 'online'} mode")
    
    def record(self, event_name: str, **data) -> bool:
        """
        Record telemetry event.
        
        Args:
            event_name: Name of event
            **data: Additional event data
            
        Returns:
            True if event was recorded
        """
        try:
            event = {
                "timestamp": time.time(),
                "event": event_name,
                "data": data
            }
            
            with self._lock:
                self._events.append(event)
                
            # If we have too many events, flush
            if len(self._events) > 100:
                threading.Thread(target=self.flush, daemon=True).start()
                
            return True
            
        except Exception as e:
            logger.error(f"Error recording telemetry event: {str(e)}")
            return False
    
    def flush(self) -> bool:
        """
        Flush telemetry events to storage.
        
        Returns:
            True if events were flushed successfully
        """
        with self._lock:
            if not self._events:
                return True
                
            events_to_flush = self._events.copy()
            self._events = []
        
        # Try remote first, but only once following the pattern from Traffic Agent
        remote_success = False
        if not self.offline_mode and not self._remote_attempt_made:
            remote_success = self._flush_to_remote(events_to_flush)
            self._remote_attempt_made = True
            
            if not remote_success:
                logger.info("Remote telemetry unavailable, switching to local-only mode permanently")
                self.offline_mode = True
        
        # Always save locally as backup, or if remote failed
        if not remote_success:
            return self._flush_to_local(events_to_flush)
            
        return remote_success
    
    def _flush_to_local(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush telemetry events to local storage.
        
        Args:
            events: List of events to flush
            
        Returns:
            True if events were flushed successfully
        """
        try:
            mode = 'a' if os.path.exists(self.telemetry_file) else 'w'
            with open(self.telemetry_file, mode) as f:
                for event in events:
                    f.write(json.dumps(event) + '\n')
            
            logger.debug(f"Flushed {len(events)} telemetry events to local storage")
            return True
            
        except Exception as e:
            logger.error(f"Error flushing telemetry to local storage: {str(e)}")
            return False
    
    def _flush_to_remote(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush telemetry events to remote service.
        
        This method follows the pattern from Traffic Agent:
        - Only attempts to connect once
        - Permanently switches to local mode if service unavailable
        
        Args:
            events: List of events to flush
            
        Returns:
            True if events were flushed successfully
        """
        try:
            # In a real implementation, this would connect to a remote service
            logger.info("Remote telemetry service not available, using local storage only")
            return False
            
        except Exception as e:
            logger.warning(f"Error flushing telemetry to remote service: {str(e)}")
            return False
    
    def is_healthy(self) -> bool:
        """
        Check if telemetry collector is healthy.
        
        Returns:
            True if healthy
        """
        # Telemetry is always healthy in offline mode
        if self.offline_mode:
            return True
            
        # In online mode, check if we can write to local storage
        try:
            test_file = os.path.join(self.telemetry_dir, "health_check.tmp")
            with open(test_file, 'w') as f:
                f.write("health check")
            os.remove(test_file)
            return True
        except Exception:
            return False

# Global singleton instance
_collector: Optional[TelemetryCollector] = None

def initialize(telemetry_dir: Optional[str] = None, offline_first: bool = True) -> TelemetryCollector:
    """
    Initialize global telemetry collector.
    
    Args:
        telemetry_dir: Directory for telemetry storage
        offline_first: Whether to start in offline mode
        
    Returns:
        Telemetry collector instance
    """
    global _collector
    
    if _collector is None:
        if telemetry_dir is None:
            telemetry_dir = os.path.join(
                os.path.expanduser("~"), 
                ".mcp_zero", 
                "editor", 
                "telemetry"
            )
        
        _collector = TelemetryCollector(telemetry_dir, offline_first)
    
    return _collector

def record(event_name: str, **data) -> bool:
    """
    Record telemetry event using global collector.
    
    Args:
        event_name: Name of event
        **data: Event data
        
    Returns:
        True if event was recorded
    """
    if _collector is None:
        logger.warning("Telemetry not initialized, event discarded")
        return False
    
    return _collector.record(event_name, **data)

def flush() -> bool:
    """
    Flush telemetry events using global collector.
    
    Returns:
        True if events were flushed successfully
    """
    if _collector is None:
        return False
    
    return _collector.flush()
