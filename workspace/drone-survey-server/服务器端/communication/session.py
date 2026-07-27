"""Session Manager V2.0 - 设备会话管理 + 心跳检测"""

import time
import uuid
import threading
from dataclasses import dataclass, field
from typing import Dict, Optional


@dataclass
class DeviceSession:
    """单个设备会话"""
    device_id: str
    session_id: str = ""
    channel: str = "tcp"            # tcp / mqtt / serial
    status: str = "offline"         # online / offline / timeout
    last_seq: int = 0
    heartbeat_time: int = 0
    created_at: int = field(default_factory=lambda: int(time.time()))

    def touch(self):
        self.heartbeat_time = int(time.time())
        self.status = "online"

    def is_timeout(self, timeout_sec: int = 120) -> bool:
        if self.status != "online":
            return False
        return int(time.time()) - self.heartbeat_time > timeout_sec


class SessionManager:
    """管理所有设备会话"""

    def __init__(self, server_id: str = "", session_timeout: int = 120,
                 heartbeat_interval: int = 30):
        self.server_id = server_id
        self.session_timeout = session_timeout
        self.heartbeat_interval = heartbeat_interval
        self._sessions: Dict[str, DeviceSession] = {}
        self._lock = threading.Lock()
        self._db = None       # DuckDBManager reference (optional)

    def set_db(self, db):
        """绑定 DuckDBManager，启用持久化"""
        self._db = db

    def create_session(self, device_id: str, channel: str = "tcp") -> DeviceSession:
        """创建或恢复会话"""
        with self._lock:
            if device_id in self._sessions:
                session = self._sessions[device_id]
                session.touch()
                return session

            session = DeviceSession(
                device_id=device_id,
                session_id=str(uuid.uuid4())[:16],
                channel=channel,
            )
            session.touch()
            self._sessions[device_id] = session

            # Persist to DuckDB
            if self._db:
                try:
                    self._db.upsert_session(
                        device_id, session.session_id,
                        channel, "online")
                except Exception:
                    pass

            return session

    def get_session(self, device_id: str) -> Optional[DeviceSession]:
        return self._sessions.get(device_id)

    def heartbeat(self, device_id: str):
        """处理设备心跳"""
        with self._lock:
            session = self._sessions.get(device_id)
            if session:
                session.touch()
                return session
            return self.create_session(device_id)

    def disconnect(self, device_id: str):
        """设备断开连接"""
        with self._lock:
            if device_id in self._sessions:
                self._sessions[device_id].status = "offline"
                if self._db:
                    try:
                        self._db.upsert_session(
                            device_id,
                            self._sessions[device_id].session_id,
                            status="offline")
                    except Exception:
                        pass

    def cleanup_timeouts(self) -> list:
        """清理超时会话, 返回超时设备列表"""
        timed_out = []
        with self._lock:
            for device_id, session in list(self._sessions.items()):
                if session.is_timeout(self.session_timeout):
                    session.status = "timeout"
                    timed_out.append(device_id)
                    if self._db:
                        try:
                            self._db.upsert_session(
                                device_id, session.session_id, status="timeout")
                        except Exception:
                            pass
        return timed_out

    def get_statistics(self) -> dict:
        """会话统计"""
        online = sum(1 for s in self._sessions.values() if s.status == "online")
        offline = sum(1 for s in self._sessions.values() if s.status == "offline")
        return {"total": len(self._sessions), "online": online, "offline": offline}

    def __len__(self):
        return len(self._sessions)
