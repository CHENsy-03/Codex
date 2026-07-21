# -*- coding: utf-8 -*-
"""V2.1 Protobuf Message Pool - GNSSPosition object reuse with Clear()"""
import threading
from protocol.proto.gnss_pb2 import GNSSPosition
class MessagePool:
    def __init__(self, size=100):
        self._pool = [GNSSPosition() for _ in range(min(size, 1000))]
        self._lock = threading.Lock()
        self._hits = 0; self._misses = 0; self._max_size = size
    def acquire(self):
        with self._lock:
            if self._pool:
                self._hits += 1
                return self._pool.pop()
        self._misses += 1
        return GNSSPosition()
    def release(self, msg):
        msg.Clear()
        with self._lock:
            if len(self._pool) < self._max_size:
                self._pool.append(msg)
    @property
    def stats(self):
        with self._lock:
            total = self._hits + self._misses
            return {"pool_size": len(self._pool), "hits": self._hits,
                    "misses": self._misses,
                    "hit_rate": f"{self._hits / max(1, total) * 100:.1f}%"}
_global_msg_pool = None
def get_msg_pool(size=100):
    global _global_msg_pool
    if _global_msg_pool is None:
        _global_msg_pool = MessagePool(size)
    return _global_msg_pool
