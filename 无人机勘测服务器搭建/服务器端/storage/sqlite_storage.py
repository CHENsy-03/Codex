"""V4 SQLite 存储层 — 与 DuckDB 并存，用于实时日志和轻量查询"""
import sqlite3, os, time, threading, json

DB_DIR = os.path.join(os.path.dirname(os.path.dirname(os.path.abspath(__file__))), "databases")
DB_PATH = os.path.join(DB_DIR, "survey_realtime.db")

class SQLiteStorage:
    def __init__(self, db_path=DB_PATH):
        os.makedirs(os.path.dirname(db_path), exist_ok=True)
        self._conn = sqlite3.connect(db_path, check_same_thread=False)
        self._lock = threading.Lock()
        self._init_db()

    def _init_db(self):
        self._conn.executescript("""
            CREATE TABLE IF NOT EXISTS raw_packets (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT, raw_data TEXT, packet_type TEXT,
                parse_status TEXT DEFAULT 'pending', created_at REAL
            );
            CREATE TABLE IF NOT EXISTS gps_log (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                device_id TEXT, latitude REAL, longitude REAL,
                altitude REAL, speed REAL, heading REAL,
                satellites INTEGER, fix_type TEXT, created_at REAL
            );
            CREATE INDEX IF NOT EXISTS idx_raw_time ON raw_packets(created_at);
            CREATE INDEX IF NOT EXISTS idx_gps_device ON gps_log(device_id);
        """)
        self._conn.commit()

    def insert_raw(self, device_id, raw_data, packet_type="unknown", status="pending"):
        with self._lock:
            self._conn.execute("INSERT INTO raw_packets(device_id,raw_data,packet_type,parse_status,created_at) VALUES(?,?,?,?,?)",
                               (device_id, raw_data, packet_type, status, time.time()))
            self._conn.commit()

    def insert_gps(self, device_id, lat, lng, alt=0, speed=0, heading=0, satellites=0, fix_type="none"):
        with self._lock:
            self._conn.execute("INSERT INTO gps_log(device_id,latitude,longitude,altitude,speed,heading,satellites,fix_type,created_at) VALUES(?,?,?,?,?,?,?,?,?)",
                               (device_id, lat, lng, alt, speed, heading, satellites, fix_type, time.time()))
            self._conn.commit()

    def query_gps(self, device_id=None, limit=100):
        with self._lock:
            if device_id:
                cur = self._conn.execute("SELECT * FROM gps_log WHERE device_id=? ORDER BY id DESC LIMIT ?", (device_id, limit))
            else:
                cur = self._conn.execute("SELECT * FROM gps_log ORDER BY id DESC LIMIT ?", (limit,))
            return [dict(zip([d[0] for d in cur.description], r)) for r in cur.fetchall()]

    def stats(self):
        with self._lock:
            raw = self._conn.execute("SELECT COUNT(*) FROM raw_packets").fetchone()[0]
            gps = self._conn.execute("SELECT COUNT(*) FROM gps_log").fetchone()[0]
            return {"raw_packets": raw, "gps_logs": gps}

# 全局实例
_default = None
def get_default():
    global _default
    if _default is None: _default = SQLiteStorage()
    return _default
