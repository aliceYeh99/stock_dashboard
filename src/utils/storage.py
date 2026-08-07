import json
import os

DATA_DIR = "data"

os.makedirs(DATA_DIR, exist_ok=True)


def load_json(filename, default):

    path = os.path.join(DATA_DIR, filename)

    if not os.path.exists(path):
        return default

    with open(path, "r", encoding="utf8") as f:
        return json.load(f)


def save_json(filename, data):

    path = os.path.join(DATA_DIR, filename)

    with open(path, "w", encoding="utf8") as f:
        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )