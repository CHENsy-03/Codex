"""地图视图：预览显示、缩放、平移与 A/B 点选择。

TASK-003：实现滚轮缩放（受限）、右键拖动平移、左键依次选择 A/B 点、
标记与连线，并保存原始栅格连续行列坐标。
不实现投影坐标、经纬度、距离或时间计算。

视图变换设计：
- 关闭滚动条、缩放锚点设为 NoAnchor；
- 场景矩形在影像四周保留足够边距，使可滚动内容始终大于视口，
  从而 mapToScene 与 transform 逆矩阵完全一致（无隐藏对齐偏移）；
- 缩放使用经典的 scale + translate 锚点补偿，保持鼠标指向场景位置稳定。
"""

import dataclasses
from dataclasses import dataclass

import numpy as np
from PySide6.QtCore import QLineF, QPointF, QRectF, Qt, Signal
from PySide6.QtGui import QColor, QImage, QPainter, QPen, QPixmap, QTransform
from PySide6.QtWidgets import (
    QGraphicsEllipseItem,
    QGraphicsItem,
    QGraphicsLineItem,
    QGraphicsPixmapItem,
    QGraphicsScene,
    QGraphicsSimpleTextItem,
    QGraphicsView,
)


@dataclasses.dataclass(frozen=True)
class MapPoint:
    """一个已选择的图像点。

    只保存场景/预览坐标与原始栅格连续行列坐标，不保存经纬度。
    """

    name: str  # "A" 或 "B"
    scene_x: float  # 预览图/场景横坐标
    scene_y: float  # 预览图/场景纵坐标
    source_col: float  # 原始栅格连续列坐标
    source_row: float  # 原始栅格连续行坐标


class MapView(QGraphicsView):
    """地图视图：未加载地图时显示提示文字，加载后支持缩放、平移与选点。"""

    EMPTY_HINT = "请导入地图数据"
    ZOOM_STEP_FACTOR = 1.25
    MAX_ZOOM_STEPS = 12
    COLOR_A = QColor("#1a73e8")  # 蓝
    COLOR_B = QColor("#e53935")  # 红
    LINE_COLOR = QColor("#f9a825")

    points_changed = Signal()
    selection_full = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._scene = QGraphicsScene(self)
        self.setScene(self._scene)
        self.setBackgroundBrush(QColor("#e8eaed"))
        self.setRenderHint(QPainter.RenderHint.SmoothPixmapTransform, True)
        # 关闭滚动条，缩放/平移完全由视图变换控制
        self.setHorizontalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setVerticalScrollBarPolicy(Qt.ScrollBarPolicy.ScrollBarAlwaysOff)
        self.setTransformationAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setResizeAnchor(QGraphicsView.ViewportAnchor.NoAnchor)
        self.setToolTip("左键选择 A/B 点；滚轮缩放；按住右键拖动平移")

        self._image_item: QGraphicsPixmapItem | None = None
        self._hint_item: QGraphicsSimpleTextItem | None = None
        self._point_a: MapPoint | None = None
        self._point_b: MapPoint | None = None
        self._line_item: QGraphicsLineItem | None = None
        self._marker_items: dict[str, list[QGraphicsItem]] = {}
        self._panning = False
        self._last_pan_pos = QPointF()
        self._zoom_steps = 0
        self._preview_width = 0
        self._preview_height = 0
        self._source_width = 0
        self._source_height = 0
        self._show_empty_hint()

    # ------------------------------------------------------------------ #
    # 只读状态
    # ------------------------------------------------------------------ #
    @property
    def has_map(self) -> bool:
        """当前是否已加载地图图片。"""
        return self._image_item is not None

    @property
    def point_a(self) -> MapPoint | None:
        return self._point_a

    @property
    def point_b(self) -> MapPoint | None:
        return self._point_b

    @property
    def has_point_a(self) -> bool:
        return self._point_a is not None

    @property
    def has_point_b(self) -> bool:
        return self._point_b is not None

    @property
    def selected_points(self) -> tuple[MapPoint, ...]:
        """按选择顺序返回已有点位（A 在前，B 在后）。"""
        points = []
        if self._point_a is not None:
            points.append(self._point_a)
        if self._point_b is not None:
            points.append(self._point_b)
        return tuple(points)

    @property
    def zoom_steps(self) -> int:
        """当前缩放步级；0 表示完整适应窗口。"""
        return self._zoom_steps

    # ------------------------------------------------------------------ #
    # 预览设置
    # ------------------------------------------------------------------ #
    def set_preview(
        self,
        rgb: np.ndarray,
        source_width: int | None = None,
        source_height: int | None = None,
    ) -> None:
        """设置 RGB 预览图（(H, W, 3) uint8）。

        可传入原始栅格宽高；未传时默认原始尺寸等于预览尺寸。
        新地图会重置点位、连线、缩放与平移状态。
        """
        if rgb.ndim != 3 or rgb.shape[2] != 3:
            raise ValueError("预览数组必须为 (H, W, 3)")
        arr = np.ascontiguousarray(rgb, dtype=np.uint8)
        height, width = arr.shape[0], arr.shape[1]
        # 深拷贝，避免引用会失效的 NumPy 内存
        image = QImage(
            arr.data,
            width,
            height,
            3 * width,
            QImage.Format.Format_RGB888,
        ).copy()
        pixmap = QPixmap.fromImage(image)

        self._clear_scene_items()
        self._image_item = QGraphicsPixmapItem(pixmap)
        self._image_item.setZValue(0)
        self._scene.addItem(self._image_item)
        # 在影像四周保留足够边距，保证可滚动内容始终大于视口
        margin = 2 * max(width, height)
        self._scene.setSceneRect(
            QRectF(-margin, -margin, width + 2 * margin, height + 2 * margin)
        )

        self._preview_width = width
        self._preview_height = height
        self._source_width = width if source_width is None else int(source_width)
        self._source_height = height if source_height is None else int(source_height)
        self._zoom_steps = 0
        self._panning = False
        self._fit_to_view()
        self.points_changed.emit()

    # ------------------------------------------------------------------ #
    # 点位操作
    # ------------------------------------------------------------------ #
    def clear_points(self) -> None:
        """清除 A/B 点、标记与连线；保留地图图片。可重复调用。"""
        if self._line_item is not None:
            self._scene.removeItem(self._line_item)
            self._line_item = None
        for items in self._marker_items.values():
            for item in items:
                self._scene.removeItem(item)
        self._marker_items = {}
        self._point_a = None
        self._point_b = None
        self.points_changed.emit()

    def _handle_left_click(self, scene_pos: QPointF) -> None:
        """处理一次左键点击的场景坐标；仅接受图像半开区间内点击。"""
        if self._image_item is None:
            return
        x, y = scene_pos.x(), scene_pos.y()
        if not (
            0.0 <= x < self._preview_width and 0.0 <= y < self._preview_height
        ):
            return
        if self._point_a is not None and self._point_b is not None:
            self.selection_full.emit()
            return

        name = "A" if self._point_a is None else "B"
        source_col = x * self._source_width / self._preview_width
        source_row = y * self._source_height / self._preview_height
        point = MapPoint(
            name=name,
            scene_x=x,
            scene_y=y,
            source_col=source_col,
            source_row=source_row,
        )
        if name == "A":
            self._point_a = point
        else:
            self._point_b = point
        self._add_marker(point)
        if self._point_b is not None:
            self._add_line()
        self.points_changed.emit()

    def _add_marker(self, point: MapPoint) -> None:
        """添加可见圆形标记与字母标签（保持屏幕尺寸）。"""
        color = self.COLOR_A if point.name == "A" else self.COLOR_B
        radius = 8.0
        ellipse = QGraphicsEllipseItem(-radius, -radius, 2 * radius, 2 * radius)
        ellipse.setBrush(color)
        ellipse.setPen(QPen(QColor("#ffffff"), 2))
        ellipse.setPos(point.scene_x, point.scene_y)
        ellipse.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )
        ellipse.setZValue(1)
        self._scene.addItem(ellipse)

        text = QGraphicsSimpleTextItem(point.name)
        font = text.font()
        font.setBold(True)
        font.setPointSize(11)
        text.setFont(font)
        text.setBrush(QColor("#ffffff"))
        text.setPos(point.scene_x + radius * 0.8, point.scene_y - radius * 1.8)
        text.setFlag(
            QGraphicsItem.GraphicsItemFlag.ItemIgnoresTransformations, True
        )
        text.setZValue(2)
        self._scene.addItem(text)

        self._marker_items[point.name] = [ellipse, text]

    def _add_line(self) -> None:
        """在 A/B 之间添加唯一连线（cosmetic pen，保持可见宽度）。"""
        if self._point_a is None or self._point_b is None:
            return
        line = QGraphicsLineItem(
            QLineF(
                self._point_a.scene_x,
                self._point_a.scene_y,
                self._point_b.scene_x,
                self._point_b.scene_y,
            )
        )
        pen = QPen(self.LINE_COLOR, 2)
        pen.setCosmetic(True)
        line.setPen(pen)
        line.setZValue(1)
        self._scene.addItem(line)
        self._line_item = line

    # ------------------------------------------------------------------ #
    # 视图变换：适应 / 缩放 / 平移
    # ------------------------------------------------------------------ #
    def _current_fit_scale(self) -> float:
        """当前窗口下整幅地图完整适应所需的比例。"""
        rect = self._image_item.boundingRect()
        vw = self.viewport().width()
        vh = self.viewport().height()
        if vw <= 0 or vh <= 0 or rect.isEmpty():
            return 1.0
        return min(vw / rect.width(), vh / rect.height())

    def _set_scale_offset(self, scale: float, ox: float, oy: float) -> None:
        """直接设置视图变换：p' = p * scale + (ox, oy)。"""
        self.setTransform(
            QTransform(
                scale, 0.0, 0.0,
                0.0, scale, 0.0,
                float(ox), float(oy), 1.0,
            )
        )
        self._sync_scrollbars()

    def _sync_scrollbars(self) -> None:
        """将隐藏滚动条归零，保证 mapToScene 与 transform 逆矩阵一致。"""
        self.horizontalScrollBar().setValue(0)
        self.verticalScrollBar().setValue(0)

    def _fit_to_view(self) -> None:
        """将整幅地图完整、居中适应窗口（缩放步级 0）。"""
        if self._image_item is None:
            return
        rect = self._image_item.boundingRect()
        vw = self.viewport().width()
        vh = self.viewport().height()
        if vw <= 0 or vh <= 0 or rect.isEmpty():
            return
        scale = min(vw / rect.width(), vh / rect.height())
        ox = (vw - rect.width() * scale) / 2.0
        oy = (vh - rect.height() * scale) / 2.0
        self._set_scale_offset(scale, ox, oy)

    def _zoom_step(self, factor: float, anchor: QPointF) -> None:
        """围绕视口锚点缩放一步，保持锚点下的场景位置稳定。"""
        old = self.mapToScene(anchor.toPoint())
        self.scale(factor, factor)
        new = self.mapToScene(anchor.toPoint())
        self.translate(new.x() - old.x(), new.y() - old.y())
        self._sync_scrollbars()

    def _on_view_resized(self) -> None:
        if self._image_item is None:
            return
        if self._zoom_steps == 0:
            self._fit_to_view()
            return
        center = QPointF(self.viewport().rect().center())
        old_scene = self.mapToScene(center.toPoint())
        scale = self._current_fit_scale() * (self.ZOOM_STEP_FACTOR ** self._zoom_steps)
        ox = center.x() - old_scene.x() * scale
        oy = center.y() - old_scene.y() * scale
        self._set_scale_offset(scale, ox, oy)

    def wheelEvent(self, event):
        if self._image_item is None:
            super().wheelEvent(event)
            return
        delta = event.angleDelta().y()
        if delta == 0:
            event.accept()
            return
        zoom_in = delta > 0
        if zoom_in and self._zoom_steps >= self.MAX_ZOOM_STEPS:
            event.accept()
            return
        if not zoom_in and self._zoom_steps <= 0:
            event.accept()
            return
        if zoom_in:
            self._zoom_steps += 1
            self._zoom_step(self.ZOOM_STEP_FACTOR, event.position())
        else:
            self._zoom_steps -= 1
            if self._zoom_steps == 0:
                self._fit_to_view()
            else:
                self._zoom_step(1.0 / self.ZOOM_STEP_FACTOR, event.position())
        event.accept()

    def mousePressEvent(self, event):
        if event.button() == Qt.MouseButton.LeftButton:
            if self._image_item is not None:
                scene_pos = self.mapToScene(event.position().toPoint())
                self._handle_left_click(scene_pos)
            event.accept()
            return
        if event.button() == Qt.MouseButton.RightButton and self._image_item is not None:
            self._panning = True
            self._last_pan_pos = event.position()
            self.viewport().setCursor(Qt.CursorShape.ClosedHandCursor)
            event.accept()
            return
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._panning and self._image_item is not None:
            delta = event.position() - self._last_pan_pos
            self._last_pan_pos = event.position()
            self.translate(delta.x(), delta.y())
            self._sync_scrollbars()
            event.accept()
            return
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._panning and event.button() == Qt.MouseButton.RightButton:
            self._panning = False
            self.viewport().unsetCursor()
            event.accept()
            return
        super().mouseReleaseEvent(event)

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self._on_view_resized()

    # ------------------------------------------------------------------ #
    # 场景管理
    # ------------------------------------------------------------------ #
    def _show_empty_hint(self) -> None:
        self._clear_scene_items()
        hint = QGraphicsSimpleTextItem(self.EMPTY_HINT)
        font = hint.font()
        font.setPointSize(16)
        hint.setFont(font)
        hint.setBrush(QColor("#5f6368"))
        self._scene.addItem(hint)
        self._hint_item = hint
        rect = hint.boundingRect()
        hint.setPos(-rect.width() / 2.0, -rect.height() / 2.0)
        self._scene.setSceneRect(
            -rect.width() / 2.0,
            -rect.height() / 2.0,
            rect.width(),
            rect.height(),
        )

    def _clear_scene_items(self) -> None:
        self._scene.clear()
        self._image_item = None
        self._hint_item = None
        self._line_item = None
        self._marker_items = {}
        self._point_a = None
        self._point_b = None
        self._panning = False