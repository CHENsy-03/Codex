"""
题目数据模型 —— 表示一道选择题。
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass
class Question:
    """一道选择题的数据模型。"""
    id: int
    text: str
    options: dict[str, str]
    answer: str
    score: int = 1
    type: str = "single"

    def __post_init__(self) -> None:
        if self.answer not in self.options:
            raise ValueError(
                "题目 {self.id} 的答案 {self.answer!r} 不在选项 {list(self.options)} 中"
            )
        if self.score <= 0:
            raise ValueError(
                "题目 {self.id} 的分值必须为正数, 当前值: {self.score}"
            )
        if self.type not in ("single", "multiple", "judge"):
            raise ValueError(
                "题目 {self.id} 的类型无效: {self.type}"
            )

    def __hash__(self) -> int:
        return hash(self.id)

    def to_dict(self) -> dict:
        return {
            "id": self.id,
            "text": self.text,
            "options": self.options,
            "answer": self.answer,
            "score": self.score,
            "type": self.type,
        }
