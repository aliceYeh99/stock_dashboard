"""
utils/backtest/strategies/swing_hold.py

波段持有策略：

核心概念：
「儘量不空手，除非中期趨勢明顯轉弱。」

規則：
1. 股價在中期均線之上 → 持有
2. 股價跌破中期均線 → 出場
3. 短期回檔不賣
4. 不使用短期交叉，避免頻繁進出

signal(df, **params) -> pd.Series (0/1)

META = {
    "name": ...,
    "params": {...},
}
"""

import pandas as pd


def signal(
    df: pd.DataFrame,
    slow: int = 60,
    exit_buffer: float = 0.03,
) -> pd.Series:

    close = df["close"]

    # 中期均線
    ma_slow = close.rolling(slow).mean()

    # -------------------------
    # 趨勢沒有明顯破壞
    #
    # 只要價格還在均線附近，
    # 就繼續持有，不因小回檔出場。
    # -------------------------
    hold = close >= ma_slow * (1 - exit_buffer)

    return hold.astype(int)


META = {
    "name": "波段持有",
    "params": {
        "slow": 60,
        "exit_buffer": 0.03,
    },
}