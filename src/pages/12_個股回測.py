import streamlit as st
import pandas as pd
import altair as alt

from datetime import datetime
from symbols import SYMBOLS
from utils.backtest.engine import run_backtest
from utils.backtest.strategies import STRATEGY_MAP
from utils.storage import *

st.title("📈 個股回測（不同股票與族群比較）")
st.caption("固定同一個策略，比較不同股票或整個族群資產曲線變化（每支股票各自獨立回測、各自一筆本金，不共用資金池）")

stock_names = load_root_json("stock_names.json", {})

DEV_SYMBOLS = SYMBOLS

# -------------------------
# 定義常見族群個股清單
# -------------------------
INDUSTRY_GROUPS = {
    "自訂 / 自選股票": [],
    "被動元件": [
        "2327.TW",  # 國巨
        "2492.TW",  # 華新科
        "3026.TW",  # 禾伸堂
        "6173.TWO", # 信昌電
        "8042.TWO", # 金山電
        "8043.TWO", # 蜜望實
        "5328.TWO", # 華容
        "2472.TW",  # 立隆電
        "3090.TW",  # 日電貿
        "3357.TWO"  # 臺慶科
    ],
    "記憶體族群": [
        "2408.TW",  # 南亞科
        "2337.TW",  # 旺宏
        "2344.TW",  # 華邦電
        "3260.TWO", # 威剛
        "8299.TWO", # 群聯
        "3006.TW",  # 晶豪科
        "2451.TW",  # 創見
        "3532.TW",  # 台勝科
    ],
    "IC設計族群": [
        "2454.TW",  # 聯發科
        "3034.TW",  # 聯詠
        "2379.TW",  # 瑞昱
        "3035.TW",  # 智原
        "3443.TW",  # 創意
        "3661.TW",  # 世芯-KY
        "6415.TW",  # 矽力*-KY
        "4966.TW",  # 譜瑞-KY
        "8016.TW",  # 矽創
        "3529.TWO", # 力旺
    ],
    "晶圓代工/半導體龍頭": [
        "2330.TW",  # 台積電
        "2303.TW",  # 聯電
        "5347.TWO", # 世界
        "6770.TW",  # 力積電
    ],
    "AI / 伺服器代工": [
        "2317.TW",  # 鴻海
        "2382.TW",  # 廣達
        "3231.TW",  # 緯創
        "6669.TW",  # 緯穎
        "2356.TW",  # 英業達
        "2301.TW",  # 光寶科
    ]
}

# -------------------------
# 選擇族群與股票
# -------------------------
st.divider()
st.subheader("📌 選擇族群或股票")

# 1. 族群下拉選單
selected_group = st.selectbox(
    "選擇族群（選擇後自動載入該族群個股）",
    options=list(INDUSTRY_GROUPS.keys()),
    index=0
)

# -------------------------
# 固定策略
# -------------------------
strategy_name = st.selectbox(
    "策略（固定用同一個策略比較不同股票）",
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


# 計算預設選取的股票
if selected_group == "自訂 / 自選股票":
    default_symbols = [s for s in ["2330.TW", "0050.TW", "2454.TW", "2308.TW", "6488.TWO", "2327.TW", "2337.TW"] if s in DEV_SYMBOLS]
else:
    default_symbols = [s for s in INDUSTRY_GROUPS[selected_group] if s in DEV_SYMBOLS]

# 2. 股票多選選單
selected_symbols = st.multiselect(
    "股票（可從清單新增或刪減，每一支都會各自畫一條資產曲線）",
    options=DEV_SYMBOLS,
    default=default_symbols,
    format_func=lambda s: f"{stock_names.get(s, '')} ({s})",
    key=f"single_stock_symbols_{selected_group}",
)

# -------------------------
# 回測區間 / 本金
# -------------------------
st.divider()
col1, col2, col3 = st.columns(3)

with col1:
    start_date = st.date_input("開始日期", value=datetime(2025, 3, 20))

with col2:
    end_date = st.date_input("結束日期", value=datetime.now())

with col3:
    initial_capital = st.number_input("每支股票的初始資金", value=2_500_000, step=10_000)

# -------------------------
# 執行回測
# -------------------------
if st.button("🚀 開始回測比較", use_container_width=True):

    if not selected_symbols:
        st.warning("請至少選擇一支股票")
        st.stop()

    results = {}
    with st.spinner("回測中..."):
        for sym in selected_symbols:
            results[sym] = run_backtest(
                symbols=[sym],
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

    valid_results = {sym: r for sym, r in results.items() if r["metrics"] is not None}
    if not valid_results:
        st.error("沒有任何股票有資料可回測")
        st.stop()

    # 排序：依照「總報酬率」從高到低重新排序 valid_results
    sorted_syms = sorted(
        valid_results.keys(),
        key=lambda sym: valid_results[sym]["metrics"]["total_return"],
        reverse=True
    )
    valid_results = {sym: valid_results[sym] for sym in sorted_syms}

    def label(sym):
        return f"{stock_names.get(sym, '')} ({sym})"

    st.divider()
    st.subheader("📊 績效指標對照（已依總報酬率高至低排序）")

    # 建立 DataFrame 並排序表格顯示
    metrics_table = pd.DataFrame({
        label(sym): {
            "最終資產": r["metrics"]["final_equity"],
            "總報酬率": r["metrics"]["total_return"],
            "CAGR": r["metrics"]["cagr"],
            "Sharpe": r["metrics"]["sharpe"],
            "最大回撤": r["metrics"]["max_dd"],
        }
        for sym, r in valid_results.items()
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
    for sym, r in valid_results.items():
        equity = r["equity"]
        chart_frames.append(pd.DataFrame({
            "日期": pd.to_datetime(equity.index),
            "資產": equity.values,
            "股票": label(sym),
        }))

    chart_df = pd.concat(chart_frames, ignore_index=True)

    chart = alt.Chart(chart_df).mark_line().encode(
        x=alt.X("日期:T", axis=alt.Axis(format="%Y/%m/%d", title="日期")),
        y=alt.Y("資產:Q", title="資產"),
        color=alt.Color("股票:N", title="股票"),
        tooltip=[
            alt.Tooltip("日期:T", format="%Y/%m/%d"),
            alt.Tooltip("股票:N"),
            alt.Tooltip("資產:Q", format=",.0f"),
        ],
    ).interactive()

    st.altair_chart(chart, use_container_width=True)

    st.divider()
    st.subheader("📋 交易紀錄（依績效順序排列）")

    tabs = st.tabs([label(sym) for sym in valid_results.keys()])
    for tab, (sym, r) in zip(tabs, valid_results.items()):
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