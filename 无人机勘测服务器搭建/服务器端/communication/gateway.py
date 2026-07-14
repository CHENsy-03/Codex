# -*- coding: utf-8 -*-
"""V2.0 Gateway - 设备接入统一入口

职责：
1. TCP Server 生命周期管理
2. 连接池 (device_id -> DeviceProtocol)
3. 协议自动识别与分发 (GPGGA / BESTPOS)
4. 数据解析 → Session 更新 → ACK → 入库回调
5. 设备上下线事件通知
"""

import time
import threading
from typing import Optional, Callable, Dict
from dataclasses import dataclass, field


@dataclass
class DeviceConnection:
    """设备连接信息"""
    device_id: str = ""
    address: str = ""
    connected_at: float = 0.0
    last_active: float = 0.0
    msg_count: int = 0
    session_id: str = ""
    status: str = "online"       # online / timeout / disconnected


@dataclass
class GatewayStats:
    """网关统计"""
    total_connections: int = 0
    active_connections: int = 0
    total_messages: int = 0
    total_errors: int = 0
    parsed_ok: int = 0
    parsed_fail: int = 0
    started_at: float = 0.0


class DeviceGateway:
    """设备网关：统一管理所有设备连接和数据流"""

    def __init__(self, server_id: str = "", host: str = "0.0.0.0", port: int = 9000):
        self.server_id = server_id
        self.host = host
        self.port = port

        # 连接池
        self._connections: Dict[str, DeviceConnection] = {}
        self._lock = threading.Lock()

        # TCP Server
        self._tcp_server: Optional[object] = None

        # 回调
        self._on_data_callback: Optional[Callable] = None
        self._on_connect_callback: Optional[Callable] = None
        self._on_disconnect_callback: Optional[Callable] = None

        # 统计
        self.stats = GatewayStats()

        # Session & ACK 管理器（延迟注入）
        self._session_mgr: Optional[object] = None
        self._ack_mgr: Optional[object] = None
        self._db: Optional[object] = None

    # ── 依赖注入 ──

    def set_db(self, db):
        """注入数据库管理器"""
        self._db = db

    def set_session_manager(self, session_mgr):
        """注入 Session 管理器"""
        self._session_mgr = session_mgr

    def set_ack_manager(self, ack_mgr):
        """注入 ACK 管理器"""
        self._ack_mgr = ack_mgr

    def set_on_data(self, callback: Callable):
        """设置数据处理回调 (device_id, gnss_data) -> None"""
        self._on_data_callback = callback

    def set_on_connect(self, callback: Callable):
        """设置设备连接回调 (device_id, address) -> None"""
        self._on_connect_callback = callback

    def set_on_disconnect(self, callback: Callable):
        """设置设备断开回调 (device_id) -> None"""
        self._on_disconnect_callback = callback

    # ── TCP Server 生命周期 ──

    def start(self) -> bool:
        """启动 TCP Server"""
        if self._tcp_server is not None:
            return False
        try:
            from communication.tcp_server import TCPServer
            srv = TCPServer(host=self.host, port=self.port)
            srv.set_callbacks(on_data=self._handle_frame)
            srv.start()
            self._tcp_server = srv
            self.stats.started_at = time.time()
            print(f"  [Gateway] TCP 监听 {self.host}:{self.port}")
            return True
        except Exception as ex:
            print(f"  [Gateway] 启动失败: {ex}")
            return False

    def stop(self):
        """停止 TCP Server"""
        if self._tcp_server:
            try:
                self._tcp_server.stop()
            except Exception:
                pass
            self._tcp_server = None
            # 标记所有连接为断开
            with self._lock:
                for dev_id, conn in self._connections.items():
                    conn.status = "disconnected"
            print("  [Gateway] 已停止")

    @property
    def is_running(self) -> bool:
        return self._tcp_server is not None

    # ── 帧处理 (TCP回调入口) ──

    def _handle_frame(self, proto_obj, header, payload: bytes):
        """处理收到的数据帧"""
        self.stats.total_messages += 1

        device_id = getattr(header, "device_id", "") or "unknown"
        session_id = str(getattr(header, "session_id", 0))
        sequence = getattr(header, "sequence", 0)
        peer = getattr(proto_obj, "peer", "unknown")
        now = time.time()

        # 更新连接池
        with self._lock:
            if device_id not in self._connections:
                conn = DeviceConnection(
                    device_id=device_id,
                    address=str(peer),
                    connected_at=now,
                    last_active=now,
                    msg_count=1,
                    session_id=session_id,
                    status="online",
                )
                self._connections[device_id] = conn
                self.stats.total_connections += 1
                self.stats.active_connections += 1
                if self._on_connect_callback:
                    try:
                        self._on_connect_callback(device_id, str(peer))
                    except Exception:
                        pass
            else:
                conn = self._connections[device_id]
                conn.last_active = now
                conn.msg_count += 1
                conn.session_id = session_id
                if conn.status != "online":
                    conn.status = "online"
                    self.stats.active_connections += 1

        # Session 心跳
        if self._session_mgr:
            try:
                self._session_mgr.heartbeat(device_id, session_id)
            except Exception:
                pass

        # 协议解析
        try:
            from protocol.parser import ProtocolDispatcher
            dp = ProtocolDispatcher(self.server_id)
            parsed = dp.parse(payload)

            if parsed:
                parsed.device_id = device_id
                parsed.server_id = self.server_id
                parsed.gnss_time = int(now)
                parsed.created_at = int(now)
                self.stats.parsed_ok += 1

                # 回调给业务层
                if self._on_data_callback:
                    self._on_data_callback(device_id, parsed)

                # ACK 成功
                if self._ack_mgr:
                    try:
                        self._ack_mgr.process_ack(device_id, sequence)
                    except Exception:
                        pass
            else:
                self.stats.parsed_fail += 1

        except Exception as ex:
            self.stats.total_errors += 1

        # 发送 ACK 帧
        self._send_ack(proto_obj, device_id, session_id, sequence,
                       self.stats.parsed_ok > 0)

    def _send_ack(self, proto_obj, device_id: str, session_id: str,
                  sequence: int, success: bool):
        """发送 ACK 帧"""
        try:
            from communication.frame import FrameHeader, pack_frame
            ack_hdr = FrameHeader()
            ack_hdr.device_id = device_id
            ack_hdr.msg_type = 0x0006   # ACK
            ack_hdr.sequence = sequence
            ack_hdr.session_id = int(session_id) if session_id.isdigit() else 0
            ack_hdr.timestamp = int(time.time())
            ack_payload = b"\x01" if success else b"\x00"
            proto_obj.send(pack_frame(ack_hdr, ack_payload))
        except Exception:
            pass

    # ── 连接管理 ──

    def get_connection(self, device_id: str) -> Optional[DeviceConnection]:
        with self._lock:
            return self._connections.get(device_id)

    def list_connections(self) -> list:
        with self._lock:
            return list(self._connections.values())

    def disconnect_device(self, device_id: str):
        """主动断开设备"""
        with self._lock:
            if device_id in self._connections:
                self._connections[device_id].status = "disconnected"
                self.stats.active_connections = max(0, self.stats.active_connections - 1)
        if self._on_disconnect_callback:
            try:
                self._on_disconnect_callback(device_id)
            except Exception:
                pass

    def cleanup_timeouts(self, timeout_seconds: float = 120.0):
        """清理超时连接"""
        now = time.time()
        removed = []
        with self._lock:
            for dev_id, conn in list(self._connections.items()):
                if conn.status == "online" and (now - conn.last_active) > timeout_seconds:
                    conn.status = "timeout"
                    self.stats.active_connections = max(0, self.stats.active_connections - 1)
                    removed.append(dev_id)
        for dev_id in removed:
            if self._on_disconnect_callback:
                try:
                    self._on_disconnect_callback(dev_id)
                except Exception:
                    pass
        return removed

    # ── 统计 ──

    def get_statistics(self) -> dict:
        with self._lock:
            active = sum(1 for c in self._connections.values() if c.status == "online")
        return {
            "total_connections": self.stats.total_connections,
            "active_connections": active,
            "total_messages": self.stats.total_messages,
            "total_errors": self.stats.total_errors,
            "parsed_ok": self.stats.parsed_ok,
            "parsed_fail": self.stats.parsed_fail,
            "uptime_seconds": int(time.time() - self.stats.started_at) if self.stats.started_at else 0,
            "is_running": self.is_running,
        }
