# -*- coding: utf-8 -*-
"""V2.1 WebSocket Test - with proper masking"""
import socket, base64, hashlib, struct, json, sys, os, time as _time
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def ws_connect(host="127.0.0.1", port=8081, path="/api/ws/device"):
    sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    sock.settimeout(5)
    sock.connect((host, port))
    key = base64.b64encode(b"0123456789abcde").decode()
    req = f"GET {path} HTTP/1.1\r\nHost: {host}:{port}\r\nUpgrade: websocket\r\nConnection: Upgrade\r\nSec-WebSocket-Key: {key}\r\nSec-WebSocket-Version: 13\r\n\r\n".encode()
    sock.send(req)
    resp = sock.recv(4096)
    if b"101" not in resp: sock.close(); return None, "handshake failed"
    return sock, "ok"
def ws_send(sock, text):
    data = text.encode("utf-8"); mask_key = os.urandom(4)
    frame = bytearray([0x81, 0x80 | len(data)]); frame.extend(mask_key)
    for i, b in enumerate(data): frame.append(b ^ mask_key[i % 4])
    sock.sendall(bytes(frame))
def ws_recv(sock):
    try: hdr = sock.recv(2)
    except Exception: return None
    if len(hdr) < 2: return None
    length = hdr[1] & 0x7F
    if length == 126: length = struct.unpack(">H", sock.recv(2))[0]
    elif length == 127: length = struct.unpack(">Q", sock.recv(8))[0]
    payload = sock.recv(length)
    return payload.decode("utf-8") if isinstance(payload, bytes) else str(payload)
def run_test():
    r = []
    def ck(n, ok, d=""): r.append((n,ok,d)); print(f"  [{'PASS' if ok else 'FAIL'}] {n}{' — '+d if d else ''}")
    print("="*55); print("  WebSocket 测试"); print("="*55)
    sock, st = ws_connect(); ck("WebSocket连接", st=="ok", st)
    if sock:
        ws_send(sock, '{"type":"subscribe"}'); _time.sleep(0.5)
        msg = ws_recv(sock)
        if msg:
            try: d = json.loads(msg); ck("订阅确认", d.get("status")=="ok", f"收到: {msg}")
            except Exception: ck("订阅确认", False, f"非JSON: {msg[:50]}")
        else: ck("订阅确认", False, "无响应")
        sock.close()
    ps = sum(1 for _,ok,_ in r if ok)
    print(f"\n{'='*55}"); print(f"  WebSocket测试: {ps}/{len(r)} 通过"); print(f"{'='*55}")
if __name__ == "__main__": run_test()
