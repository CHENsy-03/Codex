# 变更日志

本文件只记录仓库级规范、目录和治理变化。项目功能变更记录在项目内部变更日志中。

---

## 2026-08-11

### Changed

- 根级 `AGENTS.md`、`README.md` 和 `docs/` 改为多项目仓库通用规范
- 移除根级规范中的项目专属实现、任务编号、测试数量和提交记录
- `docs/DEVELOPMENT_RULES.md` 改为跨项目通用开发规则
- `docs/TASK.md` 改为通用任务模板和状态定义
- `docs/SYSTEM_ARCHITECTURE.md` 改为仓库级组织架构
- `docs/AI_WORKFLOW.md`、`docs/DEVELOPMENT_CHECKLIST.md` 修复转义文本并通用化
- 新增 `docs/decisions/ADR_PROCESS.md` 通用 ADR 流程
- 根级 `AGENTS.md` 已通用化为多项目仓库规则
- crawler 专属 ADR-001/002 已从 `docs/decisions/` 迁移至 `workspace/crawler/docs/decisions/`
- 两份 ADR 保留原编号和历史决策内容
- `docs/decisions/ADR_PROCESS.md` 已明确根级与各项目分别独立编号
- 这是文档治理和归属修正，不是 crawler 架构决策变更

### Note

- 原 `docs/decisions/ADR-001.md`、`ADR-002.md` 属于项目专属历史决策，本轮保留原文并建议迁移到对应项目的 `docs/decisions/`，未修改 `workspace/**`。

---

## 2026-08-06

### Changed

- README.md 目录树同步当前结构，修复工作区原则章节位置
- docs/DEVELOPMENT_CHECKLIST.md 新增阻塞检查章节
- docs/AI_WORKFLOW.md 改为单向控制流

---

## 2026-07-26

### Added

- 目录结构重组：workspace / archive / output / .agents
- AGENTS.md 项目最高原则文档
- docs/AI_WORKFLOW.md：AI 协作工作流
- docs/CHANGELOG.md：变更日志
- README.md：完整工作区入口文档
- output/：AI 输出隔离目录
- .agents/prompts/、templates/、reviews/、workflows/

### Changed

- 所有项目移入 workspace/，归档项目移入 archive/

### Note

- 原 ADR-001、ADR-002 为项目专属架构决策，现标记为待迁移记录。

---

## 2026-07-14

### Fixed

- 协议文档格式修正

---

## 2026-07-06

### Added

- 新增若干独立项目目录
