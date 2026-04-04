"""
Rate Limit Storage Operations
Handles Redis operations for rate limiting with fallback strategies
"""
import time
import json
import logging
from typing import Optional, Dict, Any, Tuple
from dataclasses import dataclass
from app.core.redis_config import get_async_redis, redis_manager
import redis.asyncio as aioredis

logger = logging.getLogger(__name__)


@dataclass
class RateLimitResult:
    """Result of rate limit check"""
    allowed: bool
    current_count: int
    limit: int
    window_size: int
    reset_time: int
    retry_after: Optional[int] = None


class CircuitBreaker:
    """Simple circuit breaker for Redis operations"""
    
    def __init__(self, failure_threshold: int = 5, recovery_timeout: int = 60):
        self.failure_threshold = failure_threshold
        self.recovery_timeout = recovery_timeout
        self.failure_count = 0
        self.last_failure_time = 0
        self.state = "CLOSED"  # CLOSED, OPEN, HALF_OPEN
    
    def is_open(self) -> bool:
        """Check if circuit is open"""
        if self.state == "OPEN":
            if time.time() - self.last_failure_time > self.recovery_timeout:
                self.state = "HALF_OPEN"
                return False
            return True
        return False
    
    def record_success(self):
        """Record successful operation"""
        self.failure_count = 0
        self.state = "CLOSED"
    
    def record_failure(self):
        """Record failed operation"""
        self.failure_count += 1
        self.last_failure_time = time.time()
        
        if self.failure_count >= self.failure_threshold:
            self.state = "OPEN"
            logger.warning(f"Circuit breaker opened after {self.failure_count} failures")


class RateLimitStorage:
    """Redis-based rate limit storage with circuit breaker"""
    
    def __init__(self):
        self.circuit_breaker = CircuitBreaker()
        self._redis_client: Optional[aioredis.Redis] = None
    
    async def _get_redis(self) -> Optional[aioredis.Redis]:
        """Get Redis client with error handling"""
        try:
            if self._redis_client is None:
                self._redis_client = await get_async_redis()
            return self._redis_client
        except Exception as e:
            logger.error(f"Failed to get Redis client: {e}")
            return None
    
    def _generate_key(self, identifier: str, window_start: int, window_size: int) -> str:
        """Generate Redis key for rate limiting"""
        return f"rate_limit:{identifier}:{window_start}:{window_size}"
    
    async def sliding_window_check(
        self,
        identifier: str,
        limit: int,
        window_size: int,
        current_time: Optional[float] = None
    ) -> RateLimitResult:
        """
        Sliding window rate limiting implementation
        
        Args:
            identifier: Unique identifier (user_id, ip, etc.)
            limit: Maximum requests allowed in window
            window_size: Window size in seconds
            current_time: Current timestamp (for testing)
        
        Returns:
            RateLimitResult with check results
        """
        if current_time is None:
            current_time = time.time()
        
        # If circuit breaker is open, allow requests (fail-open strategy)
        if self.circuit_breaker.is_open():
            logger.warning("Rate limiting circuit breaker is open - allowing all requests")
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                window_size=window_size,
                reset_time=int(current_time + window_size)
            )
        
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                # Fallback: allow request if Redis unavailable
                logger.warning("Redis unavailable - allowing request")
                return RateLimitResult(
                    allowed=True,
                    current_count=0,
                    limit=limit,
                    window_size=window_size,
                    reset_time=int(current_time + window_size)
                )
            
            # Use sliding window log approach
            window_start = current_time - window_size
            key = f"rate_limit:sliding:{identifier}"
            
            # Use Redis pipeline for atomic operations
            pipe = redis_client.pipeline()
            
            # Remove old entries outside the window
            pipe.zremrangebyscore(key, 0, window_start)
            
            # Count current entries in window
            pipe.zcard(key)
            
            # Add current request timestamp
            pipe.zadd(key, {str(current_time): current_time})
            
            # Set expiration
            pipe.expire(key, window_size + 1)
            
            # Execute pipeline
            results = await pipe.execute()
            
            # Get current count (after removing old entries, before adding new one)
            current_count = results[1]
            
            # Check if limit exceeded
            allowed = current_count < limit
            
            if not allowed:
                # Remove the request we just added since it's not allowed
                await redis_client.zrem(key, str(current_time))
            
            # Record success for circuit breaker
            self.circuit_breaker.record_success()
            
            return RateLimitResult(
                allowed=allowed,
                current_count=current_count + (1 if allowed else 0),
                limit=limit,
                window_size=window_size,
                reset_time=int(current_time + window_size),
                retry_after=window_size if not allowed else None
            )
            
        except Exception as e:
            logger.error(f"Rate limit check failed: {e}")
            self.circuit_breaker.record_failure()
            
            # Fail-open: allow request on error
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                window_size=window_size,
                reset_time=int(current_time + window_size)
            )
    
    async def fixed_window_check(
        self,
        identifier: str,
        limit: int,
        window_size: int,
        current_time: Optional[float] = None
    ) -> RateLimitResult:
        """
        Fixed window rate limiting implementation (more efficient)
        
        Args:
            identifier: Unique identifier
            limit: Maximum requests allowed in window
            window_size: Window size in seconds
            current_time: Current timestamp
        
        Returns:
            RateLimitResult with check results
        """
        if current_time is None:
            current_time = time.time()
        
        # Circuit breaker check
        if self.circuit_breaker.is_open():
            logger.warning("Rate limiting circuit breaker is open - allowing all requests")
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                window_size=window_size,
                reset_time=int(current_time + window_size)
            )
        
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return RateLimitResult(
                    allowed=True,
                    current_count=0,
                    limit=limit,
                    window_size=window_size,
                    reset_time=int(current_time + window_size)
                )
            
            # Calculate window start
            window_start = int(current_time // window_size) * window_size
            key = self._generate_key(identifier, window_start, window_size)
            
            # Use Lua script for atomic increment and expire
            lua_script = """
            local key = KEYS[1]
            local limit = tonumber(ARGV[1])
            local window_size = tonumber(ARGV[2])
            
            local current = redis.call('GET', key)
            if current == false then
                current = 0
            else
                current = tonumber(current)
            end
            
            if current < limit then
                local new_count = redis.call('INCR', key)
                redis.call('EXPIRE', key, window_size)
                return {1, new_count, limit}
            else
                return {0, current, limit}
            end
            """
            
            result = await redis_client.eval(lua_script, 1, key, limit, window_size)
            allowed, current_count, _ = result
            
            # Record success
            self.circuit_breaker.record_success()
            
            return RateLimitResult(
                allowed=bool(allowed),
                current_count=int(current_count),
                limit=limit,
                window_size=window_size,
                reset_time=window_start + window_size,
                retry_after=window_start + window_size - int(current_time) if not allowed else None
            )
            
        except Exception as e:
            logger.error(f"Fixed window rate limit check failed: {e}")
            self.circuit_breaker.record_failure()
            
            # Fail-open
            return RateLimitResult(
                allowed=True,
                current_count=0,
                limit=limit,
                window_size=window_size,
                reset_time=int(current_time + window_size)
            )
    
    async def get_rate_limit_info(self, identifier: str, window_size: int) -> Dict[str, Any]:
        """Get current rate limit information for identifier"""
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return {"error": "Redis unavailable"}
            
            current_time = time.time()
            
            # For sliding window
            sliding_key = f"rate_limit:sliding:{identifier}"
            window_start = current_time - window_size
            
            # Remove old entries and count current
            await redis_client.zremrangebyscore(sliding_key, 0, window_start)
            current_count = await redis_client.zcard(sliding_key)
            
            # Get all timestamps in current window
            timestamps = await redis_client.zrange(sliding_key, 0, -1, withscores=True)
            
            return {
                "identifier": identifier,
                "current_count": current_count,
                "window_size": window_size,
                "window_start": window_start,
                "current_time": current_time,
                "timestamps": [float(score) for _, score in timestamps],
                "circuit_breaker_state": self.circuit_breaker.state
            }
            
        except Exception as e:
            logger.error(f"Failed to get rate limit info: {e}")
            return {"error": str(e)}
    
    async def reset_rate_limit(self, identifier: str) -> bool:
        """Reset rate limit for identifier"""
        try:
            redis_client = await self._get_redis()
            if not redis_client:
                return False
            
            # Remove both sliding and fixed window keys
            sliding_key = f"rate_limit:sliding:{identifier}"
            pattern = f"rate_limit:{identifier}:*"
            
            # Delete sliding window key
            await redis_client.delete(sliding_key)
            
            # Delete fixed window keys
            keys = await redis_client.keys(pattern)
            if keys:
                await redis_client.delete(*keys)
            
            logger.info(f"Rate limit reset for identifier: {identifier}")
            return True
            
        except Exception as e:
            logger.error(f"Failed to reset rate limit: {e}")
            return False


# Global storage instance
rate_limit_storage = RateLimitStorage()