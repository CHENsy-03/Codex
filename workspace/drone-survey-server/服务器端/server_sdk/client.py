# -*- coding: utf-8 -*-
"""V2.1 Python SDK Client"""
import json, urllib.request, urllib.error, threading, time
from typing import Optional, Dict, Any
class UavClient:
    def __init__(self, base_url="http://127.0.0.1:8080", token=None):
        self.base_url = base_url.rstrip("/")
        self.token = token
    def _req(self, method, path, body=None):
        url = f"{self.base_url}{path}"
        data = json.dumps(body).encode("utf-8") if body else None
        req = urllib.request.Request(url, data=data, method=method)
        req.add_header("Content-Type", "application/json")
        if self.token:
            req.add_header("Authorization", f"Bearer {self.token}")
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                return json.loads(resp.read().decode("utf-8"))
        except urllib.error.HTTPError as e:
            return json.loads(e.read().decode("utf-8"))
    def login(self, username, password):
        r = self._req("POST", "/api/v1/auth/login", {"username": username, "password": password})
        if r.get("code") == 0:
            self.token = r["data"]["token"]
        return r
    def create_project(self, name, location, operator, description=""):
        return self._req("POST", "/api/v1/project/create",
                         {"project_name": name, "location": location,
                          "operator": operator, "description": description})
    def get_project(self, pid):
        return self._req("GET", f"/api/v1/project/{pid}")
    def list_projects(self):
        return self._req("GET", "/api/v1/project/list")
    def register_device(self, device_id, device_type="GNSS", model=""):
        return self._req("POST", "/api/v1/device/register",
                         {"device_id": device_id, "type": device_type, "model": model})
    def device_status(self, device_id):
        return self._req("GET", f"/api/v1/device/status/{device_id}")
    def device_list(self):
        return self._req("GET", "/api/v1/device/list")
    def start_task(self, device_id, project_id, duration=3600):
        return self._req("POST", "/api/v1/task/start",
                         {"device_id": device_id, "project_id": project_id, "duration": duration})
    def task_status(self, task_id):
        return self._req("GET", f"/api/v1/task/status/{task_id}")
    def position_latest(self, device_id):
        return self._req("GET", f"/api/v1/position/latest/{device_id}")
    def result_get(self, project_id):
        return self._req("GET", f"/api/v1/result/{project_id}")
