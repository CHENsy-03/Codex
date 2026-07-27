"""V4-Local 时间线引擎 — 管理回放事件序列和时间间隔"""
import time, logging

logger = logging.getLogger(__name__)

class TimelineEvent:
    def __init__(self, data: dict, timestamp: float = 0.0):
        self.data = data
        self.timestamp = timestamp or time.time()
        self.delay_after = 0.0  # 秒

    def to_dict(self) -> dict:
        return {**self.data, "_ts": self.timestamp, "_delay": self.delay_after}

class TimelineEngine:
    def __init__(self):
        self._events: list[TimelineEvent] = []
        self._index = 0

    def add_event(self, data: dict, delay_after: float = 0.1):
        """添加事件，delay_after 为该事件后的等待时间"""
        ev = TimelineEvent(data, delay_after=delay_after)
        self._events.append(ev)

    def add_events(self, data_list: list[dict], delay: float = 0.1):
        for d in data_list:
            self.add_event(d, delay)

    def get_events(self) -> list[dict]:
        return [ev.to_dict() for ev in self._events]

    def get_delay(self, index: int, default: float = 0.1) -> float:
        if 0 <= index < len(self._events):
            return self._events[index].delay_after
        return default

    def count(self) -> int:
        return len(self._events)

    def clear(self):
        self._events.clear()
        self._index = 0

    def stats(self) -> dict:
        return {"count": len(self._events), "index": self._index}
