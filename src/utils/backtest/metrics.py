"""
utils/backtest/metrics.py

從資金曲線算出常用績效指標。邏輯跟舊 multi_backtest.py 的 compute_metrics 一樣，
只多回傳一個 total_return 方便 UI 直接顯示。
"""
import numpy as np
import pandas as pd


def compute_metrics(equity: pd.Series, initial_value: float) -> dict:
    equity = equity.dropna()

    if len(equity) < 2:
        return {
            "total_return": 0,
            "cagr": 0,
            "sharpe": 0,
            "max_dd": 0,
            "final_equity": initial_value,
        }

    returns = equity.pct_change().dropna()
    total_return = equity.iloc[-1] / initial_value - 1

    years = (equity.index[-1] - equity.index[0]).days / 365.25
    if years >= 1:
        cagr = (1 + total_return) ** (1 / years) - 1
    else:
        cagr = total_return / years if years > 0 else 0

    sharpe = returns.mean() / returns.std() * np.sqrt(252) if returns.std() > 0 else 0
    max_dd = (equity / equity.cummax() - 1).min()

    return {
        "total_return": total_return,
        "cagr": cagr,
        "sharpe": sharpe,
        "max_dd": max_dd,
        "final_equity": equity.iloc[-1],
    }
