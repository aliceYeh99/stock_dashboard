"""
utils/backtest/engine.py

回測核心迴圈。邏輯跟舊 multi_backtest.py 的 run_backtest_for_strategy 一樣：
    - 多檔股票、共用同一個現金池
    - 每檔股票各自依訊號獨立判斷買賣
    - T 日訊號 → T+1 日「開盤價」成交（避免 lookahead bias）
    - 固定等額分配資金：initial_capital / 股票數
    - 現金不夠時，依 symbols 清單順序排隊

跟舊版不同的地方：
    - 不寫 CSV / 不畫 matplotlib 圖，單純回傳資料，畫圖交給 Streamlit 頁面
    - 資料來源改成讀本地 JSON（utils/backtest/data.py），不用 yfinance 現抓
    - 策略透過 STRATEGY_MAP 動態載入，不用改這支檔案
"""
import pandas as pd

from .data import load_multi
from .metrics import compute_metrics
from .portfolio import Portfolio
from .strategies import get_strategy


def run_backtest(
    symbols: list,
    strategy_name: str,
    start: str,
    end: str,
    initial_capital: float = 200_000,
    strategy_params: dict = None,
) -> dict:
    """
    回傳：
        equity      : pd.Series，每日總資產（index 為日期）
        trade_log   : list[dict]，交易紀錄
        metrics     : dict，績效指標（沒有任何資料時為 None）
        skipped     : list[str]，因為本地沒有資料而被跳過的股票
    """
    strategy_params = strategy_params or {}
    strategy_module = get_strategy(strategy_name)

    raw_data = load_multi(symbols, start, end)
    skipped = [s for s in symbols if s not in raw_data]

    if not raw_data:
        return {
            "equity": pd.Series(dtype=float),
            "trade_log": [],
            "metrics": None,
            "skipped": skipped,
        }

    # 套用策略訊號；T 日訊號 shift(1) 到 T+1 日才執行，避免用到當天還沒收盤的資訊
    data = {}
    for sym, df in raw_data.items():
        df = df.copy()
        df["signal"] = strategy_module.signal(df, **strategy_params).shift(1)
        data[sym] = df

    all_dates = sorted(set().union(*[df.index for df in data.values()]))

    portfolio = Portfolio(initial_capital, list(data.keys()))
    equity_curve = []
    cash_curve = []
    for date in all_dates:
        today_open, today_close = {}, {}
        for sym, df in data.items():
            if date in df.index:
                today_open[sym] = df.loc[date, "open"]
                today_close[sym] = df.loc[date, "close"]

        # 依 symbols 清單順序逐一檢查訊號（順序＝現金不夠時的優先權）
        for sym, df in data.items():
            if date not in df.index or pd.isna(df.loc[date, "signal"]):
                continue

            sig = df.loc[date, "signal"]
            price = today_open.get(sym)
            if price is None or price <= 0:
                continue

            if sig == 1 and portfolio.holdings[sym] == 0:
                budget = initial_capital / len(data)
                portfolio.buy(sym, price, budget, date)
            elif sig == 0 and portfolio.holdings[sym] > 0:
                portfolio.sell(sym, price, date)

        equity_curve.append((date, portfolio.total_value(today_close)))
        cash_curve.append((date, portfolio.cash))

    equity = pd.Series(dict(equity_curve)).sort_index()
    cash = pd.Series(dict(cash_curve)).sort_index()
    metrics = compute_metrics(equity, initial_capital)

    return {
        "equity": equity,
        "cash": cash,
        "trade_log": portfolio.trade_log,
        "metrics": metrics,
        "skipped": skipped,
    }
