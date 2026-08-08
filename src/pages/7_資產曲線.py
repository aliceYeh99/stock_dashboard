import streamlit as st
import pandas as pd
import matplotlib.pyplot as plt

from utils.storage import load_data_json


# ============================================================
# 設定
# ============================================================

st.set_page_config(
    page_title="資產曲線",
    layout="wide"
)

st.title("📈 資產曲線")


# ============================================================
# 讀取資產資料
# ============================================================

asset_data = load_data_json(
    "asset/portfolio.json",
    []
)


if not asset_data:

    st.warning("目前沒有資產資料")

    st.stop()


# ============================================================
# DataFrame
# ============================================================

df = pd.DataFrame(
    asset_data
)

df["Date"] = pd.to_datetime(
    df["Date"]
)

df = df.sort_values(
    "Date"
)


# ============================================================
# 資產曲線
# ============================================================

fig, ax = plt.subplots(
    figsize=(16, 7)
)

ax.plot(
    df["Date"],
    df["TotalAssets"],
    marker="o",
    label="總資產"
)

ax.set_title(
    "總資產曲線"
)

ax.set_xlabel(
    "日期"
)

# Y 軸放右邊
ax.yaxis.tick_right()
ax.yaxis.set_label_position("right")

ax.set_ylabel(
    "資產（萬元）"
)


# ============================================================
# Y 軸改成「萬元」
# ============================================================

ax.yaxis.set_major_formatter(
    lambda x, pos: f"{x / 10000:,.0f}"
)


ax.legend()

ax.grid(
    True,
    alpha=0.3
)

fig.autofmt_xdate()

st.pyplot(fig)