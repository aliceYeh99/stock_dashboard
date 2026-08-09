"""
utils/backtest/strategies/elliott_wave.py

艾略特波浪理論（簡化版）：
    用 ZigZag 找轉折點，嘗試標記成 1-2-3-4-5 波，
    判斷「目前是否處於多頭推動波」來決定持有/出場。

⚠️ 重要限制：
    1. 波浪理論本質是主觀型態判讀，這裡只是其中一種硬規則近似，
       不代表市場客觀事實，換一個人數波可能結果完全不同。
    2. ZigZag 轉折點確認天生有延遲（要等反轉夠多才能確認前一個高/低點），
       這裡刻意寫成 causal（只用當下已知資料），沒有偷看未來。
       如果網路上的「波浪理論神準回測」看起來完美命中每個轉折，
       通常是 lookahead bias，實盤沒辦法重現。
    3. 只做最基本規則：第2波不跌破第1波起點、轉折點交替出現。
       沒做 Fibonacci 比率、延伸波、三角收斂等進階規則。

規則：每個策略都要有
    signal(df, **params) -> pd.Series (0/1)
    META = {"name": ..., "params": {...}}
"""
import pandas as pd


def _find_pivots_causal(close: pd.Series, pct: float):
    """
    因果式 ZigZag：回傳 [(confirm_pos, pivot_pos, price, 'H'/'L'), ...]
    confirm_pos 是「確認這是轉折點」的那一天（比 pivot_pos 晚），
    故意設計成這樣以避免 lookahead。
    """
    pivots = []
    n = len(close)
    if n < 2:
        return pivots

    trend = None
    extreme_pos, extreme_price = 0, close.iloc[0]

    for i in range(1, n):
        price = close.iloc[i]

        if trend is None:
            if price >= extreme_price * (1 + pct):
                trend = "up"
                extreme_pos, extreme_price = i, price
            elif price <= extreme_price * (1 - pct):
                trend = "down"
                extreme_pos, extreme_price = i, price
            elif price > extreme_price:
                extreme_price = price
            continue

        if trend == "up":
            if price > extreme_price:
                extreme_pos, extreme_price = i, price
            elif price <= extreme_price * (1 - pct):
                pivots.append((i, extreme_pos, extreme_price, "H"))
                trend = "down"
                extreme_pos, extreme_price = i, price
        else:
            if price < extreme_price:
                extreme_pos, extreme_price = i, price
            elif price >= extreme_price * (1 + pct):
                pivots.append((i, extreme_pos, extreme_price, "L"))
                trend = "up"
                extreme_pos, extreme_price = i, price

    return pivots


def _evaluate_wave_state(wave_pivots) -> bool:
    """回傳 True 表示目前判斷處於多頭推動波，應該持有。"""
    if len(wave_pivots) < 3:
        return False

    pts = wave_pivots[-6:]
    prices = [p[1] for p in pts]
    types = [p[2] for p in pts]

    # ZigZag 理論上一定交替，若沒交替代表邏輯有誤，保守出場
    for j in range(1, len(types)):
        if types[j] == types[j - 1]:
            return False

    if types[-1] == "H":
        # 剛創新高，暫定仍在推動波中
        return True

    # 目前處在修正低點：檢查有沒有跌破前一段推動波的起點
    if len(prices) >= 3 and prices[-1] < prices[-3]:
        return False  # 結構失效

    return True


def signal(df: pd.DataFrame, pct: float = 0.05) -> pd.Series:
    close = df["close"]
    n = len(close)
    sig = pd.Series(0, index=df.index)

    pivots = _find_pivots_causal(close, pct)
    wave_pivots = []
    hold = False
    pivot_i = 0

    for bar in range(n):
        while pivot_i < len(pivots) and pivots[pivot_i][0] <= bar:
            _, ppos, pprice, ptype = pivots[pivot_i]
            wave_pivots.append((ppos, pprice, ptype))
            if len(wave_pivots) > 6:
                wave_pivots.pop(0)
            hold = _evaluate_wave_state(wave_pivots)
            pivot_i += 1

        sig.iloc[bar] = 1 if hold else 0

    return sig


META = {
    "name": "艾略特波浪（簡化版）",
    "params": {
        "pct": 0.05,
    },
}