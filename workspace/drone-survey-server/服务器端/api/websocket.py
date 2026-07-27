# -*- coding: utf-8 -*-
"""V2.1 WebSocket Server — ThreadingHTTPServer + recv_exact + ping/pong heartbeat"""
import json, time, threading, struct, hashlib, base64
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
_ws_clients = []; _ws_lock = threading.Lock()
def broadcast(msg):
    with _ws_lock:
        for c in _ws_clients[:]:
            try: c.send(json.dumps(msg, ensure_ascii=False))
            except Exception: _ws_clients.remove(c)
class WSClient:
    def __init__(self, sock, addr):
        self.sock = sock; self.addr = addr; self.alive = True
        self.sock.settimeout(None); self.sock.setblocking(True)
        self._last_pong = time.time()
        self._thread = threading.Thread(target=self._recv_loop, daemon=True); self._thread.start()
        self._hb_thread = threading.Thread(target=self._heartbeat, daemon=True); self._hb_thread.start()
    def _recv_exact(self, length):
        data = b""
        while len(data) < length:
            try: chunk = self.sock.recv(length - len(data))
            except Exception: raise ConnectionError("recv failed")
            if not chunk: raise ConnectionError("connection closed")
            data += chunk
        return data
    def send(self, text):
        if not self.alive: return
        data = text.encode("utf-8"); frame = bytearray()
        frame.append(0x81)
        if len(data) < 126: frame.append(len(data))
        elif len(data) < 65536: frame.append(126); frame.extend(struct.pack(">H", len(data)))
        else: frame.append(127); frame.extend(struct.pack(">Q", len(data)))
        frame.extend(data)
        try: self.sock.sendall(bytes(frame))
        except Exception: self.alive = False
    def _send_frame(self, opcode, payload=b""):
        if not self.alive: return
        frame = bytearray([0x80 | opcode])
        if len(payload) < 126: frame.append(len(payload))
        else: frame.append(126); frame.extend(struct.pack(">H", len(payload)))
        frame.extend(payload)
        try: self.sock.sendall(bytes(frame))
        except Exception: self.alive = False
    def _heartbeat(self):
        while self.alive:
            time.sleep(30)
            if not self.alive: break
            self._send_frame(0x9, b"ping")
            if time.time() - self._last_pong > 90:
                self.alive = False
    def _recv_loop(self):
        try:
            while self.alive:
                hdr = self._recv_exact(2)
                opcode = hdr[0] & 0x0F; length = hdr[1] & 0x7F
                if length == 126: length = struct.unpack(">H", self._recv_exact(2))[0]
                elif length == 127: length = struct.unpack(">Q", self._recv_exact(8))[0]
                if opcode == 0x8: self.alive = False; break
                if opcode == 0x9: self._send_frame(0xA, self._recv_exact(length)); self._last_pong = time.time(); continue
                if opcode == 0xA: self._last_pong = time.time(); self._recv_exact(length); continue
                mask = self._recv_exact(4)
                payload = bytearray(self._recv_exact(length))
                for i in range(length): payload[i] ^= mask[i % 4]
                if opcode == 0x1:
                    try: msg = json.loads(payload.decode("utf-8")); self._handle(msg)
                    except Exception: pass
        except Exception: pass
        finally:
            self.alive = False
            with _ws_lock:
                if self in _ws_clients: _ws_clients.remove(self)
    def _handle(self, msg):
        t = msg.get("type", "")
        if t == "subscribe":
            with _ws_lock:
                if self not in _ws_clients: _ws_clients.append(self)
            self.send(json.dumps({"type":"subscribed","status":"ok"}))
class WSHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        if self.path.startswith("/api/ws/"):
            if "Upgrade" in self.headers and "websocket" in self.headers.get("Upgrade","").lower():
                self._do_handshake()
                WSClient(self.request, self.client_address)
            else: self.send_response(426); self.end_headers()
        else: self.send_response(404); self.end_headers()
    def _do_handshake(self):
        key = self.headers.get("Sec-WebSocket-Key", "")
        accept = base64.b64encode(hashlib.sha1((key + "258EAFA5-E914-47DA-95CA-C5AB0DC85B11").encode()).digest()).decode()
        self.send_response(101); self.send_header("Upgrade", "websocket")
        self.send_header("Connection", "Upgrade"); self.send_header("Sec-WebSocket-Accept", accept)
        self.end_headers()
    def log_message(self, fmt, *args): pass
class WSServer(ThreadingHTTPServer):
    def __init__(self, addr, handler):
        ThreadingHTTPServer.__init__(self, addr, handler); self.allow_reuse_address = True
        self.daemon_threads = True
