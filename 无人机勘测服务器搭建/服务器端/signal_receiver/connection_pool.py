"""TCP 连接池 — 管理多设备连接"""
import socket, threading, time, logging
logger = logging.getLogger(__name__)

class ConnectionPool:
    def __init__(self, max_size=500):
        self.max_size = max_size
        self._conns = {}; self._lock = threading.Lock(); self._running = False

    def add(self, conn_id: str, conn: socket.socket, addr=None):
        with self._lock:
            if len(self._conns) >= self.max_size:
                return False
            self._conns[conn_id] = {"conn": conn, "addr": addr or "",
                "connected": time.time(), "last_active": time.time(), "bytes_recv": 0}
            return True

    def remove(self, conn_id: str):
        with self._lock:
            if conn_id in self._conns:
                try: self._conns[conn_id]["conn"].close()
                except: pass
                del self._conns[conn_id]

    def get(self, conn_id: str):
        with self._lock: return self._conns.get(conn_id)

    def send(self, conn_id: str, data: bytes) -> bool:
        c = self.get(conn_id)
        if not c: return False
        try:
            c["conn"].sendall(data)
            c["last_active"] = time.time()
            return True
        except: self.remove(conn_id); return False

    def broadcast(self, data: bytes):
        for cid in list(self._conns.keys()):
            self.send(cid, data)

    def stats(self):
        with self._lock:
            return {"active": len(self._conns), "max": self.max_size,
                    "connections": list(self._conns.keys())}

    def start_health_check(self, interval=30, timeout=120):
        self._running = True
        def _check():
            while self._running:
                time.sleep(interval)
                now = time.time()
                stale = [cid for cid, c in list(self._conns.items()) if now - c["last_active"] > timeout]
                for cid in stale:
                    logger.warning("Health: removing stale connection %s", cid)
                    self.remove(cid)
        threading.Thread(target=_check, daemon=True).start()

    def stop(self): self._running = False
