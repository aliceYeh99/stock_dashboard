"""
pages/11_持股比重回測.py

用「持股比重」而不是「均分」來回測比較：
    - 第一組（預設）：直接抓「富邦、聯邦、元大、員工信託」目前的實際市值比重
      （邏輯跟 10_持股比例.py 一樣，只是簡化成只算 symbol -> 權重%）
    - 你可以再新增一組（或多組），自己調整每檔股票的權重來比較
    - 固定同一個策略，把兩組資金曲線畫在同一張圖上比較

跟 9_資金池.py 的差別：
    - 9_資金池.py：每個組合選好股票後「均分」本金
    - 這支：每個組合裡每檔股票都可以自己調權重(%)，回測時依權重分配本金
      （權重不用剛好加總 100，回測時會自動正規化）
"""
import streamlit as st
import pandas as pd
import altair as alt

from datetime import datetime
from symbols import SYMBOLS
from config import BROKERS, FEE_RATES
from utils.backtest.engine import run_backtest
from utils.backtest.strategies import STRATEGY_MAP
from utils.storage import *

st.title("⚖️ 持股比重回測比較")
st.caption("固定同一個策略，比較不同的『持股比重』組合（例如：目前持股 vs 你想調整後的比重）")

stock_names = load_root_json("stock_names.json", {})


# -------------------------
# 抓「目前實際持股」的市值比重（邏輯同 10_持股比例.py，簡化成 symbol -> 權重%）
# -------------------------
def compute_current_weights() -> dict:
    rows = []
    for broker_label, broker_key in BROKERS.items():
        portfolio = load_json("portfolio.json", {}, broker_key)
        current_prices = load_json("current_prices.json", {}, broker_key)

        for symbol, info in portfolio.items():
            shares = info.get("shares", 0)
            if shares <= 0:
                continue
            price_info = current_prices.get(symbol, {})
            price = price_info.get("price", 0.0)
            price_date = price_info.get("date", "")
            rows.append({
                "symbol": symbol,
                "shares": shares,
                "price": price,
                "price_date": price_date,
            })

    if not rows:
        return {}

    raw_df = pd.DataFrame(rows)

    # 同一檔股票在不同券商都有價格時，取日期最新的那筆
    price_candidates = raw_df[raw_df["price"] > 0].copy()
    if price_candidates.empty:
        return {}
    latest_price = (
        price_candidates.sort_values("price_date")
        .groupby("symbol")
        .tail(1)[["symbol", "price"]]
    )

    shares_agg = raw_df.groupby("symbol")["shares"].sum().reset_index()
    merged = shares_agg.merge(latest_price, on="symbol", how="left")
    merged["price"] = merged["price"].fillna(0.0)
    merged["market_value"] = merged["shares"] * merged["price"]

    total = merged["market_value"].sum()
    if total <= 0:
        return {}

    merged["weight_pct"] = merged["market_value"] / total * 100
    merged = merged[merged["market_value"] > 0]
    return dict(zip(merged["symbol"], merged["weight_pct"]))


current_weights = compute_current_weights()

if not current_weights:
    st.warning("目前抓不到任何券商的持股市值（可能是還沒同步 portfolio.json / current_prices.json），"
               "『目前持股』這組會先給空白，你可以手動選股票、自己輸入權重。")

# -------------------------
# 固定策略
# -------------------------
strategy_name = st.selectbox(
    "策略（固定用同一個策略比較不同比重組合）",
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
# 動態定義幾組「持股比重」組合
# -------------------------
st.divider()
st.subheader("📦 定義持股比重組合")

num_pools = st.number_input("要比較幾組比重？", min_value=1, max_value=4, value=2, step=1)

pool_symbols_map = {}
pool_weights_map = {}

default_current_symbols = list(current_weights.keys())

for i in range(num_pools):
    is_current_pool = (i == 0)
    default_name = "目前持股" if is_current_pool else f"調整組合{i}"

    st.markdown(f"##### 組合 {i + 1}")
    pool_name = st.text_input(
        f"組合 {i + 1} 名稱", value=default_name, key=f"pool_name_{i}"
    )

    default_symbols = default_current_symbols if (is_current_pool or i == 1) else []
    default_symbols = [s for s in default_symbols if s in SYMBOLS]

    selected_symbols = st.multiselect(
        f"組合 {i + 1} 持股",
        options=SYMBOLS,
        default=default_symbols,
        format_func=lambda s: f"{stock_names.get(s, '')} ({s})",
        key=f"pool_symbols_{i}",
    )

    if not selected_symbols:
        st.caption("尚未選擇任何股票")
        pool_symbols_map[pool_name] = []
        pool_weights_map[pool_name] = {}
        st.divider()
        continue

    # 準備權重表格：目前持股組 → 帶入真實市值權重；其他組 → 帶入均分權重當起點
    weight_rows = []
    for sym in selected_symbols:
        if is_current_pool and sym in current_weights:
            w = current_weights[sym]
        else:
            w = 100 / len(selected_symbols)
        weight_rows.append({
            "symbol": sym,
            "name": stock_names.get(sym, sym),
            "weight_%": round(float(w), 2),
        })
    weight_df = pd.DataFrame(weight_rows)

    # key 一定要包含目前選了哪些股票：
    # 如果只用 f"weight_editor_{i}"，當你在上面 multiselect 加減股票（列數改變）時，
    # data_editor 底層元件會拿舊的 session_state 狀態去對新的列數，對不起來就會整個崩掉
    # （React error #185），所以這裡把股票組合也一起 hash 進 key，組合一變就強制重建元件。
    editor_key = f"weight_editor_{i}_{hash(tuple(sorted(selected_symbols)))}"

    edited_df = st.data_editor(
        weight_df,
        column_config={
            "symbol": st.column_config.TextColumn("代號", disabled=True),
            "name": st.column_config.TextColumn("名稱", disabled=True),
            "weight_%": st.column_config.NumberColumn(
                "權重 (%)", min_value=0.0, step=0.5, format="%.2f"
            ),
        },
        hide_index=True,
        use_container_width=True,
        key=editor_key,
    )

    total_weight = edited_df["weight_%"].sum()
    st.caption(
        f"權重加總：{total_weight:.1f}%"
        + ("" if abs(total_weight - 100) < 0.01 else "（不用剛好等於100%，回測時會自動正規化）")
    )

    pool_symbols_map[pool_name] = selected_symbols
    pool_weights_map[pool_name] = dict(zip(edited_df["symbol"], edited_df["weight_%"]))

    st.divider()

# -------------------------
# 回測區間 / 本金
# -------------------------
col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input("開始日期", value=datetime(2026, 1, 1))

with col2:
    end_date = st.date_input("結束日期", value=datetime.now())

with col3:
    initial_capital = st.number_input("每個組合的初始資金", value=2_500_000, step=10_000)

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
                weights=pool_weights_map[pool_name],
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
            "組合": label(name),
        }))

    chart_df = pd.concat(chart_frames, ignore_index=True)

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("日期:T", axis=alt.Axis(format="%Y/%m/%d", title="日期")),
        y=alt.Y("資產:Q", title="資產"),
        color=alt.Color("組合:N", title="組合"),
    )

    st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("📋 交易紀錄")

    #tabs = st.tabs([label(name) for name in valid_results.keys()])
    tabs = st.tabs([f"tab{i + 1}" for i in range(len(valid_results))])
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
                if "date" in trade_df.columns:
                    trade_df["date"] = trade_df["date"].astype(str)
                trade_df = trade_df.reset_index(drop=True)
                st.dataframe(trade_df, use_container_width=True, hide_index=True)