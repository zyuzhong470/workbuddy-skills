# 常见参数预设

## 预设 A：保守默认（信号少，质量高）

```pine
bbz_threshold = -1.0
slope_thresh  = 1.0
atr_mult      = 1.5
rr_ratio      = 2.0
lookback      = 20
qty           = 0.01
```

适用场景：BTC 1H / 4H，低频高胜率

---

## 预设 B：激进（信号多，适合震荡市验证）

```pine
bbz_threshold = -0.8
slope_thresh  = 0.8
atr_mult      = 1.2
rr_ratio      = 1.5
lookback      = 15
qty           = 0.01
```

适用场景：BTC 15min / 1H，用于了解策略在不同市场环境的表现

---

## 预设 C：大止损（趋势跟踪）

```pine
bbz_threshold = -1.2
slope_thresh  = 1.2
atr_mult      = 2.5
rr_ratio      = 3.0
lookback      = 30
qty           = 0.005
```

适用场景：BTC 4H / 日线，捕获大级别行情

---

## 预设 D：百分比风险（进阶仓位管理）

```pine
bbz_threshold  = -1.0
slope_thresh   = 1.0
atr_mult       = 1.5
rr_ratio       = 2.0
lookback       = 20
risk_pct       = 1.0      // 每笔风险 1% 权益
// qty 动态计算：
// qty = (strategy.equity * risk_pct/100) / math.abs(close - stop_loss)
```

适用场景：实盘模拟，权益级风控。需要 `default_qty_type = strategy.cash`

---

## 扩展参数说明

| 参数 | 含义 | 调大效果 | 调小效果 |
|------|------|----------|----------|
| `bbz_threshold` | 压缩敏感度（负值） | 更严格的压缩判断，信号更少 | 更宽松，信号更多 |
| `slope_thresh` | 趋势强度门槛 | 要求更强趋势，误判少 | 更早进场，但可能假突破多 |
| `atr_mult` | 止损距离 | 止损更宽，抗噪性强但亏损更大 | 止损更紧，被扫损概率高 |
| `rr_ratio` | 止盈倍数 | 每笔盈利更大但触发概率低 | 频繁止盈但单笔收益小 |
| `lookback` | 结构突破回望 | 突破更大阻力，信号更少 | 突破近期阻力，信号多但可靠性低 |

---

## 可视化扩展（用户明确要求时添加）

```pine
// 在代码末尾添加
plot(basis, "BB Middle", color=color.gray)
bgcolor(state == 1 ? color.new(color.blue, 90) : na, title="压缩状态")
bgcolor(state == 4 ? color.new(color.green, 90) : na, title="持仓状态")
plotshape(state == 4 and state[1] != 4, "Entry", shape.triangleup, location.belowbar, color.green, size=size.small)
```
