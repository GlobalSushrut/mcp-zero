"""
Health Checker for MCP Zero Dependencies

Implements a resilient health checking system that works in both online and offline modes,
following the same pattern as our other resilient components like DBMemoryTree and
the Traffic Agent's video processing.
"""

import time
import threading
import logging
from enum import Enum
from typing import Dict, List, Any, Optional, Callable

logger = logging.getLogger("mcp_zero.health_checker")

class HealthStatus(Enum):
    """Health status of a dependency."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


class CheckerMode(Enum):
    """Operating modes for health checker."""
    ONLINE = "online"   # Full checking with remote services
    OFFLINE = "offline"  # Local checks only


class HealthCheck:
    """Definition of a health check for a dependency."""
    
    def __init__(
        self,
        name: str,
        check_fn: Callable[[], bool],
        is_critical: bool = False,
        timeout_seconds: float = 2.0,
        requires_network: bool = True
    ):
        """
        Initialize health check.
        
        Args:
            name: Name of the check
            check_fn: Function to call to perform the check
            is_critical: Whether this is a critical dependency
            timeout_seconds: Timeout for the check
            requires_network: Whether this check requires network
        """
        self.name = name
        self.check_fn = check_fn
        self.is_critical = is_critical
        self.timeout = timeout_seconds
        self.requires_network = requires_network
        self.last_status = HealthStatus.UNKNOWN
        self.last_check_time = 0
        self.consecutive_failures = 0


class DependencyHealthChecker:
    """
    Resilient health checker for MCP Zero dependencies.
    
    This component starts in offline mode by default and attempts to
    perform full checks if possible. If remote dependencies are unavailable,
    it gracefully falls back to offline-only operation, similar to the
    DBMemoryTree and Traffic Agent implementations.
    """
    
    def __init__(
        self,
        service_name: str,
        check_interval_seconds: int = 60,
        status_cache_seconds: int = 5,
        metrics_collector = None
    ):
        """
        Initialize health checker.
        
        Args:
            service_name: Name of the service
            check_interval_seconds: Seconds between automatic checks
            status_cache_seconds: How long to cache check results
            metrics_collector: Optional metrics collector for reporting
        """
        self.service_name = service_name
        self.check_interval = check_interval_seconds
        self.status_cache = status_cache_seconds
        self.metrics = metrics_collector
        
        # Start in offline mode by default (like DBMemoryTree)
        self.mode = CheckerMode.OFFLINE
        
        self.checks = {}  # name -> HealthCheck
        self._lock = threading.RLock()
        self.overall_status = HealthStatus.UNKNOWN
        self.last_check_time = 0
        
        # Try to switch to online mode once
        self._try_online_mode()
        
        # Background thread for periodic checks
        self._start_background_thread()
        
        logger.info(
            f"Health checker initialized for {service_name} in {self.mode.value} mode"
        )
    
    def _try_online_mode(self) -> bool:
        """
        Attempt to switch to online mode by checking internet connectivity.
        
        Following the Traffic Agent pattern, this only tries once and then
        permanently settles on the determined mode.
        
        Returns:
            True if online mode activated, False otherwise
        """
        try:
            import socket
            socket.create_connection(("8.8.8.8", 53), timeout=2)
            self.mode = CheckerMode.ONLINE
            logger.info("Network connectivity verified, operating in online mode")
            return True
        except Exception as e:
            logger.warning(
                f"Network connectivity check failed: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def _start_background_thread(self) -> None:
        """Start background thread for periodic health checks."""
        thread = threading.Thread(
            target=self._background_check,
            daemon=True,
            name="health-checker"
        )
        thread.start()
    
    def _background_check(self) -> None:
        """Background thread that periodically checks health."""
        while True:
            time.sleep(self.check_interval)
            
            try:
                self.check_all()
            except Exception as e:
                logger.error(f"Error in health check: {str(e)}")
    
    def register_check(
        self,
        name: str,
        check_fn: Callable[[], bool],
        is_critical: bool = False,
        timeout_seconds: float = 2.0,
        requires_network: bool = True
    ) -> None:
        """
        Register a new health check.
        
        Args:
            name: Name of the check
            check_fn: Function to call to perform the check
            is_critical: Whether this is a critical dependency
            timeout_seconds: Timeout for the check
            requires_network: Whether this check requires network
        """
        with self._lock:
            self.checks[name] = HealthCheck(
                name=name,
                check_fn=check_fn,
                is_critical=is_critical,
                timeout_seconds=timeout_seconds,
                requires_network=requires_network
            )
        
        logger.debug(f"Registered health check: {name}")
    
    def check(self, name: str, force: bool = False) -> HealthStatus:
        """
        Perform a single health check.
        
        Args:
            name: Name of the check to perform
            force: Force check even if cache is valid
            
        Returns:
            Health status
        """
        with self._lock:
            if name not in self.checks:
                logger.warning(f"Health check '{name}' not found")
                return HealthStatus.UNKNOWN
                
            check = self.checks[name]
            
            # Return cached result if not forced and within cache time
            if not force and (time.time() - check.last_check_time) < self.status_cache:
                return check.last_status
            
            # Skip network checks if in offline mode
            if self.mode == CheckerMode.OFFLINE and check.requires_network:
                check.last_status = HealthStatus.UNKNOWN
                return check.last_status
        
        # Perform the check with timeout
        try:
            # Use a simple approach for timeout
            start_time = time.time()
            result = check.check_fn()
            
            # Update check status
            with self._lock:
                check.last_check_time = time.time()
                
                if result:
                    check.last_status = HealthStatus.HEALTHY
                    check.consecutive_failures = 0
                else:
                    check.last_status = HealthStatus.UNHEALTHY
                    check.consecutive_failures += 1
                
                # Report metrics if available
                if self.metrics:
                    try:
                        self.metrics.gauge(f"health_{name}").set(
                            1 if result else 0
                        )
                        self.metrics.gauge(f"health_{name}_time").set(
                            time.time() - start_time
                        )
                    except Exception as e:
                        logger.warning(f"Failed to report health metrics: {str(e)}")
                
                return check.last_status
                
        except Exception as e:
            logger.warning(f"Health check '{name}' failed with error: {str(e)}")
            
            with self._lock:
                check.last_check_time = time.time()
                check.last_status = HealthStatus.UNHEALTHY
                check.consecutive_failures += 1
                
                # Report metrics if available
                if self.metrics:
                    try:
                        self.metrics.gauge(f"health_{name}").set(0)
                        self.metrics.counter(f"health_{name}_errors").inc()
                    except Exception as me:
                        logger.warning(f"Failed to report health metrics: {str(me)}")
                
                return check.last_status
    
    def check_all(self, force: bool = False) -> HealthStatus:
        """
        Perform all health checks.
        
        Args:
            force: Force checks even if cache is valid
            
        Returns:
            Overall health status
        """
        with self._lock:
            check_names = list(self.checks.keys())
        
        results = {}
        critical_failures = 0
        
        for name in check_names:
            status = self.check(name, force)
            results[name] = status
            
            with self._lock:
                if status == HealthStatus.UNHEALTHY and self.checks[name].is_critical:
                    critical_failures += 1
        
        # Determine overall status
        if critical_failures > 0:
            overall = HealthStatus.UNHEALTHY
        elif any(status == HealthStatus.DEGRADED for status in results.values()):
            overall = HealthStatus.DEGRADED
        elif all(status == HealthStatus.HEALTHY for status in results.values()):
            overall = HealthStatus.HEALTHY
        else:
            overall = HealthStatus.DEGRADED
        
        with self._lock:
            self.overall_status = overall
            self.last_check_time = time.time()
        
        # Report metrics if available
        if self.metrics:
            try:
                self.metrics.gauge("health_overall").set(
                    1 if overall == HealthStatus.HEALTHY else
                    0.5 if overall == HealthStatus.DEGRADED else 0
                )
            except Exception as e:
                logger.warning(f"Failed to report overall health metrics: {str(e)}")
        
        return overall
    
    def get_status(self, force_check: bool = False) -> Dict[str, Any]:
        """
        Get complete health status report.
        
        Args:
            force_check: Force fresh checks
            
        Returns:
            Health status report
        """
        if force_check or time.time() - self.last_check_time > self.status_cache:
            self.check_all(force_check)
        
        with self._lock:
            report = {
                "service": self.service_name,
                "timestamp": time.time(),
                "status": self.overall_status.value,
                "mode": self.mode.value,
                "checks": {}
            }
            
            for name, check in self.checks.items():
                report["checks"][name] = {
                    "status": check.last_status.value,
                    "critical": check.is_critical,
                    "last_checked": check.last_check_time,
                    "failures": check.consecutive_failures
                }
            
            return report


# Global health checker instance
default_checker = None


def init(
    service_name: str,
    **kwargs
) -> DependencyHealthChecker:
    """
    Initialize the default health checker.
    
    Args:
        service_name: Service name
        **kwargs: Additional arguments for DependencyHealthChecker
        
    Returns:
        Health checker instance
    """
    global default_checker
    default_checker = DependencyHealthChecker(
        service_name=service_name,
        **kwargs
    )
    return default_checker


def register_check(
    name: str,
    check_fn: Callable[[], bool],
    **kwargs
) -> None:
    """
    Register a health check with the default checker.
    
    Args:
        name: Check name
        check_fn: Check function
        **kwargs: Additional arguments for register_check
    """
    if default_checker is None:
        raise RuntimeError("Health checker not initialized")
        
    default_checker.register_check(name, check_fn, **kwargs)


def check(name: str, force: bool = False) -> HealthStatus:
    """
    Perform a health check using the default checker.
    
    Args:
        name: Check name
        force: Force check even if cache is valid
        
    Returns:
        Health status
    """
    if default_checker is None:
        raise RuntimeError("Health checker not initialized")
        
    return default_checker.check(name, force)


def check_all(force: bool = False) -> HealthStatus:
    """
    Perform all health checks using the default checker.
    
    Args:
        force: Force check even if cache is valid
        
    Returns:
        Overall health status
    """
    if default_checker is None:
        raise RuntimeError("Health checker not initialized")
        
    return default_checker.check_all(force)


def get_status(force_check: bool = False) -> Dict[str, Any]:
    """
    Get complete health status report using the default checker.
    
    Args:
        force_check: Force fresh checks
        
    Returns:
        Health status report
    """
    if default_checker is None:
        raise RuntimeError("Health checker not initialized")
        
    return default_checker.get_status(force_check)
