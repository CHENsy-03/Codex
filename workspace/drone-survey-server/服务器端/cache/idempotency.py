
"""Idempotency key management + L1/L2 cache for dedup

L1: In-memory LRU (fastest, local to process)
L2: Redis (distributed, survives restarts)
"""

import time
import hashlib
import json
import logging
from collections import OrderedDict

logger = logging.getLogger(__name__)


class LRUCache:
    """Simple LRU cache for L1 dedup"""
    def __init__(self, capacity=10000):
        self.capacity = capacity
        self._cache = OrderedDict()

    def get(self, key):
        if key in self._cache:
            self._cache.move_to_end(key)
            return self._cache[key]
        return None

    def set(self, key, value):
        if key in self._cache:
            self._cache.move_to_end(key)
        self._cache[key] = value
        if len(self._cache) > self.capacity:
            self._cache.popitem(last=False)

    def __contains__(self, key):
        return key in self._cache


class IdempotencyManager:
    """Idempotency key manager with L1/L2 cache hierarchy.

    Key format: survey:{device_id}:{batch_id}

    Usage:
        im = IdempotencyManager()
        if im.already_processed(device_id, batch_id):
            return im.get_result(device_id, batch_id)
        result = process(data)
        im.store_result(device_id, batch_id, result)
    """
    def __init__(self, l1_capacity=10000, redis_client=None):
        self.l1 = LRUCache(l1_capacity)
        self.l2 = redis_client  # optional Redis client

    def _make_key(self, device_id, batch_id):
        return f"survey:{device_id}:{batch_id}"

    def already_processed(self, device_id, batch_id):
        key = self._make_key(device_id, batch_id)
        # Check L1
        if key in self.l1:
            return True
        # Check L2 (optional)
        if self.l2:
            return self.l2.exists(key)
        return False

    def get_result(self, device_id, batch_id):
        key = self._make_key(device_id, batch_id)
        val = self.l1.get(key)
        if val:
            return json.loads(val)
        if self.l2:
            val = self.l2.get(key)
            if val:
                self.l1.set(key, val)
                return json.loads(val)
        return None

    def store_result(self, device_id, batch_id, result, ttl=86400):
        key = self._make_key(device_id, batch_id)
        val = json.dumps(result)
        self.l1.set(key, val)
        if self.l2:
            self.l2.setex(key, ttl, val)

    def mark_failed(self, device_id, batch_id):
        """Mark a batch as failed so retry is possible"""
        key = self._make_key(device_id, batch_id)
        fail_val = json.dumps({"status": "failed", "retry_allowed": True})
        self.l1.set(key, fail_val)
