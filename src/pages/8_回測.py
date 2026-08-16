import streamlit as st
import pandas as pd
import altair as alt

from datetime import datetime, timedelta

from utils.backtest.engine import run_backtest
from utils.backtest.strategies import STRATEGY_MAP
from utils.storage import *

st.title("🧪 回測")

# -------------------------
# 股票名稱
# -------------------------
stock_names = load_root_json(
    "stock_names.json",
    {}
)


# -------------------------
# 選股票
# -------------------------
DEV_SYMBOLS = ["2330.TW", "0050.TW", '6488.TWO', '2337.TW', '2327.TW', '2344.TW','2337.TW']

symbols = st.multiselect(
    "回測股票",
    options=DEV_SYMBOLS,
    default=DEV_SYMBOLS,
    format_func=lambda symbol: f"{stock_names.get(symbol, '')} ({symbol})",
)

# -------------------------
# 選策略（可多選，一次跑多個來比較）
# default=list(STRATEGY_MAP.keys())[:1],
# -------------------------
strategy_names = st.multiselect(
    "策略（可多選比較）",
    options=list(STRATEGY_MAP.keys()),
    default=list(STRATEGY_MAP.keys())[:3],
    format_func=lambda k: STRATEGY_MAP[k].META["name"],
)

# 每個被選到的策略各自一個參數區塊，key 要帶策略名稱避免互相覆蓋
strategy_params_map = {}
for strategy_name in strategy_names:
    strategy_module = STRATEGY_MAP[strategy_name]
    with st.expander(f"⚙️ {strategy_module.META['name']} 參數", expanded=False):
        params = {}
        for key, default in strategy_module.META["params"].items():
            params[key] = st.number_input(
                key,
                value=default,
                key=f"param_{strategy_name}_{key}",
            )
        strategy_params_map[strategy_name] = params

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

    if not strategy_names:
        st.warning("請至少選擇一個策略")
        st.stop()

    results = {}  # strategy_name -> result dict
    with st.spinner("回測中..."):
        for strategy_name in strategy_names:
            results[strategy_name] = run_backtest(
                symbols=symbols,
                strategy_name=strategy_name,
                start=start_date.strftime("%Y-%m-%d"),
                end=end_date.strftime("%Y-%m-%d"),
                initial_capital=initial_capital,
                strategy_params=strategy_params_map[strategy_name],
            )

    # 統一顯示一次「本地沒資料被跳過」的警告（每個策略的 skipped 應該一樣）
    all_skipped = set()
    for r in results.values():
        all_skipped.update(r["skipped"])
    if all_skipped:
        st.warning(
            f"以下股票本地沒有資料，已跳過（請先到『下載』頁面更新）："
            f"{'、'.join(sorted(all_skipped))}"
        )

    # 過濾掉沒有任何資料可回測的策略
    valid_results = {
        name: r for name, r in results.items() if r["metrics"] is not None
    }

    if not valid_results:
        st.error("沒有任何股票資料可回測")
        st.stop()

    def label(name):
        return STRATEGY_MAP[name].META["name"]

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
            "策略": label(name),
        }))

    chart_df = pd.concat(chart_frames, ignore_index=True)

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("日期:T", axis=alt.Axis(format="%Y/%m/%d", title="日期")),
        y=alt.Y("資產:Q", title="資產"),
        color=alt.Color("策略:N", title="策略"),
    )

    st.altair_chart(chart, use_container_width=True)

    # -------------------------
    # 剩餘現金曲線
    # -------------------------

    st.divider()
    st.subheader("💵 剩餘現金")

    cash_frames = []

    for name, r in valid_results.items():
        cash = r["cash"]

        cash_frames.append(pd.DataFrame({
            "日期": pd.to_datetime(cash.index),
            "現金": cash.values,
            "策略": label(name),
        }))

    cash_df = pd.concat(cash_frames, ignore_index=True)

    cash_chart = alt.Chart(cash_df).mark_line().encode(
        x=alt.X(
            "日期:T",
            axis=alt.Axis(format="%Y/%m/%d", title="日期")
        ),
        y=alt.Y(
            "現金:Q",
            title="剩餘現金"
        ),
        color=alt.Color(
            "策略:N",
            title="策略"
        ),
    )

    st.altair_chart(cash_chart, use_container_width=True)

    st.divider()
    st.subheader("📋 交易紀錄")

    tabs = st.tabs([label(name) for name in valid_results.keys()])
    for tab, (name, r) in zip(tabs, valid_results.items()):
        with tab:
            trade_df = pd.DataFrame(r["trade_log"])
            if trade_df.empty:
                st.write("這段期間沒有觸發任何交易")
            else:
                # 股票代號 → 股票名稱
                if "symbol" in trade_df.columns:
                    trade_df["symbol"] = trade_df["symbol"].map(
                        lambda x: f"{stock_names.get(x, x)} ({x})"
                    )
                    trade_df["amount"] = (
                        trade_df["shares"] * trade_df["price"]
                    ).map(lambda x: int(x))
                st.dataframe(trade_df, use_container_width=True)