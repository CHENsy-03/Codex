"""NMEA-0183 + BESTPOSA 解析器（K803_EK0407 适用）"""
import re, math, logging

logger = logging.getLogger(__name__)

def parse_nmea(sentence: str) -> dict | None:
    """自动识别 NMEA 句子类型并解析"""
    if not sentence or not sentence.startswith("$"):
        return None
    if sentence.startswith("$GPGGA") or sentence.startswith("$GNGGA"):
        return _parse_gpgga(sentence)
    if sentence.startswith("$GPGSA") or sentence.startswith("$GNGSA"):
        return _parse_gpgsa(sentence)
    if sentence.startswith("$GPGST") or sentence.startswith("$GNGST"):
        return _parse_gpgst(sentence)
    return None

def _parse_gpgga(sentence: str) -> dict | None:
    """$GPGGA 解析 -> lat, lng, alt, quality"""
    parts = sentence.split(",")
    if len(parts) < 10:
        return None
    try:
        raw_lat, raw_lng = parts[2], parts[4]
        if not raw_lat or not raw_lng:
            return None
        lat = float(raw_lat[:2]) + float(raw_lat[2:]) / 60.0
        lng = float(raw_lng[:3]) + float(raw_lng[3:]) / 60.0
        if parts[3] == "S": lat = -lat
        if parts[5] == "W": lng = -lng
        alt = float(parts[9]) if parts[9] else 0.0
        quality = int(parts[6]) if parts[6] else 0
        return {"lat": round(lat, 6), "lng": round(lng, 6),
                "alt": round(alt, 2), "quality": quality, "source": "GGA"}
    except (ValueError, IndexError):
        return None

def _parse_gpgsa(sentence: str) -> dict | None:
    """$GPGSA 解析 -> HDOP, VDOP -> 精度估值 E,N,U (cm)"""
    parts = sentence.split(",")
    if len(parts) < 18:
        return None
    try:
        hdop = float(parts[16]) if parts[16] else 0.0
        vdop = float(parts[17].split("*")[0]) if parts[17] else 0.0
        if hdop <= 0:
            return None
        h_err = hdop * 150.0
        v_err = vdop * 150.0
        e_n = round(h_err / math.sqrt(2), 2)
        return {"e": e_n, "n": e_n, "u": round(v_err, 2), "source": "GSA"}
    except (ValueError, IndexError):
        return None

def _parse_gpgst(sentence: str) -> dict | None:
    """$GPGST 解析 -> 位置标准差 (m) -> 精度 E,N,U (cm)"""
    parts = sentence.split(",")
    if len(parts) < 8:
        return None
    try:
        lat_std = float(parts[6]) if parts[6] else 2.0
        lng_std = float(parts[7].split("*")[0]) if parts[7] else 2.0
        return {"e": round(lat_std * 100, 2), "n": round(lng_std * 100, 2),
                "u": round(max(lat_std, lng_std) * 100, 2), "source": "GST"}
    except (ValueError, IndexError):
        return None

def parse_bestposa(line: str) -> dict | None:
    """#BESTPOSA 解析（NovAtel 格式）"""
    if not line.startswith("#BESTPOSA"):
        return None
    parts = line.split(",")
    if len(parts) < 19:
        return None
    try:
        lat = float(parts[11]); lng = float(parts[12]); alt = float(parts[13])
        std_lat = float(parts[16]) if parts[16] else 0.005
        std_lng = float(parts[17]) if parts[17] else 0.006
        std_alt = float(parts[18]) if parts[18] else 0.015
        pos_type = parts[10] if len(parts) > 10 else "UNKNOWN"
        return {
            "lat": round(lat, 6), "lng": round(lng, 6), "alt": round(alt, 2),
            "e": round(std_lat * 100, 2), "n": round(std_lng * 100, 2),
            "u": round(std_alt * 100, 2), "pos_type": pos_type,
            "quality": 1 if "INT" in pos_type else 0,
            "source": "BESTPOSA"
        }
    except (ValueError, IndexError):
        return None
