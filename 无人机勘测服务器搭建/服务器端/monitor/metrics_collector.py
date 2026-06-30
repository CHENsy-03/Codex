
"""Real-time network health metrics collector (thread-safe)

Records: packet loss, CRC failures, latency, success rates
Used by: bridge_service.py (injected) and reporter.py (read-only)
"""

import time
import threading
from collections import defaultdict


class _DeviceMetrics:
    """Per-device metrics storage"""
    __slots__ = ("total_msgs", "lost_packets", "crc_failures",
                  "retransmits", "successes", "failures",
                  "last_seq", "start_time", "latency_samples")

    def __init__(self):
        self.total_msgs = 0
        self.lost_packets = 0
        self.crc_failures = 0
        self.retransmits = 0
        self.successes = 0
        self.failures = 0
        self.last_seq = 0
        self.start_time = time.time()
        self.latency_samples = []


class MetricsCollector:
    """Thread-safe singleton: collects network health metrics in real-time.

    Usage in bridge:
        metrics = MetricsCollector.get_instance()
        metrics.record_msg("device-1")
        metrics.record_crc_fail("device-1")
        metrics.record_loss("device-1", from_seq=5, to_seq=7)
    """
    _instance = None
    _lock = threading.Lock()

    def __init__(self):
        self._devices = defaultdict(_DeviceMetrics)
        self._data_lock = threading.Lock()

    @classmethod
    def get_instance(cls):
        with cls._lock:
            if cls._instance is None:
                cls._instance = cls()
            return cls._instance

    # ── Record methods ──

    def record_msg(self, device_id: str, seq: int = 0):
        """Record one received message"""
        with self._data_lock:
            dm = self._devices[device_id]
            dm.total_msgs += 1
            if seq > 0:
                if dm.last_seq > 0 and seq > dm.last_seq + 1:
                    gap = seq - dm.last_seq - 1
                    dm.lost_packets += gap
                dm.last_seq = seq

    def record_crc_fail(self, device_id: str):
        """Record one CRC integrity failure"""
        with self._data_lock:
            self._devices[device_id].crc_failures += 1

    def record_loss(self, device_id: str, seq_from: int, seq_to: int):
        """Record detected packet loss range"""
        with self._data_lock:
            self._devices[device_id].lost_packets += (seq_to - seq_from + 1)

    def record_retransmit(self, device_id: str):
        """Record one retransmission request"""
        with self._data_lock:
            self._devices[device_id].retransmits += 1

    def record_success(self, device_id: str):
        """Record one successful survey processing"""
        with self._data_lock:
            self._devices[device_id].successes += 1

    def record_failure(self, device_id: str):
        """Record one failed survey processing"""
        with self._data_lock:
            self._devices[device_id].failures += 1

    def record_latency(self, device_id: str, ms: float):
        """Record a message round-trip latency sample (ms)"""
        with self._data_lock:
            dm = self._devices[device_id]
            dm.latency_samples.append(ms)
            if len(dm.latency_samples) > 1000:
                dm.latency_samples = dm.latency_samples[-500:]

    # ── Query methods ──

    def get_device_metrics(self, device_id: str) -> dict:
        """Get computed metrics for one device"""
        with self._data_lock:
            dm = self._devices.get(device_id)
            if not dm:
                return {}
            return self._compute(dm, device_id)

    def get_all_metrics(self) -> dict:
        """Get metrics for all devices"""
        with self._data_lock:
            result = {}
            for device_id, dm in self._devices.items():
                result[device_id] = self._compute(dm, device_id)
            return result

    def get_summary(self) -> dict:
        """Get aggregate metrics across all devices"""
        with self._data_lock:
            total = _DeviceMetrics()
            for dm in self._devices.values():
                total.total_msgs += dm.total_msgs
                total.lost_packets += dm.lost_packets
                total.crc_failures += dm.crc_failures
                total.retransmits += dm.retransmits
                total.successes += dm.successes
                total.failures += dm.failures
                total.latency_samples.extend(dm.latency_samples)
            total.start_time = min(
                (dm.start_time for dm in self._devices.values()), default=time.time()
            )
            return self._compute(total, "ALL_DEVICES")

    def reset(self, device_id: str = None):
        """Reset metrics for one device or all"""
        with self._data_lock:
            if device_id:
                self._devices.pop(device_id, None)
            else:
                self._devices.clear()

    @staticmethod
    def _compute(dm, device_id):
        """Compute rates and status from raw counters"""
        total = dm.total_msgs
        loss_rate = (dm.lost_packets / total * 100) if total > 0 else 0.0
        crc_rate = (dm.crc_failures / total * 100) if total > 0 else 0.0
        retrans_rate = (dm.retransmits / total * 100) if total > 0 else 0.0
        success_rate = (dm.successes / (dm.successes + dm.failures) * 100) \
                       if (dm.successes + dm.failures) > 0 else 0.0

        # Compute average latency
        avg_latency = 0.0
        if dm.latency_samples:
            avg_latency = sum(dm.latency_samples) / len(dm.latency_samples)

        # Overall status
        if loss_rate > 5.0 or crc_rate > 2.0:
            status = "CRITICAL"
        elif loss_rate > 2.0 or crc_rate > 1.0:
            status = "WARNING"
        else:
            status = "NORMAL"

        duration = time.time() - dm.start_time
        return {
            "device_id": device_id,
            "total_msgs": total,
            "lost_packets": dm.lost_packets,
            "loss_rate": round(loss_rate, 2),
            "crc_failures": dm.crc_failures,
            "crc_rate": round(crc_rate, 2),
            "retransmits": dm.retransmits,
            "retrans_rate": round(retrans_rate, 2),
            "successes": dm.successes,
            "failures": dm.failures,
            "success_rate": round(success_rate, 2),
            "avg_latency_ms": round(avg_latency, 1),
            "status": status,
            "duration_sec": int(duration),
            "start_time": dm.start_time,
        }
