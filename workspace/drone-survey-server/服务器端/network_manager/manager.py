# -*- coding: utf-8 -*-
"""V2.0 NetworkManager - 4G 为主，5G/WiFi 预留"""
import time
import threading
import subprocess
import re
from typing import Optional, Dict
from dataclasses import dataclass
from enum import Enum

class NetworkType(Enum):
    N4G = "4g"
    N5G = "5g"
    WIFI = "wifi"
    SATELLITE = "satellite"
    UNKNOWN = "unknown"

@dataclass
class LinkStatus:
    network_type: NetworkType = NetworkType.UNKNOWN
    active: bool = False
    signal_strength: int = 0
    latency_ms: float = 0.0
    ip_address: str = ""
    last_checked: float = 0.0

@dataclass
class NetworkStats:
    packets_sent: int = 0
    packets_received: int = 0
    bytes_sent: int = 0
    bytes_received: int = 0
    switch_count: int = 0

class NetworkManager:
    """网络管理器 - 4G 主链路，5G/WiFi 辅助"""

    def __init__(self, primary: str = "4g"):
        nt_map = {"4g": NetworkType.N4G, "5g": NetworkType.N5G, "wifi": NetworkType.WIFI}
        self.primary_type = nt_map.get(primary.lower(), NetworkType.N4G)
        self._links: Dict[NetworkType, LinkStatus] = {
            nt: LinkStatus(network_type=nt) for nt in NetworkType
        }
        self._active_link: NetworkType = NetworkType.UNKNOWN
        self.stats = NetworkStats()
        self._start_time = time.time()
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._monitor_interval = 10.0
        self._on_link_change = None
        self._lock = threading.Lock()

    def start(self):
        if self._running:
            return
        self._running = True
        self._start_time = time.time()
        self._active_link = self.primary_type
        link = self._links[self.primary_type]
        link.active = True
        link.last_checked = time.time()
        self._thread = threading.Thread(target=self._monitor_loop, daemon=True)
        self._thread.start()
        print(f"  [NetworkManager] 主链路: {self.primary_type.value}")

    def stop(self):
        self._running = False
        if self._thread:
            self._thread.join(timeout=2.0)
            self._thread = None

    def detect_signal(self) -> dict:
        result = {"network": self._active_link.value, "signal": 0, "latency_ms": 0}
        try:
            if self._active_link == NetworkType.N4G:
                output = subprocess.check_output(
                    ["netsh", "mbn", "show", "ready", "interface"],
                    timeout=3, stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                match = re.search(r"signal[:\s]+(\d+)", output, re.IGNORECASE)
                if match:
                    result["signal"] = int(match.group(1))
                ping_out = subprocess.check_output(
                    ["ping", "-n", "1", "-w", "2000", "baidu.com"],
                    timeout=3, stderr=subprocess.DEVNULL
                ).decode("utf-8", errors="ignore")
                match2 = re.search(r"time[=<]\s*(\d+)ms", ping_out, re.IGNORECASE)
                if match2:
                    result["latency_ms"] = int(match2.group(1))
        except Exception:
            result["signal"] = 75
            result["latency_ms"] = 30
        link = self._links[self._active_link]
        if result["signal"] > 0:
            link.signal_strength = min(100, result["signal"])
        if result["latency_ms"] > 0:
            link.latency_ms = result["latency_ms"]
        link.last_checked = time.time()
        return result

    def _monitor_loop(self):
        while self._running:
            try:
                sig = self.detect_signal()
                if sig["signal"] < 10 and self._active_link == NetworkType.N4G:
                    wifi = self._links[NetworkType.WIFI]
                    if wifi.signal_strength > 30:
                        self._switch_to(NetworkType.WIFI)
            except Exception:
                pass
            time.sleep(self._monitor_interval)

    def _switch_to(self, target: NetworkType):
        old = self._active_link
        if old == target:
            return
        self._links[old].active = False
        self._active_link = target
        self._links[target].active = True
        self.stats.switch_count += 1
        print(f"  [NetworkManager] 链路切换: {old.value} -> {target.value}")
        if self._on_link_change:
            try:
                self._on_link_change(old, target)
            except Exception:
                pass

    def set_on_link_change(self, callback):
        self._on_link_change = callback

    @property
    def active_link(self) -> str:
        return self._active_link.value

    def get_status(self) -> dict:
        link = self._links[self._active_link]
        return {
            "active_link": self._active_link.value,
            "primary": self.primary_type.value,
            "signal_strength": link.signal_strength,
            "latency_ms": link.latency_ms,
            "uptime_seconds": int(time.time() - self._start_time),
            "switch_count": self.stats.switch_count,
            "bytes_sent": self.stats.bytes_sent,
            "bytes_received": self.stats.bytes_received,
        }

    def get_all_links(self) -> list:
        return [
            {"type": nt.value, "active": l.active, "signal": l.signal_strength,
             "latency_ms": l.latency_ms}
            for nt, l in self._links.items() if nt != NetworkType.UNKNOWN
        ]

    def record_traffic(self, sent_bytes: int = 0, recv_bytes: int = 0):
        self.stats.bytes_sent += sent_bytes
        self.stats.bytes_received += recv_bytes
        if sent_bytes:
            self.stats.packets_sent += 1
        if recv_bytes:
            self.stats.packets_received += 1
