"""
Health Checker for MCP Zero Editor

Provides resilient health monitoring with offline-first capability.
"""

import time
import threading
import logging
from typing import Dict, Callable, Optional, List

logger = logging.getLogger("mcp_zero.editor.health_checker")

class HealthChecker:
    """
    Health monitoring system with offline-first resilience.
    
    Follows offline-first approach:
    - Always works in offline mode
    - Only attempts remote health reporting once
    - Permanently switches to local mode if remote unavailable
    """
    
    def __init__(self, check_interval: int = 60, offline_first: bool = True):
        """
        Initialize health checker.
        
        Args:
            check_interval: Interval between checks in seconds
            offline_first: Whether to start in offline mode
        """
        self.check_interval = check_interval
        self.offline_mode = offline_first
        self._checks: Dict[str, Callable[[], bool]] = {}
        self._status: Dict[str, bool] = {}
        self._lock = threading.RLock()
        self._running = False
        self._thread = None
        self._remote_attempt_made = False
        
        logger.info(f"Health checker initialized in {'offline' if offline_first else 'online'} mode")
    
    def register_check(self, name: str, check_func: Callable[[], bool]) -> None:
        """
        Register health check function.
        
        Args:
            name: Name of the health check
            check_func: Function that returns True if component is healthy
        """
        with self._lock:
            self._checks[name] = check_func
            self._status[name] = False  # Initial status is unhealthy until checked
        
        logger.debug(f"Registered health check: {name}")
    
    def unregister_check(self, name: str) -> None:
        """
        Unregister health check.
        
        Args:
            name: Name of the health check to remove
        """
        with self._lock:
            if name in self._checks:
                del self._checks[name]
                del self._status[name]
        
        logger.debug(f"Unregistered health check: {name}")
    
    def start(self) -> None:
        """Start periodic health checking."""
        with self._lock:
            if self._running:
                return
                
            self._running = True
            self._thread = threading.Thread(target=self._check_loop, daemon=True)
            self._thread.start()
        
        logger.info("Health checker started")
    
    def stop(self) -> None:
        """Stop periodic health checking."""
        with self._lock:
            self._running = False
            
            # Wait for thread to finish
            if self._thread and self._thread.is_alive():
                self._thread.join(timeout=5.0)
        
        logger.info("Health checker stopped")
    
    def _check_loop(self) -> None:
        """Background health check loop."""
        while self._running:
            self.check_all()
            
            # Sleep for check interval
            time.sleep(self.check_interval)
    
    def check_all(self) -> Dict[str, bool]:
        """
        Run all health checks.
        
        Returns:
            Dictionary of health check results
        """
        with self._lock:
            checks = list(self._checks.items())
        
        results = {}
        for name, check_func in checks:
            try:
                status = check_func()
                with self._lock:
                    self._status[name] = status
                results[name] = status
            except Exception as e:
                logger.warning(f"Health check failed for {name}: {str(e)}")
                with self._lock:
                    self._status[name] = False
                results[name] = False
        
        # Try to report health status remotely, but only once
        # Following the pattern from Traffic Agent and DBMemoryTree
        if not self.offline_mode and not self._remote_attempt_made:
            remote_success = self._report_to_remote(results)
            self._remote_attempt_made = True
            
            if not remote_success:
                logger.info("Remote health reporting unavailable, switching to local-only mode permanently")
                self.offline_mode = True
        
        return results
    
    def get_status(self) -> Dict[str, bool]:
        """
        Get current health status.
        
        Returns:
            Dictionary of current health status
        """
        with self._lock:
            return self._status.copy()
    
    def is_healthy(self, service_name: Optional[str] = None) -> bool:
        """
        Check if a service or all services are healthy.
        
        Args:
            service_name: Name of service to check, or None for all services
            
        Returns:
            True if healthy
        """
        with self._lock:
            if service_name:
                return self._status.get(service_name, False)
            else:
                # All services must be healthy
                return all(self._status.values()) if self._status else True
    
    def get_unhealthy_services(self) -> List[str]:
        """
        Get list of unhealthy services.
        
        Returns:
            List of unhealthy service names
        """
        with self._lock:
            return [name for name, status in self._status.items() if not status]
    
    def _report_to_remote(self, status: Dict[str, bool]) -> bool:
        """
        Report health status to remote monitoring service.
        
        This method follows the pattern from Traffic Agent:
        - Only attempts to connect once
        - Permanently switches to local mode if service unavailable
        
        Args:
            status: Health status to report
            
        Returns:
            True if reported successfully
        """
        try:
            # In a real implementation, this would connect to a remote service
            logger.info("Remote health monitoring not available, using local monitoring only")
            return False
            
        except Exception as e:
            logger.warning(f"Error reporting health status to remote service: {str(e)}")
            return False
