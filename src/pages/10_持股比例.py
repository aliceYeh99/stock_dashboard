"""
pages/10_持股比例.py

跨券商持股比例總覽：
    - 合併「富邦、聯邦、元大、員工信託」底下的持股
    - 依個股 / 依自訂族群，畫圓餅圖看持股比例
    - 同一檔股票在不同券商都有價格時，取日期最新的價格
    - 持有成本沿用各券商自己的手續費率去算，合併後再加總
"""
import streamlit as st
import pandas as pd
import altair as alt

from utils.storage import load_json, load_root_json, save_root_json
from config import BROKERS, FEE_RATES

st.title("🥧 持股比例總覽")

stock_names = load_root_json("stock_names.json", {})
stock_groups = load_root_json("stock_groups.json", {})  # symbol -> 族群名稱

# -------------------------
# 讀取所有券商的持股 + 現價，逐筆展開
# -------------------------
rows = []
for broker_label, broker_key in BROKERS.items():
    fee_rate = FEE_RATES[broker_label]

    portfolio = load_json("portfolio.json", {}, broker_key)
    current_prices = load_json("current_prices.json", {}, broker_key)

    for symbol, info in portfolio.items():
        shares = info.get("shares", 0)
        cost = info.get("cost", 0.0)
        if shares <= 0:
            continue

        price_info = current_prices.get(symbol, {})
        price = price_info.get("price", 0.0)
        price_date = price_info.get("date", "")

        rows.append({
            "symbol": symbol,
            "broker_label": broker_label,
            "shares": shares,
            "cost": cost,
            "fee_rate": fee_rate,
            "price": price,
            "price_date": price_date,
            "cost_value": shares * cost * (1 + fee_rate),
        })

if not rows:
    st.info("目前所有券商底下都沒有持股（shares > 0）")
    st.stop()

raw_df = pd.DataFrame(rows)

# -------------------------
# 每檔股票取「日期最新」的價格（不同券商的價格理論上該一樣，
# 但若有券商還沒更新，用最新日期的那筆，避免用到舊價格）
# -------------------------
price_candidates = raw_df[raw_df["price"] > 0].copy()
if price_candidates.empty:
    latest_price = pd.DataFrame(columns=["symbol", "price"])
else:
    latest_price = (
        price_candidates.sort_values("price_date")
        .groupby("symbol")
        .tail(1)[["symbol", "price", "price_date"]]
    )

missing_price_symbols = sorted(set(raw_df["symbol"]) - set(latest_price["symbol"]))
if missing_price_symbols:
    st.warning(f"以下股票目前完全沒有價格資料，市值暫算為0：{'、'.join(missing_price_symbols)}")

# -------------------------
# 合併同一檔股票（跨券商）：股數、成本加總；股數加權平均成本供顯示用
# -------------------------
agg = raw_df.groupby("symbol").agg(
    shares=("shares", "sum"),
    cost_value=("cost_value", "sum"),
).reset_index()

agg["avg_cost"] = agg.apply(
    lambda r: r["cost_value"] / r["shares"] if r["shares"] else 0.0, axis=1
)

merged = agg.merge(latest_price[["symbol", "price"]], on="symbol", how="left")
merged["price"] = merged["price"].fillna(0.0)

merged["name"] = merged["symbol"].map(lambda s: stock_names.get(s, s))
merged["group"] = merged["symbol"].map(lambda s: stock_groups.get(s, "未分類"))
merged["market_value"] = merged["shares"] * merged["price"]
merged["pnl"] = merged["market_value"] - merged["cost_value"]
merged["pnl_pct"] = merged.apply(
    lambda r: r["pnl"] / r["cost_value"] if r["cost_value"] else 0.0, axis=1
)

total_market_value = merged["market_value"].sum()
merged["weight"] = merged["market_value"] / total_market_value if total_market_value else 0.0

# -------------------------
# 總覽指標
# -------------------------
col1, col2, col3 = st.columns(3)
with col1:
    st.metric("總市值", f"{total_market_value:,.0f}")
with col2:
    total_cost = merged["cost_value"].sum()
    st.metric("總成本", f"{total_cost:,.0f}")
with col3:
    total_pnl = merged["pnl"].sum()
    st.metric(
        "未實現損益",
        f"{total_pnl:,.0f}",
        f"{total_pnl / total_cost:.2%}" if total_cost else "0%",
    )

# -------------------------
# 族群分類（可編輯）
# -------------------------
st.divider()
st.subheader("🏷️ 族群分類")
st.caption("幫每檔股票指定族群（例如：記憶體、被動元件、AI伺服器），未分類的預設歸在「未分類」")

existing_groups = sorted(set(stock_groups.values()) | {"未分類"})

with st.expander("編輯族群分類", expanded=False):
    edited_groups = {}
    for _, row in merged.sort_values("market_value", ascending=False).iterrows():
        symbol = row["symbol"]
        current_group = stock_groups.get(symbol, "未分類")
        col_a, col_b, col_c = st.columns([2, 2, 2])
        with col_a:
            st.write(f"{row['name']} ({symbol})")
        with col_b:
            choice = st.selectbox(
                "族群",
                options=existing_groups + ["➕ 新增族群"],
                index=existing_groups.index(current_group) if current_group in existing_groups else 0,
                key=f"group_select_{symbol}",
                label_visibility="collapsed",
            )
        with col_c:
            if choice == "➕ 新增族群":
                new_group = st.text_input(
                    "新族群名稱",
                    key=f"new_group_{symbol}",
                    label_visibility="collapsed",
                )
                edited_groups[symbol] = new_group.strip() or current_group
            else:
                edited_groups[symbol] = choice

    if st.button("💾 儲存族群分類"):
        stock_groups.update(edited_groups)
        stock_groups = {k: v for k, v in stock_groups.items() if v}
        save_root_json("stock_groups.json", stock_groups)
        st.success("已儲存，重新整理頁面套用最新分類")
        st.rerun()

merged["group"] = merged["symbol"].map(lambda s: stock_groups.get(s, "未分類"))

# -------------------------
# 持股比例圖：依個股
# -------------------------
st.divider()
st.subheader("依個股")

pie_by_stock = merged.copy()
pie_by_stock["label"] = pie_by_stock["name"] + "（" + pie_by_stock["symbol"] + "）"

chart_stock = alt.Chart(pie_by_stock).mark_arc(innerRadius=60).encode(
    theta=alt.Theta("market_value:Q", title="市值"),
    color=alt.Color("label:N", title="個股"),
    tooltip=[
        alt.Tooltip("label:N", title="股票"),
        alt.Tooltip("market_value:Q", title="市值", format=",.0f"),
        alt.Tooltip("weight:Q", title="佔比", format=".1%"),
    ],
)
st.altair_chart(chart_stock, use_container_width=True)

# -------------------------
# 持股比例圖：依族群
# -------------------------
st.divider()
st.subheader("依族群")

group_agg = merged.groupby("group")["market_value"].sum().reset_index()
group_agg["weight"] = (
    group_agg["market_value"] / group_agg["market_value"].sum()
    if group_agg["market_value"].sum() else 0.0
)

chart_group = alt.Chart(group_agg).mark_arc(innerRadius=60).encode(
    theta=alt.Theta("market_value:Q", title="市值"),
    color=alt.Color("group:N", title="族群"),
    tooltip=[
        alt.Tooltip("group:N", title="族群"),
        alt.Tooltip("market_value:Q", title="市值", format=",.0f"),
        alt.Tooltip("weight:Q", title="佔比", format=".1%"),
    ],
)
st.altair_chart(chart_group, use_container_width=True)

# -------------------------
# 明細表（跨券商合併後）
# -------------------------
st.divider()
st.subheader("📋 持股明細（跨券商合併）")

display_df = merged[[
    "name", "symbol", "group", "shares", "avg_cost", "price",
    "market_value", "pnl", "pnl_pct", "weight",
]].sort_values("market_value", ascending=False)

st.dataframe(
    display_df.style.format({
        "avg_cost": "{:,.2f}",
        "price": "{:,.2f}",
        "market_value": "{:,.0f}",
        "pnl": "{:,.0f}",
        "pnl_pct": "{:.2%}",
        "weight": "{:.1%}",
    }),
    use_container_width=True,
)

# -------------------------
# 各券商持股明細
# -------------------------
st.divider()
st.subheader("🏦 各券商持股明細")

tabs = st.tabs(list(BROKERS.keys()))
for tab, broker_label in zip(tabs, BROKERS.keys()):
    with tab:
        broker_rows = raw_df[raw_df["broker_label"] == broker_label].copy()
        if broker_rows.empty:
            st.write("這個券商目前沒有持股")
            continue
        broker_rows["name"] = broker_rows["symbol"].map(lambda s: stock_names.get(s, s))
        broker_rows["market_value"] = broker_rows["shares"] * broker_rows["price"]
        st.dataframe(
            broker_rows[["name", "symbol", "shares", "cost", "price", "market_value"]]
            .style.format({
                "cost": "{:,.2f}",
                "price": "{:,.2f}",
                "market_value": "{:,.0f}",
            }),
            use_container_width=True,
        )