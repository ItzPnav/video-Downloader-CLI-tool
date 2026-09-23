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


def get_download_dir():

    config = load_config()
    target = config.get("download_directory", "")

    if target:
        p = Path(target)

        # On Termux or if path exists
        if p.exists():
            return p

        # On Windows non-Termux, convert /sdcard/Download to local project folder
        if str(target).startswith(("/sdcard", "\\sdcard")):
            if not Path("/sdcard").exists():
                fallback = ROOT / "downloaded-video"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback

        # Relative paths
        if not p.is_absolute():
            resolved = (ROOT / p).resolve()
            resolved.mkdir(parents=True, exist_ok=True)
            return resolved

        p.mkdir(parents=True, exist_ok=True)
        return p

    default_dir = ROOT / "downloaded-video"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def get_version():

    try:
        if VERSION_PATH.exists():
            return VERSION_PATH.read_text(
                encoding="utf-8"
            ).strip()
        config = load_config()
        return config.get("version", "0.2.0")

    except Exception:
        return "0.2.0"


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
