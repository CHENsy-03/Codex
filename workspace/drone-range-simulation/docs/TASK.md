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


# TASK-007：无 GUI 计算核心抽取与基线验证

## 1. 任务基本信息

- 状态：COMPLETED（本轮实施完成，未提交 Git）
- 类型：代码抽取 + 测试 + 文档记录
- 冻结基线：《无人机二维航程计算引擎_Java21常驻子进程集成技术设计 V1.0 冻结版》第 10.1 节第一项、《无人机二维航程计算样品_产品需求文档 V1.2 业务规则冻结》
- 工作目录：workspace/drone-range-simulation

## 2. 任务范围

- 新增 `app/geotiff_loader.py` 中的 `GeoTiffMetadata` 与 `load_geotiff_metadata()`：仅读取并校验直接 GeoTIFF 元数据，不生成预览、不处理 ZIP；
- 新增 `app/headless_core.py`：无 GUI 门面（`HeadlessMap`、`load_map`、`geotiff_to_wgs84`），复用现有四个计算模块的唯一实现；
- 新增 `tests/test_headless_core.py`：8 项无 GUI 核心测试；
- 更新 `docs/TASK.md` 与 `docs/CHANGELOG.md`。

## 3. 明确不做（本任务）

- 不创建 worker_main.py；
- 不实现 stdin/stdout 或 NDJSON；
- 不实现 hello、load_map、calculate、shutdown 操作；
- 不实现协议状态机或冻结错误码映射；
- 不编写 Java 示例；
- 不安装或配置 Nuitka；
- 不构建 Windows/Linux 软件包；
- 不创建 delivery 交付目录。

## 4. 关键实现规则

- 复用现有唯一实现：`CoordinateConverter`（always_xy=True）、`pyproj.Geod(ellps="WGS84").inv`、`flight_time_calculator` 的 `parse_speed_m_s`/`calculate_flight_time`；
- 像素坐标为零基连续 column/row，不取整、不自动增加 0.5；
- 只处理直接 GeoTIFF（.tif/.tiff）路径，ZIP 由 Java 解压；
- 无全局可变状态，不连接数据库，不联网，不写业务数据。

## 5. 验收项

- 无 QApplication、无窗口时可导入和调用核心（子进程验证）；
- 导入无 GUI 核心不会间接导入 PySide6（子进程验证）；
- 合法临时 GeoTIFF 元数据正确（CRS、尺寸、波段、transform）；
- 完整链路：GeoTIFF → A/B 连续像素坐标 → WGS84 → 距离 → 飞行时间；
- 结果与独立 pyproj.Geod 基准一致；
- 不增加 0.5、不交换 column/row、不交换 longitude/latitude；
- 原有 GUI 与 TASK-001—TASK-006 测试继续通过。

## 6. 执行结果

- 修改前基线完整测试：169 passed, 1 warning；
- 新增定向测试 tests/test_headless_core.py：8 passed；
- 修改后完整测试：177 passed, 1 warning（警告为既有 rasterio NotGeoreferencedWarning，未新增）；
- python -m compileall main.py app tests：通过；
- git diff --check：通过（项目未进入 Git 索引，以文件清单与哈希快照补足）；
- 未执行 worker_main.py、NDJSON、Java、Nuitka、Git 提交。

## 7. 遗留问题

- 无阻断项；项目整体仍未进入 Git 索引，所有改动未提交。


# TASK-008：常驻 Worker 入口与严格 NDJSON 传输循环

## 1. 任务基本信息

- 状态：COMPLETED（本轮实施完成，未提交 Git）
- 类型：代码新增 + 测试 + 文档记录
- 冻结基线：《无人机二维航程计算引擎_Java21常驻子进程集成技术设计 V1.0 冻结版》第 10.1 节第 2 项、《无人机二维航程计算样品_产品需求文档 V1.2 业务规则冻结》
- 前置任务：TASK-007（无 GUI 计算核心抽取与基线验证，基线 177 passed, 1 warning）
- 工作目录：workspace/drone-range-simulation

## 2. 任务范围

- 新增 `app/worker_protocol.py`：协议常量、请求校验、响应构造与严格串行 NDJSON 循环（`run_worker`/`main`）；
- 新增 `worker_main.py`：极薄进程入口，仅导入并执行 `app.worker_protocol.main`；
- 新增 `tests/test_worker_protocol.py`：37 项纯函数与真实子进程测试；
- 更新 `docs/TASK.md` 与 `docs/CHANGELOG.md`。

## 3. 明确不做（本任务）

- 不实现 load_map 成功逻辑、calculate 成功逻辑、地图缓存或地图状态机；
- 不实现 WGS84/map_crs/pixel JSON 坐标解析、点位范围校验、速度解析、距离或飞行时间协议响应；
- 不实现 READY 与 MAP_LOADED 完整状态切换或原子地图替换；
- 不编写 Java ProcessBuilderDemo.java、不生成 requests.ndjson/responses.ndjson 外发示例；
- 不安装或配置 Nuitka、不构建 Windows/Linux 软件包、不创建 delivery 目录；
- 不连接数据库、不开放 HTTP/gRPC/WebSocket；
- 不新增第三方依赖。

## 4. 协议实现

- 通道：stdin 请求 / stdout 协议响应 / stderr 日志；UTF-8；每行一个 JSON 对象；响应以 LF 结束并立即 flush；使用二进制流 `sys.stdin.buffer/stdout.buffer/stderr.buffer`。
- 常量：`PROTOCOL_VERSION = 1`、`ENGINE_VERSION = "1.0.0"`。
- 通用请求字段：id（非空字符串）、protocolVersion（JSON 整数 1，拒绝 bool/浮点/字符串/非 1）、operation（字符串）。
- hello：`{"protocolVersion":1,"engineVersion":"1.0.0","state":"READY","coordinateTypes":["wgs84","map_crs","pixel"]}`；可重复调用，id 回显。
- shutdown：`{"state":"TERMINATING"}`；先写响应并 flush，再结束循环，进程以退出码 0 退出；响应后不再处理后续输入。
- 传输层错误码（仅本阶段）：E_PROTOCOL_INVALID_JSON、E_PROTOCOL_VERSION、E_OPERATION_UNKNOWN、E_REQUEST_INVALID、E_INTERNAL。
- 无效请求不导致退出，返回错误后可继续处理下一条合法请求；stdin EOF 以 0 退出且 stdout 无额外输出；stdout 管道关闭时安全退出。
- JSON 输出：ensure_ascii=False、allow_nan=False、紧凑单行、无 BOM、无多行格式化。

## 5. 验收项

- 导入 worker_main / app.worker_protocol 不导入 PySide6、不创建 QApplication/窗口；
- 真实子进程 hello 立即返回单行响应（flush 生效）；
- 同一子进程连续 hello 不重启、不串线、每请求仅一个响应；
- 非法 JSON、空行、顶层数组/null/数字/字符串、NaN、Infinity、非法 UTF-8 → E_PROTOCOL_INVALID_JSON；
- 缺失或非法 id → E_REQUEST_INVALID（id=null）；
- protocolVersion 为 2、1.0、true、"1" → E_PROTOCOL_VERSION；
- 未知 operation → E_OPERATION_UNKNOWN；
- stdout 每行均为协议 JSON，无日志、提示、BOM、空白行或 traceback；
- shutdown 先返回 TERMINATING，退出码 0；stdin EOF 退出码 0 且无额外响应；
- 错误响应仅含 id/success/error，成功响应仅含 id/success/data。

## 6. 执行结果

- 修改前基线完整测试：177 passed, 1 warning；
- 定向测试 tests/test_worker_protocol.py：37 passed；
- TASK-007 与 TASK-008 联合定向：45 passed；
- 修改后完整测试：214 passed, 1 warning（警告为既有 rasterio NotGeoreferencedWarning，未新增）；
- python -m compileall -q main.py worker_main.py app tests：通过；
- git diff --check：仓库级仅命中 crawler/全部代码.txt 的既有无关问题；项目未进入 Git 索引，以文件清单与 SHA256 快照补足；
- 未实现 load_map、calculate、完整状态机、Java 示例、Nuitka、交付目录；未提交 Git。

## 7. 遗留问题

- 无阻断项；load_map/calculate 等业务操作将在 TASK-009 接入；
- 项目整体仍未进入 Git 索引，所有改动未提交。


# TASK-009：状态机、原子 load_map、三类坐标与完整 calculate 协议

## 1. 任务基本信息

- 状态：COMPLETED（本轮实施完成，未提交 Git）
- 类型：代码新增 + 协议扩展 + 测试 + 文档记录
- 冻结基线：《无人机二维航程计算引擎_Java21常驻子进程集成技术设计 V1.0 冻结版》第 10.1 节第 3 项、《无人机二维航程计算样品_产品需求文档 V1.2 业务规则冻结》
- 前置任务：TASK-007（无 GUI 计算核心）、TASK-008（NDJSON 传输循环），基线 214 passed, 1 warning
- 工作目录：workspace/drone-range-simulation

## 2. 任务范围

- 新增 `app/worker_engine.py`：WorkerEngine（状态机、原子 load_map、hello/calculate/shutdown、操作级字段校验与冻结错误映射）；
- 新增 `tests/test_worker_engine.py`：49 项状态机/地图/原子替换/坐标/计算/子进程测试；
- 修改 `app/worker_protocol.py`：接入 WorkerEngine 分发，新增 12 个地图/坐标/计算错误码；
- 最小修改 `app/geotiff_loader.py`（稳定异常分类：GeoTiffOpenError/GeoTiffCrsMissingError/GeoTiffTransformInvalidError）、`app/coordinate_converter.py`（逆方向转换 wgs84_to_map/map_to_pixel/wgs84_to_pixel）、`app/headless_core.py`（wgs84_to_pixel/map_crs_to_pixel）；
- 更新 `docs/TASK.md` 与 `docs/CHANGELOG.md`。

## 3. 明确不做（本任务）

- 不处理 ZIP、不生成地图预览、不创建 QApplication、不启动 GUI/HTTP/gRPC/WebSocket/数据库；
- 不使用线程池、asyncio 或多进程处理请求，不实现多地图并发；
- 不缓存 A/B 或计算结果；不新增第三方依赖；
- 不编写 Java ProcessBuilderDemo.java、不生成 requests.ndjson/responses.ndjson、不安装或配置 Nuitka、不构建软件目录、不创建 delivery 目录；
- 不修改 V1.0 冻结设计或 V1.2 PRD；不提交 Git。

## 4. 实现要点

- 状态机：READY / MAP_LOADED / TERMINATING；启动 READY；calculate 在无地图时返回 E_MAP_NOT_LOADED；load_map 成功进入/保持 MAP_LOADED，失败原子保留旧状态；shutdown 返回 TERMINATING 后释放地图并以 0 退出。
- hello：state 动态返回 READY 或 MAP_LOADED；字段固定为 protocolVersion/engineVersion/state/coordinateTypes。
- load_map：path 非空字符串且为绝对路径，否则 E_REQUEST_INVALID；不存在/非普通文件/不可读 → E_MAP_NOT_FOUND；损坏/伪 TIFF/ZIP/非 TIFF → E_MAP_OPEN_FAILED；无 CRS → E_MAP_CRS_MISSING；仿射缺失/非有限/不可逆 → E_MAP_TRANSFORM_INVALID；候选地图全部校验成功后一次性替换 current_map；成功响应仅含 state/crs/width/height/bands，crs 为 EPSG 或规范化 WKT2。
- 三类坐标：wgs84（lon/lat，[-180,180]/[-90,90]，响应保留原始值）、map_crs（x/y，逆仿射转 pixel 并范围校验）、pixel（零基连续 col/row，半开区间，不加 0.5、不交换）；统一经正向链路归一化为 WGS84。
- calculate：无地图优先 E_MAP_NOT_LOADED；pointA/pointB/speedMps 缺失 → E_REQUEST_INVALID；类型/字段/范围错误 → E_POINT_TYPE/E_POINT_INVALID/E_POINT_OUT_OF_BOUNDS/E_CRS_TRANSFORM；速度仅接受 JSON 整数 1–99，否则 E_SPEED_INVALID；距离复用 pyproj.Geod WGS84 测地线；时间复用 TASK-007 唯一实现；roundedSeconds ≥ 360000 → E_TIME_LIMIT（不返回部分 data）；同一点返回 0/00:00:00；可分类失败 → E_CALCULATION。
- 错误码：保留 TASK-008 五个传输错误码，新增 E_MAP_NOT_LOADED/E_MAP_NOT_FOUND/E_MAP_OPEN_FAILED/E_MAP_CRS_MISSING/E_MAP_TRANSFORM_INVALID/E_POINT_TYPE/E_POINT_INVALID/E_POINT_OUT_OF_BOUNDS/E_CRS_TRANSFORM/E_SPEED_INVALID/E_TIME_LIMIT/E_CALCULATION；E_INTERNAL 仅为最后保护；不按异常 message 匹配错误码。

## 5. 验收项

- 状态机、原子替换（失败保留旧地图与 MAP_LOADED）、切换后使用新地图；
- 三类坐标及混合组合、旋转/剪切仿射、无 0.5/无交换断言；
- 越界、类型、字段、CRS 转换失败映射；
- 独立 pyproj.Geod 基准差异 ≤ 0.5 m；速度 1/99；同一点 0；359999 成功 / 360000 E_TIME_LIMIT；真实远距离 E_TIME_LIMIT；
- 同一子进程 hello→load_map→多次 calculate→hello→shutdown；同一地图连续 100 次 calculate 顺序一致、不串线；
- stdout 仅单行协议 JSON；stderr 无请求原文/路径/坐标/结果/traceback；
- TASK-008 37 项、TASK-007 8 项、GUI 与 TASK-001—TASK-006 全部继续通过。

## 6. 执行结果

- 修改前基线完整测试：214 passed, 1 warning；
- TASK-009 定向 tests/test_worker_engine.py：49 passed；
- Worker 联合（protocol + engine）：86 passed；
- 无 GUI 核心联合（headless + engine + protocol）：94 passed；
- 修改后完整测试：263 passed, 1 warning（警告为既有 rasterio NotGeoreferencedWarning，未新增）；
- python -m compileall -q main.py worker_main.py app tests：通过；
- git diff --check：仓库级仅命中 crawler/全部代码.txt 的既有无关问题；项目未进入 Git 索引，以文件清单与 SHA256 快照补足；
- 未实现 Java 示例、Nuitka、交付目录；未提交 Git。

## 7. 遗留问题

- 无阻断项；协议级验收矩阵与 V1.2 交叉基准归档属 TASK-010；
- 项目整体仍未进入 Git 索引，所有改动未提交。


# TASK-010：系统化协议验收矩阵与 V1.2 业务基准交叉验证

## 1. 任务基本信息

- 状态：COMPLETED（本轮实施完成，未提交 Git）
- 类型：测试、审计、追踪与归档（不新增业务能力，不修改生产代码）
- 冻结基线：《无人机二维航程计算样品_产品需求文档_V1.2_业务规则冻结》、《无人机二维航程计算引擎_Java21常驻子进程集成技术设计_V1.0_冻结版》
- 前置任务：TASK-007 / TASK-008 / TASK-009，基线 263 passed, 1 warning
- 工作目录：workspace/drone-range-simulation

## 2. 实际新增文件

- `tests/protocol_acceptance_helpers.py`：临时 GeoTIFF 生成、子进程安全读写清理、独立数学基准辅助、响应结构断言；
- `tests/test_protocol_acceptance_matrix.py`：协议验收矩阵（TRN/ENV/STA/MAP/PNT/CAL/ERR/LIF，171 项）；
- `tests/test_v12_cross_validation.py`：V1.2 独立交叉验证（V12-001..013，13 项）；
- `docs/PROTOCOL_ACCEPTANCE_MATRIX.md`：184 个 Case ID 完整矩阵、错误码/状态/响应字段总表、stdout/stderr 审计、TASK-009 账目勘误；
- `docs/V1_2_CROSS_VALIDATION.md`：V1.2 独立 oracle 方法与可复核数值；
- 追加 `docs/TASK.md`、`docs/CHANGELOG.md`。

## 3. 矩阵数量

- Case ID 总数：184（TRN 19、ENV 11、STA 13、MAP 28、PNT 46、CAL 32、ERR 18、LIF 4、V12 13）；
- 17 个冻结错误码全部经公共协议入口触发；
- READY/MAP_LOADED/TERMINATING 状态转换全覆盖；
- 真实子进程完整序列 + 连续 100 次 calculate 通过。

## 4. V1.2 基准数量

- V12-001..013 共 13 项；每项比较独立 oracle / WorkerEngine / NDJSON 三条链，条件允许时增加既有领域函数第四条链；
- 独立期望值与实际值距离绝对误差为 0 m（远小于 ≤0.5 m 冻结阈值）；
- 359999 秒成功（99:59:59）、360000 秒 E_TIME_LIMIT、真实远距离 E_TIME_LIMIT 均通过。

## 5. 测试结果

- 修改前基线：263 passed, 1 warning；
- TASK-007~009 联合回归：94 passed；
- 协议矩阵：171 passed；V12 交叉验证：13 passed；TASK-010 联合：184 passed；
- Worker 全部相关（headless+protocol+engine+matrix+V12）：278 passed；
- 完整测试：447 passed, 1 warning（仅既有 rasterio NotGeoreferencedWarning，无新增；无 skip、无 xfail）；
- compileall：通过；git diff --check：仓库级仅命中 crawler/全部代码.txt 的既有无关问题（未修改 crawler）。

## 6. TASK-009 账目勘误

TASK-009 回执第 14 节文字误将 app/headless_core.py、app/worker_protocol.py 列入“28 个未修改文件”。
经 TASK-009 修改前后快照重新核验：修改前 34 项；修改 6 项（geotiff_loader、coordinate_converter、headless_core、worker_protocol、TASK.md、CHANGELOG.md）；新增 2 项（worker_engine.py、test_worker_engine.py）；未修改 28 项；完成后 36 项；用户文档哈希未变。
该勘误仅涉及回执文字，实际变更集合与正确账目一致；未改写 docs/TASK.md 与 docs/CHANGELOG.md 中 TASK-009 原始记录。

## 7. 明确未进入阶段

- 未进入 Java 示例、Nuitka 构建或交付包阶段；
- 未修改任何生产代码、现有测试、冻结文档或使用手册；
- 未执行 Git add、commit、push。


# TASK-010 验收补正 R1

## 1. 任务基本信息

- 状态：COMPLETED（本轮补正完成，未提交 Git）
- 类型：测试、文档与账目补正（不修改任何生产代码）
- 环境变化：用户已更新 Python，.venv 当前为 Python 3.14.7；既有 263 项基线在 3.14.7 下仍为 263 passed, 1 warning
- 工作目录：workspace/drone-range-simulation

## 2. Case ID 数量矛盾核清

- 补正前实际测试编号：PNT 46（缺口 PNT-028/029/033/041）、CAL 32（缺口 024/026/027，且 025/026/027 曾合并为一个测试）、MAP 28、LIF 4（编号 001/005/006/011 不连续）；
- 原回执“PNT-001..044 共 44 项 + PNT-045..050 共 6 项 = 50 项”与分类统计“PNT 46”的矛盾原因：实际只写了 46 个测试且存在 4 个编号缺口，并非存在 50 项；
- 补正方式：按冻结覆盖补齐缺失用例并重编号，不删除测试、不合并覆盖、不凑数；
- 补正后：TRN 19、ENV 11、STA 13、MAP 33、PNT 50、CAL 35、ERR 18、LIF 4、V12 13，总计 **196**，全部连续唯一。

## 3. CRS 存在但转换器建立失败

- 新增 MAP-032（READY）与 MAP-033（MAP_LOADED 原子保留）：临时 GeoTIFF 自身 CRS 合法（EPSG:3857），仅在 `CoordinateConverter` 建立边界注入确定性异常（monkeypatch `app.headless_core.CoordinateConverter` 构造抛 CoordinateConversionError）；
- 断言：E_MAP_CRS_MISSING、固定 message、无 data/路径/异常原文/traceback、READY 失败后仍 READY、已加载地图 A 时失败后仍 MAP_LOADED 且 calculate 结果与失败前一致、Worker 可继续处理下一条合法请求；
- 未直接 monkeypatch 错误码映射，未让 load_map 直接返回错误码。

## 4. 非有限仿射经真实生产校验器

- 使用 rasterio 以 r+ 模式向真实临时 GeoTIFF 写入 NaN / +Infinity / −Infinity 仿射参数并持久化；
- 生产 `_is_valid_transform` 直接接收非有限参数并拒绝（未替换、未绕过该校验器）；
- MAP-017（NaN）、MAP-018（+Infinity）、MAP-019（−Infinity）→ E_MAP_TRANSFORM_INVALID，固定 message、无泄漏、READY 保持；MAP-020 验证已加载地图 A 时原子保留；
- 原“monkeypatch _is_valid_transform 返回 False”的弱测试已移除。

## 5. 文档哈希与 V1.2 误差表述

- 统一为“3 份逻辑文档；4 个物理文件”，4 个物理文件修改前后大小与 SHA256 完全一致（V1.2 PRD `8294…`、V1.0 冻结设计 `460C…`、使用手册 DOCX `F284…`、PDF `63F3…`）；
- V1.2 最大误差表述纠正：参与“返回距离最大误差”统计的用例为 V12-001..010、V12-013 共 11 项，最大绝对误差 0 m；V12-011/012 为 E_TIME_LIMIT 失败边界（无 data），分别记录 oracle 距离/roundedSeconds 与两条协议实际错误码，不纳入距离误差统计。

## 6. 补正结果

- 修改前基线（排除 TASK-010 新测试）：263 passed, 1 warning；
- TASK-007~009 联合回归：94 passed；
- 协议矩阵：183 passed；V12：13 passed；TASK-010 联合：196 passed；
- 完整测试：459 passed, 1 warning（仅既有 rasterio NotGeoreferencedWarning，无新增；无 skip、无 xfail）；
- compileall：通过；文档归档后完整测试仍为 459 passed, 1 warning；
- 未修改生产代码、未修改 TASK-010 之前已有测试、未修改冻结文档/使用手册；
- 未执行 Git add、commit、push。


# TASK-010 验收补正 R1-A：Case ID 稳定性修复

## 1. 任务基本信息

- 状态：COMPLETED（本轮修复完成，未提交 Git）
- 类型：测试标识与归档追溯关系修复（不修改生产代码、不改变任何测试断言/输入/预期结果/覆盖范围）
- 原则：Case ID 是稳定审计标识，**不要求连续，稳定语义优先**；编号空档合法
- 工作目录：workspace/drone-range-simulation

## 2. MAP 编号修复

恢复 MAP-001..028 在 TASK-010 原报告中的原有语义；新增用例改为 MAP-029..033：

| 旧 ID（R1 阶段） | 最终 ID | 语义 | 说明 |
| --- | --- | --- | --- |
| MAP-018（+Infinity） | MAP-029 | +Infinity 仿射 → E_MAP_TRANSFORM_INVALID | 新增 |
| MAP-019（−Infinity） | MAP-030 | −Infinity 仿射 → E_MAP_TRANSFORM_INVALID | 新增 |
| MAP-020（非有限原子保留） | MAP-031 | 已加载 A 时非有限 B 失败且原子保留 A | 新增 |
| MAP-021（非法波段） | MAP-018 | 非法波段 → E_MAP_OPEN_FAILED | 恢复原语义 |
| MAP-022（EPSG CRS） | MAP-019 | EPSG CRS 输出 | 恢复原语义 |
| MAP-023（WKT2） | MAP-020 | 无 EPSG 返回规范化 WKT2 | 恢复原语义 |
| MAP-024（无 preview） | MAP-021 | 不生成 preview | 恢复原语义 |
| MAP-025（无 QApplication） | MAP-022 | 不创建 QApplication | 恢复原语义 |
| MAP-026（无 PySide6） | MAP-023 | 导入链无 PySide6 | 恢复原语义 |
| MAP-027（data 键集合） | MAP-024 | 成功 data 键集合精确 | 恢复原语义 |
| MAP-028（原子失败保留） | MAP-025 | 失败加载保留旧地图与结果 | 恢复原语义 |
| MAP-029（原子切换） | MAP-026 | 成功切换使用新地图 | 恢复原语义 |
| MAP-030（多次失败保持） | MAP-027 | 多次失败不降级 | 恢复原语义 |
| MAP-031（释放无异常） | MAP-028 | 替换/释放旧地图无异常 | 恢复原语义 |
| MAP-032 | MAP-032 | CRS 存在但转换器建立失败，READY 保持 | 保持不变 |
| MAP-033 | MAP-033 | CRS 存在但转换器建立失败，MAP_LOADED 原子保留 | 保持不变 |

MAP-017 保持“非有限仿射参数”语义（现以真实 NaN GeoTIFF 验证）。最终 MAP 集合：MAP-001..033。

## 3. LIF 编号修复

恢复既有稳定 ID：**LIF-001、LIF-005、LIF-006、LIF-011**（编号存在空档合法，不要求连续）。

## 4. CAL 核账（32 → 35）

| R1 前 Case ID | R1 后最终 ID | 测试语义 | 是否既有 | 是否新增/拆分 | 既有 ID 含义是否变化 |
| --- | --- | --- | --- | --- | --- |
| CAL-001..023 | CAL-001..023 | 速度/距离/时间/响应既有用例 | 是 | 否 | 否 |
| CAL-024（空缺） | CAL-024 | 独立 Geod 基准差异 ≤0.5 m | 否 | 新增 | 不适用 |
| CAL-025（合并时间公式） | CAL-025 | exact/rounded/duration 三个时间公式（合并） | 是 | 否（恢复原合并语义） | 否 |
| CAL-026（空缺） | CAL-026 | roundedSeconds=ceil(exactSeconds)（拆分自 CAL-025） | 否 | 拆分新增 | 不适用 |
| CAL-027（空缺） | CAL-027 | duration 由同一 roundedSeconds 经 divmod 生成（拆分自 CAL-025） | 否 | 拆分新增 | 不适用 |
| CAL-028..035 | CAL-028..035 | 边界与响应既有用例 | 是 | 否 | 否 |

## 5. PNT

PNT-028、029、033、041 原为空缺，本轮补入冻结规则用例可保留，无需改动；PNT 最终为 PNT-001..050。

## 6. 验证结果

- collect-only：196 个 nodeid，全部唯一、无 NOID；TRN 19、ENV 11、STA 13、MAP 33、PNT 50、CAL 35、ERR 18、LIF 4、V12 13；
- 协议矩阵 183 passed；V12 13 passed；联合 196 passed；TASK-007~009 回归 94 passed；compileall 通过；完整测试 459 passed, 1 warning（既有，无新增；0 skip、0 xfail）；
- 修改文件：tests/test_protocol_acceptance_matrix.py、docs/PROTOCOL_ACCEPTANCE_MATRIX.md、docs/TASK.md、docs/CHANGELOG.md；
- 未修改生产代码、V12 测试、共享辅助、既有测试逻辑、冻结文档或目标项目外文件；
- 未执行 Git add、commit、push。


# TASK-010 正式验收关闭与 Git 基线固化

- 日期：2026-08-09
- TASK-010 状态：CLOSED / 正式验收通过。
- 协议矩阵：183 passed；V1.2 交叉验证：13 passed；TASK-010 联合：196 passed。
- 全量测试：459 passed，1 条既有 rasterio NotGeoreferencedWarning；skip=0，xfail=0。
- collect-only：196，全部唯一，无 NOID。
- MAP-001..028 已恢复历史语义；新增 MAP-029..033。
- PNT-001..050；CAL 共 35 项；LIF 最终 ID：001、005、006、011。
- Case ID 允许存在空档，以历史语义稳定为优先。
- 未发现生产缺陷；TASK-010 的 R1/R1-A 验收补正未修改生产代码。
- 本 Git 提交只是固化此前已完成并验收的 TASK-007..010 内容，不新增生产逻辑。
- 下一阶段为 TASK-011 Java 21 ProcessBuilder 集成，但本次尚未开始。
## 空白规范化补充说明（TASK-010-GIT-BASELINE-CONTINUE）

- 日期：2026-08-09；
- 为满足 Git whitespace 质量门槛，仅在独立基线 worktree 删除 3 个文件末尾各 1 个冗余 LF：
  - app/coordinate_converter.py
  - app/headless_core.py
  - tests/test_protocol_acceptance_matrix.py
- 未修改任何逻辑、断言或运行行为；
- 正式源项目保持只读且哈希未变；
- 最终目标与源项目的关系调整为：
  - 36 项逐字节一致；
  - 3 项仅删除末尾 1 个冗余 LF；
  - 2 项文档仅有末尾追加；
- 本处理不改变 TASK-010 已正式验收通过的结论；
- TASK-011 尚未开始。
