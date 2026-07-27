"""心跳监测 — 连接保活 + 超时检测"""
import time, threading, logging
logger = logging.getLogger(__name__)

class HeartbeatMonitor:
    def __init__(self, timeout=60, interval=10):
        self.timeout = timeout; self.interval = interval
        self._beats = {}; self._running = False; self._callbacks = []

    def on_timeout(self, cb): self._callbacks.append(cb)

    def beat(self, conn_id: str):
        self._beats[conn_id] = time.time()

    def remove(self, conn_id: str):
        self._beats.pop(conn_id, None)

    def start(self):
        self._running = True
        threading.Thread(target=self._loop, daemon=True).start()
        logger.info("HeartbeatMonitor started (timeout=%ds, interval=%ds)", self.timeout, self.interval)

    def _loop(self):
        while self._running:
            time.sleep(self.interval)
            now = time.time()
            stale = [cid for cid, t in list(self._beats.items()) if now - t > self.timeout]
            for cid in stale:
                logger.warning("Heartbeat timeout: %s (%ds since last beat)", cid, now - self._beats[cid])
                del self._beats[cid]
                for cb in self._callbacks: cb(cid)

    def stop(self): self._running = False

    def stats(self):
        return {"active": len(self._beats), "timeout": self.timeout}
