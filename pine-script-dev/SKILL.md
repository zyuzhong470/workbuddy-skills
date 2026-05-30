---
name: pine-script-dev
version: "1.0.0"
agent_created: true
trigger_words:
  - pine script
  - pine代码
  - tradingview指标
  - TV代码
  - 写指标
  - trading view
description: |
  Pine Script v6 标准开发技能。基于 FatTail Radar v0.1 开发经验，
  包含 v6 陷阱规避清单、五层代码结构、百分位归一化模式、
  三套无 bug 模板、收藏指标分类体系。
  触发词：写Pine Script、TV指标、TradingView代码、Pine v6
allowed_tools:
  - Read
  - Write
  - Edit
  - Bash
  - Glob
  - Grep
---

# Pine Script v6 开发技能

## 核心原则

1. **永远是 v6** — `//@version=6`，不要写 v5
2. **零 bug 目标** — 写完直接可编译运行，不依赖返工
3. **百分位优先** — 参数百分位化，跨品种通用
4. **五层结构** — 声明→输入→计算→信号→输出

## v6 陷阱规避清单（每次写代码前检查）

| # | 陷阱 | 规避方法 |
|---|------|----------|
| 1 | 版本号 | 必须写 `//@version=6` |
| 2 | 多行三元 | 所有 `? :` 单行写，多条件用 `if/else if` |
| 3 | color na | `color x = color.new(color.gray, 100)`，不要 `= na` |
| 4 | indicator timeframe | 有 table/label/alert 时，indicator() 不加 timeframe 参数 |
| 5 | if 块赋值 | if/else 内用 `:=`，不要用 `=` |
| 6 | 变量声明 | 所有变量首次出现时赋值，if 内只改值不声明 |

## 五层代码结构

```
声明层  ：//@version=6, indicator/strategy()
输入层  ：input.int/float/source/bool → 用 group 分组
计算层  ：ta.ema/sma/rsi/atr + percentile() 归一化
信号层  ：条件判断 + 冷却期 + 状态分类
输出层  ：plot/plotshape/bgcolor/table + alertcondition
```

## 百分位归一化工具函数

```pine
percentile(float x, simple int period) =>
    float lo = ta.lowest(x, period)
    float hi = ta.highest(x, period)
    float rng = hi - lo
    rng > 0 ? (x - lo) / rng * 100.0 : 50.0
```

## 收藏指标分类体系

| 类别 | 数量 | 典型指标 | 核心函数 |
|------|------|----------|----------|
| CVD/订单流 | 14 | CVD Divergence, Order Flow | 自定义 volume delta |
| 趋势类 | 7 | EMA, MACD, ADX | ta.ema(), ta.macd() |
| 形态类 | 4 | Auto Patterns, Fibonacci | ta.pivot(), 自定义 |
| 策略类 | 2 | ATR Stop, CVD Strategy | strategy.entry() |

## 需求模板（用户填写）

```
版本：v6 | 类型：indicator/strategy | overlay：true/false
side effects：有/无 table/label | 输出路径：D:\down\trading-view\
品种：BTC/ETH/通用 | 时框：1H/4H/通用
核心计算：_____ | 输出信号：_____
参考代码：_____ | 约束：_____
```

## 模板文件位置

- 三套标准模板：`D:\down\trading-view\Pine_v6_标准模板.pine`
  - 模板 A：副图指标（overlay=false）
  - 模板 B：主图指标（overlay=true）
  - 模板 C：策略型（strategy）
- 需求模板：`D:\down\trading-view\Pine_任务需求模板.md`
