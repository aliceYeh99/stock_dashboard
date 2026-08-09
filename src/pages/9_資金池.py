import streamlit as st
import pandas as pd
import altair as alt

from datetime import datetime, timedelta

from utils.backtest.engine import run_backtest
from utils.backtest.strategies import STRATEGY_MAP
from utils.storage import *

st.title("💰 資金池比較（不同股票組合）")
st.caption("固定同一個策略，比較不同的股票組合（各自視為一個獨立資金池）")

stock_names = load_root_json("stock_names.json", {})

DEV_SYMBOLS = ["2330.TW", "0050.TW", '6488.TWO', '2337.TW', '2327.TW']

# -------------------------
# 固定策略（跟8_回測.py一樣的參數區塊）
# -------------------------
strategy_name = st.selectbox(
    "策略（固定用同一個策略比較不同組合）",
    options=list(STRATEGY_MAP.keys()),
    format_func=lambda k: STRATEGY_MAP[k].META["name"],
)

strategy_module = STRATEGY_MAP[strategy_name]
strategy_params = {}
with st.expander(f"⚙️ {strategy_module.META['name']} 參數", expanded=False):
    for key, default in strategy_module.META["params"].items():
        strategy_params[key] = st.number_input(
            key,
            value=default,
            key=f"strategy_param_{key}",
        )

# -------------------------
# 動態定義幾種「資金池」（股票組合）
# -------------------------
st.divider()
st.subheader("📦 定義股票組合")

num_pools = st.number_input("要比較幾種組合？", min_value=1, max_value=6, value=2, step=1)

pool_symbols_map = {}
cols = st.columns(min(num_pools, 3))
for i in range(num_pools):
    col = cols[i % len(cols)]
    with col:
        pool_name = st.text_input(f"組合 {i+1} 名稱", value=f"組合{i+1}", key=f"pool_name_{i}")
        selected = st.multiselect(
            f"組合 {i+1} 持股",
            options=DEV_SYMBOLS,
            default=[DEV_SYMBOLS[i % len(DEV_SYMBOLS)]],
            format_func=lambda s: f"{stock_names.get(s, '')} ({s})",
            key=f"pool_symbols_{i}",
        )
        pool_symbols_map[pool_name] = selected

# -------------------------
# 回測區間 / 本金
# -------------------------
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input("開始日期", value=datetime.now() - timedelta(days=365))

with col2:
    end_date = st.date_input("結束日期", value=datetime.now())

with col3:
    initial_capital = st.number_input("每個資金池的初始資金", value=200_000, step=10_000)

# -------------------------
# 執行回測
# -------------------------
if st.button("🚀 開始比較", use_container_width=True):

    empty_pools = [name for name, syms in pool_symbols_map.items() if not syms]
    if empty_pools:
        st.warning(f"以下組合沒有選任何股票，已略過：{'、'.join(empty_pools)}")

    valid_pools = {name: syms for name, syms in pool_symbols_map.items() if syms}
    if not valid_pools:
        st.warning("請至少為一個組合選擇股票")
        st.stop()

    results = {}
    with st.spinner("回測中..."):
        for pool_name, syms in valid_pools.items():
            results[pool_name] = run_backtest(
                symbols=syms,
                strategy_name=strategy_name,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                initial_capital=initial_capital,
                strategy_params=strategy_params,
            )

    all_skipped = set()
    for r in results.values():
        all_skipped.update(r["skipped"])
    if all_skipped:
        st.warning(
            f"以下股票本地沒有資料，已跳過（請先到『下載』頁面更新）："
            f"{'、'.join(sorted(all_skipped))}"
        )

    valid_results = {name: r for name, r in results.items() if r["metrics"] is not None}
    if not valid_results:
        st.error("沒有任何組合有資料可回測")
        st.stop()

    def label(name):
        syms_str = "、".join(valid_pools[name])
        return f"{name}（{syms_str}）"

    st.divider()
    st.subheader("📊 績效指標對照")

    metrics_table = pd.DataFrame({
        label(name): {
            "最終資產": r["metrics"]["final_equity"],
            "總報酬率": r["metrics"]["total_return"],
            "CAGR": r["metrics"]["cagr"],
            "Sharpe": r["metrics"]["sharpe"],
            "最大回撤": r["metrics"]["max_dd"],
        }
        for name, r in valid_results.items()
    }).T

    st.dataframe(
        metrics_table.style.format({
            "最終資產": "{:,.0f}",
            "總報酬率": "{:.2%}",
            "CAGR": "{:.2%}",
            "Sharpe": "{:.2f}",
            "最大回撤": "{:.2%}",
        }),
        use_container_width=True,
    )

    st.divider()
    st.subheader("💰 資產曲線比較")

    chart_frames = []
    for name, r in valid_results.items():
        equity = r["equity"]
        chart_frames.append(pd.DataFrame({
            "日期": pd.to_datetime(equity.index),
            "資產": equity.values,
            "資金池": label(name),
        }))

    chart_df = pd.concat(chart_frames, ignore_index=True)

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("日期:T", axis=alt.Axis(format="%Y/%m/%d", title="日期")),
        y=alt.Y("資產:Q", title="資產"),
        color=alt.Color("資金池:N", title="組合"),
    )

    st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("📋 交易紀錄")

    tabs = st.tabs([label(name) for name in valid_results.keys()])
    for tab, (name, r) in zip(tabs, valid_results.items()):
        with tab:
            trade_df = pd.DataFrame(r["trade_log"])
            if trade_df.empty:
                st.write("這段期間沒有觸發任何交易")
            else:
                if "symbol" in trade_df.columns:
                    trade_df["symbol"] = trade_df["symbol"].map(
                        lambda x: f"{stock_names.get(x, x)} ({x})"
                    )
                    trade_df["amount"] = (
                        trade_df["shares"] * trade_df["price"]
                    ).map(lambda x: int(x))
                st.dataframe(trade_df, use_container_width=True)