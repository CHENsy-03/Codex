"""串口监控 — 实时监听串口数据，桥接到Pipeline"""
import time, threading, logging
logger = logging.getLogger(__name__)

class SerialMonitor:
    def __init__(self, pipeline=None):
        self._ports = {}; self._pipeline = pipeline; self._running = False; self._stats = {"total":0,"parsed":0,"errors":0}

    def attach(self, port, manager, pipeline=None):
        self._ports[port] = {"manager": manager, "pipeline": pipeline, "last_data": 0, "data_count": 0}
        if pipeline: self._pipeline = pipeline

    def start(self):
        self._running = True
        for port in self._ports:
            threading.Thread(target=self._monitor, args=(port,), daemon=True).name = f"mon-{port}"
        logger.info("SerialMonitor started (%d ports)", len(self._ports))

    def _monitor(self, port):
        info = self._ports.get(port)
        if not info: return
        mgr = info["manager"]
        while self._running:
            try:
                line = mgr.read(port)
                if line:
                    info["last_data"] = time.time()
                    info["data_count"] += 1
                    self._stats["total"] += 1
                    if info["pipeline"]:
                        info["pipeline"].feed(line)
                        self._stats["parsed"] += 1
                    else:
                        for cb in getattr(mgr, "_callbacks", []): cb(line)
                else:
                    time.sleep(0.05)
            except Exception as e:
                self._stats["errors"] += 1
                logger.warning("Monitor %s error: %s", port, e)
                time.sleep(1)

    def stats(self, port=None):
        if port:
            info = self._ports.get(port)
            if not info: return {}
            return {"connected": True, "data_count": info["data_count"], "idle": int(time.time()-info["last_data"])}
        result = {}
        for p, info in self._ports.items():
            result[p] = {"connected": True, "data_count": info["data_count"], "idle": int(time.time()-info["last_data"])}
        result["_total"] = self._stats
        return result

    def stop(self): self._running = False
