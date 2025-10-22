"""Local cache service to replace Redis."""

import json
import pickle
import threading
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, Optional, Union

from src.config import get_settings
from src.utils.logger import get_logger

logger = get_logger(__name__)
settings = get_settings()


class LocalCache:
    """Thread-safe local cache implementation."""
    
    def __init__(self, cache_dir: str = "storage/local_cache"):
        """Initialize local cache."""
        self.cache_dir = Path(cache_dir)
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        # In-memory cache for fast access
        self._memory_cache: Dict[str, Dict[str, Any]] = {}
        self._lock = threading.RLock()
        
        # Cache configuration
        self.max_memory_items = 1000
        self.default_ttl = 3600  # 1 hour
        self.cleanup_interval = 300  # 5 minutes
        
        # Start cleanup thread
        self._cleanup_thread = threading.Thread(target=self._cleanup_worker, daemon=True)
        self._cleanup_thread.start()
        
        logger.info(f"Local cache initialized at: {self.cache_dir}")
    
    def _get_cache_path(self, key: str) -> Path:
        """Get file path for cache key."""
        # Create subdirectory based on key hash for better organization
        key_hash = hash(key) % 100
        subdir = self.cache_dir / f"cache_{key_hash:02d}"
        subdir.mkdir(exist_ok=True)
        return subdir / f"{hash(key)}.cache"
    
    def _load_from_disk(self, key: str) -> Optional[Dict[str, Any]]:
        """Load cache item from disk."""
        try:
            cache_path = self._get_cache_path(key)
            if not cache_path.exists():
                return None
            
            with open(cache_path, 'rb') as f:
                data = pickle.load(f)
            
            # Check if expired
            if data.get('expires_at') and datetime.now() > data['expires_at']:
                cache_path.unlink()
                return None
            
            return data
            
        except Exception as e:
            logger.warning(f"Failed to load cache item {key}: {e}")
            return None
    
    def _save_to_disk(self, key: str, data: Dict[str, Any]):
        """Save cache item to disk."""
        try:
            cache_path = self._get_cache_path(key)
            
            with open(cache_path, 'wb') as f:
                pickle.dump(data, f)
                
        except Exception as e:
            logger.warning(f"Failed to save cache item {key}: {e}")
    
    def _cleanup_worker(self):
        """Background cleanup worker."""
        while True:
            try:
                time.sleep(self.cleanup_interval)
                self._cleanup_expired()
            except Exception as e:
                logger.error(f"Cache cleanup error: {e}")
    
    def _cleanup_expired(self):
        """Remove expired items from memory and disk."""
        with self._lock:
            current_time = datetime.now()
            
            # Clean memory cache
            expired_keys = []
            for key, data in self._memory_cache.items():
                if data.get('expires_at') and current_time > data['expires_at']:
                    expired_keys.append(key)
            
            for key in expired_keys:
                del self._memory_cache[key]
            
            # Clean disk cache
            for cache_file in self.cache_dir.rglob("*.cache"):
                try:
                    with open(cache_file, 'rb') as f:
                        data = pickle.load(f)
                    
                    if data.get('expires_at') and current_time > data['expires_at']:
                        cache_file.unlink()
                        
                except Exception:
                    # If we can't read the file, delete it
                    cache_file.unlink()
            
            if expired_keys:
                logger.debug(f"Cleaned up {len(expired_keys)} expired cache items")
    
    def get(self, key: str) -> Optional[Any]:
        """Get value from cache."""
        with self._lock:
            # Check memory cache first
            if key in self._memory_cache:
                data = self._memory_cache[key]
                if not data.get('expires_at') or datetime.now() <= data['expires_at']:
                    return data['value']
                else:
                    del self._memory_cache[key]
            
            # Load from disk
            data = self._load_from_disk(key)
            if data:
                # Add to memory cache
                self._memory_cache[key] = data
                return data['value']
            
            return None
    
    def set(self, key: str, value: Any, ttl: Optional[int] = None) -> bool:
        """Set value in cache."""
        try:
            with self._lock:
                expires_at = None
                if ttl:
                    expires_at = datetime.now() + timedelta(seconds=ttl)
                elif self.default_ttl:
                    expires_at = datetime.now() + timedelta(seconds=self.default_ttl)
                
                data = {
                    'value': value,
                    'created_at': datetime.now(),
                    'expires_at': expires_at
                }
                
                # Save to memory cache
                self._memory_cache[key] = data
                
                # Save to disk
                self._save_to_disk(key, data)
                
                # Limit memory cache size
                if len(self._memory_cache) > self.max_memory_items:
                    # Remove oldest items
                    oldest_keys = sorted(
                        self._memory_cache.keys(),
                        key=lambda k: self._memory_cache[k]['created_at']
                    )[:len(self._memory_cache) - self.max_memory_items]
                    
                    for old_key in oldest_keys:
                        del self._memory_cache[old_key]
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to set cache item {key}: {e}")
            return False
    
    def delete(self, key: str) -> bool:
        """Delete value from cache."""
        try:
            with self._lock:
                # Remove from memory
                if key in self._memory_cache:
                    del self._memory_cache[key]
                
                # Remove from disk
                cache_path = self._get_cache_path(key)
                if cache_path.exists():
                    cache_path.unlink()
                
                return True
                
        except Exception as e:
            logger.error(f"Failed to delete cache item {key}: {e}")
            return False
    
    def exists(self, key: str) -> bool:
        """Check if key exists in cache."""
        return self.get(key) is not None
    
    def clear(self) -> bool:
        """Clear all cache."""
        try:
            with self._lock:
                # Clear memory cache
                self._memory_cache.clear()
                
                # Clear disk cache
                for cache_file in self.cache_dir.rglob("*.cache"):
                    cache_file.unlink()
                
                logger.info("Cache cleared successfully")
                return True
                
        except Exception as e:
            logger.error(f"Failed to clear cache: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics."""
        with self._lock:
            memory_items = len(self._memory_cache)
            
            # Count disk items
            disk_items = len(list(self.cache_dir.rglob("*.cache")))
            
            # Calculate total size
            total_size = sum(f.stat().st_size for f in self.cache_dir.rglob("*.cache"))
            
            return {
                'memory_items': memory_items,
                'disk_items': disk_items,
                'total_items': memory_items + disk_items,
                'total_size_bytes': total_size,
                'total_size_mb': round(total_size / (1024 * 1024), 2),
                'cache_dir': str(self.cache_dir),
                'max_memory_items': self.max_memory_items,
                'default_ttl': self.default_ttl
            }


# Global cache instance
_cache_instance: Optional[LocalCache] = None


def get_cache() -> LocalCache:
    """Get global cache instance."""
    global _cache_instance
    if _cache_instance is None:
        _cache_instance = LocalCache()
    return _cache_instance


# Convenience functions
def cache_get(key: str) -> Optional[Any]:
    """Get value from cache."""
    return get_cache().get(key)


def cache_set(key: str, value: Any, ttl: Optional[int] = None) -> bool:
    """Set value in cache."""
    return get_cache().set(key, value, ttl)


def cache_delete(key: str) -> bool:
    """Delete value from cache."""
    return get_cache().delete(key)


def cache_exists(key: str) -> bool:
    """Check if key exists in cache."""
    return get_cache().exists(key)


def cache_clear() -> bool:
    """Clear all cache."""
    return get_cache().clear()


def cache_stats() -> Dict[str, Any]:
    """Get cache statistics."""
    return get_cache().get_stats()
