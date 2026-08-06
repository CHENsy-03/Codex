# TASK-001：Python 3.14.4 开发基线与基础窗口

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-001 |
| 任务类型 | feature / infra |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 建立 Python 3.14.4 虚拟环境并安装固定依赖；
- 创建最小项目基线文件（AGENTS.md、.gitignore、requirements.txt、README.md、docs/TASK.md、docs/CHANGELOG.md）；
- 实现第一阶段基础窗口（PySide6 左右布局、导入/清除按钮、信息与结果字段、空地图提示）；
- 只读审计参考 ZIP 地图数据包（Rectangle_#1_卫图.zip）的 GeoTIFF 元数据；
- 创建并运行冒烟测试。

## 3. 明确不做（本任务）

- 不实现 GeoTIFF 加载、选点、距离计算、飞行时间计算；
- 不创建 `geotiff_loader.py`、`calculator.py` 等空壳模块；
- 不实现缩放、平移、坐标转换；
- 不修改仓库根目录 AGENTS.md、README.md、SYSTEM_ARCHITECTURE.md 或其他项目。

## 4. Python 解释器约束（用户最新明确约束）

- 开发解释器固定为**普通 64 位 CPython 3.14.4**；
- 该约束**覆盖**需求文档 V1.1 中 "Python 3.11/3.12" 的旧描述；
- 禁止降级 Python、改用 Conda、使用 free-threaded Python、从源码编译 GIS/Qt 依赖；
- 若 3.14.4 无法安装要求的二进制轮子，立即停止并完整报告错误。

## 5. 依赖版本（固定）

```text
PySide6==6.11.1
rasterio==1.5.0
pyproj==3.7.2
numpy==2.5.1
pytest==9.1.1
```

安装方式：`pip install --only-binary=:all: ...`（禁止删除该参数规避安装失败）。

## 6. 验收项

- [x] Python 3.14.4 虚拟环境可用（普通 64 位，非 free-threaded）；
- [x] 五项依赖以二进制轮子安装成功，`pip check` 无破损依赖；
- [x] 基础窗口标题、尺寸、初始控件状态符合要求（坐标/距离/时间为 `--`，状态"就绪"）；
- [x] 冒烟测试全部通过；
- [x] 参考 ZIP 审计结果与预期一致（1 个主 GeoTIFF，298×249，3 波段，uint8，EPSG:3857）；
- [x] 未修改仓库根目录文档或其他项目。

## 7. 执行结果

- 虚拟环境：`py -3.14 -m venv .venv`，解释器为普通 64 位 CPython 3.14.4（free_threaded=False）；
- 依赖安装：`pip install --only-binary=:all: PySide6==6.11.1 rasterio==1.5.0 pyproj==3.7.2 numpy==2.5.1 pytest==9.1.1` 成功；`pip check` 通过；
- 测试：`python -m compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen python -m pytest -q` 全部通过；
- 参考包审计：ZIP 内主 GeoTIFF 数量 1（内部路径 Rectangle_#1_卫图/Rectangle_#1_卫图_Level_15.tif），298×249、3 波段、uint8、CRS EPSG:3857；仿射变换 (4.78, 0.0, 13377760.27 / 0.0, -4.78, 3533062.77)；bounds (13377760.27, 3531873.22, 13379183.91, 3533062.77)；中心点 WGS84 (120.1808381, 30.2247173)；被忽略辅助扩展名 .tfw/.txt/.kml/.url/.jpg；临时目录已清理，未复制附件进项目。

## 8. 遗留问题

- 无阻断项。地图加载、选点、距离与时间计算按计划留待后续任务。
---

# TASK-002：GeoTIFF/ZIP 安全加载与地图预览显示

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-002 |
| 任务类型 | feature |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 新增 `app/geotiff_loader.py`：ZIP/TIF 识别、ZIP 安全检查与唯一 GeoTIFF 提取、元数据校验、降采样预览生成；
- 更新 `app/map_view.py`：RGB 预览显示、自动适应窗口、唯一图片项；
- 更新 `app/main_window.py`：导入按钮接入真实加载流程，成功/失败状态与元数据字段更新；
- 新增 `tests/test_geotiff_loader.py`；
- 更新 README.md、docs/TASK.md、docs/CHANGELOG.md。

## 3. 明确不做（本任务）

- 不实现选点、坐标转换（pyproj）、距离计算、飞行时间计算；
- 不实现缩放、平移、A/B 标记、连线；
- 不创建 calculator.py、坐标模型、API 层、数据库层等空壳；
- 不修改目标项目以外的任何文件。

## 4. 关键实现规则（已落实）

- 直接 TIF 支持 `.tif/.tiff`；ZIP 中必须恰好一个 `.tif/.tiff` 主影像；
- 只提取唯一主 GeoTIFF，忽略 `.tfw/.txt/.kml/.url/.jpg` 与目录条目；不打开 `.url/.jpg`；
- 拒绝绝对路径、`..` 穿越、盘符路径、反斜杠穿越、NUL、符号链接、加密主影像；
- 解压到 `TemporaryDirectory` 固定安全文件名，分块流式复制，上限 `MAX_ARCHIVE_TIFF_BYTES = 2 GiB`；
- 加载完成后不保留 rasterio 数据集或 ZIP 句柄；临时目录自动清理；
- 预览最长边 ≤ 2048 且不放大；rasterio `out_shape` 直接降采样；
- 1 波段灰度转 RGB、3 波段 RGB、4 波段取前 3 个；其他波段拒绝；
- CRS、仿射变换、bounds 必须有效；缺失/无效时中文报错；
- 预览数组 `(H, W, 3)` uint8 C 连续；处理 nodata/masked/NaN/常量/无有效像素。

## 5. 验收项

- [x] 新增加载器测试全部通过（直接 TIF、单/三/四波段、uint16、超 2048、元数据、缺 CRS、损坏 TIF、ZIP 成功/失败、路径穿越、预览属性、异常数据）；
- [x] MapView 初始空提示、设置预览后唯一图片项、尺寸正确；
- [x] MainWindow 加载成功更新文件名/内部名/CRS/预览；失败保留旧地图与元数据；
- [x] TASK-001 冒烟测试继续通过；
- [x] 真实参考 ZIP（Rectangle_#1_卫图.zip）加载验证通过，临时文件已清理；
- [x] 未修改目标项目以外文件。

## 6. 执行结果

- 测试：`compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen pytest -q` 全部通过；
- 真实 ZIP 集成验证：见最终汇报（外部文件名、内部路径、298×249、预览 298×249、3 波段、uint8、EPSG:3857、预览 (249, 298, 3) uint8）；
- 临时解压内容已清理；未复制参考 ZIP 或截图进项目。

## 7. 遗留问题

- 无阻断项。选点、坐标转换、距离与时间计算按计划留待后续任务。
---

# TASK-003：地图缩放、平移与 A/B 图像点选择

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-003 |
| 任务类型 | feature |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 更新 `app/map_view.py`：滚轮缩放（受限）、右键拖动平移、左键依次选择 A/B 点、标记与连线、`MapPoint` 点位数据结构；
- 更新 `app/main_window.py`：连接点位变化信号、状态提示、清除点位按钮；
- 新增 `tests/test_map_interaction.py`；
- 更新 README.md、docs/TASK.md、docs/CHANGELOG.md。

## 3. 明确不做（本任务）

- 不实现投影坐标、经纬度、距离、速度或飞行时间计算；
- 不执行 transform * (col,row)、rasterio.transform.xy、pyproj 转换、EPSG:3857→EPSG:4326；
- 不实现 A/B 经纬度显示；
- 不创建 calculator.py、坐标模型、API 层、数据库层等空壳；
- 不修改目标项目以外的任何文件。

## 4. 交互规则（已固定实现）

- 左键单击：依次选择 A 点、B 点；A/B 均存在后再次点击仅提示“A/B 点已选择，请先清除点位”，不覆盖不增加；
- 鼠标滚轮：以鼠标位置为锚点缩放；`ZOOM_STEP_FACTOR=1.25`、`MAX_ZOOM_STEPS=12`；最小为完整适应窗口；
- 按住右键拖动：平移地图（滚动条机制），不创建点位；左键不用于平移；
- 清除点位：清除 A/B 标记与连线，保留地图与缩放/平移状态，可重复调用。

## 5. 点位模型

- `MapPoint`（frozen dataclass）：name（A/B）、scene_x、scene_y、source_col、source_row；
- 仅接受图像半开区间 `0 <= scene_x < preview_width`、`0 <= scene_y < preview_height` 内的点击；
- `source_col = scene_x * source_width / preview_width`；`source_row = scene_y * source_height / preview_height`；不取整、不交换 col/row；
- 地图图片项场景范围左上角 (0,0)、右下角 (preview_width, preview_height)，保持 1:1；视觉缩放仅通过视图变换；
- A/B 状态单一可信来源在 MapView；MainWindow 通过信号同步。

## 6. 验收项

- [x] 未加载地图时无点位，点击/滚轮/右键拖动安全无报错；
- [x] 缩放：初始步级 0 完整适应；上滚放大、下滚可恢复适应；不低于适应、不超过 12 步；锚点稳定；
- [x] 平移：右键拖动改变可见区域、不创建点位；无残留拖动状态；
- [x] 选点：A→B 顺序、第三次不覆盖、图像外忽略、col/row 正确、不取整；
- [x] 标记连线：A 蓝、B 红圆形+字母标签，唯一连线端点与点位一致；缩放平移后点位坐标不变；
- [x] 清除：清除标记连线保留地图；重复调用安全；
- [x] MainWindow：A 后清除按钮启用、清除后禁用；结果字段始终 `--`；新地图成功清除旧点位并重置视图；失败保留旧地图/元数据/点位/连线；
- [x] 重复导入不叠加图片项；
- [x] TASK-001、TASK-002 全部测试继续通过；
- [x] 真实参考 ZIP 交互集成验证通过（见最终汇报）。

## 7. 执行结果

- 测试：`compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen pytest -q` 全部通过；
- 真实参考 ZIP offscreen 集成验证：选点/标记/连线/缩放/平移/清除均符合预期，A/B 经纬度与结果字段保持 `--`；
- 未复制参考 ZIP、解压文件或截图进项目；临时文件已清理。

## 8. 遗留问题

- 无阻断项。投影坐标、经纬度、距离与飞行时间计算按计划留待后续任务。
---

# TASK-004：A/B 原始栅格连续行列坐标 → 地图坐标 → WGS84 经纬度

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-004 |
| 任务类型 | feature |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 新增 `app/coordinate_converter.py`：`GeoPoint` 数据结构与 `CoordinateConverter` 转换器；
- 更新 `app/main_window.py`：建立转换上下文、根据 A/B 点派生 GeoPoint、显示经纬度、原子状态保持；
- 新增 `tests/test_coordinate_conversion.py`；
- 更新 README.md、docs/TASK.md、docs/CHANGELOG.md。

## 3. 坐标语义

- `source_col/source_row` 为 TASK-003 生成的连续栅格坐标（不取整、不加 0.5 偏移）；
- `map_x/map_y` 为 GeoTIFF 实际 CRS 下的地图坐标（参考地图为 EPSG:3857）；
- 仿射变换完整六参数：`map_x = a*col + b*row + c`，`map_y = d*col + e*row + f`；
- 源 CRS 使用 `GeoTiffPreview.crs` 原始对象，不解析界面文本；
- `Transformer.from_crs(source_crs, "EPSG:4326", always_xy=True)`，输入 (map_x, map_y)，输出 (longitude, latitude)；
- 内部保留完整浮点精度，仅 UI 显示 6 位小数（经度在前、纬度在后）。

## 4. 明确不做（本任务）

- 不计算二维/三维距离、速度校验、飞行时间或 HH:MM:SS；
- 不做 EPSG:3857 平面距离或测地线距离计算；
- 不硬编码参考地图 transform/CRS/坐标；
- 不把其他 CRS 伪装成 EPSG:3857；
- 不修改 MapView 交互规则；
- 不修改目标项目外文件。

## 5. 验收项

- [x] 单元测试：轴对齐/六参数仿射、连续坐标不取整、无 0.5 偏移、col/row 不交换、EPSG:3857 已知点、always_xy 语义、非有限输入拒绝、无效 CRS/转换失败明确异常、GeoPoint 完整精度与 source_crs；
- [x] MainWindow：选 A 显示真实经纬度且 B 为 `--`；选 B 双显示；第三次点击不变；缩放/平移不变；清除恢复 `--`；重复清除安全；
- [x] 新地图成功换用新 transform/CRS 并清除旧地理点；加载失败原子保留旧地理点/经纬度/转换上下文；取消文件选择状态不变；重复加载不叠加覆盖物；
- [x] TASK-001/002/003 原有 62 项测试全部继续通过；
- [x] 真实参考 ZIP 集成验证通过（见最终汇报）。

## 6. 执行结果

- 测试：`compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen pytest -q` 全部通过；
- 真实参考 ZIP offscreen 验证：A/B 的 source_col/source_row、EPSG:3857 map_x/map_y、longitude/latitude 均正确且与 UI 显示一致；缩放平移后不变；
- 未复制参考 ZIP、解压文件或截图进项目；临时目录已清理。

## 7. 遗留问题

- 无阻断项。二维距离与飞行时间计算按计划留待后续任务。
---

# TASK-005：A/B 两点的 WGS84 椭球面二维测地线距离

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-005 |
| 任务类型 | feature |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 新增 `app/distance_calculator.py`：`DistanceResult` 与 `calculate_distance`（pyproj.Geod 测地线）；
- 更新 `app/main_window.py`：A/B GeoPoint 完整精度经纬度计算距离并显示；
- 新增 `tests/test_distance_calculation.py`；
- 更新 README.md、docs/TASK.md、docs/CHANGELOG.md。

## 3. 距离模型与数据来源

- 输入：A/B `GeoPoint` 内部完整精度 `longitude/latitude`（不从 UI 文本或 6 位小数解析）；
- 算法：`pyproj.Geod(ellps="WGS84").inv(longitude_a, latitude_a, longitude_b, latitude_b)`，只使用 `distance_m`；
- 单位：米；`distance_m` 必须有限且非负；相同点距离为 0；支持跨 ±180° 经线短测地线；
- 明确不使用：EPSG:3857 平面欧氏距离、经纬度角度差、手写 Haversine/球面公式；
- 二维地表距离，不含海拔、高差、地形起伏或三维斜距。

## 4. 明确不做（本任务）

- 不实现速度校验、飞行时间、HH:MM:SS、三维距离、DEM；
- 不修改 MapView 交互规则与 TASK-004 坐标语义；
- 不把距离算法放入 MapView 或 CoordinateConverter；
- 不修改目标项目外文件。

## 5. 验收项

- [x] 单元测试：赤道 1°（≈111319.490793 m）、经线 1°（≈110574.388558 m）、相同点 0、A→B 与 B→A 一致、非对称点证明 lon/lat 未交换、跨 ±180° 短距离、非有限拒绝、越界拒绝、完整精度、证明使用 lon/lat 而非 map_x/map_y；
- [x] MainWindow：选 A 距离 `--`；选 B 距离显示真实值；时间字段 `--`；UI 两位小数且内部完整精度；第三次点击/缩放/平移不变；清除恢复 `--`；重复清除安全；
- [x] 新地图成功清除旧距离并换新坐标重算；加载失败原子保留旧距离/坐标/转换上下文；取消文件选择不变；距离异常不产生虚假值不崩溃；重复加载不叠加覆盖物；
- [x] TASK-001 至 TASK-004 原有 82 项测试全部继续通过；
- [x] 真实参考 ZIP 集成验证通过（含独立 pyproj.Geod 复核与 EPSG:3857 欧氏距离对照）。

## 6. 执行结果

- 测试：`compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen pytest -q` 全部通过；
- 真实参考 ZIP offscreen 验证：distance_m 与独立 Geod 复核一致；UI 文本为两位小数 + 米；缩放平移后不变；EPSG:3857 欧氏距离数值明显偏离（仅对照，生产代码未使用）；
- 未复制参考 ZIP、解压文件或截图进项目；临时目录已清理。

## 7. 遗留问题

- 无阻断项。速度校验与飞行时间计算按计划留待后续任务。
---

# TASK-006：整数飞行速度输入、飞行时间计算、整数秒显示与 HH:MM:SS

## 1. 任务基本信息

| 项 | 内容 |
| --- | --- |
| 任务编号 | TASK-006 |
| 任务类型 | feature |
| 状态 | 已完成 |
| 目标项目 | `workspace/drone-range-simulation` |
| 执行日期 | 2026-08-06 |

## 2. 任务范围

- 新增 `app/flight_time_calculator.py`：`parse_speed_m_s`、`calculate_flight_time`、`format_hhmmss`、`FlightTimeResult`；
- 更新 `app/main_window.py`：速度输入即时自动计算、状态提示（请输入飞行速度/输入错误/飞行时间超过99小时/A/B 点选择完成）；
- 新增 `tests/test_flight_time_calculation.py`；
- 更新 README.md、docs/TASK.md、docs/CHANGELOG.md。

## 3. 最终确定的速度规则（用户确认，优先于文档未锁定建议值）

- 单位固定 **m/s**；合法速度集合为 **1–99 的整数**；
- 拒绝：0、负数、100+、小数、科学计数法、NaN/inf、正负号、前后空格/纯空格、非数字字符；
- 严格文本解析，不使用 float 先解析再判断整数。

## 4. 时间模型

- `exact_seconds = distance_m / speed_m_s`（DistanceResult 完整精度距离）；
- `rounded_seconds = math.ceil(exact_seconds)`（向上取整，整数秒显示）；
- `hhmmss = format_hhmmss(rounded_seconds)`（同一取整结果，divmod 拆分）；
- 上限 `99:59:59`（359999 秒）；`rounded_seconds >= 360000` 时抛 `FlightTimeLimitError`，不截断、不取模、不显示三位小时；
- 相同点距离 0 → exact 0 / rounded 0 / `00:00:00`。

## 5. 明确不做（本任务）

- 不实现动画、三维距离、DEM、航线规划、FastAPI、数据库、后台线程、状态机；
- 不新增“计算”按钮；
- 不做 km/h 换算、小数速度、四舍五入或向下取整、秒数与 HH:MM:SS 分别取整；
- 不修改距离算法、坐标语义、MapView 交互；
- 不修改目标项目外文件与产品文档。

## 6. 验收项

- [x] 速度解析：1/50/99 合法；0/100/负数/小数/空格/NaN/inf/科学计数法/非数字被拒绝；
- [x] 时间计算：m/s 无 3.6 换算、完整精度距离、ceil、整数秒不加 1、同一取整生成 HH:MM:SS、0→00:00:00、65→00:01:05、359999→99:59:59、360000+ 拒绝、非有限/负距离拒绝、bool/非整数速度拒绝；
- [x] MainWindow：选 A 时间 `--`；A/B+空速度提示“请输入飞行速度”；先 A/B 后速度与先速度后 A/B 均自动计算；改变速度重算；空/非法速度清除旧时间；超 99 小时不保留旧时间；时间错误不影响点位/经纬度/距离；第三次点击/缩放平移不变；清除保留速度文本；重复清除安全；新地图保留速度并重算；失败/取消原子保持；
- [x] TASK-001 至 TASK-005 原有 104 项测试全部继续通过；
- [x] 真实参考 ZIP 集成验证通过（10 m/s → 86 秒/00:01:26；20 m/s → 43 秒/00:00:43）。

## 7. 执行结果

- 测试：`compileall main.py app tests` 通过；`QT_QPA_PLATFORM=offscreen pytest -q` 全部通过；
- 真实参考 ZIP offscreen 验证：见最终汇报；
- 未复制参考 ZIP、解压文件或截图进项目；临时目录已清理。

## 8. 遗留问题

- 无阻断项。动画、三维距离、DEM、航线规划等明确排除，不进入样品。

---

# TASK-007A：产品需求基线一致性审计（只读）

## 1. 任务状态

- 状态：已完成（只读审计任务，无 PASS/FAIL 判定）
- 类型：只读审计

## 2. 单一目标

按 V1.1 对 TASK-001—TASK-006 实现进行只读一致性审计：完成 FR-01—FR-15、NFR-01—NFR-09、AC-01—AC-14 矩阵，识别实现缺陷、验证缺口与需求基线冲突；不修改任何文件。

## 3. 实际执行结果

- 完成 FR/NFR/AC 三张矩阵审计；
- 识别 6 项需求基线冲突（速度类型与范围、秒数显示、HH:MM:SS 取整、99 小时上限、第三次点击、速度错误提示），以及显示缺陷（经纬度“°”、≥1000 m 公里显示）与多处验证缺口；
- 未修改代码、测试、文档或产品文件。

## 4. 有效证据摘要

- 修改前基线 pytest：151 passed / 1 条既有 rasterio NotGeoreferencedWarning；
- V1.1 全文与全部表格只读提取并逐项对照（V1.1 SHA256=E20DB98765FDA0116A5E2F53D5A3C9EBE9B36BF81ED128D0CA6C68590DEDD07A）。

## 5. 证据边界或限制

- 审计基线为 V1.1；V1.2（TASK-007B 落档）后，相关冲突口径已由产品裁决更新，以最终勘误为准。

## 6. 是否运行测试

- 运行修改前基线 pytest（151 passed）；未新增测试。

## 7. 是否提交 Git

- 否。

---

# TASK-007B：产品需求基线裁决落档与 V1.2 冻结（仅文档）

## 1. 任务状态

- 状态：已完成（仅文档任务）

## 2. 单一目标

按产品负责人裁决创建 V1.2 产品需求文档，将 TASK-006 六项业务规则写入正式产品基线；V1.1 保留为历史版本，不覆盖、不重命名。

## 3. 实际执行结果

- 创建 产品文档设计/无人机二维航程计算样品_产品需求文档_V1.2_业务规则冻结.docx（最终 SHA256=82945F5A2BAF98100ACC4C2BCDC77A803452AAE7DE6AA933A046E459A75265D4）；
- 六项业务规则、显示规则、Python 验收版本（3.14.4）与 DoD 证据要求写入 V1.2；V1.1 未修改。

## 4. 有效证据摘要

- 修改前/后基线 pytest：151 passed；
- V1.2 渲染与结构核验通过（LibreOffice PDF 16 页、页脚 V1.2、章节/表格完整）；V1.1/V1.2 SHA256 与基线一致。

## 5. 证据边界或限制

- V1.2 文件在后续被产品负责人重新保存过，最终哈希为 82945F…5D4；本记录以最终文件为准。

## 6. 是否运行测试

- 运行基线 pytest（151 passed）；未新增测试。

## 7. 是否提交 Git

- 否。

---

# TASK-007C：按 V1.2 对齐代码实现并补齐自动化技术证据

## 1. 任务状态

- 状态：PASS

## 2. 单一目标

按 V1.2 对齐代码（修复经纬度“°”显示与 ≥1000 m 公里显示），并补齐自动化技术证据（无效仿射矩阵、损坏/加密 ZIP、MainWindow 同一点选择、不同缩放等级坐标一致性、≤100 ms 刷新）。

## 3. 实际执行结果

- 修改 app/main_window.py（_format_geo 增加“°”、_format_distance 增加米+公里分支）；
- 新增 tests/test_v12_alignment.py，并在坐标/距离测试补充显示规则断言；
- 全量 pytest：169 passed（含 1 条新引入的 rasterio 警告，由 TASK-007C-R1 收敛）。

## 4. 有效证据摘要

- ≤100 ms 同步路径实测最大 0.4458 ms（15 样本）；
- 无效仿射、损坏 ZIP、加密 ZIP 均安全拒绝且 MainWindow 旧状态原子保留；
- 同一点 0 距离/0 秒/00:00:00、不同缩放等级坐标一致。

## 5. 证据边界或限制

- 自动化证据基于动态临时影像，不依赖 D 盘；真实数据验收留待 TASK-007D 系列。

## 6. 是否运行测试

- 是（完整 pytest 169 passed）。

## 7. 是否提交 Git

- 否。

---

# TASK-007C-R1：消除 TASK-007C 新增测试引入的 rasterio 警告

## 1. 任务状态

- 状态：PASS（最小收尾）

## 2. 单一目标

消除新增公里显示测试夹具（单位矩阵翻转形式）触发的 rasterio NotGeoreferencedWarning。

## 3. 实际执行结果

- 仅修改 tests/test_distance_calculation.py 的测试变换为合法、非单位、非零原点变换（Affine(0.01, 0, 120, 0, -0.01, 30)）；未增删用例、未改产品代码；
- 全量 pytest：169 passed / 1 条 warning（由 2 条收敛为修改前既有的 1 条）。

## 4. 有效证据摘要

- 定向 pytest：27 passed / 0 warning；完整 pytest：169 passed / 1 warning。

## 5. 证据边界或限制

- 剩余 1 条为修改前既有警告（test_over_99_hours_no_old_time 的测试夹具）。

## 6. 是否运行测试

- 是。

## 7. 是否提交 Git

- 否。

---

# 首次 TASK-007D：真实数据、连续运行与本机发布环境验收

## 1. 任务状态

- 状态：历史 BLOCKED（保留，不因后续 PRE/R1 独立记录改写）

## 2. 单一目标

使用指定真实数据完成三次独立进程主流程、坐标交叉核验、性能/内存实测、Python 3.14.4 干净环境启动与 Windows 版本边界验收。

## 3. 实际执行结果

- 指定数据 Rectangle_#1_卫图.zip 主影像为 298×249（最长边 298 px），不满足 V1.2 AC-04“最长边远大于 2048 px”的大影像定义；
- 按任务停止条件立即停止，未运行后续验收；不得用小夹具冒充真实大影像。

## 4. 有效证据摘要

- 修改前基线 pytest：169 passed / 1 条既有 warning；
- Rectangle_#1 主影像元数据：298×249、3 波段 uint8、CRS EPSG:3857（只读资格检查）。

## 5. 证据边界或限制

- 该 BLOCKED 仅针对 Rectangle_#1 的数据资格，不代表产品 FAIL；后续 PRE 与 R1 为独立记录，不覆盖本历史状态。

## 6. 是否运行测试

- 仅运行修改前基线 pytest（169 passed）；未运行三次主流程。

## 7. 是否提交 Git

- 否。

---

# TASK-007D-PRE：新真实大影像只读资格预检

## 1. 任务状态

- 状态：QUALIFIED

## 2. 单一目标

只读判断 Rectangle_#2_卫图.zip 是否具备重新执行 TASK-007D 的资格；不运行三次主流程、性能或干净环境验收。

## 3. 实际执行结果

- Rectangle_#2 主影像：4928×4040（最长边 4928 px，像素总量 19,909,120），3 波段 uint8，CRS EPSG:3857，JPEG 压缩、256×256 tiled、无 overview；
- ZIP 安全（无穿越/绝对路径/加密成员，唯一 TIFF 候选），四角/中心/降采样窗口抽样读取正常。

## 4. 有效证据摘要

- Rectangle_#2 SHA256=19F32B00D41DBD630F6F9A14B96DACC2BAD1D13BCA95E990EB85AE0D8D398EA6（27,802,445 字节）；
- 满足 V1.2 大影像定义（最长边远大于 2048 px），判定 QUALIFIED。

## 5. 证据边界或限制

- overview 缺失如实记录，但 V1.2 未规定必须存在，不构成失败；
- 预检只判资格，不构成性能或内存证据。

## 6. 是否运行测试

- 否（仅只读资格预检）。

## 7. 是否提交 Git

- 否。

---

# TASK-007D-R1：使用新真实大影像重新执行完整本机验收

## 1. 任务状态

- 状态：PASS（Windows 11 本机技术验收；采用最终勘误口径）

## 2. 单一目标

使用 Rectangle_#2 完成三次独立进程主流程、坐标交叉核验、性能/内存实测、Python 3.14.4 干净环境启动，并记录 Windows 版本与人工验收边界。

## 3. 实际执行结果

- 三次独立进程（速度 10/30/99 m/s）全部成功：距离 2064.11 米（2.06 公里）；飞行时间 207/69/21 秒，显示 00:03:27/00:01:09/00:00:21；
- 启动时间 287.21/135.74/140.83 ms；导入时间 543–582 ms；
- 四类交互 P95 ≤ 2.351 ms；
- 坐标独立交叉核验最大地面误差 1.384 m；
- Python 3.14.4 干净环境（无 system-site-packages）安装、pip check、模块导入、启动、真实数据加载与一组计算全部成功。

## 4. 有效证据摘要（采用最终勘误口径）

- 完整 pytest：169 passed / 1 条既有 warning；
- 内存（进程外 50 ms 轮询 Qt 宿主子进程，原始字节）：
  - post-import PollMaxWS：141,574,144 B（135.02 MiB）/ 141,565,952 B（135.01 MiB）/ 141,369,344 B（134.82 MiB）；
  - lifetime PollMaxWS：216,158,208 B（206.14 MiB）/ 235,634,688 B（224.72 MiB）/ 258,912,256 B（246.92 MiB）；
  - OS PeakWorkingSet64：284,770,304 B（271.58 MiB）/ 284,196,864 B（271.03 MiB）/ 284,254,208 B（271.09 MiB）；
  - 数值关系：post-import PollMaxWS ≤ lifetime PollMaxWS ≤ OS PeakWorkingSet64（三组均成立）；
- 三个 SHA256：V1.1=E20DB98765FDA0116A5E2F53D5A3C9EBE9B36BF81ED128D0CA6C68590DEDD07A、V1.2=82945F5A2BAF98100ACC4C2BCDC77A803452AAE7DE6AA933A046E459A75265D4、Rectangle_#2=19F32B00D41DBD630F6F9A14B96DACC2BAD1D13BCA95E990EB85AE0D8D398EA6。

## 5. 证据边界或限制

- 原始逐条 CSV 已清理，仅保留经核验的汇总证据；
- 不得声称 POST 阶段“稳定”，不得把较高内存归因于未经证明的具体操作；
- 坐标误差不跨不同坐标点组合计算；最大地面误差 1.384 m 为独立经纬度核验口径；
- 本机为 Windows 11（10.0.26200、i7-12700H、15.8 GB、AMD64）；
- Windows 10 验收：PENDING-EXTERNAL；
- 首次使用者两分钟验收：PENDING-EXTERNAL。

## 6. 是否运行测试

- 是（完整 pytest 169 passed；另执行三次独立进程主流程与内存/交互实测）。

## 7. 是否提交 Git

- 否。

---

# TASK-008：样品验收档案与项目文档收口

## 一、任务状态

- 状态：DEFINED（定义已确认，尚未执行）
- 类型：纯文档任务
- TASK-008 完成不代表 Windows 10 或首次使用者两分钟验收已经通过。
- Windows 10 与首次使用者验收继续保持 PENDING-EXTERNAL。

## 二、单一目标

将 TASK-001—TASK-007D-R1 的最终验收结论正式落盘，修正项目 README 中的过期内容，并为两个 PENDING-EXTERNAL 项准备可复现的验收步骤和空白记录模板。

不得借 TASK-008 引入产品功能、代码变更、测试变更、打包发布或正式平台能力。

## 三、TASK-008 实施阶段授权范围

实施 TASK-008 时，只允许涉及以下五个文件：

1. 修改：
   workspace/drone-range-simulation/README.md

2. 修改：
   workspace/drone-range-simulation/docs/TASK.md

3. 修改：
   workspace/drone-range-simulation/docs/CHANGELOG.md

4. 创建：
   workspace/drone-range-simulation/docs/ACCEPTANCE_RECORD.md

5. 创建：
   workspace/drone-range-simulation/docs/EXTERNAL_ACCEPTANCE_GUIDE.md

“只有五个授权文件发生变化”是指相对于 TASK-008 正式执行前建立的文件快照而言。仓库内原有用户改动不属于 TASK-008，不得处理。

## 四、实施要求

### 4.1 docs/TASK.md

- 完整保留 TASK-001—TASK-006 原文。
- 补录 TASK-007A、TASK-007B、TASK-007C、TASK-007C-R1、首次 TASK-007D、TASK-007D-PRE、TASK-007D-R1。
- 记录各任务的目标、结果、证据边界和最终状态。
- 首次 TASK-007D 必须保持历史 BLOCKED。
- TASK-007D-PRE 状态必须为 QUALIFIED。
- TASK-007D-R1 状态必须为 PASS。
- 不得把早期结论覆盖成不存在，也不得复活已被最终勘误纠正的结论。

### 4.2 docs/ACCEPTANCE_RECORD.md

建立唯一的最终验收摘要，不复制多版历史报告。

必须记录：

- 自动化验收结论；
- Windows 11 实测结论；
- 真实数据验收结论；
- 坐标交叉核验结论；
- 启动、导入和交互性能结论；
- 内存测量结论；
- PENDING-EXTERNAL 项。

必须采用 TASK-007D-R1 最终勘误后的口径，至少遵守以下证据约束：

- 自动化最终结果为 169 passed；
- pip check 与 compileall 的历史结果可以如实记录，但不得伪造执行日期或原始日志；
- Windows 11 三次独立进程主流程速度为 10、30、99 m/s；
- 对应飞行时间为 207、69、21 秒；
- 对应显示为 00:03:27、00:01:09、00:00:21；
- 距离为 2064.11 米（2.06 公里）；
- 启动时间为 287.21、135.74、140.83 ms；
- 导入时间范围为 543–582 ms；
- 四类交互 P95 不超过 2.351 ms；
- 坐标独立交叉核验最大地面误差为 1.384 m；
- post-import PollMaxWS、lifetime PollMaxWS、OS PeakWorkingSet64 必须分列说明；
- 不得声称 POST 阶段“稳定”；
- 不得把较高内存归因于某个未经证明的具体操作；
- 坐标误差不得跨不同坐标点组合计算；
- 必须说明原始逐条 CSV 已清理，目前只保留经核验的汇总证据；
- Windows 10 与首次使用者两分钟验收必须继续标记 PENDING-EXTERNAL。

### 4.3 README.md

必须修正：

- “当前状态（TASK-004）”过期标题；
- “当前尚未进行速度校验与飞行时间计算”的过期表述；
- 目录结构中缺少 tests/test_v12_alignment.py 的问题；
- 增加已验证平台与待外部验证平台的明确区分；
- 将 ACCEPTANCE_RECORD.md 和 EXTERNAL_ACCEPTANCE_GUIDE.md 补入目录结构。

### 4.4 docs/EXTERNAL_ACCEPTANCE_GUIDE.md

必须准备：

- Windows 10 实际验收步骤及空白记录表；
- 首次使用者两分钟实际验收步骤及空白记录表。

准备指南和模板不等于外部验收通过。

### 4.5 docs/CHANGELOG.md

- 只记录 TASK-008 实际完成的文档收口内容。
- 不伪造 TASK-007 系列的执行日期、提交号、原始日志或不存在的证据。

## 五、首次使用者两分钟验收冻结口径

### 5.1 前置条件

- 应用和依赖已经安装完成；
- 应用主窗口已经打开；
- 本地已准备一份合格地图 ZIP，并能从明确位置选择；
- 安装依赖、启动应用以及准备测试数据的时间不计入两分钟。

### 5.2 参与者

- 参与者此前未实际操作过该样品；
- 允许参与者阅读项目提供的快速使用说明；
- 观察者不得进行逐步口头指导或代替参与者操作。

### 5.3 计时起点

观察者发出开始指令，并将应用控制权交给参与者时开始计时。

### 5.4 必须完成的主流程

参与者独立完成：

1. 导入合格地图 ZIP；
2. 在地图上选择 A 点和 B 点；
3. 输入合法飞行速度；
4. 看到 A/B 经纬度；
5. 看到距离结果；
6. 看到整数秒飞行时间；
7. 看到 HH:MM:SS 飞行时间。

### 5.5 计时终点

上述结果全部成功显示时停止计时。

### 5.6 通过条件

- 总用时不超过 120 秒；
- 应用没有崩溃；
- 流程中没有无法继续的阻断性错误；
- 所有必需结果均成功显示。

### 5.7 不计入两分钟的操作

- 安装依赖；
- 启动应用；
- 准备或复制地图数据；
- 清除点位；
- 正常退出应用。

清除点位和正常退出可以另外验收和记录，但不得计入两分钟主流程。

### 5.8 记录要求

空白记录表至少包含：

- 操作系统和环境；
- 应用版本或对应任务状态；
- 地图数据名称及校验信息；
- 参与者；
- 观察者；
- 开始时间；
- 结束时间；
- 总用时；
- 各主流程步骤结果；
- 崩溃或阻断性错误记录；
- 最终 PASS/FAIL；
- 参与者和观察者确认字段。

不得预填执行结果或签名。

## 六、明确排除范围

TASK-008 不包括：

- 修改 Python 代码、测试、配置或依赖；
- 运行产品、pytest 或重新补测；
- 修改 V1.0、V1.1、V1.2 产品文档；
- 修改或分发 Rectangle_#2_卫图.zip；
- 判断地图数据的法律授权；
- 引入 PyInstaller、安装包或其他分发工作；
- 执行 Windows 10 实际验收；
- 执行首次使用者两分钟实际验收；
- FastAPI、数据库、Leaflet、DEM、三维距离、航线规划、飞行动画、状态机、Launcher、多地图或后台进程；
- 任何正式无人机飞行仿真平台的新功能；
- 修改仓库根 README、根 docs 或其他项目；
- Git 暂存、提交、推送、分支切换、恢复或工作区清理。

## 七、验收标准

TASK-008 实施完成时必须同时满足：

1. 相对于执行前快照，只有五个授权文件发生变化；
2. README 三项已知不一致全部修正；
3. TASK-007 系列状态、顺序和证据边界准确；
4. 最终验收记录只采用最后一次勘误后的有效口径；
5. 不复活已经作废或纠正的结论；
6. Windows 10 和首次使用者验收始终为 PENDING-EXTERNAL；
7. 外部验收指南包含步骤、环境、执行人、时间、结果和确认字段；
8. 不把“验收材料准备完成”写成“外部验收已经通过”；
9. 受保护文件修改前后 SHA256 一致；
10. 所有文档为有效 UTF-8；
11. 文档内部链接和相对路径有效；
12. git diff --check 不得发现由本任务引入的问题；
13. 因项目当前未进入 Git 索引，git diff 不得作为唯一越界检查证据，必须同时使用执行前后文件清单和 SHA256 对比；
14. 不得出现代码、测试、产品文档、地图数据、仓库根文件或其他项目的越界变化。

## 八、完成状态口径

TASK-008 文档验收全部通过后，状态写为：

TASK-008：PASS，文档与验收记录已收口；Windows 10 和首次使用者两分钟验收仍为 PENDING-EXTERNAL，尚未提交。

在实际完成上述文档工作以前，不得提前写成 PASS。