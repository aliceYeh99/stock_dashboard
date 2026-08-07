import streamlit as st

from utils.storage import *
from utils.update_prices import update_current_prices

st.title("💰 持股管理")

if st.button(
    "🔄 更新目前價格",
    use_container_width=True
):

    with st.spinner(
        "更新價格中..."
    ):

        update_current_prices()


    st.success(
        "價格更新完成"
    )


    st.rerun()

# -------------------------
# 讀取挑股清單
# -------------------------

selected = load_json(
    "selected.json",
    []
)
stock_names = load_json(
    "stock_names.json",
    {}
)

if not selected:

    st.warning(
        "目前沒有挑選股票，請先到『挑股』加入股票"
    )

    st.stop()



# -------------------------
# 讀取持股資料
# -------------------------

portfolio = load_json(
    "portfolio.json",
    {}
)
current_prices = load_json(
    "current_prices.json",
    {}
)


# -------------------------
# 編輯持股
# -------------------------

st.subheader(
    f"目前股票：{len(selected)} 檔"
)


for symbol in sorted(selected):

    if symbol not in portfolio:

        portfolio[symbol] = {
            "shares": 0,
            "cost": 0
        }

    name = stock_names.get(
        symbol,
        ""
    )

    cost = portfolio[symbol]["cost"]

    price = current_prices.get(
        symbol,
        {}
    ).get(
        "price",
        0
    )


    st.divider()


    col1, col2, col3, col4 = st.columns(
        [2,1,1,1]
    )


    with col1:

        st.write(
            f"📈 {symbol} {name}"
        )


    with col2:

        shares = st.number_input(
            "股數",
            min_value=0,
            step=100,
            value=int(
                portfolio[symbol]["shares"]
            ),
            key=f"{symbol}_shares"
        )


    with col3:

        cost = st.number_input(
            "成本",
            min_value=0.0,
            step=0.5,
            format="%.1f",
            value=float(
                portfolio[symbol]["cost"]
            ),
            key=f"{symbol}_cost"
        )


    portfolio[symbol] = {

        "shares": shares,

        "cost": cost
    }



# -------------------------
# 儲存
# -------------------------

st.divider()


if st.button(
    "💾 儲存持股",
    use_container_width=True
):

    save_json(
        "portfolio.json",
        portfolio
    )


    st.success(
        "持股資料已儲存"
    )



# -------------------------
# 預覽
# -------------------------

st.divider()

st.subheader(
    "目前持股"
)


for symbol, data in portfolio.items():

    if data["shares"] > 0:
        name = stock_names.get(
                symbol,
                ""
            )
        amount = data['shares'] * data['cost']

        st.write(
            f"""
            {symbol} {name}  {data['shares']} 股 ×  {data['cost']}  金額 {amount:,.0f} 元
            """
        )