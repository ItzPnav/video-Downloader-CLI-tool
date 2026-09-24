"""
Unit Tests for Download File Collision & Conflict Resolution System.
"""

import sys
import unittest
import tempfile
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

from video_downloader.candidate import Candidate
from video_downloader.conflict_resolver import (
    generate_unique_path,
    probe_file_info,
    get_incoming_info,
    resolve_file_conflict,
)
from video_downloader.downloader import download


class TestConflictResolver(unittest.TestCase):

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_generate_unique_path_non_existent(self):
        """If file does not exist, return original path."""
        target = self.base_dir / "video.mp4"
        self.assertEqual(generate_unique_path(target), target)

    def test_generate_unique_path_incrementing(self):
        """When files exist, increment (1), (2), (3)..."""
        file0 = self.base_dir / "my_video.mp4"
        file0.write_bytes(b"content 0")

        # First collision -> my_video (1).mp4
        res1 = generate_unique_path(file0)
        self.assertEqual(res1.name, "my_video (1).mp4")

        # Create my_video (1).mp4
        res1.write_bytes(b"content 1")

        # Second collision -> my_video (2).mp4
        res2 = generate_unique_path(file0)
        self.assertEqual(res2.name, "my_video (2).mp4")

    def test_probe_file_info(self):
        """Test reading local file stat information."""
        test_file = self.base_dir / "sample.mp4"
        test_file.write_bytes(b"A" * 1024 * 1024 * 2)  # 2MB

        info = probe_file_info(test_file)
        self.assertEqual(info["name"], "sample.mp4")
        self.assertEqual(info["format"], "MP4")
        self.assertTrue(info["exists"])
        self.assertIn("2.00 MB", info["size_str"])
        self.assertNotEqual(info["modified_str"], "Unknown")

    def test_get_incoming_info(self):
        """Test formatting incoming candidate stream info."""
        cand = Candidate(
            url="https://example.com/stream.m3u8",
            source="scrapling",
            score=95,
            metadata={
                "title": "Epic Stream",
                "filesize": 52428800,  # 50MB
                "height": 1080,
                "duration": 185,
            }
        )
        target = self.base_dir / "Epic Stream.mp4"
        info = get_incoming_info(cand, target, requested_quality="1080p")
        self.assertEqual(info["name"], "Epic Stream.mp4")
        self.assertIn("50.00 MB", info["size_str"])
        self.assertEqual(info["quality"], "1080p")
        self.assertEqual(info["duration"], "3:05")
        self.assertEqual(info["source"], "scrapling")

    def test_resolve_file_conflict_policies(self):
        """Test non-interactive override policies (replace, keep_both, skip)."""
        existing = self.base_dir / "test_file.mp4"
        existing.write_bytes(b"existing content")

        cand = Candidate(url="https://example.com/v.mp4", source="static", score=90)

        # Policy: replace
        p_replace = resolve_file_conflict(existing, cand, conflict_policy="replace")
        self.assertEqual(p_replace, existing)

        # Policy: keep_both
        p_keep = resolve_file_conflict(existing, cand, conflict_policy="keep_both")
        self.assertEqual(p_keep.name, "test_file (1).mp4")

        # Policy: skip
        p_skip = resolve_file_conflict(existing, cand, conflict_policy="skip")
        self.assertIsNone(p_skip)

    def test_resolve_file_conflict_non_interactive_fallback(self):
        """In non-interactive environments, default to safe keep_both."""
        existing = self.base_dir / "clip.mp4"
        existing.write_bytes(b"clip content")

        cand = Candidate(url="https://example.com/v.mp4", source="static", score=90)

        with patch("sys.stdin.isatty", return_value=False):
            resolved = resolve_file_conflict(existing, cand)
            self.assertEqual(resolved.name, "clip (1).mp4")

    @patch("subprocess.run")
    def test_downloader_with_skip_policy(self, mock_subproc):
        """Verify downloader returns None and does not execute ffmpeg when skipped."""
        existing = self.base_dir / "movie.mp4"
        existing.write_bytes(b"old movie")

        cand = Candidate(url="https://example.com/stream.m3u8", source="static", score=90, metadata={"title": "movie"})

        with patch("video_downloader.downloader.get_download_dir", return_value=self.base_dir):
            res = download(cand, requested_quality="1080p", conflict_policy="skip")
            self.assertIsNone(res)
            # ffmpeg should not have been called
            mock_subproc.assert_not_called()

    @patch("subprocess.run")
    def test_downloader_with_keep_both_policy(self, mock_subproc):
        """Verify downloader saves to incremented filename when keep_both is set."""
        existing = self.base_dir / "movie.mp4"
        existing.write_bytes(b"old movie")

        cand = Candidate(url="https://example.com/stream.m3u8", source="static", score=90, metadata={"title": "movie"})

        with patch("video_downloader.downloader.get_download_dir", return_value=self.base_dir):
            res = download(cand, requested_quality="1080p", conflict_policy="keep_both")
            self.assertIsNotNone(res)
            self.assertTrue(res.endswith("movie (1).mp4"))
            mock_subproc.assert_called_once()


if __name__ == "__main__":
    unittest.main()
