# SYSTEM_ARCHITECTURE.md

> 本文件描述仓库级组织架构，不描述任何单个项目的内部架构。
>
> 项目内部架构应写入 `workspace/<project>/docs/SYSTEM_ARCHITECTURE.md`。

---

## 1. 定位

本仓库是包含多个独立项目的软件研发工作区。

仓库级架构只解决以下问题：

- 根级目录如何组织；
- 项目如何隔离；
- 根级规范与项目内部文档如何分工；
- 共享规则和决策如何维护；
- 项目专属内容如何迁移。

具体业务架构、模块边界、数据流和技术栈由各项目自行定义。

---

## 2. 仓库目录

```text
Codex/
├── AGENTS.md
├── README.md
├── .agents/
├── docs/
│   ├── DEVELOPMENT_RULES.md
│   ├── DEVELOPMENT_CHECKLIST.md
│   ├── AI_WORKFLOW.md
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── TASK.md
│   ├── CHANGELOG.md
│   └── decisions/
├── workspace/
│   └── <project>/
├── archive/
└── output/
```

职责：

| 目录 | 职责 |
|---|---|
| `AGENTS.md` | 仓库级 AI/开发规则 |
| `README.md` | 仓库入口和文档导航 |
| `.agents/` | AI 工作目录、模板和流程 |
| `docs/` | 仓库级规范、任务模板、决策流程 |
| `workspace/` | 独立项目目录 |
| `archive/` | 已归档项目 |
| `output/` | 生成报告和交付物 |

---

## 3. 项目隔离

每个项目使用独立目录：

```text
workspace/<project>/
```

项目目录应自行维护：

- `AGENTS.md`；
- `README.md`；
- `docs/`；
- 源码、测试、配置和部署文件。

项目之间默认不共享业务代码。

跨项目复用应先通过根级规则或独立公共库解决，不得直接复制项目内部实现。

---

## 4. 根级规范与项目文档边界

| 内容 | 存放位置 |
|---|---|
| 多项目通用规则 | 根级 `AGENTS.md`、`docs/DEVELOPMENT_RULES.md` |
| 仓库目录与项目隔离 | 根级 `docs/SYSTEM_ARCHITECTURE.md` |
| 通用任务模板 | 根级 `docs/TASK.md` |
| AI 协作流程 | 根级 `docs/AI_WORKFLOW.md` |
| 仓库级治理变更 | 根级 `docs/CHANGELOG.md` |
| 项目内部架构 | `workspace/<project>/docs/SYSTEM_ARCHITECTURE.md` |
| 项目任务进度 | `workspace/<project>/docs/TASK.md` |
| 项目专属 ADR | `workspace/<project>/docs/decisions/` |

根级文档不得记录任何单个项目的任务进度、测试数量、提交记录或实现细节。

---

## 5. 通用架构约束

所有项目必须遵守以下仓库级约束：

- 项目内部规则不得与根级安全、Git 和文档同步规则冲突；
- 修改前必须阅读适用规则；
- 不得覆盖用户预存修改；
- 公共能力应唯一实现，不跨项目重复复制；
- 数据流、错误处理和测试结果必须可追踪；
- 项目文档必须与代码和配置保持同步；
- 架构决策应记录为 ADR。

---

## 6. 文档同步

项目内发生以下变化时必须更新项目内部文档：

- 公共接口；
- 数据模型；
- 配置项；
- 模块结构；
- 运行方式；
- 任务状态。

根级文档发生以下变化时必须更新仓库级文档：

- 目录结构；
- 根级规范；
- 项目隔离原则；
- 文档边界；
- 决策流程。

---

## 7. ADR 规则

架构决策记录用于保存重要决策的原因、方案、影响和不采用方案。

ADR 应放在：

```text
docs/decisions/
```

通用决策流程见 `docs/decisions/ADR_PROCESS.md`。

项目专属 ADR 应放在：

```text
workspace/<project>/docs/decisions/
```

已接受的 ADR 不得直接改写为相反结论。

需要改变时，应新增 ADR，并在旧 ADR 中注明被哪个新 ADR 替代。

---

## 8. 项目专属内容迁移

如果根级文件中出现项目专属内容，应按以下原则处理：

- 不自动写入项目目录；
- 在报告中列出建议迁移内容和建议目标文件；
- 项目内部已有记录时，可直接删除根级副本；
- 无法确认归属时，保留原文并标记待确认。

本轮只负责根级规范整理，不迁移或修改 `workspace/**`。

---

## 9. 新项目接入

新项目接入仓库时：

1. 在 `workspace/` 下创建独立目录；
2. 添加项目 `AGENTS.md` 和 `README.md`；
3. 添加项目 `docs/`，包括架构、任务和变更日志；
4. 确认项目内部规则不违反根级规则；
5. 将项目专属 ADR 放入项目 `docs/decisions/`。

---

End.
