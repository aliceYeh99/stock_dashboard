"""
utils/backtest/strategies/buy_and_hold.py

單純買進持有（Buy and Hold）：
    不做任何判斷，只要有資料就持有 (1)。
    作為對照組，用來檢驗其他策略是不是真的比「什麼都不做、單純抱著」更好。

規則：每個策略都要有
    signal(df, **params) -> pd.Series (0/1)
    META = {"name": ..., "params": {...}}
"""
import pandas as pd


def signal(df: pd.DataFrame) -> pd.Series:
    # 全部填 1：只要有資料的那一天，就是「持有」狀態
    # engine.py 那邊會 shift(1)，所以實際上是第 2 天才會真的買進，
    # 跟其他策略的規則（T 日訊號、T+1 日開盤成交）保持一致，避免它有不公平的優勢
    return pd.Series(1, index=df.index)


META = {
    "name": "買進持有",
    "params": {},
}