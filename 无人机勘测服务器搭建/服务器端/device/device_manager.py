# -*- coding: utf-8 -*-
"""V2.0 Device Manager - 设备注册/注销/在线状态/固件版本"""
import time
import threading
from typing import Optional, Dict, List
from dataclasses import dataclass, field
from enum import Enum

class DeviceType(Enum):
    DRONE = "drone"
    RTK = "rtk"
    GROUND_STATION = "ground_station"
    SENSOR = "sensor"
    UNKNOWN = "unknown"

class DeviceStatus(Enum):
    ONLINE = "online"
    OFFLINE = "offline"
    TIMEOUT = "timeout"
    MAINTENANCE = "maintenance"
    ERROR = "error"

@dataclass
class DeviceInfo:
    device_id: str = ""
    device_type: DeviceType = DeviceType.UNKNOWN
    device_name: str = ""
    serial_number: str = ""
    firmware_version: str = ""
    hardware_version: str = ""
    status: DeviceStatus = DeviceStatus.OFFLINE
    last_seen: float = 0.0
    registered_at: float = 0.0
    heartbeat_interval: int = 30
    session_id: str = ""
    address: str = ""
    capabilities: List[str] = field(default_factory=list)
    metadata: Dict = field(default_factory=dict)

@dataclass
class DeviceStats:
    total_registered: int = 0
    online_count: int = 0
    offline_count: int = 0
    timeout_count: int = 0
    by_type: Dict[str, int] = field(default_factory=dict)

class DeviceManager:
    """设备管理器 - 设备全生命周期"""

    def __init__(self):
        self._devices: Dict[str, DeviceInfo] = {}
        self._lock = threading.Lock()
        self._on_status_change: Optional[callable] = None
        self._db: Optional[object] = None

    def set_db(self, db):
        self._db = db

    def set_on_status_change(self, callback):
        self._on_status_change = callback

    def register(self, device_id: str, device_type: str = "unknown",
                 device_name: str = "", hardware_version: str = "",
                 firmware_version: str = "", capabilities: list = None) -> DeviceInfo:
        """注册设备"""
        dt_map = {"drone": DeviceType.DRONE, "rtk": DeviceType.RTK,
                  "ground_station": DeviceType.GROUND_STATION,
                  "sensor": DeviceType.SENSOR}
        dt = dt_map.get(device_type.lower(), DeviceType.UNKNOWN)
        now = time.time()
        with self._lock:
            if device_id in self._devices:
                dev = self._devices[device_id]
                dev.device_name = device_name or dev.device_name
                dev.firmware_version = firmware_version or dev.firmware_version
                dev.hardware_version = hardware_version or dev.hardware_version
                if capabilities:
                    dev.capabilities = capabilities
                dev.last_seen = now
                if dev.status != DeviceStatus.ONLINE:
                    dev.status = DeviceStatus.ONLINE
                    self._notify(device_id, dev.status)
                return dev
            dev = DeviceInfo(
                device_id=device_id, device_type=dt,
                device_name=device_name or device_id,
                firmware_version=firmware_version,
                hardware_version=hardware_version,
                capabilities=capabilities or [],
                status=DeviceStatus.ONLINE, last_seen=now,
                registered_at=now,
            )
            self._devices[device_id] = dev
            self._notify(device_id, dev.status)
            return dev

    def unregister(self, device_id: str) -> bool:
        """注销设备"""
        with self._lock:
            if device_id in self._devices:
                self._devices[device_id].status = DeviceStatus.OFFLINE
                self._notify(device_id, DeviceStatus.OFFLINE)
                del self._devices[device_id]
                return True
        return False

    def set_online(self, device_id: str, address: str = "",
                   session_id: str = "") -> bool:
        """标记设备上线"""
        with self._lock:
            dev = self._devices.get(device_id)
            if dev:
                old = dev.status
                dev.status = DeviceStatus.ONLINE
                dev.last_seen = time.time()
                dev.address = address
                dev.session_id = session_id
                if old != DeviceStatus.ONLINE:
                    self._notify(device_id, dev.status)
                return True
        return False

    def set_offline(self, device_id: str) -> bool:
        """标记设备下线"""
        with self._lock:
            dev = self._devices.get(device_id)
            if dev:
                dev.status = DeviceStatus.OFFLINE
                self._notify(device_id, DeviceStatus.OFFLINE)
                return True
        return False

    def heartbeat(self, device_id: str) -> bool:
        """设备心跳"""
        with self._lock:
            dev = self._devices.get(device_id)
            if dev:
                dev.last_seen = time.time()
                if dev.status != DeviceStatus.ONLINE:
                    dev.status = DeviceStatus.ONLINE
                    self._notify(device_id, dev.status)
                return True
        return False

    def update_firmware(self, device_id: str, version: str) -> bool:
        """更新固件版本"""
        with self._lock:
            dev = self._devices.get(device_id)
            if dev:
                dev.firmware_version = version
                return True
        return False

    def get_device(self, device_id: str) -> Optional[DeviceInfo]:
        with self._lock:
            return self._devices.get(device_id)

    def list_devices(self, device_type: str = None,
                     status: str = None) -> List[DeviceInfo]:
        result = []
        with self._lock:
            for dev in self._devices.values():
                if device_type and dev.device_type.value != device_type.lower():
                    continue
                if status and dev.status.value != status.lower():
                    continue
                result.append(dev)
        return result

    def list_online(self) -> List[DeviceInfo]:
        return [d for d in self._devices.values()
                if d.status == DeviceStatus.ONLINE]

    def cleanup_timeouts(self, timeout_seconds: float = 120.0) -> List[str]:
        """清理超时设备，返回超时设备ID列表"""
        now = time.time()
        timed_out = []
        with self._lock:
            for device_id, dev in list(self._devices.items()):
                if (dev.status == DeviceStatus.ONLINE and
                    (now - dev.last_seen) > timeout_seconds):
                    dev.status = DeviceStatus.TIMEOUT
                    timed_out.append(device_id)
                    self._notify(device_id, DeviceStatus.TIMEOUT)
        return timed_out

    def get_statistics(self) -> DeviceStats:
        stats = DeviceStats()
        with self._lock:
            stats.total_registered = len(self._devices)
            for dev in self._devices.values():
                if dev.status == DeviceStatus.ONLINE:
                    stats.online_count += 1
                elif dev.status == DeviceStatus.OFFLINE:
                    stats.offline_count += 1
                elif dev.status == DeviceStatus.TIMEOUT:
                    stats.timeout_count += 1
                t = dev.device_type.value
                stats.by_type[t] = stats.by_type.get(t, 0) + 1
        return stats

    def _notify(self, device_id: str, status: DeviceStatus):
        if self._on_status_change:
            try:
                self._on_status_change(device_id, status.value)
            except Exception:
                pass
