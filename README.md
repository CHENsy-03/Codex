---

## 11. 工作区原则

本工作区只维护：

- AI 开发规范
- 多项目协作
- 架构文档

具体业务规则应放在各项目内部。

工作区不直接存放业务代码。

---\n# Codex Workspace — AI 软件研发中心

> 这不是一个普通项目目录，这是一个 **AI 开发工作台**。
>
> 所有项目共享：AGENTS 规范、架构设计、开发规则、AI 工作流、Prompt 模板。

---

## 1. 工作区介绍

E:\AI_Projects\Codex\ 是你所有项目的根目录。

它不是一个单体仓库，而是一个 **多项目共享工作区**。

| 特性 | 说明 |
|---|---|
| 多项目 | 9 个在研项目统一管理 |
| 统一规范 | AGENTS.md 约束所有项目 |
| 统一架构 | Python + Go 双语言 |
| AI 协作 | GPT / Codex / DeepSeek 分工明确 |
| 文档集中 | docs/ 存放所有共享文档 |
| 输出隔离 | output/ 存放所有 AI 生成物 |

---

## 2. 目录说明

`
Codex/
├── AGENTS.md              项目最高原则（所有 AI 必须遵守）
├── .agents/                AI 模板（prompts / review / workflow）
├── .git/
│
├── docs/                   共享文档
│   ├── SYSTEM_ARCHITECTURE.md   系统架构
│   ├── DEVELOPMENT_RULES.md     开发规范
│   ├── AI_WORKFLOW.md           AI 协作工作流
│   ├── TASK.md                  当前任务
│   ├── CHANGELOG.md             变更日志
│   └── decisions/               架构决策记录（ADR）
│
├── workspace/              在研项目（9 个）
│   ├── go-spider/              Go 爬虫
│   ├── chaincode-drone/        无人机区块链
│   ├── exam-system/            考试系统（Python+Go）
│   ├── crawler/                采集平台
│   ├── drone-survey-server/    无人机勘测服务器
│   ├── gps-simulator/          GPS 定位模拟
│   ├── frontend-design/        前端网页设计
│   ├── agreements/             投资协议制作
│   └── diagram-design/         思维导图 / 流程图
│
├── archive/                归档项目
│   ├── error-analysis/
│   ├── doc-modifications/
│   └── backups/
│
└── output/                 AI 生成物
    ├── reports/      设计报告 / 架构报告 / Review 报告
    ├── diagrams/     Mermaid / PlantUML / 流程图 / ER 图
    ├── sql/          迁移 SQL / 初始化 SQL
    ├── prompts/      GPT / Codex / DeepSeek 专用 Prompt
    └── temp/         临时输出
`

---

## 3. AI 工作流程

详见 [docs/AI_WORKFLOW.md](docs/AI_WORKFLOW.md)

快速概览：

`
用户需求 → GPT(需求分析) → Codex(实现) → DeepSeek(复杂问题) → GPT(Review) → 完成
`

| 步骤 | 负责 AI | 产出 |
|---|---|---|
| 需求分析 | GPT | 需求文档 / TASK.md |
| 架构设计 | GPT | ADR / 设计文档 |
| 代码实现 | Codex + DeepSeek | workspace/ 代码 |
| 本地测试 | Codex | pytest / go test |
| Code Review | GPT | Review 意见 |
| 最终验收 | GPT | 验收确认 |

---

## 4. 如何启动 Codex

Codex 负责代码实现和文件操作。

`
适用的场景：
  - 编写代码
  - 运行测试
  - 文件操作
  - Git 操作（status / diff / log）
`

`
不适用的场景：
  - 架构决策
  - 需求分析
  - 终审验收
`

启动方式：直接在终端调用或通过 IDE 集成。

---

## 5. 如何启动 DeepSeek

DeepSeek 负责复杂推理和问题排查。

`
适用的场景：
  - 算法设计
  - 复杂 Bug 分析
  - 性能优化方案
  - 架构合理性评估
`

`
不适用的场景：
  - 执行命令
  - 文件操作
  - Git 操作
`

---

## 6. 如何创建新项目

`ash
# 1. 在 workspace/ 下创建项目目录
mkdir workspace/my-project

# 2. 添加项目级 AGENTS.md（引用根级规范）
cp .agents/templates/project-AGENTS.md workspace/my-project/AGENTS.md

# 3. 创建标准目录结构
mkdir -p workspace/my-project/{docs,tests,client,server,configs,scripts}

# 4. 更新 README.md 在研项目列表
`

建议所有项目统一结构：

`
project/
├── AGENTS.md         项目级原则
├── docs/             项目文档
├── tests/            测试
├── client/           客户端
├── server/           服务端
├── configs/          配置
└── scripts/          工具脚本
`

---

## 7. Git 规范

| 操作 | 允许 | 禁止 |
|---|---|---|
| git status | ✅ | — |
| git diff | ✅ | — |
| git log | ✅ | — |
| git add / commit | ✅（开发者确认） | — |
| git push | — | ❌ 必须开发者手动 |
| git reset --hard | — | ❌ 禁止 |
| git clean -fd | — | ❌ 禁止 |
| 强制覆盖 | — | ❌ 禁止 |

所有提交必须由开发者确认。

---

## 8. 文档说明

| 文档 | 用途 | 如何更新 |
|---|---|---|
| AGENTS.md | 项目最高原则 | 架构变更时 |
| docs/SYSTEM_ARCHITECTURE.md | 系统架构 | 架构变更时 |
| docs/DEVELOPMENT_RULES.md | 开发规范 | 规范变更时 |
| docs/AI_WORKFLOW.md | AI 协作流程 | 流程变更时 |
| docs/TASK.md | 当前任务 | 每次任务 |
| docs/CHANGELOG.md | 变更日志 | 每次修改 |
| docs/decisions/ADR-*.md | 架构决策 | 每次决策 |
| README.md | 工作区入口 | 目录变化时 |

---

## 9. 开发流程

`
① 需求
   ↓ GPT 输出 TASK.md
② 设计
   ↓ GPT 输出 ADR（如有必要）
③ 实现
   ↓ Codex 按 AGENTS.md 原则实现
④ 测试
   ↓ Codex 运行 pytest / go test
⑤ Review
   ↓ GPT 输出 Review 意见
⑥ 修复
   ↓ Codex 按 Review 修改
⑦ 提交
   ↓ 开发者确认后 commit
⑧ 更新 CHANGELOG
`

---

## 10. 更新记录

| 日期 | 变更 |
|---|---|
| 2026-07-26 | 目录结构重组：workspace / archive / output / .agents |
| 2026-07-26 | 新增文档：AI_WORKFLOW.md / CHANGELOG.md / ADR |
| 2026-07-26 | 新增 README 完整版本 |

---

*最后更新：2026-07-26*
