"""
utils/backtest/strategies/donchian.py

Donchian 通道突破策略（海龜交易法則精神，趨勢跟隨）：
    收盤價突破 entry_period 日高點 → 買進
    收盤價跌破 exit_period 日低點  → 出場

進場與出場用不同週期（entry 較長、exit 較短），
是經典turtle做法：進場要更強的訊號確認，出場相對敏感、不戀棧。
"""
import numpy as np
import pandas as pd


def signal(df: pd.DataFrame, entry_period: int = 20, exit_period: int = 10) -> pd.Series:
    entry_high = df["high"].rolling(entry_period).max().shift(1)
    exit_low = df["low"].rolling(exit_period).min().shift(1)
    close = df["close"]

    position = pd.Series(0, index=df.index, dtype=int)
    holding = False

    for i in range(len(df)):
        eh, el, c = entry_high.iloc[i], exit_low.iloc[i], close.iloc[i]
        if np.isnan(eh) or np.isnan(el):
            position.iloc[i] = int(holding)
            continue

        if not holding and c > eh:
            holding = True
        elif holding and c < el:
            holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "Donchian 通道突破",
    "params": {
        "entry_period": 20,
        "exit_period": 10,
    },
}