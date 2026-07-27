"""V4-Local 信号回放系统 — 通用信号重放

与 GPSReplayEngine 共享 TimelineEngine，
支持从文件回放各种类型信号。
"""
import time, logging, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))

from upgrade.eventbus import Event, Topics, bus
from replay.timeline_engine import TimelineEngine

logger = logging.getLogger(__name__)

class SignalReplayEngine:
    def __init__(self, speed=1.0):
        self.speed = speed
        self.timeline = TimelineEngine()
        self._replayed = 0

    def load_file(self, filepath):
        if not os.path.exists(filepath): raise FileNotFoundError(filepath)
        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                ev = {"type": "raw", "raw": line, "line_num": count + 1}
                self.timeline.add_event(ev, delay_after=0.05)
                count += 1
        logger.info("Loaded %d signals from %s", count, filepath)
        return count

    def run(self, source="signal_replay"):
        events = self.timeline.get_events()
        for i, ev in enumerate(events):
            payload = {**ev, "replay_idx": i}
            topic = Topics.DEVICE_RAW
            if ev.get("type") == "raw":
                raw = ev.get("raw", "")
                if raw.startswith("#BESTPOSA"): topic = Topics.DEVICE_RAW
                elif raw.startswith("$"): topic = Topics.GPS_DATA
            bus.publish(topic, payload, source=source)
            self._replayed += 1
            delay = self.timeline.get_delay(i, 0.05)
            if delay > 0: time.sleep(delay / self.speed)
        return self._replayed

    def stats(self):
        return {"events_loaded": self.timeline.count(), "replayed": self._replayed, "speed": self.speed}
