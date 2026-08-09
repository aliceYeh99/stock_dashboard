架構化回測系統，整合JSON資料載入與MACD策略模組。

我把之前那支肥大的 multi_backtest.py拆乾淨了，改成「一策略一檔案、資料讀本地 JSON」的架構。先建好整套檔案給你。


Created 8 files, ran 4 commands, read a file
Created 8 files, ran 4 commands, read a file
放置方式：把這些檔案照原本路徑丟進你的專案（utils/backtest/ 整包、pages/8_回測.py），資料夾結構跟你現有的 utils/ pages/ 是同一層。

架構重點：

data.py — 只讀本地 data/stocks/download/{symbol}.json，不下載，跟你的 4_下載.py 完全分工
portfolio.py / metrics.py — 從舊 multi_backtest.py 原封不動搬過來，邏輯沒動，只是拆開
strategies/macd.py — 第一支策略，只有 signal() + META（名稱、參數）兩個東西
strategies/__init__.py — 策略註冊表，之後每加一個策略（例如你之前那支「季線/半年線+MACD」），流程固定兩步：新增檔案 → STRATEGY_MAP 加一行，8_回測.py 完全不用改，選單跟參數欄位是自動長出來的
engine.py — 核心迴圈，跟舊版邏輯一致（T日訊號、T+1開盤成交、現金池共用），但拿掉了存 CSV / 畫 matplotlib，畫圖交給 Streamlit
pages/8_回測.py 目前股票清單是寫死的 ["2330.TW", "2454.TW"]（你說開發時先放兩支），之後要接「挑股清單」的話，把那行換成 load_json("selected.json", [], broker) 就好，其他都不用改。

有個地方要跟你確認一下：舊程式的 JSON 資料你範例欄位是 Adj Close、Dividends、Stock Splits，我在 data.py 只取了 Open/High/Low/Close/Volume，因為回測邏輯只需要這些。如果你的資料有配息除權息，之後要不要改用 Adj Close 算報酬率（比較準確但邏輯要調），可以之後再說。