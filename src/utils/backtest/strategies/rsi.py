"""
utils/backtest/strategies/rsi.py

RSI 超買超賣策略（均值回歸）：
    RSI <= buy_threshold  → 買進（超賣）
    RSI >= sell_threshold → 出場（超買）
"""
import numpy as np
import pandas as pd


def signal(
    df: pd.DataFrame,
    period: int = 14,
    buy_threshold: float = 30,
    sell_threshold: float = 70,
) -> pd.Series:
    delta = df["close"].diff()
    gain = delta.clip(lower=0)
    loss = -delta.clip(upper=0)

    avg_gain = gain.rolling(period).mean()
    avg_loss = loss.rolling(period).mean()

    rs = avg_gain / avg_loss
    rsi = 100 - (100 / (1 + rs))

    position = pd.Series(0, index=df.index, dtype=int)
    holding = False

    for i in range(len(df)):
        r = rsi.iloc[i]
        if np.isnan(r):
            position.iloc[i] = int(holding)
            continue

        if not holding and r <= buy_threshold:
            holding = True
        elif holding and r >= sell_threshold:
            holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "RSI 超買超賣",
    "params": {
        "period": 14,
        "buy_threshold": 30,
        "sell_threshold": 70,
    },
}