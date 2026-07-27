"""
HTTP client for Go exam backend.
Centralizes all API calls to decouple GUI from server address.
"""

from __future__ import annotations

import json
import urllib.request
import urllib.error


class ExamClient:
    """Client for the Go exam backend HTTP API."""

    def __init__(self, base_url: str = "http://localhost:8080", token: str = "Exam2026"):
        self.base_url = base_url.rstrip("/")
        self.token = token

    def _headers(self) -> dict:
        h: dict = {"Content-Type": "application/json"}
        if self.token:
            h["X-Token"] = self.token
        return h

    def _request(self, method: str, path: str, data: dict = None, timeout: int = 10) -> dict | list:
        """Unified HTTP request with error handling."""
        url = f"{self.base_url}{path}"
        body = json.dumps(data).encode("utf-8") if data is not None else None
        req = urllib.request.Request(url, data=body, headers=self._headers(), method=method)
        try:
            resp = urllib.request.urlopen(req, timeout=timeout)
            return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return {"error": f"HTTP {e.code}", "detail": str(e)}
        except urllib.error.URLError as e:
            return {"error": "backend_unavailable", "detail": f"无法连接服务器: {e.reason}"}
        except (OSError, ValueError, json.JSONDecodeError) as e:
            return {"error": "request_failed", "detail": str(e)}

    def submit(self, answers: dict[int, str] = None, session_id: str = "") -> dict:
        """Submit answers and get scoring result."""
        if isinstance(session_id, str) and session_id:
            return self._request("POST", f"/submit?session_id={session_id}", {}, 10)
        data = {str(k): v for k, v in (answers or {}).items()}
        return self._request("POST", "/submit", data, 10)

    def get_questions(self) -> list[dict]:
        """Get all questions (public, no answer field)."""
        result = self._request("GET", "/questions", timeout=10)
        if isinstance(result, list):
            return result

    def load_questions(self, questions: list[dict]) -> dict:
        """Upload imported questions to Go backend for scoring."""
        result = self._request("POST", "/load_questions", questions, 30)
        if isinstance(result, dict) and "error" in result:
            return result
        return result
        return []

    def health_check(self) -> dict:
        """Check server health."""
        return self._request("GET", "/health", timeout=5)

    def start(self) -> str:
        """Start a new exam session and return session_id."""
        result = self._request("POST", "/start", {}, 10)
        if isinstance(result, dict) and "error" in result:
            return ""
        return result.get("session_id", "")

    def load_questions(self, questions: list[dict]) -> dict:
        """Upload imported questions to Go backend for scoring."""
        result = self._request("POST", "/load_questions", questions, 30)
        if isinstance(result, dict) and "error" in result:
            return result
        return result.get("session_id", "")

    def answer(self, qid: int, choice: str, session_id: str = "") -> bool:
        """Send a single answer to the Go backend for tracking."""
        data = {"session_id": session_id, "qid": qid, "choice": choice}
        result = self._request("POST", "/answer", data, 5)
        return "error" not in result