import unittest
from pathlib import Path
import tempfile
from PIL import Image

from video_downloader.converter import (
    convert_image,
    convert_text_to_pdf,
    parse_ffmpeg_time,
)


class TestConverterExtended(unittest.TestCase):
    def test_parse_ffmpeg_time(self):
        line = "frame=  120 fps= 24 q=-0.0 size=    1024kB time=00:01:23.45 bitrate= 100.0kbits/s"
        t = parse_ffmpeg_time(line)
        self.assertAlmostEqual(t, 83.45, places=2)

    def test_convert_image_png_to_jpg(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            src = Path(tmp_dir) / "test.png"
            dst = Path(tmp_dir) / "test.jpg"
            img = Image.new("RGBA", (100, 100), (255, 0, 0, 255))
            img.save(src)

            res = convert_image(src, dst)
            self.assertTrue(dst.is_file())
            self.assertEqual(res, dst)

    def test_convert_text_to_pdf(self):
        with tempfile.TemporaryDirectory() as tmp_dir:
            txt_path = Path(tmp_dir) / "notes.txt"
            pdf_path = Path(tmp_dir) / "notes.pdf"

            txt_path.write_text("Title: Extractor Test\nLine 1: Sample text\nLine 2: Another line", encoding="utf-8")

            res = convert_text_to_pdf(txt_path, pdf_path)
            self.assertTrue(pdf_path.is_file())
            self.assertGreater(pdf_path.stat().st_size, 0)
            self.assertEqual(res, pdf_path)


if __name__ == "__main__":
    unittest.main()
