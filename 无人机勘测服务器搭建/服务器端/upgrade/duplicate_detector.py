"""重复检测 — 报文 ID 哈希表，防止重复上报

维护一个带 TTL 的哈希表（内存 + 可持久化到 DuckDB）。
自动清理 24h 前的记录。
"""
import time, hashlib, json, logging

logger = logging.getLogger(__name__)

class DuplicateDetector:
    def __init__(self, ttl=86400, cleanup_interval=3600):
        self.ttl = ttl              # 24h TTL
        self._cleanup_interval = cleanup_interval
        self._seen: dict[str, float] = {}  # hash → timestamp
        self._last_cleanup = time.time()

    def _msg_hash(self, data: dict) -> str:
        """计算报文哈希（去重键）"""
        payload = json.dumps(data, sort_keys=True, separators=(",", ":"))
        return hashlib.sha256(payload.encode()).hexdigest()[:16]

    def _auto_cleanup(self):
        now = time.time()
        if now - self._last_cleanup < self._cleanup_interval:
            return
        cutoff = now - self.ttl
        old = [k for k, ts in self._seen.items() if ts < cutoff]
        for k in old:
            del self._seen[k]
        if old:
            logger.info("DuplicateDetector cleanup: removed %d old entries", len(old))
        self._last_cleanup = now

    def check(self, data: dict) -> tuple[bool, str]:
        """检查是否重复. 返回 (is_duplicate, msg_hash)"""
        h = self._msg_hash(data)
        self._auto_cleanup()
        if h in self._seen:
            elapsed = time.time() - self._seen[h]
            return True, f"重复报文 (hash={h}, {elapsed:.0f}s 前已处理)"
        return False, h

    def record(self, data: dict):
        """记录已处理的报文"""
        h = self._msg_hash(data)
        self._seen[h] = time.time()

    def stats(self) -> dict:
        return {"total_recorded": len(self._seen), "ttl_hours": self.ttl / 3600}

# 全局单例
_default = None
def get_default():
    global _default
    if _default is None:
        _default = DuplicateDetector()
    return _default
