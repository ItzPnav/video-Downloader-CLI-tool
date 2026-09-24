"""
Unit Tests for Interactive Terminal Menu & Navigation System.
"""

import os
import sys
import unittest
import tempfile
import json
from pathlib import Path
from unittest.mock import patch, MagicMock

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

# Force UTF-8 stream encoding on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from video_downloader.utils import load_config, save_config, get_download_dir
from video_downloader.menu import get_video_files, render_banner, render_menu_options, get_clipboard_text, read_key


class TestMenu(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_save_and_load_config(self):
        """Test configuration serialization and loading round-trip."""
        config_file = self.test_dir / "config.json"
        with patch("video_downloader.utils.get_config_dir", return_value=self.test_dir):
            custom_cfg = {
                "version": "0.2.0",
                "download_directory": str(self.test_dir / "custom_downloads"),
                "preferred_format": "bv*+ba/b",
                "merge_format": "mkv",
                "browser_wait_seconds": 8,
                "use_ytdlp": False,
                "use_static_scanner": True,
                "use_browser": False,
                "use_scrapling": True,
                "race_timeout": 15,
                "confidence_threshold": 60,
                "spawn_terminals": False,
                "browser_grace_seconds": 3.0,
            }
            saved = save_config(custom_cfg)
            self.assertTrue(saved)
            self.assertTrue(config_file.exists())

            loaded = load_config()
            self.assertEqual(loaded["merge_format"], "mkv")
            self.assertEqual(loaded["race_timeout"], 15)
            self.assertEqual(loaded["browser_grace_seconds"], 3.0)
            self.assertFalse(loaded["use_ytdlp"])
            self.assertFalse(loaded["use_browser"])

    def test_get_video_files_filtering(self):
        """Test scanning download directory for supported video files."""
        # Create dummy video and non-video files
        vid1 = self.test_dir / "sample1.mp4"
        vid2 = self.test_dir / "sample2.mkv"
        vid3 = self.test_dir / "sample3.webm"
        txt_file = self.test_dir / "notes.txt"
        img_file = self.test_dir / "thumbnail.jpg"

        vid1.write_bytes(b"dummy mp4 content")
        vid2.write_bytes(b"dummy mkv content")
        vid3.write_bytes(b"dummy webm content")
        txt_file.write_bytes(b"text file")
        img_file.write_bytes(b"image file")

        with patch("video_downloader.menu.get_download_dir", return_value=self.test_dir):
            videos = get_video_files()
            video_names = [v.name for v in videos]
            self.assertEqual(len(videos), 3)
            self.assertIn("sample1.mp4", video_names)
            self.assertIn("sample2.mkv", video_names)
            self.assertIn("sample3.webm", video_names)
            self.assertNotIn("notes.txt", video_names)
            self.assertNotIn("thumbnail.jpg", video_names)

    def test_render_banner_runs_cleanly(self):
        """Test banner rendering string formats without exception."""
        dummy_cfg = {
            "version": "0.2.0",
            "download_directory": str(self.test_dir),
            "use_ytdlp": True,
            "use_scrapling": True,
            "use_static_scanner": True,
            "use_browser": False,
            "race_timeout": 20,
            "browser_grace_seconds": 2.5,
            "merge_format": "mp4",
        }
        with patch("video_downloader.menu.get_download_dir", return_value=self.test_dir):
            # Should run without error
            render_banner(dummy_cfg)

    def test_render_menu_options(self):
        """Test option list rendering with selection highlight."""
        options = [
            ("📥", "Download Video", "Extract and download stream"),
            ("▶", "Open / Play Video", "Browse and launch"),
            ("🗑", "Clear Selected Videos", "Selective deletion"),
        ]
        # Should execute without error for index 0 and index 1
        render_menu_options(options, 0)
        render_menu_options(options, 1)

    def test_auto_open_setting_toggle_and_config(self):
        """Test auto_open configuration round-trip and defaults."""
        with patch("video_downloader.utils.get_config_dir", return_value=self.test_dir):
            # Default fallback includes auto_open: True
            loaded_default = load_config()
            self.assertTrue(loaded_default.get("auto_open", True))

            # Save auto_open: False
            loaded_default["auto_open"] = False
            self.assertTrue(save_config(loaded_default))

            # Reload and verify
            reloaded = load_config()
            self.assertFalse(reloaded["auto_open"])

            # Save auto_open: True
            reloaded["auto_open"] = True
            self.assertTrue(save_config(reloaded))
            self.assertTrue(load_config()["auto_open"])

    def test_clipboard_and_paste_detection(self):
        """Test clipboard text extraction and paste handling."""
        # get_clipboard_text should return a string or None, never crash
        clip = get_clipboard_text()
        self.assertTrue(clip is None or isinstance(clip, str))

        # Test Windows msvcrt simulated Ctrl+V and rapid paste
        if sys.platform == "win32":
            import msvcrt
            with patch("msvcrt.getch", return_value=b"\x16"):
                with patch("msvcrt.kbhit", return_value=False):
                    key = read_key()
                    self.assertEqual(key, "CTRL_V")

            # Simulated rapid URL stream
            url_bytes = [b"h", b"t", b"t", b"p", b"s", b":", b"/", b"/", b"t", b"e", b"s", b"t", b".", b"c", b"o", b"m"]
            call_idx = [0]
            def fake_getch():
                i = call_idx[0]
                call_idx[0] += 1
                if i < len(url_bytes):
                    return url_bytes[i]
                return b""

            def fake_kbhit():
                return call_idx[0] < len(url_bytes)

            with patch("msvcrt.getch", side_effect=fake_getch):
                with patch("msvcrt.kbhit", side_effect=fake_kbhit):
                    key = read_key()
                    self.assertEqual(key, "URL:https://test.com")


if __name__ == "__main__":
    unittest.main()
