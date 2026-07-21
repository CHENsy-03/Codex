# -*- coding: utf-8 -*-
"""V2.0 Extended Message Types - IMU, File, Config structs."""
import json, time, struct
from dataclasses import dataclass, field
from typing import Optional, Any
@dataclass
class IMUMessage:
    device_id: str = ''
    accel_x: float = 0.0; accel_y: float = 0.0; accel_z: float = 0.0
    gyro_x: float = 0.0; gyro_y: float = 0.0; gyro_z: float = 0.0
    mag_x: float = 0.0; mag_y: float = 0.0; mag_z: float = 0.0
    temperature: float = 0.0
    timestamp: int = field(default_factory=lambda: int(time.time()))
    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
    def pack(self):
        return json.dumps(self.to_dict()).encode('utf-8')
    @classmethod
    def unpack(cls, data):
        d = json.loads(data.decode('utf-8'))
        return cls(**{k: d.get(k, 0) for k in cls.__dataclass_fields__})
@dataclass
class FileMessage:
    device_id: str = ''
    file_name: str = ''; file_type: str = ''; file_size: int = 0
    chunk_index: int = 0; total_chunks: int = 1; checksum: str = ''
    payload: bytes = b''
    timestamp: int = field(default_factory=lambda: int(time.time()))
    def to_dict(self):
        d = {k: getattr(self, k) for k in self.__dataclass_fields__ if k != 'payload'}
        d['payload_size'] = len(self.payload)
        return d
    def pack(self):
        meta = json.dumps(self.to_dict()).encode('utf-8')
        return struct.pack('!I', len(meta)) + meta + self.payload
    @classmethod
    def unpack(cls, data):
        if len(data) < 4:
            return None
        meta_len = struct.unpack('!I', data[:4])[0]
        meta = json.loads(data[4:4+meta_len].decode('utf-8'))
        payload = data[4+meta_len:]
        return cls(device_id=meta.get('device_id',''), file_name=meta.get('file_name',''),
                   file_type=meta.get('file_type',''), file_size=meta.get('file_size',0),
                   chunk_index=meta.get('chunk_index',0), total_chunks=meta.get('total_chunks',1),
                   checksum=meta.get('checksum',''), payload=payload,
                   timestamp=meta.get('timestamp',0))
@dataclass
class ConfigMessage:
    device_id: str = ''
    config_key: str = ''; config_value: Any = None
    action: str = 'set'; request_id: str = ''
    timestamp: int = field(default_factory=lambda: int(time.time()))
    def to_dict(self):
        return {k: getattr(self, k) for k in self.__dataclass_fields__}
    def pack(self):
        return json.dumps(self.to_dict(), default=str).encode('utf-8')
    @classmethod
    def unpack(cls, data):
        d = json.loads(data.decode('utf-8'))
        return cls(**{k: d.get(k, '' if k in ('config_key','action','request_id') else None)
                       for k in cls.__dataclass_fields__})
