"""
utils/backtest/strategies/sma.py

SMA 均線交叉策略（趨勢跟隨）：
    快線 > 慢線 → 持有 (1)
    快線 < 慢線 → 出場 (0)
"""
import pandas as pd


def signal(df: pd.DataFrame, fast: int = 20, slow: int = 60) -> pd.Series:
    sma_fast = df["close"].rolling(fast).mean()
    sma_slow = df["close"].rolling(slow).mean()
    return (sma_fast > sma_slow).astype(int)


META = {
    "name": "SMA 均線交叉",
    "params": {
        "fast": 20,
        "slow": 60,
    },
}