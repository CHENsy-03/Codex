"""V4 EventBus — 进程内消息总线，替代 Kafka/Queue 单节点方案"""
import threading, queue, time, logging
from collections import defaultdict

logger = logging.getLogger(__name__)

class EventBus:
    def __init__(self):
        self._subscribers = defaultdict(list)
        self._lock = threading.Lock()
        self._history = []
        self._max_history = 1000

    def subscribe(self, topic: str, callback):
        with self._lock:
            self._subscribers[topic].append(callback)
            logger.debug("Subscribed to %s", topic)

    def unsubscribe(self, topic: str, callback):
        with self._lock:
            if callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)

    def publish(self, topic: str, data):
        """同步发布 — 直接调用所有订阅者"""
        with self._lock:
            cbs = list(self._subscribers.get(topic, []))
        self._history.append({"topic": topic, "time": time.time(), "data_len": len(str(data))})
        if len(self._history) > self._max_history:
            self._history.pop(0)
        for cb in cbs:
            try:
                cb(data)
            except Exception as e:
                logger.warning("EventBus %s error: %s", topic, e)

    def publish_async(self, topic: str, data):
        """异步发布 — 在新线程中执行，不阻塞调用方"""
        threading.Thread(target=self.publish, args=(topic, data), daemon=True).start()

    def stats(self):
        with self._lock:
            return {
                "topics": {t: len(cbs) for t, cbs in self._subscribers.items()},
                "total_published": len(self._history),
                "recent_topics": list(set(h["topic"] for h in self._history[-50:]))
            }

bus = EventBus()
"""V4-Local EventBus — 标准化事件总线

功能：
- 标准 Event 结构 (id/timestamp/topic/source/payload)
- 预定义 Topic 体系
- 发布/订阅/取消订阅
- 时间范围回放 (replay)
- 流式 Pipeline 链处理
- 线程安全
"""
import uuid, time, logging, threading, heapq
from collections import defaultdict
from dataclasses import dataclass, field, asdict
from typing import Callable, Optional

logger = logging.getLogger(__name__)

# ─── 标准事件结构 ───
@dataclass
class Event:
    id: str = ""
    timestamp: float = 0.0
    topic: str = ""
    source: str = ""
    payload: dict = field(default_factory=dict)

    def __post_init__(self):
        if not self.id:
            self.id = str(uuid.uuid4())[:12]
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "Event":
        return cls(**d)


# ─── 预定义 Topic 体系 ───
class Topics:
    DEVICE_RAW     = "device.raw"       # 设备原始报文
    DEVICE_PARSED  = "device.parsed"     # 解析后的结构化数据
    GPS_DATA       = "gps.data"          # GPS 定位数据
    GPS_ANOMALY    = "gps.anomaly"       # GPS 异常事件
    CM510_SIGNAL   = "cm510.signal"      # CM510 信号
    K803_SIGNAL    = "k803.signal"       # K803 信号
    ANALYSIS_RESULT = "analysis.result"  # 比对分析结果
    ANOMALY_DETECTED = "anomaly.detected" # 异常检测事件
    SURVEY_RESULT  = "survey.result"     # 测量结果
    SYSTEM_LOG     = "system.log"        # 系统日志

    @classmethod
    def all(cls) -> list:
        return [v for k, v in vars(cls).items() if not k.startswith("_") and isinstance(v, str)]


# ─── 流式 Pipeline ───
class StreamPipeline:
    """链式处理器: Raw → Parser → Engine → Plugin → Storage"""

    def __init__(self):
        self._stages = []  # list of (name, handler)

    def add_stage(self, name: str, handler: Callable[[Event], Optional[Event]]):
        """添加处理阶段，handler 返回 Event 或 None（丢弃）"""
        self._stages.append((name, handler))
        return self

    def process(self, event: Event) -> Optional[Event]:
        """将事件依次通过所有阶段"""
        current = event
        for name, handler in self._stages:
            try:
                current = handler(current)
                if current is None:
                    logger.debug("Pipeline stage %s dropped event %s", name, event.id)
                    return None
            except Exception as e:
                logger.error("Pipeline stage %s error: %s", name, e)
                return None
        return current


# ─── 事件总线 ───
class EventBus:
    def __init__(self, max_history: int = 10000):
        self._subscribers: dict[str, list[Callable]] = defaultdict(list)
        self._lock = threading.Lock()
        self._history: list[Event] = []
        self._max_history = max_history
        self._pipeline: Optional[StreamPipeline] = None
        self._event_count = 0

    def set_pipeline(self, pipeline: StreamPipeline):
        """设置全局流式 Pipeline"""
        self._pipeline = pipeline

    # ── 发布 ──
    def publish(self, topic: str, payload: dict, source: str = "") -> Event:
        """发布事件（同步，阻塞订阅者）"""
        event = Event(topic=topic, source=source, payload=payload)
        return self._do_publish(event)

    def publish_event(self, event: Event) -> Event:
        """直接发布 Event 对象"""
        return self._do_publish(event)

    def publish_async(self, topic: str, payload: dict, source: str = ""):
        """异步发布（不阻塞调用方）"""
        event = Event(topic=topic, source=source, payload=payload)
        threading.Thread(target=self._do_publish, args=(event,), daemon=True).start()

    def _do_publish(self, event: Event) -> Event:
        # 通过 Pipeline
        if self._pipeline:
            result = self._pipeline.process(event)
            if result is None:
                return event  # pipeline 丢弃了
            event = result

        # 分发给订阅者
        with self._lock:
            cbs = list(self._subscribers.get(event.topic, []))
            # 也分发给通配订阅 "*"
            wild_cbs = list(self._subscribers.get("*", []))
            all_cbs = cbs + wild_cbs

            # 存入历史（深拷贝摘要）
            self._history.append(event)
            if len(self._history) > self._max_history:
                self._history.pop(0)
            self._event_count += 1

        for cb in all_cbs:
            try:
                cb(event)
            except Exception as e:
                logger.warning("EventBus subscriber error on %s: %s", event.topic, e)
        return event

    # ── 订阅 ──
    def subscribe(self, topic: str, callback: Callable[[Event], None]):
        """订阅主题，topic="*" 订阅所有"""
        with self._lock:
            if callback not in self._subscribers[topic]:
                self._subscribers[topic].append(callback)
            logger.debug("Subscribed to %s (total %d)", topic, len(self._subscribers[topic]))

    def unsubscribe(self, topic: str, callback: Callable):
        with self._lock:
            if callback in self._subscribers[topic]:
                self._subscribers[topic].remove(callback)

    # ── 回放 ──
    def replay(self, topic: str, start_time: float = 0, end_time: float = 0,
               callback: Optional[Callable] = None) -> list[Event]:
        """按时间范围回放历史事件"""
        if end_time <= 0:
            end_time = time.time() + 1
        matched = []
        with self._lock:
            for ev in self._history:
                if ev.topic == topic and start_time <= ev.timestamp <= end_time:
                    matched.append(ev)
        if callback:
            for ev in matched:
                try:
                    callback(ev)
                except Exception as e:
                    logger.warning("Replay callback error: %s", e)
        return matched

    def replay_all(self, callback: Optional[Callable] = None) -> list[Event]:
        """回放全部历史"""
        with self._lock:
            events = list(self._history)
        if callback:
            for ev in events:
                try:
                    callback(ev)
                except Exception as e:
                    logger.warning("Replay all callback error: %s", e)
        return events

    # ── 统计 ──
    def stats(self) -> dict:
        with self._lock:
            topic_counts = defaultdict(int)
            for ev in self._history[-500:]:
                topic_counts[ev.topic] += 1
            return {
                "total_events": self._event_count,
                "history_size": len(self._history),
                "max_history": self._max_history,
                "topics": {t: len(cbs) for t, cbs in self._subscribers.items()},
                "recent_topic_activity": dict(topic_counts),
                "pipeline_active": self._pipeline is not None,
            }

    def clear_history(self):
        with self._lock:
            self._history.clear()


# ── 全局单例 ──
bus = EventBus()
pipeline = StreamPipeline()
bus.set_pipeline(pipeline)
