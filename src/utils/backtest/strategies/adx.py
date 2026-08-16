"""
utils/backtest/strategies/adx.py

ADX 趨勢強度策略（Wilder's ADX，趨勢跟隨）：
    ADX > threshold（趨勢夠強）且 +DI > -DI（多方主導） → 持有 (1)
    其餘情況（趨勢不夠強，或空方主導）→ 出場 (0)

跟 SMA / MACD 不同之處：
    ADX 本身不判斷方向，只判斷「有沒有趨勢」，方向要靠 +DI / -DI 判斷。
    這支策略的精神是「先確認真的有趨勢，才跟」，避免盤整時被雜訊打來打去。
"""
import numpy as np
import pandas as pd


def signal(df: pd.DataFrame, period: int = 14, threshold: float = 25) -> pd.Series:
    high, low, close = df["high"], df["low"], df["close"]
    prev_close = close.shift(1)

    up_move = high.diff()
    down_move = -low.diff()

    plus_dm = pd.Series(
        np.where((up_move > down_move) & (up_move > 0), up_move, 0.0),
        index=df.index,
    )
    minus_dm = pd.Series(
        np.where((down_move > up_move) & (down_move > 0), down_move, 0.0),
        index=df.index,
    )

    tr = pd.concat(
        [
            high - low,
            (high - prev_close).abs(),
            (low - prev_close).abs(),
        ],
        axis=1,
    ).max(axis=1)

    atr = tr.ewm(alpha=1 / period, adjust=False).mean()
    plus_di = 100 * plus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr
    minus_di = 100 * minus_dm.ewm(alpha=1 / period, adjust=False).mean() / atr

    dx = 100 * (plus_di - minus_di).abs() / (plus_di + minus_di)
    adx = dx.ewm(alpha=1 / period, adjust=False).mean()

    return ((adx > threshold) & (plus_di > minus_di)).astype(int)


META = {
    "name": "ADX 趨勢強度",
    "params": {
        "period": 14,
        "threshold": 25,
    },
}