"""A/B 两点的 WGS84 椭球面二维测地线距离。

TASK-005 只实现距离：
  GeoPoint.longitude/latitude（完整精度）
    → pyproj.Geod(ellps="WGS84").inv
    → distance_m（米）

不实现速度校验、飞行时间、HH:MM:SS、三维距离或 DEM。
不依赖任何 Qt 控件、MainWindow 或界面标签。
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from pyproj import Geod

from app.coordinate_converter import GeoPoint

_GEOD = Geod(ellps="WGS84")


class DistanceCalculationError(Exception):
    """距离计算失败；message 为可直接展示给用户的中文错误。"""


@dataclasses.dataclass(frozen=True)
class DistanceResult:
    """一次成功的测地线距离结果；distance_m 保留完整浮点精度。"""

    point_a_name: str
    point_b_name: str
    distance_m: float


def calculate_distance(point_a: GeoPoint, point_b: GeoPoint) -> DistanceResult:
    """计算两个 GeoPoint 之间的 WGS84 椭球面最短测地线距离（米）。"""
    _validate_point(point_a)
    _validate_point(point_b)
    try:
        _, _, distance_m = _GEOD.inv(
            point_a.longitude,
            point_a.latitude,
            point_b.longitude,
            point_b.latitude,
        )
    except Exception as exc:
        raise DistanceCalculationError(
            "距离计算失败，请重新选择点位。"
        ) from exc
    if not math.isfinite(distance_m) or distance_m < 0:
        raise DistanceCalculationError("距离计算结果无效。")
    return DistanceResult(
        point_a_name=point_a.name,
        point_b_name=point_b.name,
        distance_m=float(distance_m),
    )


def _validate_point(point: GeoPoint) -> None:
    if not (math.isfinite(point.longitude) and math.isfinite(point.latitude)):
        raise DistanceCalculationError("点位经纬度无效（非有限数值）。")
    if not (-180.0 <= point.longitude <= 180.0):
        raise DistanceCalculationError("经度超出有效范围 [-180, 180]。")
    if not (-90.0 <= point.latitude <= 90.0):
        raise DistanceCalculationError("纬度超出有效范围 [-90, 90]。")