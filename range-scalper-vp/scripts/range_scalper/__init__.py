"""Range Scalper VP — 震荡区间高抛低吸量化策略包。

核心组件：
  - data_loader: CSV/Bybit 数据加载 + 指标预计算
  - backtester:   Bar-by-bar 限价单回测引擎（对齐 TradingView）
  - reporter:     绩效统计 + CSV 导出
  - strategies/range_scalper_opt:  Pivot 聚类 + 多维评分核心策略
"""
