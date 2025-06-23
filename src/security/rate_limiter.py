"""
Rate Limiter for MCP Zero API

Implements a resilient rate limiting system that works in both online and offline modes,
following the same pattern as the successful DBMemoryTree and Traffic Agent improvements.
"""

import time
import threading
import logging
from typing import Dict, Optional
from enum import Enum

logger = logging.getLogger("mcp_zero.security.rate_limiter")

class RateLimiterMode(Enum):
    """Operating modes for the rate limiter."""
    ONLINE = "online"   # Using shared state from distributed cache
    OFFLINE = "offline"  # Using local memory only


class TokenBucketRateLimiter:
    """
    Resilient token bucket rate limiter for MCP Zero API endpoints.
    
    This component starts in offline mode by default and attempts to
    connect to the distributed cache once. If connection fails, it
    remains in offline mode using local memory.
    """
    
    def __init__(
        self, 
        name: str,
        requests_per_period: int = 100,
        period_seconds: int = 60,
        distributed_cache_url: Optional[str] = None
    ):
        """
        Initialize rate limiter.
        
        Args:
            name: Unique name for this rate limiter instance
            requests_per_period: Number of allowed requests per period
            period_seconds: Period length in seconds
            distributed_cache_url: URL for distributed cache (None for offline only)
        """
        self.name = name
        self.requests_per_period = requests_per_period
        self.period_seconds = period_seconds
        self.refill_rate = self.requests_per_period / self.period_seconds
        self.cache_url = distributed_cache_url
        
        # Start in offline mode by default (like DBMemoryTree)
        self.mode = RateLimiterMode.OFFLINE
        
        # Local state
        self._token_buckets = {}  # client_id -> {tokens, last_refill}
        self._lock = threading.RLock()
        
        # Try to connect to distributed cache if URL provided
        if distributed_cache_url:
            self._try_connect()
        
        logger.info(
            f"Rate limiter '{name}' initialized ({requests_per_period}/{period_seconds}s) "
            f"in {self.mode.value} mode"
        )
    
    def _try_connect(self) -> bool:
        """
        Attempt to connect to distributed cache.
        
        Following the Traffic Agent pattern, this only tries once and then
        permanently settles on the determined mode.
        
        Returns:
            True if connection successful, False otherwise
        """
        try:
            import requests
            response = requests.get(
                f"{self.cache_url}/health",
                timeout=2.0
            )
            
            if response.status_code == 200:
                self.mode = RateLimiterMode.ONLINE
                logger.info(f"Connected to distributed cache: {self.cache_url}")
                return True
            else:
                logger.warning(
                    f"Failed to connect to distributed cache: {response.status_code}"
                )
                return False
                
        except Exception as e:
            logger.warning(
                f"Failed to connect to distributed cache: {str(e)}"
                f" - Operating in offline mode"
            )
            return False
    
    def allow_request(self, client_id: str) -> bool:
        """
        Check if request is allowed under rate limits.
        
        Args:
            client_id: Identifier for the client (e.g., IP, API key)
            
        Returns:
            True if request is allowed, False if rate limited
        """
        # Try online mode first if enabled
        if self.mode == RateLimiterMode.ONLINE:
            try:
                return self._online_check(client_id)
            except Exception as e:
                logger.warning(f"Error in online rate limiting: {str(e)}")
                # Fall back to offline mode permanently
                self.mode = RateLimiterMode.OFFLINE
                logger.warning("Switched to offline rate limiting due to cache issues")
        
        # Offline mode (or fallback from online failure)
        return self._offline_check(client_id)
    
    def _offline_check(self, client_id: str) -> bool:
        """
        Check rate limit using local token bucket.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if allowed, False if limited
        """
        with self._lock:
            now = time.time()
            
            # Initialize bucket if not exists
            if client_id not in self._token_buckets:
                self._token_buckets[client_id] = {
                    "tokens": self.requests_per_period,
                    "last_refill": now
                }
            
            bucket = self._token_buckets[client_id]
            
            # Calculate tokens to add based on time elapsed
            time_passed = now - bucket["last_refill"]
            tokens_to_add = time_passed * self.refill_rate
            
            # Refill bucket
            bucket["tokens"] = min(
                self.requests_per_period,  # Cap at max
                bucket["tokens"] + tokens_to_add
            )
            bucket["last_refill"] = now
            
            # Check if we have enough tokens
            if bucket["tokens"] >= 1:
                bucket["tokens"] -= 1
                return True
            else:
                return False
    
    def _online_check(self, client_id: str) -> bool:
        """
        Check rate limit using distributed cache.
        
        Args:
            client_id: Client identifier
            
        Returns:
            True if allowed, False if limited
        """
        import requests
        
        try:
            response = requests.post(
                f"{self.cache_url}/rate_limit",
                json={
                    "limiter_name": self.name,
                    "client_id": client_id,
                    "tokens_requested": 1,
                    "refill_rate": self.refill_rate,
                    "capacity": self.requests_per_period
                },
                timeout=1.0
            )
            
            if response.status_code != 200:
                # Fall back to offline if server error
                logger.warning(
                    f"Rate limit server error: {response.status_code}"
                )
                return self._offline_check(client_id)
                
            result = response.json()
            return result.get("allowed", False)
            
        except Exception as e:
            logger.warning(f"Error in online rate limiting: {str(e)}")
            return self._offline_check(client_id)


# Global rate limiters registry
_limiters = {}


def create_limiter(
    name: str,
    requests_per_period: int = 100,
    period_seconds: int = 60,
    distributed_cache_url: Optional[str] = None
) -> TokenBucketRateLimiter:
    """
    Create and register a new rate limiter.
    
    Args:
        name: Unique name for the rate limiter
        requests_per_period: Number of allowed requests per period
        period_seconds: Period length in seconds
        distributed_cache_url: URL for distributed cache
        
    Returns:
        Rate limiter instance
    """
    if name in _limiters:
        return _limiters[name]
        
    limiter = TokenBucketRateLimiter(
        name=name,
        requests_per_period=requests_per_period,
        period_seconds=period_seconds,
        distributed_cache_url=distributed_cache_url
    )
    
    _limiters[name] = limiter
    return limiter


def get_limiter(name: str) -> Optional[TokenBucketRateLimiter]:
    """
    Get an existing rate limiter by name.
    
    Args:
        name: Rate limiter name
        
    Returns:
        Rate limiter instance or None if not found
    """
    return _limiters.get(name)


def allow_request(name: str, client_id: str) -> bool:
    """
    Check if request is allowed under rate limits.
    
    Args:
        name: Rate limiter name
        client_id: Client identifier
        
    Returns:
        True if allowed, False if limited
    """
    limiter = get_limiter(name)
    if not limiter:
        logger.warning(f"Rate limiter '{name}' not found, allowing request")
        return True
        
    return limiter.allow_request(client_id)
