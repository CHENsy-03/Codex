"""V4 模拟设备 — 用于测试和压力测试"""
import time, random, threading

class MockCM510:
    def __init__(self, device_id="MOCK-001", interval=1.0):
        self.device_id = device_id; self.interval = interval
        self._callbacks = []; self._running = False

    def on_data(self, cb): self._callbacks.append(cb)

    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()

    def _run(self):
        while self._running:
            lat = round(30.0 + random.uniform(-0.05, 0.05), 6)
            lng = round(120.5 + random.uniform(-0.05, 0.05), 6)
            msg = f"$CM510,{self.device_id},{lat},{lng},{random.uniform(0,60):.1f},{random.uniform(0,360):.1f},{random.uniform(0,200):.2f},{random.randint(4,15)},{random.randint(1,5)},{int(time.time())}*{random.randint(0,255):02X}"
            for cb in self._callbacks: cb(msg)
            time.sleep(self.interval)

    def stop(self): self._running = False
