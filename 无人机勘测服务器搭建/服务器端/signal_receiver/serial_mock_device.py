"""CM510 串口模拟设备 — 定时发送报文，支持速率控制和异常注入"""
import time, random, threading, logging
logger = logging.getLogger(__name__)

class SerialMockDevice:
    def __init__(self, device_id="MOCK-CM510-001", interval=1.0):
        self.device_id = device_id
        self.interval = interval
        self._running = False; self._callbacks = []; self._inject_error = False

    def on_data(self, cb): self._callbacks.append(cb)

    def set_rate(self, interval): self.interval = interval

    def inject_error(self, enable: bool): self._inject_error = enable

    def _gen_cm510(self):
        lat = round(30.0 + random.uniform(-0.02, 0.02), 6)
        lng = round(120.5 + random.uniform(-0.02, 0.02), 6)
        alt = round(50 + random.uniform(-5, 5), 2)
        speed = round(random.uniform(0, 60), 1)
        heading = round(random.uniform(0, 360), 1)
        sats = random.randint(4, 15)
        signal = random.randint(1, 5)
        ts = int(time.time())
        crc = random.randint(0, 255)
        if self._inject_error:
            lat = 999.0  # 异常坐标
        return f"$CM510,{self.device_id},{lat:.6f},{lng:.6f},{speed:.1f},{heading:.1f},{alt:.2f},{sats},{signal},{ts}*{crc:02X}"

    def start(self):
        self._running = True
        threading.Thread(target=self._run, daemon=True).start()
        logger.info("Mock device started: %s (interval=%.1fs)", self.device_id, self.interval)

    def _run(self):
        while self._running:
            data = self._gen_cm510()
            for cb in self._callbacks: cb(data)
            time.sleep(self.interval)

    def stop(self): self._running = False
