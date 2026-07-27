"""
JSON 导出 —— 将 Question 对象列表导出为 JSON 文件。
"""

from __future__ import annotations

import json
from datetime import datetime

from model.question import Question

VERSION = "1.0"


def export_to_json(questions: list[Question], filepath: str, ensure_ascii: bool = False, indent: int = 2) -> str:
    """将题目列表导出为 JSON 文件。"""
    data = {
        "version": VERSION,
        "create_time": datetime.now().strftime("%Y-%m-%d"),
        "count": len(questions),
        "questions": [q.to_dict() for q in questions],
    }
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=ensure_ascii, indent=indent)
    return filepath


def export_to_json_string(questions: list[Question], ensure_ascii: bool = False, indent: int = 2) -> str:
    """将题目列表导出为 JSON 字符串。"""
    data = {
        "version": VERSION,
        "create_time": datetime.now().strftime("%Y-%m-%d"),
        "count": len(questions),
        "questions": [q.to_dict() for q in questions],
    }
    return json.dumps(data, ensure_ascii=ensure_ascii, indent=indent)
