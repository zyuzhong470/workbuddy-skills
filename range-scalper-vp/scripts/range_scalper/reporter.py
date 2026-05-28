"""绩效统计、CSV 导出与控制台打印。"""
from __future__ import annotations

from dataclasses import dataclass
from typing import TYPE_CHECKING

import pandas as pd

from .backtester import Trade

if TYPE_CHECKING:
    pass


@dataclass
class BacktestStats:
    total_trades: int
    win_trades: int
    loss_trades: int
    win_rate: float
    avg_win_pct: float
    avg_loss_pct: float
    profit_factor: float
    total_pnl_pct: float
    max_win_pct: float
    max_loss_pct: float
    max_drawdown_pct: float
    long_stats: dict
    short_stats: dict
    equity_curve: list[float]


def _compute_max_drawdown(equity_curve: list[float]) -> float:
    if not equity_curve:
        return 0.0
    max_dd = 0.0
    peak = equity_curve[0]
    for value in equity_curve:
        if value > peak:
            peak = value
        drawdown = peak - value
        if drawdown > max_dd:
            max_dd = drawdown
    return max_dd


def _compute_subset_stats(trades: list[Trade]) -> dict:
    total = len(trades)
    if total == 0:
        return {
            "total_trades": 0, "win_trades": 0, "loss_trades": 0,
            "win_rate": 0.0, "avg_win_pct": 0.0, "avg_loss_pct": 0.0,
            "profit_factor": 0.0, "total_pnl_pct": 0.0,
            "max_win_pct": 0.0, "max_loss_pct": 0.0, "max_drawdown_pct": 0.0,
        }
    wins = [t.pnl_pct for t in trades if t.pnl_pct > 0]
    losses = [t.pnl_pct for t in trades if t.pnl_pct <= 0]
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total
    avg_win = sum(wins) / win_count if wins else 0.0
    avg_loss = sum(losses) / loss_count if losses else 0.0
    profit_factor = avg_win / abs(avg_loss) if losses else float("inf")
    total_pnl = sum(t.pnl_pct for t in trades)
    max_win = max(wins) if wins else 0.0
    max_loss = min(losses) if losses else 0.0
    equity: list[float] = []
    cumulative = 0.0
    for t in trades:
        cumulative += t.pnl_pct
        equity.append(cumulative)
    return {
        "total_trades": total, "win_trades": win_count, "loss_trades": loss_count,
        "win_rate": win_rate, "avg_win_pct": avg_win, "avg_loss_pct": avg_loss,
        "profit_factor": profit_factor, "total_pnl_pct": total_pnl,
        "max_win_pct": max_win, "max_loss_pct": max_loss,
        "max_drawdown_pct": _compute_max_drawdown(equity),
    }


def compute_stats(trades: list[Trade]) -> BacktestStats:
    if not trades:
        return BacktestStats(
            total_trades=0, win_trades=0, loss_trades=0, win_rate=0.0,
            avg_win_pct=0.0, avg_loss_pct=0.0, profit_factor=0.0,
            total_pnl_pct=0.0, max_win_pct=0.0, max_loss_pct=0.0,
            max_drawdown_pct=0.0,
            long_stats=_compute_subset_stats([]),
            short_stats=_compute_subset_stats([]),
            equity_curve=[],
        )
    wins = [t.pnl_pct for t in trades if t.pnl_pct > 0]
    losses = [t.pnl_pct for t in trades if t.pnl_pct <= 0]
    total = len(trades)
    win_count = len(wins)
    loss_count = len(losses)
    win_rate = win_count / total
    avg_win = sum(wins) / win_count if wins else 0.0
    avg_loss = sum(losses) / loss_count if losses else 0.0
    profit_factor = avg_win / abs(avg_loss) if losses else float("inf")
    total_pnl = sum(t.pnl_pct for t in trades)
    max_win = max(wins) if wins else 0.0
    max_loss = min(losses) if losses else 0.0
    equity_curve: list[float] = []
    cumulative = 0.0
    for t in trades:
        cumulative += t.pnl_pct
        equity_curve.append(cumulative)
    max_dd = _compute_max_drawdown(equity_curve)
    long_trades = [t for t in trades if t.direction == "long"]
    short_trades = [t for t in trades if t.direction == "short"]
    return BacktestStats(
        total_trades=total, win_trades=win_count, loss_trades=loss_count,
        win_rate=win_rate, avg_win_pct=avg_win, avg_loss_pct=avg_loss,
        profit_factor=profit_factor, total_pnl_pct=total_pnl,
        max_win_pct=max_win, max_loss_pct=max_loss,
        max_drawdown_pct=max_dd,
        long_stats=_compute_subset_stats(long_trades),
        short_stats=_compute_subset_stats(short_trades),
        equity_curve=equity_curve,
    )


def export_csv(trades: list[Trade], stats: BacktestStats, filepath: str) -> None:
    if not trades:
        df = pd.DataFrame(columns=[
            "entry_time", "exit_time", "direction",
            "entry_price", "exit_price", "pnl_pct",
            "exit_reason", "equity_curve",
        ])
        df.to_csv(filepath, index=False, encoding="utf-8-sig")
        return
    rows = []
    for trade, equity_val in zip(trades, stats.equity_curve):
        rows.append({
            "entry_time": trade.entry_time,
            "exit_time": trade.exit_time,
            "direction": trade.direction,
            "entry_price": trade.entry_price,
            "exit_price": trade.exit_price,
            "pnl_pct": trade.pnl_pct,
            "exit_reason": trade.exit_reason,
            "equity_curve": equity_val,
        })
    df = pd.DataFrame(rows)
    df.to_csv(filepath, index=False, encoding="utf-8-sig")


def print_summary(stats: BacktestStats, title: str = "回测绩效摘要") -> None:
    if stats.total_trades == 0:
        print("无交易信号")
        return

    def fmt_pf(pf: float) -> str:
        return "∞" if pf == float("inf") else f"{pf:.2f}"

    print("=" * 55)
    print(f"           {title}")
    print("=" * 55)
    print(f"  总交易数      : {stats.total_trades}")
    print(f"  盈利交易      : {stats.win_trades}")
    print(f"  亏损交易      : {stats.loss_trades}")
    print(f"  胜率          : {stats.win_rate:.2%}")
    print(f"  平均盈利      : {stats.avg_win_pct:.2f}%")
    print(f"  平均亏损      : {stats.avg_loss_pct:.2f}%")
    print(f"  盈亏比        : {fmt_pf(stats.profit_factor)}")
    print(f"  总收益        : {stats.total_pnl_pct:.2f}%")
    print(f"  最大单笔盈利  : {stats.max_win_pct:.2f}%")
    print(f"  最大单笔亏损  : {stats.max_loss_pct:.2f}%")
    print(f"  最大回撤      : {stats.max_drawdown_pct:.2f}%")
    print("-" * 55)
    print("  做多统计")
    print("-" * 55)
    ls = stats.long_stats
    print(f"  总交易数 : {ls['total_trades']}  胜率 : {ls['win_rate']:.2%}  盈亏比 : {fmt_pf(ls['profit_factor'])}  收益 : {ls['total_pnl_pct']:.2f}%  最大回撤 : {ls['max_drawdown_pct']:.2f}%")
    print("-" * 55)
    print("  做空统计")
    print("-" * 55)
    ss = stats.short_stats
    print(f"  总交易数 : {ss['total_trades']}  胜率 : {ss['win_rate']:.2%}  盈亏比 : {fmt_pf(ss['profit_factor'])}  收益 : {ss['total_pnl_pct']:.2f}%  最大回撤 : {ss['max_drawdown_pct']:.2f}%")
    print("=" * 55)
