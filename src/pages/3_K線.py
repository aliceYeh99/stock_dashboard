import os
import matplotlib.pyplot as plt
import mplfinance as mpf
import pandas as pd
import streamlit as st
from symbols import SYMBOLS
from utils.download_stock import DATA_DIR, DataStorage, download_stock
from utils.storage import load_root_json
from common.Config import Config
from common.telegram import send_telegram_photo_bytes


# ============================================================
# 1. 字型與 mplfinance 樣式
# ============================================================
FONT_NAME = "Microsoft JhengHei"
plt.rcParams["font.sans-serif"] = [FONT_NAME]
plt.rcParams["axes.unicode_minus"] = False

my_style = mpf.make_mpf_style(
    base_mpf_style="nightclouds",
    marketcolors=mpf.make_marketcolors(
        up="#ff4a4a",
        down="#22c55e",
        edge="inherit",
        wick="inherit",
        volume="inherit",
    ),
    facecolor="#1e1e1e",
    figcolor="#1e1e1e",
    gridcolor="#333333",
    gridstyle="--",
    rc={"font.family": FONT_NAME, "axes.unicode_minus": False},
)

# ============================================================
# 2. 整合你的 download 功能 (讀檔 / 增量更新)
# ============================================================


def get_stock_data(symbol, force_download=False):
    """優先讀取本地 download 資料，若需要更新則呼叫增量下載"""
    storage = DataStorage()
    file_path = os.path.join(DATA_DIR, f"{symbol}.json")

    # 如果要求強制更新，或本地完全沒資料，就執行下載
    if force_download or not os.path.exists(file_path):
        download_stock(symbol)
        source = "線上增量更新"
    else:
        source = "本地 JSON 檔案"

    # 讀取本地 JSON
    raw_data = storage.load_json(file_path)

    if not raw_data:
        return pd.DataFrame(), source

    # 轉為 DataFrame，並設定 Date 為 DatetimeIndex
    df = pd.DataFrame(raw_data)
    df["Date"] = pd.to_datetime(df["Date"])
    df.set_index("Date", inplace=True)

    return df, source


# ============================================================
# 3. Streamlit UI 介面
# ============================================================
st.set_page_config(page_title="K線", layout="wide")
st.title("📈 K線圖")

stock_names = load_root_json("stock_names.json", {})
stock_options = {
    f"{symbol} {stock_names.get(symbol, '')}": symbol
    for symbol in sorted(SYMBOLS)
}

selected_label = st.selectbox("股票", list(stock_options.keys()))
symbol = stock_options[selected_label]
period = st.selectbox("顯示期間", ["3mo", "6mo", "1y"], index=1)








force_update = False

# ============================================================
# 4. 取得資料與計算均線
# ============================================================
with st.spinner(f"載入 {symbol} K線資料..."):
    df, source = get_stock_data(symbol, force_download=force_update)

if df.empty:
    st.error(f"{symbol} 沒有取得資料")
    st.stop()

st.caption(f"ℹ️ 資料來源：{source}")

# 計算 MA 均線（若原檔沒有則現場動態計算）
ma_config = [
    ("MA5", 5, "5日線", "#ffffff"),
    ("MA10", 10, "10日線", "#ffdf00"),
    ("MA20", 20, "月線", "#ff00ff"),
    ("MA60", 60, "季線", "#00ffff"),
    ("MA120", 120, "半年線", "#ffa500"),
]

for ma_key, window, _, _ in ma_config:
    if ma_key not in df.columns:
        df[ma_key] = df["Close"].rolling(window).mean()

period_days = {"3mo": 65, "6mo": 130, "1y": 250}
display_df = df.tail(period_days[period])

# 建立均線圖層
addplots = [
    mpf.make_addplot(display_df[ma_key], width=1, color=color, label=label)
    for ma_key, _, label, color in ma_config
    if ma_key in display_df.columns and display_df[ma_key].notna().any()
]

# ============================================================
# 5. 繪圖與顯示
# ============================================================
fig, axes = mpf.plot(
    display_df,
    type="candle",
    volume=True,
    addplot=addplots,
    figsize=(16, 9),
    style=my_style,
    returnfig=True,
    panel_ratios=(3, 1),
    title=f"{symbol} {stock_names.get(symbol, '')}",
)

# 2. 強制將 K 線圖與成交量圖的 Y 軸標籤與刻度移到右邊
for ax in axes:
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")

if addplots:
    axes[0].legend(
        loc="upper left",
        facecolor="#1e1e1e",
        edgecolor="none",
        labelcolor="white",
    )

st.pyplot(fig, use_container_width=True)
plt.close(fig)



# 強制下載按鈕
#force_update = st.button("🔄 強制線上重新下載 K 線", use_container_width=True)


# ============================================================
# 按鈕區 (更新 & 一鍵發送 Telegram)
# ============================================================
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 強制線上重新下載 K 線", use_container_width=True):
        st.rerun()

with col2:
    if st.button("🚀 發送至 Telegram", use_container_width=True):
        with st.spinner("正在將 K 線圖發送至 Telegram..."):
            # 讀取你的 Config (填入你的 bucket 名稱)
            cfg = Config("YOUR_BUCKET_NAME")

            stock_title = stock_names.get(symbol, "")
            caption = f"📈 {symbol} {stock_title} K線圖"

            # 直接傳入圖表物件、Token 與 Chat ID
            success = send_telegram_photo_bytes(
                fig=fig,
                bot_token=cfg.bot_token,
                chat_id=cfg.chat_id,
                caption=caption,
            )

            if success:
                st.toast("✅ 已成功發送 K 線圖至 Telegram！", icon="🎉")
            else:
                st.error("❌ 發送失敗，請確認網路或 Config 設定。")

