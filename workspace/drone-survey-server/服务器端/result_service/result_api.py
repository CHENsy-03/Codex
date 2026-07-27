"""结果服务 — HTTP REST 查询接口

4.docx §七 对外查询接口设计：
  GET /result/{device_id}  -> {"device_id":"...", "result": 1|0|-1}
  GET /result/all          -> 全部结果列表
"""
import json, time, os, sys
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse

from .result_store import store
from .schema import ResultRecord

class ResultHandler(BaseHTTPRequestHandler):
    def do_GET(self):
        parsed = urlparse(self.path)
        path = parsed.path.rstrip("/")

        try:
            if path == "/result/all":
                data = store.get_all()
                self._json(200, data)

            elif path.startswith("/result/"):
                device_id = path[len("/result/"):]
                if device_id:
                    result = store.get_or_default(device_id)
                    self._json(200, [result])
                else:
                    self._json(400, {"error": "missing device_id"})
            else:
                self._json(404, {"error": "not found"})
        except Exception as e:
            self._json(500, {"error": str(e)})

    def _json(self, code, data):
        body = json.dumps(data, ensure_ascii=False).encode("utf-8")
        self.send_response(code)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, fmt, *args):
        pass  # Quiet

class ResultAPI:
    def __init__(self, host="0.0.0.0", port=8081):
        self.host = host
        self.port = port
        self._server = None

    def start(self):
        self._server = HTTPServer((self.host, self.port), ResultHandler)
        print(f"Result API running: http://{self.host}:{self.port}/result/")
        self._server.serve_forever()

    def start_in_thread(self):
        import threading
        t = threading.Thread(target=self.start, daemon=True)
        t.start()
        return t

    def stop(self):
        if self._server:
            self._server.shutdown()

api_server = ResultAPI()
