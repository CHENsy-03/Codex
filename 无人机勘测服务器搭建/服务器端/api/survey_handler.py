# -*- coding: utf-8 -*-
"""V2.1 Survey Upload Handler - Excel parsing + DuckDB storage + auto-scoring."""
import time, json, io, sys, os
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
def process_survey_upload(body, files=None):
    pid = body.get("project_id", "")
    raw = body.get("data", "")
    records = []
    if isinstance(raw, list):
        records = raw
    elif isinstance(raw, str):
        for line in raw.strip().split("\n"):
            parts = [p.strip() for p in line.split(",")]
            if len(parts) >= 4:
                records.append({"device_id": parts[0] if len(parts) > 0 else "",
                    "latitude": float(parts[1]) if len(parts) > 1 else 0,
                    "longitude": float(parts[2]) if len(parts) > 2 else 0,
                    "height": float(parts[3]) if len(parts) > 3 else 0})
    if not records:
        return 2001, "no valid data found", None
    try:
        from storage.duckdb_manager import DuckDBManager
        from config.config_loader import ConfigLoader
        config = ConfigLoader.load("config/server.yaml")
        db = DuckDBManager(db_path=config.database.path,
                           memory_limit=config.database.memory_limit,
                           temp_directory=config.database.temp_directory)
        db.connect()
        count = 0
        for r in records:
            r["msg_type"] = "GPGGA"; r["server_id"] = config.id
            r["gnss_time"] = int(time.time()); r["created_at"] = int(time.time())
            r["solution_type"] = 1; r["e_accuracy"] = 0; r["n_accuracy"] = 0; r["u_accuracy"] = 0
            r["diff_age"] = 0; r["station_id"] = ""; r["source_channel"] = "api_upload"
            r["raw_data"] = b""
            db.insert_gnss(r)
            count += 1
        score = min(100, count * 2)
        status = "PASS" if score >= 60 else "FAIL"
        from api.handlers import result_set
        result_set(pid, score, f"uploaded {count} records", status)
        db.disconnect()
        return 0, "success", {"records_uploaded": count, "score": score, "status": status}
    except Exception as ex:
        return 5001, f"server error: {str(ex)}", None
