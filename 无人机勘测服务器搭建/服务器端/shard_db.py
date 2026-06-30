# -*- coding: utf-8 -*-
"""
5.docx §9 数据库改造 - 分片数据库管理器
4表结构: device_data / gps_data / result_data / event_log
"""
import duckdb, logging, os, math, time, json
from typing import Dict, Tuple, List, Optional
from db_config import (
    REGION_CONFIG, MAIN_DB_PATH,
    TABLE_DEVICE_DATA, TABLE_GPS_DATA, TABLE_RESULT_DATA, TABLE_EVENT_LOG,
    ALL_CREATES,
    INSERT_DEVICE_COLS, INSERT_DEVICE_PLACEHOLDERS,
    INSERT_GPS_COLS, INSERT_GPS_PLACEHOLDERS,
    INSERT_RESULT_COLS, INSERT_RESULT_PLACEHOLDERS,
    INSERT_LOG_COLS, INSERT_LOG_PLACEHOLDERS,
    PRECISION_THRESHOLD,
)
from db_base import DatabaseBase

logger = logging.getLogger(__name__)
CITY_TO_PROVINCE_MAP = {"hangzhou": "zhejiang", "shaoxing": "zhejiang", "zhaotong": "yunnan"}

def _enu(pt: dict) -> tuple:
    """从 dict 提取 e/n/u，兼容旧版 h/v/d 格式"""
    if "e" in pt:
        return float(pt.get("e", 0)), float(pt.get("n", 0)), float(pt.get("u", 0))
    if "h" in pt:
        import math as _m
        en = float(pt["h"]) / _m.sqrt(2)
        return en, en, float(pt.get("v", 0))
    return 0.0, 0.0, 0.0


class ShardDatabase(DatabaseBase):
    """分片数据库（按地区）"""

    def __init__(self, region_code: str, db_path: str = ""):
        super().__init__()
        self.region_code = region_code
        if db_path:
            self.db_path = db_path
        elif region_code in REGION_CONFIG:
            self.db_path = REGION_CONFIG[region_code]["db_path"]
        else:
            self.db_path = os.path.join(
                os.path.dirname(__file__), "databases", f"Home-{region_code}.duckdb"
            )

    def connect(self):
        self.conn = duckdb.connect(self.db_path)
        self._init_db()

    def disconnect(self):
        if self.conn:
            self.conn.close()
            self.conn = None

    def _init_db(self):
        """建表"""
        for ddl in ALL_CREATES:
            self.conn.execute(ddl)
        # 迁移旧表数据
        self._migrate_from_old()

    def _migrate_from_old(self):
        """从旧 position_data_rural/urban 表迁移数据"""
        for old_table in ["position_data_rural", "position_data_urban"]:
            try:
                exists = self.conn.execute(
                    f"SELECT count(*) FROM information_schema.tables WHERE table_name='{old_table}'"
                ).fetchone()[0]
                if not exists:
                    continue
                rows = self.conn.execute(f"SELECT * FROM {old_table}").fetchall()
                if not rows:
                    continue
                cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {old_table} LIMIT 0").description]
                migrated = 0
                for row in rows:
                    d = dict(zip(cols, row))
                    batch_id = d.get("batch_id", f"migrated_{int(time.time())}")
                    rc = d.get("region_code", self.region_code)
                    # gps_data: A/B/C
                    for label in ["a", "b", "c"]:
                        lat = d.get(f"{label}_lat", 0.0)
                        lng = d.get(f"{label}_lng", 0.0)
                        alt = d.get(f"{label}_alt", 0.0)
                        e = d.get(f"{label}_e", d.get(f"{label}_h", 0.0) / math.sqrt(2))
                        n = e  # approx
                        u = d.get(f"{label}_u", d.get(f"{label}_v", 0.0))
                        h = d.get(f"{label}_h", math.sqrt(e*e + n*n))
                        v = u
                        ddd = math.sqrt(h*h + v*v)
                        self._migrate_insert_gps(batch_id, rc, label.upper(), lat, lng, alt,
                                        e, n, u, h, v, ddd,
                                        bool(d.get("is_correct", True)),
                                        "migrated", d.get("survey_time", int(time.time())))
                    # result_data
                    ab_e = d.get("ab_h_diff", 0.0) / math.sqrt(2)
                    ab_n = ab_e
                    ab_u = d.get("ab_v_diff", 0.0)
                    is_correct = bool(d.get("is_correct", True))
                    self._migrate_insert_result(batch_id, "migrated", rc, 1 if is_correct else 0,
                                       "migrated from old", 3 if is_correct else 0,
                                       ab_e, ab_n, ab_u,
                                       d.get("ac_h_diff",0)/math.sqrt(2), d.get("ac_v_diff",0),
                                       d.get("bc_h_diff",0)/math.sqrt(2), d.get("bc_v_diff",0),
                                       is_correct, d.get("survey_time", int(time.time())))
                    migrated += 1
                logger.info("Migrated %d rows from %s", migrated, old_table)
                self.conn.execute(f"DROP TABLE IF EXISTS {old_table}")
            except Exception as e:
                logger.warning("Migration from %s: %s", old_table, e)
        # Drop other unused old tables
        for t in ["position_data_rural", "position_data_urban", "cluster_position_stats",
                   "device_info", "gps_position", "gps_quality", "raw_packet", "alarm_event"]:
            try:
                self.conn.execute(f"DROP TABLE IF EXISTS {t}")
            except:
                pass

    # ── 设备数据 ──
    def upsert_device(self, device_id, device_type="gps", region="", firmware=""):
        now = int(time.time())
        sql = f"""INSERT INTO {TABLE_DEVICE_DATA} ({INSERT_DEVICE_COLS}) VALUES ({INSERT_DEVICE_PLACEHOLDERS})
            ON CONFLICT (device_id) DO UPDATE SET
                last_seen = EXCLUDED.last_seen,
                status = EXCLUDED.status,
                region = CASE WHEN EXCLUDED.region != '' THEN EXCLUDED.region ELSE device_data.region END"""
        self.conn.execute(sql, (device_id, device_type, region, firmware, "online", now, now))

    def _migrate_insert_gps(self, batch_id, region_code, group_label,
                   lat, lng, alt, e=0.0, n=0.0, u=0.0,
                   h=0.0, v=0.0, d=0.0, is_correct=False,
                   device_id="", survey_time=0):
        now = int(time.time())
        sql = f"INSERT INTO {TABLE_GPS_DATA} (id, {INSERT_GPS_COLS}) VALUES (nextval('gps_data_seq'), {INSERT_GPS_PLACEHOLDERS})"
        self.conn.execute(sql, (batch_id, region_code, group_label, lat, lng, alt,
                           e, n, u, h, v, d, is_correct, device_id,
                           survey_time or now, now))

    def _migrate_insert_result(self, batch_id, device_id, region_code, result,
                     reason, score=0,
                     ab_e=0.0, ab_n=0.0, ab_u=0.0,
                     ac_e=0.0, ac_n=0.0, ac_u=0.0,
                     bc_e=0.0, bc_n=0.0, bc_u=0.0,
                     is_correct=False, survey_time=0):
        now = int(time.time())
        sql = f"INSERT INTO {TABLE_RESULT_DATA} (id, {INSERT_RESULT_COLS}) VALUES (nextval('result_data_seq'), {INSERT_RESULT_PLACEHOLDERS})"
        self.conn.execute(sql, (batch_id, device_id, region_code, result, reason, score,
                           ab_e, ab_n, ab_u, ac_e, ac_n, ac_u, bc_e, bc_n, bc_u,
                           is_correct, survey_time or now, now))

    def get_device(self, device_id: str) -> Optional[dict]:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_DEVICE_DATA} WHERE device_id=?", (device_id,)).fetchall()
        if not rows: return None
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_DEVICE_DATA} LIMIT 0").description]
        return dict(zip(cols, rows[0]))

    def list_devices(self) -> list:
        try:
            return self.conn.execute(f"SELECT * FROM {TABLE_DEVICE_DATA} ORDER BY last_seen DESC").fetchall()
        except:
            return []

    # ── GPS 数据 ──
    def insert_gps(self, batch_id, region_code, group_label,
                   lat, lng, alt, e=0.0, n=0.0, u=0.0,
                   h=0.0, v=0.0, d=0.0, is_correct=False,
                   device_id="", survey_time=0):
        now = int(time.time())
        self.conn.execute(f"INSERT INTO {TABLE_GPS_DATA} (id, {INSERT_GPS_COLS}) VALUES (nextval('gps_data_seq'), {INSERT_GPS_PLACEHOLDERS})",
                          (batch_id, region_code, group_label, lat, lng, alt,
                           e, n, u, h, v, d, is_correct, device_id,
                           survey_time or now, now))


    def get_gps_by_batch(self, batch_id: str) -> list:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_GPS_DATA} WHERE batch_id=? ORDER BY group_label",
                                 (batch_id,)).fetchall()
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_GPS_DATA} LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def get_all_gps(self, limit=500) -> list:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_GPS_DATA} ORDER BY created_at DESC LIMIT ?",
                                 (limit,)).fetchall()
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_GPS_DATA} LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    # ── 结果数据 ──
    def insert_result(self, batch_id, device_id, region_code, result,
                      reason, score=0,
                      ab_e=0.0, ab_n=0.0, ab_u=0.0,
                      ac_e=0.0, ac_n=0.0, ac_u=0.0,
                      bc_e=0.0, bc_n=0.0, bc_u=0.0,
                      is_correct=False, survey_time=0):
        now = int(time.time())
        self.conn.execute(f"INSERT INTO {TABLE_RESULT_DATA} (id, {INSERT_RESULT_COLS}) VALUES (nextval('result_data_seq'), {INSERT_RESULT_PLACEHOLDERS})",
                          (batch_id, device_id, region_code, result, reason, score,
                           ab_e, ab_n, ab_u, ac_e, ac_n, ac_u, bc_e, bc_n, bc_u,
                           is_correct, survey_time or now, now))


    def get_results(self, limit=200) -> list:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_RESULT_DATA} ORDER BY created_at DESC LIMIT ?",
                                 (limit,)).fetchall()
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_RESULT_DATA} LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    def get_result_by_batch(self, batch_id: str) -> Optional[dict]:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_RESULT_DATA} WHERE batch_id=?", (batch_id,)).fetchall()
        if not rows: return None
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_RESULT_DATA} LIMIT 0").description]
        return dict(zip(cols, rows[0]))

    # ── 事件日志 ──
    def log_event(self, event_type, topic="", source="", device_id="", message="", level="info"):
        now = int(time.time())
        sid = self.conn.execute("SELECT nextval('event_log_seq')").fetchone()[0]
        self.conn.execute(f"INSERT INTO {TABLE_EVENT_LOG} (id, {INSERT_LOG_COLS}) VALUES (nextval('event_log_seq'), {INSERT_LOG_PLACEHOLDERS})",
                          (event_type, topic, source, device_id, message, level, now))
        return sid

    def get_logs(self, limit=100) -> list:
        rows = self.conn.execute(f"SELECT * FROM {TABLE_EVENT_LOG} ORDER BY created_at DESC LIMIT ?",
                                 (limit,)).fetchall()
        cols = [d[0] for d in self.conn.execute(f"SELECT * FROM {TABLE_EVENT_LOG} LIMIT 0").description]
        return [dict(zip(cols, r)) for r in rows]

    # ── 勘测：保存一轮 A/B/C ──
    def save_survey(self, batch_id: str, A: dict, B: dict, C: dict,
                    region_code: str, round_number: int, is_correct: bool,
                    ab_diff: tuple, ac_diff: tuple, bc_diff: tuple,
                    device_id: str = "", survey_time: int = 0):
        """保存一轮勘测完整数据到 4 张表"""
        now = int(time.time())
        st = survey_time or now
        # 1) 更新设备
        self.upsert_device(device_id or f"survey_{batch_id}", "gps",
                          region_code, "v0.1")
        # 2) 存入 GPS 数据
        for label, pt, diff in [("A", A, ab_diff), ("B", B, ac_diff), ("C", C, bc_diff)]:
            e, n, u = _enu(pt)
            h = math.sqrt(e*e + n*n)
            v = u
            ddd = math.sqrt(h*h + v*v)
            self.insert_gps(batch_id, region_code, label,
                           pt["lat"], pt["lng"], pt["alt"],
                           e, n, u, h, v, ddd,
                           is_correct, device_id, st)
        # 3) 存入结果
        result_code = 1 if is_correct else 0
        self.insert_result(batch_id, device_id or f"survey_{batch_id}",
                          region_code, result_code,
                          "passed" if is_correct else "failed",
                          3 if is_correct else 0,
                          ab_diff[0], ab_diff[1], ab_diff[2],
                          ac_diff[0], ac_diff[1], ac_diff[2],
                          bc_diff[0], bc_diff[1], bc_diff[2],
                          is_correct, st)
        # 4) 日志
        self.log_event("survey", "survey.result", f"app:{region_code}",
                      device_id, f"batch={batch_id} correct={is_correct}", "info")
        return True

    # ── 数据管理 ──
    def delete_by_batch(self, batch_id: str):
        self.conn.execute(f"DELETE FROM {TABLE_GPS_DATA} WHERE batch_id=?", (batch_id,))
        self.conn.execute(f"DELETE FROM {TABLE_RESULT_DATA} WHERE batch_id=?", (batch_id,))

    def clear_all(self):
        self.conn.execute(f"DELETE FROM {TABLE_GPS_DATA}")
        self.conn.execute(f"DELETE FROM {TABLE_RESULT_DATA}")
        self.conn.execute(f"DELETE FROM {TABLE_DEVICE_DATA}")
        self.conn.execute(f"DELETE FROM {TABLE_EVENT_LOG}")

    def count_all(self) -> dict:
        try:
            d = self.conn.execute(f"SELECT count(*) FROM {TABLE_DEVICE_DATA}").fetchone()[0]
            g = self.conn.execute(f"SELECT count(*) FROM {TABLE_GPS_DATA}").fetchone()[0]
            r = self.conn.execute(f"SELECT count(*) FROM {TABLE_RESULT_DATA}").fetchone()[0]
            l = self.conn.execute(f"SELECT count(*) FROM {TABLE_EVENT_LOG}").fetchone()[0]
            return {"devices": d, "gps_records": g, "results": r, "logs": l}
        except:
            return {"devices": 0, "gps_records": 0, "results": 0, "logs": 0}

    # ── 导入导出 ──
    def import_from_chart(self, data: list, survey_type: str = "rural") -> Tuple[int, list]:
        """从图表导入数据 (兼容旧格式)"""
        ok, msgs = 0, []
        for item in data:
            try:
                batch_id = item.get("batch_id", f"import_{int(time.time())}_{ok}")
                rc = item.get("region_code", self.region_code)
                A = {"lat": float(item["a_lat"]), "lng": float(item["a_lng"]), "alt": float(item["a_alt"]),
                     "e": float(item.get("a_e", 0)), "n": float(item.get("a_n", 0)), "u": float(item.get("a_u", 0))}
                B = {"lat": float(item["b_lat"]), "lng": float(item["b_lng"]), "alt": float(item["b_alt"]),
                     "e": float(item.get("b_e", 0)), "n": float(item.get("b_n", 0)), "u": float(item.get("b_u", 0))}
                C = {"lat": float(item["c_lat"]), "lng": float(item["c_lng"]), "alt": float(item["c_alt"]),
                     "e": float(item.get("c_e", 0)), "n": float(item.get("c_n", 0)), "u": float(item.get("c_u", 0))}
                from position_compare import compare_position
                is_correct, details = compare_position(A, B, C, threshold=PRECISION_THRESHOLD)
                ab = (details["ab"]["e"], details["ab"]["n"], details["ab"]["u"])
                ac = (details["ac"]["e"], details["ac"]["n"], details["ac"]["u"])
                bc = (details["bc"]["e"], details["bc"]["n"], details["bc"]["u"])
                self.save_survey(batch_id, A, B, C, rc, ok+1, is_correct, ab, ac, bc,
                               device_id=item.get("device_id", ""))
                ok += 1
            except Exception as e:
                msgs.append(f"#{ok+1}: {e}")
        return ok, msgs

    def export_all(self, fmt: str = "json") -> str:
        """导出所有数据"""
        import json, csv
        data = self.get_all_gps(9999)
        ts = int(time.time())
        fname = f"export_{self.region_code}_{ts}.{fmt}"
        fpath = os.path.join(os.path.dirname(self.db_path), fname)
        if fmt == "json":
            with open(fpath, "w", encoding="utf-8") as f:
                json.dump(data, f, ensure_ascii=False, indent=2, default=str)
        elif fmt == "csv":
            if not data: return ""
            with open(fpath, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(f, fieldnames=data[0].keys())
                w.writeheader(); w.writerows(data)
        return fpath

    # ── 向后兼容：旧版 insert_survey_data 适配器 ──
    def insert_survey_data(self, A, B, C):
        import math, time
        from position_compare import compare_position
        from db_config import PRECISION_THRESHOLD
        passed, details = compare_position(A, B, C, PRECISION_THRESHOLD)
        if not passed:
            return False, "精度差超过阈值"
        region_code = self.region_code
        n = 1
        while True:
            batch_id = f"{region_code[:2].upper()}-{n}"
            existing = self.get_gps_by_batch(batch_id)
            if not existing: break
            n += 1
        ab = details["ab"]; ac = details["ac"]; bc = details["bc"]
        st = int(time.time())
        self.save_survey(batch_id, A, B, C, region_code, n, True,
                        (ab["e"], ab["n"], ab["u"]),
                        (ac["e"], ac["n"], ac["u"]),
                        (bc["e"], bc["n"], bc["u"]), "", st)
        return True, f"成功 {batch_id}"


class BatchShardMerger:
    """分库 → 总库 合并器"""

    def __init__(self):
        self.main_conn = __import__("duckdb").connect(__import__("db_config").MAIN_DB_PATH)
        for ddl in __import__("db_config").ALL_CREATES:
            self.main_conn.execute(ddl)
        for seq in ["gps_data_seq", "result_data_seq", "event_log_seq"]:
            try:
                self.main_conn.execute(f"CREATE SEQUENCE IF NOT EXISTS {seq} START 1")
            except:
                pass
        self._shards = {}
        try: self.main_conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_gps ON gps_data(batch_id, group_label, region_code)")
        except: pass
        try: self.main_conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_result ON result_data(batch_id, region_code)")
        except: pass

    def get_shard(self, region_code):
        if region_code not in self._shards:
            s = __import__("shard_db").ShardDatabase(region_code)
            s.connect()
            self._shards[region_code] = s
        return self._shards[region_code]

    def merge_all_regions(self) -> dict:
        results = {}
        _dc = __import__("db_config")
        _c2p = __import__("shard_db").CITY_TO_PROVINCE_MAP
        # Phase 1: City -> Province
        for city_rc, prov_rc in _c2p.items():
            try:
                city_shard = self.get_shard(city_rc)
                prov_shard = self.get_shard(prov_rc)
                try: prov_shard.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_gps ON gps_data(batch_id, group_label, region_code)")
                except: pass
                try: prov_shard.conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS uq_result ON result_data(batch_id, region_code)")
                except: pass
                gps_rows = city_shard.get_all_gps(99999) or []
                result_rows = city_shard.get_results(99999) or []
                ig = ir = 0
                for r in gps_rows:
                    try:
                        prov_shard.conn.execute(f"INSERT INTO {_dc.TABLE_GPS_DATA} (batch_id,region_code,group_label,lat,lng,alt,e,n,u,h,v,d,is_correct,device_id,survey_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                            (r["batch_id"],r["region_code"],r["group_label"],r["lat"],r["lng"],r["alt"],r["e"],r["n"],r["u"],r["h"],r["v"],r["d"],r["is_correct"],r["device_id"],r["survey_time"],r["created_at"]))
                        ig += 1
                    except: pass
                for r in result_rows:
                    try:
                        prov_shard.conn.execute(f"INSERT INTO {_dc.TABLE_RESULT_DATA} (batch_id,device_id,region_code,result,reason,score,ab_e,ab_n,ab_u,ac_e,ac_n,ac_u,bc_e,bc_n,bc_u,is_correct,survey_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                            (r["batch_id"],r["device_id"],r["region_code"],r["result"],r["reason"],r["score"],r["ab_e"],r["ab_n"],r["ab_u"],r["ac_e"],r["ac_n"],r["ac_u"],r["bc_e"],r["bc_n"],r["bc_u"],r["is_correct"],r["survey_time"],r["created_at"]))
                        ir += 1
                    except: pass
                results[f"{city_rc}->{prov_rc}"] = f"gps={ig} results={ir}"
            except Exception as e:
                results[f"{city_rc}->{prov_rc}"] = f"error: {e}"
        # Phase 2: Province -> Main (skip cities)
        for rc in _dc.REGION_CONFIG:
            if rc in _c2p:
                continue
            try:
                shard = self.get_shard(rc)
                gps_rows = shard.get_all_gps(99999) or []
                result_rows = shard.get_results(99999) or []
                ig = ir = 0
                for r in gps_rows:
                    try:
                        self.main_conn.execute(f"INSERT INTO {_dc.TABLE_GPS_DATA} (batch_id,region_code,group_label,lat,lng,alt,e,n,u,h,v,d,is_correct,device_id,survey_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                            (r["batch_id"],r["region_code"],r["group_label"],r["lat"],r["lng"],r["alt"],r["e"],r["n"],r["u"],r["h"],r["v"],r["d"],r["is_correct"],r["device_id"],r["survey_time"],r["created_at"]))
                        ig += 1
                    except: pass
                for r in result_rows:
                    try:
                        self.main_conn.execute(f"INSERT INTO {_dc.TABLE_RESULT_DATA} (batch_id,device_id,region_code,result,reason,score,ab_e,ab_n,ab_u,ac_e,ac_n,ac_u,bc_e,bc_n,bc_u,is_correct,survey_time,created_at) VALUES (?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?,?) ON CONFLICT DO NOTHING",
                            (r["batch_id"],r["device_id"],r["region_code"],r["result"],r["reason"],r["score"],r["ab_e"],r["ab_n"],r["ab_u"],r["ac_e"],r["ac_n"],r["ac_u"],r["bc_e"],r["bc_n"],r["bc_u"],r["is_correct"],r["survey_time"],r["created_at"]))
                        ir += 1
                    except: pass
                results[rc] = f"gps={ig} results={ir}"
            except Exception as e:
                results[rc] = f"error: {e}"
        return results
    def close(self):
        for s in list(self._shards.values()):
            try:
                s.disconnect()
            except:
                pass
        if self.main_conn:
            self.main_conn.close()


if __name__ == "__main__":
    import sys
    cmd = sys.argv[1] if len(sys.argv) > 1 else ""
    if cmd == "merge-all":
        m = BatchShardMerger()
        r = m.merge_all_regions()
        m.close()
        for f, s in r.items():
            print(f"  {f}: {s}")
    elif cmd == "list":
        for rc in REGION_CONFIG:
            with ShardDatabase(rc) as db:
                c = db.count_all()
                print(f"{rc}: {c}")
    else:
        print("usage: python shard_db.py [merge-all|list]")
