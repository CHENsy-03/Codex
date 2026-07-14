"""V2.0 Worker Pool - parallel parsing"""
from concurrent.futures import ThreadPoolExecutor, as_completed
import queue, threading

class WorkerPool:
    def __init__(self, num_workers=4, queue_size=1000):
        self.executor = ThreadPoolExecutor(max_workers=num_workers)
        self.task_queue = queue.Queue(maxsize=queue_size)
        self._running = False
        self.stats = {"processed": 0, "errors": 0}

    def start(self, handler):
        self._running = True
        self._thread = threading.Thread(target=self._run, args=(handler,), daemon=True)
        self._thread.start()

    def stop(self):
        self._running = False

    def submit(self, data):
        try: self.task_queue.put_nowait(data); return True
        except queue.Full: return False

    def _run(self, handler):
        while self._running:
            try:
                data = self.task_queue.get(timeout=0.5)
                try:
                    handler(data)
                    self.stats["processed"] += 1
                except Exception:
                    self.stats["errors"] += 1
            except queue.Empty:
                pass
            except Exception:
                pass

    def submit_batch(self, items, handler):
        futures = [self.executor.submit(handler, item) for item in items]
        return len(futures)

    def shutdown(self):
        self.stop()
        self.executor.shutdown(wait=True)
