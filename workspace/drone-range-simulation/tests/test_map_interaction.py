"""TASK-003：地图缩放、平移与 A/B 点选择测试。

使用 Qt offscreen 与动态创建的数据；事件通过真实事件对象直接发送到
与 QGraphicsView 相同的公开处理函数（mousePressEvent/mouseMoveEvent/
mouseReleaseEvent/wheelEvent），不建立平行实现。
"""

import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from PySide6.QtCore import QEvent, QPoint, QPointF, Qt
from PySide6.QtGui import QMouseEvent, QWheelEvent
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsEllipseItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsSimpleTextItem,
)
from rasterio.transform import Affine

from app.map_view import MapPoint, MapView
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
# 事件构造辅助（与真实事件共用同一逻辑）
# --------------------------------------------------------------------------- #
def make_view(width=200, height=100, source_width=None, source_height=None):
    view = MapView()
    view.resize(600, 400)
    view.show()
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    view.set_preview(
        rgb,
        source_width=width if source_width is None else source_width,
        source_height=height if source_height is None else source_height,
    )
    QApplication.processEvents()
    return view


def click(view, scene_x, scene_y):
    """在场景坐标 (scene_x, scene_y) 处发送左键按下事件（浮点视口坐标）。"""
    vp = view.mapFromScene(QPointF(scene_x, scene_y))
    ev = QMouseEvent(
        QEvent.Type.MouseButtonPress,
        vp,
        QPointF(view.viewport().mapToGlobal(vp)),
        Qt.MouseButton.LeftButton,
        Qt.MouseButton.LeftButton,
        Qt.KeyboardModifier.NoModifier,
    )
    view.mousePressEvent(ev)


def wheel(view, delta, pos=None):
    """发送滚轮事件；delta 正值为向上滚动。"""
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
    """按住右键从 start 拖动到 end（视口坐标）。"""
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


def scene_line_items(view):
    return [i for i in view.scene().items() if isinstance(i, QGraphicsLineItem)]


def scene_ellipse_items(view):
    return [i for i in view.scene().items() if isinstance(i, QGraphicsEllipseItem)]


def scene_pixmap_items(view):
    return [i for i in view.scene().items() if isinstance(i, QGraphicsPixmapItem)]


# --------------------------------------------------------------------------- #
# 基础状态与无地图交互
# --------------------------------------------------------------------------- #
def test_no_map_no_points(qapp):
    view = MapView()
    assert view.point_a is None
    assert view.point_b is None
    assert view.selected_points == ()
    assert view.has_point_a is False
    assert view.has_point_b is False
    assert view.zoom_steps == 0


def test_no_map_interactions_are_safe(qapp):
    view = MapView()
    view.resize(600, 400)
    view.show()
    QApplication.processEvents()
    click(view, 50, 50)  # 无地图：不创建点位
    wheel(view, 120)
    drag(view, QPoint(200, 150), QPoint(150, 100))
    assert view.point_a is None
    assert view.point_b is None
    assert view.selected_points == ()
    assert view.zoom_steps == 0


# --------------------------------------------------------------------------- #
# 缩放
# --------------------------------------------------------------------------- #
def test_initial_zoom_zero_and_fit(qapp):
    view = make_view(200, 100)
    assert view.zoom_steps == 0
    p0 = view.mapFromScene(QPointF(0, 0))
    p1 = view.mapFromScene(QPointF(200, 100))
    assert 0 <= p0.x() < view.viewport().width()
    assert 0 <= p0.y() < view.viewport().height()
    assert p1.x() <= view.viewport().width()
    assert p1.y() <= view.viewport().height()
    # 等比例完整显示
    w = p1.x() - p0.x()
    h = p1.y() - p0.y()
    assert w > 0 and h > 0
    assert abs(w / h - 200.0 / 100.0) < 1e-3


def test_wheel_up_zooms_in(qapp):
    view = make_view(200, 100)
    before = view.transform().m11()
    wheel(view, 120)
    assert view.zoom_steps == 1
    assert view.transform().m11() > before


def test_wheel_down_restores_fit(qapp):
    view = make_view(200, 100)
    wheel(view, 120)
    wheel(view, 120)
    assert view.zoom_steps == 2
    wheel(view, -120)
    wheel(view, -120)
    assert view.zoom_steps == 0
    p0 = view.mapFromScene(QPointF(0, 0))
    p1 = view.mapFromScene(QPointF(200, 100))
    assert 0 <= p0.x() and p1.x() <= view.viewport().width()
    assert 0 <= p0.y() and p1.y() <= view.viewport().height()


def test_zoom_not_below_fit(qapp):
    view = make_view(200, 100)
    before = view.transform().m11()
    wheel(view, -120)
    assert view.zoom_steps == 0
    assert view.transform().m11() == pytest.approx(before)


def test_zoom_not_above_max(qapp):
    view = make_view(200, 100)
    for _ in range(20):
        wheel(view, 120)
    assert view.zoom_steps == 12
    before = view.transform().m11()
    wheel(view, 120)
    assert view.zoom_steps == 12
    assert view.transform().m11() == pytest.approx(before)


def test_zoom_anchor_stable(qapp):
    view = make_view(200, 100)
    anchor = QPoint(150, 120)
    scene_before = view.mapToScene(anchor)
    wheel(view, 120, QPointF(anchor))
    scene_after = view.mapToScene(anchor)
    assert abs(scene_after.x() - scene_before.x()) < 1.0
    assert abs(scene_after.y() - scene_before.y()) < 1.0


# --------------------------------------------------------------------------- #
# 平移
# --------------------------------------------------------------------------- #
def test_pan_changes_visible_area(qapp):
    view = make_view(200, 100)
    for _ in range(4):
        wheel(view, 120)
    center = QPointF(view.viewport().rect().center())
    before = view.mapToScene(center.toPoint())
    drag(view, QPoint(300, 200), QPoint(240, 150))
    after = view.mapToScene(center.toPoint())
    assert (after - before).manhattanLength() > 10


def test_pan_does_not_create_points(qapp):
    view = make_view(200, 100)
    for _ in range(3):
        wheel(view, 120)
    drag(view, QPoint(300, 200), QPoint(240, 150))
    assert view.point_a is None
    assert view.point_b is None


# --------------------------------------------------------------------------- #
# A/B 点选择
# --------------------------------------------------------------------------- #
def test_click_outside_image_ignored(qapp):
    view = make_view(200, 100)
    click(view, -20, 50)
    click(view, 250, 50)
    assert view.point_a is None
    assert view.point_b is None


def test_first_click_creates_only_a(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    assert view.has_point_a is True
    assert view.has_point_b is False
    assert len(view.selected_points) == 1
    assert view.selected_points[0].name == "A"
    assert view.point_a.scene_x == pytest.approx(40.0, abs=1.0)
    assert view.point_a.scene_y == pytest.approx(30.0, abs=1.0)


def test_second_click_creates_b_and_unique_line(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    click(view, 120, 70)
    assert view.has_point_a is True
    assert view.has_point_b is True
    assert len(view.selected_points) == 2
    assert view.selected_points[1].name == "B"
    lines = scene_line_items(view)
    assert len(lines) == 1


def test_third_click_does_not_change_points(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    click(view, 120, 70)
    a_before = view.point_a
    b_before = view.point_b
    click(view, 180, 20)
    assert view.point_a == a_before
    assert view.point_b == b_before
    assert len(view.selected_points) == 2
    assert len(scene_line_items(view)) == 1
    assert len(scene_ellipse_items(view)) == 2


def test_markers_and_line_match_positions(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    click(view, 120, 70)
    ellipses = scene_ellipse_items(view)
    assert len(ellipses) == 2
    expected = [(40.0, 30.0), (120.0, 70.0)]
    actual = sorted((e.pos().x(), e.pos().y()) for e in ellipses)
    for (ex, ey), (ax, ay) in zip(expected, actual):
        assert ax == pytest.approx(ex, abs=1.0)
        assert ay == pytest.approx(ey, abs=1.0)
    line = scene_line_items(view)[0]
    assert line.line().p1().x() == pytest.approx(40.0, abs=1.0)
    assert line.line().p1().y() == pytest.approx(30.0, abs=1.0)
    assert line.line().p2().x() == pytest.approx(120.0, abs=1.0)
    assert line.line().p2().y() == pytest.approx(70.0, abs=1.0)


def test_points_unchanged_after_zoom_and_pan(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    click(view, 120, 70)
    a_before = view.point_a
    b_before = view.point_b
    for _ in range(3):
        wheel(view, 120)
    drag(view, QPoint(300, 200), QPoint(240, 150))
    assert view.point_a == a_before
    assert view.point_b == b_before


# --------------------------------------------------------------------------- #
# 原始栅格行列映射
# --------------------------------------------------------------------------- #
def test_source_equals_scene_when_preview_is_source(qapp):
    view = make_view(100, 50, source_width=100, source_height=50)
    click(view, 25, 10)
    assert view.point_a.source_col == pytest.approx(25.0, abs=1.0)
    assert view.point_a.source_row == pytest.approx(10.0, abs=1.0)


def test_downsampled_mapping(qapp):
    view = make_view(100, 50, source_width=1000, source_height=500)
    click(view, 25, 10)
    assert view.point_a.source_col == pytest.approx(250.0, abs=5.0)
    assert view.point_a.source_row == pytest.approx(100.0, abs=5.0)


def test_col_row_not_swapped(qapp):
    view = make_view(100, 50, source_width=1000, source_height=500)
    click(view, 25, 10)
    # 横向 -> col，纵向 -> row；若交换则 source_col 应为 100
    assert view.point_a.source_col == pytest.approx(250.0, abs=5.0)
    assert view.point_a.source_row == pytest.approx(100.0, abs=5.0)


# --------------------------------------------------------------------------- #
# 清除点位
# --------------------------------------------------------------------------- #
def test_clear_points_keeps_map(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    click(view, 120, 70)
    assert len(scene_ellipse_items(view)) == 2
    assert len(scene_line_items(view)) == 1
    view.clear_points()
    assert view.has_map is True
    assert view.point_a is None
    assert view.point_b is None
    assert len(scene_ellipse_items(view)) == 0
    assert len(scene_line_items(view)) == 0
    assert len(scene_pixmap_items(view)) == 1


def test_repeated_clear_points_is_safe(qapp):
    view = make_view(200, 100)
    click(view, 40, 30)
    view.clear_points()
    view.clear_points()
    view.clear_points()
    assert view.point_a is None
    assert view.point_b is None


# --------------------------------------------------------------------------- #
# MainWindow 集成
# --------------------------------------------------------------------------- #
def make_main_window(tmp_path, name="map.tif", width=8, height=8):
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / name
    write_tiff(tif, data, 3, "uint8")
    window = MainWindow()
    window.show()
    QApplication.processEvents()
    assert window.load_map_file(str(tif)) is True
    QApplication.processEvents()
    return window, tif


def test_main_window_clear_enabled_after_a(qapp, tmp_path):
    window, _ = make_main_window(tmp_path)
    assert window.clear_button.isEnabled() is False
    click(window.map_view, 2, 2)
    assert window.map_view.has_point_a is True
    assert window.clear_button.isEnabled() is True
    assert window.status_label.text() == "A 点已选择，请继续选择 B 点"
    window.close()


def test_main_window_clear_disabled_after_clear(qapp, tmp_path):
    window, _ = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    window.clear_button.click()
    assert window.map_view.point_a is None
    assert window.map_view.point_b is None
    assert window.clear_button.isEnabled() is False
    assert window.status_label.text() == "点位已清除，请重新选择 A 点"
    window.close()


def test_result_fields_stay_placeholder(qapp, tmp_path):
    # TASK-004 起 A/B 经纬度显示真实值；TASK-005 起距离显示真实值；
    # 时间字段仍保持 "--"
    window, _ = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    assert "经度" in window.point_a_label.text()
    assert "经度" in window.point_b_label.text()
    assert "米" in window.distance_label.text()
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    window.close()


def test_new_map_clears_points_and_resets_view(qapp, tmp_path):
    window, _ = make_main_window(tmp_path, name="m1.tif", width=8, height=8)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    for _ in range(3):
        wheel(window.map_view, 120)
    assert window.map_view.zoom_steps == 3
    data2 = np.zeros((3, 6, 6), dtype=np.uint8)
    tif2 = tmp_path / "m2.tif"
    write_tiff(tif2, data2, 3, "uint8")
    assert window.load_map_file(str(tif2)) is True
    QApplication.processEvents()
    assert window.map_view.point_a is None
    assert window.map_view.point_b is None
    assert window.map_view.zoom_steps == 0
    assert window.external_filename_label.text() == "m2.tif"
    assert window.status_label.text() == "地图加载成功"
    assert len(scene_pixmap_items(window.map_view)) == 1
    window.close()


def test_failed_load_preserves_old_map_and_points(qapp, tmp_path):
    window, _ = make_main_window(tmp_path, name="good.tif", width=8, height=8)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    a_before = window.map_view.point_a
    b_before = window.map_view.point_b
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert window.map_view.has_map is True
    assert window.map_view.point_a == a_before
    assert window.map_view.point_b == b_before
    assert window.external_filename_label.text() == "good.tif"
    assert "加载失败" in window.status_label.text()
    assert len(scene_line_items(window.map_view)) == 1
    window.close()


def test_repeated_import_no_stacked_images(qapp, tmp_path):
    window, _ = make_main_window(tmp_path, name="m1.tif")
    data2 = np.zeros((3, 6, 6), dtype=np.uint8)
    tif2 = tmp_path / "m2.tif"
    write_tiff(tif2, data2, 3, "uint8")
    assert window.load_map_file(str(tif2)) is True
    assert window.load_map_file(str(tif2)) is True
    QApplication.processEvents()
    assert len(scene_pixmap_items(window.map_view)) == 1
    window.close()