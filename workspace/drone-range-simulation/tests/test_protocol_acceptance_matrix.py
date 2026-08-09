"""TASK-010：系统化协议验收矩阵测试。

Case ID 分类：TRN / ENV / STA / MAP / PNT / CAL / ERR / LIF。
每个 Case ID 通过参数化 id 或测试函数名映射到稳定 nodeid。
只读验收：不修改生产代码；测试地图全部在临时目录动态生成。
"""

import io
import json
import math
import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from rasterio.crs import CRS
from rasterio.transform import Affine

from app.coordinate_converter import CoordinateConversionError
from app.distance_calculator import DistanceCalculationError, DistanceResult
from app.worker_engine import WorkerEngine, WorkerProtocolError
from app.worker_protocol import (
    E_CALCULATION,
    E_CRS_TRANSFORM,
    E_INTERNAL,
    E_MAP_CRS_MISSING,
    E_MAP_NOT_FOUND,
    E_MAP_NOT_LOADED,
    E_MAP_OPEN_FAILED,
    E_MAP_TRANSFORM_INVALID,
    E_OPERATION_UNKNOWN,
    E_POINT_INVALID,
    E_POINT_OUT_OF_BOUNDS,
    E_POINT_TYPE,
    E_PROTOCOL_INVALID_JSON,
    E_PROTOCOL_VERSION,
    E_REQUEST_INVALID,
    E_SPEED_INVALID,
    E_TIME_LIMIT,
    handle_raw_line,
    run_worker,
)
from protocol_acceptance_helpers import (
    BIG_TRANSFORM,
    GLOBAL_WGS84_TRANSFORM,
    ROTATED_TRANSFORM,
    TRANSFORM,
    assert_error_shape,
    assert_success_shape,
    independent_distance,
    independent_wgs84,
    line,
    make_map,
    map_crs_from_pixel,
    read_response,
    send,
    start_worker,
    stop_worker,
    write_tiff,
)

# --------------------------------------------------------------------------- #
# 请求构造辅助
# --------------------------------------------------------------------------- #
def pixel(col, row):
    return {"type": "pixel", "column": col, "row": row}


def calc_request(point_a, point_b, speed=10, cid="c-1"):
    return {
        "id": cid,
        "protocolVersion": 1,
        "operation": "calculate",
        "pointA": point_a,
        "pointB": point_b,
        "speedMps": speed,
    }


def load_request(path, cid="m-1"):
    return {"id": cid, "protocolVersion": 1, "operation": "load_map", "path": path}


def hello_request(cid="h-1"):
    return {"id": cid, "protocolVersion": 1, "operation": "hello"}


def shutdown_request(cid="s-1"):
    return {"id": cid, "protocolVersion": 1, "operation": "shutdown"}


def _loaded_engine(tmp_path, **kwargs):
    tif = make_map(tmp_path, **kwargs)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_success_shape(resp)
    assert resp["data"]["state"] == "MAP_LOADED"
    return engine, tif


def _wgs84_point(col, row, crs="EPSG:3857", transform=TRANSFORM):
    lon, lat = independent_wgs84(crs, transform, col, row)
    return {"type": "wgs84", "longitude": lon, "latitude": lat}


def _map_crs_point(col, row, transform=TRANSFORM):
    x, y = map_crs_from_pixel(transform, col, row)
    return {"type": "map_crs", "x": x, "y": y}


# --------------------------------------------------------------------------- #
# TRN：传输层
# --------------------------------------------------------------------------- #
TRANSPORT_INVALID_CASES = [
    pytest.param("TRN-001", b"\xff\xfe\x00\n", id="TRN-001"),
    pytest.param("TRN-002", b'{"id":\n', id="TRN-002"),
    pytest.param("TRN-003", b"\n", id="TRN-003"),
    pytest.param("TRN-004", b"   \n", id="TRN-004"),
    pytest.param("TRN-005", b"null\n", id="TRN-005"),
    pytest.param("TRN-006", b"[]\n", id="TRN-006"),
    pytest.param("TRN-007", b'"text"\n', id="TRN-007"),
    pytest.param("TRN-008", b"123\n", id="TRN-008"),
    pytest.param("TRN-009", b"true\n", id="TRN-009"),
    pytest.param("TRN-010", b'{"a":NaN}\n', id="TRN-010"),
    pytest.param("TRN-011", b'{"a":Infinity}\n', id="TRN-011"),
    pytest.param("TRN-012", b'{"a":-Infinity}\n', id="TRN-012"),
]


@pytest.mark.parametrize("case_id,raw", TRANSPORT_INVALID_CASES)
def test_TRN_invalid_json(case_id, raw):
    resp, should_exit = handle_raw_line(raw)
    assert should_exit is False
    assert_error_shape(resp, E_PROTOCOL_INVALID_JSON)
    assert resp["id"] is None


def test_TRN_013_subprocess_hello_single_line_flush():
    proc = start_worker()
    try:
        send(proc, hello_request("h-1"))
        resp = read_response(proc)
        assert_success_shape(resp)
        assert resp["id"] == "h-1"
        assert resp["data"]["state"] == "READY"
        assert proc.poll() is None
        send(proc, shutdown_request())
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


def test_TRN_014_subprocess_stdin_eof_exit_0_no_extra_output():
    proc = start_worker()
    try:
        proc.stdin.close()
        assert proc.wait(timeout=10) == 0
        assert proc.stdout.read() == b""
    finally:
        stop_worker(proc)


def test_TRN_015_subprocess_stdout_only_protocol_json():
    proc = start_worker()
    try:
        send(proc, hello_request("h-1"))
        raw = __import__("protocol_acceptance_helpers").readline(proc.stdout)
        assert raw.startswith(b"\xef\xbb\xbf") is False
        assert raw != b"\n"
        assert raw.endswith(b"\n")
        obj = json.loads(raw.decode("utf-8"))
        assert set(obj.keys()) == {"id", "success", "data"}
        send(proc, shutdown_request())
        assert read_response(proc)["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
        assert proc.stdout.read() == b""
    finally:
        stop_worker(proc)


def test_TRN_016_subprocess_stderr_not_merged_into_stdout():
    proc = start_worker()
    try:
        send(proc, hello_request("h-1"))
        assert read_response(proc)["success"] is True
        send(proc, shutdown_request())
        assert read_response(proc)["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
        stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
        assert "Traceback" not in stderr_text
        assert proc.stdout.read() == b""
    finally:
        stop_worker(proc)


def test_TRN_017_subprocess_shutdown_flush_then_exit():
    proc = start_worker()
    try:
        send(proc, shutdown_request("s-1"))
        resp = read_response(proc)
        assert_success_shape(resp)
        assert resp["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


def test_TRN_018_run_worker_broken_output_pipe_safe_exit():
    class BrokenOutput:
        def write(self, data):
            raise BrokenPipeError("pipe closed")

        def flush(self):
            pass

    code = run_worker(
        io.BytesIO(line(hello_request())),
        BrokenOutput(),
        io.BytesIO(),
    )
    assert code == 0


def test_TRN_019_subprocess_invalid_then_valid_continues():
    proc = start_worker()
    try:
        proc.stdin.write(b"not json\n")
        proc.stdin.flush()
        err = read_response(proc)
        assert_error_shape(err, E_PROTOCOL_INVALID_JSON)
        send(proc, hello_request("h-1"))
        ok = read_response(proc)
        assert_success_shape(ok)
        send(proc, shutdown_request())
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


# --------------------------------------------------------------------------- #
# ENV：公共请求信封
# --------------------------------------------------------------------------- #
ENVELOPE_CASES = [
    pytest.param("ENV-001", {"id": "x", "operation": "hello"}, E_REQUEST_INVALID, "x", id="ENV-001"),
    pytest.param("ENV-002", {"id": "x", "protocolVersion": 2, "operation": "hello"}, E_PROTOCOL_VERSION, "x", id="ENV-002"),
    pytest.param("ENV-003", {"id": "x", "protocolVersion": 1.0, "operation": "hello"}, E_PROTOCOL_VERSION, "x", id="ENV-003"),
    pytest.param("ENV-004", {"id": "x", "protocolVersion": True, "operation": "hello"}, E_PROTOCOL_VERSION, "x", id="ENV-004"),
    pytest.param("ENV-005", {"id": "x", "protocolVersion": "1", "operation": "hello"}, E_PROTOCOL_VERSION, "x", id="ENV-005"),
    pytest.param("ENV-006", {"protocolVersion": 1, "operation": "hello"}, E_REQUEST_INVALID, None, id="ENV-006"),
    pytest.param("ENV-007", {"id": "", "protocolVersion": 1, "operation": "hello"}, E_REQUEST_INVALID, None, id="ENV-007"),
    pytest.param("ENV-008", {"id": 123, "protocolVersion": 1, "operation": "hello"}, E_REQUEST_INVALID, None, id="ENV-008"),
    pytest.param("ENV-009", {"id": "x", "protocolVersion": 1}, E_REQUEST_INVALID, "x", id="ENV-009"),
    pytest.param("ENV-010", {"id": "x", "protocolVersion": 1, "operation": 5}, E_REQUEST_INVALID, "x", id="ENV-010"),
    pytest.param("ENV-011", {"id": "x", "protocolVersion": 1, "operation": "bogus"}, E_OPERATION_UNKNOWN, "x", id="ENV-011"),
]


@pytest.mark.parametrize("case_id,payload,expected_code,expected_id", ENVELOPE_CASES)
def test_ENV_envelope(case_id, payload, expected_code, expected_id):
    resp, should_exit = handle_raw_line(line(payload))
    assert should_exit is False
    assert_error_shape(resp, expected_code)
    assert resp["id"] == expected_id


# --------------------------------------------------------------------------- #
# STA：状态机
# --------------------------------------------------------------------------- #
def test_STA_001_start_ready():
    engine = WorkerEngine()
    assert engine.state == "READY"
    resp, _ = handle_raw_line(line(hello_request()), engine)
    assert_success_shape(resp)
    assert resp["data"]["state"] == "READY"


def test_STA_002_ready_calculate_returns_map_not_loaded_priority():
    engine = WorkerEngine()
    # 即使缺少 pointA/pointB/speedMps，READY 状态也先返回 E_MAP_NOT_LOADED
    resp, _ = handle_raw_line(
        line({"id": "c-1", "protocolVersion": 1, "operation": "calculate"}), engine
    )
    assert_error_shape(resp, E_MAP_NOT_LOADED)
    assert engine.state == "READY"


def test_STA_003_ready_load_success_enters_map_loaded(tmp_path):
    engine, tif = _loaded_engine(tmp_path)
    assert engine.state == "MAP_LOADED"


def test_STA_004_ready_load_fail_stays_ready(tmp_path):
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(bad))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)
    assert engine.state == "READY"


def test_STA_005_map_loaded_hello_returns_map_loaded(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(line(hello_request()), engine)
    assert_success_shape(resp)
    assert resp["data"]["state"] == "MAP_LOADED"


def test_STA_006_map_loaded_calculate_success_stays_map_loaded(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))), engine
    )
    assert_success_shape(resp)
    assert engine.state == "MAP_LOADED"


def test_STA_007_map_loaded_calculate_fail_stays_map_loaded(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0)), engine
    )
    assert_error_shape(resp, E_SPEED_INVALID)
    assert engine.state == "MAP_LOADED"


def test_STA_008_map_loaded_load_success_switches_map(tmp_path):
    engine, _ = _loaded_engine(tmp_path, name="a.tif", transform=TRANSFORM)
    b_tif = make_map(tmp_path, name="b.tif", transform=ROTATED_TRANSFORM)
    resp, _ = handle_raw_line(line(load_request(str(b_tif))), engine)
    assert_success_shape(resp)
    assert resp["data"]["state"] == "MAP_LOADED"
    result = engine.calculate(
        calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))
    )
    expected = independent_distance("EPSG:3857", ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_STA_009_map_loaded_load_fail_keeps_old_map(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    before = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    resp, _ = handle_raw_line(line(load_request(str(bad))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)
    assert engine.state == "MAP_LOADED"
    after = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    assert after == before


def test_STA_010_unknown_operation_state_unchanged(tmp_path):
    engine = WorkerEngine()
    resp, _ = handle_raw_line(
        line({"id": "x", "protocolVersion": 1, "operation": "bogus"}), engine
    )
    assert_error_shape(resp, E_OPERATION_UNKNOWN)
    assert engine.state == "READY"
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line({"id": "x", "protocolVersion": 1, "operation": "bogus"}), engine
    )
    assert_error_shape(resp, E_OPERATION_UNKNOWN)
    assert engine.state == "MAP_LOADED"


def test_STA_011_subprocess_shutdown_terminating_then_exit_0():
    proc = start_worker()
    try:
        send(proc, shutdown_request("s-1"))
        resp = read_response(proc)
        assert_success_shape(resp)
        assert resp["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


def test_STA_012_subprocess_after_shutdown_no_more_processing():
    proc = start_worker()
    try:
        send(proc, shutdown_request("s-1"))
        read_response(proc)
        assert proc.wait(timeout=10) == 0
        # shutdown 后进程已退出，输入不再被处理
        assert proc.poll() == 0
    finally:
        stop_worker(proc)


def test_STA_013_no_extra_protocol_states(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    assert engine.state in {"READY", "MAP_LOADED", "TERMINATING"}
    resp, _ = handle_raw_line(line(hello_request()), engine)
    assert resp["data"]["state"] in {"READY", "MAP_LOADED", "TERMINATING"}
    engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0)))
    assert engine.state in {"READY", "MAP_LOADED", "TERMINATING"}
    with pytest.raises(WorkerProtocolError):
        engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0))
    assert engine.state in {"READY", "MAP_LOADED", "TERMINATING"}


# --------------------------------------------------------------------------- #
# MAP：load_map 与原子替换
# --------------------------------------------------------------------------- #
def test_MAP_001_legal_absolute_tif(tmp_path):
    engine, tif = _loaded_engine(tmp_path)
    assert engine.state == "MAP_LOADED"


def test_MAP_002_legal_absolute_tiff(tmp_path):
    engine, tif = _loaded_engine(tmp_path, name="map.tiff")
    assert engine.state == "MAP_LOADED"


def test_MAP_003_relative_path_request_invalid(tmp_path):
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request("sub/map.tif")), engine)
    assert_error_shape(resp, E_REQUEST_INVALID)


def test_MAP_004_path_missing_request_invalid():
    engine = WorkerEngine()
    resp, _ = handle_raw_line(
        line({"id": "m-1", "protocolVersion": 1, "operation": "load_map"}), engine
    )
    assert_error_shape(resp, E_REQUEST_INVALID)


def test_MAP_005_path_non_string_request_invalid():
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(123)), engine)
    assert_error_shape(resp, E_REQUEST_INVALID)


def test_MAP_006_path_empty_request_invalid():
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request("")), engine)
    assert_error_shape(resp, E_REQUEST_INVALID)


def test_MAP_007_nonexistent_map_not_found(tmp_path):
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tmp_path / "nope.tif"))), engine)
    assert_error_shape(resp, E_MAP_NOT_FOUND)


def test_MAP_008_directory_map_not_found(tmp_path):
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tmp_path))), engine)
    assert_error_shape(resp, E_MAP_NOT_FOUND)


def test_MAP_009_unreadable_map_not_found(tmp_path, monkeypatch):
    tif = make_map(tmp_path)
    monkeypatch.setattr("app.worker_engine.os.access", lambda *a, **k: False)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_NOT_FOUND)


def test_MAP_010_corrupt_tiff_open_failed(tmp_path):
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(bad))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_011_text_fake_tif_open_failed(tmp_path):
    fake = tmp_path / "fake.tif"
    fake.write_text("this is not a tiff", encoding="utf-8")
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(fake))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_012_zip_open_failed(tmp_path):
    zpath = tmp_path / "map.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("inner.tif", b"x")
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(zpath))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_013_zip_bytes_as_tif_open_failed(tmp_path):
    zpath = tmp_path / "real.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("inner.tif", b"x")
    fake = tmp_path / "zipcontent.tif"
    fake.write_bytes(zpath.read_bytes())
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(fake))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_014_geotiff_renamed_non_tiff_ext_open_failed(tmp_path):
    tif = make_map(tmp_path)
    renamed = tmp_path / "map.dat"
    renamed.write_bytes(tif.read_bytes())
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(renamed))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_015_no_crs_crs_missing(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "nocrs.tif"
    write_tiff(tif, data, 3, "uint8", crs=None)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_CRS_MISSING)


def test_MAP_016_degenerate_transform_transform_invalid(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "degenerate.tif"
    write_tiff(
        tif, data, 3, "uint8",
        transform=Affine(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)


def _write_tiff_with_transform(tif, transform_value):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    write_tiff(tif, data, 3, "uint8")
    with rasterio.open(tif, "r+") as ds:
        ds.transform = Affine(1.0, 0.0, 0.0, 0.0, transform_value, 0.0)


def test_MAP_017_nan_transform_real_validator(tmp_path):
    # 真实文件写入 NaN 仿射；生产 _is_valid_transform 直接接收非有限参数
    tif = tmp_path / "nan_transform.tif"
    _write_tiff_with_transform(tif, float("nan"))
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)
    assert resp["id"] == "m-1"
    assert "data" not in resp
    assert engine.state == "READY"
    message = resp["error"]["message"]
    assert "Traceback" not in message and str(tif) not in message


def test_MAP_029_infinity_transform_real_validator(tmp_path):
    tif = tmp_path / "inf_transform.tif"
    _write_tiff_with_transform(tif, float("inf"))
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)
    assert engine.state == "READY"


def test_MAP_030_minus_infinity_transform_real_validator(tmp_path):
    tif = tmp_path / "ninf_transform.tif"
    _write_tiff_with_transform(tif, float("-inf"))
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)
    assert engine.state == "READY"


def test_MAP_031_nonfinite_load_keeps_map_a(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    req = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))
    before = engine.calculate(req)
    tif = tmp_path / "nan_b.tif"
    _write_tiff_with_transform(tif, float("nan"))
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)
    assert engine.state == "MAP_LOADED"
    assert engine.calculate(req) == before


def test_MAP_018_illegal_band_count_open_failed(tmp_path):
    data = np.zeros((2, 8, 8), dtype=np.uint8)
    tif = tmp_path / "two_band.tif"
    write_tiff(tif, data, 2, "uint8")
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)


def test_MAP_019_epsg_crs_string(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    metadata = engine._current_map.metadata
    assert metadata.crs_string == "EPSG:3857"


def test_MAP_020_no_epsg_returns_wkt2(tmp_path):
    custom = CRS.from_proj4(
        "+proj=tmerc +lat_0=0 +lon_0=117 +k=1 +x_0=500000 "
        "+y_0=0 +ellps=WGS84 +units=m +no_defs"
    )
    assert custom.to_epsg() is None
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "custom.tif"
    write_tiff(tif, data, 3, "uint8", crs=custom)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_success_shape(resp)
    assert "EPSG:" not in resp["data"]["crs"]
    assert resp["data"]["crs"].startswith(("PROJCRS", "PROJCS", "GEOGCRS", "GEOGCS"))


def test_MAP_021_load_no_preview(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    assert not hasattr(engine._current_map.metadata, "preview_rgb")


def test_MAP_022_import_worker_no_qapplication():
    code = (
        "from PySide6.QtWidgets import QApplication\n"
        "import app.worker_engine\n"
        "import app.worker_protocol\n"
        "import worker_main\n"
        "print(QApplication.instance() is None)\n"
    )
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=30, shell=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "True"


def test_MAP_023_import_worker_no_pyside6():
    code = (
        "import sys\n"
        "import app.worker_engine\n"
        "import app.worker_protocol\n"
        "import worker_main\n"
        "print('PySide6' in sys.modules)\n"
    )
    import subprocess, sys
    proc = subprocess.run(
        [sys.executable, "-c", code],
        cwd=os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
        capture_output=True, text=True, encoding="utf-8",
        env={**os.environ, "QT_QPA_PLATFORM": "offscreen"},
        timeout=30, shell=False,
    )
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_MAP_024_success_data_keys_exact(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(line(hello_request()), engine)
    # 重新构造一次 load_map 响应以检查键集合
    tif = make_map(tmp_path, name="keys.tif")
    resp2, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert set(resp2["data"].keys()) == {"state", "crs", "width", "height", "bands"}


def test_MAP_025_atomic_failed_loads_keep_old_map_and_calculation(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    req = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))
    before = engine.calculate(req)

    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    no_crs = tmp_path / "nocrs.tif"
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    write_tiff(no_crs, data, 3, "uint8", crs=None)
    bad_t = tmp_path / "badtransform.tif"
    write_tiff(
        bad_t, np.zeros((3, 8, 8), dtype=np.uint8), 3, "uint8",
        transform=Affine(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    for p in (bad, no_crs, bad_t):
        resp, _ = handle_raw_line(line(load_request(str(p))), engine)
        assert resp["success"] is False
    assert engine.calculate(req) == before
    assert engine.state == "MAP_LOADED"


def test_MAP_026_atomic_switch_uses_new_map(tmp_path):
    engine, _ = _loaded_engine(tmp_path, name="a.tif", transform=TRANSFORM)
    req = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))
    result_a = engine.calculate(req)
    b_tif = make_map(tmp_path, name="b.tif", transform=ROTATED_TRANSFORM)
    resp, _ = handle_raw_line(line(load_request(str(b_tif))), engine)
    assert_success_shape(resp)
    result_b = engine.calculate(req)
    assert result_b != result_a
    expected = independent_distance("EPSG:3857", ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result_b["distanceMeters"] - expected) <= 0.5


def test_MAP_027_atomic_multiple_failures_keep_map_loaded(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"x" * 64)
    for _ in range(3):
        resp, _ = handle_raw_line(line(load_request(str(bad))), engine)
        assert resp["success"] is False
    assert engine.state == "MAP_LOADED"
    result = engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0)))
    assert result["distanceMeters"] > 0


def test_MAP_028_switch_release_old_map_no_exception(tmp_path):
    engine, _ = _loaded_engine(tmp_path, name="a.tif")
    b_tif = make_map(tmp_path, name="b.tif")
    resp, _ = handle_raw_line(line(load_request(str(b_tif))), engine)
    assert_success_shape(resp)
    engine.release()
    assert engine._current_map is None


class _FailingConverter:
    """在转换器建立边界注入确定性异常（CRS 合法、元数据已成功读取）。"""

    def __init__(self, *args, **kwargs):
        raise CoordinateConversionError("converter build failed")


def test_MAP_032_crs_present_converter_build_failure_ready(tmp_path, monkeypatch):
    # GeoTIFF 自身存在合法 CRS（EPSG:3857）；仅在转换器建立边界注入失败
    tif = make_map(tmp_path)
    monkeypatch.setattr("app.headless_core.CoordinateConverter", _FailingConverter)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_CRS_MISSING)
    assert resp["id"] == "m-1"
    assert "data" not in resp
    message = resp["error"]["message"]
    assert "Traceback" not in message and "converter build failed" not in message
    assert engine.state == "READY"
    # Worker 可继续处理下一条合法请求
    resp2, _ = handle_raw_line(line(hello_request()), engine)
    assert_success_shape(resp2)


def test_MAP_033_crs_present_converter_build_failure_atomic(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)  # 地图 A
    req = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))
    before = engine.calculate(req)
    b_tif = make_map(tmp_path, name="b.tif")  # 合法 CRS 的候选地图 B
    monkeypatch.setattr("app.headless_core.CoordinateConverter", _FailingConverter)
    resp, _ = handle_raw_line(line(load_request(str(b_tif))), engine)
    assert_error_shape(resp, E_MAP_CRS_MISSING)
    assert engine.state == "MAP_LOADED"
    assert engine.calculate(req) == before
    # Worker 可继续处理下一条合法请求
    resp2, _ = handle_raw_line(line(hello_request()), engine)
    assert_success_shape(resp2)
    assert resp2["data"]["state"] == "MAP_LOADED"
# --------------------------------------------------------------------------- #
# PNT：三类坐标
# --------------------------------------------------------------------------- #
def _point_of_type(point_type, col, row, crs="EPSG:3857", transform=TRANSFORM,
                   lon_lat=None):
    if point_type == "wgs84":
        lon, lat = lon_lat if lon_lat else independent_wgs84(crs, transform, col, row)
        return {"type": "wgs84", "longitude": lon, "latitude": lat}
    if point_type == "map_crs":
        x, y = map_crs_from_pixel(transform, col, row)
        return {"type": "map_crs", "x": x, "y": y}
    return {"type": "pixel", "column": col, "row": row}


PNT_COMBOS = [
    ("wgs84", "wgs84"),
    ("map_crs", "map_crs"),
    ("pixel", "pixel"),
    ("wgs84", "pixel"),
    ("pixel", "wgs84"),
    ("map_crs", "wgs84"),
    ("wgs84", "map_crs"),
    ("pixel", "map_crs"),
    ("map_crs", "pixel"),
]
PNT_COMBO_IDS = [f"PNT-{i:03d}" for i in range(1, 10)]


@pytest.mark.parametrize("type_a,type_b", PNT_COMBOS, ids=PNT_COMBO_IDS)
def test_PNT_combos(type_a, type_b, tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.0, 3.0)
    lon_b, lat_b = independent_wgs84("EPSG:3857", TRANSFORM, 14.0, 11.0)
    point_a = _point_of_type(type_a, 2.0, 3.0, lon_lat=(lon_a, lat_a))
    point_b = _point_of_type(type_b, 14.0, 11.0, lon_lat=(lon_b, lat_b))
    result = engine.calculate(calc_request(point_a, point_b))
    assert result["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-10)
    assert result["pointA"]["latitude"] == pytest.approx(lat_a, abs=1e-10)
    assert result["pointB"]["longitude"] == pytest.approx(lon_b, abs=1e-10)
    assert result["pointB"]["latitude"] == pytest.approx(lat_b, abs=1e-10)


@pytest.mark.parametrize("case_id,col,row", [
    pytest.param("PNT-010", 2, 3, id="PNT-010"),
    pytest.param("PNT-011", 2.5, 3.75, id="PNT-011"),
])
def test_PNT_integer_and_float_pixel(case_id, col, row, tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(col, row), pixel(14.0, 11.0)))
    assert result["distanceMeters"] > 0


@pytest.mark.parametrize("case_id,value", [
    pytest.param("PNT-012", True, id="PNT-012"),
    pytest.param("PNT-013", "2.0", id="PNT-013"),
    pytest.param("PNT-014", None, id="PNT-014"),
    pytest.param("PNT-015", [2.0], id="PNT-015"),
    pytest.param("PNT-016", {"v": 2.0}, id="PNT-016"),
])
def test_PNT_invalid_coordinate_values(case_id, value, tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request({"type": "pixel", "column": value, "row": 1.0},
                         pixel(2.0, 2.0))
        )
    assert exc.value.code == E_POINT_INVALID


def test_PNT_017_nonfinite_coordinate_rejected(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request({"type": "pixel", "column": float("nan"), "row": 1.0},
                         pixel(2.0, 2.0))
        )
    assert exc.value.code == E_POINT_INVALID


def test_PNT_018_full_precision_no_truncation(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.25, 3.75), pixel(14.5, 11.25)))
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.25, 3.75)
    assert result["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-10)
    assert result["pointA"]["latitude"] == pytest.approx(lat_a, abs=1e-10)
    assert result["exactSeconds"] == pytest.approx(
        result["distanceMeters"] / 10, rel=1e-12
    )


def test_PNT_019_decimal_pixel_not_rounded(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.5, 3.5), pixel(14.0, 11.0)))
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", TRANSFORM, 2.5, 3.5)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)


def test_PNT_020_no_automatic_0p5(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.5, 3.5), pixel(14.0, 11.0)))
    lon_plus_half, _ = independent_wgs84("EPSG:3857", TRANSFORM, 3.0, 4.0)
    assert abs(result["pointA"]["longitude"] - lon_plus_half) > 1e-9


def _global_engine(tmp_path):
    return _loaded_engine(
        tmp_path,
        crs="EPSG:4326",
        transform=GLOBAL_WGS84_TRANSFORM,
        width=360,
        height=180,
    )


def test_PNT_021_wgs84_lon_minus_180_valid(tmp_path):
    engine, _ = _global_engine(tmp_path)
    result = engine.calculate(
        calc_request(
            {"type": "wgs84", "longitude": -180.0, "latitude": 0.0},
            {"type": "wgs84", "longitude": -179.0, "latitude": 1.0},
        )
    )
    assert result["pointA"]["longitude"] == -180.0


def test_PNT_022_wgs84_lon_180_range_valid_but_out_of_bounds(tmp_path):
    engine, _ = _global_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "longitude": 180.0, "latitude": 0.0},
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
            )
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_023_wgs84_lat_minus_90_out_of_bounds(tmp_path):
    engine, _ = _global_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "longitude": 0.0, "latitude": -90.0},
                {"type": "wgs84", "longitude": 1.0, "latitude": 0.0},
            )
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_024_wgs84_lat_90_valid(tmp_path):
    engine, _ = _global_engine(tmp_path)
    result = engine.calculate(
        calc_request(
            {"type": "wgs84", "longitude": 0.0, "latitude": 90.0},
            {"type": "wgs84", "longitude": 1.0, "latitude": 89.0},
        )
    )
    assert result["pointA"]["latitude"] == 90.0


def test_PNT_025_wgs84_just_out_of_range_invalid(tmp_path):
    engine, _ = _global_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "longitude": 180.0001, "latitude": 0.0},
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
            )
        )
    assert exc.value.code == E_POINT_INVALID
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "longitude": 0.0, "latitude": 90.0001},
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
            )
        )
    assert exc.value.code == E_POINT_INVALID


def test_PNT_026_wgs84_missing_field_invalid(tmp_path):
    engine, _ = _global_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "latitude": 0.0},
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
            )
        )
    assert exc.value.code == E_POINT_INVALID


def test_PNT_027_wgs84_always_xy_not_swapped(tmp_path):
    engine, _ = _global_engine(tmp_path)
    result = engine.calculate(
        calc_request(
            {"type": "wgs84", "longitude": 10.0, "latitude": 20.0},
            {"type": "wgs84", "longitude": 11.0, "latitude": 21.0},
        )
    )
    assert result["pointA"]["longitude"] == pytest.approx(10.0, abs=1e-10)
    assert result["pointA"]["latitude"] == pytest.approx(20.0, abs=1e-10)
def test_PNT_028_wgs84_in_image_success(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    lon, lat = independent_wgs84("EPSG:3857", TRANSFORM, 2.0, 3.0)
    result = engine.calculate(
        calc_request(
            {"type": "wgs84", "longitude": lon, "latitude": lat},
            pixel(14.0, 11.0),
        )
    )
    assert result["pointA"]["longitude"] == pytest.approx(lon, abs=1e-10)


def test_PNT_029_wgs84_out_of_image_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request(
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
                pixel(1.0, 1.0),
            )
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_030_map_crs_x_y_fields(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    x, y = map_crs_from_pixel(TRANSFORM, 3.0, 4.0)
    result = engine.calculate(
        calc_request({"type": "map_crs", "x": x, "y": y}, pixel(14.0, 11.0))
    )
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", TRANSFORM, 3.0, 4.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)


def test_PNT_031_map_crs_no_x_y_swap(tmp_path):
    engine, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    x, y = map_crs_from_pixel(ROTATED_TRANSFORM, 3.0, 4.0)
    result = engine.calculate(
        calc_request({"type": "map_crs", "x": x, "y": y}, pixel(10.0, 8.0))
    )
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", ROTATED_TRANSFORM, 3.0, 4.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)
    lon_swap, _ = independent_wgs84("EPSG:3857", ROTATED_TRANSFORM, 4.0, 3.0)
    assert abs(result["pointA"]["longitude"] - lon_swap) > 1e-9


def test_PNT_032_map_crs_full_inverse_affine(tmp_path):
    engine, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    x, y = map_crs_from_pixel(ROTATED_TRANSFORM, 2.5, 3.25)
    result = engine.calculate(
        calc_request({"type": "map_crs", "x": x, "y": y}, pixel(10.0, 8.0))
    )
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", ROTATED_TRANSFORM, 2.5, 3.25)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)
    assert result["pointA"]["latitude"] == pytest.approx(lat_exp, abs=1e-10)


def test_PNT_033_map_crs_in_bounds_success(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    x_a, y_a = map_crs_from_pixel(TRANSFORM, 2.0, 3.0)
    x_b, y_b = map_crs_from_pixel(TRANSFORM, 14.0, 11.0)
    result = engine.calculate(
        calc_request(
            {"type": "map_crs", "x": x_a, "y": y_a},
            {"type": "map_crs", "x": x_b, "y": y_b},
        )
    )
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.0, 3.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-10)
    assert result["pointA"]["latitude"] == pytest.approx(lat_a, abs=1e-10)


def test_PNT_034_map_crs_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request({"type": "map_crs", "x": 0.0, "y": 0.0}, pixel(1.0, 1.0))
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_035_map_crs_transform_failure_crs_transform(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)

    def boom(*args, **kwargs):
        raise CoordinateConversionError("模拟失败")

    monkeypatch.setattr("app.worker_engine.map_crs_to_pixel", boom)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            calc_request({"type": "map_crs", "x": 1.0, "y": 1.0}, pixel(1.0, 1.0))
        )
    assert exc.value.code == E_CRS_TRANSFORM


def test_PNT_036_pixel_origin_ok(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(0.0, 0.0), pixel(1.0, 1.0)))
    assert result["distanceMeters"] > 0


def test_PNT_037_pixel_near_edge_valid_decimal(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(15.999, 11.999), pixel(1.0, 1.0)))
    assert result["distanceMeters"] > 0


def test_PNT_038_pixel_column_width_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(calc_request(pixel(16.0, 0.0), pixel(1.0, 1.0)))
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_039_pixel_row_height_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(calc_request(pixel(0.0, 12.0), pixel(1.0, 1.0)))
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_040_pixel_negative_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(calc_request(pixel(-0.5, 1.0), pixel(1.0, 1.0)))
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_PNT_041_pixel_decimal_coordinates(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.5, 3.5), pixel(14.25, 11.75)))
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", TRANSFORM, 2.5, 3.5)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)
    assert result["distanceMeters"] > 0


def test_PNT_042_pixel_no_column_row_swap(tmp_path):
    engine, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    result = engine.calculate(calc_request(pixel(3.0, 4.0), pixel(10.0, 8.0)))
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", ROTATED_TRANSFORM, 3.0, 4.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)
    lon_swap, _ = independent_wgs84("EPSG:3857", ROTATED_TRANSFORM, 4.0, 3.0)
    assert abs(result["pointA"]["longitude"] - lon_swap) > 1e-9


def test_PNT_043_pixel_no_0p5(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(3.0, 4.0), pixel(10.0, 8.0)))
    lon_exp, lat_exp = independent_wgs84("EPSG:3857", TRANSFORM, 3.0, 4.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-10)
    lon_half, _ = independent_wgs84("EPSG:3857", TRANSFORM, 3.5, 4.5)
    assert abs(result["pointA"]["longitude"] - lon_half) > 1e-9


def test_PNT_044_rotated_transform_calculate(tmp_path):
    engine, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance(
        "EPSG:3857", ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0
    )
    assert abs(result["distanceMeters"] - expected) <= 0.5


@pytest.mark.parametrize("case_id,point_a", [
    pytest.param("PNT-045", {"longitude": 1.0, "latitude": 1.0}, id="PNT-045"),
    pytest.param("PNT-046", {"type": 5, "longitude": 1.0, "latitude": 1.0}, id="PNT-046"),
    pytest.param("PNT-047", {"type": "utm", "x": 1.0, "y": 1.0}, id="PNT-047"),
    pytest.param("PNT-048", 5, id="PNT-048"),
])
def test_PNT_error_codes(case_id, point_a, tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    expected = {
        "PNT-045": E_POINT_TYPE,
        "PNT-046": E_POINT_TYPE,
        "PNT-047": E_POINT_TYPE,
        "PNT-048": E_POINT_INVALID,
    }[case_id]
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(calc_request(point_a, pixel(1.0, 1.0)))
    assert exc.value.code == expected


def test_PNT_049_out_of_bounds_via_protocol(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(16.0, 0.0), pixel(1.0, 1.0))), engine
    )
    assert_error_shape(resp, E_POINT_OUT_OF_BOUNDS)


def test_PNT_050_crs_transform_via_protocol(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)

    def boom(*args, **kwargs):
        raise CoordinateConversionError("模拟失败")

    monkeypatch.setattr("app.worker_engine.wgs84_to_pixel", boom)
    resp, _ = handle_raw_line(
        line(calc_request(
            {"type": "wgs84", "longitude": 104.0, "latitude": 30.0},
            pixel(1.0, 1.0),
        )),
        engine,
    )
    assert_error_shape(resp, E_CRS_TRANSFORM)
# --------------------------------------------------------------------------- #
# CAL：距离、速度、时间与响应
# --------------------------------------------------------------------------- #
def test_CAL_001_speed_1_success(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=1))
    assert result["distanceMeters"] > 0
    assert result["exactSeconds"] == pytest.approx(result["distanceMeters"], rel=1e-12)


def test_CAL_002_speed_99_success(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=99))
    assert result["roundedSeconds"] >= 1


def test_CAL_003_speed_missing_request_invalid(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    req = calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0))
    del req["speedMps"]
    resp, _ = handle_raw_line(line(req), engine)
    assert_error_shape(resp, E_REQUEST_INVALID)


SPEED_INVALID_CASES = [
    pytest.param("CAL-004", 0, id="CAL-004"),
    pytest.param("CAL-005", 100, id="CAL-005"),
    pytest.param("CAL-006", -1, id="CAL-006"),
    pytest.param("CAL-007", True, id="CAL-007"),
    pytest.param("CAL-008", False, id="CAL-008"),
    pytest.param("CAL-009", 1.0, id="CAL-009"),
    pytest.param("CAL-010", "1", id="CAL-010"),
    pytest.param("CAL-011", None, id="CAL-011"),
    pytest.param("CAL-012", [1], id="CAL-012"),
    pytest.param("CAL-013", {"v": 1}, id="CAL-013"),
    pytest.param("CAL-014", 1e1, id="CAL-014"),
]


@pytest.mark.parametrize("case_id,speed", SPEED_INVALID_CASES)
def test_CAL_speed_invalid(case_id, speed, tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=speed)), engine
    )
    assert_error_shape(resp, E_SPEED_INVALID)
    assert engine.state == "MAP_LOADED"


def test_CAL_015_same_point_zero(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(3.0, 3.0), pixel(3.0, 3.0)))
    assert result["distanceMeters"] == 0.0
    assert result["exactSeconds"] == 0.0
    assert result["roundedSeconds"] == 0
    assert result["duration"] == "00:00:00"


def test_CAL_016_short_distance(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(3.0, 4.0)))
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 3.0, 4.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_017_normal_distance(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_018_high_precision_decimals(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.25, 3.75), pixel(14.5, 11.25)))
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.25, 3.75, 14.5, 11.25)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_019_three_types_same_physical_points(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.0, 3.0)
    lon_b, lat_b = independent_wgs84("EPSG:3857", TRANSFORM, 14.0, 11.0)
    x_a, y_a = map_crs_from_pixel(TRANSFORM, 2.0, 3.0)
    x_b, y_b = map_crs_from_pixel(TRANSFORM, 14.0, 11.0)
    combos = [
        (pixel(2.0, 3.0), pixel(14.0, 11.0)),
        ({"type": "map_crs", "x": x_a, "y": y_a}, {"type": "map_crs", "x": x_b, "y": y_b}),
        ({"type": "wgs84", "longitude": lon_a, "latitude": lat_a},
         {"type": "wgs84", "longitude": lon_b, "latitude": lat_b}),
    ]
    distances = [
        engine.calculate(calc_request(a, b))["distanceMeters"] for a, b in combos
    ]
    assert distances[0] == pytest.approx(distances[1], abs=1e-6)
    assert distances[0] == pytest.approx(distances[2], abs=1e-6)


def test_CAL_020_epsg4326_map(tmp_path):
    engine, _ = _loaded_engine(
        tmp_path, crs="EPSG:4326", transform=GLOBAL_WGS84_TRANSFORM,
        width=360, height=180,
    )
    result = engine.calculate(
        calc_request(pixel(10.0, 20.0), pixel(15.0, 25.0))
    )
    expected = independent_distance(
        "EPSG:4326", GLOBAL_WGS84_TRANSFORM, 10.0, 20.0, 15.0, 25.0
    )
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_021_epsg3857_map(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_022_other_projected_crs(tmp_path):
    utm_transform = Affine(1.0, 0.0, 500000.0, 0.0, -1.0, 4000000.0)
    engine, _ = _loaded_engine(
        tmp_path, crs="EPSG:32650", transform=utm_transform, width=16, height=12
    )
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance(
        "EPSG:32650", utm_transform, 2.0, 3.0, 14.0, 11.0
    )
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_023_rotated_shear_transform(tmp_path):
    engine, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance(
        "EPSG:3857", ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0
    )
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_024_independent_geod_diff_within_0p5(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0)))
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_CAL_025_time_formulas(tmp_path):
    # 恢复既有 CAL-025 原含义：一条用例验证 exact/rounded/duration 三个时间公式
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=7))
    assert result["exactSeconds"] == pytest.approx(
        result["distanceMeters"] / 7, rel=1e-12
    )
    assert result["roundedSeconds"] == math.ceil(result["exactSeconds"])
    hours, remainder = divmod(result["roundedSeconds"], 3600)
    minutes, seconds = divmod(remainder, 60)
    assert result["duration"] == f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def test_CAL_026_rounded_seconds_formula(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=7))
    assert result["roundedSeconds"] == math.ceil(result["exactSeconds"])


def test_CAL_027_duration_divmod(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    result = engine.calculate(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=7))
    hours, remainder = divmod(result["roundedSeconds"], 3600)
    minutes, seconds = divmod(remainder, 60)
    assert result["duration"] == f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def test_CAL_028_359999_seconds_success(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 359999.0),
    )
    result = engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1))
    assert result["roundedSeconds"] == 359999
    assert result["duration"] == "99:59:59"


def test_CAL_029_360000_seconds_time_limit(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 360000.0),
    )
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1)), engine
    )
    assert_error_shape(resp, E_TIME_LIMIT)
    assert engine.state == "MAP_LOADED"


def test_CAL_030_greater_360000_time_limit(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 400000.0),
    )
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1))
    assert exc.value.code == E_TIME_LIMIT


def test_CAL_031_time_limit_no_partial_data(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 360000.0),
    )
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1)), engine
    )
    assert resp["success"] is False
    assert "data" not in resp


def test_CAL_032_calculate_failure_keeps_map(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0)), engine
    )
    assert_error_shape(resp, E_SPEED_INVALID)
    assert engine.state == "MAP_LOADED"
    ok = engine.calculate(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0)))
    assert ok["distanceMeters"] > 0


def test_CAL_033_simulated_calculation_failure(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)

    def boom(a, b):
        raise DistanceCalculationError("模拟失败")

    monkeypatch.setattr("app.worker_engine.calculate_distance", boom)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0))), engine
    )
    assert_error_shape(resp, E_CALCULATION)


def test_CAL_034_success_data_keys_exact(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))), engine
    )
    assert_success_shape(resp)
    assert set(resp["data"].keys()) == {
        "pointA", "pointB", "distanceMeters", "exactSeconds", "roundedSeconds",
        "duration",
    }


def test_CAL_035_point_keys_exact(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0))), engine
    )
    assert set(resp["data"]["pointA"].keys()) == {"longitude", "latitude"}
    assert set(resp["data"]["pointB"].keys()) == {"longitude", "latitude"}
# --------------------------------------------------------------------------- #
# ERR：完整错误码矩阵（经公共协议入口 handle_raw_line + WorkerEngine）
# --------------------------------------------------------------------------- #
def test_ERR_001_protocol_invalid_json():
    resp, _ = handle_raw_line(b"not json\n")
    assert_error_shape(resp, E_PROTOCOL_INVALID_JSON)
    assert resp["id"] is None


def test_ERR_002_protocol_version():
    resp, _ = handle_raw_line(
        line({"id": "x", "protocolVersion": 2, "operation": "hello"})
    )
    assert_error_shape(resp, E_PROTOCOL_VERSION)
    assert resp["id"] == "x"


def test_ERR_003_operation_unknown():
    resp, _ = handle_raw_line(
        line({"id": "x", "protocolVersion": 1, "operation": "bogus"})
    )
    assert_error_shape(resp, E_OPERATION_UNKNOWN)
    assert resp["id"] == "x"


def test_ERR_004_request_invalid():
    resp, _ = handle_raw_line(
        line({"id": 1, "protocolVersion": 1, "operation": "hello"})
    )
    assert_error_shape(resp, E_REQUEST_INVALID)
    assert resp["id"] is None


def test_ERR_005_internal_last_resort(monkeypatch):
    def boom(self):
        raise RuntimeError("未分类内部错误")

    monkeypatch.setattr(WorkerEngine, "hello", boom)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(hello_request()), engine)
    assert_error_shape(resp, E_INTERNAL)
    assert resp["id"] == "h-1"


def test_ERR_006_map_not_loaded():
    engine = WorkerEngine()
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0))), engine
    )
    assert_error_shape(resp, E_MAP_NOT_LOADED)
    assert engine.state == "READY"


def test_ERR_007_map_not_found(tmp_path):
    engine = WorkerEngine()
    resp, _ = handle_raw_line(
        line(load_request(str(tmp_path / "nope.tif"))), engine
    )
    assert_error_shape(resp, E_MAP_NOT_FOUND)
    resp2, _ = handle_raw_line(line(hello_request()), engine)
    assert_success_shape(resp2)


def test_ERR_008_map_open_failed(tmp_path):
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(bad))), engine)
    assert_error_shape(resp, E_MAP_OPEN_FAILED)
    assert engine.state == "READY"


def test_ERR_009_map_crs_missing(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "nocrs.tif"
    write_tiff(tif, data, 3, "uint8", crs=None)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_CRS_MISSING)
    assert engine.state == "READY"


def test_ERR_010_map_transform_invalid(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "degenerate.tif"
    write_tiff(
        tif, data, 3, "uint8",
        transform=Affine(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    engine = WorkerEngine()
    resp, _ = handle_raw_line(line(load_request(str(tif))), engine)
    assert_error_shape(resp, E_MAP_TRANSFORM_INVALID)
    assert engine.state == "READY"


def test_ERR_011_point_type(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request({"longitude": 1.0, "latitude": 1.0}, pixel(1.0, 1.0))),
        engine,
    )
    assert_error_shape(resp, E_POINT_TYPE)


def test_ERR_012_point_invalid(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(5, pixel(1.0, 1.0))), engine
    )
    assert_error_shape(resp, E_POINT_INVALID)


def test_ERR_013_point_out_of_bounds(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(16.0, 0.0), pixel(1.0, 1.0))), engine
    )
    assert_error_shape(resp, E_POINT_OUT_OF_BOUNDS)


def test_ERR_014_crs_transform(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)

    def boom(*args, **kwargs):
        raise CoordinateConversionError("模拟失败")

    monkeypatch.setattr("app.worker_engine.wgs84_to_pixel", boom)
    resp, _ = handle_raw_line(
        line(calc_request(
            {"type": "wgs84", "longitude": 104.0, "latitude": 30.0},
            pixel(1.0, 1.0),
        )),
        engine,
    )
    assert_error_shape(resp, E_CRS_TRANSFORM)


def test_ERR_015_speed_invalid(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0)), engine
    )
    assert_error_shape(resp, E_SPEED_INVALID)
    resp2, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0))), engine
    )
    assert_success_shape(resp2)


def test_ERR_016_time_limit(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 360000.0),
    )
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1)), engine
    )
    assert_error_shape(resp, E_TIME_LIMIT)
    assert engine.state == "MAP_LOADED"


def test_ERR_017_calculation(tmp_path, monkeypatch):
    engine, _ = _loaded_engine(tmp_path)

    def boom(a, b):
        raise DistanceCalculationError("模拟失败")

    monkeypatch.setattr("app.worker_engine.calculate_distance", boom)
    resp, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0))), engine
    )
    assert_error_shape(resp, E_CALCULATION)
    assert engine.state == "MAP_LOADED"


def _assert_error_message_clean(resp, forbidden):
    message = resp["error"]["message"]
    assert isinstance(message, str) and message
    assert "Traceback" not in message
    for token in forbidden:
        assert token not in message


def test_ERR_018_message_purity(tmp_path):
    engine, _ = _loaded_engine(tmp_path)
    secret_path = str(tmp_path / "secret_map.tif")
    resp, _ = handle_raw_line(line(load_request(secret_path)), engine)
    assert_error_shape(resp, E_MAP_NOT_FOUND)
    _assert_error_message_clean(resp, [secret_path, "Traceback", "FileNotFoundError"])
    resp2, _ = handle_raw_line(
        line(calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0)), engine
    )
    assert_error_shape(resp2, E_SPEED_INVALID)
    _assert_error_message_clean(resp2, ["Traceback", "speedMps"])
# --------------------------------------------------------------------------- #
# LIF：常驻进程生命周期
# --------------------------------------------------------------------------- #
def test_LIF_001_subprocess_full_sequence(tmp_path):
    tif_a = make_map(tmp_path, name="a.tif", transform=TRANSFORM)
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    tif_b = make_map(tmp_path, name="b.tif", transform=ROTATED_TRANSFORM)
    proc = start_worker()
    pid = proc.pid
    try:
        send(proc, hello_request("h-1"))
        assert read_response(proc)["data"]["state"] == "READY"
        send(proc, load_request(str(tif_a), "m-1"))
        loaded_a = read_response(proc)
        assert_success_shape(loaded_a)
        assert loaded_a["data"]["state"] == "MAP_LOADED"
        send(proc, calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid="c-1"))
        calc_a = read_response(proc)
        assert_success_shape(calc_a)
        send(proc, calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0, cid="c-2"))
        assert_error_shape(read_response(proc), E_SPEED_INVALID)
        send(proc, calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid="c-3"))
        calc_ok = read_response(proc)
        assert_success_shape(calc_ok)
        assert calc_ok["data"] == calc_a["data"]
        send(proc, load_request(str(bad), "m-2"))
        assert_error_shape(read_response(proc), E_MAP_OPEN_FAILED)
        send(proc, calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid="c-4"))
        assert read_response(proc)["data"] == calc_a["data"]
        send(proc, load_request(str(tif_b), "m-3"))
        assert read_response(proc)["data"]["state"] == "MAP_LOADED"
        for i in range(100):
            send(
                proc,
                calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid=f"c100-{i}"),
            )
            obj = read_response(proc)
            assert obj["id"] == f"c100-{i}"
            assert obj["success"] is True
        send(proc, hello_request("h-2"))
        assert read_response(proc)["data"]["state"] == "MAP_LOADED"
        send(proc, shutdown_request("s-1"))
        assert read_response(proc)["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
        assert proc.pid == pid
        assert proc.stdout.read() == b""
        stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
        assert "Traceback" not in stderr_text
        assert str(tif_a) not in stderr_text
        assert str(tif_b) not in stderr_text
        assert "c100-" not in stderr_text
    finally:
        stop_worker(proc)


def test_LIF_005_subprocess_business_error_then_success(tmp_path):
    tif = make_map(tmp_path)
    proc = start_worker()
    try:
        send(proc, load_request(str(tif), "m-1"))
        assert read_response(proc)["success"] is True
        send(proc, calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=0, cid="c-1"))
        assert_error_shape(read_response(proc), E_SPEED_INVALID)
        send(proc, calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), cid="c-2"))
        assert read_response(proc)["success"] is True
        send(proc, shutdown_request())
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


def test_LIF_006_subprocess_switch_map_result_matches_baseline(tmp_path):
    tif_a = make_map(tmp_path, name="a.tif", transform=TRANSFORM)
    tif_b = make_map(tmp_path, name="b.tif", transform=ROTATED_TRANSFORM)
    proc = start_worker()
    try:
        send(proc, load_request(str(tif_a), "m-1"))
        assert read_response(proc)["success"] is True
        send(proc, calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid="c-1"))
        d_a = read_response(proc)["data"]["distanceMeters"]
        expected_a = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
        assert abs(d_a - expected_a) <= 0.5
        send(proc, load_request(str(tif_b), "m-2"))
        assert read_response(proc)["success"] is True
        send(proc, calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid="c-2"))
        d_b = read_response(proc)["data"]["distanceMeters"]
        expected_b = independent_distance("EPSG:3857", ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0)
        assert abs(d_b - expected_b) <= 0.5
        assert d_b != d_a
        send(proc, shutdown_request())
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)


def test_LIF_011_subprocess_state_continuity_after_100_calculates(tmp_path):
    tif = make_map(tmp_path)
    proc = start_worker()
    try:
        send(proc, load_request(str(tif), "m-1"))
        assert read_response(proc)["success"] is True
        for i in range(100):
            send(
                proc,
                calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), cid=f"c-{i}"),
            )
            assert read_response(proc)["id"] == f"c-{i}"
        send(proc, hello_request("h-1"))
        assert read_response(proc)["data"]["state"] == "MAP_LOADED"
        send(proc, shutdown_request())
        assert proc.wait(timeout=10) == 0
    finally:
        stop_worker(proc)
