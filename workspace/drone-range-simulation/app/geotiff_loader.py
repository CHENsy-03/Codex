"""GeoTIFF / ZIP 地图数据安全加载与预览生成。

TASK-002 只实现：输入识别、ZIP 安全检查与唯一 GeoTIFF 提取、
元数据读取校验、降采样预览生成。
不实现选点、坐标转换、距离或时间计算。
"""

from __future__ import annotations

import dataclasses
import math
import re
import tempfile
import zipfile
from pathlib import Path, PurePosixPath
from typing import Optional

import numpy as np
import rasterio
from rasterio.coords import BoundingBox
from rasterio.crs import CRS
from rasterio.enums import Resampling
from rasterio.transform import Affine

SUPPORTED_TIFF_EXTENSIONS = (".tif", ".tiff")
# 样品级 ZIP 解压大小上限：2 GiB
MAX_ARCHIVE_TIFF_BYTES = 2 * 1024 ** 3
DEFAULT_MAX_PREVIEW_SIDE = 2048
_CHUNK_SIZE = 1024 * 1024


class GeoTiffLoadError(Exception):
    """地图数据加载失败；message 为可直接展示给用户的中文错误。"""


@dataclasses.dataclass(frozen=True)
class GeoTiffPreview:
    """一次成功加载的地图数据结果。

    保留原始尺寸、预览尺寸、CRS 与仿射变换，供后续选点任务使用。
    """

    external_path: Path
    external_filename: str
    zip_internal_path: Optional[str]
    source_width: int
    source_height: int
    preview_width: int
    preview_height: int
    band_count: int
    dtype: str
    crs: CRS
    crs_string: str
    transform: Affine
    bounds: BoundingBox
    preview_rgb: np.ndarray


def load_geotiff(
    path: str | Path,
    max_preview_side: int = DEFAULT_MAX_PREVIEW_SIDE,
) -> GeoTiffPreview:
    """加载 .zip/.tif/.tiff 地图数据并生成 RGB 预览。

    加载完成后不保留任何 rasterio 数据集或 ZIP 文件句柄。
    """
    input_path = Path(path)
    if not input_path.exists() or not input_path.is_file():
        raise GeoTiffLoadError(f"文件不存在：{input_path.name}")
    ext = input_path.suffix.lower()
    if ext == ".zip":
        return _load_from_zip(input_path, max_preview_side)
    if ext in SUPPORTED_TIFF_EXTENSIONS:
        return _load_direct(input_path, max_preview_side)
    raise GeoTiffLoadError("不支持的扩展名，请选择 .zip、.tif 或 .tiff 文件。")


def _load_direct(input_path: Path, max_preview_side: int) -> GeoTiffPreview:
    try:
        return _build_preview(input_path, max_preview_side)
    except GeoTiffLoadError:
        raise
    except Exception as exc:
        raise GeoTiffLoadError(
            "无法读取地图数据，请选择有效的 .tif 或 .tiff 文件。"
        ) from exc


def _load_from_zip(zip_path: Path, max_preview_side: int) -> GeoTiffPreview:
    try:
        with zipfile.ZipFile(zip_path) as zf:
            infos = zf.infolist()
            _validate_zip_members(infos)
            tiff_infos = [info for info in infos if _is_tiff_member(info)]
            if len(tiff_infos) != 1:
                raise GeoTiffLoadError(
                    "地图数据包必须且只能包含一个 .tif/.tiff 主影像。"
                )
            main_info = tiff_infos[0]
            _validate_main_member(main_info)
            with tempfile.TemporaryDirectory(prefix="drone_geotiff_") as tmp:
                target = Path(tmp) / "primary.tif"
                _extract_member(zf, main_info, target)
                preview = _build_preview(target, max_preview_side)
                return dataclasses.replace(
                    preview,
                    external_path=zip_path,
                    external_filename=zip_path.name,
                    zip_internal_path=main_info.filename,
                )
    except GeoTiffLoadError:
        raise
    except Exception as exc:
        raise GeoTiffLoadError(
            "无法打开地图数据包，请选择有效且未加密的 ZIP 文件。"
        ) from exc


# --------------------------------------------------------------------------- #
# ZIP 安全检查
# --------------------------------------------------------------------------- #
def _validate_zip_members(infos: list[zipfile.ZipInfo]) -> None:
    """对所有 ZIP 成员做路径安全检查；任一成员不安全则整体拒绝。"""
    for info in infos:
        if not _is_safe_member_name(info.filename):
            raise GeoTiffLoadError("地图数据包包含不安全的文件路径，已拒绝导入。")


def _validate_main_member(info: zipfile.ZipInfo) -> None:
    if info.flag_bits & 0x1:
        raise GeoTiffLoadError("地图数据包主影像已加密，无法读取。")
    if info.file_size > MAX_ARCHIVE_TIFF_BYTES:
        raise GeoTiffLoadError("地图数据包内影像超过大小上限（2 GiB）。")


def _is_safe_member_name(name: str) -> bool:
    if "\x00" in name:
        return False
    norm = name.replace("\\", "/")
    if norm.startswith("/"):
        return False
    if re.match(r"^[A-Za-z]:", norm):
        return False
    parts = PurePosixPath(norm).parts
    if any(part == ".." for part in parts):
        return False
    return True


def _is_tiff_member(info: zipfile.ZipInfo) -> bool:
    name = info.filename
    if name.endswith("/"):
        return False
    lower = name.lower()
    return lower.endswith(".tif") or lower.endswith(".tiff")


def _extract_member(zf: zipfile.ZipFile, info: zipfile.ZipInfo, target: Path) -> None:
    """以分块流式方式将唯一 GeoTIFF 写入固定安全文件名。"""
    written = 0
    with zf.open(info, "r") as src, open(target, "wb") as dst:
        while True:
            chunk = src.read(_CHUNK_SIZE)
            if not chunk:
                break
            written += len(chunk)
            if written > MAX_ARCHIVE_TIFF_BYTES:
                raise GeoTiffLoadError("地图数据包内影像超过大小上限（2 GiB）。")
            dst.write(chunk)


# --------------------------------------------------------------------------- #
# 元数据读取与预览生成
# --------------------------------------------------------------------------- #
def _build_preview(raster_path: Path, max_preview_side: int) -> GeoTiffPreview:
    if max_preview_side < 1:
        raise GeoTiffLoadError("预览尺寸上限必须大于 0。")
    try:
        with rasterio.open(raster_path) as ds:
            width, height = ds.width, ds.height
            if width <= 0 or height <= 0:
                raise GeoTiffLoadError("地图影像尺寸无效。")
            if ds.crs is None:
                raise GeoTiffLoadError(
                    "无法计算：该 GeoTIFF 未包含有效坐标参考系。"
                )
            transform = ds.transform
            if not _is_valid_transform(transform):
                raise GeoTiffLoadError(
                    "无法计算：地图缺少有效地理变换信息。"
                )
            bounds = ds.bounds
            if not all(math.isfinite(float(v)) for v in bounds):
                raise GeoTiffLoadError("地图地理范围无效。")

            band_count = ds.count
            if band_count not in (1, 3, 4):
                raise GeoTiffLoadError(
                    "无法预览：当前影像波段组合暂不支持（仅支持 1/3/4 波段）。"
                )
            dtype = ds.dtypes[0] if ds.dtypes else "unknown"

            scale = min(1.0, max_preview_side / max(width, height))
            preview_width = max(1, int(round(width * scale)))
            preview_height = max(1, int(round(height * scale)))

            indexes = (1,) if band_count == 1 else (1, 2, 3)
            data = ds.read(
                indexes=indexes,
                out_shape=(len(indexes), preview_height, preview_width),
                resampling=Resampling.average,
            )
            preview_rgb = _normalize_to_rgb(data)

            return GeoTiffPreview(
                external_path=Path(raster_path),
                external_filename=Path(raster_path).name,
                zip_internal_path=None,
                source_width=width,
                source_height=height,
                preview_width=preview_width,
                preview_height=preview_height,
                band_count=band_count,
                dtype=dtype,
                crs=ds.crs,
                crs_string=_crs_display_string(ds.crs),
                transform=transform,
                bounds=bounds,
                preview_rgb=preview_rgb,
            )
    except GeoTiffLoadError:
        raise
    except Exception as exc:
        raise GeoTiffLoadError(
            "无法读取地图数据，请选择有效的 .zip、.tif 或 .tiff 文件。"
        ) from exc


def _crs_display_string(crs: CRS) -> str:
    epsg = crs.to_epsg()
    if epsg is not None:
        return f"EPSG:{epsg}"
    return crs.to_string()


def _is_valid_transform(transform: Affine) -> bool:
    try:
        vals = (
            transform.a,
            transform.b,
            transform.c,
            transform.d,
            transform.e,
            transform.f,
        )
        if not all(math.isfinite(float(v)) for v in vals):
            return False
        det = transform.a * transform.e - transform.b * transform.d
        return math.isfinite(det) and det != 0
    except Exception:
        return False


def _normalize_to_rgb(data: np.ndarray) -> np.ndarray:
    """将 (bands, H, W) 读取结果转换为 (H, W, 3) uint8 C 连续 RGB。"""
    band_count = data.shape[0]
    height, width = data.shape[1], data.shape[2]
    rgb = np.zeros((height, width, 3), dtype=np.uint8)
    channels = 1 if band_count == 1 else 3
    for i in range(channels):
        rgb[..., i] = _band_to_uint8(data[i])
    if band_count == 1:
        rgb[..., 1] = rgb[..., 0]
        rgb[..., 2] = rgb[..., 0]
    return np.ascontiguousarray(rgb)


def _band_to_uint8(band: np.ndarray) -> np.ndarray:
    """单波段安全转 uint8；处理 nodata/masked/NaN/常量/无有效像素。"""
    if np.ma.isMaskedArray(band):
        valid = ~np.ma.getmaskarray(band)
        arr = np.ma.filled(band, np.nan).astype(np.float64, copy=False)
        arr = np.where(valid, arr, np.nan)
    else:
        arr = band.astype(np.float64, copy=False)
        valid = np.isfinite(arr)

    if not valid.any():
        return np.zeros(arr.shape, dtype=np.uint8)

    if band.dtype == np.dtype("uint8"):
        # uint8 保留原始亮度
        out = np.zeros(arr.shape, dtype=np.uint8)
        out[valid] = np.clip(arr[valid], 0, 255).astype(np.uint8)
        return out

    lo = float(np.percentile(arr[valid], 2))
    hi = float(np.percentile(arr[valid], 98))
    if not math.isfinite(lo) or not math.isfinite(hi) or hi <= lo:
        # 常量波段：稳定显示，不产生除零或 NaN 警告
        const_value = float(arr[valid][0]) if arr[valid].size else 0.0
        fill = 128 if const_value != 0 else 0
        out = np.zeros(arr.shape, dtype=np.uint8)
        out[valid] = fill
        return out

    scaled = (arr - lo) / (hi - lo) * 255.0
    out = np.zeros(arr.shape, dtype=np.uint8)
    out[valid] = np.clip(scaled[valid], 0, 255).astype(np.uint8)
    return out