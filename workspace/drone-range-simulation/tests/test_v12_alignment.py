"""TASK-007C：V1.2 对齐的自动化技术证据。

覆盖：无效仿射矩阵、损坏 ZIP、加密 ZIP、MainWindow 层同一点选择、
不同缩放等级坐标一致性、≤100 ms 刷新。
全部使用动态临时数据，不依赖 D 盘参考 ZIP。
"""

import os
import zipfile
from time import perf_counter

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
)
from rasterio.transform import Affine

from app.geotiff_loader import GeoTiffLoadError, load_geotiff
from app.main_window import MainWindow

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
NAN_TRANSFORM = Affine(1.0, 0.0, 0.0, 0.0, float("nan"), 0.0)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


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


def click(view, scene_x, scene_y):
    vp = view.mapFromScene(QPointF(scene_x, scene_y))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(vp),
        QPointF(view.viewport().mapToGlobal(vp)),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(ev)


def wheel(view, delta):
    pos = QPointF(view.viewport().rect().center())
    ev = QWheelEvent(
        pos,
        QPointF(view.viewport().mapToGlobal(pos.toPoint())),
        QPoint(0, 0),
        QPoint(0, delta),
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
        Qt.ScrollPhase.NoScrollPhase,
        False,
    )
    view.wheelEvent(ev)


def make_main_window(tmp_path, name="map.tif", crs="EPSG:3857", transform=TRANSFORM):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    tif = tmp_path / name
    write_tiff(tif, data, 3, "uint8", crs=crs, transform=transform)
    window = MainWindow()
    window.show()
    QApplication.processEvents()
    assert window.load_map_file(str(tif)) is True
    QApplication.processEvents()
    return window


def select_ab_with_speed(window):
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()


def make_corrupt_zip(tmp_path):
    bad = tmp_path / "bad.zip"
    bad.write_bytes(b"PK\x03\x04 not a real zip" + b"\x00" * 64)
    return bad


def make_encrypted_zip(tmp_path, tif_bytes, member="map/inner.tif"):
    plain = tmp_path / "plain.zip"
    with zipfile.ZipFile(plain, "w") as zf:
        zf.writestr(member, tif_bytes)
    data = bytearray(plain.read_bytes())
    patched = 0
    idx = 0
    while True:
        idx = data.find(b"PK\x01\x02", idx)
        if idx < 0:
            break
        flags = int.from_bytes(data[idx + 8:idx + 10], "little")
        data[idx + 8:idx + 10] = (flags | 0x0001).to_bytes(2, "little")
        patched += 1
        idx += 4
    assert patched >= 1
    enc = tmp_path / "enc.zip"
    enc.write_bytes(bytes(data))
    return enc


# --------------------------------------------------------------------------- #
# 无效仿射矩阵
# --------------------------------------------------------------------------- #
def test_invalid_affine_non_finite_rejected(tmp_path):
    data = np.zeros((1, 4, 4), dtype=np.uint8)
    tif = tmp_path / "nan_tr.tif"
    write_tiff(tif, data, 1, "uint8", transform=NAN_TRANSFORM)
    with pytest.raises(GeoTiffLoadError, match="地理变换"):
        load_geotiff(tif)


def test_invalid_affine_mainwindow_preserves_state(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    select_ab_with_speed(window)
    state = (
        window.map_view.point_a,
        window.map_view.point_b,
        window.geo_point_a,
        window.geo_point_b,
        window.distance_result,
        window.flight_time_result,
        window.point_a_label.text(),
        window.distance_label.text(),
        window.flight_time_label.text(),
        window.flight_time_hms_label.text(),
        window.speed_edit.text(),
    )
    data = np.zeros((1, 4, 4), dtype=np.uint8)
    bad = tmp_path / "bad_tr.tif"
    write_tiff(bad, data, 1, "uint8", transform=NAN_TRANSFORM)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert (
        window.map_view.point_a,
        window.map_view.point_b,
        window.geo_point_a,
        window.geo_point_b,
        window.distance_result,
        window.flight_time_result,
        window.point_a_label.text(),
        window.distance_label.text(),
        window.flight_time_label.text(),
        window.flight_time_hms_label.text(),
        window.speed_edit.text(),
    ) == state
    assert "加载失败" in window.status_label.text()
    assert len([i for i in window.map_view.scene().items() if isinstance(i, QGraphicsLineItem)]) == 1
    window.close()


# --------------------------------------------------------------------------- #
# 损坏 ZIP
# --------------------------------------------------------------------------- #
def test_corrupt_zip_rejected(tmp_path):
    bad = make_corrupt_zip(tmp_path)
    with pytest.raises(GeoTiffLoadError):
        load_geotiff(bad)


def test_corrupt_zip_mainwindow_preserves_state(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    select_ab_with_speed(window)
    distance_before = window.distance_result
    time_before = window.flight_time_result
    bad = make_corrupt_zip(tmp_path)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert window.distance_result == distance_before
    assert window.flight_time_result == time_before
    assert window.map_view.point_a is not None
    assert "加载失败" in window.status_label.text()
    window.close()


# --------------------------------------------------------------------------- #
# 加密 ZIP
# --------------------------------------------------------------------------- #
def test_encrypted_zip_rejected(tmp_path):
    inner = tmp_path / "inner.tif"
    data = np.zeros((1, 4, 4), dtype=np.uint8)
    write_tiff(inner, data, 1, "uint8")
    enc = make_encrypted_zip(tmp_path, inner.read_bytes())
    with pytest.raises(GeoTiffLoadError, match="已加密"):
        load_geotiff(enc)


def test_encrypted_zip_mainwindow_preserves_state(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    select_ab_with_speed(window)
    distance_before = window.distance_result
    time_before = window.flight_time_result
    inner = tmp_path / "inner.tif"
    data = np.zeros((1, 4, 4), dtype=np.uint8)
    write_tiff(inner, data, 1, "uint8")
    enc = make_encrypted_zip(tmp_path, inner.read_bytes())
    assert window.load_map_file(str(enc)) is False
    QApplication.processEvents()
    assert window.distance_result == distance_before
    assert window.flight_time_result == time_before
    assert window.map_view.point_a is not None
    assert "加载失败" in window.status_label.text()
    window.close()


# --------------------------------------------------------------------------- #
# MainWindow 层同一点选择
# --------------------------------------------------------------------------- #
def test_mainwindow_same_point_zero_distance_time(qapp, tmp_path):
    window = make_main_window(tmp_path)
    # 同一点：第一次点击设置 A，第二次点击同一位置设置 B
    click(window.map_view, 4, 4)
    click(window.map_view, 4, 4)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.distance_result is not None
    assert window.distance_result.distance_m == 0.0
    assert window.distance_label.text() == "0.00 米"
    assert window.flight_time_result is not None
    assert window.flight_time_result.exact_seconds == 0.0
    assert window.flight_time_result.rounded_seconds == 0
    assert window.flight_time_hms_label.text() == "00:00:00"
    assert window.status_label.text() == "A/B 点选择完成"
    assert len([i for i in window.map_view.scene().items() if isinstance(i, QGraphicsLineItem)]) == 1
    window.close()


# --------------------------------------------------------------------------- #
# 不同缩放等级下坐标一致性
# --------------------------------------------------------------------------- #
def test_same_scene_position_consistent_across_zoom(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 3, 3)
    QApplication.processEvents()
    geo_zoom0 = window.geo_point_a
    src_zoom0 = window.map_view.point_a
    window.clear_button.click()
    QApplication.processEvents()
    for _ in range(4):
        wheel(window.map_view, 120)
    QApplication.processEvents()
    click(window.map_view, 3, 3)
    QApplication.processEvents()
    geo_zoom4 = window.geo_point_a
    src_zoom4 = window.map_view.point_a
    assert src_zoom4.source_col == pytest.approx(src_zoom0.source_col, abs=1.0)
    assert src_zoom4.source_row == pytest.approx(src_zoom0.source_row, abs=1.0)
    assert geo_zoom4.longitude == pytest.approx(geo_zoom0.longitude, abs=1e-3)
    assert geo_zoom4.latitude == pytest.approx(geo_zoom0.latitude, abs=1e-3)
    window.close()


# --------------------------------------------------------------------------- #
# ≤100 ms 刷新
# --------------------------------------------------------------------------- #
def test_refresh_under_100ms(qapp, tmp_path):
    window = make_main_window(tmp_path)
    select_ab_with_speed(window)
    samples_ms = []
    # 速度变化（同步 textChanged 路径）
    for i in range(10):
        QApplication.processEvents()
        t0 = perf_counter()
        window.speed_edit.setText("11" if i % 2 == 0 else "12")
        t1 = perf_counter()
        samples_ms.append((t1 - t0) * 1000.0)
    # 点位变化（清除后重新选点，同步 points_changed 路径）
    for _ in range(5):
        window.clear_button.click()
        QApplication.processEvents()
        t0 = perf_counter()
        click(window.map_view, 2, 2)
        click(window.map_view, 5, 5)
        t1 = perf_counter()
        samples_ms.append((t1 - t0) * 1000.0)
    window.close()
    print(f"perf samples={len(samples_ms)} max_ms={max(samples_ms):.4f}")
    assert max(samples_ms) <= 100.0