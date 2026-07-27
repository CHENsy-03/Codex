# -*- coding: utf-8 -*-
"""V2.1 Unified API Response Format"""
import time, json
from http.server import BaseHTTPRequestHandler
from common.error_code import ErrorCode

def api_response(code=0, message="success", data=None, request_handler=None, http_status=200):
    body = {"code": code, "message": message, "timestamp": int(time.time()), "data": data or {}}
    if request_handler is None:
        return body
    return _send_json(request_handler, body, http_status)

def api_ok(data=None, handler=None):
    return api_response(0, "success", data, handler)

def api_err(code=1000, message="error", handler=None, http_status=400):
    return api_response(code, message, None, handler, http_status)

def _send_json(handler, data, status=200):
    body = json.dumps(data, ensure_ascii=False, default=str).encode("utf-8")
    handler.send_response(status)
    handler.send_header("Content-Type", "application/json; charset=utf-8")
    handler.send_header("Access-Control-Allow-Origin", "*")
    handler.send_header("Content-Length", str(len(body)))
    handler.end_headers()
    handler.wfile.write(body)
