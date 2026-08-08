import json
from pathlib import Path


DEFAULT_BROKER = "fubon"
CONFIG_FILE = Path("data/stocks/user_config.json")


BROKERS = {
    "富邦證券":"fubon",
    "聯邦證券":"union",
    "元大證券":"yuanta",
    "員工信託":"employee"
}

FEE_RATES = {
    "富邦證券": 0,
    "聯邦證券":0.141/100,
    "元大證券":0,
    "員工信託":0
}

def load_default_broker():
    ##
    if not CONFIG_FILE.exists():
        return "CONFIG_FILE 不存在"

    with open(
        CONFIG_FILE,
        "r",
        encoding="utf-8"
    ) as f:
        config = json.load(f)
    
    return config.get(
        "broker",
        "fubon"
    )


DEFAULT_BROKER = load_default_broker()
