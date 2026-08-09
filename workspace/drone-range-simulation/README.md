# 无人机二维航程计算样品

单进程、单窗口、单地图的 Python 桌面样品：
导入本地地图数据包（ZIP/GeoTIFF）→ 显示地图 → 选择 A/B 点 → 输入无人机速度 → 计算二维距离与预计飞行时间。

## 当前状态（TASK-001—TASK-006）

- 已建立 Python 3.14.4 虚拟环境与固定依赖基线（TASK-001）；
- 已实现基础窗口（TASK-001）；
- 已实现地图数据安全加载与预览显示（TASK-002）；
- 已实现地图交互：滚轮缩放、右键拖动平移、左键依次选择 A/B 点、标记与连线（TASK-003）；
- 已实现坐标转换：A/B 栅格连续坐标 → GeoTIFF 实际 CRS 地图坐标 → WGS84 经纬度，并在界面显示 A/B 经纬度（TASK-004）；
- 已实现二维距离：A/B GeoPoint 完整精度经纬度 → WGS84 椭球面测地线距离（米），并在界面显示（TASK-005）；
- 已实现飞行时间：整数速度（1–99 m/s）解析、时间 = 距离/速度、整数秒向上取整与 HH:MM:SS 显示（TASK-006）；
- 尚未实现：动画、三维距离、DEM、航线规划等（明确排除）。

## 验收资料入口

- [最终验收摘要](docs/ACCEPTANCE_RECORD.md)
- [外部验收指南与空白记录表](docs/EXTERNAL_ACCEPTANCE_GUIDE.md)
- [任务与验收定义](docs/TASK.md)
- [变更记录](docs/CHANGELOG.md)

## 当前验收状态

- TASK-007D-R1：PASS；
- Windows 11 本机技术验收：PASS；
- Windows 10 实机验收：PENDING-EXTERNAL；
- 首次使用者两分钟验收：PENDING-EXTERNAL；
- TASK-008 整体实施：IN PROGRESS；
- Git：尚未提交。

## 外部验收边界

- Windows 10 实机验收与首次使用者两分钟验收尚未实际执行；
- 创建外部验收指南和空白记录表不等于外部验收通过；
- Windows 11 的历史技术验收不能替代 Windows 10 实机验收；
- 开发者或历史演示不能替代首次使用者验收；
- 后续实际执行时必须填写真实记录，不能预填或补造证据。
## 支持的输入格式

- `.zip`：BIGEMAP 式地图数据包（演示主格式）；
- `.tif` / `.tiff`：直接导入 GeoTIFF（兼容入口）。

## ZIP 地图数据包规则

- ZIP 中**必须且只能包含一个** `.tif`/`.tiff` 主影像；
- `.tfw`、`.txt`、`_range.kml` 等辅助文件会被**忽略**，不参与加载与计算；
- `.url`、`.jpg` 及其他无关文件一律忽略，**不得打开或访问**；
- 主 GeoTIFF 必须自带**内部 CRS 与仿射变换**，不得根据 TFW/KML 猜测或补造；
- 只安全解压唯一主 GeoTIFF 到临时目录，检查后自动清理；禁止路径穿越、符号链接、加密成员；
- 样品级 ZIP 解压大小上限：**2 GiB**（同时检查 ZIP 声明大小与实际写入字节数）。

## 预览限制

- 预览最长边不超过 **2048 像素**，不放大原图；
- 使用 rasterio `out_shape` 直接降采样读取，不整幅读入再缩小；
- 支持 1 波段（灰度转 RGB）、3 波段（RGB）、4 波段（取前 3 个波段）；其他波段数明确提示不支持；
- 输出预览数组为 `(H, W, 3)`、`uint8`、C 连续内存；uint8 保留原始亮度，其他类型做百分位拉伸。

## 地图交互（TASK-003）

- **左键单击**：依次选择 A 点、B 点；A/B 均已选择后再点击仅提示“请先清除点位”，不覆盖、不增加点位；
- **鼠标滚轮**：以鼠标位置为锚点缩放；最大 12 个缩放步级，最小为整幅地图完整适应窗口；
- **按住右键拖动**：平移地图；不创建点位，不影响已选点位；
- **清除点位按钮**：清除 A/B 标记与连线，保留当前地图与缩放/平移状态；
- **A/B 标记**：A 点蓝色、B 点红色，均为圆形标记 + 字母标签；两点齐全后绘制唯一连线；
- 图像外点击不创建点位。

## 坐标转换（TASK-004）

- A/B 点保存**图像场景坐标**与**原始栅格连续行列坐标**（source_col/source_row，不取整、不加 0.5 偏移）；
- 通过 GeoTIFF **原始 affine transform 完整六参数**计算地图坐标：

  `map_x = a * source_col + b * source_row + c`
  `map_y = d * source_col + e * source_row + f`

- 使用**实际源 CRS**（参考地图为 EPSG:3857）通过 pyproj `Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)` 转换到 WGS84；
- 输入顺序始终为 map_x、map_y，输出顺序始终为 **longitude（经度）、latitude（纬度）**；
- 界面经纬度显示格式：`经度 120.123456，纬度 30.123456`（6 位小数）；**内部保留完整浮点精度，仅 UI 格式化时控制小数位**；
- 坐标转换失败时对应经纬度保持 `--` 并显示简洁中文错误，不显示虚假坐标、不崩溃；
- 速度校验与飞行时间计算见「飞行时间（TASK-006）」节。

## 距离计算（TASK-005）

- 距离采用 **WGS84 椭球面最短测地线**，使用 `pyproj.Geod(ellps="WGS84").inv`；
- 输入为 A/B `GeoPoint` 内部保存的**完整精度** longitude/latitude（不从 UI 文本或格式化小数解析）；
- 输入顺序 `(longitude_a, latitude_a, longitude_b, latitude_b)`，只使用返回的 `distance_m`（米）；
- 相同点距离为 0；正确支持跨越 ±180° 经线的短测地线；
- **明确不使用 EPSG:3857 平面欧氏距离**，不使用经纬度角度差，不手写近似公式；
- 距离为二维地表距离，不含海拔、高差、地形起伏或三维斜距；
- UI 距离显示为两位小数 + 单位：`858.23 米`；**内部 DistanceResult 保留完整浮点精度，仅 UI 格式化时控制小数位**；
- 距离计算异常时距离保持 `--` 并显示简洁中文错误，不产生虚假距离、不崩溃。

## 飞行时间（TASK-006）

- 速度单位为 **m/s**，只接受 **1–99 的整数**（拒绝 0、负数、100+、小数、科学计数法、NaN/inf、正负号、空格与非数字字符）；
- **自动计算**：无“计算”按钮；速度输入框变化即触发；先选 A/B 再输速度、或先输速度再选 A/B 两种顺序均支持；
- 公式：`exact_seconds = distance_m / speed_m_s`，使用 DistanceResult 内部**完整精度**距离（不从 UI 文本解析）；
- 秒数显示**向上取整**（`rounded_seconds = math.ceil(exact_seconds)`），为整数；
- HH:MM:SS 由**同一个 rounded_seconds** 生成（`divmod` 逐级拆分），格式两位：`00:00:00`、`00:01:26`、`99:59:59`；
- 最大显示 **99:59:59**（359999 秒）；超过 99 小时不截断、不取模、不显示三位小时，秒数与 HH:MM:SS 均为 `--`，状态提示“飞行时间超过99小时”；
- 速度为空：秒数与 HH:MM:SS 为 `--`，状态“请输入飞行速度”；速度非法：立即清除旧时间，状态“输入错误”；均不弹窗、不显示 traceback；
- 清除点位与成功加载新地图时**保留速度输入框文本**；
- 当前仍不包含动画、三维距离、DEM、航线规划等。

## 环境要求

- Windows 10/11；
- 普通 64 位 CPython **3.14.4**（非 free-threaded、非 Conda、非源码编译）；
- 依赖版本见 `requirements.txt`。

## 安装与启动

```powershell
py -3.14 -m venv .venv
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
.\.venv\Scripts\python.exe main.py
```

## 测试

```powershell
$env:QT_QPA_PLATFORM = "offscreen"
.\.venv\Scripts\python.exe -m pytest -q
Remove-Item Env:QT_QPA_PLATFORM
```

## 目录结构

```text
drone-range-simulation/
├── AGENTS.md            项目级开发原则
├── .gitignore
├── requirements.txt     固定依赖版本
├── README.md
├── main.py              应用入口
├── app/
│   ├── __init__.py
│   ├── coordinate_converter.py  栅格坐标 → 地图坐标 → WGS84
│   ├── distance_calculator.py   WGS84 椭球面测地线距离
│   ├── flight_time_calculator.py 速度解析与飞行时间/HH:MM:SS
│   ├── geotiff_loader.py        ZIP/TIF 安全加载与预览生成
│   ├── main_window.py           主窗口、导入流程与结果显示
│   └── map_view.py              地图视图（缩放/平移/选点/标记/连线）
├── tests/
│   ├── test_smoke.py                  基础冒烟测试
│   ├── test_geotiff_loader.py         加载与预览测试
│   ├── test_map_interaction.py        地图交互测试
│   ├── test_coordinate_conversion.py  坐标转换测试
│   ├── test_distance_calculation.py   距离计算测试
│   ├── test_flight_time_calculation.py 飞行时间测试
│   └── test_v12_alignment.py          V1.2 对齐证据测试
└── docs/
    ├── TASK.md                      任务与验收定义
    ├── CHANGELOG.md                 变更日志
    ├── ACCEPTANCE_RECORD.md         最终验收摘要
    └── EXTERNAL_ACCEPTANCE_GUIDE.md 外部验收指南与空白记录表
```

## 当前尚未实现（明确排除）

- 飞行动画、三维距离、DEM、航线规划、多地图、FastAPI、数据库、后台线程、状态机、Launcher。

## 已知限制

- 仅支持单进程、单窗口、单地图，不实现多地图或多任务状态；
- 不实现 DEM、三维距离、飞行动画、状态机、FastAPI、数据库、Launcher 等明确排除能力。