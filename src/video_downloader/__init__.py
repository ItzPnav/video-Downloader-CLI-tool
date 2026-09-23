"""
Video Extractor (video_downloader)
High-performance concurrent multi-agent video and stream extractor CLI tool.
"""

from .candidate import Candidate
from .downloader import download
from .router import identify, describe
from .race_controller import ExtractionRaceController, RaceResult
from .scrapling_scanner import ScraplingScanner
from .site_extractor import extract_info
from .static_scanner import StaticScanner
from .browser_scanner import BrowserScanner
from .terminal_launcher import detect_platform, spawn_tier, kill_process_by_pid
from .utils import get_version, load_config, write_history, get_download_dir

__version__ = get_version()
__all__ = [
    "Candidate",
    "download",
    "identify",
    "describe",
    "ExtractionRaceController",
    "RaceResult",
    "ScraplingScanner",
    "extract_info",
    "StaticScanner",
    "BrowserScanner",
    "detect_platform",
    "spawn_tier",
    "kill_process_by_pid",
    "get_version",
    "load_config",
    "write_history",
    "get_download_dir",
]
