"""
utils/backtest/portfolio.py

單一現金池、多檔股票共用的簡易帳本。
從舊 multi_backtest.py 的 Portfolio class 原封不動搬過來，邏輯沒有改，
只是把它獨立成一個模組。
"""

COMMISSION = 0.001425  # 手續費（買、賣都收，未打折）
TAX = 0.003            # 證交稅（僅賣出時收）


class Portfolio:
    def __init__(self, cash: float, symbols: list):
        self.cash = cash
        self.holdings = {s: 0 for s in symbols}  # 股數
        self.trade_log = []

    def total_value(self, prices: dict) -> float:
        stock_value = sum(
            shares * prices.get(sym, 0) for sym, shares in self.holdings.items()
        )
        return self.cash + stock_value

    def buy(self, symbol: str, price: float, budget: float, date):
        if price <= 0 or budget <= 0:
            return

        shares = int(budget // (price * (1 + COMMISSION)))
        if shares <= 0:
            return

        cost = shares * price * (1 + COMMISSION)

        # 現金不夠時，用剩餘現金能買多少算多少
        if cost > self.cash:
            shares = int(self.cash // (price * (1 + COMMISSION)))
            cost = shares * price * (1 + COMMISSION)

        if shares <= 0:
            return

        self.cash -= cost
        self.holdings[symbol] += shares
        self.trade_log.append({
            "date": date,
            "symbol": symbol,
            "action": "BUY",
            "shares": shares,
            "price": price,
        })

    def sell(self, symbol: str, price: float, date):
        shares = self.holdings[symbol]
        if shares <= 0:
            return

        proceeds = shares * price * (1 - COMMISSION - TAX)
        self.cash += proceeds
        self.holdings[symbol] = 0

        self.trade_log.append({
            "date": date,
            "symbol": symbol,
            "action": "SELL",
            "shares": shares,
            "price": price,
        })
