---
name: range-scalper-vp
description: 震荡区间高抛低吸量化策略 — 基于 Pivot 聚类 + 多维评分的自动回测、优化与 Pine Script 导出。支持 Bybit/本地 CSV 数据源。当用户需要回测震荡策略、优化参数、导出 TradingView 策略时触发。
agent_created: true
license: MIT
version: 1.0.0
tags: [trading, backtest, crypto, range-scalping, pivot-clustering, pine-script, bybit, quantitative]
---

# Range Scalper VP — 震荡区间高抛低吸策略

> 你是震荡区间 Scalping 策略的执行引擎。你可以加载数据、运行回测、优化参数、导出 Pine Script。

---

## 策略概述

**核心思想：**
1. 用 Pivot 聚类算法识别当前价格附近的支撑/阻力区间（5维评分：Touch / Reaction / Recency / Compact / Extreme）
2. 在区间上沿挂空单（高抛），区间下沿挂多单（低吸）
3. 止盈挂在区间对侧边界，止损等距反向（1:1 盈亏比）
4. 多重过滤器确保只在震荡行情中交易（波动率 / 区间宽度 / EMA趋势 / RSI）

**适用品种：** BTC、ETH、SOL 等永续合约，5分钟 K 线
**技术栈：** Python + NumPy + Pandas + Numba（可选加速）

---

## 快速开始

### 1. 运行回测

当用户说"回测"、"跑回测"、"回测 BTC" 等，按以下步骤执行：

```bash
cd ~/.workbuddy/skills/range-scalper-vp/scripts
```

**数据获取：** 优先用 Bybit API（如果用户提供了 API Key），否则引导用户提供 CSV 数据。

#### 方式 A：从 Bybit 下载数据并回测

```bash
python run_backtest.py \
  --symbol BTCUSDT \
  --interval 5 \
  --days 90 \
  --output ../results/btc_3m_result.csv
```

#### 方式 B：从本地 CSV 回测

```bash
python run_backtest.py \
  --csv /path/to/data.csv \
  --output ../results/backtest_result.csv
```

### 2. 查看已优化参数

策略内置 13 个可优化参数。默认参数运行回测时使用预设值：

| 参数 | 默认值 | 范围 | 说明 |
|------|--------|------|------|
| SR_MERGE_ATR | 0.48 | 0.2~2.0 | Pivot 聚类合并距离（ATR倍数） |
| SR_MIN_SCORE | 70.0 | 40~120 | 聚类最低评分阈值 |
| MIN_WIDTH_ATR | 1.0 | 0.5~3.0 | 区间最小宽度（ATR倍数） |
| OFFSET_PCT | 0.15 | 0.0~0.3 | 限价偏移比例 |
| LIMIT_EXPIRY | 20 | 3~30 | 限价单超时根数 |
| BREAKOUT_ATR | 0.3 | 0.0~1.5 | 突破判定ATR倍数 |
| atr_ratio_low | 0.3 | 0.2~0.8 | 波动率过滤下限 |
| atr_ratio_high | 1.5 | 1.5~4.0 | 波动率过滤上限 |

### 3. 输出结果解读

回测完成后，输出以下内容给用户：

```
【回测摘要】
- 回测区间：YYYY-MM-DD ~ YYYY-MM-DD
- 总交易数：X 笔
- 胜率：XX%
- 盈亏比：X.XX
- 总收益：XX%
- 最大回撤：XX%

【方向统计】
- 做多：胜率XX%，收益XX%
- 做空：胜率XX%，收益XX%
```

同时将结果 CSV 保存到用户指定路径。

---

## 完整参数说明

### Pivot 聚类参数
| 参数 | 默认 | 说明 |
|------|------|------|
| SR_LOOKBACK | 500 | Pivot 回看窗口（固定） |
| SR_MERGE_ATR | 0.48 | 聚类合并距离 |
| SR_MIN_SCORE | 70.0 | 最低聚类评分（5维总分≥此值才有效） |
| MIN_WIDTH_ATR | 1.0 | 区间最小宽度 |

### 交易参数
| 参数 | 默认 | 说明 |
|------|------|------|
| OFFSET_PCT | 0.15 | 限价偏移（%区间宽度） |
| LIMIT_EXPIRY | 20 | 限价单超时（根数） |
| BREAKOUT_ATR | 0.3 | 突破判定ATR倍 |

### 过滤器参数（开关控制）
| 过滤器 | 默认 | 参数 |
|--------|------|------|
| 波动率过滤 | ON | atr_ratio_low=0.3, atr_ratio_high=1.5 |
| 区间宽度过滤 | ON | MIN_ATR_MULT=1.0 |
| EMA趋势过滤 | ON | slope_max=0.05, slope_window=20 |
| RSI中性过滤 | ON | rsi_neutral_lo=35, rsi_neutral_hi=65 |

---

## 技能维护

### 修改默认参数
编辑 `scripts/range_scalper/range_scalper_opt.py` 中的默认值。

### 参考文档
- `references/DESIGN.md` — 完整设计文档
- `references/STRATEGY_PSEUDOCODE.md` — 策略伪代码与优化思路

---

## 安全声明

- 本技能**仅做回测分析**，不执行实盘交易
- Bybit API Key 仅用于下载历史K线数据（只读权限）
- 不会修改用户的 API 权限或账户设置
- 所有计算在本地完成，不上传数据
