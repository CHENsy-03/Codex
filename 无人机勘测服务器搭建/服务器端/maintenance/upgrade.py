# -*- coding: utf-8 -*-
"""V2.0 Version Upgrade - version management + migration scripts."""
import os, sys, json, time, pathlib
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
CURRENT_VERSION = "2.0.0"
VERSION_FILE = "data/version.json"
def get_version():
    p = pathlib.Path(VERSION_FILE)
    if p.exists():
        try:
            data = json.loads(p.read_text(encoding="utf-8"))
            return data.get("version", CURRENT_VERSION)
        except Exception:
            pass
    return CURRENT_VERSION
def set_version(version, description=""):
    p = pathlib.Path(VERSION_FILE)
    p.parent.mkdir(parents=True, exist_ok=True)
    data = {"version": version, "updated_at": int(time.time()), "description": description}
    p.write_text(json.dumps(data, ensure_ascii=False, indent=2), encoding="utf-8")
MIGRATIONS = {
    "2.0.0": [
        "CREATE INDEX IF NOT EXISTS idx_gnss_device ON gnss_position(device_id)",
        "CREATE INDEX IF NOT EXISTS idx_gnss_time ON gnss_position(created_at)",
        "CREATE INDEX IF NOT EXISTS idx_gnss_server ON gnss_position(server_id)",
    ],
}
def run_migrations(config_path="config/server.yaml"):
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    current = get_version()
    config = ConfigLoader.load(config_path)
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    migrated = 0
    try:
        for version, sqls in sorted(MIGRATIONS.items()):
            if version > current:
                print(f"  Running migrations for v{version} ({len(sqls)} sql)...")
                for sql in sqls:
                    try:
                        db.conn.execute(sql)
                        migrated += 1
                    except Exception as ex:
                        print(f"  Migration failed: {ex}")
                set_version(version, f"Migrated from {current}")
                current = version
        if migrated == 0:
            print(f"  Database up to date (v{current})")
        else:
            print(f"  {migrated} migrations applied. Now v{current}")
    finally:
        db.disconnect()
    return migrated
def check_upgrade():
    current = get_version()
    latest = CURRENT_VERSION
    needs = current < latest
    pending = [v for v in sorted(MIGRATIONS) if v > current]
    return {"current_version": current, "latest_version": latest,
            "needs_upgrade": needs, "pending_migrations": len(pending)}
def create_pre_upgrade_backup(config_path="config/server.yaml"):
    from maintenance.backup import create_backup
    path = create_backup(config_path)
    print(f"  Pre-upgrade backup: {path}")
    return path
