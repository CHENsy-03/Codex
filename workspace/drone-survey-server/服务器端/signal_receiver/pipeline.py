"""V4-Local Stream Pipeline — 事件流处理管道

符合 Document 3 Step 2 规范：
- Raw Event → Parser → Rule Engine → Plugin → Storage
- 集成 EventBus 发布标准事件
- 多线程 Worker 处理
"""
import threading, logging, time, json
from upgrade.eventbus import Event, Topics, bus
from typing import Optional

logger = logging.getLogger(__name__)

class StreamPipeline:
    def __init__(self, maxsize=10000, workers=2):
        self._queue = __import__("queue").Queue(maxsize=maxsize)
        self._workers_count = workers
        self._running = False
        self._threads = []
        self._parsed_count = 0
        self._error_count = 0

    def start(self):
        self._running = True
        for i in range(self._workers_count):
            t = threading.Thread(target=self._process_loop, daemon=True, name=f"stream-{i}")
            t.start()
            self._threads.append(t)
        logger.info("StreamPipeline started (%d workers)", self._workers_count)

    def feed(self, raw: str, source: str = "") -> bool:
        """接收原始报文，进入队列"""
        try:
            self._queue.put((raw, source), timeout=1)
            return True
        except __import__("queue").Full:
            self._error_count += 1
            return False

    def _process_loop(self):
        """Worker 主循环：Raw → 自动检测 → 解析 → EventBus 发布"""
        while self._running:
            try:
                raw, source = self._queue.get(timeout=1)
            except __import__("queue").Empty:
                continue
            try:
                parsed = self._auto_parse(raw)
                if parsed:
                    bus.publish(Topics.DEVICE_PARSED, parsed, source=source)
                    self._parsed_count += 1
                else:
                    # 无法解析也发布原始事件
                    bus.publish(Topics.DEVICE_RAW, {"raw": raw}, source=source)
            except Exception as e:
                self._error_count += 1
                logger.warning("StreamPipeline error: %s", e)

    def _auto_parse(self, raw: str) -> Optional[dict]:
        """自动检测报文类型并解析"""
        raw = raw.strip()
        if not raw:
            return None
        if raw.startswith("#BESTPOSA"):
            try:
                from plugins.bestpos import BESTPOSASCIIParser
                return BESTPOSASCIIParser.parse(raw)
            except Exception as e:
                logger.debug("BESTPOS parse error: %s", e)
                return None
        elif raw.startswith("$GP") or raw.startswith("$GN") or raw.startswith("$GA"):
            try:
                from plugins.nmea import NMEAParser
                parser = NMEAParser()
                result = parser.parse(raw)
                if result and hasattr(result, "to_dict"):
                    return result.to_dict()
                return result
            except Exception as e:
                logger.debug("NMEA parse error: %s", e)
                return None
        elif raw.startswith("$CM510"):
            try:
                from plugins.cm510_parser import CM510Parser
                return CM510Parser.parse(raw)
            except Exception as e:
                logger.debug("CM510 parse error: %s", e)
                return None
        # JSON 格式
        elif raw.startswith("{"):
            try:
                return json.loads(raw)
            except json.JSONDecodeError:
                return None
        return None

    def stop(self):
        self._running = False
        for t in self._threads:
            t.join(timeout=3)

    def stats(self) -> dict:
        return {
            "queue_size": self._queue.qsize(),
            "maxsize": self._queue.maxsize,
            "parsed": self._parsed_count,
            "errors": self._error_count,
            "running": self._running,
            "workers": self._workers_count,
        }

    def status_line(self) -> str:
        return f"Pipeline: q={self._queue.qsize()} parsed={self._parsed_count} err={self._error_count} running={self._running}"

pipeline = StreamPipeline()
