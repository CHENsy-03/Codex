"""主窗口：左右布局、控件初始状态与地图数据导入。

TASK-002：接入真实加载流程（ZIP/TIF），加载成功后更新元数据与地图预览。
TASK-003：连接 MapView 点位变化信号，维护状态提示与清除点位按钮。
TASK-004：将 A/B 栅格连续坐标转换为地图坐标与 WGS84 经纬度并显示。
TASK-005：计算 A/B 两点 WGS84 椭球面测地线距离并显示。
TASK-006：整数速度（1–99 m/s）解析、飞行时间计算与 HH:MM:SS 显示。
不实现动画、三维距离、DEM、航线规划等。
"""

from typing import Optional

from PySide6.QtCore import Qt
from PySide6.QtWidgets import (
    QApplication,
    QFileDialog,
    QFormLayout,
    QGroupBox,
    QHBoxLayout,
    QLabel,
    QLineEdit,
    QMainWindow,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
    QWidget,
)

from app.coordinate_converter import (
    CoordinateConversionError,
    CoordinateConverter,
    GeoPoint,
)
from app.distance_calculator import (
    DistanceCalculationError,
    DistanceResult,
    calculate_distance,
)
from app.flight_time_calculator import (
    FlightTimeLimitError,
    FlightTimeResult,
    SpeedValidationError,
    calculate_flight_time,
    parse_speed_m_s,
)
from app.geotiff_loader import GeoTiffLoadError, GeoTiffPreview, load_geotiff
from app.map_view import MapPoint, MapView


class MainWindow(QMainWindow):
    """无人机二维航程计算样品主窗口。"""

    WINDOW_TITLE = "无人机二维航程计算样品"
    EMPTY_VALUE = "--"
    STATUS_READY = "就绪"
    STATUS_LOADING = "正在加载地图……"
    STATUS_LOADED = "地图加载成功"

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(self.WINDOW_TITLE)
        self.resize(1200, 760)
        self.setMinimumSize(900, 600)

        self.current_preview: Optional[GeoTiffPreview] = None
        self._converter: Optional[CoordinateConverter] = None
        self.geo_point_a: Optional[GeoPoint] = None
        self.geo_point_b: Optional[GeoPoint] = None
        self.distance_result: Optional[DistanceResult] = None
        self.flight_time_result: Optional[FlightTimeResult] = None
        self._speed_state = "empty"  # "empty" | "invalid" | "valid"
        self._flight_limit_exceeded = False
        self.last_error_message = ""
        self.last_coordinate_error = ""
        self.last_distance_error = ""

        central = QWidget(self)
        root_layout = QHBoxLayout(central)
        root_layout.setContentsMargins(8, 8, 8, 8)
        root_layout.setSpacing(8)

        self.map_view = MapView(central)
        self.map_view.points_changed.connect(self._on_points_changed)
        self.map_view.selection_full.connect(self._on_selection_full)
        root_layout.addWidget(self.map_view, stretch=3)

        panel = self._build_control_panel()
        root_layout.addWidget(panel, stretch=1)

        self.setCentralWidget(central)

    # ------------------------------------------------------------------ #
    # 控件构建
    # ------------------------------------------------------------------ #
    def _build_control_panel(self) -> QWidget:
        """构建右侧控制面板：地图数据组、点位与结果组、状态提示。"""
        panel = QWidget(self)
        layout = QVBoxLayout(panel)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(8)

        # 地图数据组
        map_group = QGroupBox("地图数据", panel)
        map_form = QFormLayout(map_group)
        self.import_button = QPushButton("导入地图数据", map_group)
        self.clear_button = QPushButton("清除点位", map_group)
        self.clear_button.setEnabled(False)
        self.external_filename_label = self._make_value_label()
        self.internal_image_label = self._make_value_label()
        self.crs_label = self._make_value_label()
        map_form.addRow(self.import_button)
        map_form.addRow(self.clear_button)
        map_form.addRow("外部文件名", self.external_filename_label)
        map_form.addRow("ZIP 内部影像名", self.internal_image_label)
        map_form.addRow("CRS", self.crs_label)
        layout.addWidget(map_group)

        # 点位与结果组
        result_group = QGroupBox("点位与结果", panel)
        result_form = QFormLayout(result_group)
        self.point_a_label = self._make_value_label()
        self.point_b_label = self._make_value_label()
        self.distance_label = self._make_value_label()
        self.flight_time_label = self._make_value_label()
        self.flight_time_hms_label = self._make_value_label()

        speed_row = QWidget(result_group)
        speed_layout = QHBoxLayout(speed_row)
        speed_layout.setContentsMargins(0, 0, 0, 0)
        self.speed_edit = QLineEdit(speed_row)
        self.speed_edit.setPlaceholderText("请输入速度")
        speed_unit = QLabel("m/s", speed_row)
        speed_layout.addWidget(self.speed_edit, stretch=1)
        speed_layout.addWidget(speed_unit)

        result_form.addRow("A 点经纬度", self.point_a_label)
        result_form.addRow("B 点经纬度", self.point_b_label)
        result_form.addRow("无人机速度", speed_row)
        result_form.addRow("二维距离", self.distance_label)
        result_form.addRow("飞行时间秒数", self.flight_time_label)
        result_form.addRow("HH:MM:SS", self.flight_time_hms_label)
        layout.addWidget(result_group)

        # 状态提示
        self.status_label = QLabel(self.STATUS_READY, panel)
        layout.addWidget(self.status_label)
        layout.addStretch(1)

        self.import_button.clicked.connect(self._on_import_clicked)
        self.clear_button.clicked.connect(self._on_clear_clicked)
        self.speed_edit.textChanged.connect(self._on_speed_changed)
        return panel

    def _make_value_label(self) -> QLabel:
        """创建初始值为 "--" 的只读值标签。"""
        label = QLabel(self.EMPTY_VALUE)
        label.setWordWrap(True)
        label.setTextInteractionFlags(Qt.TextInteractionFlag.TextSelectableByMouse)
        return label

    # ------------------------------------------------------------------ #
    # 点位事件与坐标派生
    # ------------------------------------------------------------------ #
    def _on_points_changed(self) -> None:
        """A/B 点状态变化时派生地理点、更新经纬度、距离、时间与状态。"""
        self._refresh_geo_points()
        self._update_flight_time(self.speed_edit.text())
        self._update_status()
        self.clear_button.setEnabled(
            self.map_view.has_point_a or self.map_view.has_point_b
        )

    def _refresh_geo_points(self) -> None:
        """根据 MapView 当前 A/B 点派生 GeoPoint 与 DistanceResult。"""
        self.last_coordinate_error = ""
        self.last_distance_error = ""
        self.geo_point_a = self._convert_point("A", self.map_view.point_a)
        self.geo_point_b = self._convert_point("B", self.map_view.point_b)
        self._update_coordinate_labels()
        self._update_distance()

    def _convert_point(
        self, name: str, point: Optional[MapPoint]
    ) -> Optional[GeoPoint]:
        if point is None or self._converter is None:
            return None
        try:
            return self._converter.to_geo_point(
                name, point.source_col, point.source_row
            )
        except CoordinateConversionError as exc:
            self.last_coordinate_error = str(exc)
            return None

    def _update_coordinate_labels(self) -> None:
        self.point_a_label.setText(self._format_geo(self.geo_point_a))
        self.point_b_label.setText(self._format_geo(self.geo_point_b))

    @staticmethod
    def _format_geo(geo: Optional[GeoPoint]) -> str:
        if geo is None:
            return MainWindow.EMPTY_VALUE
        return f"经度 {geo.longitude:.6f}°，纬度 {geo.latitude:.6f}°"

    def _update_distance(self) -> None:
        """A/B GeoPoint 均存在时计算距离并显示；失败时保持 "--"。"""
        self.distance_result = None
        if self.geo_point_a is None or self.geo_point_b is None:
            self.distance_label.setText(self.EMPTY_VALUE)
            return
        try:
            self.distance_result = calculate_distance(
                self.geo_point_a, self.geo_point_b
            )
        except DistanceCalculationError as exc:
            self.last_distance_error = str(exc)
            self.distance_label.setText(self.EMPTY_VALUE)
            return
        except Exception:
            self.last_distance_error = "距离计算失败，请重新选择点位。"
            self.distance_label.setText(self.EMPTY_VALUE)
            return
        self.distance_label.setText(self._format_distance(self.distance_result.distance_m))

    @staticmethod
    def _format_distance(distance_m: float) -> str:
        """按 V1.2：<1000 m 显示两位小数米；>=1000 m 同时显示两位小数米与公里。"""
        if distance_m < 1000.0:
            return f"{distance_m:.2f} 米"
        return f"{distance_m:.2f} 米（{distance_m / 1000.0:.2f} 公里）"

    # ------------------------------------------------------------------ #
    # 速度与飞行时间
    # ------------------------------------------------------------------ #
    def _on_speed_changed(self, text: str) -> None:
        """速度输入变化时即时重算；A/B 完整后才更新状态提示。"""
        self._update_flight_time(text)
        if self.map_view.has_point_a and self.map_view.has_point_b:
            self._update_status()

    def _update_flight_time(self, text: str) -> None:
        """根据当前速度文本与 DistanceResult 计算并显示飞行时间。"""
        self._flight_limit_exceeded = False
        if text == "":
            self._speed_state = "empty"
            speed = None
        else:
            try:
                speed = parse_speed_m_s(text)
                self._speed_state = "valid"
            except SpeedValidationError:
                speed = None
                self._speed_state = "invalid"

        self.flight_time_result = None
        self.flight_time_label.setText(self.EMPTY_VALUE)
        self.flight_time_hms_label.setText(self.EMPTY_VALUE)

        if speed is None or self.distance_result is None:
            return
        try:
            self.flight_time_result = calculate_flight_time(
                self.distance_result.distance_m, speed
            )
        except FlightTimeLimitError:
            self._flight_limit_exceeded = True
            return
        except Exception:
            return
        self.flight_time_label.setText(str(self.flight_time_result.rounded_seconds))
        self.flight_time_hms_label.setText(self.flight_time_result.hhmmss)

    def _update_status(self) -> None:
        """根据当前点位、距离与速度状态刷新状态提示。"""
        if self.last_coordinate_error:
            self.status_label.setText(f"坐标转换失败：{self.last_coordinate_error}")
            return
        if self.last_distance_error:
            self.status_label.setText(f"距离计算失败：{self.last_distance_error}")
            return
        if not self.map_view.has_point_a:
            self.status_label.setText("点位已清除，请重新选择 A 点")
            return
        if not self.map_view.has_point_b:
            self.status_label.setText("A 点已选择，请继续选择 B 点")
            return
        if self.distance_result is None:
            return
        if self._speed_state == "empty":
            self.status_label.setText("请输入飞行速度")
            return
        if self._speed_state == "invalid":
            self.status_label.setText("输入错误")
            return
        if self._flight_limit_exceeded:
            self.status_label.setText("飞行时间超过99小时")
            return
        if self.flight_time_result is None:
            self.status_label.setText("飞行时间计算失败")
            return
        self.status_label.setText("A/B 点选择完成")

    def _on_selection_full(self) -> None:
        """A/B 均已存在时再次点击的简洁提示。"""
        self.status_label.setText("A/B 点已选择，请先清除点位")

    def _on_clear_clicked(self) -> None:
        self.map_view.clear_points()

    # ------------------------------------------------------------------ #
    # 导入流程
    # ------------------------------------------------------------------ #
    def _on_import_clicked(self) -> None:
        """打开文件选择器并加载所选地图；取消选择时不改变当前状态。"""
        path, _ = QFileDialog.getOpenFileName(
            self,
            "导入地图数据",
            "",
            "地图数据 (*.zip *.tif *.tiff)",
        )
        if not path:
            return
        if not self.load_map_file(path):
            QMessageBox.warning(self, "加载失败", self.last_error_message)

    def load_map_file(self, path: str) -> bool:
        """加载地图文件；成功返回 True，失败返回 False 且保留当前状态。"""
        self.status_label.setText(self.STATUS_LOADING)
        QApplication.processEvents()
        try:
            preview = load_geotiff(path)
            converter = CoordinateConverter.from_preview(preview)
        except (GeoTiffLoadError, CoordinateConversionError) as exc:
            self.last_error_message = str(exc)
            self.status_label.setText(f"加载失败：{exc}")
            return False
        except Exception:
            self.last_error_message = (
                "无法打开地图数据，请选择有效的 .zip、.tif 或 .tiff 文件。"
            )
            self.status_label.setText(f"加载失败：{self.last_error_message}")
            return False

        # 只有完整加载且坐标转换器准备完成后才替换当前地图状态
        self.current_preview = preview
        self._converter = converter
        self.external_filename_label.setText(preview.external_filename)
        self.internal_image_label.setText(
            preview.zip_internal_path
            if preview.zip_internal_path is not None
            else self.EMPTY_VALUE
        )
        self.crs_label.setText(preview.crs_string)
        self.map_view.set_preview(
            preview.preview_rgb,
            source_width=preview.source_width,
            source_height=preview.source_height,
        )
        self.status_label.setText(self.STATUS_LOADED)
        return True