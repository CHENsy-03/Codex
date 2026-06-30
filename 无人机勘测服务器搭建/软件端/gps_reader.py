"""GNSS 读取器 — K803_EK0407 串口直连 / CM510-71F TCP 桥接"""
import time, socket, struct, logging, threading
from gps_parser import parse_nmea, parse_bestposa

logger = logging.getLogger(__name__)

class GNSSReader:
    def read_fix(self) -> dict | None:
        raise NotImplementedError

    def close(self):
        pass


class SerialGNSSReader(GNSSReader):
    """通过 UART 直接读取 K803_EK0407"""
    def __init__(self, port="/dev/ttyAMA0", baud=115200, timeout=3):
        self.port, self.baud, self.timeout = port, baud, timeout
        self._ser = None

    def connect(self):
        try:
            import serial
            self._ser = serial.Serial(self.port, self.baud, timeout=self.timeout)
            logger.info("Serial GNSS connected: %s @ %d", self.port, self.baud)
        except ImportError:
            raise RuntimeError("Missing pyserial: pip install pyserial")
        except Exception as e:
            raise RuntimeError(f"Serial connect failed: {e}")

    def read_fix(self) -> dict | None:
        if not self._ser or not self._ser.is_open:
            self.connect()
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                raw = self._ser.readline().decode("ascii", errors="ignore").strip()
                if raw.startswith("$"):
                    fix = parse_nmea(raw)
                    if fix and fix.get("quality", 0) > 0:
                        return fix
            except Exception:
                pass
        return None

    def close(self):
        if self._ser and self._ser.is_open:
            self._ser.close()
            self._ser = None


class TCPBridgeReader(GNSSReader):
    """通过 CM510-71F TCP 桥接读取 K803 数据"""
    def __init__(self, host="192.168.1.100", port=8888, timeout=5):
        self.host, self.port, self.timeout = host, port, timeout
        self._sock = None

    def connect(self):
        self._sock = socket.create_connection((self.host, self.port),
                                              timeout=self.timeout)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logger.info("TCP bridge connected: %s:%d", self.host, self.port)

    def read_fix(self) -> dict | None:
        if not self._sock:
            self.connect()
        buf = b""
        start = time.time()
        while time.time() - start < self.timeout:
            try:
                while True:
                    chunk = self._sock.recv(4096)
                    if not chunk:
                        raise ConnectionError("TCP disconnected")
                    buf += chunk
                    while b"\n" in buf:
                        line, buf = buf.split(b"\n", 1)
                        raw = line.decode("ascii", errors="ignore").strip()
                        if raw.startswith("#BESTPOSA"):
                            fix = parse_bestposa(raw)
                            if fix: return fix
                        if raw.startswith("$"):
                            fix = parse_nmea(raw)
                            if fix and fix.get("quality", 0) > 0:
                                return fix
            except socket.timeout:
                pass
            except Exception as e:
                logger.warning("TCP read error: %s", e)
                time.sleep(0.1)
        return None

    def close(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


class UDPBridgeReader(GNSSReader):
    """通过 CM510-71F UDP 接收 K803 数据"""
    def __init__(self, port=8888, timeout=5):
        self.port, self.timeout = port, timeout
        self._sock = None
    
    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        self._sock.settimeout(self.timeout)
        self._sock.bind(("0.0.0.0", self.port))
        logger.info("UDP bridge listening on port %d", self.port)
    
    def read_fix(self) -> dict | None:
        if not self._sock:
            self.connect()
        try:
            data, addr = self._sock.recvfrom(4096)
            for line in data.decode("ascii", errors="ignore").split("\n"):
                line = line.strip()
                if line.startswith("#BESTPOSA"):
                    return parse_bestposa(line)
                if line.startswith("$"):
                    fix = parse_nmea(line)
                    if fix and fix.get("quality", 0) > 0:
                        return fix
        except socket.timeout:
            pass
        except Exception as e:
            logger.warning("UDP read error: %s", e)
        return None
    
    def close(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


def create_reader(mode="serial", **kwargs):
    """Factory: mode='serial' | 'tcp' | 'udp'"""
    if mode == "serial":
        return SerialGNSSReader(**kwargs)
    elif mode == "tcp":
        return TCPBridgeReader(**kwargs)
    elif mode == "udp":
        return UDPBridgeReader(**kwargs)
    raise ValueError(f"Unknown GNSS reader mode: {mode}")
