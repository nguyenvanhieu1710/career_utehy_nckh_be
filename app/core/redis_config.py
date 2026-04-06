"""
Redis Configuration and Connection Management
"""
import os
import redis
import redis.asyncio as aioredis
from typing import Optional
import logging
from dotenv import load_dotenv

load_dotenv()
logger = logging.getLogger(__name__)

class RedisConfig:
    """Redis configuration settings"""
    
    def __init__(self):
        self.host = os.getenv("REDIS_HOST", "localhost")
        self.port = int(os.getenv("REDIS_PORT", 6379))
        self.password = os.getenv("REDIS_PASSWORD", "")
        self.username = os.getenv("REDIS_USERNAME", "default")
        self.db = int(os.getenv("REDIS_DB", 0))
        self.decode_responses = os.getenv("REDIS_DECODE_RESPONSES", "True").lower() == "true"
        self.max_connections = int(os.getenv("REDIS_MAX_CONNECTIONS", 20))
        self.socket_timeout = int(os.getenv("REDIS_SOCKET_TIMEOUT", 5))
        self.socket_connect_timeout = int(os.getenv("REDIS_SOCKET_CONNECT_TIMEOUT", 5))
        self.retry_on_timeout = os.getenv("REDIS_RETRY_ON_TIMEOUT", "True").lower() == "true"
        
        # Rate limiting specific settings
        self.rate_limit_enabled = os.getenv("RATE_LIMIT_ENABLED", "True").lower() == "true"
        self.rate_limit_storage = os.getenv("RATE_LIMIT_STORAGE", "redis")
        self.rate_limit_default_limit = int(os.getenv("RATE_LIMIT_DEFAULT_LIMIT", 100))
        self.rate_limit_default_window = int(os.getenv("RATE_LIMIT_DEFAULT_WINDOW", 60))

    def get_connection_params(self) -> dict:
        """Get Redis connection parameters"""
        params = {
            "host": self.host,
            "port": self.port,
            "db": self.db,
            "decode_responses": self.decode_responses,
            "socket_timeout": self.socket_timeout,
            "socket_connect_timeout": self.socket_connect_timeout,
            "retry_on_timeout": self.retry_on_timeout,
        }
        
        # Add authentication if provided
        if self.password:
            params["password"] = self.password
        if self.username and self.username != "default":
            params["username"] = self.username
            
        return params

    def get_connection_pool_params(self) -> dict:
        """Get Redis connection pool parameters"""
        params = self.get_connection_params()
        params["max_connections"] = self.max_connections
        return params


class RedisManager:
    """Redis connection manager with health checking"""
    
    def __init__(self):
        self.config = RedisConfig()
        self._sync_client: Optional[redis.Redis] = None
        self._async_client: Optional[aioredis.Redis] = None
        self._connection_pool: Optional[redis.ConnectionPool] = None
        self._async_connection_pool: Optional[aioredis.ConnectionPool] = None
        self._is_connected = False

    def get_sync_client(self) -> redis.Redis:
        """Get synchronous Redis client"""
        if self._sync_client is None:
            try:
                if self._connection_pool is None:
                    self._connection_pool = redis.ConnectionPool(
                        **self.config.get_connection_pool_params()
                    )
                
                self._sync_client = redis.Redis(
                    connection_pool=self._connection_pool
                )
                
                # Test connection
                self._sync_client.ping()
                self._is_connected = True
                # logger.info(f"✅ Redis connected: {self.config.host}:{self.config.port}")
                
            except Exception as e:
                logger.error(f"❌ Redis connection failed: {e}")
                self._is_connected = False
                raise
                
        return self._sync_client

    async def get_async_client(self) -> aioredis.Redis:
        """Get asynchronous Redis client"""
        if self._async_client is None:
            try:
                if self._async_connection_pool is None:
                    self._async_connection_pool = aioredis.ConnectionPool(
                        **self.config.get_connection_pool_params()
                    )
                
                self._async_client = aioredis.Redis(
                    connection_pool=self._async_connection_pool
                )
                
                # Test connection
                await self._async_client.ping()
                self._is_connected = True
                # logger.info(f"✅ Async Redis connected: {self.config.host}:{self.config.port}")
                
            except Exception as e:
                logger.error(f"❌ Async Redis connection failed: {e}")
                self._is_connected = False
                raise
                
        return self._async_client

    async def health_check(self) -> bool:
        """Check Redis connection health"""
        try:
            if self._async_client:
                await self._async_client.ping()
                return True
            elif self._sync_client:
                self._sync_client.ping()
                return True
            else:
                # Try to establish connection for health check
                client = await self.get_async_client()
                await client.ping()
                return True
        except Exception as e:
            logger.warning(f"Redis health check failed: {e}")
            self._is_connected = False
            return False

    def is_connected(self) -> bool:
        """Check if Redis is connected"""
        return self._is_connected

    async def close_connections(self):
        """Close all Redis connections"""
        try:
            if self._async_client:
                await self._async_client.aclose()
                self._async_client = None
                
            if self._sync_client:
                self._sync_client.close()
                self._sync_client = None
                
            if self._async_connection_pool:
                await self._async_connection_pool.aclose()
                self._async_connection_pool = None
                
            if self._connection_pool:
                self._connection_pool.disconnect()
                self._connection_pool = None
                
            self._is_connected = False
            logger.info("Redis connections closed")
            
        except Exception as e:
            logger.error(f"Error closing Redis connections: {e}")

    def get_info(self) -> dict:
        """Get Redis connection information"""
        return {
            "host": self.config.host,
            "port": self.config.port,
            "db": self.config.db,
            "connected": self._is_connected,
            "rate_limiting_enabled": self.config.rate_limit_enabled,
            "max_connections": self.config.max_connections
        }


# Global Redis manager instance
redis_manager = RedisManager()


# Convenience functions
def get_redis() -> redis.Redis:
    """Get synchronous Redis client"""
    return redis_manager.get_sync_client()


async def get_async_redis() -> aioredis.Redis:
    """Get asynchronous Redis client"""
    return await redis_manager.get_async_client()


async def redis_health_check() -> bool:
    """Check Redis health"""
    return await redis_manager.health_check()


def get_redis_info() -> dict:
    """Get Redis connection info"""
    return redis_manager.get_info()