"""DuckDB 数据库管理器 - V2.0 存储层
   支持: memory_limit, temp_directory, 大文件直接扫描
"""

import os
import time
import duckdb
from typing import List, Dict, Optional

# V2.0 表结构
DDL_GNSS_POSITION = """
CREATE TABLE IF NOT EXISTS gnss_position (
    id          BIGINT PRIMARY KEY DEFAULT nextval('gnss_seq'),
    device_id   VARCHAR NOT NULL,
    msg_type    VARCHAR DEFAULT '',
    latitude    DOUBLE,
    longitude   DOUBLE,
    height      DOUBLE,
    solution_type INTEGER DEFAULT 0,
    diff_age    DOUBLE DEFAULT 0,
    station_id  VARCHAR DEFAULT '',
    source_channel VARCHAR DEFAULT '',
    raw_data    BLOB,
    gnss_time   BIGINT DEFAULT 0,
    e_accuracy  DOUBLE DEFAULT 0,
    n_accuracy  DOUBLE DEFAULT 0,
    u_accuracy  DOUBLE DEFAULT 0,
    server_id   VARCHAR DEFAULT '',
    created_at  BIGINT DEFAULT 0
)
"""

DDL_DEVICE_SESSION = """
CREATE TABLE IF NOT EXISTS device_session (
    device_id   VARCHAR NOT NULL,
    session_id  VARCHAR NOT NULL,
    channel     VARCHAR DEFAULT '',
    last_seq    INTEGER DEFAULT 0,
    status      VARCHAR DEFAULT 'offline',
    heartbeat_time BIGINT DEFAULT 0,
    created_at  BIGINT DEFAULT 0,
    PRIMARY KEY (device_id, session_id)
)
"""

DDL_OFFLINE_QUEUE = """
CREATE TABLE IF NOT EXISTS offline_message (
    id          BIGINT PRIMARY KEY DEFAULT nextval('offline_seq'),
    device_id   VARCHAR NOT NULL,
    sequence    INTEGER NOT NULL,
    payload     BLOB,
    status      VARCHAR DEFAULT 'pending',
    retry_count INTEGER DEFAULT 0,
    created_at  BIGINT DEFAULT 0
)
"""

DDL_SERVER_REGISTRY = """
CREATE TABLE IF NOT EXISTS server_registry (
    server_id   VARCHAR PRIMARY KEY,
    server_name VARCHAR DEFAULT '',
    level       VARCHAR DEFAULT '',
    host        VARCHAR DEFAULT '',
    port        INTEGER DEFAULT 0,
    status      VARCHAR DEFAULT 'unknown',
    last_seen   BIGINT DEFAULT 0
)
"""

DDL_SYNC_LOG = """
CREATE TABLE IF NOT EXISTS sync_log (
    id          BIGINT PRIMARY KEY DEFAULT nextval('sync_seq'),
    from_server VARCHAR NOT NULL,
    to_server   VARCHAR NOT NULL,
    sync_type   VARCHAR DEFAULT 'gnss',
    records     INTEGER DEFAULT 0,
    status      VARCHAR DEFAULT 'ok',
    created_at  BIGINT DEFAULT 0
)
"""

ALL_DDLS = [DDL_GNSS_POSITION, DDL_DEVICE_SESSION, DDL_OFFLINE_QUEUE,
            DDL_SERVER_REGISTRY, DDL_SYNC_LOG]

ALL_SEQUENCES = ["gnss_seq", "offline_seq", "sync_seq"]


class DuckDBManager:
    """DuckDB 数据库管理器"""

    def __init__(self, db_path: str = "data/gnss_data.duckdb",
                 memory_limit: str = "4GB",
                 temp_directory: str = "data/temp"):
        self.db_path = db_path
        self.memory_limit = memory_limit
        self.temp_directory = temp_directory
        self.conn: Optional[duckdb.DuckDBPyConnection] = None

    def connect(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        os.makedirs(self.temp_directory, exist_ok=True)

        self.conn = duckdb.connect(self.db_path)

        # 内存限制 (DuckDB >= 0.8.0)
        try:
            self.conn.execute(f"SET memory_limit='{self.memory_limit}'")
        except Exception:
            pass

        # 临时目录
        try:
            self.conn.execute(f"SET temp_directory='{self.temp_directory}'")
        except Exception:
            pass

        # 创建序列表
        for seq in ALL_SEQUENCES:
            try:
                self.conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq} START 1")
            except Exception:
                pass

        # 创建表
        for ddl in ALL_DDLS:
            self.conn.execute(ddl)

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    # ── GNSS 数据操作 ──

    def insert_gnss(self, data) -> int:
        """插入 GNSS 数据, 返回行数"""
        d = data.to_dict() if hasattr(data, 'to_dict') else data
        sql = """INSERT INTO gnss_position 
            (device_id,msg_type,latitude,longitude,height,
             solution_type,diff_age,station_id,source_channel,
             raw_data,gnss_time,e_accuracy,n_accuracy,u_accuracy,
             server_id,created_at)
            VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)"""
        self.conn.execute(sql, (
            d.get("device_id",""), d.get("msg_type",""),
            d.get("latitude",0), d.get("longitude",0), d.get("height",0),
            d.get("solution_type",0), d.get("diff_age",0),
            d.get("station_id",""), d.get("source_channel",""),
            d.get("raw_data",b""), d.get("gnss_time",0),
            d.get("e_accuracy",0), d.get("n_accuracy",0), d.get("u_accuracy",0),
            d.get("server_id",""), d.get("created_at",0),
        ))
        return 1

    def insert_gnss_batch(self, data_list) -> int:
        """批量插入"""
        count = 0
        for item in data_list:
            self.insert_gnss(item)
            count += 1
        return count

    def query_gnss(self, limit: int = 100, device_id: str = None) -> list:
        sql = "SELECT * FROM gnss_position WHERE 1=1"
        params = []
        if device_id:
            sql += " AND device_id = ?"
            params.append(device_id)
        sql += " ORDER BY created_at DESC LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        cols = [d[0] for d in self.conn.description]
        return [dict(zip(cols, r)) for r in rows]

    def count_gnss(self) -> int:
        return self.conn.execute("SELECT count(*) FROM gnss_position").fetchone()[0]

    # ── 大文件直接扫描 ──

    def scan_csv_direct(self, filepath: str) -> int:
        """DuckDB 直接扫描 CSV, 避免 Pandas 中间层"""
        import time
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        count_before = self.count_gnss()
        self.conn.execute(f"""
            INSERT INTO gnss_position (device_id,msg_type,latitude,longitude,height,
                solution_type,e_accuracy,n_accuracy,u_accuracy,server_id,created_at)
            SELECT device_id, 'GPGGA', latitude, longitude, height,
                solution_type, e_accuracy, n_accuracy, u_accuracy, server_id, {int(time.time())}
            FROM read_csv_auto('{filepath}', header=true)
        """)
        return self.count_gnss() - count_before

    def scan_parquet_direct(self, filepath: str) -> int:
        """DuckDB 直接扫描 Parquet"""
        import time
        if not os.path.exists(filepath):
            raise FileNotFoundError(f"文件不存在: {filepath}")
        count_before = self.count_gnss()
        self.conn.execute(f"""
            INSERT INTO gnss_position SELECT * FROM '{filepath}'
        """)
        return self.count_gnss() - count_before

    # ── 会话管理 ──

    def upsert_session(self, device_id: str, session_id: str, channel: str = "",
                       status: str = "online"):
        self.conn.execute("""
            INSERT OR REPLACE INTO device_session 
            (device_id,session_id,channel,status,heartbeat_time,created_at)
            VALUES (?,?,?,?,?,?)
        """, (device_id, session_id, channel, status, int(time.time()), int(time.time())))

    def get_session(self, device_id: str, session_id: str) -> dict or None:
        rows = self.conn.execute(
            "SELECT * FROM device_session WHERE device_id=? AND session_id=?",
            (device_id, session_id)
        ).fetchall()
        if not rows:
            return None
        cols = [d[0] for d in self.conn.description]
        return dict(zip(cols, rows[0]))

    # ── 离线队列 ──

    def enqueue_offline(self, device_id: str, seq: int, payload: bytes) -> int:
        self.conn.execute(
            "INSERT INTO offline_message (device_id,sequence,payload,status,created_at) VALUES (?,?,?,?,?)",
            (device_id, seq, payload, "pending", int(time.time()))
        )
        return 1

    def get_pending_offline(self, device_id: str = None, limit: int = 100) -> list:
        sql = "SELECT * FROM offline_message WHERE status='pending'"
        params = []
        if device_id:
            sql += " AND device_id=?"
            params.append(device_id)
        sql += " ORDER BY sequence LIMIT ?"
        params.append(limit)
        rows = self.conn.execute(sql, params).fetchall()
        cols = [d[0] for d in self.conn.description]
        return [dict(zip(cols, r)) for r in rows]

    def mark_offline_sent(self, msg_id: int):
        self.conn.execute(
            "UPDATE offline_message SET status='sent' WHERE id=?", (msg_id,))

    # ── 服务器注册 ──

    def register_server(self, server_id: str, name: str = "", level: str = "",
                        host: str = "", port: int = 0):
        self.conn.execute("""
            INSERT OR REPLACE INTO server_registry
            (server_id,server_name,level,host,port,status,last_seen)
            VALUES (?,?,?,?,?,?,?)
        """, (server_id, name, level, host, port, "online", int(time.time())))

    def get_servers(self, level: str = None) -> list:
        sql = "SELECT * FROM server_registry"
        params = []
        if level:
            sql += " WHERE level=?"
            params.append(level)
        rows = self.conn.execute(sql, params).fetchall()
        cols = [d[0] for d in self.conn.description]
        return [dict(zip(cols, r)) for r in rows]

    # ── 同步日志 ──

    def log_sync(self, from_server: str, to_server: str, records: int,
                 status: str = "ok"):
        self.conn.execute(
            "INSERT INTO sync_log (from_server,to_server,sync_type,records,status,created_at) VALUES (?,?,?,?,?,?)",
            (from_server, to_server, "gnss", records, status, int(time.time())))

    # ── 实用方法 ──

    def get_table_sizes(self) -> dict:
        tables = ["gnss_position", "device_session", "offline_message",
                  "server_registry", "sync_log"]
        sizes = {}
        for t in tables:
            try:
                cnt = self.conn.execute(f"SELECT count(*) FROM {t}").fetchone()[0]
                sizes[t] = cnt
            except Exception:
                sizes[t] = 0
        return sizes

    def execute(self, sql: str, params=None):
        if params:
            return self.conn.execute(sql, params)
        return self.conn.execute(sql)

    # ── Phase 3: Batch operations ──

    def insert_gnss_batch(self, data_list, batch_size=500) -> int:
        """批量插入 (transaction-wrapped, 比逐行快 10x+)"""
        count = 0
        for i in range(0, len(data_list), batch_size):
            batch = data_list[i:i+batch_size]
            self.conn.execute("BEGIN TRANSACTION")
            for data in batch:
                try:
                    self.insert_gnss(data)
                    count += 1
                except Exception:
                    pass
            self.conn.execute("COMMIT")
        return count

    def create_indexes(self):
        """创建查询性能索引"""
        indexes = [
            "CREATE INDEX IF NOT EXISTS idx_gnss_device ON gnss_position(device_id)",
            "CREATE INDEX IF NOT EXISTS idx_gnss_time ON gnss_position(created_at)",
            "CREATE INDEX IF NOT EXISTS idx_gnss_server ON gnss_position(server_id)",
            "CREATE UNIQUE INDEX IF NOT EXISTS idx_session_unique ON device_session(device_id, session_id)",
        ]
        for sql in indexes:
            try: self.conn.execute(sql)
            except Exception: pass

    def get_sync_data(self, last_sync_time: int = 0, limit: int = 5000) -> list:
        """获取待同步数据 (created_at > last_sync_time)"""
        rows = self.conn.execute(
            "SELECT * FROM gnss_position WHERE created_at > ? ORDER BY created_at LIMIT ?",
            (last_sync_time, limit)
        ).fetchall()
        cols = [d[0] for d in self.conn.description]
        return [dict(zip(cols, r)) for r in rows]

    def get_last_sync_time(self, from_server: str = "") -> int:
        """获取上次同步时间"""
        try:
            row = self.conn.execute(
                "SELECT max(created_at) FROM sync_log WHERE from_server=?",
                (from_server,)
            ).fetchone()
            return row[0] if row and row[0] else 0
        except Exception:
            return 0

    def vacuum(self):
        """数据库维护 (DuckDB: CHECKPOINT 清理 WAL)"""
        try:
            self.conn.execute("CHECKPOINT")
        except Exception:
            pass

    def export_csv(self, table: str = "gnss_position", path: str = "") -> str:
        """导出表到 CSV"""
        import time
        if not path:
            path = f"data/export_{table}_{int(time.time())}.csv"
        self.conn.execute(f"COPY {table} TO '{path}' (HEADER, DELIMITER ',')")
        return path

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, *args):
        self.disconnect()
