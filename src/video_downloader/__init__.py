"""
Video Extractor (video_downloader)
High-performance concurrent multi-agent video and stream extractor CLI tool.
"""

from .utils import get_version

__version__ = get_version()

_LAZY_EXPORTS = {
    "Candidate": ".candidate",
    "download": ".downloader",
    "identify": ".router",
    "describe": ".router",
    "ExtractionRaceController": ".race_controller",
    "RaceResult": ".race_controller",
    "ScraplingScanner": ".scrapling_scanner",
    "extract_info": ".site_extractor",
    "StaticScanner": ".static_scanner",
    "BrowserScanner": ".browser_scanner",
    "detect_platform": ".terminal_launcher",
    "spawn_tier": ".terminal_launcher",
    "kill_process_by_pid": ".terminal_launcher",
    "load_config": ".utils",
    "save_config": ".utils",
    "write_history": ".utils",
    "get_download_dir": ".utils",
    "run_interactive_menu": ".menu",
    "resolve_file_conflict": ".conflict_resolver",
    "generate_unique_path": ".conflict_resolver",
    "convert_video_to_gif": ".converter",
    "convert_video_to_audio": ".converter",
    "convert_audio_to_audio": ".converter",
    "convert_gif_to_mp4": ".converter",
    "convert_image": ".converter",
    "convert_text_to_pdf": ".converter",
    "scrape_and_download_comic": ".comic_scraper",
    "images_to_pdf": ".packager",
    "images_to_cbz": ".packager",
    "run_ocr": ".ocr",
    "extract_text_from_image": ".ocr",
    "launch_web_previewer": ".previewer",
}

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
    "save_config",
    "write_history",
    "get_download_dir",
    "run_interactive_menu",
    "resolve_file_conflict",
    "generate_unique_path",
    "convert_video_to_gif",
    "convert_video_to_audio",
    "convert_audio_to_audio",
    "convert_gif_to_mp4",
    "convert_image",
    "convert_text_to_pdf",
    "scrape_and_download_comic",
    "images_to_pdf",
    "images_to_cbz",
    "run_ocr",
    "extract_text_from_image",
    "launch_web_previewer",
]


def __getattr__(name: str):
    """Lazily load submodules upon attribute access to ensure instantaneous CLI startup."""
    if name in _LAZY_EXPORTS:
        import importlib
        module = importlib.import_module(_LAZY_EXPORTS[name], package=__package__)
        val = getattr(module, name)
        globals()[name] = val
        return val
    raise AttributeError(f"module {__name__!r} has no attribute {name!r}")


def __dir__():
    return __all__
