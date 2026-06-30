"""V4-Local GPS 数据回放引擎

功能：
- 从文件加载 GPS 报文并按时间线回放
- 支持延时模拟（真实时间比例/加速）
- 通过 EventBus 发布回放事件
- 支持循环回放
"""
import time, logging, json, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Event, Topics, bus
from .timeline_engine import TimelineEngine

logger = logging.getLogger(__name__)

class GPSReplayEngine:
    def __init__(self, speed: float = 1.0):
        self.speed = speed
        self.timeline = TimelineEngine()
        self._running = False
        self._replayed = 0

    def load_file(self, filepath: str) -> int:
        """从文件加载 GPS/报文数据"""
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line:
                    continue
                # 自动检测格式
                if line.startswith("#BESTPOSA"):
                    ev = {"type": "bestpos", "raw": line}
                elif line.startswith("$"):
                    ev = {"type": "nmea", "raw": line}
                else:
                    ev = {"type": "json", "raw": line}
                self.timeline.add_event(ev)
                count += 1
        logger.info("Loaded %d events from %s", count, filepath)
        return count

    def load_data(self, data_list: list) -> int:
        """直接加载数据列表"""
        for item in data_list:
            self.timeline.add_event(item)
        return len(data_list)

    def run(self, loop: bool = False, source: str = "replay") -> int:
        """执行回放"""
        events = self.timeline.get_events()
        if not events:
            logger.warning("No events to replay")
            return 0
        self._running = True
        self._replayed = 0
        start_time = time.time()
        for i, ev in enumerate(events):
            if not self._running:
                break
            # 发布到 EventBus
            if ev.get("type") == "bestpos":
                payload = {"raw": ev["raw"], "replay_index": i}
                bus.publish(Topics.DEVICE_RAW, payload, source=source)
            elif ev.get("type") == "nmea":
                payload = {"raw": ev["raw"], "replay_index": i}
                bus.publish(Topics.GPS_DATA, payload, source=source)
            else:
                payload = {**ev, "replay_index": i}
                bus.publish(Topics.GPS_DATA, payload, source=source)
            self._replayed += 1
            # 模拟延时（按速度比例）
            delay = self.timeline.get_delay(i, default=0.1)
            if delay > 0 and i < len(events) - 1:
                time.sleep(delay / self.speed)
        elapsed = time.time() - start_time
        logger.info("Replay done: %d events in %.2fs (speed=%.1fx)", self._replayed, elapsed, self.speed)
        return self._replayed

    def run_geo(self, lat: float, lng: float, alt: float, count: int = 1,
                source: str = "replay:geo") -> int:
        """回放指定坐标的模拟 GPS 数据"""
        for i in range(count):
            payload = {"lat": lat, "lng": lng, "alt": alt,
                       "replay_index": i, "type": "geo_sim"}
            bus.publish(Topics.GPS_DATA, payload, source=source)
            self._replayed += 1
            time.sleep(0.1)
        return count

    def stop(self):
        self._running = False

    def stats(self) -> dict:
        return {
            "events_loaded": self.timeline.count(),
            "events_replayed": self._replayed,
            "speed": self.speed,
            "running": self._running,
        }
