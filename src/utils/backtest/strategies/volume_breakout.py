"""
utils/backtest/strategies/volume_breakout.py

帶量突破：

1. 股價突破前 N 日最高價
2. 成交量 > 平均成交量 × volume_ratio

→ 持有

跌破前 N 日低點
→ 出場
"""

import pandas as pd


def signal(
    df: pd.DataFrame,
    lookback: int = 20,
    volume_period: int = 20,
    volume_ratio: float = 2.0,
) -> pd.Series:

    previous_high = (
        df["high"]
        .rolling(lookback)
        .max()
        .shift(1)
    )

    previous_low = (
        df["low"]
        .rolling(lookback)
        .min()
        .shift(1)
    )

    avg_volume = (
        df["volume"]
        .rolling(volume_period)
        .mean()
    )

    buy = (
        (df["close"] > previous_high) &
        (df["volume"] > avg_volume * volume_ratio)
    )

    sell = df["close"] < previous_low

    position = pd.Series(0, index=df.index)

    holding = False

    for i in range(len(df)):
        if buy.iloc[i]:
            holding = True
        elif sell.iloc[i]:
            holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "帶量突破",
    "params": {
        "lookback": 20,
        "volume_period": 20,
        "volume_ratio": 2.0,
    },
}
