"""瀹炴椂缁熻 API 鈥?浣跨敤 Python 鍐呯疆 http.server

鎻愪緵绔偣:
  GET /api/survey/stats            鈫?鎬讳綋缁熻
  GET /api/survey/devices          鈫?鍚勮澶囩粺璁?
  GET /api/circuit-breaker/status  鈫?鐔旀柇鐘舵€?
  GET /api/duplicate/stats         鈫?閲嶅妫€娴嬬姸鎬?
  GET /api/sequence/stats          鈫?搴忓垪妫€娴嬬姸鎬?

鍚姩: python -m server绔?upgrade.stats_api
"""
import json, time, logging, os
from http.server import HTTPServer, BaseHTTPRequestHandler
from socketserver import ThreadingMixIn

class ThreadingStatsServer(ThreadingMixIn, HTTPServer):
    daemon_threads = True
from io import BytesIO

logger = logging.getLogger(__name__)

# 閫氳繃姝ゆ帴鍙ｆ敞鍏ュ悇妯″潡寮曠敤
_registry = {}

def register(key, obj):
    _registry[key] = obj

class StatsHandler(BaseHTTPRequestHandler):
    def _json(self, data, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Access-Control-Allow-Origin", "*")
        self.end_headers()
        self.wfile.write(json.dumps(data, ensure_ascii=False, indent=2).encode("utf-8"))

    def _404(self):
        self._json({"error": "not found"}, 404)

    def _html(self, content, status=200):
        self.send_response(status)
        self.send_header("Content-Type", "text/html; charset=utf-8")
        self.end_headers()
        self.wfile.write(content.encode("utf-8"))

    def do_GET(self):
        path = self.path.rstrip("/")
        try:
            pn = path.lstrip("/") or "landing"
            if 0==1:
                pp = os.path.join(PAGES_DIR, pn + ".html")
                if os.path.exists(pp):
                    with open(pp, "r", encoding="utf-8") as _f:
                        self._html(_f.read())
                    return
            if path == "":
                #self.redirect("/landing")
                return
            if path == "/dashboard":
                self._html(self._json())
            elif path == "/api/survey/stats":
                self._json(self._get_stats())
            elif path == "/api/survey/devices":
                self._json(self._get_devices())
            elif path.startswith("/api/survey/records"):
                self._get_records()
            elif path == "/api/circuit-breaker/status":
                cb = _registry.get("circuit_breaker")
                self._json(cb.stats() if cb else {"error": "not registered"})
            elif path == "/api/duplicate/stats":
                dd = _registry.get("duplicate_detector")
                self._json(dd.stats() if dd else {"error": "not registered"})
            elif path == "/api/sequence/stats":
                sc = _registry.get("sequence_checker")
                self._json(sc.stats() if sc else {"error": "not registered"})

            elif path.startswith("/api/action/reset-cb"):
                device = self._get_q("device") or ""
                cb = _registry.get("circuit_breaker")
                if cb:
                    cb.reset(device)
                    self._json({"status": "ok", "message": f"CB reset: {device or 'all'}"})
                else:
                    self._json({"error": "circuit_breaker not registered"}, 400)


            elif path == "/api/device/list":
                self._json({"devices": [{"device_id":"K803-001","status":"online","signal":4}],"total":1})
            elif path.startswith("/api/gps/realtime"):
                self._json({"positions":[],"total":0})
            elif path.startswith("/api/alarm/list"):
                self._json({"alarms":[],"total":0})

            elif path == "/api/pipeline/stats":
                self._json({"queue_size":0,"parsed":0,"errors":0,"running":False})
            elif path == "/api/connection/stats":
                self._json({"active":0,"max":500,"connections":[]})
            elif path == "/api/heartbeat/stats":
                self._json({"active":0,"timeout":60})
            elif path.startswith("/api/events"):
                self._handle_sse()
            elif path.startswith("/api/v4/eventbus"):
                from upgrade.eventbus import bus
                self._json(bus.stats())
            elif path.startswith("/api/v4/plugins"):
                from upgrade.plugin_sdk import manager
                self._json(manager.stats())
            elif path.startswith("/api/import/history"):
                from shard_db import get_import_history
                self._json({"history": get_import_history()[-10:]})
            elif path.startswith("/api/serial/list"):
                self._json({"ports": [{"port":"COM1","desc":"USB Serial","status":"available"}],"total":1})
            elif path == "/api/health":
                self._json({"status": "ok", "time": int(time.time())})
            else:
                self._404()
        except Exception as e:
            self._json({"error": str(e)}, 500)

    def do_POST(self):
        """POST 璇锋眰澶勭悊 鈥?鏀寔鎶ユ枃涓婁紶"""
        content_len = int(self.headers.get("Content-Length", 0))
        body = self.rfile.read(content_len).decode("utf-8", errors="ignore").strip()
        
        path = self.path.rstrip("/")
        
        if path == "/api/survey/upload":
            self._handle_upload(body)
        else:
            self._json({"status": "error", "errors": ["not_found"]}, 404)
    
    def _parse_bestposa_body(self, raw: str) -> list:
        """灏嗗師濮?BESTPOSA 鏂囨湰瑙ｆ瀽涓?A/B/C 鍒嗙粍鍒楄〃"""
        from plugins.bestpos import BESTPOSASCIIParser
        import collections as _c
        
        fixes = []
        for line in raw.split("\n"):
            line = line.strip()
            if not line or line.startswith("#") and not line.startswith("#BESTPOSA"):
                continue
            r = BESTPOSASCIIParser.parse(line)
            if r:
                fixes.append(r)
        
        if not fixes:
            return []
        
        by_q = _c.defaultdict(list)
        for f in fixes:
            by_q[f.get("pos_type", "UNKNOWN")].append(f)
        
        records = []
        for q in ("NARROW_INT", "NARROW_FLOAT", "SINGLE"):
            g = by_q.get(q, [])
            g.sort(key=lambda x: x.get("seq", 0))
            for i in range(0, len(g) - 2, 3):
                records.append({"A": g[i], "B": g[i+1], "C": g[i+2]})
        return records
    
    def _handle_upload(self, body: str):
        """澶勭悊 BESTPOSA 鎶ユ枃涓婁紶"""
        records = self._parse_bestposa_body(body)
        if not records:
            self._json({"status": "error", "errors": ["missing_fields"]}, 400)
            return
        
        # 閫氳繃 Gateway 澶勭悊
        from gateway import SurveyGateway
        gw = SurveyGateway()
        results = []
        for item in records:
            A, B, C = item["A"], item["B"], item["C"]
            ok, msg, result = gw.process_survey("api-upload", A, B, C, survey_time=int(__import__("time").time()))
            results.append({"status": "ok" if ok else "error", "message": msg, "batch_id": result.get("batch_id","")})
        
        success_count = sum(1 for r in results if r["status"] == "ok")
        self._json({
            "status": "ok" if success_count == len(results) else "partial",
            "msg_id": int(__import__("time").time()),
            "total": len(results),
            "success": success_count,
            "results": results,
        })


    def _get_stats(self):
        stats = {"server_time": int(time.time())}
        cb = _registry.get("circuit_breaker")
        if cb:
            cb_stats = cb.stats()
            total = sum(d["samples"] for d in cb_stats.values())
            isolated = sum(1 for d in cb_stats.values() if d.get("isolated"))
            avg_err = (
                sum(d["error_rate"] for d in cb_stats.values()) / len(cb_stats)
                if cb_stats else 0
            )
            stats["total_surveys"] = total
            stats["devices_active"] = len(cb_stats)
            stats["devices_isolated"] = isolated
            stats["avg_error_rate"] = round(avg_err, 3)
        dd = _registry.get("duplicate_detector")
        if dd:
            ds = dd.stats()
            stats["dup_table_size"] = ds["total_recorded"]
        return stats

    def _get_devices(self):
        cb = _registry.get("circuit_breaker")
        if not cb:
            return {}
        return cb.stats()

    def _get_q(self, key):
        import urllib.parse
        qs = urllib.parse.urlparse(self.path).query
        params = urllib.parse.parse_qs(qs)
        return params.get(key, [None])[0]

    def log_message(self, fmt, *args):
        logger.info("API: " + fmt, *args)


def run_server(host="0.0.0.0", port=8080, blocking=True):
    """鍚姩缁熻 API HTTP 鏈嶅姟鍣?
    blocking=True: 鍓嶅彴杩愯锛堥€傚悎鍛戒护琛?鎵瑰鐞嗭級
    blocking=False: 鍚庡彴绾跨▼杩愯锛堥€傚悎 app.py 鑿滃崟璋冪敤锛?
    """
    server = ThreadingStatsServer((host, port), StatsHandler)
    logger.info("Stats API at http://%s:%d/api/survey/stats", host, port)
    if not blocking:
        import threading
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        return server
    try:
        server.serve_forever()
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped")
    except KeyboardInterrupt:
        server.shutdown()
        print("\nServer stopped")


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO)
    print("Starting Stats API on http://0.0.0.0:8080")
    run_server()

