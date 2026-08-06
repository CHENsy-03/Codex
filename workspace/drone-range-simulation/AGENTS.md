# AGENTS.md（项目级）

> 本文件定义 `workspace/drone-range-simulation` 项目的最高开发原则。
>
> 本项目是独立样品，与仓库根目录的"通用信息采集平台"无关；
> 根目录 `docs/SYSTEM_ARCHITECTURE.md`（Go API + Python Worker + Redis + 数据库）不适用于本项目，
> 不得复制、修改或套用其中的架构。

---

# 1. 项目定位

本项目是**无人机二维航程计算样品**：

- 单进程、单窗口、单地图的 Python 桌面样品；
- 固定 Python 3.14.4（普通 64 位 CPython，非 free-threaded、非 Conda）；
- 只实现需求文档（V1.1 地图数据包格式更新）规定的二维闭环；
- 唯一交付主线：ZIP/GeoTIFF → 显示地图 → 选择 A/B 点 → 输入速度 → 二维距离与飞行时间。

# 2. 技术基线

- GUI：PySide6；地图视图：QGraphicsView + QGraphicsScene；
- 栅格读取：rasterio + numpy（降采样预览，最长边 ≤ 2048 px）；
- 坐标与距离：pyproj（Transformer always_xy=True、Geod.inv WGS84 测地线距离）。

# 3. 明确禁止

禁止在本项目中加入：

- Go、FastAPI、Java 接口、HTTP 通信、API Key、局域网访问；
- 数据库（含 SQLite）、Launcher、后台服务、进程守护、日志平台、性能监控平台；
- Leaflet、QWebEngine、QWebChannel、XYZ 瓦片、在线底图、多地图管理；
- DEM、高程采样、三维距离、坡度、障碍物、路径规划；
- 飞行动画、开始/暂停/恢复/停止、任务状态机、运行策略；
- 完整分辨率金字塔浏览、分块加载、遥感专业影像处理。

# 4. 任务流程

每个任务必须：

1. **先检查**：阅读适用 AGENTS.md、需求文档与现有代码，确认调用关系与数据流；
2. **后修改**：最小增量，仅修改任务要求的内容，禁止顺手优化或无关重构；
3. **再测试**：运行对应测试，禁止删除测试、禁止跳过失败测试、禁止弱化断言。

# 5. Git 原则

- 禁止未经确认执行 `git commit` 或 `git push`；
- 禁止 `git reset --hard`、`git clean`、强制覆盖或删除历史；
- 禁止将附件（ZIP/GeoTIFF 样例）复制进 Git 项目。

# 6. 文档同步

涉及接口、配置、模块或行为变化时，必须同步更新 `docs/CHANGELOG.md` 与相关文档。

---

End.