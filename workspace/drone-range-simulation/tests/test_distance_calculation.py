"""TASK-005：WGS84 椭球面二维测地线距离测试。

使用动态数据与 Qt offscreen，不依赖 D 盘参考 ZIP。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import numpy as np
import pytest
import rasterio
from pyproj import CRS, Geod
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
)
from rasterio.transform import Affine

from app.coordinate_converter import GeoPoint
from app.distance_calculator import (
    DistanceCalculationError,
    DistanceResult,
    calculate_distance,
)
from app.main_window import MainWindow

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)
GEOD = Geod(ellps="WGS84")


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def make_geo(name, lon, lat, source_crs="EPSG:3857"):
    return GeoPoint(
        name=name,
        source_col=0.0,
        source_row=0.0,
        map_x=0.0,
        map_y=0.0,
        source_crs=CRS.from_user_input(source_crs),
        longitude=lon,
        latitude=lat,
    )


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


# --------------------------------------------------------------------------- #
# 事件辅助（与真实事件共用同一逻辑）
# --------------------------------------------------------------------------- #
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


def drag(view, start, end):
    press = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        QPointF(start),
        QPointF(view.viewport().mapToGlobal(start)),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(press)
    move = QMouseEvent(
        QEvent.Type.MouseMove,
        QPointF(end),
        QPointF(view.viewport().mapToGlobal(end)),
        Qt.MouseButton.NoButton,
        Qt.MouseButton.RightButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mouseMoveEvent(move)
    release = QMouseEvent(
        QEvent.Type.MouseButtonRelease,
        QPointF(end),
        QPointF(view.viewport().mapToGlobal(end)),
        Qt.MouseButton.RightButton,
        Qt.MouseButton.NoButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mouseReleaseEvent(release)


def counts(view):
    return {
        "pixmap": len([i for i in view.scene().items() if isinstance(i, QGraphicsPixmapItem)]),
        "ellipse": len([i for i in view.scene().items() if isinstance(i, QGraphicsEllipseItem)]),
        "line": len([i for i in view.scene().items() if isinstance(i, QGraphicsLineItem)]),
    }


# --------------------------------------------------------------------------- #
# 距离计算单元测试
# --------------------------------------------------------------------------- #
def test_equator_one_degree():
    result = calculate_distance(make_geo("A", 0.0, 0.0), make_geo("B", 1.0, 0.0))
    assert result.distance_m == pytest.approx(111319.490793, abs=0.01)


def test_meridian_one_degree():
    result = calculate_distance(make_geo("A", 0.0, 0.0), make_geo("B", 0.0, 1.0))
    assert result.distance_m == pytest.approx(110574.388558, abs=0.01)


def test_same_point_zero():
    result = calculate_distance(make_geo("A", 30.0, 20.0), make_geo("B", 30.0, 20.0))
    assert result.distance_m == 0.0


def test_symmetric_distance():
    a, b = make_geo("A", 10.0, 20.0), make_geo("B", 30.0, 40.0)
    assert calculate_distance(a, b).distance_m == pytest.approx(
        calculate_distance(b, a).distance_m, abs=1e-6
    )


def test_longitude_latitude_not_swapped():
    d1 = calculate_distance(make_geo("A", 10.0, 20.0), make_geo("B", 30.0, 40.0))
    d2 = calculate_distance(make_geo("A", 20.0, 10.0), make_geo("B", 40.0, 30.0))
    assert abs(d1.distance_m - d2.distance_m) > 1.0


def test_dateline_short_distance():
    result = calculate_distance(make_geo("A", 179.9, 0.0), make_geo("B", -179.9, 0.0))
    # 0.2° 赤道弧长约 22.26 km，不得接近地球一周
    assert result.distance_m == pytest.approx(111319.490793 * 0.2, abs=50.0)
    assert result.distance_m < 1_000_000.0


def test_non_finite_rejected():
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", float("nan"), 0.0), make_geo("B", 1.0, 0.0))
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", 0.0, 0.0), make_geo("B", 1.0, float("inf")))


def test_out_of_range_rejected():
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", 181.0, 0.0), make_geo("B", 1.0, 0.0))
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", 0.0, 0.0), make_geo("B", 1.0, 91.0))
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", -181.0, 0.0), make_geo("B", 1.0, 0.0))
    with pytest.raises(DistanceCalculationError):
        calculate_distance(make_geo("A", 0.0, 0.0), make_geo("B", 1.0, -91.0))


def test_result_full_precision():
    a, b = make_geo("A", 0.0, 0.0), make_geo("B", 1.0, 0.0)
    result = calculate_distance(a, b)
    assert isinstance(result, DistanceResult)
    assert result.point_a_name == "A"
    assert result.point_b_name == "B"
    _, _, expected = GEOD.inv(0.0, 0.0, 1.0, 0.0)
    assert result.distance_m == pytest.approx(expected, abs=1e-9)


def test_uses_lon_lat_not_map_xy():
    # 两个 GeoPoint map_x/map_y 相同，但经纬度不同：距离必须来自经纬度
    a = GeoPoint(name="A", source_col=1.0, source_row=2.0, map_x=0.0, map_y=0.0,
                 source_crs=CRS.from_user_input("EPSG:3857"),
                 longitude=0.0, latitude=0.0)
    b = GeoPoint(name="B", source_col=1.0, source_row=2.0, map_x=0.0, map_y=0.0,
                 source_crs=CRS.from_user_input("EPSG:3857"),
                 longitude=10.0, latitude=10.0)
    result = calculate_distance(a, b)
    _, _, expected = GEOD.inv(0.0, 0.0, 10.0, 10.0)
    assert result.distance_m == pytest.approx(expected, abs=1e-6)
    assert result.distance_m > 1_000_000.0  # 若用 map 坐标欧氏距离会是 0


# --------------------------------------------------------------------------- #
# MainWindow 集成
# --------------------------------------------------------------------------- #
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


def test_main_window_distance_placeholder_after_a(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert window.distance_result is None
    assert window.distance_label.text() == "--"
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    window.close()


def test_main_window_distance_after_b(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.distance_result is not None
    assert window.distance_result.distance_m > 0
    assert "米" in window.distance_label.text()
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    # TASK-006：速度为空时提示请输入飞行速度；输入合法速度后恢复完成状态
    assert window.status_label.text() == "请输入飞行速度"
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.status_label.text() == "A/B 点选择完成"
    window.close()


def test_main_window_distance_full_precision_and_ui_format(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    _, _, expected = GEOD.inv(
        window.geo_point_a.longitude, window.geo_point_a.latitude,
        window.geo_point_b.longitude, window.geo_point_b.latitude,
    )
    # 内部保留完整精度，与独立复核一致
    assert window.distance_result.distance_m == pytest.approx(expected, abs=1e-6)
    # UI 按两位小数格式化
    assert window.distance_label.text() == f"{window.distance_result.distance_m:.2f} 米"
    window.close()


def test_third_click_does_not_change_distance(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    result_before = window.distance_result
    label_before = window.distance_label.text()
    click(window.map_view, 6, 6)
    QApplication.processEvents()
    assert window.distance_result == result_before
    assert window.distance_label.text() == label_before
    window.close()


def test_zoom_and_pan_do_not_change_distance(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    result_before = window.distance_result
    for _ in range(3):
        wheel(window.map_view, 120)
    drag(window.map_view, QPoint(300, 200), QPoint(240, 150))
    QApplication.processEvents()
    assert window.distance_result == result_before
    assert counts(window.map_view)["line"] == 1
    window.close()


def test_clear_points_resets_distance(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.distance_result is not None
    window.clear_button.click()
    QApplication.processEvents()
    assert window.distance_result is None
    assert window.distance_label.text() == "--"
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    window.close()


def test_repeated_clear_points_safe(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    window.clear_button.click()
    window.clear_button.click()
    QApplication.processEvents()
    assert window.distance_result is None
    assert window.distance_label.text() == "--"
    window.close()


def test_new_map_clears_and_recomputes_distance(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    old_distance = window.distance_result.distance_m
    data2 = np.zeros((3, 8, 8), dtype=np.uint8)
    tif2 = tmp_path / "m2.tif"
    transform2 = Affine(0.001, 0.0, 120.0, 0.0, -0.001, 30.0)
    write_tiff(tif2, data2, 3, "uint8", crs="EPSG:4326", transform=transform2)
    assert window.load_map_file(str(tif2)) is True
    QApplication.processEvents()
    assert window.distance_result is None
    assert window.distance_label.text() == "--"
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.distance_result is not None
    assert window.distance_result.distance_m != pytest.approx(old_distance, abs=1e-6)
    _, _, expected = GEOD.inv(
        window.geo_point_a.longitude, window.geo_point_a.latitude,
        window.geo_point_b.longitude, window.geo_point_b.latitude,
    )
    assert window.distance_result.distance_m == pytest.approx(expected, abs=1e-6)
    window.close()


def test_failed_load_preserves_distance(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    result_before = window.distance_result
    label_before = window.distance_label.text()
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert window.distance_result == result_before
    assert window.distance_label.text() == label_before
    assert window.geo_point_a is not None
    assert "加载失败" in window.status_label.text()
    assert counts(window.map_view)["line"] == 1
    window.close()


def test_cancel_file_dialog_keeps_distance(qapp, tmp_path, monkeypatch):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    result_before = window.distance_result
    label_before = window.distance_label.text()
    monkeypatch.setattr(
        "app.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )
    window._on_import_clicked()
    QApplication.processEvents()
    assert window.distance_result == result_before
    assert window.distance_label.text() == label_before
    window.close()


def test_distance_error_no_fake_value(qapp, tmp_path, monkeypatch):
    def boom(a, b):
        raise DistanceCalculationError("模拟距离计算失败")

    monkeypatch.setattr("app.main_window.calculate_distance", boom)
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.distance_result is None
    assert window.distance_label.text() == "--"
    assert "距离计算失败" in window.status_label.text()
    assert window.geo_point_a is not None  # 已成功得到的经纬度保留
    window.close()


def test_repeated_load_no_duplicates(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    assert window.load_map_file(str(tmp_path / "m1.tif")) is True
    QApplication.processEvents()
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert counts(window.map_view) == {"pixmap": 1, "ellipse": 2, "line": 1}
    window.clear_button.click()
    assert counts(window.map_view) == {"pixmap": 1, "ellipse": 0, "line": 0}
    window.close()

# --------------------------------------------------------------------------- #
# TASK-007C：距离显示规则（米 / 米＋公里，均两位小数）
# --------------------------------------------------------------------------- #
def test_format_distance_below_1000():
    assert MainWindow._format_distance(123.456) == "123.46 米"
    assert MainWindow._format_distance(999.994) == "999.99 米"


def test_format_distance_exactly_1000_uses_km_branch():
    assert MainWindow._format_distance(1000.0) == "1000.00 米（1.00 公里）"


def test_format_distance_above_1000():
    assert MainWindow._format_distance(1234.567) == "1234.57 米（1.23 公里）"


def test_format_distance_uses_internal_value_for_branch():
    # 内部值 <1000 时即使格式化后接近 1000 也不进入公里分支
    assert MainWindow._format_distance(999.999) == "1000.00 米"


def test_main_window_distance_above_1000_shows_km(qapp, tmp_path):
    # 使用非单位、非零原点的合法地理变换，避免 GDAL 单位矩阵警告
    transform = Affine(0.01, 0.0, 120.0, 0.0, -0.01, 30.0)
    window = make_main_window(tmp_path, name="wide.tif", crs="EPSG:4326", transform=transform)
    click(window.map_view, 0, 0)
    click(window.map_view, 7, 7)
    QApplication.processEvents()
    assert window.distance_result.distance_m >= 1000.0
    label = window.distance_label.text()
    assert "公里" in label
    assert "米" in label
    # 米与公里均两位小数：格式 xx.xx 米（x.xx 公里）
    assert "（" in label and "）" in label
    window.close()