---
name: gsd-commands
description: GSD (Get Shit Done) 命令库 — 67个开发工作流命令定义，涵盖项目管理、阶段规划、代码执行、审查验证等完整开发流程。触发词：GSD 命令、开发流程、阶段规划、milestone管理、phase执行。
---

# GSD Commands — 开发工作流命令库

来自 [Get Shit Done](https://github.com/mediocre/gsd) 开源项目的 67 个命令定义。

## 命令分类

### 项目初始化
| 命令 | 说明 |
|------|------|
| new-project | 创建新项目 |
| config | 配置管理 |
| settings | 设置 |
| import | 导入项目 |
| workspace | 工作区管理 |
| workstreams | 工作流管理 |

### 里程碑管理
| 命令 | 说明 |
|------|------|
| new-milestone | 创建里程碑 |
| complete-milestone | 完成里程碑 |
| audit-milestone | 审计里程碑 |
| milestone-summary | 里程碑摘要 |

### 阶段规划
| 命令 | 说明 |
|------|------|
| plan-phase | 规划阶段 |
| spec-phase | 规格阶段 |
| execute-phase | 执行阶段 |
| validate-phase | 验证阶段 |
| discuss-phase | 讨论阶段 |
| mvp-phase | MVP 阶段 |
| ui-phase | UI 阶段 |
| ai-integration-phase | AI 集成阶段 |
| secure-phase | 安全阶段 |
| ultraplan-phase | 超级规划阶段 |

### 工作流控制
| 命令 | 说明 |
|------|------|
| fast | 快速模式 |
| quick | 快速执行 |
| autonomous | 自主模式 |
| spike | 技术探针 |
| sketch | 草图 |
| pause-work | 暂停工作 |
| resume-work | 恢复工作 |

### 代码质量
| 命令 | 说明 |
|------|------|
| code-review | 代码审查 |
| add-tests | 添加测试 |
| audit-fix | 审计修复 |
| audit-uat | UAT 审计 |

### 调试
| 命令 | 说明 |
|------|------|
| debug | 调试 |
| forensics | 事后分析 |
| undo | 撤销 |

### 文档
| 命令 | 说明 |
|------|------|
| docs-update | 更新文档 |
| ingest-docs | 导入文档 |
| extract-learnings | 提取经验 |

### 进度与报告
| 命令 | 说明 |
|------|------|
| progress | 进度报告 |
| health | 健康检查 |
| stats | 统计信息 |
| surface | 表面分析 |

### 审查与评估
| 命令 | 说明 |
|------|------|
| review | 代码审查 |
| eval-review | 评估审查 |
| ui-review | UI 审查 |
| review-backlog | 待办审查 |
| plan-review-convergence | 计划审查收敛 |

### 发布
| 命令 | 说明 |
|------|------|
| ship | 发布 |
| pr-branch | PR 分支 |

### 其他
| 命令 | 说明 |
|------|------|
| explore | 探索代码库 |
| map-codebase | 映射代码库 |
| capture | 捕获 |
| cleanup | 清理 |
| graphify | 图形化 |
| thread | 线程管理 |
| inbox | 收件箱 |
| manager | 管理器 |
| help | 帮助 |
| update | 更新 |
| ns-* | 命名空间系列命令 |
| profile-user | 用户画像 |

## 使用方式

每个命令定义在 `references/` 目录下，包含完整的：
- 命令用途和触发条件
- 执行步骤和流程
- 输入输出格式
- 检查点和人工确认环节

这些命令定义可作为开发流程参考，也可用于自定义 WorkBuddy 技能的流程设计。

## 注意事项

- 命令依赖 GSD CLI 工具（`gsd-sdk`）和 `.planning/` 目录结构
- 在 WorkBuddy 中不能直接调用，需要适配
- 命令中的路径和工具引用需要转换

## 来源

- 项目: Get Shit Done (GSD)
- 许可: 见原项目 LICENSE 文件
