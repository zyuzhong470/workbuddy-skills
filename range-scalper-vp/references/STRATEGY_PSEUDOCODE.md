# Range Scalper VP — 完整策略伪代码

> 本文档面向 AI 直接生成完整策略代码。包含策略原理、完整伪代码、推荐参数、优化思路。

---

## 一、策略概述

**策略类型**：震荡区间高抛低吸（Range Mean-Reversion Scalper）

**核心思想**：
1. 用 Pivot 聚类算法识别当前价格附近的支撑/阻力区间
2. 在区间上沿挂空单（高抛），区间下沿挂多单（低吸）
3. 止盈挂在区间对侧边界，止损等距反向（1:1 盈亏比）
4. 多重过滤器确保只在震荡行情中交易

**适用品种**：期货（ES、NQ、CL 等）、加密货币、外汇
**适用周期**：5 分钟 K 线（可调整）

---

## 二、指标预计算

```pseudocode
FUNCTION compute_indicators(df):
    // ATR（真实波幅）
    df.atr = ATR(df, period=14)

    // ATR 比率（当前波动 / 历史平均波动）
    df.atr_ma = ROLLING_MEAN(df.atr, window=50)
    df.atr_ratio = df.atr / df.atr_ma

    // EMA 趋势
    df.ema20 = EMA(df.close, period=20)

    // RSI
    df.rsi = RSI(df.close, period=14)

    RETURN df
```

---

## 三、Pivot 检测（向量化）

```pseudocode
FUNCTION detect_pivots(high, low):
    // Pivot High：当前 high 大于左右各 1 根 K 线
    pivot_high[i] = (high[i] > high[i-1]) AND (high[i] > high[i+1])

    // Pivot Low：当前 low 小于左右各 1 根 K 线
    pivot_low[i] = (low[i] < low[i-1]) AND (low[i] < low[i+1])

    RETURN pivot_high_indices, pivot_low_indices
```

---

## 四、Pivot 评分（5 维）

```pseudocode
FUNCTION score_pivot(pivot_price, pivot_idx, all_pivots_in_cluster, current_bar, lookback):

    // 1. Touch 分（聚类内 Pivot 数量，最多 60 分）
    touch_count = COUNT(all_pivots_in_cluster)
    touch_score = MIN(touch_count * 15.0, 60.0)

    // 2. Reaction 分（Pivot 反应幅度，最多 50 分）
    //    向左看 3 根 K 线的最大反应（高点看跌幅，低点看涨幅）
    reaction = MAX_REACTION(pivot_price, pivot_idx, lookback=3)
    reaction_score = MIN(reaction / ATR * 10.0, 50.0)

    // 3. Recency 分（最近性，指数衰减，最多 40 分）
    bars_ago = current_bar - pivot_idx
    recency_score = 40.0 * EXP(-bars_ago / 200.0)

    // 4. Compact 分（聚类紧凑度，最多 40 分）
    cluster_spread = MAX(cluster_prices) - MIN(cluster_prices)
    compact_score = MAX(0, 40.0 * (1.0 - cluster_spread / ATR))

    // 5. Extreme 分（是否为过去 lookback 内的极值点，最多 40 分）
    is_extreme = (pivot_price == MAX/MIN of past lookback bars)
    extreme_score = 40.0 IF is_extreme ELSE 0.0

    total_score = touch_score + reaction_score + recency_score + compact_score + extreme_score
    RETURN total_score  // 最大 230 分
```

---

## 五、Centroid-Linkage 聚类

```pseudocode
FUNCTION cluster_pivots(pivot_prices, pivot_indices, atr, SR_MERGE_ATR):
    merge_distance = SR_MERGE_ATR * atr
    clusters = []

    FOR each pivot in pivot_prices (sorted by price):
        merged = False
        FOR each existing_cluster in clusters:
            centroid = MEAN(existing_cluster.prices)
            IF ABS(pivot_price - centroid) <= merge_distance:
                existing_cluster.add(pivot)
                merged = True
                BREAK
        IF NOT merged:
            clusters.append(new_cluster(pivot))

    RETURN clusters
```

---

## 六、区间识别（核心）

```pseudocode
FUNCTION find_range(df, i, params):
    // 参数
    SR_LOOKBACK   = params.SR_LOOKBACK    // 500
    SR_MERGE_ATR  = params.SR_MERGE_ATR   // 0.84
    SR_MIN_SCORE  = params.SR_MIN_SCORE   // 68.87
    MIN_WIDTH_ATR = params.MIN_WIDTH_ATR  // 1.54

    atr = df.atr[i]
    close = df.close[i]

    // 1. 取过去 SR_LOOKBACK 根 K 线内的所有 Pivot
    window_start = MAX(0, i - SR_LOOKBACK)
    ph_indices = [j for j in window_start..i-1 if pivot_high[j]]
    pl_indices = [j for j in window_start..i-1 if pivot_low[j]]

    // 2. 聚类
    ph_clusters = cluster_pivots(high[ph_indices], ph_indices, atr, SR_MERGE_ATR)
    pl_clusters = cluster_pivots(low[pl_indices], pl_indices, atr, SR_MERGE_ATR)

    // 3. 对每个聚类评分
    FOR each cluster in ph_clusters + pl_clusters:
        cluster.score = score_pivot(cluster.centroid, cluster.latest_idx,
                                    cluster.pivots, i, SR_LOOKBACK)

    // 4. 筛选：评分 >= SR_MIN_SCORE
    valid_clusters = [c for c in all_clusters if c.score >= SR_MIN_SCORE]

    // 5. 选取阻力（close 上方评分最高且最近的聚类）
    resistance_candidates = [c for c in valid_clusters if c.centroid > close]
    IF resistance_candidates is empty: RETURN None
    resistance = MIN(resistance_candidates, key=distance_to_close)  // 最近的

    // 6. 选取支撑（close 下方评分最高且最近的聚类）
    support_candidates = [c for c in valid_clusters if c.centroid < close]
    IF support_candidates is empty: RETURN None
    support = MIN(support_candidates, key=distance_to_close)

    range_high = resistance.centroid
    range_low  = support.centroid

    // 7. 区间宽度检查
    IF (range_high - range_low) < MIN_WIDTH_ATR * atr:
        RETURN None

    RETURN (range_high, range_low)
```

---

## 七、过滤器（全部始终开启）

```pseudocode
FUNCTION check_filters(df, i, params):
    atr_ratio = df.atr_ratio[i]
    ema20     = df.ema20[i]
    rsi       = df.rsi[i]
    close     = df.close[i]

    // 1. 波动率过滤（ATR 比率）
    IF atr_ratio < params.atr_ratio_low:   RETURN False  // 行情太死
    IF atr_ratio > params.atr_ratio_high:  RETURN False  // 行情太爆

    // 2. EMA 趋势过滤（斜率）
    slope_window = params.slope_window  // 28
    ema_prev = df.ema20[i - slope_window]
    slope_pct = ABS(ema20 - ema_prev) / ema_prev * 100.0
    IF slope_pct > params.slope_max:  RETURN False  // 趋势太强

    // 3. RSI 中性过滤
    IF rsi < params.rsi_neutral_lo:  RETURN False  // 超卖（可能继续跌）
    IF rsi > params.rsi_neutral_hi:  RETURN False  // 超买（可能继续涨）

    RETURN True
```

---

## 八、信号生成（逐 Bar）

```pseudocode
FUNCTION generate_signals(df, params):
    signals = DataFrame(index=df.index)
    signals.limit_buy_price  = NaN
    signals.limit_sell_price = NaN
    signals.range_high       = NaN
    signals.range_low        = NaN

    FOR i in range(SR_LOOKBACK, len(df)):
        // 过滤器检查
        IF NOT check_filters(df, i, params):
            CONTINUE

        // 区间识别
        result = find_range(df, i, params)
        IF result is None:
            CONTINUE

        range_high, range_low = result
        range_width = range_high - range_low

        // 限价单价格（OFFSET_PCT = 0 时挂在边界）
        limit_buy_price  = range_low  + range_width * params.OFFSET_PCT
        limit_sell_price = range_high - range_width * params.OFFSET_PCT

        signals.limit_buy_price[i]  = limit_buy_price
        signals.limit_sell_price[i] = limit_sell_price
        signals.range_high[i]       = range_high
        signals.range_low[i]        = range_low

    RETURN signals
```

---

## 九、回测引擎（Bar-by-bar 限价单模拟）

```pseudocode
FUNCTION run_backtest(df, signals, params):
    trades = []

    // 状态变量
    long_position  = None   // {entry, tp, sl}
    short_position = None

    pending_buy_price  = NaN
    pending_sell_price = NaN
    pending_buy_since  = -1
    pending_sell_since = -1

    current_range_high = NaN
    current_range_low  = NaN
    buy_filled_this_range  = False
    sell_filled_this_range = False

    FOR i in range(len(df)):
        open_  = df.open[i]
        high   = df.high[i]
        low    = df.low[i]
        close  = df.close[i]
        atr    = df.atr[i]

        // ── 1. 检查区间突破（持仓不受影响，只清挂单）──
        IF NOT isNaN(current_range_high):
            IF close > current_range_high + params.BREAKOUT_ATR * atr:
                // 向上突破，清空挂单
                pending_buy_price  = NaN
                pending_sell_price = NaN
                pending_buy_since  = -1
                pending_sell_since = -1
                current_range_high = NaN
                current_range_low  = NaN
                buy_filled_this_range  = False
                sell_filled_this_range = False

            ELIF close < current_range_low - params.BREAKOUT_ATR * atr:
                // 向下突破，同上
                [清空所有挂单和区间状态]

        // ── 2. 检查持仓止盈止损 ──
        IF long_position is not None:
            tp = long_position.tp
            sl = long_position.sl
            // 同 Bar 冲突：open 在 tp 上方 → 先止盈；open 在 sl 下方 → 先止损
            IF open_ >= tp:
                close_trade(long_position, tp, 'TP')
            ELIF open_ <= sl:
                close_trade(long_position, sl, 'SL')
            ELIF low <= sl AND high >= tp:
                IF open_ > (tp + sl) / 2:
                    close_trade(long_position, tp, 'TP')
                ELSE:
                    close_trade(long_position, sl, 'SL')
            ELIF high >= tp:
                close_trade(long_position, tp, 'TP')
            ELIF low <= sl:
                close_trade(long_position, sl, 'SL')

        // short_position 同理（方向相反）

        // ── 3. 检查限价单超时 ──
        IF pending_buy_since != -1 AND i - pending_buy_since >= params.LIMIT_EXPIRY:
            pending_buy_price = NaN
            pending_buy_since = -1
            buy_filled_this_range = True  // 该区间该侧不再入场

        IF pending_sell_since != -1 AND i - pending_sell_since >= params.LIMIT_EXPIRY:
            pending_sell_price = NaN
            pending_sell_since = -1
            sell_filled_this_range = True

        // ── 4. 检查限价单成交（必须 i > pending_since）──
        IF pending_buy_since != -1 AND i > pending_buy_since:
            IF low <= pending_buy_price AND long_position is None:
                entry = pending_buy_price
                tp    = current_range_high
                sl    = entry - (tp - entry)  // 1:1
                long_position = {entry, tp, sl, entry_bar=i}
                pending_buy_price = NaN
                pending_buy_since = -1
                buy_filled_this_range = True

        IF pending_sell_since != -1 AND i > pending_sell_since:
            IF high >= pending_sell_price AND short_position is None:
                entry = pending_sell_price
                tp    = current_range_low
                sl    = entry + (entry - tp)  // 1:1
                short_position = {entry, tp, sl, entry_bar=i}
                pending_sell_price = NaN
                pending_sell_since = -1
                sell_filled_this_range = True

        // ── 5. 更新挂单（来自信号）──
        new_buy  = signals.limit_buy_price[i]
        new_sell = signals.limit_sell_price[i]

        IF NOT isNaN(new_buy):
            new_range_high = signals.range_high[i]
            new_range_low  = signals.range_low[i]

            // 区间变化时重置状态
            IF new_range_high != current_range_high OR new_range_low != current_range_low:
                current_range_high = new_range_high
                current_range_low  = new_range_low
                buy_filled_this_range  = False
                sell_filled_this_range = False

            // 挂多单（该区间该侧未入场过，且无持仓）
            IF NOT buy_filled_this_range AND long_position is None:
                pending_buy_price = new_buy
                pending_buy_since = i

            // 挂空单
            IF NOT sell_filled_this_range AND short_position is None:
                pending_sell_price = new_sell
                pending_sell_since = i

    RETURN trades
```

---

## 十、推荐参数（已优化）

```json
{
  "// SR 聚类参数": "",
  "SR_LOOKBACK":   500,      // Pivot 回看窗口（Bar 数），固定不优化
  "SR_MERGE_ATR":  0.8366,   // 聚类合并距离（ATR 倍数）
  "SR_MIN_SCORE":  68.87,    // 聚类最低评分阈值（5 维总分）
  "MIN_WIDTH_ATR": 1.5397,   // 区间最小宽度（ATR 倍数）

  "// 交易参数": "",
  "OFFSET_PCT":    0.0,      // 限价偏移比例（0 = 挂在边界，不内侧偏移）
  "LIMIT_EXPIRY":  7,        // 限价单超时根数（7 根 5m K 线 ≈ 35 分钟）
  "BREAKOUT_ATR":  0.0,      // 突破判定 ATR 倍数（0 = 任何突破立即失效）

  "// 波动率过滤": "",
  "atr_ratio_low":  0.45,    // ATR 比率下限（过滤假死行情）
  "atr_ratio_high": 2.3,     // ATR 比率上限（过滤爆发行情）

  "// EMA 趋势过滤": "",
  "ema_period":    20,       // EMA 周期，固定
  "slope_max":     0.43,     // EMA 斜率上限（%）
  "slope_window":  28,       // 斜率回看窗口（Bar 数）

  "// RSI 过滤": "",
  "rsi_period":    14,       // RSI 周期，固定
  "rsi_neutral_lo": 30.0,    // RSI 下限
  "rsi_neutral_hi": 74.0     // RSI 上限
}
```

**参数解读**：
- `OFFSET_PCT = 0.0`：激进入场，挂在区间边界，成交率高但滑点风险略大
- `BREAKOUT_ATR = 0.0`：保守止损，任何突破都立即撤单，避免追趋势
- `LIMIT_EXPIRY = 7`：快速放弃不成交的单，避免死单占用资金
- `SR_MERGE_ATR = 0.84`：较宽的聚类距离，容纳更多 Pivot，区间更稳健

---

## 十一、优化目标函数（7 组件加权评分）

```pseudocode
FUNCTION objective(trades, params):
    IF len(trades) == 0: RETURN 0.0

    // 基础统计
    wins       = [t for t in trades if t.pnl_r > 0]
    win_rate   = len(wins) / len(trades)
    profit_factor = SUM(win pnl_r) / ABS(SUM(loss pnl_r))
    trade_count   = len(trades)
    sharpe        = MEAN(daily_pnl_r) / STD(daily_pnl_r) * SQRT(252)
    max_drawdown_r = MAX_DRAWDOWN(cumulative_pnl_r)
    total_r        = SUM(pnl_r for all trades)

    // 各组件归一化评分（0~100）
    wr_score    = score_component(win_rate,    baseline=0.40, target=0.60)
    pf_score    = score_component(profit_factor, baseline=0.80, target=1.40)
    tc_score    = score_component(trade_count, baseline=100,  target=500)
    sharpe_score = score_component(sharpe,     baseline=0.0,  target=0.15)
    dd_score    = score_drawdown(max_drawdown_r)  // ≤5R 满分，>30R 接近零
    tr_score    = score_component(total_r,     baseline=0.0,  target=100.0)
    cons_score  = score_consistency(trades_by_symbol)  // 跨品种一致性

    // 加权总分
    score = (wr_score    * 0.23 +
             pf_score    * 0.15 +
             tc_score    * 0.20 +
             sharpe_score * 0.20 +
             dd_score    * 0.15 +
             tr_score    * 0.10 +
             cons_score  * 0.15)

    // 交易数不足惩罚
    IF trade_count < 100:
        score *= (trade_count / 100.0)
    IF trade_count < 10:
        score *= (trade_count / 10.0)  // 平方惩罚

    RETURN score
```

---

## 十二、后续优化思路

### 12.1 参数优化方向

**当前可优化的 13 个参数**（Optuna 贝叶斯优化）：

| 参数 | 搜索范围 | 优化优先级 |
|------|---------|-----------|
| SR_MERGE_ATR | [0.2, 1.0] | 高 |
| SR_MIN_SCORE | [40, 120] | 高 |
| MIN_WIDTH_ATR | [0.5, 3.0] | 高 |
| atr_ratio_low | [0.2, 0.8] | 中 |
| atr_ratio_high | [1.5, 4.0] | 中 |
| slope_max | [0.1, 1.0] | 中 |
| slope_window | [10, 50] | 中 |
| rsi_neutral_lo | [20, 45] | 低 |
| rsi_neutral_hi | [55, 80] | 低 |
| OFFSET_PCT | [0.0, 0.3] | 低 |
| LIMIT_EXPIRY | [3, 20] | 低 |
| BREAKOUT_ATR | [0.0, 1.5] | 低 |

### 12.2 策略逻辑改进方向

**1. 动态 OFFSET_PCT（自适应偏移）**
```pseudocode
// 根据 ATR 比率动态调整入场偏移
// 波动率高时偏移更大（更保守），波动率低时偏移更小（更激进）
dynamic_offset = BASE_OFFSET * (atr_ratio / 1.0)
dynamic_offset = CLAMP(dynamic_offset, 0.0, 0.3)
```

**2. 多时间框架确认**
```pseudocode
// 在 5m 信号基础上，要求 15m 或 1h 也处于震荡状态
// 15m EMA 斜率也需 < slope_max_htf
// 可显著减少假信号，但会降低交易频率
```

**3. 成交量过滤**
```pseudocode
// 要求区间识别时有足够成交量支撑
// volume_ratio = volume[i] / ROLLING_MEAN(volume, 20)
// 过滤 volume_ratio < 0.5（成交量萎缩，区间可能无效）
```

**4. 动态止损（ATR 追踪）**
```pseudocode
// 当持仓盈利超过 0.5R 时，将止损移至保本
// 当持仓盈利超过 1.0R 时，止损追踪至 0.5R 盈利位
// 可提升盈亏比，但会降低胜率
```

**5. 区间评分动态阈值**
```pseudocode
// 根据近期市场状态动态调整 SR_MIN_SCORE
// 近期胜率低 → 提高阈值（更严格）
// 近期胜率高 → 降低阈值（更宽松）
lookback_wr = WIN_RATE(last_20_trades)
dynamic_min_score = SR_MIN_SCORE * (1.0 + (0.5 - lookback_wr) * 0.3)
```

**6. 时间过滤（Session Filter）**
```pseudocode
// 只在特定交易时段交易（避开开盘/收盘剧烈波动）
// 例如 ES：只在 09:30-11:30 和 13:30-15:00 ET 交易
// 可减少假突破，提升胜率
```

### 12.3 风险管理改进

**1. 每日最大亏损限制**
```pseudocode
daily_loss_r = SUM(pnl_r for today's closed trades)
IF daily_loss_r < -MAX_DAILY_LOSS_R:  // 例如 -5R
    STOP_TRADING_TODAY
```

**2. 连续亏损保护**
```pseudocode
consecutive_losses = COUNT(recent losses in a row)
IF consecutive_losses >= 3:
    REDUCE_POSITION_SIZE or PAUSE_TRADING
```

**3. 跨品种相关性控制**
```pseudocode
// 避免同时持有高度相关品种的同向仓位
// 例如 ES 和 NQ 同时做多 → 只保留评分更高的那个
```

### 12.4 评分函数改进

**当前权重**：WR(0.23) + PF(0.15) + TC(0.20) + Sharpe(0.20) + DD(0.15) + TotalR(0.10) + Cons(0.15)

**建议调整方向**：
- 如果目标是稳定性 → 提高 DD 权重（0.15 → 0.25），降低 TC 权重
- 如果目标是高频 → 提高 TC 权重（0.20 → 0.30），降低 Cons 权重
- 如果目标是跨品种 → 提高 Cons 权重（0.15 → 0.25）

**新增评分组件建议**：
- Calmar Ratio（年化收益 / 最大回撤）：替代或补充 Sharpe
- 月度一致性（每月盈利月份比例）：比跨品种一致性更直观
- 平均持仓时间：过短可能是噪音交易，过长可能是死单

### 12.5 实盘部署注意事项

1. **滑点处理**：实盘中限价单可能以更差价格成交，建议在回测中加入 1-2 tick 滑点
2. **数据质量**：确保历史数据无前视偏差（look-ahead bias），Pivot 检测需要 i+1 的数据
3. **参数过拟合**：优化后在 out-of-sample 数据上验证，避免过拟合
4. **品种适配**：不同品种的 ATR 量级不同，参数需要分别优化或使用 ATR 归一化
5. **执行延迟**：5m K 线收盘后才能确认信号，实盘需要考虑下一根 K 线开盘的延迟

---

## 十三、完整实现检查清单

生成完整策略代码时，确保包含以下模块：

- [ ] `compute_indicators(df)` — ATR、ATR_MA、ATR_Ratio、EMA20、RSI
- [ ] `detect_pivots(high, low)` — 向量化 Pivot 检测
- [ ] `score_pivot(...)` — 5 维评分（Touch/Reaction/Recency/Compact/Extreme）
- [ ] `cluster_pivots(...)` — Centroid-Linkage 聚类
- [ ] `find_range(df, i, params)` — 区间识别（聚类 + 评分 + 宽度过滤）
- [ ] `check_filters(df, i, params)` — 3 重过滤器（ATR比率/EMA斜率/RSI）
- [ ] `generate_signals(df, params)` — 逐 Bar 信号生成
- [ ] `run_backtest(df, signals, params)` — Bar-by-bar 限价单回测引擎
- [ ] `objective(trades, params)` — 7 组件加权评分（用于 Optuna 优化）
- [ ] 推荐参数 JSON — 直接可用的最优参数

---

*文档生成时间：2026-05-07*
*策略版本：Range Scalper VP V7（Pivot 聚类 + 多维评分）*
