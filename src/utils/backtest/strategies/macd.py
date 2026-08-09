"""
utils/backtest/strategies/macd.py

MACD 交叉策略（趨勢跟隨）：
    MACD 線 > 訊號線 → 持有 (1)
    MACD 線 < 訊號線 → 出場 (0)

規則：每個策略都要有
    signal(df, **params) -> pd.Series (0/1)
    META = {"name": ..., "params": {...}}
這樣 pages/8_回測.py 才能自動列出策略、自動長出參數輸入欄位。
"""
import pandas as pd


def signal(df: pd.DataFrame, fast: int = 12, slow: int = 26, signal_period: int = 9) -> pd.Series:
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    return (macd_line > signal_line).astype(int)


META = {
    "name": "MACD 交叉",
    "params": {
        "fast": 12,
        "slow": 26,
        "signal_period": 9,
    },
}
