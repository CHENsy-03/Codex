# -*- coding: utf-8 -*-
"""V2.0 Database Backup - timed backup + backup management."""
import os, sys, time, shutil, threading, pathlib
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
BACKUP_DIR_NAME = "backups"

def get_backup_dir():
    d = pathlib.Path(__file__).resolve().parent.parent / BACKUP_DIR_NAME
    d.mkdir(exist_ok=True)
    return d

def create_backup(config_path="config/server.yaml"):
    from config.config_loader import ConfigLoader
    config = ConfigLoader.load(config_path)
    db_path = pathlib.Path(config.database.path)
    if not db_path.exists():
        raise FileNotFoundError(f"Database not found: {db_path}")
    backup_dir = get_backup_dir()
    ts = datetime.now().strftime("%Y%m%d_%H%M%S")
    backup_name = f"gnss_backup_{config.id}_{ts}.duckdb"
    backup_path = backup_dir / backup_name
    shutil.copy2(db_path, backup_path)
    wal_path = pathlib.Path(str(db_path) + ".wal")
    if wal_path.exists():
        shutil.copy2(wal_path, str(backup_path) + ".wal")
    _cleanup_old(backup_dir, keep=10)
    return str(backup_path)

def _cleanup_old(backup_dir, keep=10):
    files = sorted(backup_dir.glob("gnss_backup_*.duckdb"),
                   key=os.path.getmtime, reverse=True)
    for f in files[keep:]:
        f.unlink(missing_ok=True)
        wal = pathlib.Path(str(f) + ".wal")
        wal.unlink(missing_ok=True)

def list_backups():
    backup_dir = get_backup_dir()
    backups = []
    for f in sorted(backup_dir.glob("gnss_backup_*.duckdb"),
                    key=os.path.getmtime, reverse=True):
        stat = f.stat()
        backups.append({"name": f.name, "path": str(f),
                        "size_mb": round(stat.st_size / 1048576, 2),
                        "created": datetime.fromtimestamp(stat.st_mtime).isoformat()})
    return backups

def restore_backup(backup_name, config_path="config/server.yaml"):
    from config.config_loader import ConfigLoader
    config = ConfigLoader.load(config_path)
    backup_dir = get_backup_dir()
    backup_path = backup_dir / backup_name
    if not backup_path.exists():
        raise FileNotFoundError(f"Backup not found: {backup_path}")
    db_path = pathlib.Path(config.database.path)
    db_path.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(backup_path, db_path)
    wal_backup = pathlib.Path(str(backup_path) + ".wal")
    if wal_backup.exists():
        shutil.copy2(wal_backup, str(db_path) + ".wal")
    return True

class BackupScheduler:
    def __init__(self, interval_hours=6.0, keep=10):
        self.interval_hours = interval_hours
        self.keep = keep
        self._running = False
        self._thread = None
        self._last_backup = None
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f"  [Backup] Scheduled every {self.interval_hours}h, keep {self.keep}")
    def stop(self):
        self._running = False
    def _run(self):
        while self._running:
            try:
                path = create_backup()
                self._last_backup = time.time()
                print(f"  [Backup] Created: {path}")
            except Exception as ex:
                print(f"  [Backup] Failed: {ex}")
            time.sleep(self.interval_hours * 3600)
    @property
    def status(self):
        return {"running": self._running, "interval_hours": self.interval_hours,
                "last_backup": self._last_backup, "backup_count": len(list_backups())}
