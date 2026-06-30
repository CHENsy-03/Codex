"""UDP 信号接收器"""
import socket, logging, threading
logger = logging.getLogger(__name__)
class UDPReceiver:
    def __init__(self, host="0.0.0.0", port=8889):
        self.host, self.port = host, port; self._callbacks = []
        self._running = False; self._sock = None
    def on_data(self, cb): self._callbacks.append(cb)
    def start(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port)); self._running = True
        logger.info("UDP receiver: %s:%d", self.host, self.port)
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        while self._running:
            try:
                d, addr = self._sock.recvfrom(8192)
                [cb(d.decode("ascii",errors="ignore")) for cb in self._callbacks]
            except: pass
    def stop(self): self._running = False
