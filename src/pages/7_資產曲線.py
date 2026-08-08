
# pip install --upgrade kaleido, 不確定要不要安裝
import io
import matplotlib.font_manager as fm
import matplotlib.pyplot as plt
import matplotlib.ticker as ticker
import pandas as pd
import plotly.graph_objects as go
import requests
import streamlit as st
from utils.storage import load_data_json
from common.Config import Config

# ============================================================
# 1. 頁面基本設定 與 解決 Matplotlib 中文亂碼
# ============================================================
st.set_page_config(page_title="資產曲線", layout="wide")

st.title("📈 資產曲線")

config = Config(bucket_name="tp1806002")
# Telegram Bot 設定 (建議存放在 st.secrets 或環境變數)
TG_BOT_TOKEN = config.bot_token  # 替換成你的 Bot Token
TG_CHAT_ID = config.chat_id  # 替換成你的 Chat ID 或 Channel ID

# 尋找系統可用的中文字型
SYSTEM_CHIN_FONT = None
for font in fm.fontManager.ttflist:
    if any(
        name in font.name
        for name in [
            "Microsoft JhengHei",
            "JhengHei",
            "PingFang",
            "SimHei",
            "Noto Sans CJK",
            "Arial Unicode MS",
        ]
    ):
        SYSTEM_CHIN_FONT = font.name
        break

# ============================================================
# 2. 讀取與處理資產資料
# ============================================================
asset_data = load_data_json("asset/portfolio.json", [])

if not asset_data:
    st.warning("目前沒有資產資料")
    st.stop()

df = pd.DataFrame(asset_data)
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

df["TotalAssets"] = pd.to_numeric(df["TotalAssets"], errors="coerce")
df = df.dropna(subset=["TotalAssets"])
df["TotalAssets_Wan"] = df["TotalAssets"] / 10000

if df.empty:
    st.warning("資產資料數值格式不正確或無有效數據")
    st.stop()

# ============================================================
# 3. 頂部關鍵數據卡片 (KPI Metrics)
# ============================================================
latest_asset = df["TotalAssets_Wan"].iloc[-1]
prev_asset = df["TotalAssets_Wan"].iloc[-2] if len(df) > 1 else latest_asset
diff = latest_asset - prev_asset
pct_change = (diff / prev_asset * 100) if prev_asset != 0 else 0

c1, c2, c3 = st.columns(3)
with c1:
    st.metric(
        label="當前總資產",
        value=f"${latest_asset:,.2f} 萬",
        delta=f"{diff:+.2f} 萬 ({pct_change:+.2f}%)",
    )
with c2:
    st.metric(
        label="歷史最高資產", value=f"${df['TotalAssets_Wan'].max():,.2f} 萬"
    )
with c3:
    st.metric(
        label="歷史最低資產", value=f"${df['TotalAssets_Wan'].min():,.2f} 萬"
    )

st.markdown("---")

# 計算精準 Y 軸上下限 (動態彈性範圍)
y_min = df["TotalAssets_Wan"].min()
y_max = df["TotalAssets_Wan"].max()
y_range = y_max - y_min
padding = y_range * 0.2 if y_range > 0 else 5
y_limit_min = y_min - padding
y_limit_max = y_max + padding

# ============================================================
# 4. 前端展示：Plotly 深色質感圖表
# ============================================================
fig = go.Figure()

fig.add_trace(
    go.Scatter(
        x=df["Date"].dt.strftime("%Y-%m-%d"),
        y=df["TotalAssets_Wan"].tolist(),
        mode="lines+markers",
        name="總資產",
        line=dict(color="#3B82F6", width=3),
        marker=dict(size=7, color="#60A5FA"),
        fill="tozeroy",
        fillcolor="rgba(59, 130, 246, 0.15)",
        hovertemplate="<b>日期</b>: %{x}<br><b>總資產</b>: $%{y:,.2f} 萬<extra></extra>",
    )
)

fig.update_layout(
    template="plotly_dark",
    title=dict(text="📈 資產走勢圖", font=dict(color="#F3F4F6", size=18)),
    plot_bgcolor="#111827",
    paper_bgcolor="#111827",
    xaxis=dict(
        type="category",
        showgrid=True,
        gridcolor="#1F2937",
        tickfont=dict(color="#9CA3AF"),
        zeroline=False,
    ),
    yaxis=dict(
        title=dict(text="資產（萬元）", font=dict(color="#9CA3AF")),
        side="right",
        showgrid=True,
        gridcolor="#1F2937",
        tickfont=dict(color="#9CA3AF"),
        range=[y_limit_min, y_limit_max],  # 鎖定 Y 軸範圍，絕不從 0 開始
        tickformat=",.1f",
        zeroline=False,
    ),
    hovermode="x unified",
    margin=dict(l=20, r=40, t=50, b=20),
    height=450,
)

st.plotly_chart(fig, use_container_width=True)

# ============================================================
# 5. 後端發送：Matplotlib 背景生成完美 PNG (修復亂碼與刻度)
# ============================================================


def send_tg_photo_via_plt():
    plt_fig, ax = plt.subplots(figsize=(10, 5), facecolor="#111827")
    ax.set_facecolor("#111827")

    # 畫折線與區域
    ax.plot(
        df["Date"],
        df["TotalAssets_Wan"],
        color="#3B82F6",
        linewidth=2.5,
        marker="o",
        markersize=5,
    )
    ax.fill_between(
        df["Date"], df["TotalAssets_Wan"], color="#3B82F6", alpha=0.15
    )

    # 邊框細節
    ax.spines["top"].set_visible(False)
    ax.spines["left"].set_visible(False)
    ax.spines["bottom"].set_color("#1F2937")
    ax.spines["right"].set_color("#1F2937")

    # 關鍵 1：Y 軸絕對不從 0 開始
    ax.set_ylim(y_limit_min, y_limit_max)

    # 關鍵 2：合理刻度密度（根據數據變化範圍，約產生 5~8 個刻度）
    step = 5.0 if y_range > 15 else 2.0
    ax.yaxis.set_major_locator(ticker.MultipleLocator(step))

    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")

    # 關鍵 3：防亂碼字型設定
    if SYSTEM_CHIN_FONT:
        font_prop = fm.FontProperties(family=SYSTEM_CHIN_FONT)
        ax.set_ylabel(
            "資產（萬元）", color="#9CA3AF", labelpad=10, fontproperties=font_prop
        )
        ax.set_title(
            "📈 資產走勢圖",
            color="#F3F4F6",
            fontsize=14,
            pad=15,
            fontproperties=font_prop,
        )
    else:
        # 若系統全無中文字型，以簡潔英文/數字呈現，避免產出框框 [X]
        ax.set_ylabel("Asset (Wan TWD)", color="#9CA3AF", labelpad=10)
        ax.set_title("📈 Asset Trend", color="#F3F4F6", fontsize=14, pad=15)

    ax.tick_params(colors="#9CA3AF")
    ax.grid(True, linestyle=":", alpha=0.3, color="#1F2937")

    # X 軸日期簡化 (MM-DD)
    fig_dates = [d.strftime("%m-%d") for d in df["Date"]]
    ax.set_xticks(df["Date"])
    ax.set_xticklabels(fig_dates, rotation=45, ha="right", color="#9CA3AF")

    plt.tight_layout()

    # 輸出 Byte
    buf = io.BytesIO()
    plt.savefig(
        buf,
        format="png",
        dpi=200,
        bbox_inches="tight",
        facecolor=plt_fig.get_facecolor(),
    )
    plt.close(plt_fig)
    buf.seek(0)

    # Telegram 簡報訊息 (支援 HTML 與中文)
    caption_text = (
        f"📈 <b>每日資產簡報</b>\n"
        f"• 當前總資產：<b>${latest_asset:,.2f} 萬</b>\n"
        f"• 日變動：<b>{diff:+.2f} 萬 ({pct_change:+.2f}%)</b>\n"
        f"• 歷史最高：<b>${df['TotalAssets_Wan'].max():,.2f} 萬</b>"
    )

    url = f"https://api.telegram.org/bot{TG_BOT_TOKEN}/sendPhoto"
    files = {"photo": ("asset_chart.png", buf.getvalue(), "image/png")}
    data = {
        "chat_id": TG_CHAT_ID,
        "caption": caption_text,
        "parse_mode": "HTML",
    }

    res = requests.post(url, data=data, files=files)
    return res.json()


# 按鈕控制
st.markdown("### 📤 自動化發送")
if st.button("🚀 產出 PNG 並發送到 Telegram"):
    with st.spinner("正在生成圖片與發送中..."):
        try:
            result = send_tg_photo_via_plt()
            if result.get("ok"):
                st.success("✅ 已順利發送至 Telegram！")
            else:
                st.error(
                    f"❌ 發送失敗，Telegram 錯誤訊息：{result.get('description')}"
                )
        except Exception as e:
            st.error(f"❌ 發生例外錯誤：{e}")