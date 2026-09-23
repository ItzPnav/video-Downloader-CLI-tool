"""
Tests for Scrapling Scanner Tier.
"""

import unittest
from unittest.mock import MagicMock, patch
import sys
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from video_downloader.scrapling_scanner import ScraplingScanner, SCRAPLING_AVAILABLE
    from video_downloader.candidate import Candidate
except ImportError:
    from scrapling_scanner import ScraplingScanner, SCRAPLING_AVAILABLE
    from candidate import Candidate


class TestScraplingScanner(unittest.TestCase):

    def setUp(self):
        self.sample_html = """
        <!DOCTYPE html>
        <html>
        <head>
            <script type="application/ld+json">
            {
                "@context": "https://schema.org",
                "@type": "VideoObject",
                "name": "Sample Video",
                "contentUrl": "https://example.com/media/ld_video.mp4"
            }
            </script>
            <script>
                var streamUrl = "https://example.com/live/playlist.m3u8";
            </script>
        </head>
        <body>
            <video src="https://example.com/media/direct.mp4">
                <source src="https://example.com/media/source_stream.m3u8" type="application/x-mpegURL">
            </video>
            <iframe src="https://example.com/embed/player?vid=999"></iframe>
            <div data-video="https://example.com/media/custom_attr.webm"></div>
        </body>
        </html>
        """

    def test_scrapling_available(self):
        self.assertTrue(SCRAPLING_AVAILABLE, "Scrapling library should be available")

    def test_dom_and_regex_extraction(self):
        scanner = ScraplingScanner("https://example.com/test-page")
        candidates = scanner.scan_html(self.sample_html, base_url="https://example.com/test-page")

        self.assertGreater(len(candidates), 0)
        urls = [c.url for c in candidates]

        # Check video tag candidate
        self.assertIn("https://example.com/media/direct.mp4", urls)
        # Check source stream candidate
        self.assertIn("https://example.com/media/source_stream.m3u8", urls)
        # Check iframe candidate
        self.assertIn("https://example.com/embed/player?vid=999", urls)
        # Check custom attribute candidate
        self.assertIn("https://example.com/media/custom_attr.webm", urls)
        # Check JSON-LD candidate
        self.assertIn("https://example.com/media/ld_video.mp4", urls)
        # Check JS regex candidate
        self.assertIn("https://example.com/live/playlist.m3u8", urls)

    def test_blocked_detection(self):
        scanner = ScraplingScanner("https://example.com")

        mock_blocked_resp = MagicMock()
        mock_blocked_resp.status = 403
        mock_blocked_resp.text = "Forbidden"
        self.assertTrue(scanner.is_blocked(mock_blocked_resp))

        mock_cf_resp = MagicMock()
        mock_cf_resp.status = 200
        mock_cf_resp.text = "Just a moment... Enable JavaScript to verify you are human."
        self.assertTrue(scanner.is_blocked(mock_cf_resp))

        mock_ok_resp = MagicMock()
        mock_ok_resp.status = 200
        mock_ok_resp.text = "<html><body>Welcome to video site</body></html>"
        self.assertFalse(scanner.is_blocked(mock_ok_resp))

    def test_markdown_fallback(self):
        empty_dom_html = """
        <html><body>
        <p>Watch our video <a href="https://example.com/clean/markdown_video.mp4">here</a>!</p>
        </body></html>
        """
        scanner = ScraplingScanner("https://example.com/md-page")
        candidates = scanner.scan_html(empty_dom_html, base_url="https://example.com/md-page")
        urls = [c.url for c in candidates]
        self.assertIn("https://example.com/clean/markdown_video.mp4", urls)


if __name__ == "__main__":
    unittest.main()
