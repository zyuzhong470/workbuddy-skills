#!/usr/bin/env python3
"""
Range Scalper VP — CLI 回测入口。

用法：
    # 从 Bybit 下载数据并回测
    python run_backtest.py --symbol BTCUSDT --interval 5 --days 90 --output ../results/btc_3m.csv

    # 从本地 CSV 回测
    python run_backtest.py --csv /path/to/data.csv --output ../results/result.csv

    # 自定义参数
    python run_backtest.py --symbol BTCUSDT --days 90 --sr-min-score 80 --offset-pct 0.1
"""
import argparse
import os
import sys

# 确保包可导入
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from range_scalper.data_loader import load_csv, compute_indicators, download_bybit_kline, download_okx_kline
from range_scalper.backtester import run_backtest
from range_scalper.reporter import compute_stats, export_csv, print_summary
from range_scalper.range_scalper_opt import StrategyRangeScalperOpt


# 默认参数
DEFAULT_PARAMS = {
    "SR_MERGE_ATR": 0.48,
    "SR_MIN_SCORE": 70.0,
    "MIN_WIDTH_ATR": 1.0,
    "OFFSET_PCT": 0.15,
    "BREAKOUT_ATR": 0.3,
    "LIMIT_EXPIRY": 20,
    "enable_volatility_filter": True,
    "atr_ratio_low": 0.3,
    "atr_ratio_high": 1.5,
    "enable_narrow_range_filter": True,
    "MIN_ATR_MULT": 1.0,
    "enable_ema_trend_filter": True,
    "ema_period": 100,
    "slope_max": 0.05,
    "slope_window": 20,
    "enable_rsi_filter": True,
    "rsi_period": 14,
    "rsi_neutral_lo": 35,
    "rsi_neutral_hi": 65,
}


def main():
    parser = argparse.ArgumentParser(
        description="Range Scalper VP — 震荡区间高抛低吸策略回测"
    )
    # 数据源
    group = parser.add_mutually_exclusive_group(required=True)
    group.add_argument("--csv", type=str, help="本地 CSV 文件路径")
    group.add_argument("--symbol", type=str, help="交易对，如 BTCUSDT")

    parser.add_argument("--interval", type=str, default="5", help="K 线周期（分钟），默认 5")
    parser.add_argument("--days", type=int, default=90, help="回看天数，默认 90")
    parser.add_argument("--source", type=str, default="okx", choices=["okx", "bybit"],
                        help="数据源，默认 okx（公开API无需Key）")
    parser.add_argument("--output", type=str, required=True, help="输出 CSV 路径")

    # API 凭证（仅 Bybit 需要）
    parser.add_argument("--api-key", type=str, default=None, help="Bybit/OKX API Key")
    parser.add_argument("--api-secret", type=str, default=None, help="Bybit/OKX API Secret")

    # 策略参数覆盖
    parser.add_argument("--sr-merge-atr", type=float, help="聚类合并距离")
    parser.add_argument("--sr-min-score", type=float, help="最低聚类评分")
    parser.add_argument("--min-width-atr", type=float, help="区间最小宽度")
    parser.add_argument("--offset-pct", type=float, help="限价偏移比例")
    parser.add_argument("--breakout-atr", type=float, help="突破判定 ATR 倍")
    parser.add_argument("--limit-expiry", type=int, help="限价单超时根数")

    args = parser.parse_args()

    # 构建参数
    params = dict(DEFAULT_PARAMS)

    # 命令行覆盖
    overrides = {
        "SR_MERGE_ATR": args.sr_merge_atr,
        "SR_MIN_SCORE": args.sr_min_score,
        "MIN_WIDTH_ATR": args.min_width_atr,
        "OFFSET_PCT": args.offset_pct,
        "BREAKOUT_ATR": args.breakout_atr,
        "LIMIT_EXPIRY": args.limit_expiry,
    }
    for k, v in overrides.items():
        if v is not None:
            params[k] = v

    # 加载数据
    if args.csv:
        print(f"[加载数据] {args.csv}")
        df = load_csv(args.csv)
    elif args.source == "okx":
        # OKX 公开 API，无需 Key
        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
        os.makedirs(cache_dir, exist_ok=True)

        okx_symbol = f"{args.symbol}-USDT-SWAP" if "-" not in args.symbol else args.symbol
        okx_bar = f"{args.interval}m"

        print(f"[下载数据] OKX {okx_symbol} {okx_bar}, {args.days} 天")
        df = download_okx_kline(
            symbol=okx_symbol,
            bar=okx_bar,
            days=args.days,
            cache_dir=cache_dir,
        )
    else:
        # Bybit API
        api_key = args.api_key or os.environ.get("BYBIT_API_KEY")
        api_secret = args.api_secret or os.environ.get("BYBIT_API_SECRET")

        cache_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "data")
        os.makedirs(cache_dir, exist_ok=True)

        print(f"[下载数据] Bybit {args.symbol} {args.interval}m, {args.days} 天")
        df = download_bybit_kline(
            symbol=args.symbol,
            interval=args.interval,
            days=args.days,
            api_key=api_key,
            api_secret=api_secret,
            cache_dir=cache_dir,
        )

    print(f"[数据加载完成] {len(df)} 根 K 线, {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")

    # 计算指标
    print("[计算指标] ATR, EMA...")
    df = compute_indicators(df)
    print(f"[指标计算完成] {len(df)} 根有效 K 线")

    # 运行回测
    print("[运行回测] Range Scalper VP...")
    strategy = StrategyRangeScalperOpt(params)
    trades = run_backtest(df, strategy)

    # 统计
    stats = compute_stats(trades)

    print()
    print_summary(stats, f"Range Scalper VP — {args.symbol or 'CSV'} 回测")

    # 导出
    output_dir = os.path.dirname(os.path.abspath(args.output))
    os.makedirs(output_dir, exist_ok=True)
    export_csv(trades, stats, args.output)
    print(f"\n[结果已保存] {os.path.abspath(args.output)}")

    return 0


if __name__ == "__main__":
    sys.exit(main())
