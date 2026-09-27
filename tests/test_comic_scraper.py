import unittest
from pathlib import Path
import tempfile

from video_downloader.comic_scraper import (
    extract_images_from_html,
    get_html_title,
    is_allowed_by_robots,
)


class TestComicScraper(unittest.TestCase):
    def test_extract_images_from_html(self):
        sample_html = """
        <html>
        <head><title>Test Comic - Chapter 1</title></head>
        <body>
            <img src="images/01.jpg" />
            <img data-src="https://example.com/images/02.png" />
            <a href="images/03.webp">Next</a>
            <div style="background-image: url('images/04.jpg');"></div>
        </body>
        </html>
        """
        urls = extract_images_from_html(sample_html, base_url="https://example.com/chapter/")
        self.assertEqual(len(urls), 4)
        self.assertIn("https://example.com/chapter/images/01.jpg", urls)
        self.assertIn("https://example.com/images/02.png", urls)
        self.assertIn("https://example.com/chapter/images/03.webp", urls)
        self.assertIn("https://example.com/chapter/images/04.jpg", urls)

    def test_get_html_title(self):
        html = "<html><head><title>Super Hero Manga - Read Online Free</title></head><body></body></html>"
        title = get_html_title(html)
        self.assertIn("Super Hero Manga", title)


if __name__ == "__main__":
    unittest.main()
