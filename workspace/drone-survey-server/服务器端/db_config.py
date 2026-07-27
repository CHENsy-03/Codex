# -*- coding: utf-8 -*-
"""
5.docx §9 数据库改造：统一为 4 张标准表
  device_data — 设备注册信息
  gps_data    — GPS 定位数据
  result_data — 结果裁决记录
  event_log   — 事件日志
"""
import os, math

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
DB_DIR = os.path.join(BASE_DIR, "databases")
os.makedirs(DB_DIR, exist_ok=True)

REGION_CONFIG = {
    "hangzhou": {
        "code": "HW", "name": "杭州",
        "db_path": os.path.join(DB_DIR, "Home-HW.duckdb"),
        "rural_alt_min": 0.0, "rural_alt_max": 200.0,
        "boundary": {"points": [(30.0,119.5),(30.6,119.5),(30.6,120.8),(30.0,120.8)]},
    },
    "shaoxing": {
        "code": "SX", "name": "绍兴",
        "db_path": os.path.join(DB_DIR, "Home-SX.duckdb"),
        "rural_alt_min": 0.0, "rural_alt_max": 250.0,
        "boundary": {"points": [(29.4,119.8),(30.15,119.8),(30.15,121.3),(29.4,121.3)]},
    },
    "zhejiang": {
        "code": "ZJ", "name": "浙江",
        "db_path": os.path.join(DB_DIR, "Home-ZJ.duckdb"),
        "rural_alt_min": 0.0, "rural_alt_max": 250.0,
        "boundary": {"points": [(28.0,118.0),(31.0,118.0),(31.0,123.0),(28.0,123.0)]},
    },
    "yunnan": {
        "code": "YN", "name": "云南",
        "db_path": os.path.join(DB_DIR, "Home-YN.duckdb"),
        "rural_alt_min": 0.0, "rural_alt_max": 3500.0,
        "boundary": {"points": [(21.0,97.0),(29.0,97.0),(29.0,106.0),(21.0,106.0)]},
    },
    "zhaotong": {
        "code": "ZT", "name": "昭通",
        "db_path": os.path.join(DB_DIR, "Home-ZT.duckdb"),
        "rural_alt_min": 0.0, "rural_alt_max": 4000.0,
        "boundary": {"points": [(26.5,102.5),(29.0,102.5),(29.0,105.5),(26.5,105.5)]},
    },
}

MAIN_DB_PATH = os.path.join(DB_DIR, "Home-ALL.duckdb")
PRECISION_THRESHOLD = 0.05  # 5cm
APPENDER_BATCH_SIZE = 100
PARQUET_TEMP_DIR = os.path.join(DB_DIR, 'parquet_exports')
PARTITION_BY = 'region_code'
os.makedirs(PARQUET_TEMP_DIR, exist_ok=True)

from utils.geo import build_bbox
for _cfg in REGION_CONFIG.values():
    if "boundary" in _cfg and "points" in _cfg["boundary"]:
        _cfg["boundary"]["_bbox"] = build_bbox(_cfg["boundary"]["points"])

# ── 表名 ──
TABLE_DEVICE_DATA = "device_data"
TABLE_GPS_DATA = "gps_data"
TABLE_RESULT_DATA = "result_data"
TABLE_EVENT_LOG = "event_log"

# ── 4 张标准表定义 (5.docx §9) ──

CREATE_DEVICE_DATA = f"""
CREATE TABLE IF NOT EXISTS {TABLE_DEVICE_DATA} (
    device_id   VARCHAR PRIMARY KEY,
    device_type VARCHAR DEFAULT 'gps',
    region      VARCHAR DEFAULT '',
    firmware    VARCHAR DEFAULT '',
    status      VARCHAR DEFAULT 'offline',
    first_seen  BIGINT,
    last_seen   BIGINT
)
"""

CREATE_GPS_DATA = f"""
CREATE TABLE IF NOT EXISTS {TABLE_GPS_DATA} (
    id          INTEGER PRIMARY KEY DEFAULT nextval('gps_data_seq'),
    batch_id    VARCHAR,
    region_code VARCHAR,
    group_label VARCHAR,        -- A/B/C
    lat DOUBLE, lng DOUBLE, alt DOUBLE,
    e DOUBLE, n DOUBLE, u DOUBLE,
    h DOUBLE, v DOUBLE, d DOUBLE,
    is_correct  BOOLEAN DEFAULT FALSE,
    device_id   VARCHAR DEFAULT '',
    survey_time BIGINT,
    created_at  BIGINT
)
"""

CREATE_RESULT_DATA = f"""
CREATE TABLE IF NOT EXISTS {TABLE_RESULT_DATA} (
    id          INTEGER PRIMARY KEY DEFAULT nextval('result_data_seq'),
    batch_id    VARCHAR,
    device_id   VARCHAR DEFAULT '',
    region_code VARCHAR,
    result      INTEGER DEFAULT -1,  -- 1=正确 0=错误 -1=未知
    reason      VARCHAR DEFAULT '',
    score       INTEGER DEFAULT 0,
    ab_e DOUBLE, ab_n DOUBLE, ab_u DOUBLE,
    ac_e DOUBLE, ac_n DOUBLE, ac_u DOUBLE,
    bc_e DOUBLE, bc_n DOUBLE, bc_u DOUBLE,
    is_correct  BOOLEAN DEFAULT FALSE,
    survey_time BIGINT,
    created_at  BIGINT
)
"""

CREATE_EVENT_LOG = f"""
CREATE TABLE IF NOT EXISTS {TABLE_EVENT_LOG} (
    id          INTEGER PRIMARY KEY DEFAULT nextval('event_log_seq'),
    event_type  VARCHAR DEFAULT 'info',
    topic       VARCHAR DEFAULT '',
    source      VARCHAR DEFAULT '',
    device_id   VARCHAR DEFAULT '',
    message     VARCHAR DEFAULT '',
    level       VARCHAR DEFAULT 'info',
    created_at  BIGINT
)
"""

# ── 序列自增辅助 ──
CREATE_GPS_SEQ = "CREATE SEQUENCE IF NOT EXISTS gps_data_seq START 1"
CREATE_RESULT_SEQ = "CREATE SEQUENCE IF NOT EXISTS result_data_seq START 1"
CREATE_LOG_SEQ = "CREATE SEQUENCE IF NOT EXISTS event_log_seq START 1"

ALL_CREATES = [
    CREATE_GPS_SEQ, CREATE_RESULT_SEQ, CREATE_LOG_SEQ,
    CREATE_DEVICE_DATA, CREATE_GPS_DATA, CREATE_RESULT_DATA, CREATE_EVENT_LOG,
]

# ── 导入字段兼容 ──
IMPORT_FIELDS = [
    "a_lat","a_lng","a_alt","a_e","a_n","a_u",
    "b_lat","b_lng","b_alt","b_e","b_n","b_u",
    "c_lat","c_lng","c_alt","c_e","c_n","c_u",
]

INSERT_GPS_COLS = "batch_id, region_code, group_label, lat, lng, alt, e, n, u, h, v, d, is_correct, device_id, survey_time, created_at"
INSERT_GPS_PLACEHOLDERS = ", ".join(["?" for _ in range(16)])

INSERT_RESULT_COLS = "batch_id, device_id, region_code, result, reason, score, ab_e, ab_n, ab_u, ac_e, ac_n, ac_u, bc_e, bc_n, bc_u, is_correct, survey_time, created_at"
INSERT_RESULT_PLACEHOLDERS = ", ".join(["?" for _ in range(18)])

INSERT_LOG_COLS = "event_type, topic, source, device_id, message, level, created_at"
INSERT_LOG_PLACEHOLDERS = ", ".join(["?" for _ in range(7)])

INSERT_DEVICE_COLS = "device_id, device_type, region, firmware, status, first_seen, last_seen"
INSERT_DEVICE_PLACEHOLDERS = ", ".join(["?" for _ in range(7)])
