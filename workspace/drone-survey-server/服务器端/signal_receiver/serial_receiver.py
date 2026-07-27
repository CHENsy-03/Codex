"""串口信号接收器 — 接收 CM510/K803 串口数据"""
import time, logging, threading
logger = logging.getLogger(__name__)
class SerialReceiver:
    def __init__(self, port="COM3", baud=115200, timeout=3):
        self.port, self.baud, self.timeout = port, baud, timeout
        self._ser = None; self._running = False; self._callbacks = []
    def on_data(self, cb): self._callbacks.append(cb)
    def start(self):
        import serial
        self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
        self._running = True
        logger.info("Serial receiver started: %s @ %d", self.port, self.baud)
        threading.Thread(target=self._run, daemon=True).start()
    def _run(self):
        while self._running:
            try:
                line = self._ser.readline().decode("ascii", errors="ignore").strip()
                if line: [cb(line) for cb in self._callbacks]
            except: time.sleep(0.01)
    def stop(self):
        self._running = False
        if self._ser: self._ser.close()
