import time
import asyncio
from typing import Any, Dict, Optional, Union
from functools import wraps
from collections import OrderedDict


class SimpleCache:
    """
    A simple in-memory cache with TTL (Time To Live) functionality
    """
    def __init__(self, max_size: int = 1000, default_ttl: int = 300):  # 5 minutes default
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.cache: Dict[str, Dict[str, Any]] = OrderedDict()

    def _cleanup_expired(self):
        """
        Remove expired entries from the cache
        """
        now = time.time()
        expired_keys = [
            key for key, value in self.cache.items()
            if now > value['expires_at']
        ]
        for key in expired_keys:
            del self.cache[key]

    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """
        Set a value in the cache with an optional TTL
        """
        self._cleanup_expired()

        if ttl is None:
            ttl = self.default_ttl

        expires_at = time.time() + ttl

        # If cache is at max capacity, remove oldest entry
        if len(self.cache) >= self.max_size:
            oldest_key = next(iter(self.cache))
            del self.cache[oldest_key]

        self.cache[key] = {
            'value': value,
            'expires_at': expires_at
        }

        # Move to end to mark as most recently used
        self.cache.move_to_end(key)

        return True

    def get(self, key: str) -> Optional[Any]:
        """
        Get a value from the cache
        """
        self._cleanup_expired()

        if key in self.cache:
            item = self.cache[key]
            # Move to end to mark as most recently used
            self.cache.move_to_end(key)
            return item['value']

        return None

    def delete(self, key: str) -> bool:
        """
        Delete a key from the cache
        """
        if key in self.cache:
            del self.cache[key]
            return True
        return False

    def clear(self):
        """
        Clear all entries from the cache
        """
        self.cache.clear()

    def exists(self, key: str) -> bool:
        """
        Check if a key exists in the cache
        """
        self._cleanup_expired()
        return key in self.cache


# Global cache instance
cache = SimpleCache(max_size=1000, default_ttl=300)  # 5 minute default TTL


def cached(ttl: int = 300, cache_key_func=None):
    """
    Decorator to cache function results
    """
    def decorator(func):
        @wraps(func)
        async def async_wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                key = cache_key_func(*args, **kwargs)
            else:
                # Default cache key generation
                key_parts = [func.__name__] + list(args)
                key = ":".join(str(part) for part in key_parts)

            # Check if result is in cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Call the function and cache the result
            result = await func(*args, **kwargs)
            cache.set(key, result, ttl)

            return result

        @wraps(func)
        def sync_wrapper(*args, **kwargs):
            # Generate cache key
            if cache_key_func:
                key = cache_key_func(*args, **kwargs)
            else:
                # Default cache key generation
                key_parts = [func.__name__] + list(args)
                key = ":".join(str(part) for part in key_parts)

            # Check if result is in cache
            cached_result = cache.get(key)
            if cached_result is not None:
                return cached_result

            # Call the function and cache the result
            result = func(*args, **kwargs)
            cache.set(key, result, ttl)

            return result

        # Return the appropriate wrapper based on whether the function is async
        if asyncio.iscoroutinefunction(func):
            return async_wrapper
        else:
            return sync_wrapper

    return decorator


# Example usage functions
async def get_user_tasks_cached(user_id: str):
    """
    Example function that would benefit from caching
    """
    # This would normally fetch from database
    # For example purposes, we'll simulate a delay
    await asyncio.sleep(0.1)
    return [{"id": 1, "title": "Sample task", "status": "pending"}]


# Predefined cache keys for common operations
def get_user_tasks_cache_key(user_id: str, status: str = "all"):
    return f"user_tasks:{user_id}:{status}"


def get_task_cache_key(task_id: int, user_id: str):
    return f"task:{user_id}:{task_id}"