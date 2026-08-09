"""无 GUI 计算核心门面（TASK-007）。

从现有 Python 样品抽取的地图加载、坐标转换、距离与飞行时间核心，
供未来 worker_main.py 直接调用。

- 只处理直接 GeoTIFF（.tif/.tiff）路径，不处理 ZIP（ZIP 由 Java 解压）；
- 不生成地图预览、不创建 QApplication、不导入 main_window.py / map_view.py；
- 复用 app.geotiff_loader / app.coordinate_converter / app.distance_calculator /
  app.flight_time_calculator 的唯一实现，不复制或重写算法；
- 无全局可变状态，不连接数据库，不联网，不写业务数据。
"""

from __future__ import annotations

import dataclasses
from pathlib import Path

from app.coordinate_converter import CoordinateConverter, GeoPoint
from app.distance_calculator import (
    DistanceCalculationError,
    DistanceResult,
    calculate_distance,
)
from app.flight_time_calculator import (
    FlightTimeCalculationError,
    FlightTimeLimitError,
    FlightTimeResult,
    SpeedValidationError,
    calculate_flight_time,
    parse_speed_m_s,
)
from app.geotiff_loader import (
    GeoTiffLoadError,
    GeoTiffMetadata,
    load_geotiff_metadata,
)

__all__ = [
    "HeadlessMap",
    "load_map",
    "geotiff_to_wgs84",
    "wgs84_to_pixel",
    "map_crs_to_pixel",
    "calculate_distance",
    "calculate_flight_time",
    "parse_speed_m_s",
    "GeoPoint",
    "DistanceResult",
    "FlightTimeResult",
    "GeoTiffMetadata",
    "GeoTiffLoadError",
    "DistanceCalculationError",
    "FlightTimeCalculationError",
    "FlightTimeLimitError",
    "SpeedValidationError",
]


@dataclasses.dataclass(frozen=True)
class HeadlessMap:
    """一次成功加载的无 GUI 地图：元数据 + 坐标转换器（不可变）。"""

    metadata: GeoTiffMetadata
    converter: CoordinateConverter


def load_map(path: str | Path) -> HeadlessMap:
    """从直接 GeoTIFF 路径加载无 GUI 地图核心。

    仅接受 .tif/.tiff；不处理 ZIP；不生成预览；失败抛出 GeoTiffLoadError。
    """
    resolved = Path(path).resolve()
    metadata = load_geotiff_metadata(resolved)
    converter = CoordinateConverter(metadata.transform, metadata.crs)
    return HeadlessMap(metadata=metadata, converter=converter)


def geotiff_to_wgs84(
    headless_map: HeadlessMap,
    col: float,
    row: float,
    name: str = "A",
) -> GeoPoint:
    """连续零基 column/row → WGS84 longitude/latitude（复用 CoordinateConverter）。

    不取整、不自动增加 0.5；坐标轴固定为 x/y，经纬度固定为 longitude/latitude；
    内部保留完整浮点精度。
    """
    return headless_map.converter.to_geo_point(name, col, row)
def wgs84_to_pixel(
    headless_map: HeadlessMap,
    longitude: float,
    latitude: float,
) -> tuple[float, float]:
    """WGS84 经纬度 → 连续零基 column/row（复用 CoordinateConverter 逆转换）。"""
    return headless_map.converter.wgs84_to_pixel(longitude, latitude)


def map_crs_to_pixel(
    headless_map: HeadlessMap,
    x: float,
    y: float,
) -> tuple[float, float]:
    """当前地图 CRS 坐标 → 连续零基 column/row（复用逆仿射，不取整、不加 0.5）。"""
    return headless_map.converter.map_to_pixel(x, y)
