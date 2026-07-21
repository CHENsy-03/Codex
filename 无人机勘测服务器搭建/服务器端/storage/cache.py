# -*- coding: utf-8 -*-
"""V2.0 In-Memory Cache - Redis-compatible local cache for real-time data."""
import time, threading
from collections import OrderedDict
class MemoryCache:
    def __init__(self, max_size=10000):
        self._store = OrderedDict()
        self._expiry = {}
        self._lock = threading.Lock()
        self._max_size = max_size
        self._hits = 0
        self._misses = 0
    def set(self, key, value, ttl=None):
        with self._lock:
            if len(self._store) >= self._max_size:
                self._store.popitem(last=False)
            self._store[key] = value
            if ttl:
                self._expiry[key] = time.time() + ttl
    def get(self, key, default=None):
        with self._lock:
            if key not in self._store:
                self._misses += 1
                return default
            if key in self._expiry and time.time() > self._expiry[key]:
                del self._store[key]; del self._expiry[key]
                self._misses += 1
                return default
            self._hits += 1
            return self._store[key]
    def delete(self, key):
        with self._lock:
            self._store.pop(key, None); self._expiry.pop(key, None)
    def keys(self, pattern='*'):
        with self._lock:
            return [k for k in self._store if pattern == '*' or pattern in k]
    def flush(self):
        with self._lock:
            self._store.clear(); self._expiry.clear()
    @property
    def stats(self):
        with self._lock:
            total = self._hits + self._misses
            return {'size':len(self._store), 'max_size':self._max_size,
                    'hits':self._hits, 'misses':self._misses,
                    'hit_rate':f'{self._hits/max(1,total)*100:.1f}%'}
_global_cache = None
def get_cache(max_size=10000):
    global _global_cache
    if _global_cache is None:
        _global_cache = MemoryCache(max_size=max_size)
    return _global_cache
