"""结果服务 — 结果持久化存储

支持内存索引 + JSON 文件持久化。
"""
import json, os, logging, threading, time
from .schema import ResultRecord

logger = logging.getLogger(__name__)

class ResultStore:
    def __init__(self, filepath: str = ""):
        self._lock = threading.Lock()
        self._data: dict[str, ResultRecord] = {}
        self._filepath = filepath or os.path.join(
            os.path.dirname(__file__), "result_data.json"
        )
        self._load()

    def save(self, record: ResultRecord):
        with self._lock:
            self._data[record.device_id] = record
            self._persist()
        logger.debug("Result saved: %s -> %d", record.device_id, record.result)

    def get(self, device_id: str) -> ResultRecord:
        with self._lock:
            return self._data.get(device_id)

    def get_or_default(self, device_id: str) -> dict:
        r = self.get(device_id)
        if r:
            return r.to_dict()
        return {"device_id": device_id, "result": -1, "reason": "未计算"}

    def get_all(self) -> list[dict]:
        with self._lock:
            return [r.to_dict() for r in self._data.values()]

    def count(self) -> int:
        with self._lock:
            return len(self._data)

    def clear(self):
        with self._lock:
            self._data.clear()
            self._persist()

    def _persist(self):
        try:
            with open(self._filepath, "w", encoding="utf-8") as f:
                json.dump({k: r.to_dict() for k, r in self._data.items()},
                          f, ensure_ascii=False, indent=2)
        except Exception as e:
            logger.warning("ResultStore persist error: %s", e)

    def _load(self):
        if os.path.exists(self._filepath):
            try:
                with open(self._filepath, "r", encoding="utf-8") as f:
                    raw = json.load(f)
                    for k, v in raw.items():
                        self._data[k] = ResultRecord.from_dict(v)
            except Exception as e:
                logger.warning("ResultStore load error: %s", e)

store = ResultStore()
