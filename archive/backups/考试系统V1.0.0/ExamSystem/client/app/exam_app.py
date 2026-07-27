"""
离线考试小程序 —— 基于 Tkinter 的桌面 GUI。
"""

from __future__ import annotations

import tkinter as tk
from tkinter import ttk, messagebox, filedialog
from typing import Optional

from utils.config import *
from model.question import Question
from parser.docx_parser import parse_docx
from parser.answer_parser import parse_answer_file, merge_answers
from core.client import ExamClient
from utils.ui import bind_mousewheel, unbind_mousewheel
from dataclasses import dataclass


@dataclass
class _QInfo:
    """题目摘要——答题记录中的题目信息"""
    id: int
    text: str
    options: dict
    answer: str
    score: int


@dataclass
class _AnswerRec:
    """单题答题记录"""
    question: _QInfo
    chosen: str
    is_correct: bool
    earned_score: int


@dataclass
class _ResultData:
    """考试结果"""
    total_score: int
    earned_score: int
    correct_count: int
    total_count: int
    records: list


# ═══════════════════════════════════════════════════════════════
#  主应用
# ═══════════════════════════════════════════════════════════════

class ExamApp(tk.Tk):
    def __init__(self) -> None:
        super().__init__()
        self.title("离线考试系统")
        self.geometry(WINDOW_SIZE)
        self.minsize(WINDOW_MIN_W, WINDOW_MIN_H)
        self.configure(bg=COLOR_BG)
        self.client = ExamClient()
        self.imported_questions: list[Question] = []
        self._current_frame: Optional[tk.Frame] = None
        self.exam_result_data: Optional[dict] = None
        self._show_import_view()

    def _switch_to(self, frame_class: type, **kw) -> None:
        if self._current_frame:
            self._current_frame.destroy()
        self._current_frame = frame_class(self, **kw)
        self._current_frame.pack(fill="both", expand=True)

    def _show_import_view(self) -> None:
        self._switch_to(ImportView)

    def _show_exam_view(self) -> None:
        self._switch_to(ExamView)

    def _show_result_view(self) -> None:
        self._switch_to(ResultView)


# ═══════════════════════════════════════════════════════════════
#  导入页面
# ═══════════════════════════════════════════════════════════════

class ImportView(tk.Frame):
    def __init__(self, master: ExamApp) -> None:
        super().__init__(master, bg=COLOR_BG)
        self.master_app = master
        self._create_widgets()
        self.after(100, self._try_auto_load)

    def _create_widgets(self) -> None:
        tk.Label(self, text="导入题库", font=FONT_TITLE,
                 bg=COLOR_BG, fg=COLOR_PRIMARY).pack(pady=(30, 10))
        file_frame = tk.Frame(self, bg=COLOR_BG)
        file_frame.pack(fill="x", padx=60, pady=5)
        tk.Label(file_frame, text="Word 题库文件：", font=FONT_BODY,
                 bg=COLOR_BG).pack(side="left")
        self._file_path_var = tk.StringVar()
        tk.Entry(file_frame, textvariable=self._file_path_var,
                 font=FONT_BODY, width=50).pack(side="left", padx=5)
        tk.Button(file_frame, text="浏览...", font=FONT_BODY,
                  command=self._browse_file).pack(side="left", padx=2)
        ans_frame = tk.Frame(self, bg=COLOR_BG)
        ans_frame.pack(fill="x", padx=60, pady=5)
        tk.Label(ans_frame, text="答案文件（可选）：", font=FONT_BODY,
                 bg=COLOR_BG).pack(side="left")
        self._ans_path_var = tk.StringVar()
        tk.Entry(ans_frame, textvariable=self._ans_path_var,
                 font=FONT_BODY, width=50).pack(side="left", padx=5)
        tk.Button(ans_frame, text="浏览...", font=FONT_BODY,
                  command=self._browse_answer_file).pack(side="left", padx=2)
        score_frame = tk.Frame(self, bg=COLOR_BG)
        score_frame.pack(fill="x", padx=60, pady=5)
        tk.Label(score_frame, text="每题默认分值：", font=FONT_BODY,
                 bg=COLOR_BG).pack(side="left")
        self._score_var = tk.IntVar(value=1)
        tk.Spinbox(score_frame, from_=1, to=100,
                   textvariable=self._score_var, width=5,
                   font=FONT_BODY).pack(side="left", padx=5)
        tk.Button(self, text="解析题库", font=("微软雅黑", 11, "bold"),
                  bg=COLOR_PRIMARY, fg="white",
                  command=self._parse_questions).pack(pady=15)
        tk.Label(self, text="题目预览：", font=FONT_HEADING,
                 bg=COLOR_BG, anchor="w").pack(fill="x", padx=60)
        cols = ("id", "text", "answer", "score")
        self._tree = ttk.Treeview(self, columns=cols, show="headings",
                                  height=10, selectmode="browse")
        self._tree.heading("id", text="题号")
        self._tree.heading("text", text="题目（前40字）")
        self._tree.heading("answer", text="答案")
        self._tree.heading("score", text="分值")
        self._tree.column("id", width=60, anchor="center")
        self._tree.column("text", width=500)
        self._tree.column("answer", width=80, anchor="center")
        self._tree.column("score", width=80, anchor="center")
        sb = ttk.Scrollbar(self, orient="vertical", command=self._tree.yview)
        self._tree.configure(yscrollcommand=sb.set)
        self._tree.pack(side="left", fill="both", expand=True,
                        padx=(60, 0), pady=5)
        sb.pack(side="left", fill="y", padx=(0, 60), pady=5)
        self._tree.bind("<Double-1>", self._edit_score)
        bottom = tk.Frame(self, bg=COLOR_BG)
        bottom.pack(fill="x", padx=60, pady=15)
        self._status_label = tk.Label(bottom, text="请选择 Word 题库文件",
                                      font=FONT_BODY, bg=COLOR_BG,
                                      fg=COLOR_SUBTEXT)
        self._status_label.pack(side="left")
        self._start_btn = tk.Button(bottom, text="开始考试",
                                    font=("微软雅黑", 12, "bold"),
                                    bg=COLOR_SUCCESS, fg="white",
                                    state="disabled",
                                    command=self._start_exam)
        self._start_btn.pack(side="right")
    def _try_auto_load(self) -> None:
        """自动加载安装目录下的题库文件。"""
        import json, os, sys, glob
        search_dirs = []
        if getattr(sys, "frozen", False):
            search_dirs.append(os.path.dirname(sys.executable))
        else:
            sd = os.path.dirname(os.path.abspath(__file__))
            search_dirs.extend([sd, os.path.join(sd, "..", "..")])
        for base in search_dirs:
            qdir = os.path.join(base, "data", "questions")
            if os.path.isdir(qdir):
                jfs = glob.glob(os.path.join(qdir, "*.json"))
                if jfs:
                    self._load_from_json_dir(qdir)
                    return
        self._status_label.config(text="未找到已保存的题库，请导入 Word 文件", fg=COLOR_SUBTEXT)

    def _load_from_json_dir(self, qdir: str) -> None:
        """从 JSON 文件加载题目。"""
        import json, os, glob
        questions = []
        for fpath in sorted(glob.glob(os.path.join(qdir, "*.json"))):
            try:
                with open(fpath, encoding="utf-8") as f:
                    data = json.load(f)
                items = data.get("questions", data) if isinstance(data, dict) else data
                for item in items:
                    q = Question(
                        id=item["id"],
                        text=item["text"],
                        options=item["options"],
                        answer=item["answer"],
                        score=item.get("score", 1),
                        type=item.get("type", "single"),
                    )
                    questions.append(q)
            except Exception:
                pass
        if not questions:
            return
        for i, q in enumerate(questions, 1):
            q.id = i
        self.master_app.imported_questions = questions
        self._populate_preview(questions)
        self._refresh_total_score()
        self._start_btn.config(state="normal")
        self._status_label.config(text=f"已自动加载题库: {len(questions)} 道题", fg=COLOR_SUCCESS)

    def _browse_file(self) -> None:
        p = filedialog.askopenfilename(
            title="选择 Word 题库文件",
            filetypes=[("Word 文档", "*.docx"), ("所有文件", "*.*")])
        if p:
            self._file_path_var.set(p)

    def _browse_answer_file(self) -> None:
        p = filedialog.askopenfilename(
            title="选择答案文件",
            filetypes=[("文本文件", "*.txt"), ("所有文件", "*.*")])
        if p:
            self._ans_path_var.set(p)

    def _parse_questions(self) -> None:
        path = self._file_path_var.get().strip()
        if not path:
            messagebox.showwarning("提示", "请先选择题库文件")
            return
        try:
            questions = parse_docx(path, default_score=self._score_var.get())
            ans_path = self._ans_path_var.get().strip()
            if ans_path:
                questions = merge_answers(questions, parse_answer_file(ans_path))
            if not questions:
                messagebox.showwarning("解析结果", "未从文件中解析到有效题目。")
                return
            self.master_app.imported_questions = questions
            self._populate_preview(questions)
            self._refresh_total_score()
            self._start_btn.config(state="normal")
        except Exception as e:
            messagebox.showerror("解析失败", f"无法解析文件：\n{e}")
            self._status_label.config(text="解析失败", fg=COLOR_DANGER)

    def _populate_preview(self, questions: list[Question]) -> None:
        self._tree.selection_remove(self._tree.selection())
        self._tree.delete(*self._tree.get_children())
        if not questions:
            return
        info = self._tree.pack_info()
        self._tree.pack_forget()
        for q in questions:
            preview = (q.text[:40] + "...") if len(q.text) > 40 else q.text
            self._tree.insert("", "end",
                              values=(q.id, preview, q.answer, q.score),
                              iid=str(q.id))
        self._tree.pack(info)

    def _refresh_total_score(self) -> None:
        total = sum(q.score for q in self.master_app.imported_questions)
        self._status_label.config(text=f"总分：{total} 分", fg=COLOR_SUCCESS)

    def _edit_score(self, _event) -> None:
        sel = self._tree.selection()
        if not sel:
            return
        vals = self._tree.item(sel[0], "values")
        if not vals:
            return
        ScoreEditDialog(self, int(vals[0]), int(vals[3]) if vals[3] else 1,
                        self.master_app.imported_questions, self._tree)

    def _start_exam(self) -> None:
        qs = self.master_app.imported_questions
        if not qs:
            messagebox.showwarning("提示", "题库为空，请先解析题目")
            return
        result = self.master_app.client.load_questions([q.to_dict() for q in qs])
        if isinstance(result, dict) and "error" in result:
            messagebox.showerror("上传失败", f"导入题目到考试引擎失败：{result.get('detail', '未知错误')}")
            return
        self.master_app._show_exam_view()


class ScoreEditDialog(tk.Toplevel):
    def __init__(self, parent: tk.Frame, qid: int, current: int,
                 questions: list[Question], tree: ttk.Treeview) -> None:
        super().__init__(parent)
        self.title(f"修改题 #{qid} 分值")
        self.geometry("300x120")
        self.resizable(False, False)
        self.transient(parent)
        self.grab_set()
        self.questions = questions
        self.qid = qid
        self.tree = tree
        tk.Label(self, text=f"题目 #{qid} 的分值：",
                 font=FONT_BODY).pack(pady=(15, 5))
        self._var = tk.IntVar(value=current)
        tk.Spinbox(self, from_=1, to=100, textvariable=self._var,
                   width=8, font=FONT_BODY).pack()
        tk.Button(self, text="确定", command=self._confirm).pack(pady=10)

    def _confirm(self) -> None:
        new_score = self._var.get()
        q = next(q for q in self.questions if q.id == self.qid)
        q.score = new_score
        self.tree.item(str(self.qid), values=(q.id,
                        (q.text[:40] + "...") if len(q.text) > 40 else q.text,
                        q.answer, q.score))
        self.master._refresh_total_score()
        self.destroy()


# ═══════════════════════════════════════════════════════════════
#  考试页面（逐题显示）
# ═══════════════════════════════════════════════════════════════

class ExamView(tk.Frame):
    def __init__(self, master: ExamApp) -> None:
        super().__init__(master, bg=COLOR_BG)
        self.master_app = master
        self.current_index = 0
        self.var: Optional[tk.StringVar] = None
        self._current_card: Optional[tk.Frame] = None
        self.answers: dict[int, str] = {}
        self.page_cache: dict[int, tk.Frame] = {}
        self.page_vars: dict[int, tk.StringVar] = {}
        self.session_id = self.master_app.client.start()
        self._create_widgets()
        self.show_question()

    def _create_widgets(self) -> None:
        questions = self.master_app.imported_questions
        if not questions:
            return
        top = tk.Frame(self, bg=COLOR_PRIMARY, height=50)
        top.pack(fill="x")
        top.pack_propagate(False)
        tk.Label(top, text="答题", font=FONT_TITLE,
                 bg=COLOR_PRIMARY, fg="white").pack(side="left", padx=20)
        self.progress = tk.Label(top, text="", font=FONT_BODY,
                                        bg=COLOR_PRIMARY, fg="white")
        self.progress.pack(side="right", padx=20)
        self.question_frame = tk.Frame(self, bg=COLOR_BG)
        self.question_frame.pack(fill="both", expand=True, padx=40, pady=10)
        bottom = tk.Frame(self, bg=COLOR_BG)
        bottom.pack(fill="x", padx=40, pady=(5, 20))
        self._prev_btn = tk.Button(bottom, text="上一题",
                                   font=FONT_BODY, command=self.previous_question)
        self._prev_btn.pack(side="left")
        self._next_btn = tk.Button(bottom, text="下一题",
                                   font=FONT_BODY, command=self.next_question)
        self._next_btn.pack(side="left", padx=10)
        self.next_btn = self._next_btn
        self._progress_text = tk.Label(bottom, text="", font=FONT_BODY,
                                       bg=COLOR_BG, fg=COLOR_TEXT)
        self._progress_text.pack(side="left", expand=True)
        self._unanswered_label = tk.Label(bottom, text="", font=FONT_BODY,
                                          bg=COLOR_BG, fg=COLOR_SUBTEXT)
        self._unanswered_label.pack(side="right", padx=5)
        self.status = tk.Label(bottom, text="", font=FONT_BODY,
                               bg=COLOR_BG, fg=COLOR_SUBTEXT)
        self.status.pack(side="right", padx=5)
        tk.Button(bottom, text="提交试卷", font=("微软雅黑", 12, "bold"),
                  bg=COLOR_PRIMARY, fg="white",
                  command=self._confirm_submit).pack(side="right")

    def show_question(self) -> None:
        # cached
        if hasattr(self, '_current_card') and self._current_card is not None:
            self._current_card.pack_forget()
        index = self.current_index
        if index not in self.page_cache:
            self.build_question(index)
        card = self.page_cache[index]
        card.pack(fill="x", pady=20)
        self._current_card = card
        self.var = self.page_vars[index]
        total = len(self.master_app.imported_questions)
        self.progress.config(text=f"{self.current_index+1}/{total}")
        self._progress_text.config(text=f"第 {self.current_index+1} 题 / 共 {total} 题")
        self._prev_btn.config(state="normal" if self.current_index > 0 else "disabled")
        if self.current_index >= total - 1:
            self.next_btn.config(text="提交试卷", command=self._confirm_submit)
        else:
            self.next_btn.config(text="下一题", command=self.next_question)
        self._update_progress()
        self.after(50, self.preload)
        return

    def _on_answer(self, q: Question, var: tk.StringVar) -> None:
        choice = var.get()
        self.answers[q.id] = choice
        if choice and self.session_id:
            self.master_app.client.answer(q.id, choice, self.session_id)
        self._update_progress()

    def _update_progress(self) -> None:
        ua = len(self.master_app.imported_questions) - sum(1 for q in self.master_app.imported_questions if self.answers.get(q.id))
        if ua > 0:
            self._unanswered_label.config(text=f"未答 {ua} 题", fg="#E67E22")
        else:
            self._unanswered_label.config(text="已全部作答", fg=COLOR_SUCCESS)

    def update_unanswered(self) -> None:
        count = len(self.master_app.imported_questions) - len(self.answers)
        self.status.config(text=f"还有 {count} 题未作答")

    def build_question(self, index: int) -> None:
        q = self.master_app.imported_questions[index]
        card = tk.Frame(self.question_frame, bg=COLOR_CARD)
        tk.Label(card, text=f"第 {q.id} 题 ({q.score}分)",
                 font=("微软雅黑", 18)).pack()
        q_lbl = tk.Label(card, text=q.text,
                 wraplength=900, justify="left")
        q_lbl.pack(fill="x")
        def _reflow(evt, lbl=q_lbl):
            w = evt.width - 20
            if w > 100: lbl.config(wraplength=w)
        card.bind("<Configure>", _reflow)
        var = tk.StringVar()
        answer = self.answers.get(q.id)
        if answer:
            var.set(answer)
        for key, value in q.options.items():
            tk.Radiobutton(card,
                text=f"{key}. {value}",
                variable=var, value=key,
                command=lambda q=q, v=var: self._on_answer(q, v)
            ).pack(anchor="w")
        self.page_cache[index] = card
        self.page_vars[index] = var

    def preload(self) -> None:
        total = len(self.master_app.imported_questions)
        need_more = False
        for i in range(self.current_index, min(self.current_index + 4, total)):
            if i not in self.page_cache:
                self.build_question(i)
                need_more = True
        if len(self.page_cache) > 5:
            old_idx = self.current_index - 2
            if old_idx in self.page_cache:
                self.page_cache[old_idx].destroy()
                del self.page_cache[old_idx]
                del self.page_vars[old_idx]
        if need_more:
            self.after(100, self.preload)

    def previous_question(self) -> None:
        if self.current_index > 0:
            self.current_index -= 1
            self.show_question()

    def next_question(self) -> None:
        q = self.master_app.imported_questions[self.current_index]
        choice = self.var.get()
        self.answers[q.id] = choice
        if choice and self.session_id:
            self.master_app.client.answer(q.id, choice, self.session_id)
        self.update_unanswered()
        if self.current_index < len(self.master_app.imported_questions) - 1:
            self.current_index += 1
            self.show_question()
        else:
            self.submit_exam()

    def _confirm_submit(self) -> None:
        ua = len(self.master_app.imported_questions) - sum(1 for q in self.master_app.imported_questions if self.answers.get(q.id))
        if ua > 0:
            if not messagebox.askyesno("确认交卷", f"还有 {ua} 题未作答，确定提交？"):
                return
        else:
            if not messagebox.askyesno("确认交卷", "确定提交？"):
                return
        import traceback
        try:
            result = self.master_app.client.submit(session_id=self.session_id)
            if isinstance(result, dict) and "error" in result:
                messagebox.showerror("提交失败", result.get("detail", "未知错误"))
                return
            self.master_app.exam_result_data = result
            self.master_app._show_result_view()
        except Exception as e:
            messagebox.showerror("交卷失败",
                f"无法连接考试服务器：\n{e}\n\n请确保 Go 后端已启动。")
            traceback.print_exc()

    submit_exam = _confirm_submit

# ═══════════════════════════════════════════════════════════════
#  成绩页面
# ═══════════════════════════════════════════════════════════════

class ResultView(tk.Frame):
    def __init__(self, master: ExamApp) -> None:
        super().__init__(master, bg=COLOR_BG)
        self.master_app = master
        self._canvas: Optional[tk.Canvas] = None
        result_data = master.exam_result_data
        if result_data is None:
            messagebox.showerror("错误", "没有考试结果数据")
            master._show_import_view()
            return
        self.result = _ResultData(
            total_score=result_data["total_score"],
            earned_score=result_data["earned_score"],
            correct_count=result_data["correct_count"],
            total_count=result_data["total_count"],
            records=[]
        )
        for rd in result_data["records"]:
            qi = _QInfo(
                id=rd["id"],
                text=rd["text"],
                options=rd["options"],
                answer=rd.get("answer", ""),
                score=rd["score"],
            )
            rec = _AnswerRec(
                question=qi,
                chosen=rd["chosen"],
                is_correct=rd["is_correct"],
                earned_score=rd["earned_score"],
            )
            self.result.records.append(rec)
        self._create_widgets()

    def _create_widgets(self) -> None:
        r = self.result
        pct = (r.earned_score / r.total_score * 100) if r.total_score > 0 else 0
        tk.Label(self, text="考试成绩", font=FONT_TITLE,
                 bg=COLOR_BG, fg=COLOR_PRIMARY).pack(pady=(30, 10))
        score_card = tk.Frame(self, bg=COLOR_CARD, relief="solid", bd=1)
        score_card.pack(padx=60, pady=10, fill="x")
        fg = COLOR_SUCCESS if pct >= 60 else COLOR_DANGER
        tk.Label(score_card,
                 text=f"{r.earned_score} / {r.total_score}",
                 font=("微软雅黑", 36, "bold"),
                 fg=fg, bg=COLOR_CARD).pack(pady=(15, 0))
        tk.Label(score_card,
                 text=f"正确 {r.correct_count}/{r.total_count} 题  |  得分率 {pct:.1f}%",
                 font=FONT_HEADING, bg=COLOR_CARD,
                 fg=COLOR_TEXT).pack(pady=(0, 15))
        tk.Label(self, text="逐题解析：", font=FONT_HEADING,
                 bg=COLOR_BG, anchor="w").pack(fill="x", padx=60, pady=(10, 0))
        container = tk.Frame(self, bg=COLOR_BG)
        container.pack(fill="both", expand=True, padx=40, pady=5)
        canvas = tk.Canvas(container, bg=COLOR_BG, highlightthickness=0)
        sb = ttk.Scrollbar(container, orient="vertical", command=canvas.yview)
        sf = tk.Frame(canvas, bg=COLOR_BG)
        sf.bind("<Configure>", lambda e: canvas.configure(
            scrollregion=canvas.bbox("all") or "0 0 1 1"))
        canvas.create_window((0, 0), window=sf, anchor="nw")
        bottom = tk.Frame(self, bg=COLOR_BG)
        bottom.pack(fill="x", padx=60, pady=15)
        tk.Button(bottom, text="重新考试", font=("微软雅黑", 11),
                  bg=COLOR_PRIMARY, fg="white",
                  command=self._retry).pack(side="left", padx=5)
        tk.Button(bottom, text="返回首页", font=("微软雅黑", 11),
                  command=self._go_home).pack(side="left", padx=5)
        pg_frame = tk.Frame(self, bg=COLOR_BG)
        pg_frame.pack(fill="x", padx=60, pady=(0, 10))
        self._prev_page_btn = tk.Button(pg_frame, text="上一页",
            font=FONT_BODY, command=self._prev_page)
        self._prev_page_btn.pack(side="left")
        self._page_label = tk.Label(pg_frame, text="", font=FONT_BODY,
            bg=COLOR_BG, fg=COLOR_TEXT)
        self._page_label.pack(side="left", expand=True)
        self._next_page_btn = tk.Button(pg_frame, text="下一页",
            font=FONT_BODY, command=self._next_page)
        self._next_page_btn.pack(side="left")
        canvas.configure(yscrollcommand=sb.set)
        canvas.pack(side="left", fill="both", expand=True)
        sb.pack(side="right", fill="y")
        self._canvas = canvas
        bind_mousewheel(canvas)
        self.page_size = 10
        self.current_page = 0
        self.record_pages: dict[int, list[tk.Frame]] = {}
        self.sf = sf
        self.total_pages = (len(r.records) + self.page_size - 1) // self.page_size
        self.show_page(0)

    def _retry(self) -> None:
        if self._canvas:
            self._canvas.unbind_all("<MouseWheel>")
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")
        self.master_app._show_exam_view()

    def _go_home(self) -> None:
        if self._canvas:
            self._canvas.unbind_all("<MouseWheel>")
            self._canvas.unbind_all("<Button-4>")
            self._canvas.unbind_all("<Button-5>")
        self.master_app._show_import_view()

    def _build_record(self, index: int) -> tk.Frame:
        rec = self.result.records[index]
        q = rec.question
        ok = rec.is_correct
        color = COLOR_SUCCESS if ok else COLOR_DANGER
        icon = "正确" if ok else "错误"
        card = tk.Frame(self.sf, bg=COLOR_CARD, relief="solid", bd=1)
        card.pack(fill="x", pady=6)
        hdr = tk.Frame(card, bg=COLOR_CARD)
        hdr.pack(fill="x", padx=15, pady=(8, 2))
        tk.Label(hdr, text=f"{icon} 第 {q.id} 题（{q.score} 分）",
                 font=FONT_HEADING, bg=COLOR_CARD, fg=color).pack(side="left")
        tk.Label(hdr, text=f"得分: {rec.earned_score}/{q.score}",
                 font=FONT_BODY, bg=COLOR_CARD, fg=color).pack(side="right")
        q_lbl = tk.Label(card, text=q.text, font=FONT_BODY,
                 bg=COLOR_CARD, fg=COLOR_TEXT, wraplength=400, justify="left")
        q_lbl.pack(fill="x", padx=15, pady=(0, 4))
        def _reflow2(evt, lbl=q_lbl):
            w = evt.width - 30
            if w > 100: lbl.config(wraplength=w)
        card.bind("<Configure>", _reflow2)
        af = tk.Frame(card, bg=COLOR_CARD)
        af.pack(fill="x", padx=15, pady=(0, 8))
        chosen = rec.chosen or "（未作答）"
        chosen_text = q.options.get(rec.chosen, "") if rec.chosen else ""
        correct_text = q.options.get(q.answer, "")
        tk.Label(af, text=f"你的答案: {chosen}. {chosen_text}",
                 font=FONT_BODY, bg=COLOR_CARD, fg=color).pack(anchor="w")
        if not ok and q.answer:
            tk.Label(af, text=f"正确答案: {q.answer}. {correct_text}",
                     font=FONT_BODY, bg=COLOR_CARD, fg=COLOR_PRIMARY).pack(anchor="w")
        return card

    def show_page(self, page_num: int) -> None:
        self.current_page = page_num
        start = page_num * self.page_size
        end = min(start + self.page_size, len(self.result.records))
        
        # Remove old page records from the scrollable frame
        for widgets in self.sf.winfo_children():
            widgets.destroy()
        
        # Evict old cache: keep only current and adjacent pages
        max_pages = 3
        old_keys = [k for k in self.record_pages if abs(k - page_num) >= max_pages]
        for k in old_keys:
            for f in self.record_pages[k]:
                try:
                    f.destroy()
                except Exception:
                    pass
            del self.record_pages[k]
        
        # Build current page records
        frames: list[tk.Frame] = []
        for i in range(start, end):
            card = self._build_record(i)
            frames.append(card)
        self.record_pages[page_num] = frames
        
        # Update navigation
        total = self.total_pages
        self._page_label.config(
            text=f"第 {page_num+1}/{total} 页（{start+1}-{end} 题）")
        self._prev_page_btn.config(state="normal" if page_num > 0 else "disabled")
        self._next_page_btn.config(
            state="normal" if page_num < total - 1 else "disabled")
        # Update scrollregion
        self.after_idle(lambda: self._canvas.config(
            scrollregion=self._canvas.bbox("all") or "0 0 1 1"))

    def _prev_page(self) -> None:
        if self.current_page > 0:
            self.show_page(self.current_page - 1)

    def _next_page(self) -> None:
        if self.current_page < self.total_pages - 1:
            self.show_page(self.current_page + 1)