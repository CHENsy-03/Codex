"""
Backend Manager - manages Go ExamSystem.exe lifecycle.
Auto-starts backend when GUI launches, stops when GUI exits.
"""

from __future__ import annotations

import subprocess
import sys
import time
import os
import atexit
import urllib.request
import urllib.error


class BackendManager:
    """Manages the Go backend process lifecycle."""

    def __init__(self, exe_path: str = None,
                 questions_path: str = None,
                 base_url: str = "http://localhost:8080",
                 timeout: int = 15):
        self.base_url = base_url.rstrip("/")
        self.timeout = timeout
        self.process: subprocess.Popen | None = None

        if exe_path is None:
            exe_path = self._find_exe()
        self.exe_path = exe_path
        self.questions_path = questions_path or self._find_questions()

        atexit.register(self.stop)


    def _find_exe(self) -> str | None:
        """Find backend/ExamSystem.exe relative to app location."""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..", "release")
        for name in ("ExamSystem.exe", "exam_system.exe"):
            for sub in ("backend", ""):
                p = os.path.join(base, sub, name) if sub else os.path.join(base, name)
                if os.path.exists(p):
                    return os.path.abspath(p)
        return None

    def _find_questions(self) -> str | None:
        """Find data/questions/ relative to app location."""
        if getattr(sys, "frozen", False):
            base = os.path.dirname(sys.executable)
        else:
            base = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "..")
        qdir = os.path.join(base, "data", "questions")
        if os.path.isdir(qdir):
            for f in os.listdir(qdir):
                if f.endswith(".json"):
                    return os.path.abspath(qdir)
        for name in ("default.json", "questions.json"):
            p = os.path.join(base, "data", name)
            if os.path.exists(p):
                return os.path.abspath(p)
        return None

    def is_running(self) -> bool:
        """Check if the backend health endpoint responds."""
        try:
            r = urllib.request.urlopen(f"{self.base_url}/health", timeout=2)
            return r.status == 200
        except (urllib.error.URLError, urllib.error.HTTPError, OSError):
            return False

    def _kill_orphaned(self) -> None:
        try:
            subprocess.run("taskkill /F /IM ExamSystem.exe 2>nul", shell=True,
                          capture_output=True, timeout=5)
            time.sleep(0.5)
        except Exception:
            pass

    def start(self) -> bool:
        """Start backend. Returns True if running."""
        if self.is_running():
            if self.process and self.process.poll() is None:
                return True
            self._kill_orphaned()
        if not self.exe_path or not os.path.exists(self.exe_path):
            return False
        try:
            flags = 0
            if sys.platform == "win32":
                try:
                    flags = subprocess.CREATE_NO_WINDOW
                except AttributeError:
                    flags = 0
            args = [self.exe_path]
            if self.questions_path:
                args += ["-questions", self.questions_path]
            self.process = subprocess.Popen(args, stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL, creationflags=flags,
                cwd=os.path.dirname(self.exe_path))
        except Exception:
            return False
        deadline = time.time() + self.timeout
        while time.time() < deadline:
            if self.is_running():
                return True
            time.sleep(0.5)
        self.stop()
        return False

    def stop(self) -> None:
        """Stop the backend process."""
        if self.process and self.process.poll() is None:
            try:
                self.process.terminate()
                self.process.wait(timeout=5)
            except Exception:
                try:
                    self.process.kill()
                    self.process.wait(timeout=3)
                except Exception:
                    pass
        self.process = None

    def __enter__(self):
        self.start()
        return self

    def __exit__(self, *args):
        self.stop()
