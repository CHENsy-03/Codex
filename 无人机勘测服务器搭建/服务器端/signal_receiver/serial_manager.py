"""串口管理器 — 扫描/打开/关闭/配置"""
import time, threading, logging
logger = logging.getLogger(__name__)

class SerialManager:
    def __init__(self):
        self._ports = {}; self._open_ports = {}; self._callbacks = []

    def list_ports(self):
        """扫描可用串口"""
        try:
            import serial.tools.list_ports
            ports = []
            for p in serial.tools.list_ports.comports():
                ports.append({"port": p.device, "desc": p.description, "hwid": p.hwid, "status": "available"})
            return ports
        except ImportError:
            return [{"port": "COM1","desc":"Mock","hwid":"","status":"simulated"}]

    def open(self, port, baud=115200, timeout=3):
        """打开串口"""
        if port in self._open_ports: return True
        try:
            import serial
            ser = serial.Serial(port, baud, timeout=timeout)
            self._open_ports[port] = {"ser": ser, "baud": baud, "opened": time.time(), "bytes": 0, "errors": 0}
            logger.info("Serial %s opened @ %d", port, baud)
            return True
        except Exception as e:
            logger.warning("Serial %s open error: %s", port, e)
            return False

    def close(self, port):
        if port in self._open_ports:
            try: self._open_ports[port]["ser"].close()
            except: pass
            del self._open_ports[port]

    def send(self, port, data: bytes):
        p = self._open_ports.get(port)
        if not p: return False
        try:
            n = p["ser"].write(data)
            p["bytes"] += n
            return True
        except: return False

    def read(self, port):
        p = self._open_ports.get(port)
        if not p: return None
        try:
            data = p["ser"].readline()
            p["bytes"] += len(data)
            return data.decode("ascii", errors="ignore").strip()
        except: return None

    def status(self):
        return {p: {"status": "open", "baud": info["baud"], "uptime": int(time.time()-info["opened"]),
                     "bytes": info["bytes"], "errors": info["errors"]}
                for p, info in self._open_ports.items()}

    def close_all(self):
        for p in list(self._open_ports.keys()): self.close(p)

# Global singleton
_default = None
def get_default():
    global _default
    if _default is None: _default = SerialManager()
    return _default
