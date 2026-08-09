"""
utils/backtest/data.py

只負責「讀」本地已下載好的股價資料，不負責下載。
下載交給 pages/4_下載.py 的 update_stocks() 去做。

資料來源：data/stocks/download/{symbol}.json
格式（yfinance history() 轉出來的樣子）：
[
    {
        "Date": "2024-11-01",
        "Open": 46.5374984741,
        "High": 47.6375007629,
        "Low": 46.4874992371,
        "Close": 47.625,
        "Volume": 78483628,
        ...
    },
    ...
]
"""
import json
import os

import pandas as pd

DOWNLOAD_DIR = "data/stocks/download"


def load_price_data(symbol: str, start: str = None, end: str = None) -> pd.DataFrame:
    """
    讀取單一股票的本地 JSON，轉成回測用的標準格式：
        index   = 日期 (DatetimeIndex，已排序)
        columns = open, high, low, close, volume
    """
    path = os.path.join(DOWNLOAD_DIR, f"{symbol}.json")

    if not os.path.exists(path):
        raise FileNotFoundError(f"找不到股價資料：{path}，請先到『下載』頁面更新")

    with open(path, "r", encoding="utf-8") as f:
        raw = json.load(f)

    if not raw:
        raise ValueError(f"{symbol} 的資料檔是空的：{path}")

    df = pd.DataFrame(raw)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.set_index("Date").sort_index()

    df = df.rename(columns={
        "Open": "open",
        "High": "high",
        "Low": "low",
        "Close": "close",
        "Volume": "volume",
    })

    df = df[["open", "high", "low", "close", "volume"]]

    if start:
        df = df[df.index >= pd.Timestamp(start)]
    if end:
        df = df[df.index <= pd.Timestamp(end)]

    return df


def load_multi(symbols: list, start: str = None, end: str = None) -> dict:
    """
    讀多檔股票，回傳 {symbol: df}。
    單一檔案讀取失敗（例如還沒下載過）不會讓整批回測掛掉，會直接跳過該檔。
    """
    data = {}
    for sym in symbols:
        try:
            data[sym] = load_price_data(sym, start, end)
        except (FileNotFoundError, ValueError) as e:
            print(f"⚠️ {sym} 跳過：{e}")
    return data
