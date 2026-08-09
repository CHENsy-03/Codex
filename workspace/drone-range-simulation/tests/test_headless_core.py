"""TASK-007：无 GUI 计算核心抽取与基线验证测试。

覆盖：
- 无 QApplication / 无窗口时可导入并调用核心；
- 导入无 GUI 核心不会间接导入 PySide6；
- 合法临时 GeoTIFF 元数据（CRS、尺寸、波段、transform）正确；
- 完整链路：GeoTIFF → A/B 连续像素坐标 → WGS84 → 距离 → 飞行时间；
- 结果与独立 pyproj.Geod 基准一致；
- 不增加 0.5、不交换 column/row、不交换 longitude/latitude；
- 新入口拒绝 ZIP（只处理直接 GeoTIFF）。

测试数据全部通过 pytest 临时目录动态创建，不复制真实地图、真实坐标或 ZIP。
"""

import math
import os
import subprocess
import sys
import textwrap
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from pyproj import Geod, Transformer
from rasterio.transform import Affine

from app.distance_calculator import calculate_distance
from app.flight_time_calculator import calculate_flight_time
from app.geotiff_loader import GeoTiffLoadError
from app.headless_core import HeadlessMap, geotiff_to_wgs84, load_map

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)


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


def _run_headless(code: str) -> subprocess.CompletedProcess:
    """在独立子进程中运行无 GUI 代码（不创建 QApplication）。"""
    env = dict(os.environ)
    env["QT_QPA_PLATFORM"] = "offscreen"
    project_root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    return subprocess.run(
        [sys.executable, "-c", textwrap.dedent(code)],
        cwd=project_root,
        capture_output=True,
        text=True,
        encoding="utf-8",
        env=env,
        timeout=120,
    )


def _independent_baseline(transform, col_a, row_a, col_b, row_b, speed):
    """独立基准：直接使用 pyproj Transformer/Geod 计算，不经过核心。"""
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    geod = Geod(ellps="WGS84")

    def xy(col, row):
        return (
            transform.a * col + transform.b * row + transform.c,
            transform.d * col + transform.e * row + transform.f,
        )

    xa, ya = xy(col_a, row_a)
    xb, yb = xy(col_b, row_b)
    lon_a, lat_a = transformer.transform(xa, ya, errcheck=True)
    lon_b, lat_b = transformer.transform(xb, yb, errcheck=True)
    _, _, distance_m = geod.inv(lon_a, lat_a, lon_b, lat_b)
    exact_seconds = distance_m / speed
    rounded_seconds = math.ceil(exact_seconds)
    hours, remainder = divmod(rounded_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    hhmmss = f"{hours:02d}:{minutes:02d}:{seconds:02d}"
    return distance_m, rounded_seconds, hhmmss


# --------------------------------------------------------------------------- #
# 无 GUI / 无 PySide6 导入
# --------------------------------------------------------------------------- #
def test_import_does_not_import_pyside6():
    code = """
        import sys
        import app.headless_core  # noqa: F401
        print("PySide6" in sys.modules)
    """
    proc = _run_headless(code)
    assert proc.returncode == 0, proc.stderr
    assert proc.stdout.strip() == "False"


def test_headless_chain_without_gui_matches_baseline(tmp_path):
    height, width = 24, 24
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "chain.tif"
    write_tiff(tif, data, 3, "uint8")

    col_a, row_a = 2.0, 3.0
    col_b, row_b = 15.5, 12.25
    speed = 10
    d_expected, sec_expected, hms_expected = _independent_baseline(
        TRANSFORM, col_a, row_a, col_b, row_b, speed
    )

    code = f"""
        from app.headless_core import load_map, geotiff_to_wgs84
        from app.distance_calculator import calculate_distance
        from app.flight_time_calculator import calculate_flight_time

        headless_map = load_map({str(tif)!r})
        point_a = geotiff_to_wgs84(headless_map, {col_a!r}, {row_a!r}, "A")
        point_b = geotiff_to_wgs84(headless_map, {col_b!r}, {row_b!r}, "B")
        result = calculate_distance(point_a, point_b)
        flight = calculate_flight_time(result.distance_m, {speed})
        print(f"{{result.distance_m:.9f}} {{flight.rounded_seconds}} {{flight.hhmmss}}")
    """
    proc = _run_headless(code)
    assert proc.returncode == 0, proc.stderr
    parts = proc.stdout.strip().split()
    assert len(parts) == 3
    assert float(parts[0]) == pytest.approx(d_expected, abs=1e-6)
    assert int(parts[1]) == sec_expected
    assert parts[2] == hms_expected


# --------------------------------------------------------------------------- #
# 元数据加载
# --------------------------------------------------------------------------- #
def test_load_map_returns_correct_metadata(tmp_path):
    height, width = 10, 12
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "meta.tif"
    write_tiff(tif, data, 3, "uint8")

    headless_map = load_map(str(tif))
    assert isinstance(headless_map, HeadlessMap)
    metadata = headless_map.metadata
    assert metadata.source_width == width
    assert metadata.source_height == height
    assert metadata.band_count == 3
    assert metadata.dtype == "uint8"
    assert metadata.crs.to_epsg() == 3857
    assert metadata.crs_string == "EPSG:3857"
    assert metadata.transform == TRANSFORM
    assert metadata.transform.a == 1.0
    assert metadata.transform.b == 0.0
    assert metadata.transform.c == 100.0
    assert metadata.transform.d == 0.0
    assert metadata.transform.e == -1.0
    assert metadata.transform.f == 200.0
    assert metadata.external_path == tif
    # 不生成地图预览
    assert not hasattr(metadata, "preview_rgb")


def test_load_map_rejects_zip(tmp_path):
    zpath = tmp_path / "map.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        zf.writestr("inner.tif", b"not really a tif")
    with pytest.raises(GeoTiffLoadError):
        load_map(str(zpath))


# --------------------------------------------------------------------------- #
# 坐标口径：无 0.5、不交换 column/row、不交换 longitude/latitude
# --------------------------------------------------------------------------- #
def test_geotiff_to_wgs84_no_0p5_no_swap_no_lon_lat_swap(tmp_path):
    transform = Affine(0.5, 0.1, 100.0, -0.2, -0.7, 200.0)
    height, width = 8, 8
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "swap.tif"
    write_tiff(tif, data, 3, "uint8", transform=transform)

    headless_map = load_map(str(tif))
    col, row = 3.0, 4.0
    point = geotiff_to_wgs84(headless_map, col, row, "A")

    map_x = transform.a * col + transform.b * row + transform.c
    map_y = transform.d * col + transform.e * row + transform.f
    transformer = Transformer.from_crs("EPSG:3857", "EPSG:4326", always_xy=True)
    lon_expected, lat_expected = transformer.transform(map_x, map_y, errcheck=True)

    assert point.source_col == col
    assert point.source_row == row
    assert point.map_x == pytest.approx(map_x, abs=1e-9)
    assert point.map_y == pytest.approx(map_y, abs=1e-9)
    assert point.longitude == pytest.approx(lon_expected, abs=1e-9)
    assert point.latitude == pytest.approx(lat_expected, abs=1e-9)

    # 未自动增加 0.5
    plus_half_x = transform.a * (col + 0.5) + transform.b * (row + 0.5) + transform.c
    assert abs(point.map_x - plus_half_x) > 0.1
    # 未交换 column/row
    swapped_x = transform.a * row + transform.b * col + transform.c
    assert abs(point.map_x - swapped_x) > 0.1
    # 未交换 longitude/latitude
    assert abs(point.longitude - lat_expected) > 1e-9


# --------------------------------------------------------------------------- #
# 距离与飞行时间
# --------------------------------------------------------------------------- #
def test_distance_matches_independent_geod(tmp_path):
    height, width = 16, 16
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "dist.tif"
    write_tiff(tif, data, 3, "uint8")

    headless_map = load_map(str(tif))
    point_a = geotiff_to_wgs84(headless_map, 2.0, 3.0, "A")
    point_b = geotiff_to_wgs84(headless_map, 14.5, 11.25, "B")

    distance_m, _, _ = _independent_baseline(TRANSFORM, 2.0, 3.0, 14.5, 11.25, 1)
    result = calculate_distance(point_a, point_b)
    assert result.distance_m == pytest.approx(distance_m, abs=1e-6)


def test_same_point_zero_seconds_and_hhmmss(tmp_path):
    height, width = 8, 8
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "same.tif"
    write_tiff(tif, data, 3, "uint8")

    headless_map = load_map(str(tif))
    point_a = geotiff_to_wgs84(headless_map, 3.0, 3.0, "A")
    point_b = geotiff_to_wgs84(headless_map, 3.0, 3.0, "B")
    result = calculate_distance(point_a, point_b)
    assert result.distance_m == 0.0

    flight = calculate_flight_time(result.distance_m, 10)
    assert flight.exact_seconds == 0.0
    assert flight.rounded_seconds == 0
    assert flight.hhmmss == "00:00:00"


def test_flight_time_rules_preserved(tmp_path):
    height, width = 20, 20
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "time.tif"
    write_tiff(tif, data, 3, "uint8")

    headless_map = load_map(str(tif))
    point_a = geotiff_to_wgs84(headless_map, 1.0, 1.0, "A")
    point_b = geotiff_to_wgs84(headless_map, 18.0, 15.0, "B")
    result = calculate_distance(point_a, point_b)

    flight = calculate_flight_time(result.distance_m, 7)
    assert flight.exact_seconds == pytest.approx(result.distance_m / 7, abs=1e-9)
    assert flight.rounded_seconds == math.ceil(flight.exact_seconds)
    hours, remainder = divmod(flight.rounded_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    assert flight.hhmmss == f"{hours:02d}:{minutes:02d}:{seconds:02d}"
