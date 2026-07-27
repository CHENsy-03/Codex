"""
【已弃用】此模块由 Go 引擎替代，不再被生产代码引用。

评分逻辑已迁移至：
  go/internal/engine/session.go   会话提交评分
  go/internal/engine/exam.go      记录与结果类型

所有考试逻辑统一由 Go 后端处理，Python 端仅负责界面显示与 HTTP 通信。
"""

"""
考试引擎模块 —— 管理答题状态、自动评分。
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Optional

from question_parser import Question


@dataclass
class AnswerRecord:
    """单题的作答记录。"""
    question: Question
    chosen: Optional[str]
    is_correct: bool = False
    earned_score: int = 0


@dataclass
class ExamResult:
    """一次交卷的完整结果。"""
    total_score: int = 0
    earned_score: int = 0
    correct_count: int = 0
    total_count: int = 0
    records: list[AnswerRecord] = field(default_factory=list)


class ExamEngine:
    """考试核心逻辑：加载题目、记录作答、评分。"""

    def __init__(self) -> None:
        self.questions: list[Question] = []
        self.question_map: dict[int, Question] = {}
        self._answers: dict[int, Optional[str]] = {}
        self._result: Optional[ExamResult] = None

    def load_questions(self, questions: list[Question]) -> None:
        self.questions = list(questions)
        self.reset()
        self.question_map = {q.id: q for q in questions}

    def get_question_count(self) -> int:
        return len(self.questions)

    def get_total_score(self) -> int:
        return sum(q.score for q in self.questions)

    def reset(self) -> None:
        self.question_map.clear()
        self._answers = {}
        self._result = None

    def get_question(self, qid: int) -> Optional[Question]:
        return self.question_map.get(qid)

    def answer(self, qid: int, choice: str) -> None:
        q = self.get_question(qid)
        if q is None:
            raise ValueError(f"question #{qid} not found")
        if choice not in q.options:
            raise ValueError(f"invalid choice for question #{qid}: {choice!r}")
        self._answers[qid] = choice

    def get_answer(self, qid: int) -> Optional[str]:
        return self._answers.get(qid)

    def is_all_answered(self) -> bool:
        return all(q.id in self._answers for q in self.questions)

    def get_unanswered_count(self) -> int:
        total = len(self.questions)
        answered = sum(1 for q in self.questions if q.id in self._answers)
        return total - answered

    def submit(self) -> ExamResult:
        if not self.questions:
            raise RuntimeError("No questions loaded")
        if self._result is not None:
            return self._result
        records: list[AnswerRecord] = []
        earned = 0
        correct_count = 0
        for q in self.questions:
            chosen = self._answers.get(q.id)
            if q.type == "multiple":
                correct = chosen is not None and set(chosen) == set(q.answer)
            else:
                correct = (chosen == q.answer) if chosen else False
            score_earned = q.score if correct else 0
            if correct:
                correct_count += 1
            earned += score_earned
            records.append(AnswerRecord(
                question=q, chosen=chosen,
                is_correct=correct, earned_score=score_earned,
            ))
        self._result = ExamResult(
            total_score=self.get_total_score(),
            earned_score=earned,
            correct_count=correct_count,
            total_count=len(self.questions),
            records=records,
        )
        return self._result

    def get_result(self) -> Optional[ExamResult]:
        return self._result

    def has_result(self) -> bool:
        return self._result is not None
