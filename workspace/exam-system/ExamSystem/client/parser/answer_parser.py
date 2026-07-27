"""
答案文件解析器 —— 从 .txt 答案文件中提取答案映射。
"""

from __future__ import annotations

import re

from model.question import Question


def parse_answer_file(filepath: str) -> dict[int, str]:
    """解析单独的答案文件（每行格式: "1:A" 或 "1 A"）。"""
    result: dict[int, str] = {}
    for enc in ("utf-8", "gbk", "utf-16"):
        try:
            with open(filepath, encoding=enc) as f:
                for line in f:
                    line = line.strip()
                    if not line:
                        continue
                    m = re.match(r"(\d+)\s*[:：\s]\s*([A-Z])", line)
                    if m:
                        result[int(m.group(1))] = m.group(2)
            return result
        except UnicodeDecodeError:
            continue
    with open(filepath, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line:
                continue
            m = re.match(r"(\d+)\s*[:：\s]\s*([A-Z])", line)
            if m:
                result[int(m.group(1))] = m.group(2)
    return result


def merge_answers(questions: list[Question], answer_map: dict[int, str]) -> list[Question]:
    """用独立答案文件的内容覆盖文档中原有的答案。"""
    for q in questions:
        if q.id in answer_map:
            ans = answer_map[q.id]
            if ans in q.options:
                q.answer = ans
    return questions


def format_questions_preview(questions: list[Question]) -> str:
    """生成题目预览文本（供控制台或日志使用）。"""
    lines = [f"共解析到 {len(questions)} 道题：\n"]
    for q in questions:
        opts = "  ".join(f"{k}. {v}" for k, v in q.options.items())
        lines.append(
            f"#{q.id} [{q.score}分] {q.text[:40]}...  {opts}  -> 答案: {q.answer}"
        )
    return "\n".join(lines)
