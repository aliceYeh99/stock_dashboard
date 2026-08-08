import streamlit as st
import json
import os


# ============================================================
# 設定
# ============================================================

DATA_DIR = "data/bank"

FILE_PATH = os.path.join(
    DATA_DIR,
    "portfolio.json"
)


BROKERS = [
    "富邦證券",
    "聯邦證券",
    "元大證券"
]

BANKS = [
    "富邦銀行",
    "Newnewbank",
    "國泰"
]


# ============================================================
# 讀取 JSON
# ============================================================

def load_data():

    if not os.path.exists(FILE_PATH):
        return {}

    with open(
        FILE_PATH,
        "r",
        encoding="utf-8"
    ) as f:

        return json.load(f)


# ============================================================
# 儲存 JSON
# ============================================================

def save_data(data):

    os.makedirs(
        DATA_DIR,
        exist_ok=True
    )

    with open(
        FILE_PATH,
        "w",
        encoding="utf-8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )


# ============================================================
# Page
# ============================================================

st.set_page_config(
    page_title="銀行存款",
    layout="wide"
)

st.title("🏦 銀行存款")


data = load_data()


# ============================================================
# 交割金額
# ============================================================

st.subheader("📋 交割金額")

broker = st.selectbox(
    "證券",
    BROKERS
)

settlement_date = st.date_input(
    "交割日期"
)

settlement_amount = st.number_input(
    "交割金額",
    value=0,
    step=100,
    format="%d"
)


if st.button(
    "💾 儲存交割金額",
    use_container_width=True
):

    date_text = settlement_date.strftime(
        "%m/%d"
    ).lstrip("0").replace(
        "/0",
        "/"
    )

    key = (
        f"{broker} "
        f"{date_text} "
        f"交割金額"
    )

    data[key] = settlement_amount

    save_data(data)

    st.success(
        f"✅ 已儲存：{key} = ${settlement_amount:,}"
    )

    st.rerun()


# ============================================================
# 員工持股信託
# ============================================================

st.divider()

st.subheader("👥 員工持股信託")

trust_cash = st.number_input(
    "尚未購股金額（剩餘現金）",
    value=0,
    step=1000,
    format="%d"
)


if st.button(
    "💾 儲存員工信託現金",
    use_container_width=True
):

    data[
        "員工持股信託 尚未購股金額"
    ] = trust_cash

    save_data(data)

    st.success(
        f"✅ 已儲存剩餘現金：${trust_cash:,}"
    )

    st.rerun()


# ============================================================
# 銀行存款
# ============================================================

st.divider()

st.subheader("🏦 銀行存款")

bank = st.selectbox(
    "銀行",
    BANKS
)

balance = st.number_input(
    "存款金額",
    value=0,
    step=1000,
    format="%d"
)


if st.button(
    "💾 儲存銀行存款",
    use_container_width=True
):

    key = f"{bank} 存款"

    data[key] = balance

    save_data(data)

    st.success(
        f"✅ 已儲存：{key} = ${balance:,}"
    )

    st.rerun()


# ============================================================
# 目前資料
# ============================================================

st.divider()

st.subheader("📊 目前資料")

if data:

    for key, value in list(data.items()):

        col1, col2 = st.columns([5, 1])

        with col1:
            st.write(
                f"**{key}** : ${value:,}"
            )

        with col2:

            if st.button(
                "🗑️",
                key=f"delete_{key}"
            ):

                del data[key]

                save_data(data)

                st.rerun()

else:

    st.info(
        "目前沒有資料"
    )