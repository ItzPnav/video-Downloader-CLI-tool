import json
import os
import re
import sys
from pathlib import Path


ROOT = Path(__file__).resolve().parent.parent.parent

VERSION_PATH = ROOT / "VERSION"

DEFAULT_CONFIG = {
    "version": "0.2.0",
    "download_directory": "/sdcard/Download" if Path("/sdcard").exists() else str(Path.home() / "Downloads"),
    "preferred_format": "bv*+ba/b",
    "merge_format": "mp4",
    "browser_wait_seconds": 8,
    "use_ytdlp": True,
    "use_static_scanner": True,
    "use_browser": True,
    "use_scrapling": True,
    "race_timeout": 20,
    "confidence_threshold": 50,
    "spawn_terminals": False,
    "browser_grace_seconds": 2.5,
    "auto_open": True,
    "github": {
        "repository": "ItzPnav/video-Downloader-CLI-tool",
        "branch": "main"
    }
}



def get_config_dir() -> Path:
    """
    Get the directory containing configuration and history logs.
    Prioritizes local repo directory if running from source checkout,
    otherwise uses user's config directory (for pip-installed global package).
    """
    # Check if running in a local cloned git repo with config/
    repo_config_dir = ROOT / "config"
    if repo_config_dir.exists() and (repo_config_dir / "config.json").exists():
        return repo_config_dir

    # User environment config directory
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix:
        user_config = Path.home() / ".config" / "video-extractor"
    elif sys.platform == "win32":
        user_config = Path(os.environ.get("APPDATA", str(Path.home()))) / "video-extractor"
    else:
        user_config = Path(os.environ.get("XDG_CONFIG_HOME", str(Path.home() / ".config"))) / "video-extractor"

    try:
        user_config.mkdir(parents=True, exist_ok=True)
    except Exception:
        pass
    return user_config


def load_config() -> dict:
    """Load configuration dictionary, initializing defaults if missing."""
    config_dir = get_config_dir()
    config_path = config_dir / "config.json"

    if not config_path.exists():
        try:
            config_path.write_text(
                json.dumps(DEFAULT_CONFIG, indent=2, ensure_ascii=False),
                encoding="utf-8"
            )
            return DEFAULT_CONFIG.copy()
        except Exception:
            return DEFAULT_CONFIG.copy()

    try:
        loaded = json.loads(config_path.read_text(encoding="utf-8"))
        # Merge missing defaults
        merged = DEFAULT_CONFIG.copy()
        merged.update(loaded)
        return merged
    except Exception:
        return DEFAULT_CONFIG.copy()


def save_config(config_data: dict) -> bool:
    """Save configuration dictionary to config.json."""
    config_dir = get_config_dir()
    config_path = config_dir / "config.json"
    try:
        config_path.write_text(
            json.dumps(config_data, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
        return True
    except Exception as error:
        print(f"[!] Warning: Could not write configuration: {error}", file=sys.stderr)
        return False


def get_download_dir() -> Path:
    """
    Resolve the target download directory based on configuration and platform.
    Ensures safe fallbacks on non-Termux systems.
    """
    config = load_config()
    target = config.get("download_directory", "")

    if target:
        p = Path(target)

        # On Termux or if path exists
        if p.exists():
            return p

        # On Windows/Linux non-Termux, convert /sdcard/Download to user's Downloads directory
        if str(target).startswith(("/sdcard", "\\sdcard")):
            if not Path("/sdcard").exists():
                fallback = Path.home() / "Downloads"
                fallback.mkdir(parents=True, exist_ok=True)
                return fallback

        # Relative paths
        if not p.is_absolute():
            repo_download = ROOT / p
            if (ROOT / ".git").exists():
                repo_download.mkdir(parents=True, exist_ok=True)
                return repo_download
            fallback = Path.home() / p
            fallback.mkdir(parents=True, exist_ok=True)
            return fallback

        try:
            p.mkdir(parents=True, exist_ok=True)
            return p
        except Exception:
            pass

    # Default fallback
    if Path("/sdcard").exists():
        sdcard = Path("/sdcard/Download")
        sdcard.mkdir(parents=True, exist_ok=True)
        return sdcard

    default_dir = Path.home() / "Downloads"
    default_dir.mkdir(parents=True, exist_ok=True)
    return default_dir


def get_version() -> str:
    """Read the package version string."""
    try:
        if VERSION_PATH.exists():
            return VERSION_PATH.read_text(encoding="utf-8").strip()
        config = load_config()
        return config.get("version", "0.2.0")
    except Exception:
        return "0.2.0"


def safe_filename(name: str) -> str:
    """Sanitize string for safe filesystem usage across platforms."""
    if not name:
        return "video"

    name = re.sub(r'[<>:"/\\|?*\x00-\x1f]', "_", str(name))
    name = re.sub(r"\s+", " ", name).strip()
    return name[:180] or "video"


def print_banner() -> None:
    """Render terminal application header banner."""
    print()
    print("=" * 60)
    print("                 VIDEO EXTRACTOR")
    print("=" * 60)
    print(f"                 v{get_version()}")
    print("=" * 60)
    print()


def print_step(number: int, total: int, message: str) -> None:
    """Print numbered execution step indicator."""
    print(f"[{number}/{total}] {message}")


def write_history(data: dict) -> None:
    """
    Log download record to history.json.
    Maintains capped history of last 100 entries.
    """
    config_dir = get_config_dir()
    history_file = config_dir / "history.json"

    try:
        if history_file.exists():
            history = json.loads(history_file.read_text(encoding="utf-8"))
        else:
            history = []
    except Exception:
        history = []

    history.append(data)
    history = history[-100:]

    try:
        history_file.write_text(
            json.dumps(history, indent=2, ensure_ascii=False),
            encoding="utf-8"
        )
    except Exception as error:
        print(f"[!] Warning: Could not write download history: {error}", file=sys.stderr)
