import yfinance as yf

from datetime import datetime

from utils.storage import (
    load_json,
    save_json
)


def update_current_prices(broker):


    selected = load_json(
        "selected.json",
        [],
        broker
    )


    prices = {}


    for symbol in selected:

        ticker = yf.Ticker(symbol)

        data = ticker.history(
            period="1d",
            interval="1m"
        )


        if not data.empty:

            price = float(
                data["Close"].iloc[-1]
            )


            prices[symbol] = {

                "price": price,

                "date": datetime.now()
                        .strftime("%Y-%m-%d"),

                "time": datetime.now()
                        .strftime("%H:%M:%S")
            }


    save_json(
        "current_prices.json",
        prices,
        broker
    )


    return prices