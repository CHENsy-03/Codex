"""5.docx §3 EventBus 核心

标准事件结构:
    id: str, timestamp: int, topic: str, device_id: str, data: dict
"""
import uuid, time, logging, threading
from collections import defaultdict
from typing import Callable, Optional

logger = logging.getLogger(__name__)

class Event:
    def __init__(self, topic="", device_id="", data=None):
        self.id = str(uuid.uuid4())[:8]
        self.timestamp = int(time.time() * 1000)
        self.topic = topic
        self.device_id = device_id
        self.data = data or {}

    def to_dict(self):
        return {"id": self.id, "timestamp": self.timestamp,
                "topic": self.topic, "device_id": self.device_id, "data": self.data}

class EventBus:
    def __init__(self, max_history=5000):
        self._subs = defaultdict(list)
        self._lock = threading.Lock()
        self._history = []
        self._max = max_history
        self._pipeline = None
        self._count = 0

    def set_pipeline(self, p):
        self._pipeline = p

    def publish(self, topic, event):
        if isinstance(event, Event):
            e = event
        elif isinstance(event, dict):
            e = Event(topic=event.get("topic", topic),
                      device_id=event.get("device_id", ""),
                      data=event.get("data", event))
        else:
            e = Event(topic=topic, data={"raw": str(event)})
        if self._pipeline:
            r = self._pipeline.process(e.to_dict())
            if r is None: return
            e = Event(**r)
        with self._lock:
            cbs = list(self._subs.get(e.topic, []))
            wcbs = list(self._subs.get("*", []))
            self._history.append(e)
            if len(self._history) > self._max: self._history.pop(0)
            self._count += 1
        for cb in cbs + wcbs:
            try: cb(e)
            except Exception as ex: logger.warning("publish error: %s", ex)

    def subscribe(self, topic, handler):
        with self._lock:
            if handler not in self._subs[topic]:
                self._subs[topic].append(handler)

    def unsubscribe(self, topic, handler):
        with self._lock:
            if handler in self._subs[topic]:
                self._subs[topic].remove(handler)

    def replay(self, topic, start_ms=0, end_ms=0):
        if end_ms <= 0: end_ms = int(time.time() * 1000) + 1000
        res = []
        with self._lock:
            for e in self._history:
                if e.topic == topic and start_ms <= e.timestamp <= end_ms:
                    res.append(e)
        return res

    def stats(self):
        with self._lock:
            return {"count": self._count, "history": len(self._history),
                    "max_history": self._max,
                    "topics": {t: len(c) for t, c in self._subs.items()}}

bus = EventBus()
