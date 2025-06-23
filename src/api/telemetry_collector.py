"""
Telemetry Collector for MCP Zero

This module implements a resilient telemetry collector that works in both
online and offline modes, following the same pattern as the DBMemoryTree
and Traffic Agent improvements.
"""

import os
import time
import json
import logging
import threading
from enum import Enum
from typing import Dict, List, Any, Optional

logger = logging.getLogger("mcp_zero.telemetry")

class CollectionMode(Enum):
    """Operating modes for the telemetry collector."""
    ONLINE = "online"
    OFFLINE = "offline"


class TelemetryCollector:
    """
    Resilient telemetry collector that gracefully handles connection issues.
    
    This collector will start in offline mode by default and attempt to
    connect to the telemetry server. If connection fails, it will remain
    in offline mode, storing data locally for later transmission.
    """
    
    def __init__(
        self,
        component_name: str,
        server_url: Optional[str] = None,
        cache_dir: str = "/var/lib/mcp-zero/telemetry",
        buffer_size: int = 1000,
        flush_interval_seconds: int = 60
    ):
        """
        Initialize the telemetry collector.
        
        Args:
            component_name: Name of component generating telemetry
            server_url: URL of telemetry server (None for offline only)
            cache_dir: Directory to store telemetry data when offline
            buffer_size: Maximum number of events to buffer before flush
            flush_interval_seconds: How often to flush data in background
        """
        self.component_name = component_name
        self.server_url = server_url
        self.cache_dir = cache_dir
        self.buffer_size = buffer_size
        self.flush_interval = flush_interval_seconds
        
        # Ensure cache directory exists
        if not os.path.exists(cache_dir):
            os.makedirs(cache_dir, exist_ok=True)
        
        # Initialize in offline mode
        self.mode = CollectionMode.OFFLINE
        self.buffer = []
        self.last_flush = time.time()
        self._lock = threading.RLock()
        
        # Try to connect to telemetry server if provided
        if server_url:
            self._try_connect()
            
        # Start background flush thread
        self._start_flush_thread()
        
        logger.info(
            f"Telemetry collector initialized for {component_name} in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to the telemetry server.
        
        Returns:
            True if connection successful, False otherwise
        """
        if not self.server_url:
            return False
            
        try:
            # Simple connection test
            import requests
            response = requests.get(
                f"{self.server_url}/health", 
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = CollectionMode.ONLINE
                logger.info(f"Connected to telemetry server: {self.server_url}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to telemetry server: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to telemetry server: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def _start_flush_thread(self) -> None:
        """Start background thread for flushing telemetry data."""
        thread = threading.Thread(
            target=self._background_flush,
            daemon=True,
            name="telemetry-flush"
        )
        thread.start()
    
    def _background_flush(self) -> None:
        """Background thread that periodically flushes telemetry data."""
        while True:
            time.sleep(self.flush_interval)
            
            try:
                self.flush()
            except Exception as e:
                logger.error(f"Error in telemetry flush: {str(e)}")
    
    def record(self, event_type: str, data: Dict[str, Any]) -> None:
        """
        Record a telemetry event.
        
        Args:
            event_type: Type of event (e.g., "api.request", "agent.create")
            data: Event data
        """
        event = {
            "component": self.component_name,
            "type": event_type,
            "timestamp": time.time(),
            "data": data
        }
        
        with self._lock:
            self.buffer.append(event)
            
            # Flush if buffer is full
            if len(self.buffer) >= self.buffer_size:
                self.flush()
    
    def flush(self) -> bool:
        """
        Flush buffered telemetry data to storage/server.
        
        Returns:
            True if flush was successful, False otherwise
        """
        with self._lock:
            if not self.buffer:
                return True
                
            # Copy and clear buffer
            events_to_flush = self.buffer.copy()
            self.buffer = []
            
        # Try online flush first if in online mode
        if self.mode == CollectionMode.ONLINE:
            success = self._flush_online(events_to_flush)
            if success:
                return True
                
            # Fall back to offline mode if online flush fails
            self.mode = CollectionMode.OFFLINE
            logger.warning("Switched to offline telemetry mode due to server issues")
            
        # Offline flush
        return self._flush_offline(events_to_flush)
    
    def _flush_online(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush events to online telemetry server.
        
        Args:
            events: List of events to flush
            
        Returns:
            True if successful, False otherwise
        """
        if not self.server_url:
            return False
            
        try:
            import requests
            response = requests.post(
                f"{self.server_url}/events",
                json={"events": events},
                timeout=5.0
            )
            
            return response.status_code == 200
                
        except Exception as e:
            logger.warning(f"Failed to flush telemetry online: {str(e)}")
            return False
    
    def _flush_offline(self, events: List[Dict[str, Any]]) -> bool:
        """
        Flush events to local storage.
        
        Args:
            events: List of events to flush
            
        Returns:
            True if successful, False otherwise
        """
        try:
            timestamp = int(time.time())
            filename = f"{self.cache_dir}/{self.component_name}_{timestamp}.json"
            
            with open(filename, 'w') as f:
                json.dump({"events": events}, f)
                
            return True
                
        except Exception as e:
            logger.error(f"Failed to flush telemetry offline: {str(e)}")
            # Put events back in buffer to retry later
            with self._lock:
                self.buffer = events + self.buffer
                # Trim if too large
                if len(self.buffer) > self.buffer_size * 2:
                    self.buffer = self.buffer[:self.buffer_size]
            return False
    
    def try_upload_cached(self) -> int:
        """
        Try to upload cached telemetry files if we're in online mode.
        
        Returns:
            Number of successfully uploaded cache files
        """
        if self.mode != CollectionMode.ONLINE:
            return 0
            
        if not os.path.exists(self.cache_dir):
            return 0
            
        count = 0
        for filename in os.listdir(self.cache_dir):
            if not filename.endswith('.json'):
                continue
                
            filepath = os.path.join(self.cache_dir, filename)
            try:
                with open(filepath, 'r') as f:
                    cached_data = json.load(f)
                    
                if self._flush_online(cached_data.get("events", [])):
                    os.remove(filepath)
                    count += 1
                    
            except Exception as e:
                logger.warning(f"Error processing cached telemetry {filepath}: {str(e)}")
                
        return count


# Global telemetry collector instance for easy import
default_collector = None


def initialize(
    component_name: str,
    server_url: Optional[str] = None,
    **kwargs
) -> TelemetryCollector:
    """
    Initialize the default telemetry collector.
    
    Args:
        component_name: Name of component generating telemetry
        server_url: URL of telemetry server
        **kwargs: Additional arguments for TelemetryCollector
        
    Returns:
        Telemetry collector instance
    """
    global default_collector
    default_collector = TelemetryCollector(
        component_name=component_name,
        server_url=server_url,
        **kwargs
    )
    return default_collector


def record(event_type: str, **data) -> None:
    """
    Record a telemetry event using the default collector.
    
    Args:
        event_type: Type of event
        **data: Event data as keyword arguments
    """
    if default_collector is None:
        logger.warning("Telemetry not initialized, event discarded")
        return
        
    default_collector.record(event_type, data)


def flush() -> bool:
    """
    Flush the default collector.
    
    Returns:
        True if successful, False otherwise
    """
    if default_collector is None:
        return False
        
    return default_collector.flush()
