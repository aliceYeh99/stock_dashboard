import streamlit as st
import pandas as pd
from datetime import datetime, timedelta

from utils.backtest.engine import run_backtest
from utils.backtest.strategies import STRATEGY_MAP

st.title("🧪 回測")

# -------------------------
# 選股票
# 開發階段先手動放兩支，之後要接「挑股清單」的話
# 改成: symbols_all = load_json("selected.json", [], broker) 就好
# -------------------------
DEV_SYMBOLS = ["2330.TW", "2454.TW"]

symbols = st.multiselect(
    "回測股票",
    options=DEV_SYMBOLS,
    default=DEV_SYMBOLS,
)

# -------------------------
# 選策略（自動列出 STRATEGY_MAP 裡有的策略）
# -------------------------
strategy_name = st.selectbox(
    "策略",
    options=list(STRATEGY_MAP.keys()),
    format_func=lambda k: STRATEGY_MAP[k].META["name"],
)

strategy_module = STRATEGY_MAP[strategy_name]

# 策略參數欄位是根據 META["params"] 自動長出來的，
# 之後新增策略完全不用改這支頁面
with st.expander("⚙️ 策略參數", expanded=False):
    strategy_params = {}
    for key, default in strategy_module.META["params"].items():
        strategy_params[key] = st.number_input(
            key,
            value=default,
            key=f"param_{strategy_name}_{key}",
        )

# -------------------------
# 回測區間 / 本金
# -------------------------
col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input(
        "開始日期",
        value=datetime.now() - timedelta(days=365),
    )

with col2:
    end_date = st.date_input(
        "結束日期",
        value=datetime.now(),
    )

with col3:
    initial_capital = st.number_input(
        "初始資金",
        value=200_000,
        step=10_000,
    )

# -------------------------
# 執行回測
# -------------------------
if st.button("🚀 開始回測", use_container_width=True):

    if not symbols:
        st.warning("請至少選擇一檔股票")
        st.stop()

    with st.spinner("回測中..."):
        result = run_backtest(
            symbols=symbols,
            strategy_name=strategy_name,
            start=start_date.strftime("%Y-%m-%d"),
            end=end_date.strftime("%Y-%m-%d"),
            initial_capital=initial_capital,
            strategy_params=strategy_params,
        )

    if result["skipped"]:
        st.warning(
            f"以下股票本地沒有資料，已跳過（請先到『下載』頁面更新）："
            f"{'、'.join(result['skipped'])}"
        )

    if result["metrics"] is None:
        st.error("沒有任何股票資料可回測")
        st.stop()

    metrics = result["metrics"]

    st.divider()
    st.subheader("📊 回測結果")

    col1, col2, col3, col4, col5 = st.columns(5)

    with col1:
        st.metric("最終資產", f"{metrics['final_equity']:,.0f}")

    with col2:
        st.metric("總報酬率", f"{metrics['total_return']:.2%}")

    with col3:
        st.metric("CAGR", f"{metrics['cagr']:.2%}")

    with col4:
        st.metric("Sharpe", f"{metrics['sharpe']:.2f}")

    with col5:
        st.metric("最大回撤", f"{metrics['max_dd']:.2%}")

    st.divider()
    st.subheader("💰 資產曲線")
    st.line_chart(result["equity"])

    st.divider()
    st.subheader("📋 交易紀錄")

    trade_df = pd.DataFrame(result["trade_log"])
    if trade_df.empty:
        st.write("這段期間沒有觸發任何交易")
    else:
        st.dataframe(trade_df, use_container_width=True)
