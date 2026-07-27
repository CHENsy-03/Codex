"""TCP Adapter"""
import socket
from .device_adapter import DeviceAdapter
class TCPAdapter(DeviceAdapter):
    name = "tcp"
    def __init__(self, host="0.0.0.0", port=8888):
        self.host, self.port = host, port
        self._sock = None
    def connect(self):
        self._sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        self._sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        self._sock.bind((self.host, self.port))
        self._sock.listen(5)
    def disconnect(self):
        if self._sock: self._sock.close()
    def send(self, data): pass
    def on_data(self, cb): pass
