"""数据加载：CSV 读取 + Bybit API 下载 + 指标预计算。"""
import os
import time
import hashlib
import hmac
import json
from datetime import datetime, timedelta
from typing import Optional

import numpy as np
import pandas as pd
import requests

# 列名映射
_COLUMN_MAP = {
    "time": "time",
    "datetime": "datetime",
    "Datetime": "datetime",
    "open": "open",
    "Open": "open",
    "high": "high",
    "High": "high",
    "low": "low",
    "Low": "low",
    "close": "close",
    "Close": "close",
    "volume": "volume",
    "Volume": "volume",
}

BYBIT_BASE = "https://api.bybit.com"
OKX_BASE = "https://www.okx.com"


def _bybit_request(endpoint: str, api_key: str, api_secret: str,
                   params: Optional[dict] = None) -> dict:
    """发送 Bybit v5 API 签名请求。"""
    if params is None:
        params = {}
    timestamp = str(int(time.time() * 1000))
    params["api_key"] = api_key
    params["timestamp"] = timestamp

    # 按 key 排序
    sorted_keys = sorted(params.keys())
    query_string = "&".join(f"{k}={params[k]}" for k in sorted_keys)
    signature = hmac.new(
        api_secret.encode("utf-8"),
        query_string.encode("utf-8"),
        hashlib.sha256
    ).hexdigest()
    params["sign"] = signature

    url = f"{BYBIT_BASE}{endpoint}"
    resp = requests.get(url, params=params, timeout=30)
    data = resp.json()
    if data.get("retCode") != 0:
        raise RuntimeError(f"Bybit API 错误: {data.get('retMsg', 'unknown')}")
    return data


def download_bybit_kline(
    symbol: str = "BTCUSDT",
    interval: str = "5",
    days: int = 90,
    api_key: Optional[str] = None,
    api_secret: Optional[str] = None,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    从 Bybit 下载永续合约 K 线数据。

    symbol:  交易对，如 BTCUSDT
    interval: K 线周期（分钟），如 5/15/60/240/D
    days:    回看天数
    api_key/api_secret: Bybit API 凭证（可选，有则用签名请求）
    cache_dir: 缓存目录（可选，有则缓存下载数据）
    """
    category = "linear"
    limit = 200  # Bybit 单次最大
    interval_min = int(interval)

    end_time = int(time.time() * 1000)
    start_time = end_time - days * 24 * 3600 * 1000

    all_rows = []
    current_end = end_time

    params = {
        "category": category,
        "symbol": symbol,
        "interval": interval,
        "limit": limit,
    }

    def _do_request(p):
        if api_key and api_secret:
            return _bybit_request("/v5/market/kline", api_key, api_secret, p)
        else:
            # 公开接口不需要签名
            url = f"{BYBIT_BASE}/v5/market/kline"
            resp = requests.get(url, params=p, timeout=30)
            data = resp.json()
            if data.get("retCode") != 0:
                raise RuntimeError(f"Bybit API 错误: {data.get('retMsg', 'unknown')}")
            return data

    while current_end > start_time:
        req_params = dict(params)
        req_params["end"] = current_end
        req_params["start"] = start_time
        data = _do_request(req_params)
        klines = data["result"]["list"]
        if not klines:
            break
        all_rows.extend(klines)
        # 取最早一根的时间戳作为下一批的 end
        earliest_ts = int(klines[-1][0])
        if earliest_ts <= start_time:
            break
        current_end = earliest_ts  # int conversion for next batch
        time.sleep(0.15)  # 温和限速

    if not all_rows:
        raise ValueError(f"未获取到 {symbol} 的 K 线数据")

    # 解析
    rows = []
    for k in all_rows:
        ts = int(k[0])
        rows.append({
            "datetime": pd.to_datetime(ts, unit="ms", utc=True),
            "open": float(k[1]),
            "high": float(k[2]),
            "low": float(k[3]),
            "close": float(k[4]),
            "volume": float(k[5]),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df.drop_duplicates(subset="datetime", keep="last").reset_index(drop=True)

    # 缓存
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        cache_file = os.path.join(
            cache_dir,
            f"{symbol}_{interval}_{days}d_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        df.to_csv(cache_file, index=False, encoding="utf-8-sig")
        print(f"[数据已缓存] {cache_file}")

    print(f"[数据下载完成] {symbol} {interval}m, {days}天, {len(df)} 根 K 线")
    return df


def download_okx_kline(
    symbol: str = "BTC-USDT-SWAP",
    bar: str = "5m",
    days: int = 90,
    cache_dir: Optional[str] = None,
) -> pd.DataFrame:
    """
    从 OKX 公开 API 下载永续合约 K 线数据（无需 API Key）。

    symbol:  产品ID，如 BTC-USDT-SWAP, ETH-USDT-SWAP, SOL-USDT-SWAP
    bar:     K 线周期，如 5m/15m/1H/4H/1D
    days:    回看天数
    cache_dir: 缓存目录（可选）
    """
    limit = 100  # OKX 单次最大
    bar_minutes = _bar_to_minutes(bar)
    total_candles_needed = int(days * 24 * 60 / bar_minutes)

    end_ts = int(time.time() * 1000)
    start_ts = end_ts - days * 24 * 3600 * 1000

    all_candles = []
    page_count = 0
    current_before = ""  # 首次不传 before，取最新数据

    while True:
        params = {
            "instId": symbol,
            "bar": bar,
            "limit": str(limit),
        }
        if current_before:
            params["before"] = current_before

        url = f"{OKX_BASE}/api/v5/market/candles"
        resp = requests.get(url, params=params, timeout=30)
        data = resp.json()

        if data.get("code") != "0":
            raise RuntimeError(f"OKX API 错误: {data.get('msg', 'unknown')}")

        candles = data.get("data", [])
        if not candles:
            break

        all_candles.extend(candles)
        page_count += 1

        # 检查是否已覆盖足够时间范围
        oldest_ts = int(candles[-1][0])
        if oldest_ts <= start_ts:
            break

        # 用最旧一根的时间戳减1ms作为下批的 before（避免包含已获取的K线）
        current_before = str(oldest_ts - 1)

        # 进度提示
        if page_count % 5 == 0 or len(all_candles) <= 100:
            oldest_dt = pd.to_datetime(oldest_ts, unit="ms", utc=True)
            print(f"  [OKX] 第 {page_count} 页, 累计 {len(all_candles)} 根, 最旧: {oldest_dt}")

        time.sleep(0.12)  # OKX 公开接口限速: 20 req/2s ≈ 0.1s/req

    if not all_candles:
        raise ValueError(f"未获取到 {symbol} 的 K 线数据")

    # 解析: OKX 返回 [ts, o, h, l, c, vol, volCcy, volCcyQuote, confirm]
    rows = []
    for c in all_candles:
        ts = int(c[0])
        rows.append({
            "datetime": pd.to_datetime(ts, unit="ms", utc=True),
            "open": float(c[1]),
            "high": float(c[2]),
            "low": float(c[3]),
            "close": float(c[4]),
            "volume": float(c[5]),
        })

    df = pd.DataFrame(rows)
    df = df.sort_values("datetime").reset_index(drop=True)
    df = df.drop_duplicates(subset="datetime", keep="last").reset_index(drop=True)

    # 缓存
    if cache_dir:
        os.makedirs(cache_dir, exist_ok=True)
        safe_name = symbol.replace("-", "_").replace("/", "_")
        cache_file = os.path.join(
            cache_dir,
            f"{safe_name}_{bar}_{days}d_{datetime.now().strftime('%Y%m%d')}.csv"
        )
        df.to_csv(cache_file, index=False, encoding="utf-8-sig")
        print(f"[数据已缓存] {cache_file}")

    print(f"[OKX 数据下载完成] {symbol} {bar}, {days}天, {len(df)} 根 K 线")
    print(f"  时间范围: {df['datetime'].iloc[0]} ~ {df['datetime'].iloc[-1]}")
    return df


def _bar_to_minutes(bar: str) -> int:
    """将 OKX bar 格式转为分钟数。"""
    bar_upper = bar.upper()
    if bar_upper.endswith("M"):
        return int(bar_upper[:-1])
    elif bar_upper.endswith("H"):
        return int(bar_upper[:-1]) * 60
    elif bar_upper.endswith("D"):
        return int(bar_upper[:-1]) * 1440
    elif bar_upper.endswith("W"):
        return int(bar_upper[:-1]) * 10080
    else:
        # 纯数字，默认分钟
        try:
            return int(bar_upper)
        except ValueError:
            raise ValueError(f"无法解析 bar 格式: {bar}")


def load_csv(filepath: str) -> pd.DataFrame:
    """读取 CSV 文件，兼容多种列名格式。"""
    if not os.path.exists(filepath):
        raise FileNotFoundError(f"文件不存在：{filepath}")

    df = pd.read_csv(filepath, encoding="utf-8")

    col_map = {}
    for c in df.columns:
        if c.strip() in _COLUMN_MAP:
            col_map[c] = _COLUMN_MAP[c.strip()]
    df = df.rename(columns=col_map)

    required = {"open", "high", "low", "close"}
    has_time = "datetime" in df.columns
    has_unix = "time" in df.columns
    if not has_time and not has_unix:
        raise ValueError("CSV 缺少时间列（需要 Datetime/time/datetime）")
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"CSV 缺少必要列：{sorted(missing)}")

    if has_time:
        df["datetime"] = pd.to_datetime(df["datetime"], utc=True)
    elif has_unix:
        df["datetime"] = pd.to_datetime(df["time"], unit="s", utc=True)

    if "volume" not in df.columns:
        df["volume"] = 0

    df = df[["datetime", "open", "high", "low", "close", "volume"]].copy()
    df = df.reset_index(drop=True)
    return df


def compute_indicators(df: pd.DataFrame) -> pd.DataFrame:
    """计算震荡策略所需指标。"""
    df = df.copy()
    df["ema20"] = df["close"].ewm(span=20, adjust=False).mean()
    df["ema60"] = df["close"].ewm(span=60, adjust=False).mean()
    df["ema120"] = df["close"].ewm(span=120, adjust=False).mean()
    df["ema360"] = df["close"].ewm(span=360, adjust=False).mean()
    df["atr"] = _compute_atr(df, period=14)
    df["hour"] = df["datetime"].dt.hour
    df["day_of_week"] = df["datetime"].dt.dayofweek

    WARMUP = 360
    if len(df) > WARMUP:
        df = df.iloc[WARMUP:].reset_index(drop=True)
    return df


def _compute_atr(df: pd.DataFrame, period: int = 14) -> pd.Series:
    high = df["high"]
    low = df["low"]
    prev_close = df["close"].shift(1)
    tr = pd.concat([
        high - low,
        (high - prev_close).abs(),
        (low - prev_close).abs(),
    ], axis=1).max(axis=1)
    return tr.ewm(span=period, adjust=False).mean()
