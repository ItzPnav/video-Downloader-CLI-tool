import json
import re
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent

CONFIG_PATH = ROOT / "config" / "config.json"

VERSION_PATH = ROOT / "VERSION"


def load_config():

    try:
        return json.loads(
            CONFIG_PATH.read_text(
                encoding="utf-8"
            )
        )

    except Exception:
        return {}


def get_version():

    try:
        return VERSION_PATH.read_text(
            encoding="utf-8"
        ).strip()

    except Exception:
        return "unknown"


def safe_filename(name):

    if not name:
        return "video"

    name = re.sub(
        r'[<>:"/\\|?*\x00-\x1f]',
        "_",
        str(name)
    )

    name = re.sub(
        r"\s+",
        " ",
        name
    ).strip()

    return name[:180] or "video"


def print_banner():

    print()
    print("=" * 60)
    print("                 VIDEO EXTRACTOR")
    print("=" * 60)
    print(f"                 v{get_version()}")
    print("=" * 60)
    print()


def print_step(number, total, message):

    print(
        f"[{number}/{total}] {message}"
    )


def write_history(data):

    history_file = (
        ROOT
        / "config"
        / "history.json"
    )

    try:

        if history_file.exists():

            history = json.loads(
                history_file.read_text(
                    encoding="utf-8"
                )
            )

        else:
            history = []

    except Exception:
        history = []

    history.append(data)

    history = history[-100:]

    history_file.write_text(
        json.dumps(
            history,
            indent=2,
            ensure_ascii=False
        ),
        encoding="utf-8"
    )
