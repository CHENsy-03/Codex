"""通信帧协议 V2.0 - Frame packing/unpacking + CRC32"""

import struct
import time
import zlib
from dataclasses import dataclass, field
from typing import Optional, Tuple

# ── Message Type Constants ──
MSG_HEARTBEAT = 0x01
MSG_GNSS      = 0x02
MSG_IMU       = 0x03
MSG_STATUS    = 0x04
MSG_FILE      = 0x05
MSG_ACK       = 0x06
MSG_NACK      = 0x07
MSG_CONFIG    = 0x08
MSG_COMMAND   = 0x09

MSG_NAMES = {
    0x01: "HEARTBEAT", 0x02: "GNSS", 0x03: "IMU",
    0x04: "STATUS", 0x05: "FILE", 0x06: "ACK",
    0x07: "NACK", 0x08: "CONFIG", 0x09: "COMMAND",
}

MAGIC = b'\xA5\x5A'
HEADER_SIZE = 44       # 2+1+1+8+16+4+4+8 = 44 bytes
CRC_SIZE = 4

# ── Frame Header ──
@dataclass
class FrameHeader:
    """44-byte fixed-size frame header"""
    device_id: str = ""
    session_id: str = ""
    msg_type: int = 0
    sequence: int = 0
    payload_length: int = 0
    magic: bytes = MAGIC
    version: int = 2
    timestamp: int = field(default_factory=lambda: int(time.time() * 1000))

    def pack(self) -> bytes:
        """Serialize header to 44 bytes"""
        did = self.device_id.encode('ascii', errors='ignore')[:8].ljust(8, b'\x00')
        sid = self.session_id.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00')
        return struct.pack('!2sBB8s16sIIQ',
            MAGIC, self.version, self.msg_type,
            did, sid,
            self.sequence, self.payload_length, self.timestamp)

    @classmethod
    def unpack(cls, data: bytes) -> Optional['FrameHeader']:
        """Deserialize 44 bytes to FrameHeader"""
        if len(data) < HEADER_SIZE:
            return None
        try:
            magic, ver, mtype, did, sid, seq, plen, ts = struct.unpack(
                '!2sBB8s16sIIQ', data[:HEADER_SIZE])
            if magic != MAGIC:
                return None
            return cls(
                device_id=did.rstrip(b'\x00').decode('ascii', errors='ignore'),
                session_id=sid.rstrip(b'\x00').decode('ascii', errors='ignore'),
                msg_type=mtype, sequence=seq, payload_length=plen,
                version=ver, timestamp=ts)
        except struct.error:
            return None


def pack_frame(header: FrameHeader, payload: bytes = b'') -> bytes:
    """Pack header + payload + CRC32 -> complete frame"""
    header.payload_length = len(payload)
    hdr_bytes = header.pack()
    data = hdr_bytes + payload
    crc = zlib.crc32(data) & 0xFFFFFFFF
    return data + struct.pack('!I', crc)


def unpack_frame(data: bytes) -> Optional[Tuple[FrameHeader, bytes]]:
    """Unpack complete frame -> (header, payload) or None if CRC fails"""
    if len(data) < HEADER_SIZE + CRC_SIZE:
        return None
    header = FrameHeader.unpack(data[:HEADER_SIZE])
    if not header:
        return None
    body_end = HEADER_SIZE + header.payload_length
    crc_end = body_end + CRC_SIZE
    if len(data) < crc_end:
        return None
    body = data[:body_end]
    payload = data[HEADER_SIZE:body_end]
    received_crc = struct.unpack('!I', data[body_end:crc_end])[0]
    expected_crc = zlib.crc32(body) & 0xFFFFFFFF
    if received_crc != expected_crc:
        return None
    return (header, payload)


def create_frame_header(device_id: str, session_id: str, msg_type: int,
                        sequence: int = 0) -> FrameHeader:
    """Factory: create a FrameHeader with current timestamp"""
    return FrameHeader(
        device_id=device_id, session_id=session_id,
        msg_type=msg_type, sequence=sequence)


def make_ack_frame(device_id: str, session_id: str, ack_seq: int,
                   status: str = "ok") -> bytes:
    """Quick build an ACK frame"""
    payload = f'{{"ack_seq":{ack_seq},"status":"{status}"}}'.encode('ascii')
    hdr = create_frame_header(device_id, session_id, MSG_ACK, ack_seq)
    return pack_frame(hdr, payload)


def make_nack_frame(device_id: str, session_id: str, nack_seq: int,
                    reason: str = "error") -> bytes:
    """Quick build a NACK frame"""
    payload = f'{{"nack_seq":{nack_seq},"reason":"{reason}"}}'.encode('ascii')
    hdr = create_frame_header(device_id, session_id, MSG_NACK, nack_seq)
    return pack_frame(hdr, payload)


def make_heartbeat_frame(device_id: str, session_id: str, sequence: int = 0) -> bytes:
    """Quick build a heartbeat frame"""
    hdr = create_frame_header(device_id, session_id, MSG_HEARTBEAT, sequence)
    return pack_frame(hdr, b'')
