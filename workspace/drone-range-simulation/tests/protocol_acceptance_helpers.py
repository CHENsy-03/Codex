"""TASK-010 协议验收与 V1.2 交叉验证共享辅助（只读测试工具）。

本文件只包含：
- pytest 临时 GeoTIFF 生成；
- 子进程安全启动、逐行读写与清理；
- 独立数学基准辅助（仿射、CRS、Geod、时间）；
- 响应结构断言。

不包含生产逻辑副本；独立基准不调用生产计算函数生成期望值。
"""

import json
import math
import os
import subprocess
import sys
import threading

import numpy as np
import rasterio
from pyproj import Geod, Transformer
from rasterio.transform import Affine

PROJECT_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
ROTATED_TRANSFORM = Affine(0.5, 0.1, 100.0, -0.2, -0.7, 200.0)
BIG_TRANSFORM = Affine(1000.0, 0.0, 0.0, 0.0, -1000.0, 1000000.0)
# EPSG:4326 全球覆盖（lon -180..180，lat -90..90）
GLOBAL_WGS84_TRANSFORM = Affine(1.0, 0.0, -180.0, 0.0, -1.0, 90.0)


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


def line(payload: dict) -> bytes:
    return (json.dumps(payload, ensure_ascii=False) + "\n").encode("utf-8")


def readline(stream, timeout: float = 10.0) -> bytes:
    result: list = []

    def reader():
        result.append(stream.readline())

    thread = threading.Thread(target=reader, daemon=True)
    thread.start()
    thread.join(timeout)
    if thread.is_alive():
        raise TimeoutError("读取子进程 stdout 超时")
    return result[0]


def start_worker():
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


def send(proc, payload: dict) -> None:
    proc.stdin.write(line(payload))
    proc.stdin.flush()


def read_response(proc, timeout: float = 10.0) -> dict:
    raw = readline(proc.stdout, timeout)
    assert raw.endswith(b"\n"), "响应必须以 LF 结束"
    assert not raw.startswith(b"\xef\xbb\xbf"), "响应不得带 BOM"
    return json.loads(raw.decode("utf-8"))


def stop_worker(proc) -> None:
    if proc.poll() is None:
        proc.kill()
    try:
        proc.wait(timeout=10)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=10)


def assert_success_shape(resp: dict) -> None:
    assert set(resp.keys()) == {"id", "success", "data"}
    assert resp["success"] is True
    assert "error" not in resp
    assert isinstance(resp["data"], dict)


def assert_error_shape(resp: dict, expected_code: str) -> None:
    assert set(resp.keys()) == {"id", "success", "error"}
    assert resp["success"] is False
    assert "data" not in resp
    assert set(resp["error"].keys()) == {"code", "message"}
    assert resp["error"]["code"] == expected_code
    assert isinstance(resp["error"]["message"], str)
    assert resp["error"]["message"]


# --------------------------------------------------------------------------- #
# 独立数学基准（不调用生产计算函数）
# --------------------------------------------------------------------------- #
def independent_wgs84(crs, transform, col, row):
    """像素 → map_crs（独立仿射）→ WGS84（独立 Transformer，always_xy=True）。"""
    transformer = Transformer.from_crs(crs, "EPSG:4326", always_xy=True)
    map_x = transform.a * col + transform.b * row + transform.c
    map_y = transform.d * col + transform.e * row + transform.f
    return transformer.transform(map_x, map_y, errcheck=True)


def independent_distance(crs, transform, col_a, row_a, col_b, row_b):
    lon_a, lat_a = independent_wgs84(crs, transform, col_a, row_a)
    lon_b, lat_b = independent_wgs84(crs, transform, col_b, row_b)
    _, _, distance_m = Geod(ellps="WGS84").inv(lon_a, lat_a, lon_b, lat_b)
    return distance_m


def independent_time(distance_m, speed_m_s):
    exact_seconds = distance_m / speed_m_s
    rounded_seconds = math.ceil(exact_seconds)
    hours, remainder = divmod(rounded_seconds, 3600)
    minutes, seconds = divmod(remainder, 60)
    return (
        exact_seconds,
        rounded_seconds,
        f"{hours:02d}:{minutes:02d}:{seconds:02d}",
    )


def map_crs_from_pixel(transform, col, row):
    return (
        transform.a * col + transform.b * row + transform.c,
        transform.d * col + transform.e * row + transform.f,
    )
