"""GPGGA 和 BESTPOS 协议解析器"""

import re
from typing import Optional
from .base import BaseParser, GNSSData


class GPGGAParser(BaseParser):
    """$GPGGA/$GNGGA ASCII 协议解析"""

    @staticmethod
    def can_handle(raw: bytes) -> bool:
        try:
            return raw.startswith(b"$GPGGA") or raw.startswith(b"$GNGGA")
        except Exception:
            return False

    @staticmethod
    def parse(raw: bytes) -> Optional[GNSSData]:
        try:
            pool = _get_data_pool(32)
            line = raw.decode("ascii", errors="ignore").strip()
            parts = line.split(",")
            if len(parts) < 10 or not parts[2] or not parts[4]:
                return None
            if parts[6] in ("", "0"):
                return None

            lat_raw = parts[2]
            lat = int(lat_raw[:2]) + float(lat_raw[2:]) / 60.0
            if parts[3] == "S":
                lat = -lat

            lng_raw = parts[4]
            lng = int(lng_raw[:3]) + float(lng_raw[3:]) / 60.0
            if parts[5] == "W":
                lng = -lng

            alt = float(parts[9]) if parts[9] else 0.0
            quality = int(parts[6]) if parts[6] else 0
            hdop = float(parts[8]) if len(parts) > 8 and parts[8] else 5.0

            pool = _get_data_pool(32)
            return GNSSData(
                msg_type="GPGGA",
                latitude=round(lat, 8),
                longitude=round(lng, 8),
                height=round(alt, 4),
                solution_type=quality,
                e_accuracy=round(hdop * 150, 2),
                n_accuracy=round(hdop * 150, 2),
                u_accuracy=round(hdop * 150 * 2, 2),
                raw_data=raw,
                gnss_time=0,
            )
        except (ValueError, IndexError):
            return None


class BESTPOSParser(BaseParser):
    """#BESTPOSA NovAtel 二进制协议解析"""

    _LINE_PATTERN = re.compile(rb"^#[A-Z]+,COM\d+,\d+,[\d.]+,\w+,\d+,[\d.]+,"
                               rb"[\dA-Fa-f]+,\w+,\w+;[\w_]+,[\w_]+,[\d.]+,[\d.]+,[\d.]+,")

    @staticmethod
    def can_handle(raw: bytes) -> bool:
        try:
            return raw.startswith(b"#BESTPOSA")
        except Exception:
            return False

    @staticmethod
    def parse(raw: bytes) -> Optional[GNSSData]:
        try:
            pool = _get_data_pool(32)
            line = raw.decode("ascii", errors="ignore").strip()
            if not line.startswith("#BESTPOSA"):
                return None
            parts = line.split(",")
            if len(parts) < 20:
                return None

            sol_stat = parts[10] if len(parts) > 10 else ""
            lat = float(parts[11]) if parts[11] else 0.0
            lng = float(parts[12]) if parts[12] else 0.0
            alt = float(parts[13]) if parts[13] else 0.0

            sol_map = {"SOL_COMPUTED": 1, "NARROW_INT": 4, "NARROW_FLOAT": 5}
            sol_type = sol_map.get(sol_stat.split(";")[-1] if ";" in sol_stat else sol_stat, 0)

            e_acc = float(parts[17]) if len(parts) > 17 and parts[17] else 0.0
            n_acc = float(parts[18]) if len(parts) > 18 and parts[18] else 0.0
            u_acc = float(parts[19]) if len(parts) > 19 and parts[19] else 0.0

            pool = _get_data_pool(32)
            return GNSSData(
                msg_type="BESTPOS",
                latitude=lat, longitude=lng, height=alt,
                solution_type=sol_type,
                e_accuracy=e_acc * 100, n_accuracy=n_acc * 100, u_accuracy=u_acc * 100,
                raw_data=raw, gnss_time=0,
            )
        except (ValueError, IndexError):
            return None


class ProtocolDispatcher:
    """协议调度器：自动选择解析器"""

    def __init__(self, server_id: str = ""):
        self.server_id = server_id
        self._parsers = [GPGGAParser, BESTPOSParser]

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
from protocol.base import get_global_pool as _get_data_pool
