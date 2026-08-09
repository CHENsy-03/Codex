"""TASK-002：GeoTIFF/ZIP 安全加载与地图预览测试。

测试数据全部通过 pytest 临时目录动态创建，不依赖开发者机器上的固定路径。
"""

import os
import zipfile

os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

import numpy as np
import pytest
import rasterio
from PySide6.QtWidgets import (
    QApplication,
    QGraphicsPixmapItem,
    QGraphicsSimpleTextItem,
)
from rasterio.transform import Affine

from app.geotiff_loader import GeoTiffLoadError, load_geotiff
from app.map_view import MapView
from app.main_window import MainWindow

TRANSFORM = Affine(1.0, 0.0, 100.0, 0.0, -1.0, 200.0)


@pytest.fixture(scope="session")
def qapp():
    app = QApplication.instance() or QApplication([])
    yield app


def write_tiff(path, data, count, dtype, crs="EPSG:3857", transform=TRANSFORM, nodata=None):
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
        nodata=nodata,
    ) as dst:
        for i in range(count):
            dst.write(data[i], i + 1)


def make_zip(tmp_path, entries):
    zpath = tmp_path / "map.zip"
    with zipfile.ZipFile(zpath, "w") as zf:
        for name, content in entries:
            zf.writestr(name, content)
    return zpath


def tif_bytes_of(data, count, dtype, crs="EPSG:3857", transform=TRANSFORM, nodata=None):
    import tempfile

    with tempfile.TemporaryDirectory(prefix="drone_test_") as tmp:
        p = os.path.join(tmp, "t.tif")
        write_tiff(p, data, count, dtype, crs=crs, transform=transform, nodata=nodata)
        with open(p, "rb") as f:
            return f.read()


# --------------------------------------------------------------------------- #
# 直接 GeoTIFF 加载
# --------------------------------------------------------------------------- #
def test_three_band_direct_load(tmp_path):
    height, width = 10, 12
    data = np.zeros((3, height, width), dtype=np.uint8)
    data[0] = 10
    data[1] = 20
    data[2] = 30
    tif = tmp_path / "rgb.tif"
    write_tiff(tif, data, 3, "uint8")
    preview = load_geotiff(tif)
    assert preview.source_width == width
    assert preview.source_height == height
    assert preview.preview_width == width
    assert preview.preview_height == height
    assert preview.band_count == 3
    assert preview.dtype == "uint8"
    assert preview.crs.to_epsg() == 3857
    assert preview.crs_string == "EPSG:3857"
    assert preview.zip_internal_path is None
    assert preview.external_filename == "rgb.tif"
    assert preview.preview_rgb.shape == (height, width, 3)
    assert preview.preview_rgb.dtype == np.uint8
    assert preview.preview_rgb.flags["C_CONTIGUOUS"]
    assert preview.preview_rgb[0, 0].tolist() == [10, 20, 30]


def test_single_band_gray_to_rgb(tmp_path):
    height, width = 5, 7
    data = np.full((1, height, width), 77, dtype=np.uint8)
    tif = tmp_path / "gray.tif"
    write_tiff(tif, data, 1, "uint8")
    preview = load_geotiff(tif)
    rgb = preview.preview_rgb
    assert rgb.shape == (height, width, 3)
    assert np.array_equal(rgb[..., 0], rgb[..., 1])
    assert np.array_equal(rgb[..., 1], rgb[..., 2])
    assert rgb[0, 0].tolist() == [77, 77, 77]


def test_four_band_uses_first_three(tmp_path):
    height, width = 4, 4
    data = np.zeros((4, height, width), dtype=np.uint8)
    data[0] = 1
    data[1] = 2
    data[2] = 3
    data[3] = 255
    tif = tmp_path / "rgba.tif"
    write_tiff(tif, data, 4, "uint8")
    preview = load_geotiff(tif)
    assert preview.band_count == 4
    assert preview.preview_rgb[0, 0].tolist() == [1, 2, 3]


def test_uint16_normalized_to_uint8(tmp_path):
    height, width = 8, 8
    data = np.zeros((1, height, width), dtype=np.uint16)
    data[0] = np.linspace(0, 65535, height * width, dtype=np.uint16).reshape(height, width)
    tif = tmp_path / "u16.tif"
    write_tiff(tif, data, 1, "uint16")
    preview = load_geotiff(tif)
    rgb = preview.preview_rgb
    assert rgb.dtype == np.uint8
    assert rgb.shape == (height, width, 3)
    assert rgb.min() <= 1
    assert rgb.max() >= 254


def test_preview_caps_at_2048(tmp_path):
    height, width = 100, 2050
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "wide.tif"
    write_tiff(tif, data, 3, "uint8")
    preview = load_geotiff(tif)
    assert preview.source_width == 2050
    assert preview.preview_width == 2048
    assert preview.preview_height >= 1
    assert preview.preview_height <= height
    assert preview.preview_rgb.shape == (preview.preview_height, 2048, 3)


def test_small_image_not_upscaled(tmp_path):
    height, width = 5, 6
    data = np.zeros((1, height, width), dtype=np.uint8)
    tif = tmp_path / "small.tif"
    write_tiff(tif, data, 1, "uint8")
    preview = load_geotiff(tif)
    assert preview.preview_width == width
    assert preview.preview_height == height


def test_metadata_preserved(tmp_path):
    transform = Affine(2.5, 0.0, 500000.0, 0.0, -2.5, 4000000.0)
    data = np.zeros((3, 20, 30), dtype=np.uint8)
    tif = tmp_path / "meta.tif"
    write_tiff(tif, data, 3, "uint8", crs="EPSG:32650", transform=transform)
    preview = load_geotiff(tif)
    assert preview.transform == transform
    assert preview.crs.to_epsg() == 32650
    assert preview.crs_string == "EPSG:32650"
    assert preview.bounds.left == 500000.0
    assert preview.bounds.top == 4000000.0
    assert preview.source_width == 30
    assert preview.source_height == 20


def test_missing_crs_rejected(tmp_path):
    data = np.zeros((1, 4, 4), dtype=np.uint8)
    tif = tmp_path / "nocrs.tif"
    write_tiff(tif, data, 1, "uint8", crs=None)
    with pytest.raises(GeoTiffLoadError, match="坐标参考系"):
        load_geotiff(tif)


def test_corrupt_tif_rejected(tmp_path):
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"not a tiff at all" * 100)
    with pytest.raises(GeoTiffLoadError):
        load_geotiff(bad)


def test_unsupported_extension_fails(tmp_path):
    f = tmp_path / "data.txt"
    f.write_text("hello")
    with pytest.raises(GeoTiffLoadError, match="不支持的扩展名"):
        load_geotiff(f)


def test_missing_file_fails(tmp_path):
    with pytest.raises(GeoTiffLoadError, match="文件不存在"):
        load_geotiff(tmp_path / "nope.tif")


# --------------------------------------------------------------------------- #
# ZIP 安全加载
# --------------------------------------------------------------------------- #
def test_zip_with_nested_tif_and_aux_files(tmp_path):
    height, width = 6, 6
    data = np.zeros((3, height, width), dtype=np.uint8)
    data[0] = 1
    data[1] = 2
    data[2] = 3
    tif_bytes = tif_bytes_of(data, 3, "uint8")
    zpath = make_zip(
        tmp_path,
        [
            ("地图包/Rectangle_#1_卫图_Level_15.tif", tif_bytes),
            ("地图包/Rectangle_#1_卫图_Level_15.tfw", "1.0\n0.0\n0.0\n-1.0\n100.0\n200.0\n"),
            ("地图包/说明.txt", "说明"),
            ("地图包/范围.kml", "<kml/>"),
            ("地图包/使用帮助.url", "[InternetShortcut]"),
            ("地图包/手机版APP安装.jpg", b"jpeg"),
        ],
    )
    preview = load_geotiff(zpath)
    assert preview.external_filename == "map.zip"
    assert preview.zip_internal_path == "地图包/Rectangle_#1_卫图_Level_15.tif"
    assert preview.source_width == width
    assert preview.source_height == height
    assert preview.preview_rgb[0, 0].tolist() == [1, 2, 3]


def test_zip_without_tif_fails(tmp_path):
    zpath = make_zip(tmp_path, [("readme.txt", "x")])
    with pytest.raises(GeoTiffLoadError, match="只能包含一个"):
        load_geotiff(zpath)


def test_zip_with_multiple_tifs_fails(tmp_path):
    zpath = make_zip(tmp_path, [("a.tif", b"x"), ("b.tiff", b"y")])
    with pytest.raises(GeoTiffLoadError, match="只能包含一个"):
        load_geotiff(zpath)


@pytest.mark.parametrize(
    "member",
    [
        "../escape.tif",
        "..\\escape.tif",
        "a/../../escape.tif",
        "/abs.tif",
        "C:/evil.tif",
    ],
)
def test_zip_path_traversal_rejected(tmp_path, member):
    zpath = make_zip(tmp_path, [(member, b"tif")])
    with pytest.raises(GeoTiffLoadError):
        load_geotiff(zpath)
    assert not (tmp_path / "escape.tif").exists()
    assert not (tmp_path.parent / "escape.tif").exists()


def test_zip_unsafe_aux_member_rejected(tmp_path):
    data = np.zeros((1, 2, 2), dtype=np.uint8)
    tif_bytes = tif_bytes_of(data, 1, "uint8")
    zpath = make_zip(tmp_path, [("ok.tif", tif_bytes), ("../bad.txt", "x")])
    with pytest.raises(GeoTiffLoadError):
        load_geotiff(zpath)


# --------------------------------------------------------------------------- #
# 预览数组与异常数据
# --------------------------------------------------------------------------- #
def test_preview_array_properties(tmp_path):
    height, width = 9, 11
    data = np.zeros((3, height, width), dtype=np.uint8)
    tif = tmp_path / "prop.tif"
    write_tiff(tif, data, 3, "uint8")
    preview = load_geotiff(tif)
    rgb = preview.preview_rgb
    assert rgb.shape == (height, width, 3)
    assert rgb.dtype == np.uint8
    assert rgb.flags["C_CONTIGUOUS"]


def test_constant_band_does_not_crash(tmp_path):
    data = np.full((1, 8, 8), 50, dtype=np.uint8)
    tif = tmp_path / "const.tif"
    write_tiff(tif, data, 1, "uint8")
    preview = load_geotiff(tif)
    assert np.all(preview.preview_rgb == 50)


def test_nodata_masked_does_not_crash(tmp_path):
    data = np.zeros((1, 8, 8), dtype=np.uint8)
    data[0, 2:6, 2:6] = 100
    tif = tmp_path / "nodata.tif"
    write_tiff(tif, data, 1, "uint8", nodata=0)
    preview = load_geotiff(tif)
    assert preview.preview_rgb.shape == (8, 8, 3)


def test_nan_float_does_not_crash(tmp_path):
    data = np.full((1, 8, 8), np.nan, dtype=np.float32)
    data[0, 1, 1] = 0.5
    tif = tmp_path / "nan.tif"
    write_tiff(tif, data, 1, "float32")
    preview = load_geotiff(tif)
    assert preview.preview_rgb.dtype == np.uint8
    assert preview.preview_rgb.shape == (8, 8, 3)


# --------------------------------------------------------------------------- #
# MapView 预览显示
# --------------------------------------------------------------------------- #
def test_map_view_initial_empty_hint(qapp):
    view = MapView()
    assert view.has_map is False
    texts = [
        item.text()
        for item in view.scene().items()
        if isinstance(item, QGraphicsSimpleTextItem)
    ]
    assert texts == ["请导入地图数据"]


def test_map_view_set_preview_single_image(qapp):
    view = MapView()
    rgb = np.zeros((30, 40, 3), dtype=np.uint8)
    rgb[..., 0] = 255
    view.set_preview(rgb)
    assert view.has_map is True
    pix_items = [
        item for item in view.scene().items() if isinstance(item, QGraphicsPixmapItem)
    ]
    assert len(pix_items) == 1
    assert pix_items[0].pixmap().width() == 40
    assert pix_items[0].pixmap().height() == 30
    # 重复导入替换旧图片，不叠加
    view.set_preview(np.zeros((10, 10, 3), dtype=np.uint8))
    pix_items = [
        item for item in view.scene().items() if isinstance(item, QGraphicsPixmapItem)
    ]
    assert len(pix_items) == 1
    assert pix_items[0].pixmap().width() == 10
    assert pix_items[0].pixmap().height() == 10


# --------------------------------------------------------------------------- #
# MainWindow 集成
# --------------------------------------------------------------------------- #
def test_main_window_load_success(qapp, tmp_path):
    data = np.zeros((3, 8, 8), dtype=np.uint8)
    data[0] = 10
    data[1] = 20
    data[2] = 30
    tif = tmp_path / "map.tif"
    write_tiff(tif, data, 3, "uint8")
    window = MainWindow()
    assert window.load_map_file(str(tif)) is True
    assert window.external_filename_label.text() == "map.tif"
    assert window.internal_image_label.text() == "--"
    assert window.crs_label.text() == "EPSG:3857"
    assert window.map_view.has_map is True
    assert window.current_preview is not None
    assert window.current_preview.source_width == 8
    assert window.status_label.text() == "地图加载成功"
    window.close()


def test_main_window_zip_load_shows_internal_name(qapp, tmp_path):
    data = np.zeros((3, 6, 6), dtype=np.uint8)
    tif_bytes = tif_bytes_of(data, 3, "uint8")
    zpath = make_zip(tmp_path, [("地图包/主影像.tif", tif_bytes), ("地图包/说明.txt", "x")])
    window = MainWindow()
    assert window.load_map_file(str(zpath)) is True
    assert window.external_filename_label.text() == "map.zip"
    assert window.internal_image_label.text() == "地图包/主影像.tif"
    assert window.crs_label.text() == "EPSG:3857"
    assert window.map_view.has_map is True
    window.close()


def test_failed_load_preserves_previous(qapp, tmp_path):
    good = tmp_path / "good.tif"
    data = np.zeros((3, 6, 6), dtype=np.uint8)
    write_tiff(good, data, 3, "uint8")
    window = MainWindow()
    assert window.load_map_file(str(good)) is True
    before = window.current_preview
    bad = tmp_path / "bad.tif"
    bad.write_bytes(b"garbage" * 50)
    assert window.load_map_file(str(bad)) is False
    assert window.current_preview is before
    assert window.external_filename_label.text() == "good.tif"
    assert window.map_view.has_map is True
    assert "加载失败" in window.status_label.text()
    window.close()