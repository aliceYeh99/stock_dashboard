import pandas as pd
import plotly.graph_objects as go
import streamlit as st
from utils.storage import load_data_json

# ============================================================
# 設定
# ============================================================
st.set_page_config(page_title="資產曲線", layout="wide")

st.title("📈 資產曲線")

# ============================================================
# 讀取資產資料
# ============================================================
asset_data = load_data_json("asset/portfolio.json", [])

if not asset_data:
    st.warning("目前沒有資產資料")
    st.stop()

# ============================================================
# DataFrame 處理 (關鍵修復：數值轉型)
# ============================================================
df = pd.DataFrame(asset_data)

# 1. 確保日期格式與排序
df["Date"] = pd.to_datetime(df["Date"])
df = df.sort_values("Date")

# 2. 強制把 TotalAssets 轉為浮點數 (防止 JSON 讀進來是字串)，並剔除空值
df["TotalAssets"] = pd.to_numeric(df["TotalAssets"], errors="coerce")
df = df.dropna(subset=["TotalAssets"])

# 3. 轉為萬元單位
df["TotalAssets_Wan"] = df["TotalAssets"] / 10000

if df.empty:
    st.warning("資產資料數值格式不正確或無有效數據")
    st.stop()

# ============================================================
# 頂部關鍵資產數據卡片 (KPI Metrics)
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

# ============================================================
# 資產曲線（Plotly 修復版）
# ============================================================
y_min = df["TotalAssets_Wan"].min()
y_max = df["TotalAssets_Wan"].max()
padding = (y_max - y_min) * 0.15 if y_max != y_min else 5

fig = go.Figure()

# 明確傳入 list / Series 確保解析正常
fig.add_trace(
    go.Scatter(
        x=df["Date"].dt.strftime("%Y-%m-%d"),  # 轉為標準日期字串，避免 JS 轉型異常
        y=df["TotalAssets_Wan"].tolist(),  # 強制轉為標準 Python List
        mode="lines+markers",
        name="總資產",
        line=dict(color="#1D4ED8", width=3),  # 鮮艷深藍色
        marker=dict(size=7, color="#1D4ED8"),
        fill="tozeroy",
        fillcolor="rgba(29, 78, 216, 0.12)",
        hovertemplate="<b>日期</b>: %{x}<br><b>總資產</b>: $%{y:,.2f} 萬<extra></extra>",
    )
)

fig.update_layout(
    template="plotly_white",
    xaxis=dict(
        type="category",  # 強制 X 軸以類別對齊
        showgrid=True,
        gridcolor="#F3F4F6",
        zeroline=False,
    ),
    yaxis=dict(
        title="資產（萬元）",
        side="right",
        showgrid=True,
        gridcolor="#F3F4F6",
        range=[y_min - padding, y_max + padding],
        tickformat=",.1f",
        zeroline=False,
    ),
    hovermode="x unified",
    margin=dict(l=10, r=40, t=20, b=20),
    height=450,
)

st.plotly_chart(fig, use_container_width=True)