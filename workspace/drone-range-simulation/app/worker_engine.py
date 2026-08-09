"""常驻 Worker 状态机与业务操作（TASK-009）。

冻结基线：《无人机二维航程计算引擎_Java21常驻子进程集成技术设计 V1.0 冻结版》
第 10.1 节第 3 项“实现状态机、原子 load_map、三类坐标解析和冻结错误码”。

- 状态机：READY / MAP_LOADED / TERMINATING；
- 保存唯一当前地图；load_map 候选地图全部校验成功后原子替换；
- 实现 hello、load_map、calculate、shutdown 及操作级字段校验和冻结错误映射；
- 不负责 stdin/stdout 编解码（由 app.worker_protocol 负责）；
- 无模块级可变状态；单次请求失败不导致 Worker 退出。
"""

from __future__ import annotations

import math
import os
from pathlib import Path
from typing import Any, Optional

from app.coordinate_converter import CoordinateConversionError, GeoPoint
from app.distance_calculator import (
    DistanceCalculationError,
    calculate_distance,
)
from app.flight_time_calculator import (
    FlightTimeCalculationError,
    FlightTimeLimitError,
    calculate_flight_time,
)
from app.geotiff_loader import (
    GeoTiffCrsMissingError,
    GeoTiffLoadError,
    GeoTiffOpenError,
    GeoTiffTransformInvalidError,
)
from app.headless_core import (
    HeadlessMap,
    geotiff_to_wgs84,
    load_map as headless_load_map,
    map_crs_to_pixel,
    wgs84_to_pixel,
)
from app.worker_protocol import (
    COORDINATE_TYPES,
    E_CALCULATION,
    E_CRS_TRANSFORM,
    E_MAP_CRS_MISSING,
    E_MAP_NOT_FOUND,
    E_MAP_NOT_LOADED,
    E_MAP_OPEN_FAILED,
    E_MAP_TRANSFORM_INVALID,
    E_POINT_INVALID,
    E_POINT_OUT_OF_BOUNDS,
    E_POINT_TYPE,
    E_REQUEST_INVALID,
    E_SPEED_INVALID,
    E_TIME_LIMIT,
    ENGINE_VERSION,
    PROTOCOL_VERSION,
)

_STATE_READY = "READY"
_STATE_MAP_LOADED = "MAP_LOADED"
_STATE_TERMINATING = "TERMINATING"

_POINT_TYPES = ("wgs84", "map_crs", "pixel")


class WorkerProtocolError(Exception):
    """Worker 业务操作错误；code 为冻结错误码，程序行为只依赖 code。"""

    def __init__(self, code: str):
        super().__init__(code)
        self.code = code


class WorkerEngine:
    """单进程 Worker 状态与业务操作；每次进程启动只创建一个实例。"""

    def __init__(self) -> None:
        self._state = _STATE_READY
        self._current_map: Optional[HeadlessMap] = None

    @property
    def state(self) -> str:
        return self._state

    def release(self) -> None:
        """释放当前地图资源（HeadlessMap 不持有打开的文件句柄）。"""
        self._current_map = None

    # ------------------------------------------------------------------ #
    # 操作
    # ------------------------------------------------------------------ #
    def hello(self) -> dict[str, Any]:
        return {
            "protocolVersion": PROTOCOL_VERSION,
            "engineVersion": ENGINE_VERSION,
            "state": self._state,
            "coordinateTypes": list(COORDINATE_TYPES),
        }

    def shutdown(self) -> dict[str, Any]:
        self._state = _STATE_TERMINATING
        self._current_map = None
        return {"state": _STATE_TERMINATING}

    def load_map(self, request: dict[str, Any]) -> dict[str, Any]:
        """原子 load_map：候选地图全部校验成功后一次性替换当前地图。"""
        path_value = request.get("path")
        if not isinstance(path_value, str) or path_value == "":
            raise WorkerProtocolError(E_REQUEST_INVALID)
        if not os.path.isabs(path_value):
            raise WorkerProtocolError(E_REQUEST_INVALID)

        path = Path(path_value)
        if not path.exists():
            raise WorkerProtocolError(E_MAP_NOT_FOUND)
        if not path.is_file():
            raise WorkerProtocolError(E_MAP_NOT_FOUND)
        if not os.access(path, os.R_OK):
            raise WorkerProtocolError(E_MAP_NOT_FOUND)

        try:
            candidate = headless_load_map(path)
        except GeoTiffCrsMissingError:
            raise WorkerProtocolError(E_MAP_CRS_MISSING)
        except GeoTiffTransformInvalidError:
            raise WorkerProtocolError(E_MAP_TRANSFORM_INVALID)
        except GeoTiffOpenError:
            raise WorkerProtocolError(E_MAP_OPEN_FAILED)
        except GeoTiffLoadError:
            raise WorkerProtocolError(E_MAP_OPEN_FAILED)
        except CoordinateConversionError:
            raise WorkerProtocolError(E_MAP_CRS_MISSING)
        except Exception:
            raise WorkerProtocolError(E_MAP_OPEN_FAILED)

        # 原子替换：候选地图已全部校验成功，才替换当前地图并进入 MAP_LOADED
        self._current_map = candidate
        self._state = _STATE_MAP_LOADED
        metadata = candidate.metadata
        return {
            "state": _STATE_MAP_LOADED,
            "crs": metadata.crs_string,
            "width": metadata.source_width,
            "height": metadata.source_height,
            "bands": metadata.band_count,
        }

    def calculate(self, request: dict[str, Any]) -> dict[str, Any]:
        """完整 calculate：先检查地图，再校验字段、坐标与速度，最后计算。"""
        if self._state != _STATE_MAP_LOADED or self._current_map is None:
            raise WorkerProtocolError(E_MAP_NOT_LOADED)

        for field in ("pointA", "pointB", "speedMps"):
            if field not in request:
                raise WorkerProtocolError(E_REQUEST_INVALID)

        point_a = self._normalize_point("A", request["pointA"])
        point_b = self._normalize_point("B", request["pointB"])
        speed_m_s = self._parse_speed(request["speedMps"])

        geo_a = self._build_geo_point("A", point_a)
        geo_b = self._build_geo_point("B", point_b)
        try:
            distance_result = calculate_distance(geo_a, geo_b)
        except DistanceCalculationError:
            raise WorkerProtocolError(E_CALCULATION)

        try:
            flight = calculate_flight_time(distance_result.distance_m, speed_m_s)
        except FlightTimeLimitError:
            raise WorkerProtocolError(E_TIME_LIMIT)
        except FlightTimeCalculationError:
            raise WorkerProtocolError(E_CALCULATION)

        return {
            "pointA": {
                "longitude": point_a["longitude"],
                "latitude": point_a["latitude"],
            },
            "pointB": {
                "longitude": point_b["longitude"],
                "latitude": point_b["latitude"],
            },
            "distanceMeters": distance_result.distance_m,
            "exactSeconds": flight.exact_seconds,
            "roundedSeconds": flight.rounded_seconds,
            "duration": flight.hhmmss,
        }

    # ------------------------------------------------------------------ #
    # 内部：坐标与速度
    # ------------------------------------------------------------------ #
    def _normalize_point(
        self, name: str, point_obj: Any
    ) -> dict[str, float]:
        """解析并归一化单个坐标点；返回 WGS84 经纬度及内部 col/row。"""
        headless_map = self._current_map
        if headless_map is None:
            raise WorkerProtocolError(E_MAP_NOT_LOADED)
        if not isinstance(point_obj, dict):
            raise WorkerProtocolError(E_POINT_INVALID)

        point_type = point_obj.get("type")
        if not isinstance(point_type, str) or point_type not in _POINT_TYPES:
            raise WorkerProtocolError(E_POINT_TYPE)

        if point_type == "wgs84":
            longitude = self._require_number(point_obj, "longitude")
            latitude = self._require_number(point_obj, "latitude")
            if not (-180.0 <= longitude <= 180.0):
                raise WorkerProtocolError(E_POINT_INVALID)
            if not (-90.0 <= latitude <= 90.0):
                raise WorkerProtocolError(E_POINT_INVALID)
            try:
                col, row = wgs84_to_pixel(headless_map, longitude, latitude)
            except CoordinateConversionError:
                raise WorkerProtocolError(E_CRS_TRANSFORM)
            self._check_pixel_bounds(col, row)
            # 归一化响应保留原始 WGS84 数值
            return {
                "longitude": longitude,
                "latitude": latitude,
                "col": col,
                "row": row,
            }

        if point_type == "map_crs":
            x = self._require_number(point_obj, "x")
            y = self._require_number(point_obj, "y")
            try:
                col, row = map_crs_to_pixel(headless_map, x, y)
            except CoordinateConversionError:
                raise WorkerProtocolError(E_CRS_TRANSFORM)
            self._check_pixel_bounds(col, row)
            geo = geotiff_to_wgs84(headless_map, col, row, name)
            return {
                "longitude": geo.longitude,
                "latitude": geo.latitude,
                "col": col,
                "row": row,
            }

        # pixel
        col = self._require_number(point_obj, "column")
        row = self._require_number(point_obj, "row")
        self._check_pixel_bounds(col, row)
        geo = geotiff_to_wgs84(headless_map, col, row, name)
        return {
            "longitude": geo.longitude,
            "latitude": geo.latitude,
            "col": col,
            "row": row,
        }

    def _require_number(self, obj: dict[str, Any], key: str) -> float:
        if key not in obj:
            raise WorkerProtocolError(E_POINT_INVALID)
        value = obj[key]
        if isinstance(value, bool) or not isinstance(value, (int, float)):
            raise WorkerProtocolError(E_POINT_INVALID)
        if not math.isfinite(value):
            raise WorkerProtocolError(E_POINT_INVALID)
        return float(value)

    def _check_pixel_bounds(self, col: float, row: float) -> None:
        metadata = self._current_map.metadata
        if not (
            0.0 <= col < metadata.source_width
            and 0.0 <= row < metadata.source_height
        ):
            raise WorkerProtocolError(E_POINT_OUT_OF_BOUNDS)

    def _parse_speed(self, value: Any) -> int:
        if isinstance(value, bool) or not isinstance(value, int):
            raise WorkerProtocolError(E_SPEED_INVALID)
        if not (1 <= value <= 99):
            raise WorkerProtocolError(E_SPEED_INVALID)
        return value

    def _build_geo_point(self, name: str, point: dict[str, float]) -> GeoPoint:
        """用内部 col/row 复用正向转换得到 map 坐标，并以归一化 WGS84 参与距离。"""
        geo = geotiff_to_wgs84(
            self._current_map, point["col"], point["row"], name
        )
        return GeoPoint(
            name=name,
            source_col=geo.source_col,
            source_row=geo.source_row,
            map_x=geo.map_x,
            map_y=geo.map_y,
            source_crs=geo.source_crs,
            longitude=point["longitude"],
            latitude=point["latitude"],
        )
