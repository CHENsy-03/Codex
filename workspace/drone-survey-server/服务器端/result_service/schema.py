"""结果服务 — ResultRecord 标准数据结构

符合 4.docx §五 数据规范：
  device_id: str       设备标识
  timestamp: int       时间戳
  result: int          1=正确 0=错误 -1=未知
  reason: str          原因说明（内部使用）
"""
import time, json
from dataclasses import dataclass, field, asdict

@dataclass
class ResultRecord:
    device_id: str = ""
    timestamp: float = 0.0
    result: int = -1       # 1=正确 0=错误 -1=未知
    reason: str = ""       # 可选：原因描述
    source: str = ""       # 数据来源

    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = time.time()

    def to_dict(self) -> dict:
        return {"device_id": self.device_id, "result": self.result,
                "reason": self.reason, "source": self.source,
                "updated_at": int(self.timestamp)}

    @classmethod
    def from_dict(cls, d: dict) -> "ResultRecord":
        return cls(
            device_id=d.get("device_id", ""),
            timestamp=d.get("updated_at", 0) or d.get("timestamp", 0),
            result=d.get("result", -1),
            reason=d.get("reason", ""),
            source=d.get("source", ""),
        )

    def to_json(self) -> str:
        return json.dumps(self.to_dict(), ensure_ascii=False)
