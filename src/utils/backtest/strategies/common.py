"""
utils/backtest/strategies/common.py

均線支撐 + MACD 轉強 策略（通用版，季線/半年線都用這個，只換 ma_period）

給「均線支撐 + MACD 轉強」這一類策略共用的工具函式。
這支檔案本身不是一個策略，不會被放進 STRATEGY_MAP，
單純是給 half_year.py、quarter.py（之後如果要加）共用邏輯用的。
"""
import pandas as pd


def macd_cross_up(df: pd.DataFrame, fast: int = 12, slow: int = 26,
                   signal_period: int = 9) -> pd.Series:
    """
    計算 MACD「黃金交叉發生的當下」(True/False)。
    只在交叉那一天是 True，避免用「MACD > 訊號線」這種會持續很多天的
    狀態當訊號，造成雜訊（那樣每天都會觸發，不是只有轉強那一刻）。
    """
    ema_fast = df["close"].ewm(span=fast, adjust=False).mean()
    ema_slow = df["close"].ewm(span=slow, adjust=False).mean()
    macd_line = ema_fast - ema_slow
    signal_line = macd_line.ewm(span=signal_period, adjust=False).mean()

    # 今天 macd > signal，但昨天 macd <= signal → 今天就是交叉發生的那一天
    cross_up = (macd_line > signal_line) & (macd_line.shift(1) <= signal_line.shift(1))
    return cross_up


def ma_support_macd_signal(
    df: pd.DataFrame,
    ma_period: int,
    tolerance: float = 0.03,
    cross_lookback: int = 5,
    fast: int = 12,
    slow: int = 26,
    signal_period: int = 9,
) -> pd.Series:
    """
    均線支撐 + MACD 轉強，買入並持有（不主動賣出）。

    規則：
        1. price_near_ma : 股價貼近均線 (MA 上下 tolerance% 以內)
        2. macd_turning  : 過去 cross_lookback 天內發生過 MACD 黃金交叉
        3. entry         : price_near_ma 且 macd_turning 同時成立 → 進場訊號
        4. 一旦 entry 觸發過一次，訊號就永遠鎖在 1，不會再變回 0

    第 4 點是關鍵：用 cummax()（累積最大值）。
    entry 是一排 True/False，cummax() 會沿著時間往後看「目前為止出現過最大的值」，
    布林值的 True 比 False 大，所以只要曾經出現過一次 True，
    後面所有日期都會變成 True —— 這就是「買了就永遠持有」的效果。
    """
    ma = df["close"].rolling(window=ma_period).mean()

    price_near_ma = (df["close"] >= ma * (1 - tolerance)) & (df["close"] <= ma * (1 + tolerance))
    cross_up = macd_cross_up(df, fast, slow, signal_period)
    macd_turning = cross_up.rolling(window=cross_lookback, min_periods=1).max().astype(bool)

    entry = price_near_ma & macd_turning

    # 買入並持有：訊號一旦變 1，之後就鎖住不再回到 0
    signal = entry.cummax().astype(int)

    return signal
