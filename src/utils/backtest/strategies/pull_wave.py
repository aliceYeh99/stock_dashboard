"""
utils/backtest/strategies/pull_wave.py

拉一波策略：

找出股票開始進入一段上升波段的時機。

條件：
1. 短期均線 > 中期均線
2. 收盤價 > 短期均線
3. 短期均線正在上升
4. 成交量高於近期平均

符合條件 → 持有 (1)
否則 → 出場 (0)

規則：每個策略都要有
signal(df, **params) -> pd.Series (0/1)
META = {"name": ..., "params": {...}}
"""

import pandas as pd


def signal(
    df: pd.DataFrame,
    fast: int = 20,
    slow: int = 60,
    slope_period: int = 5,
    volume_period: int = 20,
    volume_ratio: float = 1.2,
) -> pd.Series:

    close = df["close"]

    # -------------------------
    # 均線
    # -------------------------
    ma_fast = close.rolling(fast).mean()
    ma_slow = close.rolling(slow).mean()

    # -------------------------
    # 1. 短均線 > 長均線
    # -------------------------
    trend_up = ma_fast > ma_slow

    # -------------------------
    # 2. 股價站在短均線上
    # -------------------------
    price_strong = close > ma_fast

    # -------------------------
    # 3. 短均線正在上升
    # -------------------------
    ma_rising = ma_fast > ma_fast.shift(slope_period)

    # -------------------------
    # 4. 成交量放大
    # -------------------------
    volume_ma = df["volume"].rolling(volume_period).mean()

    volume_strong = df["volume"] > volume_ma * volume_ratio

    # -------------------------
    # 四個條件同時成立
    # -------------------------
    signal = (
        trend_up
        & price_strong
        & ma_rising
        & volume_strong
    )

    return signal.astype(int)


META = {
    "name": "拉一波",
    "params": {
        "fast": 20,
        "slow": 60,
        "slope_period": 5,
        "volume_period": 20,
        "volume_ratio": 1.2,
    },
}