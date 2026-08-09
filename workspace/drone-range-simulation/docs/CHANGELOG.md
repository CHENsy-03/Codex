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
- 当前边界：Windows 10 实机验收仍为 PENDING-EXTERNAL；首次使用者两分钟验收仍为 PENDING-EXTERNAL；本轮未执行任何外部验收；TASK-008 整体仍为 IN PROGRESS；Git 尚未提交。


## 2026-08-07：无 GUI 计算核心抽取（TASK-007）

- 新增 `app/geotiff_loader.py`：`GeoTiffMetadata` 与 `load_geotiff_metadata()`（仅读取直接 GeoTIFF 元数据，不生成预览、不处理 ZIP）；
- 新增 `app/headless_core.py`：无 GUI 门面（`HeadlessMap`、`load_map`、`geotiff_to_wgs84`），复用现有坐标/距离/时间唯一实现；
- 新增 `tests/test_headless_core.py`：8 项无 GUI 核心测试（含无 PySide6 导入与独立 pyproj 基准交叉验证）；
- 更新 docs/TASK.md；
- 测试结果：修改前完整测试 169 passed；新增定向测试 8 passed；修改后完整测试 177 passed，1 warning（既有 rasterio 警告，未新增）；
- 未实现 worker_main.py、stdin/stdout NDJSON、协议状态机、Java 示例、Nuitka 或交付包。


## 2026-08-07：常驻 Worker 入口与严格 NDJSON 传输循环（TASK-008）

- 新增 `worker_main.py`：极薄进程入口，仅导入并执行 `app.worker_protocol.main`；
- 新增 `app/worker_protocol.py`：协议常量（PROTOCOL_VERSION=1、ENGINE_VERSION="1.0.0"）、请求校验、响应构造与严格串行 NDJSON 循环；
- 本阶段实际支持 `hello`（READY）与 `shutdown`（TERMINATING）；传输层错误码：E_PROTOCOL_INVALID_JSON、E_PROTOCOL_VERSION、E_OPERATION_UNKNOWN、E_REQUEST_INVALID、E_INTERNAL；
- stdout 仅输出协议 JSON（UTF-8、LF、立即 flush、无 BOM/日志/traceback）；stderr 仅记录进程日志；
- 新增 `tests/test_worker_protocol.py`：37 项纯函数与真实子进程测试（含 flush、多请求串行、非法输入、shutdown、stdin EOF、stdout 纯净性）；
- 测试结果：基线 177 passed；定向 37 passed；联合定向（TASK-007+TASK-008）45 passed；完整测试 214 passed，1 warning（既有 rasterio 警告，未新增）；
- 明确未实现：load_map、calculate、完整地图状态机、Java 示例、Nuitka、交付目录、Git 提交。


## 2026-08-07：状态机、原子 load_map、三类坐标与完整 calculate 协议（TASK-009）

- 新增 `app/worker_engine.py`：WorkerEngine（READY/MAP_LOADED/TERMINATING 状态机、原子 load_map、hello/calculate/shutdown、操作级字段校验与冻结错误映射）；
- 修改 `app/worker_protocol.py`：合法操作分发给同一 WorkerEngine 实例，新增 12 个地图/坐标/计算错误码；
- hello 的 state 由固定 READY 改为动态返回当前真实状态（READY/MAP_LOADED）；
- 原子地图替换：候选地图全部校验成功后才替换 current_map，失败保留旧地图与 MAP_LOADED；
- 三类坐标解析（wgs84/map_crs/pixel，A/B 可混用）与完整 calculate 响应（归一化 WGS84、distanceMeters、exactSeconds、roundedSeconds、duration）；
- 最小修改 `app/geotiff_loader.py`（稳定异常分类）、`app/coordinate_converter.py`（逆仿射与 WGS84→地图 CRS 双向转换）、`app/headless_core.py`（wgs84_to_pixel/map_crs_to_pixel）；
- 新增 `tests/test_worker_engine.py`：49 项测试（状态机、加载错误映射、原子替换、坐标口径、速度/时间边界、100 次连续计算、stderr 纯净性）；
- 测试结果：基线 214 passed；TASK-009 定向 49 passed；Worker 联合 86 passed；无 GUI 联合 94 passed；完整测试 263 passed，1 warning（既有 rasterio 警告，未新增）；
- 明确未实现：Java 示例、Nuitka、交付目录、Git 提交。


## 2026-08-07：系统化协议验收矩阵与 V1.2 业务基准交叉验证（TASK-010）

- 新增 `tests/protocol_acceptance_helpers.py`、`tests/test_protocol_acceptance_matrix.py`（协议验收矩阵）、`tests/test_v12_cross_validation.py`（V1.2 独立交叉验证）；
- 新增 `docs/PROTOCOL_ACCEPTANCE_MATRIX.md`（184 个 Case ID 矩阵、17 个错误码、状态/响应字段总表、stdout/stderr 审计、TASK-009 账目勘误）与 `docs/V1_2_CROSS_VALIDATION.md`（独立 oracle 与可复核数值）；
- 17 个冻结错误码全部经公共协议入口覆盖；README 中不涉及协议部分，无需修改；
- 独立 oracle 方法：测试侧独立仿射、pyproj.Transformer(always_xy=True)、pyproj.Geod、distance/speed+ceil+divmod；三条链（独立/WorkerEngine/NDJSON）全部一致；
- 测试结果：基线 263 passed；TASK-010 定向 184 passed；Worker 全部相关 278 passed；完整测试 447 passed，1 warning（既有 rasterio 警告，未新增）；无 skip、无 xfail；
- TASK-009 回执第 14 节文字账目勘误已核验并记录（实际变更集合 6 修改 + 2 新增 + 28 未修改，用户文档未变）；
- 未修改生产代码、未修改现有测试、未修改冻结文档/使用手册；
- Java 示例、Nuitka、交付包仍未完成；未执行 Git add、commit、push。


## 2026-08-07：TASK-010 验收补正 R1

- 核清 Case ID 数量矛盾：PNT 46→50（补齐 PNT-028/029/033/041）、CAL 32→35（补齐 024，拆分 025/026/027）、MAP 28→33（真实非有限仿射 017/018/019、原子保留 020、转换器建立失败 032/033）、LIF 重编号 001..004；补正后总计 196，连续唯一；
- 新增“CRS 存在但转换器建立失败”验收（MAP-032/033）：CRS 合法，仅在 CoordinateConverter 建立边界注入异常，返回 E_MAP_CRS_MISSING，原子保留旧地图；
- 非有限仿射改为真实文件写入 NaN/±Infinity 并经生产 `_is_valid_transform` 校验（MAP-017/018/019/020），移除 monkeypatch 校验器的弱测试；
- 文档哈希统一为“3 份逻辑文档；4 个物理文件”，4 个物理文件修改前后 SHA256 一致；
- V1.2 最大误差表述纠正：可比较距离用例 11 项，最大绝对误差 0 m；V12-011/012 为 E_TIME_LIMIT 失败边界（无 data），不纳入距离误差统计；
- 测试结果：基线 263 passed；矩阵 183 passed；V12 13 passed；联合 196 passed；完整 459 passed，1 warning（既有，无新增）；无 skip、无 xfail；
- 未修改生产代码、未修改 TASK-010 之前已有测试；Java、Nuitka、交付包仍未完成；未执行 Git add、commit、push。


## 2026-08-07：TASK-010 验收补正 R1-A（Case ID 稳定性修复）

- 恢复 MAP-001..028 的 TASK-010 原语义（MAP-018 非法波段、MAP-019 EPSG、MAP-020 WKT2、MAP-021..023 无 preview/QApplication/PySide6、MAP-024 data 键集合、MAP-025..028 原子替换）；新增用例移至 MAP-029（+Infinity）、MAP-030（−Infinity）、MAP-031（非有限原子保留）；MAP-032/033（CRS 存在但转换器建立失败）保持不变；MAP-017 保持非有限仿射语义（真实 NaN GeoTIFF）；
- 恢复 LIF 既有稳定 ID：LIF-001、LIF-005、LIF-006、LIF-011（空档合法）；
- CAL 核账 32→35：CAL-001..023、028..035 为既有（含义未变）；CAL-025 恢复为合并时间公式原语义；CAL-024、026、027 为新增/拆分用例（使用此前未占用 ID）；
- 仅修改测试函数标识与文档引用，未改变任何测试断言、输入、预期结果或覆盖范围；
- 验证：collect-only 196（全部唯一、无 NOID）；矩阵 183 passed；V12 13 passed；联合 196 passed；回归 94 passed；完整 459 passed，1 warning（既有，无新增；0 skip、0 xfail）；
- 未修改生产代码；Java、Nuitka、交付包仍未完成；未执行 Git add、commit、push。


## 2026-08-09：TASK-010 正式验收关闭与 Git 基线固化

- TASK-010：CLOSED / 正式验收通过；
- 协议矩阵 183 passed；V1.2 交叉验证 13 passed；TASK-010 联合 196 passed；
- 全量 459 passed，1 条既有 rasterio warning；skip=0，xfail=0；collect-only 196，全部唯一，无 NOID；
- MAP-001..028 已恢复历史语义，新增 MAP-029..033；PNT-001..050；CAL 共 35 项；LIF 最终 ID：001、005、006、011；
- Case ID 允许存在空档，以历史语义稳定为优先；未发现生产缺陷；R1/R1-A 未修改生产代码；
- 本 Git 提交仅固化此前已完成并验收的 TASK-007..010 内容，不新增生产逻辑；
- 下一阶段为 TASK-011 Java 21 ProcessBuilder 集成，本次尚未开始。
## 2026-08-09：空白规范化补充说明（TASK-010-GIT-BASELINE-CONTINUE）

- 为满足 Git whitespace 质量门槛，仅在独立基线 worktree 删除 3 个文件末尾各 1 个冗余 LF：app/coordinate_converter.py、app/headless_core.py、tests/test_protocol_acceptance_matrix.py；
- 未修改任何逻辑、断言或运行行为；正式源项目保持只读且哈希未变；
- 最终目标与源项目关系：36 项逐字节一致；3 项仅删除末尾 1 个冗余 LF；2 项文档仅有末尾追加；
- 本处理不改变 TASK-010 已正式验收通过的结论；TASK-011 尚未开始。
