#!/usr/bin/env python3
"""
Cache Manager for Asset Generation Pipeline

Provides intelligent caching for:
- Ollama responses (prompts, design specs)
- Temperature and performance data
- File existence checks
- Computed values

Features:
- Hash-based cache keys for deterministic caching
- TTL (time-to-live) support for time-sensitive data
- LRU eviction for memory management
- Persistent disk cache for expensive operations
- Thread-safe operations
"""

from __future__ import annotations

import hashlib
import json
import threading
import time
from collections import OrderedDict
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, Optional, Tuple


@dataclass
class CacheEntry:
    """A single cache entry with TTL support."""
    value: Any
    timestamp: float = field(default_factory=time.time)
    ttl: Optional[float] = None  # None = never expires
    access_count: int = 0
    last_access: float = field(default_factory=time.time)
    
    def is_expired(self) -> bool:
        """Check if entry has expired."""
        if self.ttl is None:
            return False
        return (time.time() - self.timestamp) > self.ttl
    
    def touch(self) -> None:
        """Update access time and count."""
        self.last_access = time.time()
        self.access_count += 1


class CacheManager:
    """
    Thread-safe cache manager with TTL and LRU eviction.
    
    Supports both in-memory and persistent disk caching.
    """
    
    def __init__(
        self,
        max_size: int = 1000,
        default_ttl: Optional[float] = None,
        cache_dir: Optional[Path] = None,
        enable_disk_cache: bool = True,
        verbose: bool = False
    ):
        """
        Initialize cache manager.
        
        Args:
            max_size: Maximum number of entries in memory cache
            default_ttl: Default time-to-live in seconds (None = no expiration)
            cache_dir: Directory for persistent disk cache
            enable_disk_cache: Enable disk-based caching
            verbose: Print cache operations
        """
        self.max_size = max_size
        self.default_ttl = default_ttl
        self.verbose = verbose
        
        # In-memory cache (LRU ordered dict)
        self._cache: OrderedDict[str, CacheEntry] = OrderedDict()
        self._cache_lock = threading.RLock()
        
        # Disk cache
        self.enable_disk_cache = enable_disk_cache
        self.cache_dir = cache_dir or Path.home() / ".cache" / "asset_generator"
        if self.enable_disk_cache:
            self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # Statistics
        self._stats = {
            "hits": 0,
            "misses": 0,
            "evictions": 0,
            "disk_hits": 0,
            "disk_misses": 0,
        }
        self._stats_lock = threading.Lock()
    
    def _make_key(self, *args, **kwargs) -> str:
        """
        Create a deterministic cache key from arguments.
        
        Args:
            *args: Positional arguments
            **kwargs: Keyword arguments
        
        Returns:
            Hash-based cache key
        """
        # Create a deterministic string representation
        key_parts = []
        
        # Add positional args
        for arg in args:
            if isinstance(arg, (str, int, float, bool, type(None))):
                key_parts.append(str(arg))
            elif isinstance(arg, (list, tuple)):
                key_parts.append(json.dumps(arg, sort_keys=True))
            elif isinstance(arg, dict):
                key_parts.append(json.dumps(arg, sort_keys=True))
            else:
                key_parts.append(str(hash(str(arg))))
        
        # Add keyword args (sorted for determinism)
        if kwargs:
            sorted_kwargs = sorted(kwargs.items())
            key_parts.append(json.dumps(dict(sorted_kwargs), sort_keys=True))
        
        # Create hash
        key_str = "|".join(key_parts)
        return hashlib.sha256(key_str.encode('utf-8')).hexdigest()
    
    def _get_disk_path(self, key: str) -> Path:
        """Get disk cache file path for a key."""
        return self.cache_dir / f"{key}.cache"
    
    def _load_from_disk(self, key: str) -> Optional[Any]:
        """Load value from disk cache."""
        if not self.enable_disk_cache:
            return None
        
        try:
            cache_file = self._get_disk_path(key)
            if not cache_file.exists():
                return None
            
            with open(cache_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
            
            # Check TTL
            if 'ttl' in data and data['ttl'] is not None:
                age = time.time() - data['timestamp']
                if age > data['ttl']:
                    # Expired, delete file
                    cache_file.unlink()
                    return None
            
            with self._stats_lock:
                self._stats["disk_hits"] += 1
            
            if self.verbose:
                print(f"    [CACHE] Disk hit: {key[:16]}...")
            
            return data['value']
        except Exception as e:
            if self.verbose:
                print(f"    [CACHE] Disk load error: {e}")
            return None
    
    def _save_to_disk(self, key: str, value: Any, ttl: Optional[float] = None) -> bool:
        """Save value to disk cache."""
        if not self.enable_disk_cache:
            return False
        
        try:
            cache_file = self._get_disk_path(key)
            data = {
                'value': value,
                'timestamp': time.time(),
                'ttl': ttl,
            }
            
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, default=str)
            
            return True
        except Exception as e:
            if self.verbose:
                print(f"    [CACHE] Disk save error: {e}")
            return False
    
    def get(
        self,
        *args,
        ttl: Optional[float] = None,
        use_disk: bool = True,
        **kwargs
    ) -> Optional[Any]:
        """
        Get value from cache.
        
        Args:
            *args: Positional arguments for key generation
            ttl: Override default TTL for this lookup
            use_disk: Check disk cache if memory miss
            **kwargs: Keyword arguments for key generation
        
        Returns:
            Cached value or None if not found/expired
        """
        key = self._make_key(*args, **kwargs)
        
        with self._cache_lock:
            # Check memory cache
            if key in self._cache:
                entry = self._cache[key]
                
                # Check expiration
                if entry.is_expired():
                    del self._cache[key]
                    with self._stats_lock:
                        self._stats["misses"] += 1
                else:
                    # Move to end (LRU)
                    self._cache.move_to_end(key)
                    entry.touch()
                    with self._stats_lock:
                        self._stats["hits"] += 1
                    if self.verbose:
                        print(f"    [CACHE] Memory hit: {key[:16]}...")
                    return entry.value
            
            # Memory miss
            with self._stats_lock:
                self._stats["misses"] += 1
        
        # Try disk cache
        if use_disk:
            disk_value = self._load_from_disk(key)
            if disk_value is not None:
                # Load into memory cache
                self.set(*args, value=disk_value, ttl=ttl or self.default_ttl, use_disk=False, **kwargs)
                return disk_value
        
        if self.verbose:
            print(f"    [CACHE] Miss: {key[:16]}...")
        return None
    
    def set(
        self,
        *args,
        value: Any,
        ttl: Optional[float] = None,
        use_disk: bool = True,
        **kwargs
    ) -> None:
        """
        Set value in cache.
        
        Args:
            *args: Positional arguments for key generation
            value: Value to cache
            ttl: Time-to-live in seconds (None = use default)
            use_disk: Also save to disk cache
            **kwargs: Keyword arguments for key generation
        """
        key = self._make_key(*args, **kwargs)
        ttl = ttl if ttl is not None else self.default_ttl
        
        entry = CacheEntry(value=value, ttl=ttl)
        
        with self._cache_lock:
            # Remove if exists (will be re-added at end)
            if key in self._cache:
                del self._cache[key]
            
            # Add to end (LRU)
            self._cache[key] = entry
            
            # Evict if over limit
            while len(self._cache) > self.max_size:
                oldest_key, _ = self._cache.popitem(last=False)
                with self._stats_lock:
                    self._stats["evictions"] += 1
                if self.verbose:
                    print(f"    [CACHE] Evicted: {oldest_key[:16]}...")
        
        # Save to disk
        if use_disk:
            self._save_to_disk(key, value, ttl)
    
    def invalidate(self, *args, **kwargs) -> bool:
        """
        Invalidate a cache entry.
        
        Args:
            *args: Positional arguments for key generation
            **kwargs: Keyword arguments for key generation
        
        Returns:
            True if entry was found and removed
        """
        key = self._make_key(*args, **kwargs)
        
        with self._cache_lock:
            removed = key in self._cache
            if removed:
                del self._cache[key]
        
        # Remove from disk
        if self.enable_disk_cache:
            cache_file = self._get_disk_path(key)
            if cache_file.exists():
                cache_file.unlink()
        
        return removed
    
    def clear(self, memory_only: bool = False) -> None:
        """
        Clear cache.
        
        Args:
            memory_only: Only clear memory cache, keep disk cache
        """
        with self._cache_lock:
            self._cache.clear()
        
        if not memory_only and self.enable_disk_cache:
            # Clear disk cache
            for cache_file in self.cache_dir.glob("*.cache"):
                try:
                    cache_file.unlink()
                except Exception:
                    pass
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._stats_lock:
            stats = self._stats.copy()
        
        with self._cache_lock:
            stats["size"] = len(self._cache)
            stats["max_size"] = self.max_size
        
        if self.enable_disk_cache:
            stats["disk_cache_files"] = len(list(self.cache_dir.glob("*.cache")))
        
        return stats


# Global cache instance
_global_cache: Optional[CacheManager] = None
_cache_lock = threading.Lock()


def get_cache(
    max_size: int = 1000,
    default_ttl: Optional[float] = None,
    cache_dir: Optional[Path] = None,
    enable_disk_cache: bool = True,
    verbose: bool = False
) -> CacheManager:
    """
    Get or create global cache instance.
    
    Args:
        max_size: Maximum cache size
        default_ttl: Default TTL
        cache_dir: Cache directory
        enable_disk_cache: Enable disk cache
        verbose: Verbose output
    
    Returns:
        CacheManager instance
    """
    global _global_cache
    
    with _cache_lock:
        if _global_cache is None:
            _global_cache = CacheManager(
                max_size=max_size,
                default_ttl=default_ttl,
                cache_dir=cache_dir,
                enable_disk_cache=enable_disk_cache,
                verbose=verbose
            )
        return _global_cache
