# utils/download_stock.py
import os
import json
from datetime import datetime, timedelta

import yfinance as yf


# -------------------------
# 設定
# -------------------------

DATA_DIR = "data/stocks/download"

DAYS = 430


# -------------------------
# DataStorage
# -------------------------

class DataStorage:

    def load_json(
        self,
        file_path,
        date_key="Date"
    ):
        """
        讀取本地 JSON
        """

        if not os.path.exists(file_path):
            return []

        with open(
            file_path,
            "r",
            encoding="utf-8"
        ) as f:

            old_data = json.load(f)


        if (
            old_data
            and isinstance(old_data, list)
        ):

            old_data = sorted(
                old_data,
                key=lambda x: x[date_key]
            )


        return old_data


    def merge_json(
        self,
        json_data,
        file_path,
        date_key="Date"
    ):
        """
        新舊資料依 Date merge
        新資料覆蓋舊資料
        """

        new_data = json.loads(
            json_data
        )


        old_data = self.load_json(
            file_path,
            date_key
        )


        # -------------------------
        # Date 當 key
        # -------------------------

        merged = {
            item[date_key]: item
            for item in old_data
        }


        for item in new_data:

            merged[item[date_key]] = item


        # -------------------------
        # 排序
        # -------------------------

        result = sorted(
            merged.values(),
            key=lambda x: x[date_key]
        )


        json_result = json.dumps(
            result,
            ensure_ascii=False,
            indent=4
        )


        self.save_json(
            json_result,
            file_path
        )


    def save_json(
        self,
        json_data,
        file_path
    ):
        """
        儲存本地 JSON
        """

        os.makedirs(
            os.path.dirname(file_path),
            exist_ok=True
        )


        print(
            f"💾 儲存 JSON：{file_path}"
        )


        with open(
            file_path,
            "w",
            encoding="utf-8"
        ) as f:

            f.write(
                json_data
            )


# -------------------------
# 下載單支股票
# -------------------------

def download_stock(
    symbol,
    days=DAYS
):

    storage = DataStorage()


    file_path = os.path.join(
        DATA_DIR,
        f"{symbol}.json"
    )


    print()
    print("=" * 60)
    print(f"📈 {symbol}")
    print("=" * 60)


    # -------------------------
    # 讀舊資料
    # -------------------------

    old_data = storage.load_json(
        file_path
    )


    # -------------------------
    # 第一次下載
    # -------------------------

    if not old_data:

        print(
            f"📥 找不到舊資料，下載最近 {days} 天"
        )


        df = yf.Ticker(
            symbol
        ).history(
            period=f"{days}d",
            auto_adjust=False
        )


    # -------------------------
    # 增量下載
    # -------------------------

    else:

        last_date = old_data[-1]["Date"]


        print(
            f"📅 最後資料：{last_date}"
        )


        last_datetime = datetime.strptime(
            last_date,
            "%Y-%m-%d"
        )


        start_date = (
            last_datetime
            + timedelta(days=1)
        ).strftime(
            "%Y-%m-%d"
        )


        today = datetime.now().date()


        # 已經有今天以前的資料
        if (
            datetime.strptime(
                start_date,
                "%Y-%m-%d"
            ).date()
            > today
        ):

            print(
                "✅ 已經是最新資料，不需要下載"
            )

            return


        print(
            f"📥 增量下載：{start_date} → 今天"
        )


        df = yf.Ticker(
            symbol
        ).history(
            start=start_date,
            end=(
                today
                + timedelta(days=1)
            ).strftime("%Y-%m-%d"),
            auto_adjust=False
        )


    # -------------------------
    # 沒有資料
    # -------------------------

    if df.empty:

        print(
            "⚠️ Yahoo 沒有回傳資料"
        )

        return


    # -------------------------
    # DataFrame → JSON 格式
    # -------------------------

    df = df.reset_index()


    df["Date"] = (
        df["Date"]
        .dt.strftime("%Y-%m-%d")
    )


    # -------------------------
    # 不計算 MA
    # 只保存原始資料
    # -------------------------

    stock_data_json = df.to_json(
        orient="records"
    )


    # -------------------------
    # Merge
    # -------------------------

    storage.merge_json(
        stock_data_json,
        file_path,
        date_key="Date"
    )


    print(
        f"✅ {symbol} 更新完成"
    )

    print(
        f"   本次取得：{len(df)} 筆"
    )


# -------------------------
# 更新全部股票
# -------------------------

def update_stocks(
    symbols
):

    total = len(symbols)


    print()
    print(
        "=" * 60
    )

    print(
        f"📥 開始更新股票資料：{total} 檔"
    )

    print(
        "=" * 60
    )


    for idx, symbol in enumerate(
        sorted(symbols),
        start=1
    ):

        print(
            f"\n🔄 [{idx}/{total}] {symbol}"
        )


        try:

            download_stock(
                symbol
            )

        except Exception as e:

            print(
                f"❌ {symbol} 下載失敗：{e}"
            )


    print()
    print(
        "=" * 60
    )

    print(
        "✅ 全部股票更新完成"
    )

    print(
        "=" * 60
    )