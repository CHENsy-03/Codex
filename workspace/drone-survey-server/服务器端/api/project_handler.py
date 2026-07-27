# -*- coding: utf-8 -*-
import time, uuid
_projects = {}
def create_project(body):
    pid = f"P{int(time.time())}"
    _projects[pid] = {"project_id": pid, "project_name": body.get("project_name",""),
        "location": body.get("location",""), "operator": body.get("operator",""),
        "description": body.get("description",""), "status": "active",
        "created_at": int(time.time())}
    return 0, "success", {"project_id": pid}
def get_project(pid):
    if pid in _projects:
        return 0, "success", _projects[pid]
    return 1002, "project not found", None
def list_projects():
    return 0, "success", list(_projects.values())
