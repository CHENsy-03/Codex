"""V2.0 Health Check Module"""
import os, time, psutil, platform
from dataclasses import dataclass, field

@dataclass
class SystemHealth:
    status: str = "ok"
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    disk_percent: float = 0.0
    uptime_seconds: int = 0
    python_version: str = ""
    process_count: int = 0
    online_devices: int = 0
    db_records: int = 0
    last_check: int = field(default_factory=lambda: int(time.time()))

class HealthChecker:
    def __init__(self, db=None, server_id=""):
        self.db = db
        self.server_id = server_id
        self._start_time = int(time.time())

    def check(self) -> SystemHealth:
        h = SystemHealth(
            python_version=platform.python_version(),
            uptime_seconds=int(time.time()) - self._start_time)
        try:
            h.cpu_percent = psutil.cpu_percent(interval=0.1)
            mem = psutil.virtual_memory()
            h.memory_percent = mem.percent
            disk = psutil.disk_usage("/")
            h.disk_percent = disk.percent
            h.process_count = len(psutil.pids())
        except Exception:
            pass
        try:
            if self.db:
                h.db_records = self.db.count_gnss()
        except Exception:
            pass
        return h

    def to_dict(self, h: SystemHealth) -> dict:
        return {
            "server_id": self.server_id,
            "status": h.status,
            "cpu_percent": h.cpu_percent,
            "memory_percent": h.memory_percent,
            "disk_percent": h.disk_percent,
            "uptime_seconds": h.uptime_seconds,
            "python_version": h.python_version,
            "process_count": h.process_count,
            "online_devices": h.online_devices,
            "db_records": h.db_records,
            "last_check": h.last_check,
        }
