# Pine Script 任务需求模板
# 用法：下次需要写 Pine Script 代码时，按这个模板提需求，可以避免返工

---

## 模板（复制并填写）

```
【Pine Script 开发需求】

版本：v6（必填，默认 v6）
类型：□ indicator(overlay=true)  □ indicator(overlay=false)  □ strategy
输出路径：D:\down\trading-view\{{filename}}.pine

是否有 side effects（table/label/alertcondition）：□ 是  □ 否

输入参数要求：
- 品种：{{BTCUSDT / ETHUSDT / 通用}}
- 时间框架：{{1H / 4H / 通用}}
- 核心计算：{{描述你要算什么}}
- 输出信号：{{描述你要看什么}}

参考代码/模板：
- 基于：{{已有代码路径 或 "从零开始"}}

已知约束：
- {{如：百分位化、不写死参数、无 OI 数据等}}

质量要求：
- ☑ Pine v6 语法
- ☑ 无多行三元表达式（用 if/else if）
- ☑ color 变量不赋值 na
- ☑ indicator() 不带 timeframe 参数（如果有 table/label）
- ☑ 直接可编译运行
```

---

## 今天的问题复盘

### 用户实际怎么提的：
> "写吧" → "什么问题修复代码" → "什么问题修复代码" → "什么问题修复代码"

### 问题出在哪：
1. 没有指定 v6（我默认写了 v5）
2. 没有说明有 side effects（table），我加了 timeframe 参数
3. 没有要求"零 bug 直接可运行"，我以为写完可以改
4. 3 轮返工 = 约 15 分钟浪费

### 用模板后会怎样：
> "写吧" 变成：
> 版本 v6，indicator overlay=false，有 table，输出到 D:\down\trading-view\
> → 一次写对，0 轮返工

---

## 建议的工作流程

```
用户提需求（用模板）→ 小爪写代码 → TradingView 编译
       ↑                                    │
       └── 有 bug？截图 + 错误信息 ←─────────┘
                        │
                   小爪修复（1轮搞定）
```

核心原则：**需求越具体，返工越少。**
