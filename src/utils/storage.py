import json
import os


BASE_DIR = "data/stocks"

def get_root_path(
    filename
):

    path = os.path.join(
        BASE_DIR,
        filename
    )

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    return path

def get_path(
    filename,
    broker
):

    path = os.path.join(
        BASE_DIR,
        broker,
        filename
    )

    os.makedirs(
        os.path.dirname(path),
        exist_ok=True
    )

    return path


def load_json(
    filename,
    default,
    broker
):

    path = get_path(
        filename,
        broker
    )

    print(f"path={path}")


    if not os.path.exists(path):
        return default


    with open(
        path,
        "r",
        encoding="utf8"
    ) as f:

        return json.load(f)


def load_root_json(
    filename,
    default
):

    path = get_root_path(
        filename
    )

    print(f"path={path}")


    if not os.path.exists(path):
        return default


    with open(
        path,
        "r",
        encoding="utf8"
    ) as f:

        return json.load(f)

def save_json(
    filename,
    data,
    broker
):

    path = get_path(
        filename,
        broker
    )


    with open(
        path,
        "w",
        encoding="utf8"
    ) as f:

        json.dump(
            data,
            f,
            indent=4,
            ensure_ascii=False
        )

