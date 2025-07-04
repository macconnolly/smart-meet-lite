"""
Simple caching layer with TTL support for LLM operations.
Prevents duplicate expensive API calls.
"""

import time
import json
import hashlib
from typing import Dict, Any, Optional
import logging

logger = logging.getLogger(__name__)


class CacheLayer:
    """
    A simple in-memory cache with Time-To-Live (TTL) support.
    Used to cache expensive LLM operations and database queries.
    """
    
    def __init__(self, default_ttl: int = 3600):
        """
        Initialize cache with default TTL.
        
        Args:
            default_ttl: Default time-to-live in seconds (default: 1 hour)
        """
        self._cache: Dict[str, Any] = {}
        self._ttl: Dict[str, float] = {}
        self.default_ttl = default_ttl
        self._hits = 0
        self._misses = 0
        
    def get(self, key: str) -> Optional[Any]:
        """
        Get value from cache if it exists and hasn't expired.
        
        Args:
            key: Cache key
            
        Returns:
            Cached value if found and not expired, None otherwise
        """
        if key in self._cache and time.time() < self._ttl[key]:
            self._hits += 1
            logger.debug(f"Cache hit for key: {key[:32]}...")
            return self._cache[key]
            
        if key in self._cache:
            # Expired - remove from cache
            del self._cache[key]
            del self._ttl[key]
            logger.debug(f"Cache expired for key: {key[:32]}...")
            
        self._misses += 1
        return None
        
    def set(self, key: str, value: Any, ttl: Optional[int] = None):
        """
        Set value in cache with TTL.
        
        Args:
            key: Cache key
            value: Value to cache
            ttl: Time-to-live in seconds (uses default if not specified)
        """
        self._cache[key] = value
        self._ttl[key] = time.time() + (ttl or self.default_ttl)
        logger.debug(f"Cached value for key: {key[:32]}... (TTL: {ttl or self.default_ttl}s)")
        
    def clear(self):
        """Clear all cached values."""
        self._cache.clear()
        self._ttl.clear()
        self._hits = 0
        self._misses = 0
        logger.info("Cache cleared")
        
    def stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        total_requests = self._hits + self._misses
        hit_rate = self._hits / total_requests if total_requests > 0 else 0
        
        return {
            "hits": self._hits,
            "misses": self._misses,
            "hit_rate": hit_rate,
            "size": len(self._cache),
            "total_requests": total_requests
        }
        
    def make_key(self, *args, **kwargs) -> str:
        """
        Create a cache key from arguments.
        
        Args:
            *args: Positional arguments to include in key
            **kwargs: Keyword arguments to include in key
            
        Returns:
            MD5 hash of the combined arguments
        """
        # Combine all arguments into a single structure
        key_data = {
            "args": args,
            "kwargs": kwargs
        }
        
        # Convert to JSON for consistent serialization
        key_str = json.dumps(key_data, sort_keys=True)
        
        # Return MD5 hash for compact key
        return hashlib.md5(key_str.encode()).hexdigest()