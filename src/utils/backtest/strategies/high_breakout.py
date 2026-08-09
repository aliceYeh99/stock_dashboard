
"""
utils/backtest/strategies/high_breakout.py

前高突破策略：

今日收盤價突破前 N 日最高價
→ 持有

跌破前 N 日最低價
→ 出場
"""

import pandas as pd


def signal(
    df: pd.DataFrame,
    lookback: int = 20,
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

    buy = df["close"] > previous_high
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
    "name": "前高突破",
    "params": {
        "lookback": 20,
    },
}

