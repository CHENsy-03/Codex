"""协议解析基类 - V2.0 统一 GNSS 数据对象"""

import time
from dataclasses import dataclass, field
from typing import Optional, Dict


@dataclass
class GNSSData:
    """V2.0 统一定位数据对象"""
    device_id: str = ""
    msg_type: str = ""                  # GPGGA / BESTPOS
    latitude: float = 0.0
    longitude: float = 0.0
    height: float = 0.0
    solution_type: int = 0              # 0=none 1=fix 2=float 4=rtk_fixed 5=rtk_float
    diff_age: float = 0.0
    station_id: str = ""
    source_channel: str = ""            # serial/tcp/mqtt
    raw_data: bytes = field(default_factory=bytes)
    gnss_time: int = 0                  # UNIX timestamp from GNSS
    e_accuracy: float = 0.0             # 东向精度(cm)
    n_accuracy: float = 0.0             # 北向精度(cm)
    u_accuracy: float = 0.0             # 高度精度(cm)
    server_id: str = ""
    created_at: int = field(default_factory=lambda: int(time.time()))

    def to_dict(self) -> Dict:
        return {
            "device_id": self.device_id, "msg_type": self.msg_type,
            "latitude": self.latitude, "longitude": self.longitude,
            "height": self.height, "solution_type": self.solution_type,
            "diff_age": self.diff_age, "station_id": self.station_id,
            "source_channel": self.source_channel,
            "gnss_time": self.gnss_time,
            "e_accuracy": self.e_accuracy,
            "n_accuracy": self.n_accuracy,
            "u_accuracy": self.u_accuracy,
            "server_id": self.server_id,
            "created_at": self.created_at,
        }


class BaseParser:
    """协议解析器基类"""

    @staticmethod
    def can_handle(raw: bytes) -> bool:
        raise NotImplementedError

    @staticmethod
    def parse(raw: bytes) -> Optional[GNSSData]:
        raise NotImplementedError


class ProtocolParser:
    """协议解析调度器 - 自动选择解析器"""

    def __init__(self, server_id: str = ""):
        self.server_id = server_id
        self._parsers = []

    def register(self, parser_class):
        self._parsers.append(parser_class)

    def parse(self, raw: bytes) -> Optional[GNSSData]:
        for parser_class in self._parsers:
            try:
                if parser_class.can_handle(raw):
                    result = parser_class.parse(raw)
                    if result:
                        result.server_id = self.server_id
                        return result
            except Exception:
                continue
        return None
