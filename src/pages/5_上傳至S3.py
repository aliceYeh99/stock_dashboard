import streamlit as st
import boto3
import os


st.title("☁️ 上傳至 S3")


# ============================================================
# 設定
# ============================================================

BUCKET_NAME = "tp1806002"

BROKERS = {
    "fubon": "富邦證券",
    "union": "聯邦證券",
    "yuanta": "元大證券",
    "employee": "員工信託"
}


# ============================================================
# 上傳
# ============================================================

if st.button(
    "☁️ 上傳所有資料",
    use_container_width=True
):

    s3 = boto3.client("s3")

    upload_count = 0


    # ========================================================
    # 股票資料
    # ========================================================

    st.subheader("📈 股票資料")

    for broker, broker_name in BROKERS.items():

        local_dir = os.path.join(
            "data",
            "stocks",
            broker
        )


        if not os.path.exists(local_dir):

            st.warning(
                f"{broker_name} 資料夾不存在"
            )

            continue


        for filename in [
            "portfolio.json"
        ]:

            local_path = os.path.join(
                local_dir,
                filename
            )


            if not os.path.exists(local_path):

                continue


            s3_key = (
                f"stock_dashboard/input/"
                f"{broker}/{filename}"
            )


            s3.upload_file(
                local_path,
                BUCKET_NAME,
                s3_key
            )


            upload_count += 1


            st.write(
                f"✅ {broker_name} / {filename}"
            )


    # ========================================================
    # 銀行資料
    # ========================================================

    st.subheader("🏦 銀行資料")

    bank_path = os.path.join(
        "data",
        "bank",
        "portfolio.json"
    )


    if os.path.exists(bank_path):

        s3_key = (
            "stock_dashboard/input/"
            "bank/portfolio.json"
        )


        s3.upload_file(
            bank_path,
            BUCKET_NAME,
            s3_key
        )


        upload_count += 1


        st.write(
            "✅ 銀行 / portfolio.json"
        )

    else:

        st.warning(
            "銀行資料不存在"
        )


    # ========================================================
    # 完成
    # ========================================================

    st.success(
        f"完成，共上傳 {upload_count} 個檔案"
    )