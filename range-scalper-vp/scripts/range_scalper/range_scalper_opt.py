"""
Range Scalper VP — Pivot 聚类 + 多维评分核心策略。
V7: 性能优化版 — 向量化 pivot 预计算 + numba JIT 主循环。
"""
import math
from typing import Optional, Tuple

import numpy as np
import pandas as pd

try:
    from numba import njit
    HAS_NUMBA = True
except ImportError:
    HAS_NUMBA = False

from .base import BaseStrategy, StrategyConfig


def _vectorized_pivot_detection(high_arr: np.ndarray, low_arr: np.ndarray, n: int):
    """向量化检测所有 Pivot High 和 Pivot Low（left=1, right=1）。"""
    ph_mask = np.zeros(n, dtype=np.bool_)
    pl_mask = np.zeros(n, dtype=np.bool_)
    if n < 3:
        return ph_mask, pl_mask
    ph_mask[1:-1] = (high_arr[1:-1] > high_arr[:-2]) & (high_arr[1:-1] > high_arr[2:])
    pl_mask[1:-1] = (low_arr[1:-1] < low_arr[:-2]) & (low_arr[1:-1] < low_arr[2:])
    return ph_mask, pl_mask


def _vectorized_reaction(high_arr, low_arr, ph_mask, pl_mask, n, react_look=3):
    ph_react = np.zeros(n, dtype=np.float64)
    pl_react = np.zeros(n, dtype=np.float64)
    for j in range(react_look):
        start = j
        if start >= n:
            break
        diff_h = high_arr[start:] - low_arr[:n - start]
        ph_react[start:] = np.maximum(ph_react[start:], diff_h)
        diff_l = high_arr[:n - start] - low_arr[start:]
        pl_react[start:] = np.maximum(pl_react[start:], diff_l)
    ph_react[~ph_mask] = 0.0
    pl_react[~pl_mask] = 0.0
    return ph_react, pl_react


def _vectorized_extreme(high_arr, low_arr, ph_mask, pl_mask, n, lookback):
    ph_extreme = np.zeros(n, dtype=np.bool_)
    pl_extreme = np.zeros(n, dtype=np.bool_)
    win = min(lookback, n)
    if win < 2:
        return ph_extreme, pl_extreme
    high_series = pd.Series(high_arr)
    low_series = pd.Series(low_arr)
    roll_max_high = high_series.rolling(window=win, min_periods=1).max().to_numpy()
    roll_min_low = low_series.rolling(window=win, min_periods=1).min().to_numpy()
    ph_indices = np.where(ph_mask)[0]
    for idx in ph_indices:
        ph_extreme[idx] = (high_arr[idx] >= roll_max_high[idx])
    pl_indices = np.where(pl_mask)[0]
    for idx in pl_indices:
        pl_extreme[idx] = (low_arr[idx] <= roll_min_low[idx])
    return ph_extreme, pl_extreme


def _precompute_pivots_vectorized(high_arr, low_arr, n, sr_lookback, react_look=3):
    ph_mask, pl_mask = _vectorized_pivot_detection(high_arr, low_arr, n)
    ph_react, pl_react = _vectorized_reaction(high_arr, low_arr, ph_mask, pl_mask, n, react_look)
    ph_extreme, pl_extreme = _vectorized_extreme(high_arr, low_arr, ph_mask, pl_mask, n, sr_lookback)
    ph_indices = np.where(ph_mask)[0]
    pl_indices = np.where(pl_mask)[0]
    n_ph = len(ph_indices)
    n_pl = len(pl_indices)
    total = n_ph + n_pl
    piv_bars = np.empty(total, dtype=np.int64)
    piv_prices = np.empty(total, dtype=np.float64)
    piv_reacts = np.empty(total, dtype=np.float64)
    piv_extremes = np.empty(total, dtype=np.bool_)
    piv_bars[:n_ph] = ph_indices
    piv_prices[:n_ph] = high_arr[ph_indices]
    piv_reacts[:n_ph] = ph_react[ph_indices]
    piv_extremes[:n_ph] = ph_extreme[ph_indices]
    piv_bars[n_ph:] = pl_indices
    piv_prices[n_ph:] = low_arr[pl_indices]
    piv_reacts[n_ph:] = pl_react[pl_indices]
    piv_extremes[n_ph:] = pl_extreme[pl_indices]
    sort_idx = np.argsort(piv_bars)
    return piv_bars[sort_idx], piv_prices[sort_idx], piv_reacts[sort_idx], piv_extremes[sort_idx]


def _find_pivot_sr_numpy(
    piv_bars, piv_prices, piv_reacts, piv_extremes,
    current_bar, atr, current_close,
    sr_lookback, sr_merge_atr, sr_min_score, min_width_atr,
) -> Optional[Tuple[float, float]]:
    if atr <= 0.0 or np.isnan(atr):
        return None
    window_start = max(0, current_bar - sr_lookback)
    left_idx = np.searchsorted(piv_bars, window_start, side='left')
    right_idx = np.searchsorted(piv_bars, current_bar, side='left')
    if right_idx - left_idx < 2:
        return None

    w_prices = piv_prices[left_idx:right_idx]
    w_bars = piv_bars[left_idx:right_idx]
    w_reacts = piv_reacts[left_idx:right_idx]
    w_extremes = piv_extremes[left_idx:right_idx]
    sort_idx = np.argsort(w_prices)
    s_prices = w_prices[sort_idx]
    s_bars = w_bars[sort_idx]
    s_reacts = w_reacts[sort_idx]
    s_extremes = w_extremes[sort_idx]

    merge_dist = sr_merge_atr * atr
    n_piv = len(s_prices)
    max_clusters = n_piv
    clu_centers = np.empty(max_clusters, dtype=np.float64)
    clu_counts = np.empty(max_clusters, dtype=np.int64)
    clu_ids = np.empty(n_piv, dtype=np.int64)
    n_clusters = 0

    for i in range(n_piv):
        px = s_prices[i]
        best_ci = -1
        best_gap = merge_dist + 1.0
        for ci in range(n_clusters):
            gap = abs(px - clu_centers[ci])
            if gap <= merge_dist and gap < best_gap:
                best_gap = gap
                best_ci = ci
        if best_ci < 0:
            clu_centers[n_clusters] = px
            clu_counts[n_clusters] = 1
            clu_ids[i] = n_clusters
            n_clusters += 1
        else:
            cnt = clu_counts[best_ci]
            clu_centers[best_ci] = (clu_centers[best_ci] * cnt + px) / (cnt + 1)
            clu_counts[best_ci] = cnt + 1
            clu_ids[i] = best_ci

    CAP_TOUCH = 60.0
    CAP_REACT = 50.0
    CAP_RECENT = 40.0
    CAP_COMPACT = 40.0
    CAP_EXTREME = 40.0
    recency_decay = max(6.0, sr_lookback / 3.0)

    best_res_center = 0.0
    best_res_dist_val = float('inf')
    found_res = False
    best_sup_center = 0.0
    best_sup_dist_val = float('inf')
    found_sup = False

    for cid in range(n_clusters):
        mask = clu_ids == cid
        c_prices = s_prices[mask]
        c_bars = s_bars[mask]
        c_reacts = s_reacts[mask]
        c_extremes = s_extremes[mask]
        c_size = len(c_prices)
        if c_size == 0:
            continue

        c_min = c_prices.min()
        c_max = c_prices.max()
        center = (c_min + c_max) / 2.0

        score_touch = min(CAP_TOUCH, c_size / 4.0 * CAP_TOUCH)
        newest_bar = c_bars.max()
        min_age = float(current_bar - newest_bar)
        score_recent = min(CAP_RECENT, CAP_RECENT * math.exp(-min_age / recency_decay))
        spread = c_max - c_min
        width_ratio = spread / merge_dist if merge_dist > 0 else 0.0
        compact = max(0.0, 1.0 - min(1.0, width_ratio / 2.5))
        score_compact = compact * CAP_COMPACT
        reaction_avg = c_reacts.mean() / max(atr, 1e-10)
        score_react = min(CAP_REACT, reaction_avg / 1.2 * CAP_REACT)
        score_extreme = CAP_EXTREME if c_extremes.any() else 0.0

        total_score = score_touch + score_react + score_recent + score_compact + score_extreme
        if total_score < sr_min_score:
            continue

        if center > current_close:
            dist = center - current_close
            if dist < best_res_dist_val:
                best_res_dist_val = dist
                best_res_center = center
                found_res = True
        elif center < current_close:
            dist = current_close - center
            if dist < best_sup_dist_val:
                best_sup_dist_val = dist
                best_sup_center = center
                found_sup = True

    if not found_res or not found_sup:
        return None
    if best_res_center - best_sup_center < min_width_atr * atr:
        return None
    return (best_res_center, best_sup_center)


if HAS_NUMBA:
    @njit(cache=True)
    def _find_sr_numba(
        piv_bars, piv_prices, piv_reacts, piv_extremes,
        current_bar, atr, current_close,
        sr_lookback, sr_merge_atr, sr_min_score, min_width_atr
    ):
        if atr <= 0.0:
            return (False, 0.0, 0.0)
        window_start = max(0, current_bar - sr_lookback)
        merge_dist = sr_merge_atr * atr
        lo, hi = 0, len(piv_bars)
        while lo < hi:
            mid = (lo + hi) // 2
            if piv_bars[mid] < window_start:
                lo = mid + 1
            else:
                hi = mid
        left_idx = lo
        lo, hi = left_idx, len(piv_bars)
        while lo < hi:
            mid = (lo + hi) // 2
            if piv_bars[mid] < current_bar:
                lo = mid + 1
            else:
                hi = mid
        right_idx = lo
        n_piv = right_idx - left_idx
        if n_piv < 2:
            return (False, 0.0, 0.0)
        idx_arr = np.empty(n_piv, dtype=np.int64)
        for i in range(n_piv):
            idx_arr[i] = left_idx + i
        for i in range(1, n_piv):
            key = idx_arr[i]
            key_price = piv_prices[key]
            j = i - 1
            while j >= 0 and piv_prices[idx_arr[j]] > key_price:
                idx_arr[j + 1] = idx_arr[j]
                j -= 1
            idx_arr[j + 1] = key
        clu_centers = np.empty(n_piv, dtype=np.float64)
        clu_counts = np.empty(n_piv, dtype=np.int64)
        clu_ids = np.empty(n_piv, dtype=np.int64)
        n_clusters = 0
        for i in range(n_piv):
            px = piv_prices[idx_arr[i]]
            best_ci = -1
            best_gap = merge_dist + 1.0
            for ci in range(n_clusters):
                gap = abs(px - clu_centers[ci])
                if gap <= merge_dist and gap < best_gap:
                    best_gap = gap
                    best_ci = ci
            if best_ci < 0:
                clu_centers[n_clusters] = px
                clu_counts[n_clusters] = 1
                clu_ids[i] = n_clusters
                n_clusters += 1
            else:
                cnt = clu_counts[best_ci]
                clu_centers[best_ci] = (clu_centers[best_ci] * cnt + px) / (cnt + 1)
                clu_counts[best_ci] = cnt + 1
                clu_ids[i] = best_ci
        CAP_TOUCH = 60.0
        CAP_REACT = 50.0
        CAP_RECENT = 40.0
        CAP_COMPACT = 40.0
        CAP_EXTREME = 40.0
        recency_decay = max(6.0, sr_lookback / 3.0)
        best_res_center = 0.0
        best_res_dist = 1e18
        found_res = False
        best_sup_center = 0.0
        best_sup_dist = 1e18
        found_sup = False
        for cid in range(n_clusters):
            c_min = 1e18
            c_max = -1e18
            c_count = 0
            react_sum = 0.0
            newest_bar = -1
            has_extreme = False
            for i2 in range(n_piv):
                if clu_ids[i2] == cid:
                    oi = idx_arr[i2]
                    p = piv_prices[oi]
                    if p < c_min:
                        c_min = p
                    if p > c_max:
                        c_max = p
                    c_count += 1
                    react_sum += piv_reacts[oi]
                    b = piv_bars[oi]
                    if b > newest_bar:
                        newest_bar = b
                    if piv_extremes[oi]:
                        has_extreme = True
            if c_count == 0:
                continue
            center = (c_min + c_max) / 2.0
            score_touch = min(CAP_TOUCH, c_count / 4.0 * CAP_TOUCH)
            min_age = float(current_bar - newest_bar)
            score_recent = min(CAP_RECENT, CAP_RECENT * math.exp(-min_age / recency_decay))
            spread = c_max - c_min
            width_ratio = spread / merge_dist if merge_dist > 0 else 0.0
            compact_val = max(0.0, 1.0 - min(1.0, width_ratio / 2.5))
            score_compact = compact_val * CAP_COMPACT
            reaction_avg = (react_sum / c_count) / max(atr, 1e-10)
            score_react = min(CAP_REACT, reaction_avg / 1.2 * CAP_REACT)
            score_extreme = CAP_EXTREME if has_extreme else 0.0
            total = score_touch + score_react + score_recent + score_compact + score_extreme
            if total < sr_min_score:
                continue
            if center > current_close:
                d = center - current_close
                if d < best_res_dist:
                    best_res_dist = d
                    best_res_center = center
                    found_res = True
            elif center < current_close:
                d = current_close - center
                if d < best_sup_dist:
                    best_sup_dist = d
                    best_sup_center = center
                    found_sup = True
        if not found_res or not found_sup:
            return (False, 0.0, 0.0)
        if best_res_center - best_sup_center < min_width_atr * atr:
            return (False, 0.0, 0.0)
        return (True, best_res_center, best_sup_center)

    @njit(cache=True)
    def _main_loop_numba(
        close_arr, atr_arr, n,
        piv_bars, piv_prices, piv_reacts, piv_extremes,
        sr_lookback, sr_merge_atr, sr_min_score, min_width_atr,
        offset_pct, breakout_atr
    ):
        out_active = np.zeros(n, dtype=np.bool_)
        out_high = np.full(n, np.nan)
        out_low = np.full(n, np.nan)
        out_width = np.full(n, np.nan)
        out_buy = np.full(n, np.nan)
        out_sell = np.full(n, np.nan)
        range_active = False
        range_high_val = 0.0
        range_low_val = 0.0
        start_bar = 50
        for i in range(start_bar, n):
            if range_active:
                if close_arr[i] > range_high_val + breakout_atr * atr_arr[i]:
                    range_active = False
                elif close_arr[i] < range_low_val - breakout_atr * atr_arr[i]:
                    range_active = False
                if range_active:
                    width = range_high_val - range_low_val
                    out_active[i] = True
                    out_high[i] = range_high_val
                    out_low[i] = range_low_val
                    out_width[i] = width
                    out_buy[i] = range_low_val + width * offset_pct
                    out_sell[i] = range_high_val - width * offset_pct
                    continue
            found, res_c, sup_c = _find_sr_numba(
                piv_bars, piv_prices, piv_reacts, piv_extremes,
                i, atr_arr[i], close_arr[i],
                sr_lookback, sr_merge_atr, sr_min_score, min_width_atr
            )
            if found:
                range_high_val = res_c
                range_low_val = sup_c
                range_active = True
                width = range_high_val - range_low_val
                out_active[i] = True
                out_high[i] = range_high_val
                out_low[i] = range_low_val
                out_width[i] = width
                out_buy[i] = range_low_val + width * offset_pct
                out_sell[i] = range_high_val - width * offset_pct
        return out_active, out_high, out_low, out_width, out_buy, out_sell


class StrategyRangeScalperOpt(BaseStrategy):
    """震荡高抛低吸策略（Pivot 聚类 + 多维评分法）。V7: 向量化 + numba JIT。"""

    def __init__(self, params: dict) -> None:
        config = StrategyConfig(
            name="range_scalper_opt",
            take_profit=0.02,
            stop_loss=0.02,
            direction="both",
        )
        super().__init__(config)
        self.params = params

    def generate_signals(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        if "atr" not in df.columns:
            raise KeyError("缺少 'atr' 列，请先调用 compute_indicators()")

        SR_LOOKBACK = 500
        SR_MERGE_ATR = float(p.get("SR_MERGE_ATR", 0.48))
        SR_MIN_SCORE = float(p.get("SR_MIN_SCORE", 70.0))
        MIN_WIDTH_ATR = float(p.get("MIN_WIDTH_ATR", 1.0))
        OFFSET_PCT = float(p.get("OFFSET_PCT", 0.15))
        BREAKOUT_ATR = float(p.get("BREAKOUT_ATR", 0.3))

        out = df.copy()
        n = len(out)
        high_arr = out["high"].to_numpy(dtype=np.float64)
        low_arr = out["low"].to_numpy(dtype=np.float64)
        close_arr = out["close"].to_numpy(dtype=np.float64)
        atr_arr = out["atr"].to_numpy(dtype=np.float64)

        piv_bars, piv_prices, piv_reacts, piv_extremes = _precompute_pivots_vectorized(
            high_arr, low_arr, n, SR_LOOKBACK
        )

        if HAS_NUMBA and len(piv_bars) > 0:
            out_active, out_high, out_low, out_width, out_buy, out_sell = _main_loop_numba(
                close_arr, atr_arr, n,
                piv_bars.astype(np.int64), piv_prices.astype(np.float64),
                piv_reacts.astype(np.float64), piv_extremes.astype(np.bool_),
                sr_lookback=SR_LOOKBACK, sr_merge_atr=SR_MERGE_ATR,
                sr_min_score=SR_MIN_SCORE, min_width_atr=MIN_WIDTH_ATR,
                offset_pct=OFFSET_PCT, breakout_atr=BREAKOUT_ATR,
            )
        else:
            out_active = np.zeros(n, dtype=bool)
            out_high = np.full(n, np.nan)
            out_low = np.full(n, np.nan)
            out_width = np.full(n, np.nan)
            out_buy = np.full(n, np.nan)
            out_sell = np.full(n, np.nan)
            range_active = False
            range_high_val = 0.0
            range_low_val = 0.0
            start_bar = max(50, 2)
            for i in range(start_bar, n):
                if range_active:
                    if close_arr[i] > range_high_val + BREAKOUT_ATR * atr_arr[i]:
                        range_active = False
                    elif close_arr[i] < range_low_val - BREAKOUT_ATR * atr_arr[i]:
                        range_active = False
                    if range_active:
                        width = range_high_val - range_low_val
                        out_active[i] = True
                        out_high[i] = range_high_val
                        out_low[i] = range_low_val
                        out_width[i] = width
                        out_buy[i] = range_low_val + width * OFFSET_PCT
                        out_sell[i] = range_high_val - width * OFFSET_PCT
                        continue
                result = _find_pivot_sr_numpy(
                    piv_bars, piv_prices, piv_reacts, piv_extremes,
                    i, atr_arr[i], close_arr[i],
                    SR_LOOKBACK, SR_MERGE_ATR, SR_MIN_SCORE, MIN_WIDTH_ATR,
                )
                if result is not None:
                    range_high_val, range_low_val = result
                    range_active = True
                    width = range_high_val - range_low_val
                    out_active[i] = True
                    out_high[i] = range_high_val
                    out_low[i] = range_low_val
                    out_width[i] = width
                    out_buy[i] = range_low_val + width * OFFSET_PCT
                    out_sell[i] = range_high_val - width * OFFSET_PCT

        out["range_active"] = out_active
        out["range_high"] = out_high
        out["range_low"] = out_low
        out["range_width"] = out_width
        out["limit_buy_price"] = out_buy
        out["limit_sell_price"] = out_sell
        out = self._apply_filters(out)
        return out

    def _apply_filters(self, df: pd.DataFrame) -> pd.DataFrame:
        p = self.params
        if p.get("enable_volatility_filter", True):
            atr_ma50 = df["atr"].rolling(50, min_periods=10).mean()
            atr_ratio = df["atr"] / atr_ma50.replace(0, np.nan)
            lo = float(p.get("atr_ratio_low", 0.3))
            hi = float(p.get("atr_ratio_high", 1.5))
            vol_ok = (atr_ratio >= lo) & (atr_ratio <= hi)
        else:
            vol_ok = True

        if p.get("enable_narrow_range_filter", True):
            min_mult = float(p.get("MIN_ATR_MULT", p.get("min_atr_mult", 1.0)))
            width_ok = df["range_width"] >= df["atr"] * min_mult
        else:
            width_ok = True

        if p.get("enable_ema_trend_filter", True):
            trend_period = int(p.get("trend_ema_period", p.get("ema_period", 100)))
            trend_window = int(p.get("slope_window", 20))
            threshold = float(p.get("trend_threshold", p.get("slope_max", 0.05)))
            trend_col = f"ema{trend_period}"
            if trend_col not in df.columns:
                df[trend_col] = df["close"].ewm(span=trend_period, adjust=False).mean()
            trend_shifted = df[trend_col].shift(trend_window)
            trend_slope = (df[trend_col] - trend_shifted) / trend_shifted * 100
            uptrend = trend_slope > threshold
            downtrend = trend_slope < -threshold
            dir_long = uptrend | (~uptrend & ~downtrend)
            dir_short = downtrend | (~uptrend & ~downtrend)
        else:
            dir_long = True
            dir_short = True

        mask = df["range_active"] & vol_ok & width_ok

        if p.get("enable_rsi_filter", True):
            rsi_period = int(p.get("rsi_period", 14))
            rsi_lo = float(p.get("rsi_neutral_lo", 35))
            rsi_hi = float(p.get("rsi_neutral_hi", 65))
            delta = df["close"].diff()
            gain = delta.clip(lower=0)
            loss = -delta.clip(upper=0)
            avg_gain = gain.ewm(com=rsi_period - 1, min_periods=rsi_period, adjust=False).mean()
            avg_loss = loss.ewm(com=rsi_period - 1, min_periods=rsi_period, adjust=False).mean()
            rs = avg_gain / avg_loss.replace(0, np.nan)
            rsi = (100 - 100 / (1 + rs)).fillna(50.0)
            rsi_ok = (rsi >= rsi_lo) & (rsi <= rsi_hi)
        else:
            rsi_ok = True

        df["limit_buy_price"] = df["limit_buy_price"].where(mask & dir_long & rsi_ok, np.nan)
        df["limit_sell_price"] = df["limit_sell_price"].where(mask & dir_short & rsi_ok, np.nan)
        return df
