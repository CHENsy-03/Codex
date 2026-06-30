"""V4-Local Plugin SDK Schema 标准"""
from dataclasses import dataclass, field, asdict
from typing import Optional, Any

@dataclass
class PluginInput:
    topic: str = ""
    data: dict = field(default_factory=dict)
    source: str = ""
    timestamp: float = 0.0

@dataclass
class PluginOutput:
    status: str = "success"
    result: dict = field(default_factory=dict)
    error: str = ""
    processing_ms: float = 0.0

@dataclass
class EventSchema:
    id: str = ""
    topic: str = ""
    source: str = ""
    payload: dict = field(default_factory=dict)
    timestamp: float = 0.0

    def to_dict(self) -> dict:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict) -> "EventSchema":
        return cls(**{k: v for k, v in d.items() if k in cls.__dataclass_fields__})
