"""
utils/backtest/strategies/bollinger.py

布林通道均值回歸策略：
    收盤價 <= 下軌 → 買進（視為超跌）
    收盤價 >= 中軌（均線）→ 出場（回歸即獲利了結）

跟 range_trading 的差異：
    區間邊界是「動態的均線 ± 標準差」，會隨波動率自動縮放，
    不是單純的近 N 日最高/最低價。
"""
import numpy as np
import pandas as pd


def signal(df: pd.DataFrame, period: int = 20, num_std: float = 2.0) -> pd.Series:
    ma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    lower = ma - num_std * std

    close = df["close"]
    position = pd.Series(0, index=df.index, dtype=int)
    holding = False

    for i in range(len(df)):
        m, lo, c = ma.iloc[i], lower.iloc[i], close.iloc[i]
        if np.isnan(m) or np.isnan(lo):
            position.iloc[i] = int(holding)
            continue

        if not holding and c <= lo:
            holding = True
        elif holding and c >= m:
            holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "布林通道均值回歸",
    "params": {
        "period": 20,
        "num_std": 2.0,
    },
}