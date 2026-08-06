# 变更日志

## 2026-08-06：项目初始化（TASK-001）

- 新建项目基线：AGENTS.md、.gitignore、requirements.txt、README.md；
- 建立 Python 3.14.4 虚拟环境（.venv，不入库），安装固定依赖：
  PySide6 6.11.1、rasterio 1.5.0、pyproj 3.7.2、numpy 2.5.1、pytest 9.1.1；
- 新增基础窗口：main.py、app/__init__.py、app/main_window.py、app/map_view.py；
- 新增冒烟测试 tests/test_smoke.py；
- 新增任务记录 docs/TASK.md。
## 2026-08-06：地图数据安全加载与预览显示（TASK-002）

- 新增 `app/geotiff_loader.py`：ZIP/TIF 安全加载、元数据校验、降采样预览（最长边 ≤ 2048）；
- 更新 `app/map_view.py`：RGB 预览显示、自动适应窗口、唯一图片项；
- 更新 `app/main_window.py`：导入按钮接入真实加载流程，失败保留旧地图；
- 新增 `tests/test_geotiff_loader.py`；
- 更新 README.md、docs/TASK.md。
## 2026-08-06：地图缩放、平移与 A/B 点选择（TASK-003）

- 更新 `app/map_view.py`：滚轮缩放（1.25 倍/步，最多 12 步，最小完整适应）、右键拖动平移、左键依次选择 A/B 点、A/B 标记与唯一连线、`MapPoint` 点位模型（scene_x/scene_y/source_col/source_row）；
- 更新 `app/main_window.py`：点位信号连接、状态提示（A 已选/B 完成/清除/已满提示）、清除点位按钮状态；
- 新增 `tests/test_map_interaction.py`；
- 更新 README.md、docs/TASK.md。
## 2026-08-06：栅格坐标 → 地图坐标 → WGS84 经纬度（TASK-004）

- 新增 `app/coordinate_converter.py`：`GeoPoint`（frozen dataclass）与 `CoordinateConverter`（affine 六参数 + pyproj always_xy=True 转 EPSG:4326）；
- 更新 `app/main_window.py`：建立转换上下文、派生 A/B GeoPoint、经纬度显示（经度/纬度 6 位小数）、加载失败/取消时原子状态保持；
- 新增 `tests/test_coordinate_conversion.py`；
- 更新 README.md、docs/TASK.md。
## 2026-08-06：WGS84 椭球面二维测地线距离（TASK-005）

- 新增 `app/distance_calculator.py`：`DistanceResult`（frozen dataclass）与 `calculate_distance`（pyproj.Geod(ellps="WGS84").inv，完整精度 longitude/latitude）；
- 更新 `app/main_window.py`：A/B 点齐全后计算并显示距离（两位小数 + 米），失败保持 `--` 且不崩溃；
- 新增 `tests/test_distance_calculation.py`；
- 更新 README.md、docs/TASK.md。
## 2026-08-06：整数速度、飞行时间与 HH:MM:SS（TASK-006）

- 新增 `app/flight_time_calculator.py`：严格整数速度解析（1–99 m/s）、`exact_seconds = distance_m / speed_m_s`、`math.ceil` 整数秒、`format_hhmmss`（上限 99:59:59）、`FlightTimeResult`；
- 更新 `app/main_window.py`：速度框 textChanged 即时自动计算；状态提示“请输入飞行速度 / 输入错误 / 飞行时间超过99小时 / A/B 点选择完成”；清除与新地图保留速度文本；
- 新增 `tests/test_flight_time_calculation.py`；
- 更新 README.md、docs/TASK.md。
## 2026-08-06：验收文档收口（TASK-008）

- TASK-008-A：补录 TASK-007 系列最终记录（docs/TASK.md）；
- TASK-008-B：创建最终验收摘要（docs/ACCEPTANCE_RECORD.md）；
- TASK-008-C：创建外部验收指南与空白记录表（docs/EXTERNAL_ACCEPTANCE_GUIDE.md）；
- TASK-008-D：完成 README 与 CHANGELOG 文档收口。
- 当前边界：Windows 10 实机验收仍为 PENDING-EXTERNAL；首次使用者两分钟验收仍为 PENDING-EXTERNAL；本轮未执行任何外部验收；TASK-008 整体仍为 IN PROGRESS；本条目形成时 Git 尚未提交；后续入库状态以本仓库 Git 历史为准。