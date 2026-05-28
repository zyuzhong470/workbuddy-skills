# 震荡高抛低吸策略 — 设计文档 V2.0

> 项目代号：`range_scalper`
> 日期：2026-05-04
> 状态：V3 趋势段重构完成

---

## 1. 策略核心理念

### 1.1 交易逻辑

在识别出的**震荡区间**内，于区间上沿挂空单（高抛）、下沿挂多单（低吸），利用价格在区间内反复波动的特征获利。

### 1.2 震荡区间识别算法

**核心思路：趋势段反转 + 推动计数法（V3）**

1. **推动定义（V3 趋势段方式）**：推动是一段完整的趋势运动（Trend Segment），而非单根 bar 的局部极值点。具体地：
   - **趋势段跟踪**：逐 bar 跟踪当前趋势方向，持续更新段内极值（向上段跟踪 segment_high，向下段跟踪 segment_low）
   - **反转确认**：价格从当前趋势段的极值点回撤达到 `REVERSAL_PCT`% 时，确认当前趋势段结束
   - **向上推动**：从前一个向下段的低点到当前向上段的高点，幅度 ≥ `MIN_IMPULSE_PCT`%
   - **向下推动**：从前一个向上段的高点到当前向下段的低点，幅度 ≥ `MIN_IMPULSE_PCT`%

2. **震荡区间判定**：
   - 在一个观察窗口内，检测到 **≥ N_PUSH 次交替推动**（默认3次，即 上→下→上 或 下→上→下）
   - 各向上推动终点（段高点）之间**基本平行**：离散度 / 区间宽度 ≤ `PARALLEL_TOLERANCE`
   - 各向下推动终点（段低点）同理
   - 推动方向必须**交替出现**（连续2次同向推动 → 判定为趋势，清空重来）

3. **区间参数**：
   - `RANGE_HIGH`：区间上沿 = 各向上推动终点价格的均值
   - `RANGE_LOW`：区间下沿 = 各向下推动终点价格的均值
   - `RANGE_WIDTH`：区间宽度 = RANGE_HIGH - RANGE_LOW

4. **失效判定**（区间突破）：
   - 收盘价 > 区间上沿 + `BREAKOUT_ATR` × ATR，判定区间失效
   - 收盘价 < 区间下沿 - `BREAKOUT_ATR` × ATR，判定区间失效
   - 区间失效后清除所有挂单和推动状态，重新寻找新区间

### 1.3 入场与出场

| 动作 | 条件 | 执行方式 |
|------|------|---------|
| 做多入场 | 价格触及 `limit_buy_price` | 限价单，成交价 = limit_buy_price |
| 做空入场 | 价格触及 `limit_sell_price` | 限价单，成交价 = limit_sell_price |
| 做多止盈 | 价格触及 `RANGE_HIGH` | 限价单，挂在区间顶部 |
| 做空止盈 | 价格触及 `RANGE_LOW` | 限价单，挂在区间底部 |
| 做多止损 | 入场价 - `tp_distance` | 市价止损（止损距离 = 止盈距离，1:1） |
| 做空止损 | 入场价 + `tp_distance` | 市价止损（止损距离 = 止盈距离，1:1） |
| 限价超时 | 挂单后超过 `LIMIT_EXPIRY` 根Bar未成交 | 自动撤单，该区间该侧不再入场 |
| 区间突破 | 收盘价突破区间 | 持仓按原有止损/止盈处理 |

**限价单位置说明**：
- `limit_buy_price` = `RANGE_LOW + 区间宽度 × OFFSET_PCT`（下沿内侧偏移挂多单）
- `limit_sell_price` = `RANGE_HIGH - 区间宽度 × OFFSET_PCT`（上沿内侧偏移挂空单）
- `OFFSET_PCT` 可优化（默认 0.05~0.40），偏移目的是避免恰好挂在边界上

**止损/止盈计算（纯区间驱动，不用ATR）**：

```
做多：
  止盈距离(tp_dist) = RANGE_HIGH - limit_buy_price       # 止盈在区间顶部
  止损价 = limit_buy_price - tp_dist                       # 1:1盈亏比，止损距离=止盈距离

做空：
  止盈距离(tp_dist) = limit_sell_price - RANGE_LOW        # 止盈在区间底部
  止损价 = limit_sell_price + tp_dist                      # 1:1盈亏比
```

**限价单超时（`LIMIT_EXPIRY`）**：
- 限价单挂出后，每根Bar检查一次是否成交
- 超过 `LIMIT_EXPIRY` 根Bar仍未成交则自动撤单
- 撤单后该区间该侧**不再入场**，另一侧不受影响
- **建议默认值：20根Bar**（5分钟K线≈1.67小时）
  - 1.67小时约为一次完整区间震荡的半周期
  - 超过这个时间价格还没回到边界，说明区间可能正在失效
  - 设为可搜索参数，范围 3~30

### 1.4 过滤条件

以下过滤模块**按开关独立控制**，优化时决定哪些保留：

| 过滤器 | 说明 | 参数 |
|--------|------|------|
| 波动率过滤 | ATR% 过高（剧烈波动）或过低（无波动）时不入场 | `atr_pct_low`, `atr_pct_high` |
| 区间宽度过滤 | 区间太窄（宽度 < ATR × MIN_ATR_MULT）不做 | `min_atr_mult` |
| EMA趋势过滤 | EMA斜率绝对值 > 阈值时判定为趋势，不开仓 | `ema_period`, `slope_max`, `slope_window` |
| 连续亏损冷却 | 连续 N 次亏损后跳过下一信号 | `cooldown_losses` |

---

## 2. 项目结构

```
D:\cl2\range_scalper\
├── range_scalper_optimizer_ui.py      # 主UI（Tkinter，3标签页）
├── range_scalper_optimize_worker.py   # Worker子进程（Optuna优化循环）
├── .range_scalper_prefs.json          # UI偏好持久化
│
├── range_scalper_backtest/
│   ├── __init__.py
│   ├── base.py                        # BaseStrategy + StrategyConfig（照抄ema20）
│   ├── backtester.py                  # 回测引擎（需改造：支持限价单）
│   ├── data_loader.py                 # 数据加载 + 指标预计算
│   ├── reporter.py                    # 统计 + 导出（照抄ema20）
│   └── strategies/
│       ├── __init__.py
│       └── range_scalper_opt.py       # 核心策略：震荡识别 + 高抛低吸信号
│
├── export_to_pine.py                  # 优化结果 → Pine预设参数
└── inject_params_to_pine.py           # 预设参数 → Pine脚本注入
```

---

## 3. 回测引擎改造

### 3.1 现有引擎 vs 需求

| 特性 | ema20引擎 | range_scalper需求 |
|------|----------|------------------|
| 入场方式 | 信号Bar次日Open市价 | 限价单触及入场（Bar内High/Low判定） |
| 信号生命周期 | 单Bar | 区间存续期间挂单有效，最多 `LIMIT_EXPIRY` 根Bar |
| 止损位 | ATR × ATR_N | 入场价 ± 止盈距离（1:1盈亏比，范围驱动） |
| 止盈位 | 入场价 + ATR × ATR_N × RR | 区间顶部（多）/ 底部（空），价格驱动 |
| 区间状态 | 无 | 需跟踪区间建立/失效 + 限价单有效期 |
| 多次入场 | 允许同一条件的连续Bar | 每个区间每侧最多入场1次 |
| 持仓管理 | 一次只持一仓 | 一次只持一仓（相同） |

### 3.2 限价单回测方案

由于回测需要跟踪限价单有效期的 Bar 计数以及每个区间是否已入场，采用**Bar-by-bar模拟**：

```python
def run_backtest(df, strategy, limit_expiry=20, cooldown_losses=0):
    df = strategy.generate_signals(df)
    
    # 策略输出列：
    #   range_active: bool — 当前Bar是否处于活跃震荡区间内
    #   range_high: float — 区间上沿
    #   range_low: float — 区间下沿
    #   range_width: float — 区间宽度
    #   atr: float — ATR值
    #   limit_buy_price: float — 做多限价（range_low + offset）
    #   limit_sell_price: float — 做空限价（range_high - offset）
    
    # 回测运行时维护的状态：
    pending_buy_since = -1      # 做多限价单挂出的Bar索引（-1=无挂单）
    pending_sell_since = -1     # 做空限价单挂出的Bar索引
    long_filled_this_range = False    # 该区间是否已做多
    short_filled_this_range = False   # 该区间是否已做空
    
    for bar_idx in range(len(df)):
        bar = df.iloc[bar_idx]
        
        # 跳过预热期
        if bar_idx < MIN_WARMUP:
            continue
        
        # 检查区间状态变化
        range_just_activated = (df.iloc[bar_idx-1]["range_active"] == False
                                and bar["range_active"] == True)
        range_just_broken = (df.iloc[bar_idx-1]["range_active"] == True
                             and bar["range_active"] == False)
        
        if range_just_activated:
            # 新区间 → 重置入场标记，挂新单
            long_filled_this_range = False
            short_filled_this_range = False
            pending_buy_since = bar_idx   # 当前Bar挂单
            pending_sell_since = bar_idx
        
        if range_just_broken:
            # 区间失效 → 清挂单（持仓继续用原止损止盈）
            pending_buy_since = -1
            pending_sell_since = -1
        
        # 限价单超时检查：从挂单后的下一根Bar开始算
        # 所以计时 = bar_idx - pending_since - 1
        if pending_buy_since != -1 and not long_filled_this_range:
            if bar_idx - pending_buy_since - 1 >= limit_expiry:
                pending_buy_since = -1
        if pending_sell_since != -1 and not short_filled_this_range:
            if bar_idx - pending_sell_since - 1 >= limit_expiry:
                pending_sell_since = -1
        
        if not in_position:
            # 先检查做多（因为low先触达，时间优先级更高）
            if (pending_buy_since != -1 and not long_filled_this_range
                and not pd.isna(bar["limit_buy_price"])
                and bar["low"] <= bar["limit_buy_price"]):
                
                entry_price = bar["limit_buy_price"]
                tp_price = bar["range_high"]
                tp_dist = tp_price - entry_price
                sl_price = entry_price - tp_dist
                long_filled_this_range = True
                pending_buy_since = -1
                # ... 记录交易 ...
            
            # 再检查做空
            elif (pending_sell_since != -1 and not short_filled_this_range
                  and not pd.isna(bar["limit_sell_price"])
                  and bar["high"] >= bar["limit_sell_price"]):
                
                entry_price = bar["limit_sell_price"]
                tp_price = bar["range_low"]
                tp_dist = entry_price - tp_price
                sl_price = entry_price + tp_dist
                short_filled_this_range = True
                pending_sell_since = -1
                # ... 记录交易 ...
        else:
            # 检查止损/止盈 - 向量化查找出场（同ema20）
            # 注意：区间突破后，止盈止损单仍有效
            ...
```

**关键决策**：
1. 限价单触发：做多用 `low <= limit_buy_price`，做空用 `high >= limit_sell_price`
2. 止盈价格是**固定的区间边界**（不随区间范围变化）
3. 止损距离 = 止盈距离（严格1:1）
4. 限价单超时从**挂单后的下一根Bar**开始计数（排除挂单Bar本身）
5. **每个区间每侧最多入场1次**：用 `long_filled_this_range` / `short_filled_this_range` 标记
6. **同Bar双向冲突**：先检查做多（low优先），若成交则做空挂单保留
7. **区间突破不平仓**：持仓继续使用原有止盈止损单，未出场时到数据末尾强制平仓

### 3.3 Trade数据结构

照抄ema20的 `Trade` dataclass，新增：

```python
@dataclass
class Trade:
    # ... 原有字段（entry/exit time, price, direction, pnl_pct, exit_reason...）
    range_high: float    # 入场时区间上沿
    range_low: float     # 入场时区间下沿
    limit_price: float   # 限价单触发价格
    tp_distance: float   # 止盈距离（= range_high - entry for long）
    range_width: float   # 区间宽度（range_high - range_low）
```

---

## 4. 策略信号逻辑详细设计

### 4.1 震荡区间识别（`generate_signals` 核心逻辑）

```
输入：OHLCV + ATR DataFrame
输出：新增以下列：
  range_active: bool       — 当前Bar是否处于活跃震荡区间
  range_high: float        — 区间上沿
  range_low: float         — 区间下沿
  limit_buy_price: float   — 做多限价（有区间且不过滤时的值）
  limit_sell_price: float  — 做空限价（有区间且不过滤时的值）

算法详解（V3 趋势段反转状态机，逐Bar扫描）：

=== Step 1: 趋势段跟踪 ===

  维护状态：
    direction: "up" / "down" / None  — 当前趋势段方向
    segment_high: float              — 向上段的最高价（high列）
    segment_low: float               — 向下段的最低价（low列）
    segment_start_price: float       — 当前趋势段的起点价格

  初始化：
    用第一根 bar 的 close >= open 判断初始方向
    close >= open → direction="up", segment_high=high, start=low
    close < open  → direction="down", segment_low=low, start=high

  逐 bar 更新：
    向上段：如果 high[i] > segment_high → 更新 segment_high
    向下段：如果 low[i] < segment_low → 更新 segment_low

=== Step 2: 反转检测与推动确认 ===

  向上段反转条件：
    (segment_high - low[i]) / segment_high * 100 >= REVERSAL_PCT
    → 向上趋势段结束
    → 计算幅度：(segment_high - segment_start_price) / segment_start_price * 100
    → 幅度 >= MIN_IMPULSE_PCT → 确认为有效向上推动
    → 开始新的向下趋势段（start_price = segment_high）

  向下段反转条件：
    (high[i] - segment_low) / segment_low * 100 >= REVERSAL_PCT
    → 向下趋势段结束
    → 计算幅度：(segment_start_price - segment_low) / segment_start_price * 100
    → 幅度 >= MIN_IMPULSE_PCT → 确认为有效向下推动
    → 开始新的向上趋势段（start_price = segment_low）

=== Step 3: 交替性检查 ===

  每次确认一个新推动后：
    如果 last_impulse_dir == 新推动方向（连续同向）：
      → 清空 impulses_up 和 impulses_down
      → 仅保留当前推动作为新序列起点
    更新 last_impulse_dir

=== Step 4: 区间建立（满足 N_PUSH 后触发）===

  每次确认新推动后，调用 _try_build_range()：
    1. 过滤掉超过 SWING_LOOKBACK 的过期推动
    2. 检查总推动数 >= N_PUSH
    3. 平行度检查：
       up_spread = max(up_prices) - min(up_prices)
       down_spread = max(down_prices) - min(down_prices)
       est_width = mean(up_prices) - mean(down_prices)
       up_spread <= PARALLEL_TOLERANCE * est_width 且
       down_spread <= PARALLEL_TOLERANCE * est_width
    4. 通过 → range_active=True, range_high=mean(up_prices), range_low=mean(down_prices)

=== Step 5: 区间失效检测（每根Bar检查）===

  if range_active:
      if close > range_high + BREAKOUT_ATR * ATR:
          range_active = False     # 向上突破
          重置所有推动状态
      if close < range_low - BREAKOUT_ATR * ATR:
          range_active = False     # 向下突破
          重置所有推动状态

  区间活跃时：填充输出列，跳过推动检测（continue）
  区间边界固定不漂移。
```

### 4.2 限价单挂单逻辑

```
当 range_active=True 时：

  offset = (range_high - range_low) × OFFSET_PCT
  
  limit_buy_price  = range_low + offset     # 在下沿内侧挂多单
  limit_sell_price = range_high - offset    # 在上沿内侧挂空单

入场后自动设置止盈/止损（不用ATR）：
  做多：TP = range_high（固定）, SL = entry - (range_high - entry)  # 1:1
  做空：TP = range_low（固定）,  SL = entry + (entry - range_low)   # 1:1

限价单超时：挂单后超过 LIMIT_EXPIRY 根Bar未成交则撤单
  
  # 过滤叠加
  if 波动率过滤开启 and not vol_ok:
      limit_buy_price = limit_sell_price = NaN  # 不挂单
  if 区间窄度过滤 and range_width < ATR × MIN_ATR_MULT:
      limit_buy_price = limit_sell_price = NaN  # 区间太窄不做
  if EMA趋势过滤 and ema_slope绝对值 > slope_max:
      limit_buy_price = limit_sell_price = NaN
```

### 4.3 工程注意事项与Edge Cases

**① LIMIT_EXPIRY 计时起点**
- 区间建立时挂单的**当前Bar**不算入超时计数
- 从**挂单后的下一根Bar**开始检查：`bar_idx - pending_since_bar - 1 >= LIMIT_EXPIRY`
- 原因是挂单Bar本身可能刚好处于区间中部，需要完整的一根Bar给价格运动时间

**② 同Bar双向冲突处理**
- 同Bar内 `low <= limit_buy_price` 且 `high >= limit_sell_price` 同时满足
- 回测规则：**严格按照 low→high 的顺序**。先检查做多（low先触达），再检查做空
- 一旦一个方向成交，另一个方向的挂单保留（该侧仍有效）

**③ 区间边界固定不漂移**
- 区间建立后，即使后续推动仍在容忍范围内，也不更新 range_high / range_low
- 第4+N次推动的唯一作用是：如果超出容忍范围则区间失效
- 这样避免区间"越震越宽"

**④ 连续同向推动重置**
- 检测到连续2次同向推动（如上→上）→ 判定为趋势
- 清空所有推动记录，以最新的这个推动为起点重新计数
- 这是防止在趋势行情中错误识别震荡的关键防线

**⑤ 持仓中区间突破的处理**
- 区间突破信号出现时：**不立即平仓**，持仓继续按原有止盈/止损单等待成交
- 因为止盈挂在区间边界，突破时做空单止盈在区间下沿会被触发（向下突破时）
- 做多单止损在上沿也能被触发（向上突破时）
- 如果既没触止盈也没触止损，到数据末尾强制平仓

---

## 5. 优化参数设计

### 5.1 搜索参数（Optuna suggest）

| # | 参数名 | 类型 | 默认范围 | 说明 |
|---|--------|------|---------|------|
| 1 | `N_PUSH` | int | 3 ~ 5 | 构成震荡的最少推动次数 |
| 2 | `MIN_IMPULSE_PCT` | float | 0.3 ~ 2.0 | 趋势段幅度必须达到此百分比才确认为推动 |
| 3 | `REVERSAL_PCT` | float | 0.1 ~ 2.0 | 价格从极值点回撤达到此百分比时确认趋势段结束 |
| 4 | `PARALLEL_TOLERANCE` | float | 0.1 ~ 1.0 | 高低点平行度容忍度（区间宽度比例） |
| 5 | `OFFSET_PCT` | float | 0.05 ~ 0.40 | 限价偏移占区间宽度的比例 |
| 6 | `LIMIT_EXPIRY` | int | 3 ~ 30 | 限价单超时根数（默认20，5分钟K线≈1.7h） |
| 7 | `BREAKOUT_ATR` | float | 0.1 ~ 1.5 | 突破判定ATR倍数（默认0.6） |
| 8 | `MIN_ATR_MULT` | float | 0.3 ~ 3.0 | 区间窄度过滤：区间宽度 < ATR × 此值 不做 |
| 9 | `SWING_LOOKBACK` | int | 30 ~ 120 | 推动统计的回看Bar数 |

### 5.2 开关参数（UI Checkbox）

| # | 参数名 | 默认 | 说明 |
|---|--------|------|------|
| 1 | `enable_volatility_filter` | ON | 波动率过滤 |
| 2 | `enable_narrow_range_filter` | ON | 区间窄度过滤（宽度 < ATR × MIN_ATR_MULT 不做） |
| 3 | `enable_ema_trend_filter` | OFF | EMA趋势过滤 |

### 5.3 固定参数

| 参数 | 值 | 说明 |
|------|---|------|
| `RR_RATIO` | 1.0 | 盈亏比固定1:1（止损距离 = 止盈距离），不优化 |
| `ATR_PERIOD` | 14 | ATR计算周期（仅用于波动率过滤） |
| `EMA_PERIOD` | 20 | EMA趋势过滤用周期（若开启） |

### 5.4 过滤器子参数（随开关启用，可搜索）

波动率过滤：
- `atr_pct_low`：float, 0.15 ~ 0.30
- `atr_pct_high`：float, 3.0 ~ 12.0

区间窄度过滤（随开关启用，参数可搜索）：
- `min_atr_mult`：float, 0.3 ~ 3.0（区间宽度 < ATR × 此值 → 不做）
- 例如 ATR=20, MIN_ATR_MULT=1.5 → 区间宽度必须 ≥ 30 才交易

EMA趋势过滤：
- `slope_max`：float, 0.05 ~ 0.30（斜率绝对值上限，超过视为趋势）
- `slope_window`：int, 5 ~ 30

---

## 6. 评分系统

照搬 ema20 的 **7组件加权归一化评分**，调整目标值以适应震荡策略的交易特征（预期交易频率中等、胜率偏高）：

| 组件 | 默认权重 | 目标值 | 说明 |
|------|---------|--------|------|
| 胜率 (WR) | 0.23 | 0.60 | 震荡策略应偏重胜率 |
| 盈亏比 (PF) | 0.15 | 1.40 | 中等目标 |
| 交易数 (TC) | 0.20 | 500 | 比ema20少，但比second_wave多 |
| 夏普 (Sharpe) | 0.20 | 0.15 | 中等目标 |
| 回撤 (DD) | 0.15 | 5/15/30R | 与ema20相同分档 |
| 总R (TotalR) | 0.10 | 100R | 中等目标 |
| 一致性 (Cons) | 0.15 | — | 跨品种一致性 |

---

## 7. UI设计

### 7.1 布局

照搬 ema20 的3标签页架构：

**Tab 1 — 参数配置**
- 数据源面板（MT5 / 期货 / 本地文件夹）
- 基础参数面板：
  - 推动检测：N_PUSH, MIN_IMPULSE_PCT, REVERSAL_PCT, SWING_LOOKBACK
  - 区间判定：PARALLEL_TOLERANCE, BREAKOUT_ATR
  - 交易参数：OFFSET_PCT, LIMIT_EXPIRY
- 过滤器面板（3个Enable复选框 + 子参数范围）
- 评分权重配置面板

**Tab 2 — 运行与日志**
- 开始/停止按钮
- Worker数量
- 优化轮数
- 实时日志滚动框

**Tab 3 — 结果与导出**
- Top-20 结果表格
- 详细参数展示
- CSV/JSON导出按钮

### 7.2 类名映射

| ema20 | range_scalper |
|-------|---------------|
| `EMA20OptimizerUI` | `RangeScalperOptimizerUI` |
| `OptimizationWorker` | `RangeScalperWorker` |
| `StrategyEMA20Opt` | `StrategyRangeScalperOpt` |
| `.ema20_optimizer_prefs.json` | `.range_scalper_prefs.json` |
| `ema20_optimize_worker.py` | `range_scalper_optimize_worker.py` |

---

## 8. 数据管线

### 8.1 数据源

与 ema20 相同，支持4种数据源：
1. MT5 实盘数据
2. yfinance 期货数据
3. OKX 加密货币
4. 本地 CSV 文件夹（优先，复用 `D:\cl2\期货数据\`）

### 8.2 指标预计算

`compute_indicators()` 计算：
- 保留：`atr`, `ema20`, 各周期EMA
- 注意：推动识别（趋势段反转）在策略层逐 bar 完成，不需要预计算局部高低点

### 8.3 数据流转

```
UI加载数据 → compute_indicators() → 序列化pickle
     ↓
Worker子进程加载pickle → Optuna循环
     ↓
StrategyRangeScalperOpt.generate_signals(df) → 信号列
     ↓
run_backtest(df, strategy, ...) → Trade列表
     ↓
7组件评分 → 日志输出 → pickle存档
```

---

## 9. Pine Script 导出

### 9.1 预设参数提取

照搬 ema20 的 `export_to_pine.py` 逻辑：
- 从 worker pickle 文件加载所有 trial
- 多样性选取 Top-N 预设
- 生成 Pine 常量块

### 9.2 Pine 脚本目标

新建 `D:\cl2\tv-ea\range_scalper_strategy.pine`，功能：
- 震荡区间识别 + 可视化（画区间上下沿）
- 限价单挂单标记
- 多预设切换（input.bool）
- 止损/止盈线绘制

---

## 10. 开发计划

| 阶段 | 任务 | 依赖 |
|------|------|------|
| **P1** | 创建项目骨架 + base.py + data_loader.py + reporter.py（照抄） | 无 |
| **P2** | 实现核心策略 `range_scalper_opt.py`（震荡识别 + 信号生成） | P1 |
| **P3** | 改造回测引擎 `backtester.py`（限价单支持） | P2 |
| **P4** | 实现 Worker `range_scalper_optimize_worker.py` | P3 |
| **P5** | 实现 UI `range_scalper_optimizer_ui.py` | P4 |
| **P6** | 单元测试 + 调试（用现有期货数据跑通） | P5 |
| **P7** | Pine Script 导出 + 策略脚本编写 | P6 |

**预计工作量**：P1-P5 可并行参考 ema20 代码快速搭建，P2-P3 是核心逻辑需重点调试。

---

## 11. 风险与待确认项

| # | 问题 | 影响 | 建议 |
|---|------|------|------|
| 1 | 推动识别算法的鲁棒性——如何避免在趋势中误判为震荡 | 虚假信号 | 交替方向检查 + 连续同向重置 + EMA趋势过滤 |
| 2 | 限价单回测的精度——Bar内触发的假设是否合理 | 回测偏差 | 后期可考虑加入滑点模型 |
| 3 | 区间建立后是否更新边界？ | 稳定性 | **不更新**，固定不变。后续推动用容忍度检查，超出则失效。避免区间漂移 |
| 4 | 区间宽度很窄时，止盈距离很小，止损距离更小 | 滑点影响大 | `MIN_ATR_MULT` 过滤会拒绝窄区间（宽度 < ATR × N） |
| 5 | 同Bar双向都触发如何处理？ | 冲突 | 按 low→high 顺序，先检查做多 |
| 6 | LIMIT_EXPIRY 计时从挂单Bar还是下一Bar开始？ | 一致性 | 从下一Bar开始（挂单Bar不计入） |
| 7 | 数据量不足时无法识别区间 | 无交易 | `MIN_WARMUP` 保护，数据至少需要几百根K线才有意义 |

---

## 12. 关键设计决策总结

| 决策 | 选择 | 理由 |
|------|------|------|
| 回测引擎 | 改造ema20引擎，新增限价单+超时支持 | 最大程度复用已有代码 |
| 区间识别 | 趋势段反转 + 推动计数法 + 平行度检查（V3） | 识别真正的趋势运动，而非局部极值点，更鲁棒 |
| 入场方式 | 限价单（区间边界内侧偏移） | 符合"高抛低吸"策略本质 |
| 止损/止盈 | 范围驱动，1:1盈亏比，**不用ATR** | 止盈挂区间边界，止损=等距反向 |
| 限价超时 | 20根Bar（5分钟K线≈1.7h），可搜索 3~30 | 避免死单挂到区间失效 |
| 区间窄度过滤 | ATR × MIN_ATR_MULT，区间太窄不做 | 避免窄区间利润不足以覆盖滑点 |
| 多次入场 | 每个区间每侧最多1次 | 避免同区间反复亏损 |
| 评分系统 | 7组件加权（照搬ema20，调整目标值） | 已验证有效，无需重新设计 |
| 数据管线 | 复用ema20的pickle + 多进程架构 | 成熟稳定 |
| Pine导出 | 照搬ema20的2步流程 | 代码复用 |

---

> **下一步**：请审阅本设计文档，确认或提出修改意见。确认后按 P1→P7 顺序实现。
