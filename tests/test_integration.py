"""
Integration Tests for Video Extractor Multi-Agent Race and Downloader.
"""

import os
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

# Add src to sys.path
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

try:
    from video_downloader.candidate import Candidate
    from video_downloader.downloader import download, safe_filename
    from video_downloader.router import identify
    from video_downloader.race_controller import ExtractionRaceController
except ImportError:
    from candidate import Candidate
    from downloader import download, safe_filename
    from router import identify
    from race_controller import ExtractionRaceController


class TestIntegration(unittest.TestCase):

    def test_safe_filename(self):
        dirty = 'My Video: Episode 1 / Part 2? *<Awesome>*'
        cleaned = safe_filename(dirty)
        self.assertNotIn(":", cleaned)
        self.assertNotIn("/", cleaned)
        self.assertNotIn("?", cleaned)
        self.assertNotIn("*", cleaned)
        self.assertNotIn("<", cleaned)
        self.assertNotIn(">", cleaned)

    def test_router_identification(self):
        r1 = identify("https://www.youtube.com/watch?v=dQw4w9WgXcQ")
        self.assertEqual(r1.platform, "youtube")

        r2 = identify("https://vimeo.com/12345678")
        self.assertEqual(r2.platform, "vimeo")

        r3 = identify("https://example.com/video/page")
        self.assertEqual(r3.platform, "generic")

    @patch("subprocess.run")
    def test_downloader_ffmpeg_execution(self, mock_subproc):
        mock_subproc.return_value = MagicMock(returncode=0)

        candidate = Candidate(
            url="https://example.com/test_stream.m3u8",
            source="scrapling",
            extension=".m3u8",
            mime_type="application/x-mpegURL",
            score=100,
            metadata={"title": "Integration Test Video"}
        )

        output_path = download(candidate, filename="custom_name")
        self.assertTrue(output_path.endswith(".mp4"))
        mock_subproc.assert_called_once()
        cmd_args = mock_subproc.call_args[0][0]
        self.assertEqual(cmd_args[0], "ffmpeg")
        self.assertIn("https://example.com/test_stream.m3u8", cmd_args)
        self.assertIn("-c", cmd_args)
        self.assertIn("copy", cmd_args)

    @patch("video_downloader.site_extractor.download")
    def test_downloader_ytdlp_execution(self, mock_ytdlp_dl):
        mock_ytdlp_dl.return_value = True

        candidate = Candidate(
            url="https://example.com/watch?v=abc",
            source="ytdlp",
            score=100,
            metadata={"title": "YTDLP Video", "engine": "ytdlp"}
        )

        output_path = download(candidate, filename="ytdlp_name", requested_quality="720p")
        self.assertIsNotNone(output_path)
        mock_ytdlp_dl.assert_called_once_with("https://example.com/watch?v=abc", "720p")
        # Ensure it returns an mp4 filepath, not a directory
        self.assertTrue(output_path.endswith(".mp4"))


if __name__ == "__main__":
    unittest.main()
