"""TASK-008：常驻 Worker 入口与严格 NDJSON 传输循环测试。

覆盖：
- 导入 worker_main / app.worker_protocol 不导入 PySide6、不创建 QApplication/窗口；
- 真实子进程 hello flush、多请求串行不串线；
- 非法 JSON/空行/顶层非对象/NaN/Infinity/非法 UTF-8 → E_PROTOCOL_INVALID_JSON；
- 缺失或非法 id → E_REQUEST_INVALID（id=null）；
- protocolVersion 2/1.0/true/"1" → E_PROTOCOL_VERSION；
- 未知 operation → E_OPERATION_UNKNOWN；
- stdout 纯净性（每行均为协议 JSON，无日志/BOM/空白行/traceback）；
- shutdown 先返回 TERMINATING 再以退出码 0 退出；
- stdin EOF 以退出码 0 退出且 stdout 无额外响应。

子进程测试：明确超时、finally 终止残留进程、shell=False、
stderr 独立（不合并进 stdout）、不遗留常驻 Python 进程。
"""

import io
import json
import os
import subprocess
import sys
import threading

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import pytest

from app.worker_protocol import (
    E_OPERATION_UNKNOWN,
    E_PROTOCOL_INVALID_JSON,
    E_PROTOCOL_VERSION,
    E_REQUEST_INVALID,
    ENGINE_VERSION,
    PROTOCOL_VERSION,
    handle_raw_line,
    run_worker,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

HELLO_DATA = {
    "protocolVersion": PROTOCOL_VERSION,
    "engineVersion": ENGINE_VERSION,
    "state": "READY",
    "coordinateTypes": ["wgs84", "map_crs", "pixel"],
}

HELLO_REQUEST = {"id": "h-1", "protocolVersion": 1, "operation": "hello"}
SHUTDOWN_REQUEST = {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"}


def _line(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _readline(stream, timeout: float = 10.0) -> bytes:
    result: list = []

    def reader():
        result.append(stream.readline())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError("读取子进程 stdout 超时")
    return result[0]


def _start_worker():
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    return subprocess.Popen(
        [sys.executable, "worker_main.py"],
        cwd=PROJECT_ROOT,
        stdin=subprocess.PIPE,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        env=env,
        shell=False,
    )


def _stop_worker(proc):
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def _send(proc, payload: dict):
    proc.stdin.write(_line(payload))
    proc.stdin.flush()


# --------------------------------------------------------------------------- #
# 导入纯净性
# --------------------------------------------------------------------------- #
def test_import_worker_modules_do_not_import_pyside6():
    code = (
        "import sys\n"
        "import app.worker_protocol\n"
        "import worker_main\n"
        "print('PySide6' in sys.modules)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=30,
        shell=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_import_does_not_create_qapplication_or_window():
    # 在独立子进程中验证：导入协议模块不会创建 QApplication 或窗口
    code = (
        "from PySide6.QtWidgets import QApplication\n"
        "import app.worker_protocol\n"
        "import worker_main\n"
        "print(QApplication.instance() is None)\n"
    )
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=PROJECT_ROOT,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=30,
        shell=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"


# --------------------------------------------------------------------------- #
# 纯函数协议测试
# --------------------------------------------------------------------------- #
def test_hello_response_content_and_shape():
    response, should_exit = handle_raw_line(_line(HELLO_REQUEST))
    assert should_exit is False
    assert set(response.keys()) == {"id", "success", "data"}
    assert response == {"id": "h-1", "success": True, "data": HELLO_DATA}


def test_shutdown_returns_terminating_and_exit_flag():
    response, should_exit = handle_raw_line(_line(SHUTDOWN_REQUEST))
    assert should_exit is True
    assert set(response.keys()) == {"id", "success", "data"}
    assert response == {
        "id": "s-1",
        "success": True,
        "data": {"state": "TERMINATING"},
    }


@pytest.mark.parametrize(
    "raw",
    [
        b"\n",
        b"   \n",
        b"[]\n",
        b"null\n",
        b"true\n",
        b"123\n",
        b'"text"\n',
        b'{"a":NaN}\n',
        b'{"a":Infinity}\n',
        b'{"a":-Infinity}\n',
        b'{"id":\n',
        b"\xff\xfe\x01\n",
    ],
)
def test_invalid_json_variants_return_protocol_invalid_json(raw):
    response, should_exit = handle_raw_line(raw)
    assert should_exit is False
    assert response["success"] is False
    assert response["error"]["code"] == "E_PROTOCOL_INVALID_JSON"
    assert response["id"] is None
    assert set(response.keys()) == {"id", "success", "error"}
    assert set(response["error"].keys()) == {"code", "message"}


@pytest.mark.parametrize(
    "payload",
    [
        {"protocolVersion": 1, "operation": "hello"},
        {"id": 123, "protocolVersion": 1, "operation": "hello"},
        {"id": "", "protocolVersion": 1, "operation": "hello"},
        {"id": None, "protocolVersion": 1, "operation": "hello"},
        {"id": ["x"], "protocolVersion": 1, "operation": "hello"},
    ],
)
def test_missing_or_invalid_id_returns_request_invalid(payload):
    response, should_exit = handle_raw_line(_line(payload))
    assert should_exit is False
    assert response["success"] is False
    assert response["error"]["code"] == "E_REQUEST_INVALID"
    assert response["id"] is None
    assert set(response.keys()) == {"id", "success", "error"}


def test_missing_required_fields_return_request_invalid_with_id():
    response, _ = handle_raw_line(_line({"id": "x", "operation": "hello"}))
    assert response["error"]["code"] == "E_REQUEST_INVALID"
    assert response["id"] == "x"

    response, _ = handle_raw_line(_line({"id": "x", "protocolVersion": 1}))
    assert response["error"]["code"] == "E_REQUEST_INVALID"
    assert response["id"] == "x"

    response, _ = handle_raw_line(
        _line({"id": "x", "protocolVersion": 1, "operation": 5})
    )
    assert response["error"]["code"] == "E_REQUEST_INVALID"
    assert response["id"] == "x"


@pytest.mark.parametrize("version", [2, 1.0, True, "1"])
def test_protocol_version_mismatch(version):
    payload = {"id": "x", "protocolVersion": version, "operation": "hello"}
    response, should_exit = handle_raw_line(_line(payload))
    assert should_exit is False
    assert response["success"] is False
    assert response["error"]["code"] == "E_PROTOCOL_VERSION"
    assert response["id"] == "x"


def test_unknown_operation():
    payload = {"id": "x", "protocolVersion": 1, "operation": "bogus"}
    response, should_exit = handle_raw_line(_line(payload))
    assert should_exit is False
    assert response["success"] is False
    assert response["error"]["code"] == "E_OPERATION_UNKNOWN"
    assert response["id"] == "x"


def test_run_worker_bytesio_loop():
    inp = io.BytesIO()
    out = io.BytesIO()
    err = io.BytesIO()
    inp.write(_line(HELLO_REQUEST))
    inp.write(_line({"id": "bad", "protocolVersion": 1, "operation": "bogus"}))
    inp.write(_line(SHUTDOWN_REQUEST))
    inp.seek(0)

    code = run_worker(inp, out, err)
    assert code == 0
    lines = out.getvalue().split(b"\n")
    assert lines[-1] == b""
    objs = [json.loads(x.decode("utf-8")) for x in lines if x]
    assert [o["id"] for o in objs] == ["h-1", "bad", "s-1"]
    assert objs[0]["success"] is True
    assert objs[1]["error"]["code"] == "E_OPERATION_UNKNOWN"
    assert objs[2]["data"] == {"state": "TERMINATING"}
    assert b"hello" not in err.getvalue().lower()


def test_run_worker_stdin_eof_returns_0_no_output():
    code = run_worker(io.BytesIO(), io.BytesIO(), io.BytesIO())
    assert code == 0


# --------------------------------------------------------------------------- #
# 真实子进程测试
# --------------------------------------------------------------------------- #
def test_subprocess_hello_single_line_flush():
    proc = _start_worker()
    try:
        _send(proc, HELLO_REQUEST)
        line = _readline(proc.stdout)
        assert line.endswith(b"\n")
        obj = json.loads(line.decode("utf-8"))
        assert obj == {"id": "h-1", "success": True, "data": HELLO_DATA}
        # stdin 保持打开，进程仍在运行：证明 flush 生效且只输出一行
        assert proc.poll() is None
        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_subprocess_multiple_hello_no_restart_no_cross_talk():
    proc = _start_worker()
    try:
        ids = ["h-1", "h-2", "h-3"]
        for i in ids:
            _send(proc, {"id": i, "protocolVersion": 1, "operation": "hello"})
        for i in ids:
            line = _readline(proc.stdout)
            obj = json.loads(line.decode("utf-8"))
            assert obj["id"] == i
            assert obj["success"] is True
            assert obj["data"] == HELLO_DATA
        assert proc.poll() is None
        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_invalid_json_then_hello_still_works():
    proc = _start_worker()
    try:
        proc.stdin.write(b"not json at all\n")
        proc.stdin.flush()
        line = _readline(proc.stdout)
        err = json.loads(line.decode("utf-8"))
        assert err["success"] is False
        assert err["error"]["code"] == "E_PROTOCOL_INVALID_JSON"
        assert err["id"] is None

        _send(proc, HELLO_REQUEST)
        line = _readline(proc.stdout)
        ok = json.loads(line.decode("utf-8"))
        assert ok == {"id": "h-1", "success": True, "data": HELLO_DATA}

        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_subprocess_unknown_operation_then_shutdown():
    proc = _start_worker()
    try:
        _send(proc, {"id": "u-1", "protocolVersion": 1, "operation": "bogus"})
        line = _readline(proc.stdout)
        obj = json.loads(line.decode("utf-8"))
        assert obj["id"] == "u-1"
        assert obj["error"]["code"] == "E_OPERATION_UNKNOWN"
        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_stdout_only_protocol_json_no_bom_no_blank_no_logs():
    proc = _start_worker()
    try:
        requests = [
            {"id": "r1", "protocolVersion": 1, "operation": "hello"},
            {"id": "bad", "protocolVersion": 1, "operation": "bogus"},
            {"id": "r2", "protocolVersion": 1, "operation": "hello"},
        ]
        for req in requests:
            _send(proc, req)
        for _ in requests:
            line = _readline(proc.stdout)
            assert line.startswith(b"\xef\xbb\xbf") is False
            assert line != b"\n"
            assert line.endswith(b"\n")
            obj = json.loads(line.decode("utf-8"))
            assert set(obj.keys()) in (
                {"id", "success", "data"},
                {"id", "success", "error"},
            )
        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_subprocess_shutdown_terminating_then_exit_0():
    proc = _start_worker()
    try:
        _send(proc, SHUTDOWN_REQUEST)
        line = _readline(proc.stdout)
        obj = json.loads(line.decode("utf-8"))
        assert obj == {
            "id": "s-1",
            "success": True,
            "data": {"state": "TERMINATING"},
        }
        assert proc.wait(timeout=10) == 0
        assert proc.stdout.read() == b""
    finally:
        _stop_worker(proc)


def test_subprocess_stdin_eof_exits_0_no_extra_output():
    proc = _start_worker()
    try:
        proc.stdin.close()
        assert proc.wait(timeout=10) == 0
        assert proc.stdout.read() == b""
    finally:
        _stop_worker(proc)


def test_stderr_is_separate_and_has_no_request_content():
    proc = _start_worker()
    try:
        _send(proc, {"id": "secret-id-123", "protocolVersion": 1, "operation": "hello"})
        line = _readline(proc.stdout)
        obj = json.loads(line.decode("utf-8"))
        assert obj["success"] is True
        _send(proc, SHUTDOWN_REQUEST)
        assert proc.wait(timeout=10) == 0
        stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
        assert "secret-id-123" not in stderr_text
        assert "hello" not in stderr_text.lower()
        assert "Traceback" not in stderr_text
        assert "Traceback" not in proc.stdout.read().decode("utf-8", errors="replace")
    finally:
        _stop_worker(proc)
