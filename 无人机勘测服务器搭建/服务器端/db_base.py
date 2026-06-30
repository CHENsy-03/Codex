"""数据库基类：共享方法 + 上下文管理器"""

from typing import Dict, List


class DatabaseBase:
    """数据库基类，提供 _row_to_dict、_get_columns 和上下文管理器支持"""

    def __init__(self):
        self.conn = None

    def connect(self):
        """子类重写：建立连接"""
        raise NotImplementedError

    def disconnect(self):
        """子类重写：关闭连接"""
        raise NotImplementedError

    def __enter__(self):
        self.connect()
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        self.disconnect()

    def _row_to_dict(self, row, columns) -> Dict:
        return dict(zip(columns, row))

    def _get_columns(self, table: str) -> List[str]:
        if not self.conn:
            return []
        return [desc[0] for desc in
                self.conn.execute(f"SELECT * FROM {table} LIMIT 0").description]
