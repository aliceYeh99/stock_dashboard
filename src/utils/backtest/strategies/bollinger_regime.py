"""
utils/backtest/strategies/bollinger_regime.py

布林通道 + 趨勢regime判斷（混合策略）：
    先用長天期均線判斷目前是「多頭 regime」還是「空頭/盤整 regime」：
        收盤價 > regime_period 日均線 → 多頭 regime → 用突破邏輯（追突破上軌、跌破中軌出場）
        收盤價 < regime_period 日均線 → 空頭/盤整 regime → 用均值回歸邏輯（買下軌、賣中軌）

    這是想解決 range_trading 遇到的問題：
    同一套規則不分趨勢/盤整環境硬套，容易在趨勢盤裡買在假支撐。
    這支策略先判斷環境，再決定要用哪一種邏輯。
"""
import numpy as np
import pandas as pd


def signal(
    df: pd.DataFrame,
    period: int = 20,
    num_std: float = 2.0,
    regime_period: int = 100,
) -> pd.Series:
    ma = df["close"].rolling(period).mean()
    std = df["close"].rolling(period).std()
    upper = ma + num_std * std
    lower = ma - num_std * std
    long_ma = df["close"].rolling(regime_period).mean()

    close = df["close"]
    position = pd.Series(0, index=df.index, dtype=int)
    holding = False

    for i in range(len(df)):
        c = close.iloc[i]
        u, lo, m, lm = upper.iloc[i], lower.iloc[i], ma.iloc[i], long_ma.iloc[i]

        if np.isnan(u) or np.isnan(lo) or np.isnan(lm):
            position.iloc[i] = int(holding)
            continue

        is_bull_regime = c > lm

        if is_bull_regime:
            # 多頭 regime：突破追買，跌破中軌出場
            if not holding and c > u:
                holding = True
            elif holding and c < m:
                holding = False
        else:
            # 盤整/空頭 regime：均值回歸
            if not holding and c <= lo:
                holding = True
            elif holding and c >= m:
                holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "布林通道 Regime 混合",
    "params": {
        "period": 20,
        "num_std": 2.0,
        "regime_period": 100,
    },
}