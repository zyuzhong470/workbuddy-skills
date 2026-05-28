---
name: gsd-workflows
description: GSD (Get Shit Done) 工作流模板库 — 包含 workflows、templates、contexts 等开发流程模板，用于规范化开发过程。触发词：GSD 工作流、开发模板、计划模板、摘要模板。
---

# GSD Workflows — 工作流模板库

来自 [Get Shit Done](https://github.com/mediocre/gsd) 开源项目的工作流、模板和上下文定义。

## 内容

### Workflows
开发工作流程定义，涵盖从项目初始化到发布的完整流程。

### Templates
文档模板，包括：
- 计划文档模板 (PLAN.md)
- 摘要文档模板 (SUMMARY.md)
- 状态文档模板 (STATE.md)
- 路线图模板 (ROADMAP.md)

### Contexts
执行上下文定义，为不同阶段提供环境配置和参数。

## 使用方式

1. 参考 workflows/ 中的流程定义来设计自己的开发流程
2. 使用 templates/ 中的模板来规范化项目文档
3. 参考 contexts/ 中的定义来理解不同阶段的参数需求

## 注意事项

- 模板中的变量占位符（如 `{phase}`, `{plan}`）需要替换为实际值
- 部分模板引用 GSD CLI 工具，在 WorkBuddy 中需要适配
- 原始路径 `@~/.claude/get-shit-done/` 需要映射到当前技能目录

## 来源

- 项目: Get Shit Done (GSD)
- 许可: 见原项目 LICENSE 文件
