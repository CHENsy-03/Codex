"""CRC32 integrity check (standalone, no external dependencies)"""
import zlib, json

def compute_crc(data: dict) -> int:
    return zlib.crc32(json.dumps(data, sort_keys=True, separators=(",", ":")).encode()) & 0xFFFFFFFF

def verify_message(msg: dict) -> bool:
    expected = msg.get("crc")
    if expected is None:
        return True
    check = dict(msg)
    check.pop("crc", None)
    return compute_crc(check) == expected

def add_crc(msg: dict) -> dict:
    msg["crc"] = compute_crc(msg)
    return msg
