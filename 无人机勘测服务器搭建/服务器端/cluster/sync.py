"""V2.0 Sync Engine - county->city->province->center"""
import json, time, struct
from typing import Optional

class SyncEngine:
    def __init__(self, db, server_id="", upstream_id="", batch_size=5000, retry_max=3):
        self.db = db; self.server_id = server_id
        self.upstream_id = upstream_id; self.batch_size = batch_size
        self.retry_max = retry_max
        self.last_sync_time = 0
        self.stats = {"synced": 0, "failed": 0, "last": 0}

    def get_pending_count(self) -> int:
        try:
            row = self.db.conn.execute(
                "SELECT count(*) FROM gnss_position WHERE created_at > ?", (self.last_sync_time,)
            ).fetchone()
            return row[0] if row else 0
        except Exception: return 0

    def get_sync_batch(self) -> list:
        data = self.db.get_sync_data(self.last_sync_time, self.batch_size)
        return data

    def prepare_sync_payload(self, records: list) -> bytes:
        return json.dumps({
            "from": self.server_id, "to": self.upstream_id,
            "records": records, "ts": int(time.time())
        }, default=str).encode("utf-8")

    def process_received_sync(self, payload_json: str) -> int:
        try:
            data = json.loads(payload_json)
            records = data.get("records", [])
            if records:
                from storage.duckdb_manager import DuckDBManager
                count = self.db.insert_gnss_batch(records, batch_size=1000)
                self.stats["synced"] += count
                self.stats["last"] = int(time.time())
                return count
        except Exception: pass
        return 0

    def mark_synced(self, count: int):
        self.stats["synced"] += count
        self.stats["last"] = int(time.time())
        if count > 0:
            self.last_sync_time = self.db.get_last_sync_time(self.server_id)

    def get_statistics(self) -> dict:
        return {"server_id": self.server_id, "upstream_id": self.upstream_id,
                "pending": self.get_pending_count(),
                "synced": self.stats["synced"], "failed": self.stats["failed"],
                "last_sync": self.stats["last"]}
