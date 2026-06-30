"""CM510 设备协议解析插件

CM510是一款无线数据传输设备，支持：
- GPS定位数据上报
- 设备状态数据上报
- 心跳数据上报

报文格式：
$CM510,<device_id>,<lat>,<lng>,<speed>,<heading>,<altitude>,<satellites>,<signal>,<timestamp>*<CRC>
"""
import re, time, logging

logger = logging.getLogger(__name__)

# 预编译正则
_CM510_PATTERN = re.compile(r"^\$CM510,(\w+),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*),([^,]*)\*(\w{2})$")
_NMEA_LAT = re.compile(r"^(\d{2})(\d{2}\.\d+)$")
_NMEA_LNG = re.compile(r"^(\d{3})(\d{2}\.\d+)$")


class CM510Parser:
    """CM510 设备协议解析器"""

    @staticmethod
    def can_parse(data) -> bool:
        if isinstance(data, bytes):
            try:
                data = data.decode("utf-8", errors="ignore")
            except Exception:
                return False
        return isinstance(data, str) and data.startswith("$CM510")

    @staticmethod
    def parse(data) -> dict or None:
        """解析 CM510 报文 -> 统一位置字典"""
        if isinstance(data, bytes):
            data = data.decode("utf-8", errors="ignore")
        data = data.strip()
        
        m = _CM510_PATTERN.match(data)
        if not m:
            return None
        
        try:
            device_id = m.group(1)
            lat = CM510Parser._parse_nmea_coord(m.group(2), "N")
            lng = CM510Parser._parse_nmea_coord(m.group(3), "E")
            speed = float(m.group(4)) if m.group(4) else 0.0
            heading = float(m.group(5)) if m.group(5) else 0.0
            altitude = float(m.group(6)) if m.group(6) else 0.0
            satellites = int(m.group(7)) if m.group(7) else 0
            signal = int(m.group(8)) if m.group(8) else 0
            timestamp = int(m.group(9)) if m.group(9) else int(time.time())
            
            return {
                "device_id": device_id,
                "lat": round(lat, 6),
                "lng": round(lng, 6),
                "alt": round(altitude, 2),
                "speed": round(speed, 2),
                "heading": round(heading, 2),
                "satellites": satellites,
                "signal_level": signal,
                "timestamp": timestamp,
                "pos_type": "SINGLE" if satellites < 4 else "NARROW_FLOAT" if satellites < 8 else "NARROW_INT",
                "source": "CM510",
            }
        except (ValueError, IndexError) as e:
            logger.warning("CM510 parse error: %s", e)
            return None

    @staticmethod
    def _parse_nmea_coord(raw: str, hemi: str) -> float:
        """NMEA 坐标格式 -> 十进制"""
        if not raw:
            return 0.0
        if "." not in raw:
            return float(raw)
        try:
            if len(raw.split(".")[0]) == 5:  # DDDMM.MMMM (经度)
                deg = int(raw[:3])
                minute = float(raw[3:])
            else:  # DDMM.MMMM (纬度)
                deg = int(raw[:2])
                minute = float(raw[2:])
            result = deg + minute / 60.0
            return -result if hemi in ("S", "W") else result
        except (ValueError, IndexError):
            return 0.0


# 注册到自动检测链
_PARSER_INSTANCE = None
def get_default():
    global _PARSER_INSTANCE
    if _PARSER_INSTANCE is None:
        _PARSER_INSTANCE = CM510Parser()
    return _PARSER_INSTANCE
