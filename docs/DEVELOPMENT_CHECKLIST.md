# DEVELOPMENT_CHECKLIST.md

> 本文件用于提醒开发者和 AI 在开发过程中不要遗漏关键步骤。
>
> 每完成一个功能，都应按以下顺序检查。

---

## \u2460 开发前

\u2610 阅读 AGENTS.md

\u2610 阅读 SYSTEM_ARCHITECTURE.md

\u2610 阅读 DEVELOPMENT_RULES.md

\u2610 阅读 TASK.md

\u2610 明确修改范围

\u2610 确认影响模块

\u2610 确认测试方式

---

## \u2461 开发中

\u2610 仅修改允许修改的文件

\u2610 不扩大修改范围

\u2610 不修改无关模块

\u2610 不破坏架构

\u2610 保持 Python / Go 职责边界

\u2610 不重复实现已有功能

\u2610 错误全部处理

\u2610 日志完整

\u2610 配置不硬编码

---

## \u2462 开发完成

\u2610 Python 测试通过

\u2610 Go 测试通过

\u2610 新功能测试完成

\u2610 边界测试完成

\u2610 异常测试完成

\u2610 git diff 已检查

\u2610 无无关修改

\u2610 无敏感信息

---



## \u2463 阻塞检查

\u2610 \u51fa\u73b0\u963b\u585e\u662f\u5426\u7acb\u5373\u505c\u6b62\uff1f

\u2610 \u662f\u5426\u8f93\u51fa\uff1a

- \u9519\u8bef\u65e5\u5fd7
- \u4fee\u6539\u6587\u4ef6
- \u5df2\u5b8c\u6210\u5185\u5bb9
- \u672a\u5b8c\u6210\u5185\u5bb9
- \u5f53\u524d\u963b\u585e\u70b9

\u2610 \u662f\u5426\u7b49\u5f85 GPT \u65b0\u65b9\u6848\uff1f

---

## \u2463 GPT Review

\u2610 GPT 已完成 Code Review

\u2610 Review 问题已修复

\u2610 剩余风险已说明

---

## \u2464 文档

\u2610 TASK 更新

\u2610 CHANGELOG 更新

\u2610 判断是否需要新增 ADR

\u2610 README 是否需要同步

---

## \u2465 Git

\u2610 git status

\u2610 git diff

\u2610 git add

\u2610 git commit

\u2610 不执行 git push（除非开发者确认）

---

## \u2466 发布

\u2610 版本号确认

\u2610 输出目录已整理

\u2610 临时文件已清理

\u2610 可以交付
