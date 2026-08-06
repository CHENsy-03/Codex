"""TASK-006：整数速度解析、飞行时间与 HH:MM:SS 格式化测试。

使用动态数据与 Qt offscreen，不依赖 D 盘参考 ZIP。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import math

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
)
from rasterio.transform import Affine

from app.flight_time_calculator import (
    FlightTimeCalculationError,
    FlightTimeLimitError,
    FlightTimeResult,
    SpeedValidationError,
    calculate_flight_time,
    format_hhmmss,
    parse_speed_m_s,
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
# 速度解析单元测试
# --------------------------------------------------------------------------- #
@pytest.mark.parametrize("text,expected", [("1", 1), ("50", 50), ("99", 99)])
def test_valid_speeds(text, expected):
    assert parse_speed_m_s(text) == expected


@pytest.mark.parametrize(
    "text",
    [
        "0",
        "100",
        "-1",
        "+5",
        "1.5",
        "1,5",
        " 1",
        "1 ",
        " ",
        "1e2",
        "NaN",
        "inf",
        "abc",
        "5.0",
        "1_0",
        "０",  # 全角数字
    ],
)
def test_invalid_speeds_rejected(text):
    with pytest.raises(SpeedValidationError):
        parse_speed_m_s(text)


# --------------------------------------------------------------------------- #
# 飞行时间计算单元测试
# --------------------------------------------------------------------------- #
def test_no_kmh_conversion():
    # 360 m 以 10 m/s 飞行 = 36 s；若误做 km/h 换算会变成 129.6 s
    result = calculate_flight_time(360.0, 10)
    assert result.exact_seconds == pytest.approx(36.0, abs=1e-9)


def test_full_precision_distance_used():
    result = calculate_flight_time(857.9490860499758, 10)
    assert result.exact_seconds == pytest.approx(85.79490860499758, abs=1e-9)


def test_exact_seconds_full_precision():
    result = calculate_flight_time(857.9490860499758, 10)
    assert isinstance(result.exact_seconds, float)
    assert result.exact_seconds != pytest.approx(round(result.exact_seconds, 2))


def test_ceil_for_non_integer_seconds():
    result = calculate_flight_time(86.1, 10)
    assert result.exact_seconds == pytest.approx(8.61)
    assert result.rounded_seconds == 9


def test_integer_seconds_no_extra():
    result = calculate_flight_time(120.0, 10)
    assert result.exact_seconds == pytest.approx(12.0)
    assert result.rounded_seconds == 12


def test_hhmmss_from_same_rounded_seconds():
    result = calculate_flight_time(86.1, 10)
    assert result.hhmmss == format_hhmmss(result.rounded_seconds)


def test_zero_seconds_format():
    result = calculate_flight_time(0.0, 10)
    assert result.rounded_seconds == 0
    assert result.hhmmss == "00:00:00"


def test_65_seconds_format():
    assert format_hhmmss(65) == "00:01:05"


def test_359999_seconds_format():
    assert format_hhmmss(359999) == "99:59:59"
    result = calculate_flight_time(359999.0, 1)
    assert result.rounded_seconds == 359999
    assert result.hhmmss == "99:59:59"


def test_over_99_hours_rejected():
    with pytest.raises(FlightTimeLimitError):
        format_hhmmss(360000)
    with pytest.raises(FlightTimeLimitError):
        calculate_flight_time(360000.0, 1)
    # 不得截断或显示三位小时
    with pytest.raises(FlightTimeLimitError):
        format_hhmmss(360001)


def test_invalid_distance_rejected():
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(float("nan"), 10)
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(float("inf"), 10)
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(-1.0, 10)


def test_invalid_speed_type_rejected():
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(100.0, 1.5)
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(100.0, True)  # bool 不得作为合法整数
    with pytest.raises(FlightTimeCalculationError):
        calculate_flight_time(100.0, "10")


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


def test_time_placeholder_after_a(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    window.close()


def test_speed_empty_status_after_ab(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.status_label.text() == "请输入飞行速度"
    window.close()


def test_speed_after_ab_auto_computes(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    assert window.flight_time_result.speed_m_s == 10
    assert window.flight_time_label.text() == str(window.flight_time_result.rounded_seconds)
    assert window.flight_time_hms_label.text() == window.flight_time_result.hhmmss
    assert window.status_label.text() == "A/B 点选择完成"
    window.close()


def test_speed_before_ab_auto_computes(qapp, tmp_path):
    window = make_main_window(tmp_path)
    window.speed_edit.setText("10")
    click(window.map_view, 2, 2)
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.status_label.text() == "A 点已选择，请继续选择 B 点"
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.flight_time_result is not None
    assert window.flight_time_label.text() != "--"
    assert window.status_label.text() == "A/B 点选择完成"
    window.close()


def test_valid_speed_change_recomputes(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    first = window.flight_time_result
    distance_before = window.distance_result
    window.speed_edit.setText("20")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    assert window.flight_time_result.speed_m_s == 20
    assert window.flight_time_result != first
    assert window.flight_time_result.exact_seconds == pytest.approx(
        first.exact_seconds / 2.0, abs=1e-9
    )
    assert window.distance_result == distance_before  # 距离不重算
    window.close()


def test_clear_speed_clears_time(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    window.speed_edit.setText("")
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.status_label.text() == "请输入飞行速度"
    assert window.distance_label.text() != "--"
    window.close()


def test_invalid_speed_clears_time(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    window.speed_edit.setText("1.5")
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.status_label.text() == "输入错误"
    assert window.distance_label.text() != "--"
    window.close()


def test_over_99_hours_no_old_time(qapp, tmp_path):
    # EPSG:4326 + 大范围变换：两点距离约 1000+ km，speed=1 超过 99 小时
    transform = Affine(1.0, 0.0, 0.0, 0.0, -1.0, 0.0)
    window = make_main_window(tmp_path, name="wide.tif", crs="EPSG:4326", transform=transform)
    click(window.map_view, 0, 0)
    click(window.map_view, 7, 7)
    window.speed_edit.setText("1")
    QApplication.processEvents()
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.status_label.text() == "飞行时间超过99小时"
    # 点位、经纬度与距离不受影响
    assert window.geo_point_a is not None and window.geo_point_b is not None
    assert window.distance_label.text() != "--"
    assert "经度" in window.point_a_label.text()
    window.close()


def test_third_click_does_not_change_time(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    result_before = window.flight_time_result
    click(window.map_view, 6, 6)
    QApplication.processEvents()
    assert window.flight_time_result == result_before
    window.close()


def test_zoom_and_pan_do_not_change_time(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    result_before = window.flight_time_result
    for _ in range(3):
        wheel(window.map_view, 120)
    drag(window.map_view, QPoint(300, 200), QPoint(240, 150))
    QApplication.processEvents()
    assert window.flight_time_result == result_before
    window.close()


def test_clear_points_keeps_speed(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    window.clear_button.click()
    QApplication.processEvents()
    assert window.speed_edit.text() == "10"
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    assert window.distance_label.text() == "--"
    assert window.status_label.text() == "点位已清除，请重新选择 A 点"
    window.close()


def test_repeated_clear_points_safe(qapp, tmp_path):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    window.speed_edit.setText("10")
    window.clear_button.click()
    window.clear_button.click()
    QApplication.processEvents()
    assert window.speed_edit.text() == "10"
    assert window.flight_time_result is None
    window.close()


def test_new_map_keeps_speed_and_recomputes(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert window.flight_time_result is not None
    data2 = np.zeros((3, 8, 8), dtype=np.uint8)
    tif2 = tmp_path / "m2.tif"
    transform2 = Affine(0.001, 0.0, 120.0, 0.0, -0.001, 30.0)
    write_tiff(tif2, data2, 3, "uint8", crs="EPSG:4326", transform=transform2)
    assert window.load_map_file(str(tif2)) is True
    QApplication.processEvents()
    assert window.speed_edit.text() == "10"
    assert window.flight_time_result is None
    assert window.flight_time_label.text() == "--"
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert window.flight_time_result is not None
    assert window.flight_time_result.speed_m_s == 10
    assert window.status_label.text() == "A/B 点选择完成"
    window.close()


def test_failed_load_preserves_speed_and_time(qapp, tmp_path):
    window = make_main_window(tmp_path, name="good.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    time_before = window.flight_time_result
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    assert window.load_map_file(str(bad)) is False
    QApplication.processEvents()
    assert window.speed_edit.text() == "10"
    assert window.flight_time_result == time_before
    assert window.flight_time_label.text() != "--"
    assert "加载失败" in window.status_label.text()
    window.close()


def test_cancel_keeps_speed_and_time(qapp, tmp_path, monkeypatch):
    window = make_main_window(tmp_path)
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    QApplication.processEvents()
    time_before = window.flight_time_result
    monkeypatch.setattr(
        "app.main_window.QFileDialog.getOpenFileName",
        lambda *a, **k: ("", ""),
    )
    window._on_import_clicked()
    QApplication.processEvents()
    assert window.flight_time_result == time_before
    assert window.speed_edit.text() == "10"
    window.close()


def test_repeated_interactions_no_duplicates(qapp, tmp_path):
    window = make_main_window(tmp_path, name="m1.tif")
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    window.speed_edit.setText("10")
    window.speed_edit.setText("20")
    window.speed_edit.setText("10")
    QApplication.processEvents()
    assert counts(window.map_view) == {"pixmap": 1, "ellipse": 2, "line": 1}
    window.clear_button.click()
    click(window.map_view, 2, 2)
    click(window.map_view, 5, 5)
    QApplication.processEvents()
    assert counts(window.map_view) == {"pixmap": 1, "ellipse": 2, "line": 1}
    assert window.flight_time_result is not None
    window.close()