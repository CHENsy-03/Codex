# -*- coding: utf-8 -*-
"""V2.1 REST API Server — clean version"""
import json, time, sys, os, argparse
from http.server import HTTPServer, BaseHTTPRequestHandler
from urllib.parse import urlparse
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from api.response import api_ok, api_err
from api.auth_handler import handle_login, verify_token
from api.project_handler import create_project, get_project, list_projects
from api.handlers import device_register, device_status, device_list, task_start, task_status, position_latest, result_get
from api.survey_handler import process_survey_upload
def _get_db():
    from config.config_loader import ConfigLoader
    from storage.duckdb_manager import DuckDBManager
    c = ConfigLoader.load('config/server.yaml')
    db = DuckDBManager(db_path=c.database.path, memory_limit=c.database.memory_limit, temp_directory=c.database.temp_directory)
    db.connect(); return db, c
def _check_auth(handler):
    auth = handler.headers.get("Authorization", "")
    token = auth[7:] if auth.startswith("Bearer ") else ""
    if not token or not verify_token(token): api_err(1001, "auth required", handler, 401); return False
    return True
LOGIN_HTML = '''<!DOCTYPE html><html><head><meta charset="utf-8"><title>勘测系统</title>
<style>body{font-family:Arial;max-width:500px;margin:40px auto;padding:20px}
h2{color:#1a73e8}.box{background:#f5f5f5;padding:15px;border-radius:8px;margin:10px 0}
input{width:90%;padding:8px;margin:5px 0;border:1px solid #ccc;border-radius:4px}
button{background:#1a73e8;color:#fff;border:none;padding:10px 20px;border-radius:4px;cursor:pointer;margin:5px}
pre{background:#fff;padding:10px;border-radius:4px;font-size:12px;max-height:300px;overflow:auto}
</style></head><body><h2>勘测系统服务器 V2.1</h2>
<div class="box"><h3>登录</h3>
<input id="u" placeholder="用户名" value="admin"><br>
<input id="p" type="password" placeholder="密码" value="admin123"><br>
<button id="btnLogin">登录</button><div id="r"></div></div>
<script>
var _token = null;
document.getElementById("btnLogin").onclick = async function(){
  var u = document.getElementById("u").value;
  var p = document.getElementById("p").value;
  var resp = await fetch("/api/v1/auth/login", {
    method: "POST", headers: {"Content-Type": "application/json"},
    body: JSON.stringify({username: u, password: p})
  });
  var d = await resp.json(); var el = document.getElementById("r");
  if(d.code == 0) {
    _token = d.data.token;
    el.innerHTML = "<b style=color:green>登录成功</b><br>Token: " + _token +
      "<br>有效期: " + Math.floor(d.data.expire/3600) + "时" + Math.floor((d.data.expire%3600)/60) + "分<br>" +
      "<button onclick=testAPI()>测试 /api/v1/project/list</button><br><pre id=apiResult></pre>";
  } else { el.innerHTML = "<b style=color:red>失败:</b> " + d.message; }
};
function testAPI() {
  fetch("/api/v1/project/list", {headers: {"Authorization": "Bearer " + _token}})
    .then(r => r.json())
    .then(d => { document.getElementById("apiResult").innerText = JSON.stringify(d, null, 2); });
}
</script></body></html>'''
class RESTHandler(BaseHTTPRequestHandler):
    def log_message(self, fmt, *args): pass
    def do_OPTIONS(self):
        self.send_response(200)
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "GET,POST,PUT,OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type,Authorization")
        self.end_headers()
    def do_GET(self):
        p = urlparse(self.path); path = p.path.rstrip("/")
        if path == "" or path == "/api/v1":
            self.send_response(200); self.send_header("Content-Type","text/html;charset=utf-8"); self.end_headers()
            self.wfile.write(LOGIN_HTML.encode()); return
        if path == "/api/stats/summary":
            db, _ = _get_db()
            try:
                total = db.count_gnss(); sizes = db.get_table_sizes()
                by_type = db.conn.execute("SELECT msg_type, count(*) FROM gnss_position GROUP BY msg_type").fetchall()
                api_ok({"total_gnss": total, "by_type": dict(by_type), "tables": sizes}, self)
            except Exception as e: api_err(5001, str(e), self, 500)
            finally: db.disconnect()
            return
        if path == "/api/v1/auth/login": return api_err(4001, "use POST", self, 405)
        if not _check_auth(self): return
        if path == "/api/v1/project/list": api_ok(list_projects(), self)
        elif path.startswith("/api/v1/project/"):
            pid = path.split("/")[-1]; code, msg, data = get_project(pid)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        elif path.startswith("/api/v1/device/status/"):
            did = path.split("/")[-1]; code, msg, data = device_status(did)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        elif path == "/api/v1/device/list": api_ok(device_list(), self)
        elif path.startswith("/api/v1/task/status/"):
            tid = path.split("/")[-1]; code, msg, data = task_status(tid)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        elif path.startswith("/api/v1/position/latest/"):
            did = path.split("/")[-1]; code, msg, data = position_latest(did)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        elif path.startswith("/api/v1/result/"):
            pid = path.split("/")[-1]; code, msg, data = result_get(pid)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        else: api_err(4001, "not found", self, 404)
    def do_POST(self):
        p = urlparse(self.path); path = p.path.rstrip("/")
        length = int(self.headers.get("Content-Length", 0))
        try:
            body = json.loads(self.rfile.read(length).decode("utf-8")) if length > 0 else {}
        except (json.JSONDecodeError, UnicodeDecodeError):
            api_err(2001, "invalid JSON format", self, 400); return
        if path == "/api/v1/auth/login":
            code, msg, data = handle_login(body)
            return api_ok(data, self) if code == 0 else api_err(code, msg, self, 401)
        if not _check_auth(self): return
        if path == "/api/v1/project/create": api_ok(create_project(body)[2], self)
        elif path == "/api/v1/device/register": api_ok(device_register(body)[2], self)
        elif path == "/api/v1/task/start": api_ok(task_start(body)[2], self)
        elif path == "/api/v1/survey/upload":
            code, msg, data = process_survey_upload(body)
            api_ok(data, self) if code == 0 else api_err(code, msg, self)
        else: api_err(4001, "not found", self, 404)
def main():
    parser = argparse.ArgumentParser(description="V2.1 REST API Server")
    parser.add_argument("--port", type=int, default=8080); parser.add_argument("--host", default="0.0.0.0")
    args = parser.parse_args()
    HTTPServer((args.host, args.port), RESTHandler).serve_forever()
if __name__ == "__main__": main()
