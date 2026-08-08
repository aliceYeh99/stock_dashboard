# common/telegram.py
import json
import os
import traceback
import urllib.request
from io import BytesIO


def send_photo(photo_url, bot_token, chat_id):
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"

    data = {
        "chat_id": chat_id,
        "photo": photo_url
    }

    req = urllib.request.Request(
        url,
        data=json.dumps(data).encode("utf-8"),
        headers={"Content-Type": "application/json"}
    )

    urllib.request.urlopen(req)

def send_telegram(message, bot_token, chat_id):

    url = f"https://api.telegram.org/bot{bot_token}/sendMessage"

    # 🌟 核心關鍵：檢查 message 是不是 list，如果是，用換行符號 \n 串起來
    if isinstance(message, list):
        message = "\n".join(map(str, message))

    elif isinstance(message, dict):
        message = json.dumps(message, ensure_ascii=False, indent=2)

    elif not isinstance(message, str):
        message = str(message)

    data = {
        "chat_id": chat_id,
        "text": message
    }
    
    print("\n")
    print(f"url: {url}\n")
    print(f" data: {data}   ")
    print(f" message: {message}   ")

    try:
        # ❌ 舊寫法（中文會變成 \u4f60\u597d）
        # req_data = json.dumps(data).encode("utf-8")
        req = urllib.request.Request(
            url,
             # ✅ 新寫法（保留原始中文 UTF-8 編碼）
            data=json.dumps(data, ensure_ascii=False).encode("utf-8"),
            headers={"Content-Type": "application/json"},
            method="POST"
        )

        with urllib.request.urlopen(req) as response:
            return response.read().decode()
    except Exception as e:
        print("Error message:", e)
        traceback.print_exc()


def send_telegram_photo_bytes(fig, bot_token, chat_id, caption=""):
    """將 Matplotlib/mplfinance 的 Figure 圖表轉成 Bytes，直接上傳至 Telegram"""
    # 1. 把圖表物件直接轉為記憶體內的 PNG Bytes
    img_buffer = BytesIO()
    fig.savefig(
        img_buffer,
        format="png",
        facecolor=fig.get_facecolor(),
        edgecolor="none",
        bbox_inches="tight",
    )
    img_bytes = img_buffer.getvalue()

    # 2. 建立 HTTP multipart/form-data 封包
    boundary = "----WebKitFormBoundary7MA4YWxkTrZu0gW"
    body = []

    # 欄位：chat_id
    body.extend(
        [
            f"--{boundary}".encode(),
            'Content-Disposition: form-data; name="chat_id"'.encode(),
            "".encode(),
            str(chat_id).encode(),
        ]
    )

    # 欄位：caption (選填)
    if caption:
        body.extend(
            [
                f"--{boundary}".encode(),
                'Content-Disposition: form-data; name="caption"'.encode(),
                "".encode(),
                caption.encode("utf-8"),
            ]
        )

    # 欄位：photo (圖片檔案 Bytes)
    body.extend(
        [
            f"--{boundary}".encode(),
            'Content-Disposition: form-data; name="photo"; filename="kline.png"'.encode(),
            "Content-Type: image/png".encode(),
            "".encode(),
            img_bytes,
        ]
    )

    body.extend([f"--{boundary}--".encode(), "".encode()])
    payload = b"\r\n".join(body)

    # 3. 發送 Request
    url = f"https://api.telegram.org/bot{bot_token}/sendPhoto"
    req = urllib.request.Request(
        url,
        data=payload,
        headers={"Content-Type": f"multipart/form-data; boundary={boundary}"},
        method="POST",
    )

    try:
        with urllib.request.urlopen(req) as response:
            return response.status == 200
    except Exception as e:
        print(f"Telegram 發送圖片失敗: {e}")
        return False