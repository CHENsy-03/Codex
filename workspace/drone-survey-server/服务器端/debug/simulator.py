"""V2.0 Device Simulator"""
import time, random, threading

class SimDevice:
    def __init__(self, device_id, lat_base=28.229, lng_base=103.671, interval=1.0):
        self.device_id = device_id
        self.lat_base = lat_base
        self.lng_base = lng_base
        self.alt_base = 300.0
        self.interval = interval

    def generate_gga(self) -> bytes:
        lat = self.lat_base + random.uniform(-0.001, 0.001)
        lng = self.lng_base + random.uniform(-0.001, 0.001)
        alt = self.alt_base + random.uniform(-5, 5)
        lat_deg = int(lat)
        lat_min = (lat - lat_deg) * 60
        lng_deg = int(lng)
        lng_min = (lng - lng_deg) * 60
        lat_s = f"{lat_deg:02d}{lat_min:07.4f}"
        lng_s = f"{lng_deg:03d}{lng_min:07.4f}"
        h = random.uniform(1.0, 6.0)
        t = int(time.time()) % 86400
        return f"$GPGGA,{t:06d}.00,{lat_s},N,{lng_s},E,1,12,{h:.1f},{alt:.1f},M,0,M,,*00".encode()

class DeviceSimulator:
    def __init__(self):
        self.devices = []
        self._running = False
        self._thread = None
        self._callback = None
        self.stats = {"sent": 0, "errors": 0}

    def add_device(self, device_id, lat=28.229, lng=103.671, interval=1.0):
        self.devices.append(SimDevice(device_id, lat, lng, interval))

    def set_callback(self, callback):
        self._callback = callback

    def start(self):
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def _run(self):
        while self._running:
            for dev in self.devices:
                try:
                    data = dev.generate_gga()
                    if self._callback:
                        self._callback(dev.device_id, data)
                    self.stats["sent"] += 1
                except Exception:
                    self.stats["errors"] += 1
            wait = min(d.interval for d in self.devices) if self.devices else 1.0
            time.sleep(wait)

    def get_status(self) -> dict:
        return {"running": self._running, "devices": len(self.devices), **self.stats}
