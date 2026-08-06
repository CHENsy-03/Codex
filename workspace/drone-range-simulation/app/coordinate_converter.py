"""A/B 原始栅格连续行列坐标 → 地图坐标 → WGS84 经纬度。

TASK-004 只实现坐标转换：
  source_col/source_row
    → GeoTIFF 实际 CRS 下的地图坐标（map_x/map_y，仿射变换完整六参数）
    → WGS84 经度、纬度（pyproj，always_xy=True）

不计算距离、速度或飞行时间。不依赖任何 Qt 控件或界面标签。
"""

from __future__ import annotations

import dataclasses
import math
from dataclasses import dataclass

from pyproj import CRS, Transformer
from rasterio.transform import Affine

from app.geotiff_loader import GeoTiffPreview


class CoordinateConversionError(Exception):
    """坐标转换失败；message 为可直接展示给用户的中文错误。"""


@dataclasses.dataclass(frozen=True)
class GeoPoint:
    """一个已完成坐标转换的地理点。

    内部保留完整浮点精度；source_crs 为实际使用的源 CRS。
    """

    name: str  # "A" 或 "B"
    source_col: float
    source_row: float
    map_x: float  # 实际源 CRS 下的地图横坐标
    map_y: float  # 实际源 CRS 下的地图纵坐标
    source_crs: CRS
    longitude: float  # WGS84 经度
    latitude: float  # WGS84 纬度


class CoordinateConverter:
    """基于 GeoTIFF 原始 transform 与 crs 的坐标转换器。"""

    def __init__(self, transform: Affine, crs) -> None:
        self._transform = transform
        try:
            self._crs = CRS.from_user_input(crs)
            self._transformer = Transformer.from_crs(
                self._crs, "EPSG:4326", always_xy=True
            )
        except Exception as exc:
            raise CoordinateConversionError(
                "无法建立坐标转换：源 CRS 无效。"
            ) from exc

    @classmethod
    def from_preview(cls, preview: GeoTiffPreview) -> "CoordinateConverter":
        """使用 GeoTiffPreview 中未经字符串化、未经舍入的原始 transform/crs。"""
        return cls(preview.transform, preview.crs)

    @property
    def transform(self) -> Affine:
        return self._transform

    @property
    def source_crs(self) -> CRS:
        return self._crs

    def to_geo_point(
        self, name: str, source_col: float, source_row: float
    ) -> GeoPoint:
        """将连续栅格行列坐标转换为地图坐标与 WGS84 经纬度。"""
        if not (math.isfinite(source_col) and math.isfinite(source_row)):
            raise CoordinateConversionError("点位栅格坐标无效（非有限数值）。")

        # map_x = a * col + b * row + c
        # map_y = d * col + e * row + f
        map_x = (
            self._transform.a * source_col
            + self._transform.b * source_row
            + self._transform.c
        )
        map_y = (
            self._transform.d * source_col
            + self._transform.e * source_row
            + self._transform.f
        )
        if not (math.isfinite(map_x) and math.isfinite(map_y)):
            raise CoordinateConversionError(
                "地图坐标转换失败：结果为非有限数值。"
            )

        try:
            longitude, latitude = self._transformer.transform(
                map_x, map_y, errcheck=True
            )
        except Exception as exc:
            raise CoordinateConversionError(
                "地图坐标转换到 WGS84 失败，请重新选择或更换地图。"
            ) from exc

        if not (math.isfinite(longitude) and math.isfinite(latitude)):
            raise CoordinateConversionError("WGS84 转换结果不是有限数值。")
        if not (-180.0 <= longitude <= 180.0):
            raise CoordinateConversionError("经度超出有效范围 [-180, 180]。")
        if not (-90.0 <= latitude <= 90.0):
            raise CoordinateConversionError("纬度超出有效范围 [-90, 90]。")

        return GeoPoint(
            name=name,
            source_col=float(source_col),
            source_row=float(source_row),
            map_x=float(map_x),
            map_y=float(map_y),
            source_crs=self._crs,
            longitude=float(longitude),
            latitude=float(latitude),
        )