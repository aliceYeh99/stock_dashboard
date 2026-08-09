# pages/4_下載.py
import streamlit as st

from utils.download_stock import update_stocks


# -------------------------
# 股票
# -------------------------

SYMBOLS = [
    "2301.TW",
    "2330.TW",
    "6488.TWO",
]


# -------------------------
# 標題
# -------------------------

st.title("📥 下載股票資料")


st.write(
    f"目前股票：{len(SYMBOLS)} 檔"
)


st.write(
    "、".join(
        sorted(SYMBOLS)
    )
)


# -------------------------
# 下載
# -------------------------

if st.button(
    "📥 開始更新股票資料",
    use_container_width=True
):

    update_stocks(
        SYMBOLS
    )

    st.success(
        f"✅ 已完成 {len(SYMBOLS)} 檔股票更新"
    )