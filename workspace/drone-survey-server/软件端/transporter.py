"""数据传输抽象 — MQTT / TCP (CM510-71F) / UDP """
import json, time, socket, abc, hmac, hashlib, logging
from crc import add_crc

logger = logging.getLogger(__name__)

class Transporter(abc.ABC):
    @abc.abstractmethod
    def connect(self):
        ...

    @abc.abstractmethod
    def send(self, data: dict) -> bool:
        ...

    @abc.abstractmethod
    def receive(self, timeout=5) -> dict | None:
        ...

    def disconnect(self):
        pass

    def _sign(self, msg: dict, key: str) -> dict:
        if key:
            payload = json.dumps(msg, sort_keys=True, separators=(",", ":"))
            msg["signature"] = hmac.new(key.encode(), payload.encode(),
                                        hashlib.sha256).hexdigest()
        return msg


class MQTTTransporter(Transporter):
    """MQTT 传输（基于 paho-mqtt）"""
    def __init__(self, device_id, host="localhost", port=1883, user="", password="",
                 topic_data="survey/data", topic_resp="survey/response", hmac_key=""):
        self.device_id = device_id
        self.host, self.port = host, port
        self.user, self.password = user, password
        self.topic_data = f"{topic_data}/{device_id}"
        self.topic_resp = f"{topic_resp}/{device_id}"
        self.hmac_key = hmac_key
        self._client = None
        self._last_response = None

    def connect(self):
        import paho.mqtt.client as mqtt
        self._client = mqtt.Client(client_id=self.device_id, clean_session=False)
        if self.user:
            self._client.username_pw_set(self.user, self.password)

        def on_msg(client, userdata, msg):
            try:
                self._last_response = json.loads(msg.payload)
            except Exception:
                pass

        self._client.on_message = on_msg
        self._client.connect(self.host, self.port, keepalive=60)
        self._client.subscribe(self.topic_resp, qos=1)
        self._client.loop_start()
        logger.info("MQTT connected: %s:%d", self.host, self.port)
        return True

    def send(self, data: dict) -> bool:
        if not self._client:
            self.connect()
        msg = add_crc(self._sign(data.copy(), self.hmac_key))
        result = self._client.publish(self.topic_data, json.dumps(msg), qos=1)
        return result.rc == 0

    def receive(self, timeout=5) -> dict | None:
        if self._last_response:
            resp = self._last_response
            self._last_response = None
            return resp
        time.sleep(0.3)
        return None

    def disconnect(self):
        if self._client:
            self._client.loop_stop()
            self._client.disconnect()
            self._client = None


class TCPTransporter(Transporter):
    """TCP 直连传输（适配 CM510-71F 透传模式）"""
    def __init__(self, host="192.168.1.100", port=8888, device_id="K803-001",
                 delimiter=b"\n", hmac_key=""):
        self.host, self.port = host, port
        self.device_id = device_id
        self.delimiter = delimiter
        self.hmac_key = hmac_key
        self._sock = None
        self._buf = b""

    def connect(self):
        self._sock = socket.create_connection((self.host, self.port), timeout=10)
        self._sock.setsockopt(socket.IPPROTO_TCP, socket.TCP_NODELAY, 1)
        logger.info("TCP connected: %s:%d", self.host, self.port)
        return True

    def send(self, data: dict) -> bool:
        if not self._sock:
            self.connect()
        msg = add_crc(self._sign(data.copy(), self.hmac_key))
        payload = json.dumps(msg) + "\n"
        try:
            self._sock.sendall(payload.encode("utf-8"))
            return True
        except Exception as e:
            logger.error("TCP send error: %s", e)
            return False

    def receive(self, timeout=5) -> dict | None:
        if not self._sock:
            return None
        self._sock.settimeout(timeout)
        try:
            while self.delimiter not in self._buf:
                chunk = self._sock.recv(4096)
                if not chunk:
                    raise ConnectionError("Disconnected")
                self._buf += chunk
            line, self._buf = self._buf.split(self.delimiter, 1)
            return json.loads(line.decode("utf-8"))
        except socket.timeout:
            return None
        except Exception as e:
            logger.warning("TCP receive error: %s", e)
            return None

    def disconnect(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


class UDPTransporter(Transporter):
    """UDP 传输（适配 CM510-71F UDP 模式）"""
    def __init__(self, remote_host="192.168.1.100", remote_port=8888,
                 local_port=0, device_id="K803-001", hmac_key=""):
        self.remote = (remote_host, remote_port)
        self.local_port = local_port
        self.device_id = device_id
        self.hmac_key = hmac_key
        self._sock = None

    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_DGRAM)
        if self.local_port:
            self._sock.bind(("0.0.0.0", self.local_port))
        self._sock.settimeout(5)
        logger.info("UDP ready -> %s:%d", *self.remote)
        return True

    def send(self, data: dict) -> bool:
        if not self._sock:
            self.connect()
        msg = add_crc(self._sign(data.copy(), self.hmac_key))
        try:
            self._sock.sendto(json.dumps(msg).encode("utf-8"), self.remote)
            return True
        except Exception as e:
            logger.error("UDP send error: %s", e)
            return False

    def receive(self, timeout=5) -> dict | None:
        if not self._sock:
            return None
        self._sock.settimeout(timeout)
        try:
            data, _ = self._sock.recvfrom(4096)
            return json.loads(data.decode("utf-8"))
        except socket.timeout:
            return None
        except Exception:
            return None

    def disconnect(self):
        if self._sock:
            try: self._sock.close()
            except: pass
            self._sock = None


def create_transporter(mode="mqtt", **kwargs):
    modes = {"mqtt": MQTTTransporter, "tcp": TCPTransporter, "udp": UDPTransporter}
    cls = modes.get(mode)
    if not cls:
        raise ValueError(f"Unknown transport mode: {mode}")
    return cls(**kwargs)
