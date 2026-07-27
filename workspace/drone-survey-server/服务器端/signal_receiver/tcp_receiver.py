"""TCP 信号接收器 — TCP Server/Client 模式"""
import socket, time, logging, threading
logger = logging.getLogger(__name__)
class TCPReceiver:
    def __init__(self, host="0.0.0.0", port=8888, mode="server"):
        self.host, self.port, self.mode = host, port, mode
        self._sock = None; self._running = False; self._callbacks = []
    def on_data(self, cb): self._callbacks.append(cb)
    def start(self):
        self._running = True
        if self.mode == "server":
            self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            self._sock.bind((self.host, self.port)); self._sock.listen(5)
            logger.info("TCP server: %s:%d", self.host, self.port)
            threading.Thread(target=self._accept, daemon=True).start()
        else:
            threading.Thread(target=self._run_client, daemon=True).start()
    def _accept(self):
        while self._running:
            try:
                conn, addr = self._sock.accept()
                threading.Thread(target=self._handle, args=(conn,), daemon=True).start()
            except: time.sleep(0.1)
    def _handle(self, conn):
        buf = b""
        while self._running:
            try:
                d = conn.recv(4096)
                if not d: break
                buf += d
                while b"\n" in buf:
                    line, buf = buf.split(b"\n", 1)
                    [cb(line.decode("ascii",errors="ignore")) for cb in self._callbacks]
            except: break
    def _run_client(self):
        backoff = 1; max_backoff = 60
        while self._running:
            try:
                self._sock = socket.create_connection((self.host, self.port), timeout=5)
            except Exception as e:
                logger.warning("TCP client reconnect in %ds: %s", backoff, e)
                self._running and time.sleep(backoff)
                backoff = min(backoff * 2, max_backoff)
                continue
            buf = b""
            while self._running:
                try:
                    d = self._sock.recv(4096)
                    if not d: break
                    buf += d
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        [cb(line.decode("ascii",errors="ignore")) for cb in self._callbacks]
                except: break
            break
    def stop(self): self._running = False
