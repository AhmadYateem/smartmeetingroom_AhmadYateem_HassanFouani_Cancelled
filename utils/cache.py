"""
Redis caching utilities for performance optimization.
Part II Enhancement: Performance Optimization - Caching Mechanism
"""

import json
import redis
from functools import wraps
from typing import Any, Callable, Optional
from configs.config import Config
from utils.logger import setup_logger

logger = setup_logger(__name__)


class RedisCache:
    """
    Redis cache manager for application-wide caching.

    Provides methods for caching frequently accessed data to improve performance.
    """

    def __init__(self):
        """Initialize Redis connection."""
        try:
            self.redis_client = redis.Redis(
                host=Config.REDIS_HOST,
                port=Config.REDIS_PORT,
                db=Config.REDIS_DB,
                decode_responses=True,
                socket_connect_timeout=5,
                socket_timeout=5
            )
            # Test connection
            self.redis_client.ping()
            self.enabled = True
            logger.info("Redis cache initialized successfully")
        except redis.ConnectionError:
            logger.warning("Redis connection failed. Caching disabled.")
            self.redis_client = None
            self.enabled = False
        except Exception as e:
            logger.error(f"Redis initialization error: {str(e)}")
            self.redis_client = None
            self.enabled = False

    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache.

        Args:
            key: Cache key

        Returns:
            Cached value or None if not found
        """
        if not self.enabled:
            return None

        try:
            value = self.redis_client.get(key)
            if value:
                logger.debug(f"Cache hit for key: {key}")
                return json.loads(value)

            logger.debug(f"Cache miss for key: {key}")
            return None

        except Exception as e:
            logger.error(f"Cache get error for key {key}: {str(e)}")
            return None

    def set(self, key: str, value: Any, ttl: int = None) -> bool:
        """
        Set value in cache.

        Args:
            key: Cache key
            value: Value to cache
            ttl: Time to live in seconds (default from config)

        Returns:
            Boolean indicating success
        """
        if not self.enabled:
            return False

        try:
            if ttl is None:
                ttl = Config.CACHE_TTL

            serialized = json.dumps(value)
            self.redis_client.setex(key, ttl, serialized)

            logger.debug(f"Cache set for key: {key} (TTL: {ttl}s)")
            return True

        except Exception as e:
            logger.error(f"Cache set error for key {key}: {str(e)}")
            return False

    def delete(self, key: str) -> bool:
        """
        Delete value from cache.

        Args:
            key: Cache key

        Returns:
            Boolean indicating success
        """
        if not self.enabled:
            return False

        try:
            self.redis_client.delete(key)
            logger.debug(f"Cache deleted for key: {key}")
            return True

        except Exception as e:
            logger.error(f"Cache delete error for key {key}: {str(e)}")
            return False

    def delete_pattern(self, pattern: str) -> int:
        """
        Delete all keys matching pattern.

        Args:
            pattern: Key pattern (e.g., 'user:*')

        Returns:
            Number of keys deleted
        """
        if not self.enabled:
            return 0

        try:
            keys = self.redis_client.keys(pattern)
            if keys:
                deleted = self.redis_client.delete(*keys)
                logger.debug(f"Cache deleted {deleted} keys matching pattern: {pattern}")
                return deleted
            return 0

        except Exception as e:
            logger.error(f"Cache delete pattern error for {pattern}: {str(e)}")
            return 0

    def clear_all(self) -> bool:
        """
        Clear all cache entries.

        Returns:
            Boolean indicating success
        """
        if not self.enabled:
            return False

        try:
            self.redis_client.flushdb()
            logger.info("Cache cleared")
            return True

        except Exception as e:
            logger.error(f"Cache clear error: {str(e)}")
            return False

    def exists(self, key: str) -> bool:
        """
        Check if key exists in cache.

        Args:
            key: Cache key

        Returns:
            Boolean indicating if key exists
        """
        if not self.enabled:
            return False

        try:
            return bool(self.redis_client.exists(key))
        except Exception as e:
            logger.error(f"Cache exists error for key {key}: {str(e)}")
            return False

    def get_ttl(self, key: str) -> int:
        """
        Get remaining TTL for key.

        Args:
            key: Cache key

        Returns:
            TTL in seconds, -1 if no expiry, -2 if key doesn't exist
        """
        if not self.enabled:
            return -2

        try:
            return self.redis_client.ttl(key)
        except Exception as e:
            logger.error(f"Cache TTL error for key {key}: {str(e)}")
            return -2

    def increment(self, key: str, amount: int = 1) -> Optional[int]:
        """
        Increment a counter in cache.

        Args:
            key: Cache key
            amount: Amount to increment by

        Returns:
            New value or None on error
        """
        if not self.enabled:
            return None

        try:
            return self.redis_client.incrby(key, amount)
        except Exception as e:
            logger.error(f"Cache increment error for key {key}: {str(e)}")
            return None


# Global cache instance
cache = RedisCache()


def cached(key_prefix: str, ttl: int = None, key_builder: Callable = None):
    """
    Decorator to cache function results.

    Args:
        key_prefix: Prefix for cache key
        ttl: Time to live in seconds
        key_builder: Optional function to build cache key from args

    Returns:
        Decorated function
    """
    def decorator(func: Callable) -> Callable:
        @wraps(func)
        def wrapper(*args, **kwargs):
            # Build cache key
            if key_builder:
                cache_key = f"{key_prefix}:{key_builder(*args, **kwargs)}"
            else:
                # Default: use function name and arguments
                args_key = ':'.join(str(arg) for arg in args)
                kwargs_key = ':'.join(f"{k}={v}" for k, v in sorted(kwargs.items()))
                cache_key = f"{key_prefix}:{func.__name__}:{args_key}:{kwargs_key}"

            # Try to get from cache
            cached_result = cache.get(cache_key)
            if cached_result is not None:
                logger.debug(f"Returning cached result for {func.__name__}")
                return cached_result

            # Execute function
            result = func(*args, **kwargs)

            # Cache result
            cache.set(cache_key, result, ttl)

            return result

        # Add cache control methods to decorated function
        wrapper.invalidate = lambda: cache.delete_pattern(f"{key_prefix}:*")
        wrapper.cache_key_prefix = key_prefix

        return wrapper

    return decorator


def invalidate_cache(key_prefix: str):
    """
    Invalidate all cache entries with given prefix.

    Args:
        key_prefix: Cache key prefix to invalidate
    """
    cache.delete_pattern(f"{key_prefix}:*")
    logger.info(f"Invalidated cache for prefix: {key_prefix}")


def get_cache_stats() -> dict:
    """
    Get cache statistics.

    Returns:
        Dictionary with cache statistics
    """
    if not cache.enabled:
        return {
            'enabled': False,
            'message': 'Cache is disabled'
        }

    try:
        info = cache.redis_client.info('stats')
        return {
            'enabled': True,
            'total_commands': info.get('total_commands_processed', 0),
            'keyspace_hits': info.get('keyspace_hits', 0),
            'keyspace_misses': info.get('keyspace_misses', 0),
            'hit_rate': (
                info.get('keyspace_hits', 0) /
                (info.get('keyspace_hits', 0) + info.get('keyspace_misses', 1))
            ) * 100
        }
    except Exception as e:
        logger.error(f"Error getting cache stats: {str(e)}")
        return {'enabled': True, 'error': str(e)}
