import streamlit as st

from symbols import SYMBOLS
from config import DEFAULT_BROKER, BROKERS
from utils.storage import *

broker_name = st.selectbox(
    "證券",
    BROKERS.keys(),
    index=list(BROKERS.values()).index(
        DEFAULT_BROKER
    )
)

broker = BROKERS[broker_name]

st.title("📋 挑股")

stock_names = load_root_json(
    "stock_names.json",
    {}
)

# -------------------------
# 讀取已保存清單
# -------------------------

saved_selected = load_json(
    "selected.json",
    [],
    broker
)


# 放到 session_state
if "selected" not in st.session_state:

    st.session_state.selected = saved_selected.copy()



selected = st.session_state.selected



# -------------------------
# 搜尋
# -------------------------

keyword = st.text_input(
    "🔍 搜尋股票"
).strip()



# -------------------------
# 股票 Button
# -------------------------

cols = st.columns(4)


for i, symbol in enumerate(sorted(SYMBOLS)):
    
    name = stock_names.get(
        symbol,
        ""
    )


    if keyword:

        if (
            keyword not in symbol
            and keyword not in name
        ):
            continue



    is_selected = symbol in selected


    button_text = (
        "🟩 "
        if is_selected
        else "⬜ "
    )


    button_text += f"{symbol}\n{name}"



    with cols[i % 4]:


        if st.button(
            button_text,
            key=symbol,
            use_container_width=True
        ):


            if symbol in selected:

                selected.remove(symbol)

            else:

                selected.append(symbol)



            st.rerun()



# -------------------------
# 儲存
# -------------------------

st.divider()


st.write(
    f"目前選擇：{len(selected)} 檔"
)



if st.button(
    "💾 儲存挑股清單",
    use_container_width=True
):

    save_json(
        "selected.json",
        selected,
        broker
    )


    st.success(
        "挑股清單已保存"
    )



# -------------------------
# 顯示
# -------------------------

st.divider()


st.subheader(
    "已選股票"
)


for s in selected:

    st.write(
        "🟩",
        s
    )