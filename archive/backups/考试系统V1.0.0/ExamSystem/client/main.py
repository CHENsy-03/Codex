"""离线考试系统 —— 入口模块。"""
from __future__ import annotations

import sys
import os
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

import importlib.util

from core.backend_manager import BackendManager
def _check_deps() -> bool:
    missing: list[str] = []
    for name, import_name in [("python-docx", "docx")]:
        if importlib.util.find_spec(import_name) is None:
            missing.append(name)
    try:
        import tkinter
    except ImportError:
        missing.append("tkinter")
        if importlib.util.find_spec(import_name) is None:
            missing.append(name)
    if missing:
        print("缺少依赖：" + ", ".join(missing))
        print(f"请运行: pip install {' '.join(missing)}")
        input("按 Enter 键退出…")
        return False
    return True


def main() -> None:
    if not _check_deps():
        sys.exit(1)
    from app.exam_app import ExamApp
    bm = BackendManager()
    if not bm.start():
        import tkinter as tk
        from tkinter import messagebox
        root = tk.Tk()
        root.withdraw()
        messagebox.showerror(
            "启动失败",
            "无法启动后端服务 ExamSystem.exe\n\n"
            "请确认 ExamSystem.exe 位于以下位置之一：\n"
            "  - 当前目录\n"
            "  - ExamSystem/\n"
            "  - go/\n"
            "  - EXE文件/"
        )
        root.destroy()
        sys.exit(1)
    app = ExamApp()
    try:
        app.mainloop()
    finally:
        bm.stop()


if __name__ == "__main__":
    main()
