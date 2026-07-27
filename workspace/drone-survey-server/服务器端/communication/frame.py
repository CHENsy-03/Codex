# -*- coding: utf-8 -*-
"""V2.0 Frame Protocol - 16-byte device_id + CRC32"""
import struct, zlib, time
from typing import Optional, Tuple
MAGIC = b'US'
VERSION = 2
HEADER_SIZE = 52
CRC_SIZE = 4
class FrameHeader:
    def __init__(self):
        self.magic = MAGIC; self.version = VERSION; self.msg_type = 0
        self.device_id = ""; self.session_id = ""; self.sequence = 0
        self.timestamp = 0; self.payload_length = 0
    def pack(self) -> bytes:
        did = self.device_id.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00')
        sid = self.session_id.encode('ascii', errors='ignore')[:16].ljust(16, b'\x00')
        return struct.pack('!2sBB16s16sIIQ', self.magic[:2], self.version, self.msg_type,
                           did, sid, self.sequence, self.payload_length, self.timestamp)
    @classmethod
    def unpack(cls, data: bytes) -> 'FrameHeader':
        if len(data) < HEADER_SIZE:
            return None
        magic, ver, msg_type, did, sid, seq, plen, ts = struct.unpack(
            '!2sBB16s16sIIQ', data[:HEADER_SIZE])
        h = cls()
        h.magic = magic; h.version = ver; h.msg_type = msg_type
        h.device_id = did.rstrip(b'\x00').decode('ascii', errors='ignore')
        h.session_id = sid.rstrip(b'\x00').decode('ascii', errors='ignore')
        h.sequence = seq; h.payload_length = plen; h.timestamp = ts
        return h
def pack_frame(header: FrameHeader, payload: bytes = b'') -> bytes:
    header.payload_length = len(payload)
    header.timestamp = int(time.time())
    frame = header.pack() + payload
    crc = zlib.crc32(frame) & 0xFFFFFFFF
    return frame + struct.pack('!I', crc)
def unpack_frame(data: bytes) -> Optional[Tuple[FrameHeader, bytes]]:
    if len(data) < HEADER_SIZE + CRC_SIZE:
        return None
    header = FrameHeader.unpack(data[:HEADER_SIZE])
    if header is None:
        return None
    body_end = HEADER_SIZE + header.payload_length
    if len(data) < body_end + CRC_SIZE:
        return None
    payload = data[HEADER_SIZE:body_end]
    crc_received = struct.unpack('!I', data[body_end:body_end + CRC_SIZE])[0]
    crc_calc = zlib.crc32(data[:body_end]) & 0xFFFFFFFF
    if crc_received != crc_calc:
        return None
    return header, payload
