"""回测引擎：Bar-by-bar限价单模拟 + 向量化出场查找。"""
from dataclasses import dataclass
from typing import Literal, Optional

import numpy as np
import pandas as pd


@dataclass
class Trade:
    entry_time:     pd.Timestamp
    exit_time:      pd.Timestamp
    direction:      Literal["long", "short"]
    entry_price:    float
    exit_price:     float
    pnl_pct:        float
    exit_reason:    Literal["take_profit", "stop_loss", "end_of_data"]
    atr_at_entry:   float
    sl_pct:         float
    range_high:     float
    range_low:      float
    limit_price:    float
    tp_distance:    float
    range_width:    float


def run_backtest(
    df: pd.DataFrame,
    strategy,
    atr_n: float = 1.0,
    rr_ratio: float = 1.0,
    cooldown_losses: int = 0,
) -> list[Trade]:
    """Bar-by-bar限价单回测（对齐 TradingView strategy 引擎）。"""
    df = strategy.generate_signals(df)
    df = df.reset_index(drop=True)

    n = len(df)
    high = df["high"].to_numpy()
    low = df["low"].to_numpy()
    open_arr = df["open"].to_numpy()
    atr_arr = df["atr"].to_numpy()
    datetime_arr = df["datetime"].to_numpy()
    close = df["close"].to_numpy()

    limit_buy = df["limit_buy_price"].to_numpy()
    limit_sell = df["limit_sell_price"].to_numpy()
    range_active_arr = df["range_active"].to_numpy()
    range_high_arr = df["range_high"].to_numpy()
    range_low_arr = df["range_low"].to_numpy()
    range_width_arr = df["range_width"].to_numpy()

    trades: list[Trade] = []
    in_position = False
    position_entry_idx = -1
    position_direction: Optional[Literal["long", "short"]] = None
    position_entry_price = 0.0
    position_tp_price = 0.0
    position_sl_price = 0.0
    position_range_high = 0.0
    position_range_low = 0.0
    position_range_width = 0.0
    position_limit_price = 0.0
    position_atr = 0.0
    position_tp_dist = 0.0
    consecutive_losses = 0

    pending_buy_since = -1
    pending_sell_since = -1
    pending_buy_price = np.nan
    pending_sell_price = np.nan
    buy_filled_this_range = False
    sell_filled_this_range = False
    current_range_high = np.nan
    current_range_low = np.nan
    current_range_id = -1

    limit_expiry = int(strategy.params.get("LIMIT_EXPIRY", 20))

    def _range_id(rh, rl):
        if pd.isna(rh) or pd.isna(rl):
            return -1
        return hash((round(rh, 4), round(rl, 4)))

    for i in range(n):
        rid = _range_id(range_high_arr[i], range_low_arr[i])

        if range_active_arr[i] and rid != current_range_id:
            current_range_high = range_high_arr[i]
            current_range_low = range_low_arr[i]
            current_range_id = rid
            buy_filled_this_range = False
            sell_filled_this_range = False
            if not pd.isna(limit_buy[i]):
                pending_buy_since = i
                pending_buy_price = float(limit_buy[i])
            if not pd.isna(limit_sell[i]):
                pending_sell_since = i
                pending_sell_price = float(limit_sell[i])

        elif not range_active_arr[i] and current_range_id != -1:
            current_range_high = np.nan
            current_range_low = np.nan
            current_range_id = -1
            pending_buy_since = -1
            pending_sell_since = -1
            pending_buy_price = np.nan
            pending_sell_price = np.nan

        if range_active_arr[i] and rid == current_range_id:
            if not buy_filled_this_range and not pd.isna(limit_buy[i]) and pending_buy_since == -1:
                pending_buy_since = i
                pending_buy_price = float(limit_buy[i])
            if not sell_filled_this_range and not pd.isna(limit_sell[i]) and pending_sell_since == -1:
                pending_sell_since = i
                pending_sell_price = float(limit_sell[i])

        if pending_buy_since != -1 and i - pending_buy_since >= limit_expiry:
            pending_buy_since = -1
            pending_buy_price = np.nan
            buy_filled_this_range = True
        if pending_sell_since != -1 and i - pending_sell_since >= limit_expiry:
            pending_sell_since = -1
            pending_sell_price = np.nan
            sell_filled_this_range = True

        if not in_position:
            entered = False
            if cooldown_losses > 0 and consecutive_losses >= cooldown_losses:
                consecutive_losses = 0

            can_buy = (pending_buy_since != -1
                       and i > pending_buy_since
                       and not buy_filled_this_range
                       and not np.isnan(pending_buy_price)
                       and low[i] <= pending_buy_price)

            can_sell = (pending_sell_since != -1
                        and i > pending_sell_since
                        and not sell_filled_this_range
                        and not np.isnan(pending_sell_price)
                        and high[i] >= pending_sell_price)

            if can_buy and can_sell:
                dist_to_buy = abs(open_arr[i] - pending_buy_price)
                dist_to_sell = abs(open_arr[i] - pending_sell_price)
                if dist_to_buy <= dist_to_sell:
                    can_sell = False
                else:
                    can_buy = False

            if can_buy:
                entry_px = pending_buy_price
                tp_px = float(current_range_high)
                tp_dist = tp_px - entry_px
                sl_px = entry_px - tp_dist
                in_position = True
                position_entry_idx = i
                position_direction = "long"
                position_entry_price = entry_px
                position_tp_price = tp_px
                position_sl_price = sl_px
                position_range_high = float(current_range_high)
                position_range_low = float(current_range_low)
                position_range_width = position_range_high - position_range_low
                position_limit_price = entry_px
                position_atr = float(atr_arr[i]) if not pd.isna(atr_arr[i]) else 0.0
                position_tp_dist = tp_dist
                buy_filled_this_range = True
                pending_buy_since = -1
                pending_buy_price = np.nan
                entered = True

            elif can_sell:
                entry_px = pending_sell_price
                tp_px = float(current_range_low)
                tp_dist = entry_px - tp_px
                sl_px = entry_px + tp_dist
                in_position = True
                position_entry_idx = i
                position_direction = "short"
                position_entry_price = entry_px
                position_tp_price = tp_px
                position_sl_price = sl_px
                position_range_high = float(current_range_high)
                position_range_low = float(current_range_low)
                position_range_width = position_range_high - position_range_low
                position_limit_price = entry_px
                position_atr = float(atr_arr[i]) if not pd.isna(atr_arr[i]) else 0.0
                position_tp_dist = tp_dist
                sell_filled_this_range = True
                pending_sell_since = -1
                pending_sell_price = np.nan
                entered = True

            if entered:
                search_start = i + 1
                if search_start >= n:
                    exit_px = float(close[i])
                    exit_reason = "end_of_data"
                    exit_idx = i
                else:
                    if position_direction == "long":
                        tp_hit = high[search_start:] >= position_tp_price
                        sl_hit = low[search_start:] <= position_sl_price
                    else:
                        tp_hit = low[search_start:] <= position_tp_price
                        sl_hit = high[search_start:] >= position_sl_price

                    if tp_hit.any() or sl_hit.any():
                        tp_first = int(np.argmax(tp_hit)) if tp_hit.any() else len(tp_hit)
                        sl_first = int(np.argmax(sl_hit)) if sl_hit.any() else len(sl_hit)

                        if tp_first < sl_first:
                            rel_idx = tp_first
                            exit_px = float(position_tp_price)
                            exit_reason = "take_profit"
                        elif sl_first < tp_first:
                            rel_idx = sl_first
                            exit_px = float(position_sl_price)
                            exit_reason = "stop_loss"
                        else:
                            exit_bar_abs = search_start + tp_first
                            bar_open = open_arr[exit_bar_abs]
                            dist_tp = abs(bar_open - position_tp_price)
                            dist_sl = abs(bar_open - position_sl_price)
                            if dist_tp <= dist_sl:
                                rel_idx = tp_first
                                exit_px = float(position_tp_price)
                                exit_reason = "take_profit"
                            else:
                                rel_idx = sl_first
                                exit_px = float(position_sl_price)
                                exit_reason = "stop_loss"
                        exit_idx = search_start + rel_idx
                    else:
                        exit_idx = n - 1
                        exit_px = float(close[exit_idx])
                        exit_reason = "end_of_data"

                if position_direction == "long":
                    pnl = (exit_px - position_entry_price) / position_entry_price * 100
                else:
                    pnl = (position_entry_price - exit_px) / position_entry_price * 100

                if pnl <= 0:
                    consecutive_losses += 1
                else:
                    consecutive_losses = 0

                sl_pct_val = position_tp_dist / position_entry_price * 100 if position_entry_price > 0 else 0.0

                trades.append(Trade(
                    entry_time=pd.Timestamp(str(datetime_arr[position_entry_idx])),
                    exit_time=pd.Timestamp(str(datetime_arr[exit_idx])),
                    direction=position_direction,
                    entry_price=position_entry_price,
                    exit_price=float(exit_px),
                    pnl_pct=pnl,
                    exit_reason=exit_reason,
                    atr_at_entry=position_atr,
                    sl_pct=sl_pct_val,
                    range_high=position_range_high,
                    range_low=position_range_low,
                    limit_price=position_limit_price,
                    tp_distance=position_tp_dist,
                    range_width=position_range_width,
                ))

                in_position = False
                position_direction = None
                if exit_idx > i and exit_idx < n - 1:
                    i = exit_idx - 1

    return trades
