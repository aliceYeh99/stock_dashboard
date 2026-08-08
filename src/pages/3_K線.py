import streamlit as st
import yfinance as yf
import pandas as pd
import mplfinance as mpf
import matplotlib.pyplot as plt

from config import BROKERS, DEFAULT_BROKER
from utils.storage import load_json


st.title("📈 K線圖")


# ============================================================
# 證券
# ============================================================

broker_name = st.selectbox(
    "證券",
    BROKERS.keys(),
    index=list(BROKERS.values()).index(
        DEFAULT_BROKER
    )
)

broker = BROKERS[broker_name]


# ============================================================
# 讀取股票
# ============================================================

selected = load_json(
    "selected.json",
    [],
    broker
)


stock_names = load_json(
    "stock_names.json",
    {},
    broker
)


if not selected:

    st.warning(
        "目前沒有挑選股票，請先到「挑股」加入股票。"
    )

    st.stop()


# ============================================================
# 股票選擇
# ============================================================

stock_options = {
    f"{symbol} {stock_names.get(symbol, '')}": symbol
    for symbol in sorted(selected)
}


selected_label = st.selectbox(
    "股票",
    list(stock_options.keys())
)


symbol = stock_options[selected_label]


# ============================================================
# 期間
# ============================================================

period = st.selectbox(
    "期間",
    [
        "1mo",
        "3mo",
        "6mo",
        "1y",
        "2y"
    ],
    index=3
)


# ============================================================
# 更新
# ============================================================

if st.button(
    "🔄 更新",
    use_container_width=True
):

    st.rerun()


# ============================================================
# 下載資料
# ============================================================

with st.spinner(
    f"下載 {symbol} 資料中..."
):

    ticker = yf.Ticker(symbol)

    df = ticker.history(
        period=period,
        interval="1d"
    )


if df.empty:

    st.error(
        f"{symbol} 沒有取得資料"
    )

    st.stop()


# ============================================================
# 計算均線
# ============================================================

df["MA5"] = (
    df["Close"]
    .rolling(5)
    .mean()
)

df["MA10"] = (
    df["Close"]
    .rolling(10)
    .mean()
)

df["MA20"] = (
    df["Close"]
    .rolling(20)
    .mean()
)

df["MA60"] = (
    df["Close"]
    .rolling(60)
    .mean()
)

df["MA120"] = (
    df["Close"]
    .rolling(120)
    .mean()
)


# ============================================================
# K線
# ============================================================

addplots = [
    mpf.make_addplot(
        df["MA5"],
        width=1
    ),

    mpf.make_addplot(
        df["MA10"],
        width=1
    ),

    mpf.make_addplot(
        df["MA20"],
        width=1
    ),

    mpf.make_addplot(
        df["MA60"],
        width=1
    ),

    mpf.make_addplot(
        df["MA120"],
        width=1
    ),
]


fig, axes = mpf.plot(
    df,
    type="candle",
    volume=True,
    addplot=addplots,
    figsize=(14, 8),
    style="yahoo",
    returnfig=True,
    title=f"{symbol} {stock_names.get(symbol, '')}"
)


st.pyplot(
    fig,
    use_container_width=True
)


plt.close(fig)