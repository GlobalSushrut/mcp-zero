"""
Advanced Resilience Module for MCP Zero

This module implements circuit breakers, fallback mechanisms, and graceful
degradation to ensure continuous operation under various failure conditions.
"""

import time
import logging
import functools
from enum import Enum
from typing import Dict, Any, Callable, Optional, TypeVar, List, Tuple

logger = logging.getLogger("mcp-zero.resilience")

# Type definitions
T = TypeVar('T')
FallbackFunc = Callable[..., T]


class CircuitState(Enum):
    """Possible states for the circuit breaker."""
    CLOSED = "closed"  # Normal operation, requests go through
    OPEN = "open"      # Failing, requests are immediately rejected
    HALF_OPEN = "half_open"  # Testing if system has recovered


class CircuitBreaker:
    """
    Implements the circuit breaker pattern to prevent cascading failures.
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout: float = 30.0,
        half_open_max_calls: int = 3
    ):
        """
        Initialize circuit breaker.
        
        Args:
            failure_threshold: Number of failures before opening circuit
            recovery_timeout: Seconds to wait before attempting recovery
            half_open_max_calls: Number of successful calls needed to close circuit
        """
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout
        self._last_failure_time = 0
        self._half_open_successes = 0
        self._half_open_max_calls = half_open_max_calls
        self._lock = None  # Replace with appropriate lock mechanism for thread safety
    
    def execute(self, func, *args, **kwargs) -> Any:
        """
        Execute function with circuit breaker protection.
        
        Args:
            func: Function to execute
            *args: Arguments for the function
            **kwargs: Keyword arguments for the function
            
        Returns:
            Function result or raises exception if circuit is open
            
        Raises:
            CircuitBreakerOpenError: When circuit is open
        """
        if self._state == CircuitState.OPEN:
            if time.time() - self._last_failure_time >= self._recovery_timeout:
                logger.info("Circuit half-open, testing recovery")
                self._state = CircuitState.HALF_OPEN
            else:
                raise CircuitBreakerOpenError("Circuit is open")
        
        try:
            result = func(*args, **kwargs)
            
            # Handle successful execution
            if self._state == CircuitState.HALF_OPEN:
                self._half_open_successes += 1
                if self._half_open_successes >= self._half_open_max_calls:
                    logger.info("Circuit closed, system recovered")
                    self._reset()
            
            return result
            
        except Exception as e:
            # Handle failure
            self._last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                self._failure_count += 1
                if self._failure_count >= self._failure_threshold:
                    logger.warning(f"Circuit opened after {self._failure_count} failures")
                    self._state = CircuitState.OPEN
            
            elif self._state == CircuitState.HALF_OPEN:
                logger.warning("Circuit re-opened due to failure during recovery")
                self._state = CircuitState.OPEN
                self._half_open_successes = 0
            
            raise e
    
    def _reset(self):
        """Reset the circuit breaker to closed state."""
        self._state = CircuitState.CLOSED
        self._failure_count = 0
        self._half_open_successes = 0


class CircuitBreakerOpenError(Exception):
    """Raised when a circuit is open and a call is attempted."""
    pass


class ResiliencePolicy:
    """Configuration for resilience mechanisms."""
    def __init__(
        self,
        retry_attempts: int = 3,
        retry_delay_ms: int = 500,
        timeout_ms: int = 5000,
        circuit_breaker_enabled: bool = True,
        fallback_enabled: bool = True
    ):
        self.retry_attempts = retry_attempts
        self.retry_delay_ms = retry_delay_ms
        self.timeout_ms = timeout_ms
        self.circuit_breaker_enabled = circuit_breaker_enabled
        self.fallback_enabled = fallback_enabled


class ResilientSystem:
    """
    Manages system-wide resilience policies and circuit breakers.
    """
    
    def __init__(self):
        self._circuit_breakers: Dict[str, CircuitBreaker] = {}
        self._global_policy = ResiliencePolicy()
        self._component_policies: Dict[str, ResiliencePolicy] = {}
    
    def with_resilience(
        self,
        component_name: str,
        fallback_func: Optional[FallbackFunc] = None
    ):
        """
        Decorator to add resilience to a function.
        
        Args:
            component_name: Name of the component (used for circuit breaker identification)
            fallback_func: Function to call if the primary function fails
            
        Returns:
            Decorated function with resilience mechanisms
        """
        def decorator(func):
            @functools.wraps(func)
            def wrapper(*args, **kwargs):
                # Get policy for this component
                policy = self._component_policies.get(
                    component_name, self._global_policy
                )
                
                # Get or create circuit breaker for this component
                if policy.circuit_breaker_enabled:
                    if component_name not in self._circuit_breakers:
                        self._circuit_breakers[component_name] = CircuitBreaker()
                    circuit = self._circuit_breakers[component_name]
                
                # Try primary execution with retries
                exception = None
                for attempt in range(policy.retry_attempts):
                    try:
                        if policy.circuit_breaker_enabled:
                            return circuit.execute(func, *args, **kwargs)
                        else:
                            return func(*args, **kwargs)
                    except CircuitBreakerOpenError:
                        logger.warning(f"Circuit open for {component_name}, using fallback")
                        break
                    except Exception as e:
                        logger.warning(
                            f"Attempt {attempt+1} failed for {component_name}: {str(e)}"
                        )
                        exception = e
                        time.sleep(policy.retry_delay_ms / 1000.0)
                
                # If we reach here, all attempts failed or circuit is open
                if fallback_func and policy.fallback_enabled:
                    logger.info(f"Using fallback for {component_name}")
                    return fallback_func(*args, **kwargs)
                
                # No fallback or fallback disabled
                if exception:
                    raise exception
                raise CircuitBreakerOpenError(
                    f"Circuit open for {component_name} and no fallback available"
                )
            
            return wrapper
        
        return decorator
    
    def set_policy(self, component_name: str, policy: ResiliencePolicy):
        """Set resilience policy for a specific component."""
        self._component_policies[component_name] = policy
    
    def reset_circuit(self, component_name: str):
        """Force reset a circuit breaker."""
        if component_name in self._circuit_breakers:
            self._circuit_breakers[component_name]._reset()


# Global resilience system instance
resilience_system = ResilientSystem()


# Specialized resilience utilities
def create_offline_capable_client(
    service_name: str,
    online_factory: Callable[..., Any],
    offline_factory: Callable[..., Any]
) -> Any:
    """
    Creates a client that can operate in both online and offline modes.
    
    Args:
        service_name: Name of the service
        online_factory: Function that creates the online client
        offline_factory: Function that creates the offline client
        
    Returns:
        A client that transparently switches between modes
    """
    client = None
    offline_mode = False
    
    try:
        client = online_factory()
        logger.info(f"{service_name} client initialized in online mode")
        return client
    except Exception as e:
        logger.warning(
            f"Failed to initialize {service_name} in online mode: {str(e)}"
            f" - Falling back to offline mode"
        )
        offline_mode = True
        return offline_factory()


# Example implementations for the DBMemoryTree and Traffic Agent
def create_resilient_db_memory_tree(
    connection_string: str, 
    max_retries: int = 3,
    cache_dir: str = "/var/lib/mcp-zero/local_cache"
) -> Any:
    """
    Creates a DBMemoryTree that starts in offline mode and connects when possible.
    
    Args:
        connection_string: Database connection string
        max_retries: Maximum connection attempts
        cache_dir: Directory for local cache storage
        
    Returns:
        DBMemoryTree instance with resilience capabilities
    """
    # Implementation would go here, based on the actual DBMemoryTree class
    
    # Example pseudocode:
    # db_tree = DBMemoryTree(connection_string, start_offline=True, cache_dir=cache_dir)
    # db_tree.enable_resilience(max_retries=max_retries)
    # return db_tree
    
    pass


def create_resilient_traffic_agent(
    acceleration_server: Optional[str] = None,
    local_processing_path: str = "/var/lib/mcp-zero/local_processing"
) -> Any:
    """
    Creates a Traffic Agent that gracefully falls back to local processing.
    
    Args:
        acceleration_server: URL of the acceleration server
        local_processing_path: Path for local processing modules
        
    Returns:
        Traffic Agent with resilience capabilities
    """
    # Implementation would go here, based on the actual TrafficAgent class
    
    # Example pseudocode:
    # def online_factory():
    #     return TrafficAgent(acceleration_server=acceleration_server)
    #
    # def offline_factory():
    #     return TrafficAgent(local_processing=True, modules_path=local_processing_path)
    #
    # return create_offline_capable_client(
    #     "TrafficAgent", online_factory, offline_factory
    # )
    
    pass
