# -*- coding: utf-8 -*-
"""
5.docx §9 总部数据库管理器 (4表结构)
"""
import duckdb, logging, os, json
from typing import Dict, List
from db_config import (
    MAIN_DB_PATH, ALL_CREATES,
    TABLE_DEVICE_DATA, TABLE_GPS_DATA, TABLE_RESULT_DATA, TABLE_EVENT_LOG,
    PARQUET_TEMP_DIR, PARTITION_BY, REGION_CONFIG,
)
from db_base import DatabaseBase

logger = logging.getLogger(__name__)

class MainDatabase(DatabaseBase):
    def __init__(self):
        super().__init__()
        self.db_path = MAIN_DB_PATH

    def connect(self):
        self.conn = duckdb.connect(self.db_path)
        for ddl in ALL_CREATES:
            self.conn.execute(ddl)
        for seq in ['gps_data_seq','result_data_seq','event_log_seq']:
            self.conn.execute(f'CREATE SEQUENCE IF NOT EXISTS {seq} START 1')

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def get_all_gps(self, limit=1000) -> list:
        try:
            rows = self.conn.execute(
                f"SELECT * FROM {TABLE_GPS_DATA} ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_GPS_DATA} LIMIT 0").description]
            return [dict(zip(cols, r)) for r in rows]
        except:
            return []

    def get_all_results(self, limit=500) -> list:
        try:
            rows = self.conn.execute(
                f"SELECT * FROM {TABLE_RESULT_DATA} ORDER BY created_at DESC LIMIT ?", (limit,)
            ).fetchall()
            cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_RESULT_DATA} LIMIT 0").description]
            return [dict(zip(cols, r)) for r in rows]
        except:
            return []

    def get_summary(self) -> dict:
        try:
            total_gps = self.conn.execute(f"SELECT count(*) FROM {TABLE_GPS_DATA}").fetchone()[0]
            total_results = self.conn.execute(f"SELECT count(*) FROM {TABLE_RESULT_DATA}").fetchone()[0]
            correct = self.conn.execute(
                f"SELECT count(*) FROM {TABLE_RESULT_DATA} WHERE result=1"
            ).fetchone()[0]
            failed = self.conn.execute(
                f"SELECT count(*) FROM {TABLE_RESULT_DATA} WHERE result=0"
            ).fetchone()[0]
            regions = self.conn.execute(
                f"SELECT region_code, count(*) as cnt FROM {TABLE_GPS_DATA} GROUP BY region_code"
            ).fetchall()
            return {
                "total_gps": total_gps,
                "total_results": total_results,
                "correct": correct,
                "failed": failed,
                "regions": {r[0]: r[1] for r in regions},
            }
        except Exception as e:
            return {"error": str(e)}

    def export_parquet(self, table: str = "") -> dict:
        os.makedirs(PARQUET_TEMP_DIR, exist_ok=True)
        tables = [table] if table else [TABLE_GPS_DATA, TABLE_RESULT_DATA]
        exported = {}
        for t in tables:
            try:
                table_dir = os.path.join(PARQUET_TEMP_DIR, t)
                self.conn.execute(f"""
                    COPY (SELECT * FROM {t} ORDER BY region_code, created_at)
                    TO '{table_dir}' (FORMAT PARQUET, CODEC 'ZSTD', PARTITION_BY (region_code))
                """)
                exported[t] = table_dir
                logger.info("Parquet export: %s", table_dir)
            except Exception as e:
                logger.warning("Parquet export %s error: %s", t, e)
        return exported

    def clear_all(self):
        for t in [TABLE_GPS_DATA, TABLE_RESULT_DATA, TABLE_DEVICE_DATA, TABLE_EVENT_LOG]:
            try:
                self.conn.execute(f"DELETE FROM {t}")
            except:
                pass
