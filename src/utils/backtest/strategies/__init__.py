"""
utils/backtest/strategies/__init__.py

策略註冊表。

之後要加新策略（例如 rsi、季線+MACD...），流程固定：
    1. 新增 utils/backtest/strategies/xxx.py
       裡面要有 signal(df, **params) 跟 META = {"name":..., "params": {...}}
    2. 在下面 import 該模組，並加進 STRATEGY_MAP 一行

pages/8_回測.py 完全不用改，選單跟參數欄位都是自動長出來的。
"""
from . import macd, half_year, quarter, year, month, buy_and_hold, high_breakout,volume_breakout,pull_wave, elliott_wave, swing_hold

STRATEGY_MAP = {
    "buy_and_hold": buy_and_hold,
    "month": month,
    "macd": macd,
    "half_year": half_year,
    "year": year,
    "quarter": quarter,
    "volume_breakout": volume_breakout,
    "swing_hold": swing_hold,
    "elliott_wave": elliott_wave
}

不行的 ={
    "high_breakout": high_breakout,
    "pull_wave": pull_wave,

}


def get_strategy(name: str):
    module = STRATEGY_MAP.get(name)
    if module is None:
        raise ValueError(f"未知策略：{name}，可用策略：{list(STRATEGY_MAP.keys())}")
    return module
