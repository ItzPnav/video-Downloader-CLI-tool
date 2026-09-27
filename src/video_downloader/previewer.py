"""
Web Video Previewer Launcher for Video Extractor CLI.
Opens the standalone HTML5 video previewer in the user's default web browser.
"""

import os
import sys
import webbrowser
from pathlib import Path
from typing import Optional
from urllib.parse import quote

from .cli import system_open


def get_previewer_html_path() -> Path:
    """Return the absolute path to the bundled previewer index.html."""
    return Path(__file__).parent / "previewer" / "index.html"


def launch_web_previewer(initial_url: Optional[str] = None) -> bool:
    """
    Launch the web previewer in default web browser, optionally pre-populating target URL.
    """
    html_path = get_previewer_html_path()
    if not html_path.is_file():
        print(f"[-] Previewer assets not found at: {html_path}")
        return False

    uri = html_path.as_uri()
    if initial_url:
        uri += f"?url={quote(initial_url, safe=':/?&=#')}"

    try:
        opened = webbrowser.open(uri)
        if not opened:
            # Fallback to system_open
            system_open(html_path)
        return True
    except Exception as e:
        print(f"[-] Failed to launch previewer in browser: {e}")
        return False
