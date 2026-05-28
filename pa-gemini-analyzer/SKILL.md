---
name: pa-gemini-analyzer
description: PA Agent + Gemini 交易分析助手。一键获取加密货币K线数据，通过Google Gemini API进行Al Brooks价格行为市场结构分析。支持BTC/ETH/SOL等品种，自动计算EMA20/ATR14/K线特征。
agent_created: true
license: MIT
version: 1.0.0
tags: [trading, price-action, gemini, crypto, technical-analysis, kline]
---

# PA Gemini 交易分析助手

> 一键获取加密货币K线数据，通过 Google Gemini 进行 Al Brooks 价格行为分析。

---

## 功能

1. **获取K线数据** — 用 yfinance 拉取指定品种的日线/小时线数据
2. **计算技术指标** — EMA20、ATR14、K线几何特征（实体比、影线、内包/外包等）
3. **PA 市场结构分析** — 通过 Gemini API 执行两阶段分析（诊断→决策）
4. **输出结构化结果** — 周期位置、方向偏好、关键信号、交易建议

---

## 前置条件

- Python 3.11+
- 安装依赖：`pip install yfinance pandas openai`
- 环境变量 `GEMINI_API_KEY` 已设置（或硬编码在脚本中）
- PA Agent 项目代码在 `D:\down\PA_Agent5.27更新\PA_Agent\`

---

## 使用方法

### 方式一：命令行直接分析

```bash
python analyze_crypto.py BTC-USD
```

### 方式二：Python 代码调用

```python
from pa_gemini_analyzer import analyze_symbol

result = analyze_symbol("BTC-USD", period="60d", bars=30)
print(result["diagnosis"])
print(result["decision"])
```

### 方式三：集成到 PA Agent

使用 `run_gemini.py` 启动完整桌面应用：

```bash
set GEMINI_API_KEY=你的key
python run_gemini.py
```

---

## 分析流程

```
获取K线 → 计算EMA20/ATR14/特征 → 组装Prompt → Gemini API → 解析结果
```

### K线特征计算

| 特征 | 说明 |
|------|------|
| bar_type | trend_bull/trend_bear/doji/inside/outside_bull/outside_bear/flat |
| body_ratio | 实体/全长比 |
| range_atr | Range/ATR14 比值 |
| ema_relation | above/below/touch |
| inside_sequence | 内包序列 ii/iii |

### Prompt 结构

```
[system] Al Brooks 价格行为分析师角色设定
[user] K线数据表 + 几何特征表 + 市场诊断请求
```

### 输出格式

```
【阶段一：市场诊断】
周期位置：xxx
方向偏好：xxx
关键信号：xxx

【阶段二：交易建议】
入场条件：...
止损位置：...
止盈目标：...
仓位：...
```

---

## 配置

| 配置项 | 默认值 | 说明 |
|--------|--------|------|
| model | gemini-2.5-flash | Gemini 模型 |
| base_url | https://generativelanguage.googleapis.com/v1beta/openai/ | OpenAI 兼容端点 |
| context_window | 1,000,000 | 上下文窗口 |
| max_tokens | 65,536 | 输出上限 |

---

## 适用品种

- **加密货币**：BTC-USD, ETH-USD, SOL-USD 等
- **股票**：AAPL, TSLA 等（yfinance 支持的任何代码）
- **外汇**：EURUSD=X 等

---

## 技术说明

- **数据源**：yfinance（Yahoo Finance 数据）
- **AI 后端**：Google Gemini 2.5 Flash（通过 OpenAI 兼容 API）
- **分析框架**：Al Brooks 价格行为（Price Action）
- **客户端**：复用 PA Agent 的 `DeepSeekClient`（OpenAI 兼容）
