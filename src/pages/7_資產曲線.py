# pip install --upgrade kaleido, 不確定要不要安裝
"""
資產曲線頁面
------------------------------------------------------------
1. 讀取資產歷史資料
2. 顯示 KPI 卡片
3. 繪製 Plotly 互動圖表（前端顯示）
4. 使用 Matplotlib 產出美化後的 PNG，並發送至 Telegram
   （僅使用原本就有的套件：matplotlib / plotly，不需要 kaleido）
"""

import io
from typing import Optional, Tuple

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
# 常數設定（把顏色抽出來，之後要調色只需改這裡）
# ============================================================
PAGE_TITLE = "資產曲線"
DATA_PATH = "asset/portfolio.json"

COLOR_BG = "#0B1120"       # 整體背景（比原本更深、更沉穩）
COLOR_PANEL = "#111827"    # 圖表面板背景
COLOR_GRID = "#1F2937"
COLOR_TEXT_MUTE = "#94A3B8"
COLOR_TEXT_BRIGHT = "#F1F5F9"
COLOR_LINE = "#38BDF8"         # 天空藍，比原本的藍更亮更有質感
COLOR_LINE_MARKER = "#7DD3FC"
COLOR_UP = "#34D399"           # 上漲 / 最高點
COLOR_DOWN = "#F87171"         # 下跌

FONT_CANDIDATES = [
    "Microsoft JhengHei",
    "JhengHei",
    "PingFang",
    "SimHei",
    "Noto Sans CJK",
    "Arial Unicode MS",
]


# ============================================================
# 字型工具
# ============================================================
def find_system_chinese_font() -> Optional[str]:
    """尋找系統可用的中文字型名稱，找不到回傳 None"""
    for font in fm.fontManager.ttflist:
        if any(name in font.name for name in FONT_CANDIDATES):
            return font.name
    return None


# ============================================================
# 資料處理
# ============================================================
def build_asset_dataframe(asset_data: list) -> pd.DataFrame:
    """把原始 asset_data（list of dict）轉成清理過、依日期排序的 DataFrame"""
    df = pd.DataFrame(asset_data)
    df["Date"] = pd.to_datetime(df["Date"])
    df = df.sort_values("Date")

    df["TotalAssets"] = pd.to_numeric(df["TotalAssets"], errors="coerce")
    df = df.dropna(subset=["TotalAssets"])
    df["TotalAssets_Wan"] = df["TotalAssets"] / 10000
    return df


def compute_y_axis_range(
    df: pd.DataFrame, padding_ratio: float = 0.2, fallback_padding: float = 5.0
) -> Tuple[float, float]:
    """計算圖表 Y 軸上下限，避免從 0 開始造成波動被壓縮"""
    y_min = df["TotalAssets_Wan"].min()
    y_max = df["TotalAssets_Wan"].max()
    y_range = y_max - y_min
    padding = y_range * padding_ratio if y_range > 0 else fallback_padding
    return y_min - padding, y_max + padding


def compute_kpi(df: pd.DataFrame) -> dict:
    """計算 KPI 卡片 / 圖表標題會用到的數值"""
    latest = df["TotalAssets_Wan"].iloc[-1]
    prev = df["TotalAssets_Wan"].iloc[-2] if len(df) > 1 else latest
    diff = latest - prev
    pct_change = (diff / prev * 100) if prev != 0 else 0
    return {
        "latest": latest,
        "diff": diff,
        "pct_change": pct_change,
        "max": df["TotalAssets_Wan"].max(),
        "min": df["TotalAssets_Wan"].min(),
    }


# ============================================================
# 前端展示 - KPI 卡片
# ============================================================
def render_kpi_cards(kpi: dict) -> None:
    c1, c2, c3 = st.columns(3)
    with c1:
        st.metric(
            label="當前總資產",
            value=f"${kpi['latest']:,.2f} 萬",
            delta=f"{kpi['diff']:+.2f} 萬 ({kpi['pct_change']:+.2f}%)",
        )
    with c2:
        st.metric(label="歷史最高資產", value=f"${kpi['max']:,.2f} 萬")
    with c3:
        st.metric(label="歷史最低資產", value=f"${kpi['min']:,.2f} 萬")


# ============================================================
# 前端展示 - Plotly 圖表（互動版）
# ============================================================
def build_plotly_chart(df: pd.DataFrame, y_limit: Tuple[float, float]) -> go.Figure:
    y_limit_min, y_limit_max = y_limit

    fig = go.Figure()

    # 主線：用平滑曲線 + 漸層填色，比原本的直線折角更柔和好看
    fig.add_trace(
        go.Scatter(
            x=df["Date"].dt.strftime("%Y-%m-%d"),
            y=df["TotalAssets_Wan"].tolist(),
            mode="lines+markers",
            name="總資產",
            line=dict(color=COLOR_LINE, width=3, shape="spline", smoothing=0.4),
            marker=dict(size=6, color=COLOR_LINE_MARKER, line=dict(width=1, color=COLOR_BG)),
            fill="tozeroy",
            fillcolor="rgba(56, 189, 248, 0.18)",
            hovertemplate="<b>%{x}</b><br>總資產 $%{y:,.2f} 萬<extra></extra>",
        )
    )

    # 標記歷史最高點
    max_idx = df["TotalAssets_Wan"].idxmax()
    fig.add_trace(
        go.Scatter(
            x=[df.loc[max_idx, "Date"].strftime("%Y-%m-%d")],
            y=[df.loc[max_idx, "TotalAssets_Wan"]],
            mode="markers+text",
            text=["歷史最高"],
            textposition="top center",
            textfont=dict(color=COLOR_UP, size=11),
            marker=dict(size=10, color=COLOR_UP, symbol="star"),
            showlegend=False,
            hoverinfo="skip",
        )
    )

    fig.update_layout(
        template="plotly_dark",
        title=dict(text="📈 資產走勢圖", font=dict(color=COLOR_TEXT_BRIGHT, size=20)),
        plot_bgcolor=COLOR_PANEL,
        paper_bgcolor=COLOR_BG,
        font=dict(color=COLOR_TEXT_MUTE),
        xaxis=dict(
            type="category",
            showgrid=False,
            tickfont=dict(color=COLOR_TEXT_MUTE),
            zeroline=False,
        ),
        yaxis=dict(
            title=dict(text="資產（萬元）", font=dict(color=COLOR_TEXT_MUTE)),
            side="right",
            showgrid=True,
            gridcolor=COLOR_GRID,
            griddash="dot",
            tickfont=dict(color=COLOR_TEXT_MUTE),
            range=[y_limit_min, y_limit_max],  # 鎖定 Y 軸範圍，絕不從 0 開始
            tickformat=",.1f",
            zeroline=False,
        ),
        hovermode="x unified",
        margin=dict(l=20, r=40, t=60, b=20),
        height=460,
        legend=dict(orientation="h", yanchor="bottom", y=1.02, x=0),
    )
    return fig


def render_plotly_chart(fig: go.Figure) -> None:
    st.plotly_chart(fig, use_container_width=True)


# ============================================================
# 後端發送 - Matplotlib PNG 生成（美化版，完全不需要新套件）
# ============================================================
def build_matplotlib_png(
    df: pd.DataFrame,
    kpi: dict,
    y_limit: Tuple[float, float],
    chinese_font: Optional[str],
) -> bytes:
    y_limit_min, y_limit_max = y_limit
    y_range = y_limit_max - y_limit_min

    fig, ax = plt.subplots(figsize=(10, 5.2), facecolor=COLOR_BG, dpi=200)
    # 設定字型優先順序：先找中文字型，找不到（如 Emoji）再自動退回找 Emoji 字型
    plt.rcParams['font.family'] = ['Microsoft JhengHei', 'Segoe UI Emoji']
    ax.set_facecolor(COLOR_PANEL)

    dates = df["Date"]
    values = df["TotalAssets_Wan"]

    # 面積填色
    ax.fill_between(dates, values, y_limit_min, color=COLOR_LINE, alpha=0.12, zorder=1)

    # 主線加「發光」效果：疊三層不同寬度/透明度的線，比單一實線更有質感
    for lw, alpha in [(6, 0.06), (4, 0.10), (2.4, 1.0)]:
        ax.plot(
            dates, values,
            color=COLOR_LINE, linewidth=lw, alpha=alpha,
            solid_capstyle="round", zorder=2,
        )

    ax.scatter(
        dates, values,
        s=28, color=COLOR_LINE_MARKER, edgecolor=COLOR_PANEL, linewidth=1.2, zorder=3,
    )

    # 標記「最新一點」與「歷史最高點」
    latest_date, latest_val = dates.iloc[-1], values.iloc[-1]
    ax.scatter(
        [latest_date], [latest_val],
        s=90, color="#FFFFFF", edgecolor=COLOR_LINE, linewidth=2, zorder=4,
    )
    max_idx = values.idxmax()
    ax.scatter(
        [df.loc[max_idx, "Date"]], [df.loc[max_idx, "TotalAssets_Wan"]],
        s=80, marker="*", color=COLOR_UP, zorder=4,
    )

    # 邊框：只留右側/底部，畫面更清爽
    for side in ["top", "left"]:
        ax.spines[side].set_visible(False)
    ax.spines["bottom"].set_color(COLOR_GRID)
    ax.spines["right"].set_color(COLOR_GRID)

    # Y 軸絕對不從 0 開始
    ax.set_ylim(y_limit_min, y_limit_max)

    # 合理刻度密度
    step = 5.0 if y_range > 15 else 2.0
    ax.yaxis.set_major_locator(ticker.MultipleLocator(step))
    ax.yaxis.tick_right()
    ax.yaxis.set_label_position("right")

    ax.grid(True, axis="y", linestyle=":", alpha=0.35, color=COLOR_GRID, zorder=0)
    ax.grid(False, axis="x")

    # 防亂碼字型設定
    if chinese_font:
        font_prop = fm.FontProperties(family=chinese_font)
        ax.set_ylabel("資產（萬元）", color=COLOR_TEXT_MUTE, labelpad=10, fontproperties=font_prop)
        ax.set_title(
            "📈 資產走勢圖",
            color=COLOR_TEXT_BRIGHT, fontsize=16, pad=32,
            loc="left", fontweight="bold",
        )
        subtitle = (
            f"當前 ${kpi['latest']:,.1f} 萬　"
            f"({kpi['diff']:+.1f} 萬 / {kpi['pct_change']:+.2f}%)"
        )
        ax.text(
            0, 1.05, subtitle, transform=ax.transAxes,
            color=(COLOR_UP if kpi["diff"] >= 0 else COLOR_DOWN),
            fontsize=11, fontproperties=font_prop,
        )
        tick_font = font_prop
    else:
        # 若系統全無中文字型，以簡潔英文/數字呈現，避免產出框框 [X]
        ax.set_ylabel("Asset (Wan TWD)", color=COLOR_TEXT_MUTE, labelpad=10)
        ax.set_title("Asset Trend", color=COLOR_TEXT_BRIGHT, fontsize=16, pad=15, loc="left", fontweight="bold")
        tick_font = None

    ax.tick_params(colors=COLOR_TEXT_MUTE, length=0)

    # X 軸日期簡化 (MM-DD)
    date_labels = [d.strftime("%m-%d") for d in dates]
    ax.set_xticks(dates)
    ax.set_xticklabels(
        date_labels, rotation=45, ha="right", color=COLOR_TEXT_MUTE, fontproperties=tick_font
    )

    plt.tight_layout()

    buf = io.BytesIO()
    plt.savefig(buf, format="png", dpi=200, bbox_inches="tight", facecolor=fig.get_facecolor())
    plt.close(fig)
    buf.seek(0)
    return buf.getvalue()


# ============================================================
# 後端發送 - Telegram
# ============================================================
def build_telegram_caption(kpi: dict) -> str:
    return (
        f"📈 <b>每日資產簡報</b>\n"
        f"• 當前總資產：<b>${kpi['latest']:,.2f} 萬</b>\n"
        f"• 日變動：<b>{kpi['diff']:+.2f} 萬 ({kpi['pct_change']:+.2f}%)</b>\n"
        f"• 歷史最高：<b>${kpi['max']:,.2f} 萬</b>"
    )


def send_telegram_photo(bot_token: str, chat_id: str, png_bytes: bytes, caption: str) -> dict:
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    files = {"photo": ("asset_chart.png", png_bytes, "image/png")}
    data = {"chat_id": chat_id, "caption": caption, "parse_mode": "HTML"}
    res = requests.post(url, data=data, files=files)
    return res.json()


# ============================================================
# 主流程
# ============================================================
def main() -> None:
    st.set_page_config(page_title=PAGE_TITLE, layout="wide")
    st.title("📈 資產曲線")

    config = Config(bucket_name="tp1806002")
    tg_bot_token = config.bot_token  # 替換成你的 Bot Token
    tg_chat_id = config.chat_id      # 替換成你的 Chat ID 或 Channel ID

    chinese_font = find_system_chinese_font()

    raw_asset_data = load_data_json(DATA_PATH, [])
    if not raw_asset_data:
        st.warning("目前沒有資產資料")
        st.stop()

    df = build_asset_dataframe(raw_asset_data)
    if df.empty:
        st.warning("資產資料數值格式不正確或無有效數據")
        st.stop()

    kpi = compute_kpi(df)
    render_kpi_cards(kpi)
    st.markdown("---")

    y_limit = compute_y_axis_range(df)

    fig = build_plotly_chart(df, y_limit)
    render_plotly_chart(fig)

    st.markdown("### 📤 自動化發送")
    if st.button("🚀 產出 PNG 並發送到 Telegram"):
        with st.spinner("正在生成圖片與發送中..."):
            try:
                png_bytes = build_matplotlib_png(df, kpi, y_limit, chinese_font)
                caption = build_telegram_caption(kpi)
                result = send_telegram_photo(tg_bot_token, tg_chat_id, png_bytes, caption)
                if result.get("ok"):
                    st.success("✅ 已順利發送至 Telegram！")
                else:
                    st.error(f"❌ 發送失敗，Telegram 錯誤訊息：{result.get('description')}")
            except Exception as e:
                st.error(f"❌ 發生例外錯誤：{e}")


if __name__ == "__main__":
    main()