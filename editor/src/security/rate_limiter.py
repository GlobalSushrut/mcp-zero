"""
Rate Limiter for MCP Zero Editor

Provides resilient rate limiting with offline-first capability.
"""

import time
import threading
import logging
from typing import Dict, Any, Optional

logger = logging.getLogger("mcp_zero.editor.security.rate_limiter")

class RateLimiter:
    """
    Token bucket rate limiter with offline-first resilience.
    
    Follows offline-first approach:
    - Starts in offline mode by default (following DBMemoryTree pattern)
    - Only attempts one connection to distributed cache
    - Falls back to local memory mode permanently if distributed cache unavailable
    """
    
    def __init__(
        self, 
        name: str = "default", 
        requests_per_period: int = 60,
        period_seconds: int = 60,
        cache_dir: Optional[str] = None,
        offline_first: bool = True
    ):
        """
        Initialize token bucket rate limiter.
        
        Args:
            name: Name of the rate limiter
            requests_per_period: Number of requests allowed per period
            period_seconds: Period length in seconds
            cache_dir: Directory for local cache
            offline_first: Whether to start in offline mode
        """
        self.name = name
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.tokens_per_second = requests_per_period / period_seconds
        self.offline_mode = offline_first
        self.cache_dir = cache_dir
        
        # Token bucket state
        self.last_refill = time.time()
        self.tokens = requests_per_period
        
        # Thread safety
        self._lock = threading.RLock()
        self._remote_attempt_made = False
        
        logger.info(f"Rate limiter '{name}' initialized in {'offline' if offline_first else 'online'} mode")
        logger.info(f"Rate limit: {requests_per_period} requests per {period_seconds} seconds")
    
    def _refill_tokens(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.time()
        elapsed = now - self.last_refill
        
        # Calculate tokens to add
        new_tokens = elapsed * self.tokens_per_second
        
        # Update tokens (not exceeding max)
        self.tokens = min(self.tokens + new_tokens, self.requests_per_period)
        self.last_refill = now
    
    def check_rate_limit(self, tokens_needed: int = 1) -> bool:
        """
        Check if operation is allowed by rate limit.
        
        Args:
            tokens_needed: Number of tokens needed for operation
            
        Returns:
            True if operation is allowed
        """
        with self._lock:
            # Refill tokens
            self._refill_tokens()
            
            # Check if enough tokens available
            if self.tokens >= tokens_needed:
                self.tokens -= tokens_needed
                return True
            else:
                return False
                
    def allow_request(self, request_type: str = "default", tokens_needed: int = 1) -> bool:
        """
        Check if a request is allowed by the rate limiter.
        This is an adapter method for the LLMService.
        
        Args:
            request_type: Type of request (unused)
            tokens_needed: Number of tokens needed
            
        Returns:
            True if request is allowed
        """
        return self.check_rate_limit(tokens_needed)
    
    def wait_for_token(self, tokens_needed: int = 1, max_wait: float = 60.0) -> bool:
        """
        Wait until rate limit allows operation.
        
        Args:
            tokens_needed: Number of tokens needed for operation
            max_wait: Maximum wait time in seconds
            
        Returns:
            True if operation is allowed within max_wait time
        """
        start_time = time.time()
        
        while time.time() - start_time < max_wait:
            with self._lock:
                # Refill tokens
                self._refill_tokens()
                
                # Check if enough tokens available
                if self.tokens >= tokens_needed:
                    self.tokens -= tokens_needed
                    return True
            
            # Wait for a short time before checking again
            time.sleep(0.1)
        
        # Max wait time exceeded
        return False
    
    def _try_distributed_cache(self) -> bool:
        """
        Try to connect to distributed rate limit cache.
        
        Following the pattern from Traffic Agent and DBMemoryTree:
        - Only attempts to connect once
        - Permanently switches to local mode if service unavailable
        
        Returns:
            True if connected successfully
        """
        # Skip if already attempted or in offline mode
        if self._remote_attempt_made or self.offline_mode:
            return False
            
        try:
            # Mark that we've made the attempt
            self._remote_attempt_made = True
            
            # In a real implementation, this would connect to a distributed cache
            logger.info(f"Distributed rate limit cache not available for '{self.name}', using local memory")
            return False
            
        except Exception as e:
            logger.warning(f"Error connecting to distributed rate limit cache: {str(e)}")
            return False
    
    def is_healthy(self) -> bool:
        """
        Check if rate limiter is healthy.
        
        Returns:
            True if healthy
        """
        # Rate limiter is always healthy in offline mode
        return True

# Global registry of rate limiters
_limiters: Dict[str, RateLimiter] = {}
_registry_lock = threading.RLock()

def create_limiter(
    name: str,
    requests_per_period: int = 60,
    period_seconds: int = 60,
    cache_dir: Optional[str] = None,
    offline_first: bool = True
) -> RateLimiter:
    """
    Create a new rate limiter.
    
    Args:
        name: Name of the rate limiter
        requests_per_period: Number of requests allowed per period
        period_seconds: Period length in seconds
        cache_dir: Directory for local cache
        offline_first: Whether to start in offline mode
        
    Returns:
        Rate limiter instance
    """
    with _registry_lock:
        if name in _limiters:
            logger.warning(f"Rate limiter '{name}' already exists, returning existing instance")
            return _limiters[name]
            
        limiter = RateLimiter(
            name=name,
            requests_per_period=requests_per_period,
            period_seconds=period_seconds,
            cache_dir=cache_dir,
            offline_first=offline_first
        )
        
        _limiters[name] = limiter
        return limiter

def get_limiter(name: str) -> Optional[RateLimiter]:
    """
    Get an existing rate limiter by name.
    
    Args:
        name: Name of the rate limiter
        
    Returns:
        Rate limiter instance or None if not found
    """
    with _registry_lock:
        return _limiters.get(name)
