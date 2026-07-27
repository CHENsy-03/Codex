"""V2.0 Metrics Collector"""
import time, threading
from collections import defaultdict

class MetricsCollector:
    _instance = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._init()
        return cls._instance

    def _init(self):
        self._lock = threading.Lock()
        self.counters = defaultdict(int)
        self.gauges = defaultdict(float)
        self._start_time = int(time.time())

    def incr(self, name: str, value: int = 1):
        with self._lock:
            self.counters[name] += value

    def set_gauge(self, name: str, value: float):
        with self._lock:
            self.gauges[name] = value

    def get_all(self) -> dict:
        with self._lock:
            return {
                "counters": dict(self.counters),
                "gauges": dict(self.gauges),
                "uptime_seconds": int(time.time()) - self._start_time,
            }

    @classmethod
    def get_instance(cls):
        return cls()
