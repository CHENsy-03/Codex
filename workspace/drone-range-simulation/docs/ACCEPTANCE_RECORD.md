# 无人机航程时间计算样品最终验收记录

## 一、文档定位与当前结论

- 本文件汇总 TASK-001—TASK-007D-R1 的最终有效验收结论，是唯一最终验收摘要，不复制多轮执行报告；
- TASK-007D-R1：PASS；
- Windows 11 本机技术验收已经完成；
- Windows 10 验收仍为 PENDING-EXTERNAL；
- 首次使用者两分钟验收仍为 PENDING-EXTERNAL；
- TASK-008 文档收口：已完成（TASK-008-A..D 均 PASS）；TASK-010 验收归档：CLOSED；TASK-011 Java 外部客户端：CLOSED；
- Git：本项目独立 worktree 已建立基线提交（b045d19、8ffdc47），尚未推送远端；
- 创建本验收摘要不代表两个外部验收已经通过。

任务演进与证据边界详见 [TASK.md](TASK.md)。

## 二、任务历史边界

- 首次 TASK-007D：历史 BLOCKED（保留）；
- TASK-007D-PRE：QUALIFIED；
- TASK-007D-R1：PASS；
- 三者是相互独立的历史记录；后续 PRE 和 R1 没有抹除首次 TASK-007D 的 BLOCKED 历史。
- 首次 BLOCKED 的具体原因仅采用原始记录中明确存在的表述：指定数据 Rectangle_#1_卫图.zip 的主影像为 298×249（最长边 298 px），不满足 V1.2 AC-04“最长边远大于 2048 px”的大影像定义，按任务停止条件停止。

## 三、自动化技术验收

- 自动化最终结果：169 passed；
- TASK-007C-R1 后警告数由 2 降至 1（不是 0 warnings；剩余 1 条为修改前既有的 rasterio NotGeoreferencedWarning）；
- 上述为历史验收结果，本轮没有重新运行测试。
- pip check 与 compileall：历史报告中存在明确、无冲突的通过结论（pip check “No broken requirements found”、compileall 退出码 0），此处仅记录历史汇总结论；不伪造执行日期、命令逐行输出或原始日志。

## 四、真实数据资格与导入验收

- 合格真实大影像：Rectangle_#2_卫图.zip；
- 影像尺寸：4928 × 4040；
- TASK-007D-PRE 结论：QUALIFIED；
- TASK-007D-R1 使用该合格影像完成复验；
- 实际导入时间范围：543–582 ms。
- 边界：本记录未判断地图数据的法律授权，未声明该数据可对外分发；未修改、复制或重新打包地图数据；未伪造未记录的地图哈希。

## 五、Windows 11 三次独立进程主流程验收

- 三次验收均为独立进程；
- 距离结果：2064.11 米（2.06 公里）。

| 独立进程 | 速度 | 整数秒 | HH:MM:SS |
| --- | ---: | ---: | --- |
| 第 1 次 | 10 m/s | 207 秒 | 00:03:27 |
| 第 2 次 | 30 m/s | 69 秒 | 00:01:09 |
| 第 3 次 | 99 m/s | 21 秒 | 00:00:21 |

## 六、启动与交互性能

启动时间：

| 独立进程 | 启动时间 |
| --- | ---: |
| 第 1 次 | 287.21 ms |
| 第 2 次 | 135.74 ms |
| 第 3 次 | 140.83 ms |

- 导入时间范围：543–582 ms；
- 四类交互（滚轮→视图变换、右键拖拽→平移、A/B 点击→字段更新、速度修改→时间字段更新）的 P95 均不超过 2.351 ms（历史报告明确列出的四类名称）。

## 七、坐标独立交叉核验

- 坐标使用独立方法（rasterio 原始 affine + pyproj Transformer always_xy=True）与产品内部结果交叉核验；
- 最大地面误差：1.384 m；
- 该结论只基于相同坐标点之间的独立核验。
- 边界：不跨不同坐标点组合误差；不将不同样本的经纬度分量拼接；不伪造逐点原始表格；不引入已被最终勘误否定的误差数据。

## 八、内存测量结果

三个指标完全分开，并按同一次独立进程横向对应：

| 独立进程 | post-import PollMaxWS | lifetime PollMaxWS | OS PeakWorkingSet64 |
| --- | ---: | ---: | ---: |
| 第 1 次 | 141,574,144 B | 216,158,208 B | 284,770,304 B |
| 第 2 次 | 141,565,952 B | 235,634,688 B | 284,196,864 B |
| 第 3 次 | 141,369,344 B | 258,912,256 B | 284,254,208 B |

- 每行均满足：post-import PollMaxWS ≤ lifetime PollMaxWS ≤ OS PeakWorkingSet64；
- 三类指标不能互换；
- 不声称 POST 阶段“稳定”；
- 不把较高内存归因于任何未经证明的具体操作；
- 不根据这些汇总值推测内存增长原因。

## 九、证据保留边界

- 原始逐条 CSV 已清理；
- 当前只保留经核验的汇总证据；
- 不声称已保存不存在的原始 CSV、完整终端日志或逐次原始明细；
- 本文件不伪造执行日期、Git 提交号、签字或原始日志；
- 本轮没有重新运行产品、自动化测试、GUI、性能测试或外部验收。

## 十、待外部验收项目

| 项目 | 状态 | 当前边界 |
| --- | --- | --- |
| Windows 10 实机验收 | PENDING-EXTERNAL | 尚未实际执行，不得写成 PASS |
| 首次使用者两分钟验收 | PENDING-EXTERNAL | 尚未实际执行，不得写成 PASS |

- 后续只会准备外部验收指南（待创建文件：docs/EXTERNAL_ACCEPTANCE_GUIDE.md，当前仅作为待创建文件名提及）和空白记录表；
- 准备材料不等于外部验收通过；
- 不得预填执行人、日期、时间、结果或签名；
- 本轮不创建 docs/EXTERNAL_ACCEPTANCE_GUIDE.md。

## 十一、最终验收口径

- TASK-007D-R1：PASS；
- Windows 11 本机技术验收：PASS；
- Windows 10 验收：PENDING-EXTERNAL；
- 首次使用者两分钟验收：PENDING-EXTERNAL；
- TASK-008-B（最终验收摘要创建）：PASS；
- TASK-008 文档收口：已完成（TASK-008-A..D 均 PASS）；TASK-010 验收归档：CLOSED；TASK-011 Java 外部客户端：CLOSED；
- Git：本项目独立 worktree 已建立基线提交（b045d19、8ffdc47），尚未推送远端；

不使用“项目全部验收完成”“正式交付完成”“所有平台均通过”等超出证据范围的表述。

## 九、TASK-011 内部自动化验收记录

- 验收提交：8ffdc47edbad2f003bfc12456ff9df88fa7279af；
- Java：Tests run: 30, Failures: 0, Errors: 0, Skipped: 0；
- Python：459 passed，1 个既有 rasterio NotGeoreferencedWarning；
- Java 测试组成：WorkerCommandLineTest 4、NdjsonCodecTest 13、DroneWorkerClientIntegrationTest 1、DroneWorkerClientProcessTest 12；
- 覆盖范围：命令行、NDJSON、真实 worker 往返、超时、业务异常、协议错误、传输错误、队列溢出、EOF、restart、shutdown、close、PID 回收；
- 结论仅限内部自动化验收通过；不改变以下外部验收状态：Windows 10 实机验收 PENDING-EXTERNAL、首次使用者两分钟验收 PENDING-EXTERNAL。
