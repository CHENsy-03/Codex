"""信号模拟器 — 模拟 CM510/K803 发送测试数据"""
import time, random, logging, threading
logger = logging.getLogger(__name__)
class SignalSimulator:
    def __init__(self, device_id="SIM-001", interval=3):
        self.device_id = device_id; self.interval = interval
        self._running = False; self._callbacks = []
    def on_data(self, cb): self._callbacks.append(cb)
    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()
        logger.info("Simulator started: %s (interval=%ds)", self.device_id, self.interval)
    def _gen_gps(self):
        return "$CM510,{},{:.6f},{:.6f},{:.1f},{:.1f},{:.1f},{},{},{},*{:02X}".format(
            self.device_id,
            30.0 + random.uniform(-0.05, 0.05),
            120.5 + random.uniform(-0.05, 0.05),
            random.uniform(0, 60),  # speed
            random.uniform(0, 360),  # heading
            random.uniform(0, 200),  # altitude
            random.randint(4, 15),   # satellites
            random.randint(1, 5),    # signal
            int(time.time()),
            random.randint(0, 255),  # CRC
        )
    def _run(self):
        while self._running:
            data = self._gen_gps()
            [cb(data) for cb in self._callbacks]
            time.sleep(self.interval)
    def stop(self): self._running = False
