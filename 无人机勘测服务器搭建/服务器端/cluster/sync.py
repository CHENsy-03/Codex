# -*- coding: utf-8 -*-
"""V2.1 Sync Engine - protobuf SyncMessage replaces JSON"""
import time, struct
from typing import Optional
from message.converter import to_protobuf, from_protobuf
class SyncEngine:
    def __init__(self, db, server_id="", upstream_id="", batch_size=5000, retry_max=3):
        self.db = db; self.server_id = server_id
        self.upstream_id = upstream_id; self.batch_size = batch_size
        self.retry_max = retry_max; self.last_sync_time = 0
        self.stats = {"synced": 0, "failed": 0, "last": 0}
    def get_pending_count(self) -> int:
        try:
            row = self.db.conn.execute(
                "SELECT count(*) FROM gnss_position WHERE created_at > ?", (self.last_sync_time,)
            ).fetchone()
            return row[0] if row else 0
        except Exception: return 0
    def get_sync_batch(self) -> list:
        return self.db.get_sync_data(self.last_sync_time, self.batch_size)
    def prepare_sync_payload(self, records: list) -> bytes:
        """Serialize records to protobuf SyncMessage binary"""
        msgs = [to_protobuf(r).SerializeToString() for r in records]
        header = f"{self.server_id},{self.upstream_id},{int(time.time())}".encode()
        return struct.pack("!I", len(header)) + header + b"".join(
            struct.pack("!I", len(m)) + m for m in msgs)
    def process_received_sync(self, payload: bytes) -> int:
        """Deserialize protobuf SyncMessage and insert to DB"""
        try:
            data = payload
            header_len = struct.unpack("!I", data[:4])[0]
            header = data[4:4+header_len].decode()
            parts = header.split(","); from_srv = parts[0] if len(parts) > 0 else ""
            pos = 4 + header_len; records = []
            from protocol.proto.gnss_pb2 import GNSSPosition
            while pos + 4 <= len(data):
                msg_len = struct.unpack("!I", data[pos:pos+4])[0]
                pos += 4
                if pos + msg_len > len(data): break
                msg = GNSSPosition()
                msg.ParseFromString(data[pos:pos+msg_len])
                records.append(from_protobuf(msg)); pos += msg_len
            if records:
                count = self.db.insert_gnss_batch(records, batch_size=1000)
                self.stats["synced"] += count; self.stats["last"] = int(time.time())
                return count
        except Exception: pass
        return 0
    def mark_synced(self, count: int):
        self.stats["synced"] += count; self.stats["last"] = int(time.time())
        if count > 0: self.last_sync_time = self.db.get_last_sync_time(self.server_id)
    def get_statistics(self) -> dict:
        return {"server_id": self.server_id, "upstream_id": self.upstream_id,
                "pending": self.get_pending_count(),
                "synced": self.stats["synced"], "failed": self.stats["failed"],
                "last_sync": self.stats["last"]}
