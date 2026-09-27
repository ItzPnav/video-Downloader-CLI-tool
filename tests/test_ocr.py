import unittest
from unittest.mock import patch, MagicMock
from pathlib import Path
import tempfile
from PIL import Image

from video_downloader.ocr import (
    natural_sort_key,
    extract_text_from_image,
    run_ocr,
    is_tesseract_available,
    IMAGE_EXTENSIONS,
)


class TestOcrEngine(unittest.TestCase):
    def test_natural_sort_key(self):
        files = ["page_10.jpg", "page_1.jpg", "page_2.jpg", "page_20.jpg"]
        sorted_files = sorted(files, key=natural_sort_key)
        self.assertEqual(sorted_files, ["page_1.jpg", "page_2.jpg", "page_10.jpg", "page_20.jpg"])

    def test_extract_text_mocked(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_path = Path(tmp_dir) / "test.png"
            img = Image.new("RGB", (100, 100), color="white")
            img.save(img_path)

            with patch("video_downloader.ocr.find_tesseract_binary", return_value="C:\\Tesseract\\tesseract.exe"), \
                 patch("video_downloader.ocr.PYTESSERACT_AVAILABLE", True), \
                 patch("pytesseract.image_to_string", return_value="Hello World from OCR"):
                text = extract_text_from_image(img_path)
                self.assertEqual(text, "Hello World from OCR")

    def test_run_ocr_batch_mocked(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            img_dir = Path(tmp_dir) / "images"
            img_dir.mkdir()
            out_dir = Path(tmp_dir) / "out"

            img1 = img_dir / "001.png"
            img2 = img_dir / "002.png"
            Image.new("RGB", (50, 50), "white").save(img1)
            Image.new("RGB", (50, 50), "white").save(img2)

            with patch("video_downloader.ocr.is_tesseract_available", return_value=True), \
                 patch("video_downloader.ocr.extract_text_from_image", side_effect=["Text 1", "Text 2"]):
                ok, out_path, preview = run_ocr(
                    target=img_dir,
                    output_dir=out_dir,
                    lang="eng",
                    combine_output=True,
                )
                self.assertTrue(ok)
                self.assertTrue(out_path.is_file())
                content = out_path.read_text(encoding="utf-8")
                self.assertIn("Text 1", content)
                self.assertIn("Text 2", content)


if __name__ == "__main__":
    unittest.main()
