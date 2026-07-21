# -*- coding: utf-8 -*-
"""V2.0 Data Lifecycle - TTL cleanup + periodic archiving + compression."""
import os, sys, time, threading, pathlib
from datetime import datetime
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
DEFAULT_RETENTION_DAYS = 90
ARCHIVE_DIR_NAME = 'data/archive'
def cleanup_expired(config_path='config/server.yaml', retention_days=DEFAULT_RETENTION_DAYS):
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    config = ConfigLoader.load(config_path)
    cutoff = int(time.time()) - (retention_days * 86400)
    db = DuckDBManager(db_path=config.database.path,
                       memory_limit=config.database.memory_limit,
                       temp_directory=config.database.temp_directory)
    db.connect()
    try:
        count = db.conn.execute(
            'SELECT count(*) FROM gnss_position WHERE created_at < ?', (cutoff,)
        ).fetchone()[0]
        archive_dir = pathlib.Path(ARCHIVE_DIR_NAME)
        archive_dir.mkdir(parents=True, exist_ok=True)
        ts = datetime.now().strftime('%Y%m%d')
        archive_path = archive_dir / f'gnss_archive_{ts}.csv.gz'
        db.conn.execute(f"COPY (SELECT * FROM gnss_position WHERE created_at < {cutoff}) "
                        f"TO '{archive_path}' (HEADER, DELIMITER ',')")
        deleted = db.conn.execute(
            'DELETE FROM gnss_position WHERE created_at < ?', (cutoff,)
        ).fetchall()[0][0] if db.conn.description else 0
        print(f'  [Lifecycle] Archived {count} records, deleted {deleted}')
        return {'archived': count, 'deleted': deleted, 'archive_path': str(archive_path)}
    finally:
        db.disconnect()
def get_retention_policy():
    return {'retention_days': DEFAULT_RETENTION_DAYS,
            'archive_dir': ARCHIVE_DIR_NAME, 'compression': 'gzip'}
class LifecycleScheduler:
    def __init__(self, interval_hours=24.0, retention_days=DEFAULT_RETENTION_DAYS):
        self.interval_hours = interval_hours
        self.retention_days = retention_days
        self._running = False
        self._thread = None
        self._last_run = None
    def start(self):
        if self._running:
            return
        self._running = True
        self._thread = threading.Thread(target=self._run, daemon=True)
        self._thread.start()
        print(f'  [Lifecycle] Scheduled every {self.interval_hours}h, '
              f'retention {self.retention_days}d')
    def stop(self):
        self._running = False
    def _run(self):
        while self._running:
            try:
                self._last_run = time.time()
                cleanup_expired(retention_days=self.retention_days)
            except Exception as ex:
                print(f'  [Lifecycle] Failed: {ex}')
            time.sleep(self.interval_hours * 3600)
    @property
    def status(self):
        return {'running': self._running, 'interval_hours': self.interval_hours,
                'retention_days': self.retention_days, 'last_run': self._last_run}
