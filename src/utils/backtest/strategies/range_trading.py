"""
utils/backtest/strategies/range_trading.py

震盪區間來回做價差策略 (Range Trading):
    使用前 N 個交易日的高低點建立區間（shift(1)，避免 look-ahead bias）：
        接近區間下緣 → 買進
        接近區間上緣 → 賣出
    若收盤價向上突破區間最高價：
        停止依區間規則賣出，原本有持股則續抱，沒有持股則不追價買進
    若收盤價向下跌破區間最低價：
        第一版採保守處理，強制出場，且當天不產生新的 BUY 訊號
        （回到區間內後，即恢復正常區間交易判斷）

規則：每個策略都要有
    signal(df, **params) -> pd.Series (0/1)
    META = {"name": ..., "params": {...}}
"""
import numpy as np
import pandas as pd


def signal(
    df: pd.DataFrame,
    lookback: int = 20,
    entry_zone: float = 0.2,
    exit_zone: float = 0.2,
) -> pd.Series:
    # 前 N 日高低點，shift(1) 確保今天的決策只用得到「昨天以前」已知的資料
    rolling_high = df["high"].rolling(lookback).max().shift(1)
    rolling_low = df["low"].rolling(lookback).min().shift(1)
    range_width = rolling_high - rolling_low

    entry_price = rolling_low + range_width * entry_zone
    exit_price = rolling_high - range_width * exit_zone

    close = df["close"]

    position = pd.Series(0, index=df.index, dtype=int)

    holding = False

    for i in range(len(df)):
        rh = rolling_high.iloc[i]
        rl = rolling_low.iloc[i]
        ep = entry_price.iloc[i]
        xp = exit_price.iloc[i]
        c = close.iloc[i]

        # 前 N 天資料還沒湊滿，無法定義區間 → 不動作
        if np.isnan(rh) or np.isnan(rl):
            position.iloc[i] = int(holding)
            continue

        # 向下跌破：強制出場，當天不進場
        if c < rl:
            holding = False
            position.iloc[i] = 0
            continue

        # 向上突破：不再依區間規則賣出；原持股續抱，無持股不追價買進
        if c > rh:
            position.iloc[i] = int(holding)
            continue

        # 區間內：正常震盪交易判斷
        if not holding and c <= ep:
            holding = True
        elif holding and c >= xp:
            holding = False

        position.iloc[i] = int(holding)

    return position


META = {
    "name": "震盪區間來回做價差",
    "params": {
        "lookback": 20,
        "entry_zone": 0.2,
        "exit_zone": 0.2,
    },
}