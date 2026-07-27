"""
Word 文档解析器 —— 从 .docx 文件中提取选择题。
"""
from __future__ import annotations
import re
from pathlib import Path
from typing import Optional
from model.question import Question
_RE_Q_NUM = re.compile(r"^(\d+)\s*[.、）)．]\s*(.*)")
_RE_OPT = re.compile(r"^([A-Z])\s*[.、）)．]\s*(.*)")
_RE_ANS = re.compile(r"(?:正确答案|答案|【答案】)\s*[：:]?\s*([A-Z])")
def _detect_type(options: dict[str, str], answer: str) -> str:
    if len(answer) > 1:
        return "multiple"
    keys = list(options.keys())
    if len(keys) == 2:
        vals = {v.lower() for v in options.values()}
        if "true" in vals and "false" in vals:
            return "judge"
        if "对" in vals and "错" in vals:
            return "judge"
    return "single"
def parse_docx(filepath: str, default_score: int = 1) -> list[Question]:
    """解析 Word 文档，返回题目列表。"""
    from docx import Document
    if not Path(filepath).exists():
        raise FileNotFoundError(f"File not found: {filepath}")
    try:
        doc = Document(filepath)
    except Exception:
        raise ValueError("Word file is damaged or invalid")
    paragraphs = [p.text.strip() for p in doc.paragraphs]
    questions: list[Question] = []
    current_text_parts: list[str] = []
    current_options: dict[str, str] = {}
    current_answer: Optional[str] = None
    inside = False
    def _flush() -> None:
        nonlocal inside, current_text_parts, current_options, current_answer
        if not inside:
            return
        if current_options and current_answer:
            q_id = len(questions) + 1
            text = "\n".join(current_text_parts).strip()
            questions.append(
                Question(
                    id=q_id, text=text, options=current_options,
                    answer=current_answer, score=default_score,
                    type=_detect_type(current_options, current_answer),
                )
            )
        inside = False
        current_text_parts = []
        current_options = {}
        current_answer = None
    empty_count = 0
    for para in paragraphs:
        if not para:
            empty_count += 1
            if empty_count >= 2:
                _flush()
            continue
        empty_count = 0
        m_q = _RE_Q_NUM.match(para)
        if m_q:
            _flush()
            inside = True
            current_text_parts.append(m_q.group(2))
            continue
        m_o = _RE_OPT.match(para)
        if m_o and inside:
            key, val = m_o.group(1), m_o.group(2)
            current_options[key] = val
            continue
        m_a = _RE_ANS.search(para)
        if m_a and inside:
            current_answer = m_a.group(1)
            continue
        if inside:
            current_text_parts.append(para)
    _flush()
    return questions
