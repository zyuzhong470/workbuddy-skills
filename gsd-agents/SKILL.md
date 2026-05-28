---
name: gsd-agents
description: GSD (Get Shit Done) Agent 角色库 — 33个专业 AI agent 角色定义，涵盖规划、执行、调试、审查、文档、研究等。当需要按 GSD 方法论组织开发流程、使用专业 agent 分工协作时触发。触发词：GSD agent、项目规划、阶段执行、代码审查agent、开发流程agent。
---

# GSD Agents — AI Agent 角色库

来自 [Get Shit Done](https://github.com/mediocre/gsd) 开源项目的 33 个专业 agent 角色定义。

## 角色分类

### 规划与执行
| Agent | 职责 |
|-------|------|
| gsd-planner | 创建可执行的阶段计划，任务分解+依赖分析 |
| gsd-executor | 执行 PLAN.md，原子提交+偏差处理+检查点 |
| gsd-verifier | 验证工作完成度，确认任务达标 |
| gsd-plan-checker | 检查计划质量，发现遗漏和冲突 |

### 代码质量
| Agent | 职责 |
|-------|------|
| gsd-code-reviewer | 代码审查，发现安全和性能问题 |
| gsd-code-fixer | 自动修复代码问题 |
| gsd-security-auditor | 安全审计 |
| gsd-integration-checker | 集成测试检查 |

### 调试
| Agent | 职责 |
|-------|------|
| gsd-debugger | 系统化调试 |
| gsd-debug-session-manager | 调试会话管理 |
| gsd-forensics | 事后分析 |

### 文档
| Agent | 职责 |
|-------|------|
| gsd-doc-writer | 编写文档 |
| gsd-doc-synthesizer | 文档综合 |
| gsd-doc-classifier | 文档分类 |
| gsd-doc-verifier | 文档验证 |

### 研究
| Agent | 职责 |
|-------|------|
| gsd-ai-researcher | AI 技术研究 |
| gsd-domain-researcher | 领域研究 |
| gsd-advisor-researcher | 顾问研究 |
| gsd-research-synthesizer | 研究综合 |
| gsd-project-researcher | 项目研究 |
| gsd-phase-researcher | 阶段研究 |

### 项目管理
| Agent | 职责 |
|-------|------|
| gsd-roadmapper | 路线图规划 |
| gsd-assumptions-analyzer | 假设分析 |
| gsd-framework-selector | 框架选择 |
| gsd-pattern-mapper | 模式映射 |

### 评估与审计
| Agent | 职责 |
|-------|------|
| gsd-eval-planner | 评估计划 |
| gsd-eval-auditor | 评估审计 |
| gsd-nyquist-auditor | 奈奎斯特审计 |

### UI
| Agent | 职责 |
|-------|------|
| gsd-ui-researcher | UI 研究 |
| gsd-ui-checker | UI 检查 |
| gsd-ui-auditor | UI 审计 |

### 其他
| Agent | 职责 |
|-------|------|
| gsd-intel-updater | 情报更新 |
| gsd-user-profiler | 用户画像 |
| gsd-codebase-mapper | 代码库映射 |

## 使用方式

这些 agent 角色定义可作为 prompt 模板，用于：
1. **WorkBuddy Agent 子任务** — 启动 agent 时加载对应角色定义
2. **开发流程参考** — 了解专业分工的最佳实践
3. **自定义技能基础** — 基于这些角色创建适配本平台的技能

每个 agent 文件在 `references/` 目录下，格式为 Markdown + YAML frontmatter，包含完整的角色描述、工具需求、执行流程和约束条件。

## 注意事项

- GSD 原生依赖 `gsd-sdk` CLI 和 `.planning/` 目录结构
- Agent 中的 `@~/.claude/get-shit-done/references/` 路径指向 Claude Code 专用路径
- 在 WorkBuddy 中使用时，需要适配工具调用方式和文件路径
- Agent 中的 `gsd-sdk query` 命令需要 GSD CLI 已安装

## 来源

- 项目: Get Shit Done (GSD)
- 作者: GSD 团队
- 许可: 见原项目 LICENSE 文件
