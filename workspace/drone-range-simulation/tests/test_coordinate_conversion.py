"""TASK-004：栅格连续坐标 → 地图坐标 → WGS84 经纬度测试。

使用动态创建的数据与 Qt offscreen，不依赖 D 盘参考 ZIP。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

import numpy as np
import pytest
import rasterio
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import QApplication, QGraphicsEllipseItem, QGraphicsLineItem, QGraphicsPixmapItem
from rasterio.transform import Affine

from app.coordinate_converter import (
    CoordinateConversionError,
    CoordinateConverter,
    GeoPoint,
)
from app.main_window import MainWindow

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)


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


def wheel(view, delta, pos=None):
    if pos is None:
        pos = QPointF(view.viewport().rect().center())
    global_pos = QPointF(view.viewport().mapToGlobal(pos.toPoint()))
    ev = QWheelEvent(
        pos,
        global_pos,
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


def pixmap_count(view):
    return len([i for i in view.scene().items() if isinstance(i, QGraphicsPixmapItem)])


def ellipse_count(view):
    return len([i for i in view.scene().items() if isinstance(i, QGraphicsEllipseItem)])


def line_count(view):
    return len([i for i in view.scene().items() if isinstance(i, QGraphicsLineItem)])


# --------------------------------------------------------------------------- #
# 转换器单元测试
# --------------------------------------------------------------------------- #
def test_axis_aligned_affine():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    geo = converter.to_geo_point("A", 3.0, 4.0)
    assert geo.map_x == pytest.approx(103.0)
    assert geo.map_y == pytest.approx(196.0)


def test_continuous_coords_not_rounded():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    geo = converter.to_geo_point("A", 3.75, 4.25)
    assert geo.source_col == 3.75
    assert geo.source_row == 4.25
    assert geo.map_x == pytest.approx(103.75)
    assert geo.map_y == pytest.approx(195.75)


def test_no_half_pixel_offset():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    geo = converter.to_geo_point("A", 0.0, 0.0)
    assert geo.map_x == pytest.approx(100.0)  # c，无 0.5 偏移
    assert geo.map_y == pytest.approx(200.0)  # f，无 0.5 偏移


def test_col_row_not_swapped():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    geo = converter.to_geo_point("A", 1.0, 0.0)
    assert geo.map_x == pytest.approx(101.0)  # col -> x
    assert geo.map_y == pytest.approx(200.0)  # row 不影响 x
    geo2 = converter.to_geo_point("A", 0.0, 1.0)
    assert geo2.map_x == pytest.approx(100.0)
    assert geo2.map_y == pytest.approx(199.0)  # row -> y


def test_full_six_param_affine():
    transform = Affine(1.5, 0.2, 10.0, -0.3, 2.5, 20.0)
    converter = CoordinateConverter(transform, "EPSG:3857")
    geo = converter.to_geo_point("A", 2.5, 3.5)
    assert geo.map_x == pytest.approx(1.5 * 2.5 + 0.2 * 3.5 + 10.0)
    assert geo.map_y == pytest.approx(-0.3 * 2.5 + 2.5 * 3.5 + 20.0)


def test_epsg3857_known_points():
    converter = CoordinateConverter(Affine.identity(), "EPSG:3857")
    origin = converter.to_geo_point("A", 0.0, 0.0)
    assert origin.longitude == pytest.approx(0.0, abs=1e-9)
    assert origin.latitude == pytest.approx(0.0, abs=1e-9)

    geo = converter.to_geo_point(
        "A", 1113194.9079327357, 1118889.9748579594
    )
    assert geo.longitude == pytest.approx(10.0, abs=1e-6)
    assert geo.latitude == pytest.approx(10.0, abs=1e-6)


def test_always_xy_semantics_no_swap():
    converter = CoordinateConverter(Affine.identity(), "EPSG:3857")
    lon_only = converter.to_geo_point("A", 1113194.9079327357, 0.0)
    assert lon_only.longitude == pytest.approx(10.0, abs=1e-6)
    assert lon_only.latitude == pytest.approx(0.0, abs=1e-6)
    lat_only = converter.to_geo_point("A", 0.0, 1118889.9748579594)
    assert lat_only.longitude == pytest.approx(0.0, abs=1e-6)
    assert lat_only.latitude == pytest.approx(10.0, abs=1e-6)


def test_non_finite_source_rejected():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    with pytest.raises(CoordinateConversionError):
        converter.to_geo_point("A", float("nan"), 1.0)
    with pytest.raises(CoordinateConversionError):
        converter.to_geo_point("A", 1.0, float("inf"))
    with pytest.raises(CoordinateConversionError):
        converter.to_geo_point("A", float("inf"), float("nan"))


def test_invalid_crs_and_conversion_failure():
    with pytest.raises(CoordinateConversionError):
        CoordinateConverter(TRANSFORM, "NOT_A_REAL_CRS")

    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")

    def boom(*args, **kwargs):
        raise RuntimeError("pyproj failed")

    converter._transformer.transform = boom
    with pytest.raises(CoordinateConversionError):
        converter.to_geo_point("A", 1.0, 1.0)


def test_geopoint_full_precision_and_crs():
    converter = CoordinateConverter(TRANSFORM, "EPSG:3857")
    geo = converter.to_geo_point("A", 3.75, 4.25)
    assert isinstance(geo, GeoPoint)
    assert geo.source_col == 3.75
    assert geo.source_row == 4.25
    assert geo.map_x == pytest.approx(103.75)
    assert geo.map_y == pytest.approx(195.75)
    assert geo.source_crs.to_epsg() == 3857
    assert isinstance(geo.longitude, float)
    assert isinstance(geo.latitude, float)


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


def test_main_window_a_selected_shows_real_value(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert window.geo_point_a is not None
    assert "经度" in window.point_a_label.text()
    # map_x 为 EPSG:3857 投影坐标；经度为其转换后的 WGS84 值
    assert window.geo_point_a.map_x == pytest.approx(102.0, abs=0.5)
    assert window.geo_point_a.longitude == pytest.approx(102.0 / 111319.49079327358, abs=1e-5)
    assert window.point_b_label.text() == "--"
    assert window.distance_label.text() == "--"
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.status_label.text() == "A 点已选择，请继续选择 B 点"
    window.close()


def test_main_window_b_selected_shows_both(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert "经度" in window.point_a_label.text()
    assert "经度" in window.point_b_label.text()
    assert window.geo_point_b is not None
    # TASK-005 起距离显示真实值；时间字段仍保持 "--"
    assert "米" in window.distance_label.text()
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    # TASK-006：速度为空时提示请输入飞行速度；输入合法速度后恢复完成状态
    assert window.status_label.text() == "请输入飞行速度"
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.status_label.text() == "A/B 点选择完成"
    window.close()


def test_third_click_does_not_change_coordinates(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    a_before = window.geo_point_a
    b_before = window.geo_point_b
    label_a_before = window.point_a_label.text()
    label_b_before = window.point_b_label.text()
    click(window.map_view, 6, 6)
    QApplication.processEvents()
    assert window.geo_point_a == a_before
    assert window.geo_point_b == b_before
    assert window.point_a_label.text() == label_a_before
    assert window.point_b_label.text() == label_b_before
    window.close()


def test_zoom_and_pan_do_not_change_geo(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    a_before = window.geo_point_a
    b_before = window.geo_point_b
    for _ in range(3):
        wheel(window.map_view, 120)
    drag(window.map_view, QPoint(300, 200), QPoint(240, 150))
    QApplication.processEvents()
    assert window.geo_point_a == a_before
    assert window.geo_point_b == b_before
    assert window.map_view.point_a.source_col == pytest.approx(a_before.source_col, abs=1.0)
    assert window.map_view.point_b.source_row == pytest.approx(b_before.source_row, abs=1.0)
    window.close()


def test_clear_points_resets_labels(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.geo_point_a is not None
    window.clear_button.click()
    QApplication.processEvents()
    assert window.geo_point_a is None
    assert window.geo_point_b is None
    assert window.point_a_label.text() == "--"
    assert window.point_b_label.text() == "--"
    assert window.distance_label.text() == "--"
    assert window.status_label.text() == "点位已清除，请重新选择 A 点"
    window.close()


def test_repeated_clear_points_safe(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    window.clear_button.click()
    window.clear_button.click()
    window.clear_button.click()
    QApplication.processEvents()
    assert window.geo_point_a is None
    assert window.geo_point_b is None
    window.close()


def test_new_map_uses_new_transform_and_crs(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert window.geo_point_a is not None
    data2 = np.zeros((3, 8, 8), dtype=np.uint8)
    tif2 = tmp_path / "m2.tif"
    transform2 = Affine(0.001, 0.0, 120.0, 0.0, -0.001, 30.0)
    write_tiff(tif2, data2, 3, "uint8", crs="EPSG:4326", transform=transform2)
    assert window.load_map_file(str(tif2)) is True
    QApplication.processEvents()
    assert window.geo_point_a is None
    assert window.geo_point_b is None
    assert window.point_a_label.text() == "--"
    assert window._converter is not None
    assert window._converter.source_crs.to_epsg() == 4326
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    # EPSG:4326 下 transform 直接给出经纬度：x=120.002, y=29.998
    assert window.geo_point_a.longitude == pytest.approx(120.002, abs=1e-4)
    assert window.geo_point_a.latitude == pytest.approx(29.998, abs=1e-4)
    window.close()


def test_failed_load_preserves_geo_state(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    a_geo_before = window.geo_point_a
    b_geo_before = window.geo_point_b
    a_label_before = window.point_a_label.text()
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert window.geo_point_a == a_geo_before
    assert window.geo_point_b == b_geo_before
    assert window.point_a_label.text() == a_label_before
    assert window.current_preview is not None
    assert window._converter is not None
    assert "加载失败" in window.status_label.text()
    assert line_count(window.map_view) == 1
    window.close()


def test_cancel_file_dialog_changes_nothing(qapp, tmp_path, monkeypatch):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    a_geo_before = window.geo_point_a
    label_before = window.point_a_label.text()
    monkeypatch.setattr(
        "app.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )
    window._on_import_clicked()
    QApplication.processEvents()
    assert window.geo_point_a == a_geo_before
    assert window.point_a_label.text() == label_before
    assert window.map_view.point_a is not None
    assert window.status_label.text() == "A 点已选择，请继续选择 B 点"
    window.close()


def test_repeated_load_no_duplicate_overlays(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    assert window.load_map_file(str(tmp_path / "m1.tif")) is True
    QApplication.processEvents()
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert pixmap_count(window.map_view) == 1
    assert ellipse_count(window.map_view) == 2
    assert line_count(window.map_view) == 1
    window.clear_button.click()
    assert pixmap_count(window.map_view) == 1
    assert ellipse_count(window.map_view) == 0
    assert line_count(window.map_view) == 0
    window.close()

# --------------------------------------------------------------------------- #
# TASK-007C：经纬度显示规则（6 位小数 + °）
# --------------------------------------------------------------------------- #
def _make_geo(name, lon, lat):
    from pyproj import CRS
    return GeoPoint(
        name=name, source_col=0.0, source_row=0.0, map_x=0.0, map_y=0.0,
        source_crs=CRS.from_user_input("EPSG:3857"),
        longitude=lon, latitude=lat,
    )


def test_format_geo_positive_with_degree():
    text = MainWindow._format_geo(_make_geo("A", 120.123456, 30.123456))
    assert text == "经度 120.123456°，纬度 30.123456°"


def test_format_geo_negative_with_degree():
    text = MainWindow._format_geo(_make_geo("A", -120.123456, -30.123456))
    assert text == "经度 -120.123456°，纬度 -30.123456°"


def test_format_geo_six_decimals_rounding():
    text = MainWindow._format_geo(_make_geo("A", 120.1234567, 30.9876543))
    # 6 位小数 + °；正负号按实际值保留
    assert text == "经度 120.123457°，纬度 30.987654°"


def test_main_window_label_has_degree(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert "°" in window.point_a_label.text()
    assert window.point_b_label.text() == "--"
    window.close()