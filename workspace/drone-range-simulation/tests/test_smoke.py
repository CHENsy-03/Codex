"""TASK-001 冒烟测试。

覆盖：依赖可导入、主窗口创建与关闭、窗口标题、按钮初始状态、初始占位值。
"""

import os

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy
import pyproj
import rasterio
import pytest
from PySide6 import __version__ as pyside6_version
from PySide6.QtWidgets import QApplication

from app.main_window import MainWindow


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def test_dependencies_importable():
    assert pyside6_version == "6.11.1"
    assert rasterio.__version__ == "1.5.0"
    assert pyproj.__version__ == "3.7.2"
    assert numpy.__version__ == "2.5.1"


def test_main_window_creates_and_closes(qapp):
    window = MainWindow()
    window.show()
    assert window.isVisible()
    window.close()
    assert not window.isVisible()


def test_window_title(qapp):
    window = MainWindow()
    assert window.windowTitle() == "无人机二维航程计算样品"
    window.close()


def test_import_button_enabled_by_default(qapp):
    window = MainWindow()
    assert window.import_button.isEnabled()
    window.close()


def test_clear_button_disabled_by_default(qapp):
    window = MainWindow()
    assert not window.clear_button.isEnabled()
    window.close()


def test_initial_values_are_placeholder(qapp):
    window = MainWindow()
    assert window.point_a_label.text() == "--"
    assert window.point_b_label.text() == "--"
    assert window.distance_label.text() == "--"
    assert window.flight_time_label.text() == "--"
    assert window.flight_time_hms_label.text() == "--"
    window.close()