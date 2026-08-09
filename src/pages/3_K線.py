from io import BytesIO
import os
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import pandas as pd
import streamlit as st
from common.Config import Config
from common.telegram import send_telegram_photo_bytes
from symbols import SYMBOLS
from utils.download_stock import DATA_DIR, DataStorage, download_stock
from utils.storage import load_root_json

# ============================================================
# 1. 字型與中文字型初始化 (比照 Lambda init_font)
# ============================================================
FONT_NAME = "Microsoft JhengHei"
plt.rcParams["font.sans-serif"] = [
    FONT_NAME,
    "Arial Unicode MS",
    "SimHei",
    "sans-serif",
]
plt.rcParams["axes.unicode_minus"] = False

# ============================================================
# 2. 整合你的 download 功能 (讀檔 / 增量更新)
# ============================================================


def get_stock_data(symbol, force_download=False):
    """優先讀取本地 download 資料，若需要更新則呼叫增量下載"""
    storage = DataStorage()
    file_path = os.path.join(DATA_DIR, f"{symbol}.json")

    if force_download or not os.path.exists(file_path):
        download_stock(symbol, 430)
        source = "線上增量更新"
    else:
        source = "本地 JSON 檔案"

    raw_data = storage.load_json(file_path)

    if not raw_data:
        return pd.DataFrame(), source

    df = pd.DataFrame(raw_data)
    # 確保日期格式正確
    df["Date"] = pd.to_datetime(df["Date"]).dt.strftime("%Y-%m-%d")

    return df, source


# ============================================================
# 3. Streamlit UI 介面
# ============================================================
import json  # 👈 加在檔案最上方的 import 區塊即可，這裡先提醒一下

st.set_page_config(page_title="K線", layout="wide")
st.title("📈 K線圖")

stock_names = load_root_json("stock_names.json", {})
stock_options = {
    f"{symbol} {stock_names.get(symbol, '')}": symbol
    for symbol in sorted(SYMBOLS)
}
option_labels = list(stock_options.keys())

# ------------------------------------------------------------
# 3.1 常用股票：讀取 / 儲存 (存成 JSON 檔，不再 hard code)
# ------------------------------------------------------------
FAVORITES_FILE = os.path.join(DATA_DIR, "favorite_symbols.json")


def load_favorites():
    if os.path.exists(FAVORITES_FILE):
        try:
            with open(FAVORITES_FILE, "r", encoding="utf-8") as f:
                data = json.load(f)
                if isinstance(data, list):
                    return data
        except Exception:
            pass
    return []


def save_favorites(symbols):
    with open(FAVORITES_FILE, "w", encoding="utf-8") as f:
        json.dump(symbols, f, ensure_ascii=False, indent=2)


if "favorite_symbols" not in st.session_state:
    st.session_state.favorite_symbols = load_favorites()

if "selected_symbol" not in st.session_state:
    st.session_state.selected_symbol = None

# ------------------------------------------------------------
# 3.2 勾選常用股票 + 儲存按鈕
# ------------------------------------------------------------
with st.expander("⭐ 設定常用股票", expanded=False):
    favorite_labels_default = [
        label
        for label, sym in stock_options.items()
        if sym in st.session_state.favorite_symbols
    ]

    selected_favorite_labels = st.multiselect(
        "勾選要放進常用股票的項目",
        options=option_labels,
        default=favorite_labels_default,
    )

    if st.button("💾 儲存常用股票", use_container_width=True):
        new_favorites = [stock_options[label] for label in selected_favorite_labels]
        save_favorites(new_favorites)
        st.session_state.favorite_symbols = new_favorites
        st.toast("✅ 已儲存常用股票！", icon="💾")

# ------------------------------------------------------------
# 3.3 常用股票快捷按鈕（依儲存結果動態顯示）
# ------------------------------------------------------------
if st.session_state.favorite_symbols:
    st.write("🔥 常用股票")
    quick_cols = st.columns(len(st.session_state.favorite_symbols))
    for col, sym in zip(quick_cols, st.session_state.favorite_symbols):
        name = stock_names.get(sym, "")
        with col:
            if st.button(f"{sym} {name}", use_container_width=True, key=f"quick_{sym}"):
                st.session_state.selected_symbol = sym
else:
    st.info("💡 尚未設定常用股票，可在上方「設定常用股票」勾選並儲存。")

# ------------------------------------------------------------
# 3.4 搜尋股票下拉選單
# ------------------------------------------------------------
default_label = None
if st.session_state.selected_symbol:
    for label, sym in stock_options.items():
        if sym == st.session_state.selected_symbol:
            default_label = label
            break

selected_label = st.selectbox(
    "搜尋股票 (可直接輸入代號或名稱)",
    options=option_labels,
    index=option_labels.index(default_label) if default_label else None,
    placeholder="請輸入或選擇股票...",
)

# 防呆：如果尚未選擇股票，提示使用者並暫停後續繪圖
if not selected_label:
    st.info("💡 請在上方搜尋並選擇一檔股票以顯示 K 線圖。")
    st.stop()

symbol = stock_options[selected_label]
st.session_state.selected_symbol = symbol



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

# 計算均線 (防呆：若資料內沒有則動態計算)
ma_config = [
    ("MA5", 5, "MA5", "#ffffff"),
    ("MA10", 10, "MA10", "#ffdf00"),
    ("MA20", 20, "MA20", "#ff00ff"),
    ("MA60", 60, "MA60", "#00ffff"),
    ("MA120", 120, "MA120", "#ffa500"),
]

for ma_key, window, _, _ in ma_config:
    if ma_key not in df.columns:
        df[ma_key] = df["Close"].rolling(window).mean()

period_days = {"3mo": 65, "6mo": 130, "1y": 250}
display_df = df.tail(period_days[period]).reset_index(drop=True)

# ============================================================
# 5. 繪圖 (完全重寫：複製你 Lambda generate_kline_chart 的純 Matplotlib 邏輯)
# ============================================================
dates = display_df["Date"].tolist()
opens = display_df["Open"].tolist()
highs = display_df["High"].tolist()
lows = display_df["Low"].tolist()
closes = display_df["Close"].tolist()
volumes = display_df["Volume"].tolist()

ma5 = display_df["MA5"].tolist()
ma10 = display_df["MA10"].tolist()
ma20 = display_df["MA20"].tolist()
ma60 = display_df["MA60"].tolist()
ma120 = display_df["MA120"].tolist()

# 建立 3:1 高度比的上下子圖，共用 X 軸
fig, (ax1, ax2) = plt.subplots(
    2,
    1,
    figsize=(14, 8),
    dpi=150,
    sharex=True,
    gridspec_kw={"height_ratios": [3, 1]},
)

fig.patch.set_facecolor("#1e1e1e")
ax1.set_facecolor("#1e1e1e")
ax2.set_facecolor("#1e1e1e")

# 👇 貼上這段：將上圖與下圖的所有邊框改為黑色（或與背景同色的 #1e1e1e）
for ax in [ax1, ax2]:
    for spine in ax.spines.values():
        spine.set_color("#1e1e1e")  # 若想留極細微灰框可設 '#333333'

# ────── 上圖：手動繪製蠟燭 K 線 & 成交量顏色判定 ──────
bar_colors = []
for i in range(len(display_df)):
    if closes[i] >= opens[i]:
        color = "#ff4a4a"  # 紅
        lower_body = opens[i]
        height = max(closes[i] - opens[i], 0.3)
    else:
        color = "#22c55e"  # 綠
        lower_body = closes[i]
        height = max(opens[i] - closes[i], 0.3)

    bar_colors.append(color)

    # 畫 K 線的影線與實體矩形到 ax1
    ax1.vlines(x=i, ymin=lows[i], ymax=highs[i], colors=color, linewidth=1.2)
    ax1.add_patch(
        plt.Rectangle(
            (i - 0.3, lower_body),
            0.6,
            height,
            facecolor=color,
            edgecolor=color,
        )
    )

# ────── 上圖：繪製 5, 10, 20, 60, 120 均線 ──────
ax1.plot(ma5, label="MA5", color="#ffffff", linewidth=1.0, alpha=0.9)
ax1.plot(ma10, label="MA10", color="#ffdf00", linewidth=1.0, alpha=0.9)
ax1.plot(ma20, label="MA20", color="#ff00ff", linewidth=1.0, alpha=0.9)
ax1.plot(ma60, label="MA60", color="#00ffff", linewidth=1.0, alpha=0.9)
ax1.plot(ma120, label="MA120", color="#ffa500", linewidth=1.0, alpha=0.9)
ax1.legend(
    loc="upper left", facecolor="#1e1e1e", edgecolor="none", labelcolor="white"
)

# ────── 下圖：繪製成交量直條圖 ──────
ax2.bar(
    range(len(display_df)), volumes, color=bar_colors, width=0.6, alpha=0.8
)

# ────── 圖表細節美化 & Y 軸靠右設定 ──────
stock_title = stock_names.get(symbol, "")
ax1.set_title(
    f"{symbol} {stock_title} K線圖", color="white", fontsize=16, pad=15
)
ax1.grid(True, color="#333333", linestyle="--", linewidth=0.5)
ax2.grid(True, color="#333333", linestyle="--", linewidth=0.5)

# 上圖與下圖不顯示左邊 Y 軸刻度，標籤全部靠右
ax1.yaxis.tick_right()
ax1.yaxis.set_label_position("right")
ax1.tick_params(
    axis="y",
    colors="white",
    labelleft=False,
    left=False,
    labelright=True,
    right=True,
)

ax2.yaxis.tick_right()
ax2.yaxis.set_label_position("right")
ax2.tick_params(
    axis="y",
    colors="white",
    labelleft=False,
    left=False,
    labelright=True,
    right=True,
)

# X 軸坐標軸控制
step = max(len(dates) // 6, 1)
ax2.set_xticks(range(0, len(dates), step))
ax2.set_xticklabels(
    [dates[i] for i in range(0, len(dates), step)], rotation=30, color="white"
)
ax2.set_xlim(-1, len(display_df))

plt.tight_layout()

# 顯示在頁面上
st.pyplot(fig, use_container_width=True)

# ============================================================
# 6. 按鈕區 (更新 & 一鍵發送 Telegram)
# ============================================================
col1, col2 = st.columns(2)

with col1:
    if st.button("🔄 強制線上重新下載 K 線", use_container_width=True):
        with st.spinner("正在下載最新 K 線資料..."):
            download_stock(symbol)
        st.rerun()

with col2:
    if st.button("🚀 發送至 Telegram", use_container_width=True):
        with st.spinner("正在將 K 線圖發送至 Telegram..."):
            cfg = Config("YOUR_BUCKET_NAME")

            caption = f"📈 {symbol} {stock_title} K線圖"

            # 直接將 Matplotlib 產生的 fig 物件轉為 Bytes 發送
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

# 最後才關閉圖表
plt.close(fig)