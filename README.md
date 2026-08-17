# Codex Workspace

> 这是一个多项目软件研发工作区，不是单一业务系统。
> 根目录维护仓库级规范、文档和协作入口；具体项目代码与项目文档放在 `workspace/<project>` 中。

---

## 1. 仓库用途

本仓库用于统一管理多个独立项目，并提供一套跨项目复用的人工和 AI 协作规则。

根级内容负责回答：

- 项目如何组织；
- 根级规范与项目内部文档如何分工；
- AI 和开发者开始任务前必须遵守哪些规则；
- 文档、变更记录和架构决策如何维护。

项目业务规则、架构、任务进度和测试结果应放在对应项目的 `AGENTS.md` 或 `docs/` 中，不应写入根级规范。

---

## 2. 目录职责

```text
Codex/
├── AGENTS.md              仓库级 AI/开发规则
├── README.md              仓库入口文档
├── .agents/               AI 工作目录、模板和流程
├── docs/                  仓库级规范文档
│   ├── DEVELOPMENT_RULES.md      跨项目开发规则
│   ├── DEVELOPMENT_CHECKLIST.md  开发检查清单
│   ├── AI_WORKFLOW.md            AI 协作工作流
│   ├── SYSTEM_ARCHITECTURE.md    仓库级组织架构
│   ├── TASK.md                   通用任务模板与字段约定
│   ├── CHANGELOG.md              仓库级治理变更日志
│   └── decisions/                架构决策记录
├── workspace/             各独立项目目录
│   └── <project>/
├── archive/               已归档项目
└── output/                生成报告和交付物
```

根级目录不应存放具体项目的业务代码。

---

## 3. 项目隔离原则

每个项目使用独立目录：

```text
workspace/<project>/
```

项目应自行维护：

- `AGENTS.md`：项目级规则；
- `docs/`：项目架构、任务、开发规则、变更记录和 ADR；
- 源码、测试、配置和部署文件。

根级规范适用于所有项目；项目内部规则可以更具体，但不得与根级的安全、Git、文档同步和最小修改原则冲突。

---

## 4. 新项目基本结构

```text
workspace/<project>/
├── AGENTS.md
├── README.md
├── docs/
│   ├── SYSTEM_ARCHITECTURE.md
│   ├── DEVELOPMENT_RULES.md
│   ├── TASK.md
│   └── CHANGELOG.md
├── tests/
├── configs/
├── scripts/
└── <源码目录>
```

项目可以根据技术栈调整结构，但应保持文档、测试和配置目录清晰。

---

## 5. 根级规范与项目文档分工

| 内容 | 存放位置 |
|---|---|
| 多项目通用 AI/开发规则 | 根级 `AGENTS.md`、`docs/DEVELOPMENT_RULES.md` |
| 仓库目录和项目隔离原则 | 根级 `docs/SYSTEM_ARCHITECTURE.md` |
| 通用任务模板和状态定义 | 根级 `docs/TASK.md` |
| AI/Codex 协作流程 | 根级 `docs/AI_WORKFLOW.md` |
| 项目内部架构、任务进度、测试结果 | `workspace/<project>/docs/` |
| 项目专属 ADR | `workspace/<project>/docs/decisions/` |

---

## 6. 通用工作方式

```text
用户需求
    ↓
明确任务范围
    ↓
阅读适用的 AGENTS.md 和项目文档
    ↓
确认 Git 现场与修改边界
    ↓
实施最小修改
    ↓
运行相关测试和检查
    ↓
输出真实结果与剩余风险
    ↓
由开发者决定提交和发布
```

开始任何修改前必须：

- 阅读仓库根目录和当前项目的 `AGENTS.md`；
- 检查当前分支、HEAD、暂存区、工作区和未跟踪文件；
- 确认允许修改的文件范围；
- 不覆盖用户预存修改；
- 不执行未经授权的 Git 写操作。

---

## 7. Git 与任务基本流程

- 每个任务建议使用独立分支，分支名应表达任务类型和内容。
- 修改前记录 Git 基线，修改后核对差异。
- 暂存和提交由开发者明确授权后执行。
- AI 默认不得 push、创建 PR 或修改历史。
- 所有测试结果必须来自真实执行，不得预填或虚构。

---

## 8. 文档入口

- [AGENTS.md](./AGENTS.md)
- [docs/DEVELOPMENT_RULES.md](./docs/DEVELOPMENT_RULES.md)
- [docs/DEVELOPMENT_CHECKLIST.md](./docs/DEVELOPMENT_CHECKLIST.md)
- [docs/AI_WORKFLOW.md](./docs/AI_WORKFLOW.md)
- [docs/SYSTEM_ARCHITECTURE.md](./docs/SYSTEM_ARCHITECTURE.md)
- [docs/TASK.md](./docs/TASK.md)
- [docs/CHANGELOG.md](./docs/CHANGELOG.md)
- [docs/decisions/ADR_PROCESS.md](./docs/decisions/ADR_PROCESS.md)

---

## 9. 仓库级变更日志

根级 `docs/CHANGELOG.md` 只记录仓库级规范、目录和治理变化。具体项目功能变更应记录在项目内部变更日志中。

---

*最后更新：2026-08-11*
