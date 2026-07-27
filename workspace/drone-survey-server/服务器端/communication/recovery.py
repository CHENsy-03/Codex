# -*- coding: utf-8 -*-
"""V2.0 Session Recovery - 服务器重启后恢复设备会话"""
import time
from typing import Optional, Dict, List
from dataclasses import dataclass, field
@dataclass
class RecoveredSession:
    device_id: str = ""
    session_id: str = ""
    last_sequence: int = 0
    channel: str = ""
    status: str = "offline"
    last_heartbeat: int = 0
@dataclass
class RecoveryResult:
    sessions_restored: int = 0
    ack_pending_restored: int = 0
    offline_queued: int = 0
    errors: List[str] = field(default_factory=list)
class SessionRecovery:
    def __init__(self, db=None, session_mgr=None, ack_mgr=None, gateway=None):
        self._db = db
        self._session_mgr = session_mgr
        self._ack_mgr = ack_mgr
        self._gateway = gateway
    def execute(self) -> RecoveryResult:
        result = RecoveryResult()
        if not self._db:
            result.errors.append("No database connection")
            return result
        try:
            rows = self._db.conn.execute(
                "SELECT * FROM device_session WHERE status='online' ORDER BY heartbeat_time DESC"
            ).fetchall()
            cols = [d[0] for d in self._db.conn.description]
            sessions = [dict(zip(cols, r)) for r in rows]
            for s in sessions:
                try:
                    dev_id = s.get("device_id", "")
                    ses_id = s.get("session_id", "")
                    if self._session_mgr and dev_id and ses_id:
                        self._session_mgr.create_session(dev_id, ses_id,
                                                          s.get("channel", ""))
                        result.sessions_restored += 1
                except Exception:
                    pass
        except Exception as ex:
            result.errors.append(f"Session recovery failed: {ex}")
        try:
            if self._ack_mgr and hasattr(self._ack_mgr, 'restore_pending_from_db'):
                count = self._ack_mgr.restore_pending_from_db()
                result.ack_pending_restored = count
        except Exception as ex:
            result.errors.append(f"ACK recovery failed: {ex}")
        try:
            offline_count = self._db.conn.execute(
                "SELECT count(*) FROM offline_message WHERE status='pending'"
            ).fetchone()[0]
            result.offline_queued = offline_count
        except Exception:
            pass
        print(f"  [恢复] 会话={result.sessions_restored} 待确认ACK={result.ack_pending_restored} 离线消息={result.offline_queued}")
        return result
