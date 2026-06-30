"""5.docx §5.1 文件回放"""
import time, logging, os, sys
sys.path.insert(0, os.path.dirname(os.path.dirname(__file__)))
from eventbus import Event, Topic, bus
from replay.timeline_engine import TimelineEngine

logger = logging.getLogger(__name__)

class FileReplay:
    def __init__(self, speed=1.0):
        self.speed = speed
        self.timeline = TimelineEngine()
        self._replayed = 0

    def load(self, filepath):
        if not os.path.exists(filepath): raise FileNotFoundError(filepath)
        count = 0
        with open(filepath, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line: continue
                topic = Topic.GPS_DATA if line.startswith(("#","$")) else Topic.DEVICE_RAW
                self.timeline.add_event({"topic": topic, "raw": line}, 0.05)
                count += 1
        logger.info("Loaded %d lines from %s", count, filepath)
        return count

    def geo(self, lat=30.0, lng=120.5, count=10, alt=50.0):
        for i in range(count):
            self.timeline.add_event({
                "topic": Topic.GPS_DATA,
                "data": {"lat": lat+i*0.001, "lng": lng+i*0.001, "alt": alt, "e":0.01, "n":0.01, "u":0.02}
            }, 0.1)
        return count

    def run(self, source="replay"):
        events = self.timeline.get_events()
        for ev in events:
            t = ev.get("topic", Topic.GPS_DATA)
            d = ev.get("data", ev)
            bus.publish(t, Event(topic=t, device_id=source, data=d))
            self._replayed += 1
            time.sleep(self.timeline.get_delay(self._replayed-1, 0.05) / self.speed)
        return self._replayed

    def stats(self):
        return {"loaded": self.timeline.count(), "replayed": self._replayed, "speed": self.speed}
