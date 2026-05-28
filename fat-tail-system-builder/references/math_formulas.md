# 数学公式详细定义 — 7 Engine Architecture

> **核心规则：禁止重新发明指标。**  
> 所有模块必须使用 Pine Script 原生函数（`ta.sma`, `ta.stdev`, `ta.linreg`, `ta.macd`, `ta.atr` 等）。  
> 数学化的是 Z-score 归一化 + 状态组合 — 不是重写经典指标本身。

## 引擎链架构

```
Regime (环境) → Squeeze (压缩) → Structure (结构) → Momentum (动量) → Fat Tail (肥尾) → Risk (风控) → Exit (退出)
```

每个引擎只做一件事。下游引擎依赖上游引擎的判断结果。

---

## 1. 环境识别模块 (Regime Engine)

**职责：判断当前市场是否适合交易，过滤极端行情和死市。**

```pine
atr_base  = ta.atr(14)
atr_mean  = ta.sma(atr_base, 50)       // 长期波动率均值
atr_ratio = atr_base / atr_mean

is_crisis = atr_ratio > 3.0            // ATR 3x = 极端行情，不交易
is_dead   = atr_ratio < 0.3            // ATR < 0.3x = 死市，不交易

// BB 宽度确认市场活力
basis   = ta.sma(close, 20)
dev     = ta.stdev(close, 20)
bbw     = (basis + 2*dev - (basis - 2*dev)) / basis
bbw_mean = ta.sma(bbw, 200)
market_alive = bbw > bbw_mean * 0.5    // BB宽度不低于历史50%

regime_ok = not is_crisis and not is_dead and market_alive
```

> 这是整个系统的第一道过滤。极端行情不做，死市不做。

---

## 2. 压缩检测模块 (Squeeze Engine)

**职责：识别波动率压缩 — 肥尾的前兆，能量积累阶段。**

布林带宽度 Z-score：

```pine
basis = ta.sma(close, 20)
dev   = ta.stdev(close, 20)
upper = basis + 2 * dev
lower = basis - 2 * dev
bbw   = (upper - lower) / basis

// Z-score 归一化（200根回望）
bbw_sma = ta.sma(bbw, 200)
bbw_std = ta.stdev(bbw, 200)
bbz     = (bbw - bbw_sma) / math.max(bbw_std, 1e-8)
```

压缩触发：`is_squeezed = bbz < bbz_threshold`（默认 -1.0）

> bbz < -1.0 意味着当前 BB 宽度比历史均值低 1 个标准差以上 — **能量正在积累**。

---

## 3. 结构突破模块 (Structure Engine)

**职责：判断价格是否有效突破关键结构，不是假突破。**

```pine
// [1] 偏移避免同根K线未来函数
resistance   = ta.highest(high, lookback)[1]   // lookback=20
support      = ta.lowest(low, lookback)[1]
breakout_up  = close > resistance

// HH/HL 序列确认（最近 N 根 K线）
hh_sequence = true; hl_sequence = true
for i = 1 to min_bars - 1
    if high[i] <= high[i+1]
        hh_sequence := false
    if low[i] <= low[i+1]
        hl_sequence := false

structure_valid = breakout_up and hh_sequence and hl_sequence
```

> **关键**：不仅突破阻力，还要 HH+HL 序列确认趋势结构成立。单一突破 ≠ 有效信号。

---

## 4. 动量加速模块 (Momentum Engine)

**职责：确认趋势正在加速，排除假突破后的回撤。**

```pine
linreg0    = ta.linreg(close, 20, 0)
linreg1    = ta.linreg(close, 20, 1)
slope      = linreg0 - linreg1

// Z-score 归一化（100根回望）
slope_sma  = ta.sma(slope, 100)
slope_std  = ta.stdev(slope, 100)
norm_slope = (slope - slope_sma) / math.max(slope_std, 1e-8)

is_trending     = norm_slope > slope_thresh      // 默认 1.0
acceleration    = norm_slope - norm_slope[1]
is_accelerating = acceleration > 0
```

> 趋势 + 加速双重确认。只有"正在走强且越来越强"才算通过。

---

## 5. 肥尾确认模块 (Fat Tail Engine)

**职责：确认波动进入非线性扩张 — 这是整个系统的终极目标。**

4 个确认条件，至少满足 N 个（默认 2 个）：

```pine
// 条件1: ATR 突然扩大到均值的 N 倍以上
ft_atr_expanding = ta.atr(14) > ta.sma(ta.atr(14), 50) * 1.5

// 条件2: BB 宽度从压缩中释放（bbz 由负转正并持续上升）
ft_bbw_expanding = bbz > bbz[1] and bbz > 0

// 条件3: 成交量突增
ft_vol = volume > ta.sma(volume, 20) * 1.5

// 条件4: 连续 N 根趋势实体 K线（收盘价持续走高）
ft_consec_trend = true
for i = 0 to N-2
    if close[i] <= close[i+1]
        ft_consec_trend := false

// 综合分数
ft_score = ft_atr_expanding + ft_bbw_expanding + ft_vol + ft_consec_trend
fat_tail_confirmed = ft_score >= min_confirm  // 默认 >= 2
```

> 肥尾不是"涨很多"，而是**波动突然进入非线性扩张** — ATR 爆炸 + BB 开口 + 量能 + 趋势K线。

---

## 6. 风险控制模块 (Risk Engine)

**职责：仓位计算、止损止盈、连续亏损暂停。**

```pine
atr_val   = ta.atr(14)

// 开仓时固定止损
stop_loss = close - atr_mult * atr_val          // atr_mult=1.5

// 止盈（可选）
take_profit = close + rr_ratio * atr_mult * atr_val  // rr_ratio=2.0 (0=关闭)
```

### 仓位管理（两种模式）

**模式 A：固定数量（MVP 默认）**
```pine
qty = input.float(0.01, "固定仓位(BTC)")
```

**模式 B：百分比风险（进阶）**
```
PositionSize = (Equity × Risk%) / |Entry - Stop|
```
```pine
riskPct = input.float(1.0, "每笔风险%") / 100
qty    = (strategy.equity * riskPct) / math.abs(close - stop_loss)
```

### 连续亏损暂停
```pine
var int consec_losses = 0
if 持仓平仓 and 本次亏损
    consec_losses += 1
if consec_losses >= max_consec_losses  // 默认 3
    pause 24 根K线
```

---

## 7. 退出模块 (Exit Engine)

**职责：判断何时退出持仓。两套机制并行。**

```pine
// 机制1: MACD 柱线衰减（动量衰竭）
[macdLine, signalLine, macdHist] = ta.macd(close, 12, 26, 9)
exit_macd = macdHist < macdHist[1] and macdHist < 0

// 机制2: 价格回到中轨下方（结构失效）
exit_structure = close < basis   // basis = ta.sma(close, 20)

exit_signal = exit_macd or exit_structure
```

> 两套退出逻辑：MACD 管动量衰竭，中轨管结构失效。任一触发即离场。

---

## 状态机（6 状态，顺序晋级）

```
state 0 (IDLE)      → state 1 (REGIME)    : regime_ok
state 1 (REGIME)    → state 2 (SQUEEZE)   : is_squeezed
state 2 (SQUEEZE)   → state 3 (STRUCTURE) : structure_valid
state 3 (STRUCTURE) → state 4 (MOMENTUM)  : is_trending AND is_accelerating
state 4 (MOMENTUM)  → state 5 (FAT_TAIL)  : fat_tail_confirmed → ENTRY
state 5 (POSITION)  → state 0 (IDLE)      : exit_signal OR stop hit
```

**退化规则（状态防卡死）：**
- state 1: 环境恶化 → 回到 0
- state 2: 压缩释放但未突破 → 回到 0
- state 3: 动量反转 → 回到 0
- state 5: position_size == 0 → 自动回到 0

---

## 参数 Warmup 建议

| 参数 | 建议 warmup |
|------|-------------|
| `sq_bbz_lookback=200` + `sq_bb_len=20` | 最少 220 根 |
| `regime_atr_len=50` | 最少 50 根 |
| `mo_slope_lookback=100` + `mo_lr_len=20` | 最少 120 根 |
| `rk_atr_len=14` | 最少 14 根 |
| **综合建议** | **至少 250 根** |
