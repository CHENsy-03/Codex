"""TASK-009：状态机、原子 load_map、三类坐标与完整 calculate 协议测试。

测试地图全部在 pytest 临时目录动态生成，不复制真实地图、ZIP、真实坐标或用户文件。
子进程测试：明确超时、shell=False、stderr 独立、finally 清理残留进程。
"""

import json
import math
import os
import subprocess
import sys
import threading
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from pyproj import Geod, Transformer
from rasterio.crs import CRS
from rasterio.transform import Affine

from app.coordinate_converter import CoordinateConversionError
from app.distance_calculator import DistanceCalculationError, DistanceResult
from app.flight_time_calculator import FlightTimeCalculationError
from app.geotiff_loader import GeoTiffLoadError
from app.headless_core import geotiff_to_wgs84
from app.worker_engine import WorkerEngine, WorkerProtocolError
from app.worker_protocol import (
    E_CALCULATION,
    E_CRS_TRANSFORM,
    E_MAP_CRS_MISSING,
    E_MAP_NOT_FOUND,
    E_MAP_NOT_LOADED,
    E_MAP_OPEN_FAILED,
    E_MAP_TRANSFORM_INVALID,
    E_POINT_INVALID,
    E_POINT_OUT_OF_BOUNDS,
    E_POINT_TYPE,
    E_REQUEST_INVALID,
    E_SPEED_INVALID,
    E_TIME_LIMIT,
    handle_raw_line,
)

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
ROTATED_TRANSFORM = Affine(0.5, 0.1, 100.0, -0.2, -0.7, 200.0)
BIG_TRANSFORM = Affine(1000.0, 0.0, 0.0, 0.0, -1000.0, 1000000.0)


def write_tiff(path, data, count, dtype, crs="EPSG:3857", transform=TRANSFORM):
    height, width = data.shape[1], data.shape[2]
    with rasterio.open(
        path,
        "w",
        driver="GTiff",
        width=width,
        height=height,
        count=count,
        dtype=dtype,
        crs=crs,
        transform=transform,
    ) as dst:
        for i in range(count):
            dst.write(data[i], i + 1)


def make_map(
    tmp_path,
    name="map.tif",
    crs="EPSG:3857",
    transform=TRANSFORM,
    width=16,
    height=12,
    bands=3,
):
    data = np.zeros((bands, height, width), dtype=np.uint8)
    tif = tmp_path / name
    write_tiff(tif, data, bands, "uint8", crs=crs, transform=transform)
    return tif


def _load(engine, path):
    return engine.load_map({"path": path})


def _loaded_engine(tmp_path, **kwargs):
    tif = make_map(tmp_path, **kwargs)
    engine = WorkerEngine()
    result = _load(engine, str(tif))
    return engine, tif, result


def _calc_request(point_a, point_b, speed=10, cid="c-1"):
    return {
        "id": cid,
        "protocolVersion": 1,
        "operation": "calculate",
        "pointA": point_a,
        "pointB": point_b,
        "speedMps": speed,
    }


def _pixel(col, row):
    return {"type": "pixel", "column": col, "row": row}


def _line(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def _baseline_wgs84(transform, col, row):
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    map_x = transform.a * col + transform.b * row + transform.c
    map_y = transform.d * col + transform.e * row + transform.f
    return transformer.transform(map_x, map_y, errcheck=True)


def _baseline_distance(transform, col_a, row_a, col_b, row_b):
    lon_a, lat_a = _baseline_wgs84(transform, col_a, row_a)
    lon_b, lat_b = _baseline_wgs84(transform, col_b, row_b)
    _, _, distance = Geod(ellps="WGS84").inv(lon_a, lat_a, lon_b, lat_b)
    return distance


# --------------------------------------------------------------------------- #
# 子进程辅助
# --------------------------------------------------------------------------- #
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
# A. 状态机
# --------------------------------------------------------------------------- #
def test_start_state_ready_and_hello():
    engine = WorkerEngine()
    assert engine.state == "READY"
    assert engine.hello()["state"] == "READY"
    response, should_exit = handle_raw_line(
        _line({"id": "h-1", "protocolVersion": 1, "operation": "hello"})
    )
    assert should_exit is False
    assert response["data"]["state"] == "READY"


def test_calculate_before_load_returns_map_not_loaded():
    engine = WorkerEngine()
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(1, 1), _pixel(2, 2)))
    assert exc.value.code == E_MAP_NOT_LOADED
    assert engine.state == "READY"

    response, should_exit = handle_raw_line(
        _line(_calc_request(_pixel(1, 1), _pixel(2, 2))), engine
    )
    assert should_exit is False
    assert response["success"] is False
    assert response["error"]["code"] == E_MAP_NOT_LOADED


def test_legal_load_map_returns_map_loaded(tmp_path):
    engine, tif, result = _loaded_engine(tmp_path)
    assert result == {
        "state": "MAP_LOADED",
        "crs": "EPSG:3857",
        "width": 16,
        "height": 12,
        "bands": 3,
    }
    assert engine.state == "MAP_LOADED"


def test_hello_after_load_returns_map_loaded(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    assert engine.hello()["state"] == "MAP_LOADED"


def test_failed_load_keeps_state(tmp_path):
    engine = WorkerEngine()
    bad = os.path.join(str(tmp_path), "bad.tif")
    with open(bad, "wb") as f:
        f.write(b"garbage" * 50)
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, bad)
    assert exc.value.code == E_MAP_OPEN_FAILED
    assert engine.state == "READY"

    good = make_map(tmp_path, name="good.tif")
    _load(engine, str(good))
    with pytest.raises(WorkerProtocolError):
        _load(engine, bad)
    assert engine.state == "MAP_LOADED"


def test_shutdown_sets_terminating_and_releases_map(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    data = engine.shutdown()
    assert data == {"state": "TERMINATING"}
    assert engine.state == "TERMINATING"
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(1, 1), _pixel(2, 2)))
    assert exc.value.code == E_MAP_NOT_LOADED


# --------------------------------------------------------------------------- #
# B. 地图加载
# --------------------------------------------------------------------------- #
def test_load_map_returns_correct_metadata(tmp_path):
    engine, tif, result = _loaded_engine(tmp_path)
    assert result["state"] == "MAP_LOADED"
    assert result["crs"] == "EPSG:3857"
    assert result["width"] == 16
    assert result["height"] == 12
    assert result["bands"] == 3


def test_relative_or_invalid_path_returns_request_invalid(tmp_path):
    engine = WorkerEngine()
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, "relative/map.tif")
    assert exc.value.code == E_REQUEST_INVALID
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, "")
    assert exc.value.code == E_REQUEST_INVALID
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, 123)
    assert exc.value.code == E_REQUEST_INVALID


def test_not_found_and_directory_returns_map_not_found(tmp_path):
    engine = WorkerEngine()
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(tmp_path / "nope.tif"))
    assert exc.value.code == E_MAP_NOT_FOUND
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(tmp_path))
    assert exc.value.code == E_MAP_NOT_FOUND


def test_corrupt_fake_zip_returns_map_open_failed(tmp_path):
    engine = WorkerEngine()
    corrupt = tmp_path / "corrupt.tif"
    corrupt.write_bytes(b"garbage" * 50)
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(corrupt))
    assert exc.value.code == E_MAP_OPEN_FAILED

    fake = tmp_path / "fake.tif"
    fake.write_text("this is not a tiff", encoding="utf-8")
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(fake))
    assert exc.value.code == E_MAP_OPEN_FAILED

    zpath = tmp_path / "map.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("inner.tif", b"x")
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(zpath))
    assert exc.value.code == E_MAP_OPEN_FAILED


def test_missing_crs_returns_map_crs_missing(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "nocrs.tif"
    write_tiff(tif, data, 3, "uint8", crs=None)
    engine = WorkerEngine()
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(tif))
    assert exc.value.code == E_MAP_CRS_MISSING


def test_degenerate_transform_returns_transform_invalid(tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "degenerate.tif"
    write_tiff(
        tif,
        data,
        3,
        "uint8",
        transform=Affine(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    engine = WorkerEngine()
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(tif))
    assert exc.value.code == E_MAP_TRANSFORM_INVALID


def test_no_epsg_returns_wkt2(tmp_path):
    custom = CRS.from_proj4(
        "+proj=tmerc +lat_0=0 +lon_0=117 +k=1 +x_0=500000 "
        "+y_0=0 +ellps=WGS84 +units=m +no_defs"
    )
    assert custom.to_epsg() is None
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / "custom.tif"
    write_tiff(tif, data, 3, "uint8", crs=custom)
    engine = WorkerEngine()
    result = _load(engine, str(tif))
    assert "EPSG:" not in result["crs"]
    assert result["crs"].startswith(("PROJCRS", "PROJCS", "GEOGCRS", "GEOGCS"))


def test_load_map_no_preview_and_no_gui(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    metadata = engine._current_map.metadata
    assert not hasattr(metadata, "preview_rgb")


def test_import_worker_engine_does_not_import_pyside6():
    code = (
        "import sys\n"
        "import app.worker_engine\n"
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


# --------------------------------------------------------------------------- #
# C. 原子替换
# --------------------------------------------------------------------------- #
def test_failed_loads_keep_old_map_and_calculation(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    req = _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0))
    before = engine.calculate(req)

    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    for _ in range(2):
        with pytest.raises(WorkerProtocolError):
            _load(engine, str(bad))

    after = engine.calculate(req)
    assert after == before
    assert engine.state == "MAP_LOADED"


def test_failed_load_missing_crs_keeps_old_map(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    req = _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0))
    before = engine.calculate(req)

    data = np.zeros((3, 8, 8), dtype=np.uint8)
    no_crs = tmp_path / "nocrs.tif"
    write_tiff(no_crs, data, 3, "uint8", crs=None)
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(no_crs))
    assert exc.value.code == E_MAP_CRS_MISSING

    assert engine.calculate(req) == before
    assert engine.state == "MAP_LOADED"


def test_failed_load_invalid_transform_keeps_old_map(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    req = _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0))
    before = engine.calculate(req)

    data = np.zeros((3, 8, 8), dtype=np.uint8)
    bad_t = tmp_path / "badtransform.tif"
    write_tiff(
        bad_t,
        data,
        3,
        "uint8",
        transform=Affine(1.0, 0.0, 0.0, 0.0, 0.0, 0.0),
    )
    with pytest.raises(WorkerProtocolError) as exc:
        _load(engine, str(bad_t))
    assert exc.value.code == E_MAP_TRANSFORM_INVALID

    assert engine.calculate(req) == before
    assert engine.state == "MAP_LOADED"


def test_successful_switch_uses_new_map(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path, name="a.tif", transform=TRANSFORM)
    req = _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0))
    result_a = engine.calculate(req)

    _loaded_map_b = make_map(
        tmp_path, name="b.tif", transform=ROTATED_TRANSFORM
    )
    _load(engine, str(_loaded_map_b))
    result_b = engine.calculate(req)
    assert engine.state == "MAP_LOADED"
    assert result_b != result_a
    expected_b = _baseline_distance(ROTATED_TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result_b["distanceMeters"] - expected_b) <= 0.5


def test_multiple_failures_keep_map_loaded(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"x" * 64)
    for _ in range(3):
        with pytest.raises(WorkerProtocolError):
            _load(engine, str(bad))
    assert engine.state == "MAP_LOADED"
    req = _calc_request(_pixel(1.0, 1.0), _pixel(10.0, 9.0))
    assert engine.calculate(req)["distanceMeters"] > 0


# --------------------------------------------------------------------------- #
# D. 坐标
# --------------------------------------------------------------------------- #
def test_three_mixed_coordinate_combinations(tmp_path):
    engine, tif, _ = _loaded_engine(tmp_path)
    lon_a, lat_a = _baseline_wgs84(TRANSFORM, 2.0, 3.0)
    lon_b, lat_b = _baseline_wgs84(TRANSFORM, 14.0, 11.0)
    map_x_a = TRANSFORM.a * 2.0 + TRANSFORM.b * 3.0 + TRANSFORM.c
    map_y_a = TRANSFORM.d * 2.0 + TRANSFORM.e * 3.0 + TRANSFORM.f
    map_x_b = TRANSFORM.a * 14.0 + TRANSFORM.b * 11.0 + TRANSFORM.c
    map_y_b = TRANSFORM.d * 14.0 + TRANSFORM.e * 11.0 + TRANSFORM.f

    combos = [
        (
            {"type": "wgs84", "longitude": lon_a, "latitude": lat_a},
            _pixel(14.0, 11.0),
        ),
        (
            {"type": "map_crs", "x": map_x_a, "y": map_y_a},
            {"type": "wgs84", "longitude": lon_b, "latitude": lat_b},
        ),
        (
            _pixel(2.0, 3.0),
            {"type": "map_crs", "x": map_x_b, "y": map_y_b},
        ),
    ]
    for point_a, point_b in combos:
        result = engine.calculate(_calc_request(point_a, point_b))
        assert result["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-9)
        assert result["pointA"]["latitude"] == pytest.approx(lat_a, abs=1e-9)
        assert result["pointB"]["longitude"] == pytest.approx(lon_b, abs=1e-9)
        assert result["pointB"]["latitude"] == pytest.approx(lat_b, abs=1e-9)


def test_rotated_transform_no_0p5_no_swap(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path, transform=ROTATED_TRANSFORM)
    result = engine.calculate(
        _calc_request(_pixel(3.0, 4.0), _pixel(10.0, 8.0))
    )
    lon_exp, lat_exp = _baseline_wgs84(ROTATED_TRANSFORM, 3.0, 4.0)
    assert result["pointA"]["longitude"] == pytest.approx(lon_exp, abs=1e-9)
    assert result["pointA"]["latitude"] == pytest.approx(lat_exp, abs=1e-9)

    # 未自动增加 0.5
    lon_half, lat_half = _baseline_wgs84(ROTATED_TRANSFORM, 3.5, 4.5)
    assert abs(result["pointA"]["longitude"] - lon_half) > 1e-9
    # 未交换 column/row
    lon_swap, lat_swap = _baseline_wgs84(ROTATED_TRANSFORM, 4.0, 3.0)
    assert abs(result["pointA"]["longitude"] - lon_swap) > 1e-9
    # 未交换 longitude/latitude
    assert abs(result["pointA"]["longitude"] - lat_exp) > 1e-9


def test_out_of_bounds_all_types(tmp_path):
    engine, tif, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(16.0, 0.0), _pixel(1.0, 1.0)))
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS

    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request(
                {"type": "map_crs", "x": 0.0, "y": 0.0},
                _pixel(1.0, 1.0),
            )
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS

    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request(
                {"type": "wgs84", "longitude": 0.0, "latitude": 0.0},
                _pixel(1.0, 1.0),
            )
        )
    assert exc.value.code == E_POINT_OUT_OF_BOUNDS


def test_point_type_errors(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request({"longitude": 1.0, "latitude": 1.0}, _pixel(1.0, 1.0))
        )
    assert exc.value.code == E_POINT_TYPE
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request({"type": 5, "longitude": 1.0, "latitude": 1.0}, _pixel(1.0, 1.0))
        )
    assert exc.value.code == E_POINT_TYPE
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request({"type": "utm", "x": 1.0, "y": 1.0}, _pixel(1.0, 1.0))
        )
    assert exc.value.code == E_POINT_TYPE


def test_point_invalid_variants(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    invalid_points = [
        5,
        {"type": "wgs84", "latitude": 1.0},
        {"type": "wgs84", "longitude": True, "latitude": 1.0},
        {"type": "wgs84", "longitude": "1.0", "latitude": 1.0},
        {"type": "wgs84", "longitude": None, "latitude": 1.0},
        {"type": "wgs84", "longitude": float("nan"), "latitude": 1.0},
        {"type": "wgs84", "longitude": 200.0, "latitude": 1.0},
        {"type": "wgs84", "longitude": 1.0, "latitude": 95.0},
        {"type": "map_crs", "y": 1.0},
        {"type": "pixel", "row": 1.0},
    ]
    for point_a in invalid_points:
        with pytest.raises(WorkerProtocolError) as exc:
            engine.calculate(_calc_request(point_a, _pixel(1.0, 1.0)))
        assert exc.value.code == E_POINT_INVALID


def test_crs_transform_failure_returns_crs_transform(tmp_path, monkeypatch):
    engine, _, _ = _loaded_engine(tmp_path)

    def boom(*args, **kwargs):
        raise CoordinateConversionError("模拟转换失败")

    monkeypatch.setattr("app.worker_engine.wgs84_to_pixel", boom)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request(
                {"type": "wgs84", "longitude": 104.0, "latitude": 30.0},
                _pixel(1.0, 1.0),
            )
        )
    assert exc.value.code == E_CRS_TRANSFORM


# --------------------------------------------------------------------------- #
# E. 计算
# --------------------------------------------------------------------------- #
def test_distance_matches_independent_geod(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    result = engine.calculate(_calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0)))
    expected = _baseline_distance(TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    assert abs(result["distanceMeters"] - expected) <= 0.5


def test_speed_1_and_99_success(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    for speed in (1, 99):
        result = engine.calculate(
            _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0), speed=speed)
        )
        assert result["distanceMeters"] > 0
        assert result["exactSeconds"] == pytest.approx(
            result["distanceMeters"] / speed, rel=1e-12
        )
        assert result["roundedSeconds"] == math.ceil(result["exactSeconds"])


@pytest.mark.parametrize("speed", [0, 100, -1, True, 1.0, "1", None])
def test_speed_invalid_variants(tmp_path, speed):
    engine, _, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(
            _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0), speed=speed)
        )
    assert exc.value.code == E_SPEED_INVALID


def test_same_point_zero_result(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    result = engine.calculate(_calc_request(_pixel(3.0, 3.0), _pixel(3.0, 3.0)))
    assert result["distanceMeters"] == 0.0
    assert result["exactSeconds"] == 0.0
    assert result["roundedSeconds"] == 0
    assert result["duration"] == "00:00:00"


def test_rounded_seconds_359999_success(tmp_path, monkeypatch):
    engine, _, _ = _loaded_engine(tmp_path)

    def fake_distance(a, b):
        return DistanceResult("A", "B", 359999.0)

    monkeypatch.setattr("app.worker_engine.calculate_distance", fake_distance)
    result = engine.calculate(_calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0), speed=1))
    assert result["roundedSeconds"] == 359999
    assert result["duration"] == "99:59:59"


def test_rounded_seconds_360000_time_limit(tmp_path, monkeypatch):
    engine, _, _ = _loaded_engine(tmp_path)

    def fake_distance(a, b):
        return DistanceResult("A", "B", 360000.0)

    monkeypatch.setattr("app.worker_engine.calculate_distance", fake_distance)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0), speed=1))
    assert exc.value.code == E_TIME_LIMIT
    assert engine.state == "MAP_LOADED"


def test_real_far_distance_time_limit(tmp_path):
    engine, _, _ = _loaded_engine(
        tmp_path, transform=BIG_TRANSFORM, width=1000, height=1000
    )
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(0.0, 0.0), _pixel(999.0, 999.0), speed=1))
    assert exc.value.code == E_TIME_LIMIT
    assert engine.state == "MAP_LOADED"


def test_calculation_exception_returns_calculation(tmp_path, monkeypatch):
    engine, _, _ = _loaded_engine(tmp_path)

    def boom(a, b):
        raise DistanceCalculationError("模拟距离失败")

    monkeypatch.setattr("app.worker_engine.calculate_distance", boom)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0)))
    assert exc.value.code == E_CALCULATION


def test_calculation_exception_flight_time_returns_calculation(tmp_path, monkeypatch):
    engine, _, _ = _loaded_engine(tmp_path)

    def boom(distance, speed):
        raise FlightTimeCalculationError("模拟时间失败")

    monkeypatch.setattr("app.worker_engine.calculate_flight_time", boom)
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(_calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0)))
    assert exc.value.code == E_CALCULATION


def test_response_uses_full_precision_no_truncation(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    result = engine.calculate(_calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0), speed=7))
    geo_a = geotiff_to_wgs84(engine._current_map, 2.0, 3.0, "A")
    assert result["pointA"]["longitude"] == geo_a.longitude
    assert result["pointA"]["latitude"] == geo_a.latitude
    assert result["exactSeconds"] == pytest.approx(
        result["distanceMeters"] / 7, rel=1e-12
    )
    assert result["roundedSeconds"] == math.ceil(result["exactSeconds"])


def test_calculate_failure_does_not_change_map(tmp_path):
    engine, _, _ = _loaded_engine(tmp_path)
    with pytest.raises(WorkerProtocolError):
        engine.calculate(
            _calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0), speed=0)
        )
    assert engine.state == "MAP_LOADED"
    result = engine.calculate(_calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0)))
    assert result["distanceMeters"] > 0


def test_protocol_dispatch_with_shared_engine(tmp_path):
    tif = make_map(tmp_path)
    engine = WorkerEngine()

    resp, _ = handle_raw_line(
        _line({"id": "m-1", "protocolVersion": 1, "operation": "load_map", "path": str(tif)}),
        engine,
    )
    assert resp["success"] is True
    assert resp["data"]["state"] == "MAP_LOADED"

    resp, _ = handle_raw_line(
        _line(_calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0))), engine
    )
    assert resp["success"] is True
    assert resp["data"]["distanceMeters"] > 0

    resp, _ = handle_raw_line(
        _line({"id": "h-2", "protocolVersion": 1, "operation": "hello"}), engine
    )
    assert resp["data"]["state"] == "MAP_LOADED"


# --------------------------------------------------------------------------- #
# F. 常驻进程与回归
# --------------------------------------------------------------------------- #
def test_subprocess_full_lifecycle(tmp_path):
    tif = make_map(tmp_path)
    proc = _start_worker()
    try:
        _send(proc, {"id": "h-1", "protocolVersion": 1, "operation": "hello"})
        hello = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert hello["data"]["state"] == "READY"

        _send(proc, {
            "id": "m-1",
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(tif),
        })
        loaded = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert loaded["success"] is True
        assert loaded["data"]["state"] == "MAP_LOADED"
        assert loaded["data"]["crs"] == "EPSG:3857"

        _send(proc, _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0)))
        calc = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert calc["success"] is True
        assert calc["data"]["distanceMeters"] > 0

        _send(proc, {"id": "h-2", "protocolVersion": 1, "operation": "hello"})
        hello2 = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert hello2["data"]["state"] == "MAP_LOADED"

        _send(proc, {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"})
        shut = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert shut["data"] == {"state": "TERMINATING"}
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_subprocess_100_calculates_no_reload_no_cross_talk(tmp_path):
    tif = make_map(tmp_path)
    proc = _start_worker()
    try:
        _send(proc, {
            "id": "m-1",
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(tif),
        })
        loaded = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert loaded["success"] is True

        for i in range(100):
            # 发一条、读一条，避免 Windows 管道缓冲死锁；仍为同一地图连续 100 次 calculate
            _send(
                proc,
                _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0), cid=f"c-{i}"),
            )
            line = _readline(proc.stdout)
            assert line.startswith(b"\xef\xbb\xbf") is False
            obj = json.loads(line.decode("utf-8"))
            assert obj["id"] == f"c-{i}"
            assert obj["success"] is True
        assert proc.poll() is None

        _send(proc, {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"})
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_business_error_then_valid_calculate(tmp_path):
    tif = make_map(tmp_path)
    proc = _start_worker()
    try:
        _send(proc, {
            "id": "m-1",
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(tif),
        })
        json.loads(_readline(proc.stdout).decode("utf-8"))

        _send(proc, _calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0), speed=0))
        err = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert err["success"] is False
        assert err["error"]["code"] == "E_SPEED_INVALID"

        _send(proc, _calc_request(_pixel(1.0, 1.0), _pixel(2.0, 2.0)))
        ok = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert ok["success"] is True

        _send(proc, {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"})
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_subprocess_failed_load_keeps_old_map(tmp_path):
    tif_a = make_map(tmp_path, name="a.tif")
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    proc = _start_worker()
    try:
        _send(proc, {
            "id": "m-1",
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(tif_a),
        })
        json.loads(_readline(proc.stdout).decode("utf-8"))

        _send(proc, _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0)))
        first = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert first["success"] is True

        _send(proc, {
            "id": "m-2",
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(bad),
        })
        err = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert err["error"]["code"] == "E_MAP_OPEN_FAILED"

        _send(proc, _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0)))
        second = json.loads(_readline(proc.stdout).decode("utf-8"))
        assert second["success"] is True
        assert second["data"] == first["data"]

        _send(proc, {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"})
        assert proc.wait(timeout=10) == 0
    finally:
        _stop_worker(proc)


def test_stderr_has_no_request_content(tmp_path):
    tif = make_map(tmp_path)
    proc = _start_worker()
    try:
        secret_id = "secret-map-id-xyz"
        _send(proc, {
            "id": secret_id,
            "protocolVersion": 1,
            "operation": "load_map",
            "path": str(tif),
        })
        json.loads(_readline(proc.stdout).decode("utf-8"))
        _send(proc, _calc_request(_pixel(2.0, 3.0), _pixel(14.0, 11.0)))
        json.loads(_readline(proc.stdout).decode("utf-8"))
        _send(proc, {"id": "s-1", "protocolVersion": 1, "operation": "shutdown"})
        assert proc.wait(timeout=10) == 0

        stderr_text = proc.stderr.read().decode("utf-8", errors="replace")
        stdout_text = proc.stdout.read().decode("utf-8", errors="replace")
        assert secret_id not in stderr_text
        assert str(tif) not in stderr_text
        assert "Traceback" not in stderr_text
        assert "Traceback" not in stdout_text
    finally:
        _stop_worker(proc)
