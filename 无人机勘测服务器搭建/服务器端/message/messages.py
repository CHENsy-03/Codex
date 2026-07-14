# -*- coding: utf-8 -*-
"""V2.0 Message Types - 消息枚举、工厂、序列化

消息类型映射 (对应 FrameHeader.msg_type):
  0x0001  Heartbeat     心跳
  0x0002  GNSS          定位数据
  0x0003  IMU           惯性测量
  0x0004  Status        设备状态
  0x0005  File          文件传输
  0x0006  ACK           确认
  0x0007  NACK          否认
  0x0008  Config        配置
  0x0009  Command       指令
"""
import json
import time
from enum import IntEnum
from typing import Optional, Dict, Any
from dataclasses import dataclass, field


class MessageType(IntEnum):
    HEARTBEAT = 0x0001
    GNSS = 0x0002
    IMU = 0x0003
    STATUS = 0x0004
    FILE = 0x0005
    ACK = 0x0006
    NACK = 0x0007
    CONFIG = 0x0008
    COMMAND = 0x0009

    @classmethod
    def from_code(cls, code: int) -> "MessageType":
        try:
            return cls(code)
        except ValueError:
            return None

    @classmethod
    def name_of(cls, code: int) -> str:
        mt = cls.from_code(code)
        return mt.name if mt else f"UNKNOWN(0x{code:04X})"


# ── 消息数据结构 ──

@dataclass
class HeartbeatMessage:
    device_id: str = ""
    status: int = 0
    battery: int = 0
    temperature: float = 0.0
    uptime_seconds: int = 0
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id, "status": self.status,
            "battery": self.battery, "temperature": self.temperature,
            "uptime_seconds": self.uptime_seconds, "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "HeartbeatMessage":
        return cls(**{k: d.get(k, getattr(cls, k).default)
                       for k in ["device_id","status","battery",
                                 "temperature","uptime_seconds","timestamp"]})

    def pack(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def unpack(cls, data: bytes) -> "HeartbeatMessage":
        return cls.from_dict(json.loads(data.decode("utf-8")))


@dataclass
class GNSSMessage:
    device_id: str = ""
    msg_type: str = "GPGGA"
    latitude: float = 0.0
    longitude: float = 0.0
    height: float = 0.0
    solution_type: int = 0
    e_accuracy: float = 0.0
    n_accuracy: float = 0.0
    u_accuracy: float = 0.0
    diff_age: float = 0.0
    station_id: str = ""
    gnss_time: int = 0
    raw_data: bytes = b""
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id, "msg_type": self.msg_type,
            "latitude": self.latitude, "longitude": self.longitude,
            "height": self.height, "solution_type": self.solution_type,
            "e_accuracy": self.e_accuracy, "n_accuracy": self.n_accuracy,
            "u_accuracy": self.u_accuracy, "diff_age": self.diff_age,
            "station_id": self.station_id, "gnss_time": self.gnss_time,
            "timestamp": self.timestamp,
        }

    @classmethod
    def from_dict(cls, d: dict) -> "GNSSMessage":
        return cls(**{k: d.get(k, 0 if k != "raw_data" else b"")
                       for k in cls.__dataclass_fields__ if k != "raw_data"})

    def pack(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def unpack(cls, data: bytes) -> "GNSSMessage":
        return cls.from_dict(json.loads(data.decode("utf-8")))


@dataclass
class StatusMessage:
    device_id: str = ""
    status_code: int = 0
    message: str = ""
    cpu_percent: float = 0.0
    memory_percent: float = 0.0
    storage_percent: float = 0.0
    error_count: int = 0
    temperature: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict:
        return {k: getattr(self, k) for k in self.__dataclass_fields__}

    @classmethod
    def from_dict(cls, d: dict) -> "StatusMessage":
        return cls(**{k: d.get(k, 0 if k != "message" else "")
                       for k in cls.__dataclass_fields__})

    def pack(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def unpack(cls, data: bytes) -> "StatusMessage":
        return cls.from_dict(json.loads(data.decode("utf-8")))


@dataclass
class CommandMessage:
    device_id: str = ""
    command: str = ""
    params: Dict[str, Any] = field(default_factory=dict)
    request_id: str = ""
    timestamp: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> dict:
        return {
            "device_id": self.device_id, "command": self.command,
            "params": self.params, "request_id": self.request_id,
            "timestamp": self.timestamp,
        }

    def pack(self) -> bytes:
        return json.dumps(self.to_dict()).encode("utf-8")

    @classmethod
    def unpack(cls, data: bytes) -> "CommandMessage":
        d = json.loads(data.decode("utf-8"))
        return cls(device_id=d.get("device_id",""), command=d.get("command",""),
                   params=d.get("params",{}), request_id=d.get("request_id",""),
                   timestamp=d.get("timestamp",0))


# ── 消息工厂 ──

MESSAGE_CLASS_MAP = {
    MessageType.HEARTBEAT: HeartbeatMessage,
    MessageType.GNSS: GNSSMessage,
    MessageType.STATUS: StatusMessage,
    MessageType.COMMAND: CommandMessage,
}


class MessageFactory:
    """消息工厂：根据类型码创建/序列化消息"""

    @staticmethod
    def create(msg_type: int, **kwargs) -> Optional[Any]:
        """创建消息对象"""
        mt = MessageType.from_code(msg_type)
        cls = MESSAGE_CLASS_MAP.get(mt)
        if cls:
            return cls(**kwargs)
        return None

    @staticmethod
    def pack(msg_type: int, data: Any) -> Optional[bytes]:
        """序列化消息"""
        mt = MessageType.from_code(msg_type)
        if mt in MESSAGE_CLASS_MAP and hasattr(MESSAGE_CLASS_MAP[mt], 'pack'):
            return data.pack()
        if isinstance(data, dict):
            return json.dumps(data).encode("utf-8")
        return None

    @staticmethod
    def unpack(msg_type: int, payload: bytes) -> Optional[Any]:
        """反序列化消息"""
        mt = MessageType.from_code(msg_type)
        cls = MESSAGE_CLASS_MAP.get(mt)
        if cls and hasattr(cls, 'unpack'):
            return cls.unpack(payload)
        try:
            data = json.loads(payload.decode("utf-8"))
            return data
        except Exception:
            return None

    @staticmethod
    def get_type_name(msg_type: int) -> str:
        return MessageType.name_of(msg_type)

    @staticmethod
    def all_types() -> list:
        return [{"code": mt.value, "name": mt.name,
                 "hex": f"0x{mt.value:04X}"}
                for mt in MessageType]
