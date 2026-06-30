# Trend analysis module (optional, needs duckdb)
try:
    import duckdb
except ImportError:
    duckdb = None


def keyword_trend(conn, keyword, days=30):
    if conn is None:
        return []
    sql = 'SELECT DATE(publish_time) as d, COUNT(*) as cnt FROM articles WHERE title LIKE ? AND publish_time >= DATE(' + chr(39) + 'now' + chr(39) + ', ?) GROUP BY d ORDER BY d'
    return conn.execute(sql, ['%' + keyword + '%', '-' + str(days) + ' days']).fetchall()


def province_rank(conn, limit=10):
    if conn is None:
        return []
    return conn.execute('SELECT province, COUNT(*) as cnt FROM articles GROUP BY province ORDER BY cnt DESC LIMIT ?', [limit]).fetchall()
