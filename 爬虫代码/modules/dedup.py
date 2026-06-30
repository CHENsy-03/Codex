import sqlite3
import hashlib
import os
import logging

log = logging.getLogger('crawler.dedup')

class DedupDB:
    def __init__(self, db_path=None):
        if db_path is None:
            db_path = os.path.join(os.path.dirname(__file__), '..', 'output', 'crawler.db')
        self.db_path = os.path.abspath(db_path)
        self._init_db()

    def _init_db(self):
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.conn = sqlite3.connect(self.db_path)
        self.conn.execute('''
            CREATE TABLE IF NOT EXISTS crawled (
                url_hash TEXT PRIMARY KEY,
                url TEXT NOT NULL,
                title TEXT DEFAULT '',
                crawl_time TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                score INTEGER DEFAULT 0
            )
        ''')
        self.conn.commit()

    def _url_hash(self, url):
        return hashlib.sha256(url.encode('utf-8')).hexdigest()[:16]

    def is_duplicate(self, url):
        h = self._url_hash(url)
        cur = self.conn.execute('SELECT 1 FROM crawled WHERE url_hash = ?', (h,))
        return cur.fetchone() is not None

    def mark_crawled(self, url, title='', score=0):
        h = self._url_hash(url)
        self.conn.execute(
            'INSERT OR IGNORE INTO crawled (url_hash, url, title, score) VALUES (?, ?, ?, ?)',
            (h, url, title, score)
        )
        self.conn.commit()

    def dedup_list(self, articles):
        result = []
        for a in articles:
            url = a.get('url', '')
            if url and not self.is_duplicate(url):
                self.mark_crawled(url, a.get('title', ''), a.get('score', 0))
                result.append(a)
        return result

    def get_stats(self):
        cur = self.conn.execute('SELECT COUNT(*) FROM crawled')
        total = cur.fetchone()[0]
        cur = self.conn.execute('SELECT COUNT(*) FROM crawled WHERE score > 0')
        matched = cur.fetchone()[0]
        return {'total_crawled': total, 'total_matched': matched}

    def close(self):
        if hasattr(self, 'conn'):
            self.conn.close()

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()
