"""
utils/backtest/strategies/half_year.py

半年線（120日）均線支撐 + MACD 轉強，買入並持有策略。

注意：這是「買入並持有」策略 —— 一旦訊號觸發過一次，就永遠持有，不會賣出。
engine.py 的規則是「訊號從 1 變回 0 才賣出」，但這支策略透過
common.py 裡的 cummax() 把訊號鎖住了，觸發後只會一直是 1，
所以自然不會有賣出動作，engine.py 完全不用改。

參數:
    tolerance      : 股價貼近均線的容忍區間。半年線波動較大，
                     建議放寬到 0.05~0.08（±5%~8%）
    cross_lookback : MACD 黃金交叉後，訊號有效的天數視窗。
                     3 天較嚴格、5 天（建議）、10 天較寬鬆


# 半年線（120MA）  因為波動比較大， tolerance 可以放到： 0.05 ~ 0.08
#  cross_lookback = 5 我不太會動 
# 我覺得 5 天滿合理  MACD 本來就不是很即時。很多人會抓：3 天（比較嚴格）
# 5 天（我比較推薦） 10 天（有點太鬆）
"""
import pandas as pd

from .common import ma_support_macd_signal


def signal(df: pd.DataFrame, tolerance: float = 0.08, cross_lookback: int = 5) -> pd.Series:
    return ma_support_macd_signal(
        df,
        ma_period=120,
        tolerance=tolerance,
        cross_lookback=cross_lookback,
    )


META = {
    "name": "半年線支撐 + MACD 轉強（買入持有）",
    "params": {
        "tolerance": 0.08,
        "cross_lookback": 5,
    },
}
