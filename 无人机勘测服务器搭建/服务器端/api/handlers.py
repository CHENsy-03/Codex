# -*- coding: utf-8 -*-
"""V2.1 REST API Handlers - device, task, position, result endpoints."""
import time
_devices = {}; _tasks = {}; _positions = {}; _results = {}
def device_register(body):
    did = body.get("device_id",""); dt = body.get("type","GNSS")
    _devices[did] = {"device_id": did, "type": dt, "model": body.get("model",""),
        "status": "waiting", "online": False, "network": "", "signal": 0,
        "device_token": f"tok_{did}_{int(time.time())}"}
    return 0, "success", {"device_id": did, "device_token": _devices[did]["device_token"]}
def device_status(did):
    if did not in _devices: return 1002, "device not found", None
    return 0, "success", _devices[did]
def device_list():
    return 0, "success", list(_devices.values())
def task_start(body):
    tid = f"T{int(time.time())}"
    _tasks[tid] = {"task_id": tid, "device_id": body.get("device_id",""),
        "project_id": body.get("project_id",""), "duration": body.get("duration",3600),
        "status": "running", "started_at": int(time.time())}
    return 0, "success", {"task_id": tid}
def task_status(tid):
    if tid not in _tasks: return 1002, "task not found", None
    return 0, "success", _tasks[tid]
def position_latest(did):
    p = _positions.get(did)
    if not p: return 1002, "no position data", None
    return 0, "success", p
def position_update(did, lat, lng, hgt, sol="RTK_FIXED"):
    _positions[did] = {"device_id": did, "latitude": lat, "longitude": lng,
        "height": hgt, "solution": sol, "updated_at": int(time.time())}
def result_get(pid):
    r = _results.get(pid)
    if not r: return 1002, "result not found", None
    return 0, "success", r
def result_set(pid, score, message="", status="PASS"):
    _results[pid] = {"project_id": pid, "result": status,
        "score": score, "message": message, "created_at": int(time.time())}
