"""TASK-010：V1.2 业务规则独立交叉验证。

独立 oracle 方法（测试侧独立计算，不调用生产计算函数生成期望值）：
- 仿射基准：用测试构造时已知的 Affine 独立计算 pixel <-> map_crs；
- CRS 基准：独立建立 pyproj.Transformer，always_xy=True；
- 距离基准：独立 pyproj.Geod(ellps="WGS84").inv；
- 时间基准：独立 distance/speed + math.ceil + divmod。

每个用例至少比较三条链：独立基准 / WorkerEngine 直接结果 / NDJSON 公共协议结果；
条件允许时增加第四条：既有 V1.2 领域函数（calculate_distance + calculate_flight_time）。
"""

import math
import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest

from app.distance_calculator import DistanceResult, calculate_distance
from app.flight_time_calculator import calculate_flight_time
from app.headless_core import geotiff_to_wgs84
from app.worker_engine import WorkerEngine, WorkerProtocolError
from app.worker_protocol import E_TIME_LIMIT, handle_raw_line
from protocol_acceptance_helpers import (
    BIG_TRANSFORM,
    GLOBAL_WGS84_TRANSFORM,
    ROTATED_TRANSFORM,
    TRANSFORM,
    independent_distance,
    independent_time,
    independent_wgs84,
    line,
    make_map,
    map_crs_from_pixel,
    write_tiff,
)


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


def _engine_with(tmp_path, **kwargs):
    tif = make_map(tmp_path, **kwargs)
    engine = WorkerEngine()
    resp, _ = handle_raw_line(
        line({"id": "m-1", "protocolVersion": 1, "operation": "load_map",
              "path": str(tif)}),
        engine,
    )
    assert resp["success"] is True
    return engine, tif


def _domain_chain(engine, point_a, point_b, speed, name_a="A", name_b="B"):
    """第四条链：既有 V1.2 领域函数（无 GUI 调用）。"""
    headless_map = engine._current_map

    def to_geo(name, point):
        if point["type"] == "pixel":
            return geotiff_to_wgs84(headless_map, point["column"], point["row"], name)
        if point["type"] == "map_crs":
            col, row = headless_map.converter.map_to_pixel(point["x"], point["y"])
            return geotiff_to_wgs84(headless_map, col, row, name)
        lon, lat = point["longitude"], point["latitude"]
        col, row = headless_map.converter.wgs84_to_pixel(lon, lat)
        geo = geotiff_to_wgs84(headless_map, col, row, name)
        return GeoPoint(
            name=name,
            source_col=geo.source_col,
            source_row=geo.source_row,
            map_x=geo.map_x,
            map_y=geo.map_y,
            source_crs=geo.source_crs,
            longitude=lon,
            latitude=lat,
        )

    geo_a = to_geo(name_a, point_a)
    geo_b = to_geo(name_b, point_b)
    distance = calculate_distance(geo_a, geo_b)
    flight = calculate_flight_time(distance.distance_m, speed)
    return distance.distance_m, flight.exact_seconds, flight.rounded_seconds, flight.hhmmss


def _run_chains(engine, request):
    ndjson_resp, _ = handle_raw_line(line(request), engine)
    assert ndjson_resp["success"] is True
    ndjson_data = ndjson_resp["data"]
    engine_data = engine.calculate(request)
    return engine_data, ndjson_data


def _assert_against_oracle(engine_data, ndjson_data, expected_distance,
                           speed, expected_exact=None, expected_rounded=None,
                           expected_duration=None, tol=0.5):
    expected_exact = expected_exact if expected_exact is not None else expected_distance / speed
    expected_rounded = expected_rounded if expected_rounded is not None else math.ceil(expected_exact)
    expected_duration = expected_duration or _fmt(expected_rounded)
    for data in (engine_data, ndjson_data):
        assert abs(data["distanceMeters"] - expected_distance) <= tol
        assert data["exactSeconds"] == pytest.approx(expected_exact, rel=1e-12)
        assert data["roundedSeconds"] == expected_rounded
        assert data["duration"] == expected_duration
        assert set(data.keys()) == {
            "pointA", "pointB", "distanceMeters", "exactSeconds",
            "roundedSeconds", "duration",
        }


def _fmt(rounded):
    hours, rem = divmod(rounded, 3600)
    minutes, seconds = divmod(rem, 60)
    return f"{hours:02d}:{minutes:02d}:{seconds:02d}"


def test_V12_001_same_point_zero(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(3.0, 3.0), pixel(3.0, 3.0), speed=10)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 3.0, 3.0, 3.0, 3.0)
    assert expected == 0.0
    for data in (engine_data, ndjson_data):
        assert data["distanceMeters"] == 0.0
        assert data["exactSeconds"] == 0.0
        assert data["roundedSeconds"] == 0
        assert data["duration"] == "00:00:00"
    domain = _domain_chain(engine, pixel(3.0, 3.0), pixel(3.0, 3.0), 10)
    assert domain[0] == 0.0 and domain[2] == 0 and domain[3] == "00:00:00"


def test_V12_002_short_distance(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(2.0, 3.0), pixel(3.0, 4.0), speed=10)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 3.0, 4.0)
    _assert_against_oracle(engine_data, ndjson_data, expected, 10)
    domain = _domain_chain(engine, pixel(2.0, 3.0), pixel(3.0, 4.0), 10)
    assert abs(domain[0] - expected) <= 0.5


def test_V12_003_high_precision_wgs84(tmp_path):
    engine, _ = _engine_with(tmp_path)
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.25, 3.75)
    lon_b, lat_b = independent_wgs84("EPSG:3857", TRANSFORM, 14.5, 11.25)
    request = calc_request(
        {"type": "wgs84", "longitude": lon_a, "latitude": lat_a},
        {"type": "wgs84", "longitude": lon_b, "latitude": lat_b},
        speed=7,
    )
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.25, 3.75, 14.5, 11.25)
    _assert_against_oracle(engine_data, ndjson_data, expected, 7)
    # 归一化响应保留原始 WGS84 数值
    for data in (engine_data, ndjson_data):
        assert data["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-10)
        assert data["pointA"]["latitude"] == pytest.approx(lat_a, abs=1e-10)


def test_V12_004_pixel_input(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=10)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    _assert_against_oracle(engine_data, ndjson_data, expected, 10)


def test_V12_005_map_crs_input(tmp_path):
    engine, _ = _engine_with(tmp_path)
    x_a, y_a = map_crs_from_pixel(TRANSFORM, 2.0, 3.0)
    x_b, y_b = map_crs_from_pixel(TRANSFORM, 14.0, 11.0)
    request = calc_request(
        {"type": "map_crs", "x": x_a, "y": y_a},
        {"type": "map_crs", "x": x_b, "y": y_b},
        speed=10,
    )
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    _assert_against_oracle(engine_data, ndjson_data, expected, 10)


def test_V12_006_three_types_same_physical_point(tmp_path):
    engine, _ = _engine_with(tmp_path)
    lon_a, lat_a = independent_wgs84("EPSG:3857", TRANSFORM, 2.0, 3.0)
    lon_b, lat_b = independent_wgs84("EPSG:3857", TRANSFORM, 14.0, 11.0)
    x_a, y_a = map_crs_from_pixel(TRANSFORM, 2.0, 3.0)
    x_b, y_b = map_crs_from_pixel(TRANSFORM, 14.0, 11.0)
    variants = [
        (pixel(2.0, 3.0), pixel(14.0, 11.0)),
        ({"type": "map_crs", "x": x_a, "y": y_a}, {"type": "map_crs", "x": x_b, "y": y_b}),
        ({"type": "wgs84", "longitude": lon_a, "latitude": lat_a},
         {"type": "wgs84", "longitude": lon_b, "latitude": lat_b}),
    ]
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    distances = []
    for pa, pb in variants:
        engine_data, ndjson_data = _run_chains(engine, calc_request(pa, pb, speed=10))
        _assert_against_oracle(engine_data, ndjson_data, expected, 10)
        distances.append(engine_data["distanceMeters"])
    assert distances[0] == pytest.approx(distances[1], abs=1e-6)
    assert distances[0] == pytest.approx(distances[2], abs=1e-6)


def test_V12_007_rotated_shear_affine(tmp_path):
    engine, _ = _engine_with(tmp_path, transform=ROTATED_TRANSFORM)
    request = calc_request(pixel(2.5, 3.25), pixel(14.0, 11.0), speed=10)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance(
        "EPSG:3857", ROTATED_TRANSFORM, 2.5, 3.25, 14.0, 11.0
    )
    _assert_against_oracle(engine_data, ndjson_data, expected, 10)


def test_V12_008_speed_1(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=1)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    _assert_against_oracle(engine_data, ndjson_data, expected, 1)


def test_V12_009_speed_99(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(2.0, 3.0), pixel(14.0, 11.0), speed=99)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.0, 3.0, 14.0, 11.0)
    _assert_against_oracle(engine_data, ndjson_data, expected, 99)


def test_V12_010_359999_success_boundary(tmp_path, monkeypatch):
    engine, _ = _engine_with(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 359999.0),
    )
    request = calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected_exact, expected_rounded, expected_duration = independent_time(359999.0, 1)
    assert expected_rounded == 359999
    _assert_against_oracle(
        engine_data, ndjson_data, 359999.0, 1,
        expected_exact=expected_exact, expected_rounded=expected_rounded,
        expected_duration=expected_duration,
    )


def test_V12_011_360000_failure_boundary(tmp_path, monkeypatch):
    engine, _ = _engine_with(tmp_path)
    monkeypatch.setattr(
        "app.worker_engine.calculate_distance",
        lambda a, b: DistanceResult("A", "B", 360000.0),
    )
    request = calc_request(pixel(1.0, 1.0), pixel(2.0, 2.0), speed=1)
    expected_exact, expected_rounded, _ = independent_time(360000.0, 1)
    assert expected_rounded == 360000
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(request)
    assert exc.value.code == E_TIME_LIMIT
    ndjson_resp, _ = handle_raw_line(line(request), engine)
    assert ndjson_resp["success"] is False
    assert ndjson_resp["error"]["code"] == E_TIME_LIMIT
    assert "data" not in ndjson_resp


def test_V12_012_real_far_distance_time_limit(tmp_path):
    engine, _ = _engine_with(
        tmp_path, transform=BIG_TRANSFORM, width=1000, height=1000
    )
    request = calc_request(pixel(0.0, 0.0), pixel(999.0, 999.0), speed=1)
    expected = independent_distance(
        "EPSG:3857", BIG_TRANSFORM, 0.0, 0.0, 999.0, 999.0
    )
    _, expected_rounded, _ = independent_time(expected, 1)
    assert expected_rounded >= 360000
    with pytest.raises(WorkerProtocolError) as exc:
        engine.calculate(request)
    assert exc.value.code == E_TIME_LIMIT
    ndjson_resp, _ = handle_raw_line(line(request), engine)
    assert ndjson_resp["error"]["code"] == E_TIME_LIMIT
    assert engine.state == "MAP_LOADED"


def test_V12_013_no_ui_precision_truncation(tmp_path):
    engine, _ = _engine_with(tmp_path)
    request = calc_request(pixel(2.25, 3.75), pixel(14.5, 11.25), speed=7)
    engine_data, ndjson_data = _run_chains(engine, request)
    expected = independent_distance("EPSG:3857", TRANSFORM, 2.25, 3.75, 14.5, 11.25)
    for data in (engine_data, ndjson_data):
        assert data["exactSeconds"] == pytest.approx(expected / 7, rel=1e-12)
        # 若按 UI 6 位小数截断，误差约 5e-7，以下断言可区分
        assert abs(data["exactSeconds"] - round(expected / 7, 6)) > 1e-8
        lon_a, _ = independent_wgs84("EPSG:3857", TRANSFORM, 2.25, 3.75)
        assert data["pointA"]["longitude"] == pytest.approx(lon_a, abs=1e-10)
        assert abs(data["pointA"]["longitude"] - round(lon_a, 6)) > 1e-9
