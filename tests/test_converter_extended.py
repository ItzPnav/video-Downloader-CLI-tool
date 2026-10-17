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
    def test_combine_videos_validation(self):
        from video_downloader.converter import combine_videos
        with self.assertRaises(ValueError):
            combine_videos([], "output.mp4")

        with self.assertRaises(FileNotFoundError):
            combine_videos(["non_existent_1.mp4", "non_existent_2.mp4"], "output.mp4")

    def test_combine_videos_execution(self):
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import combine_videos

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            out = Path(tmp_dir) / "merged.mp4"

            v1.write_bytes(b"dummy video 1")
            v2.write_bytes(b"dummy video 2")

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.get_media_duration", return_value=10.0), \
                 patch("subprocess.Popen") as mock_popen:
                    mock_proc = MagicMock()
                    mock_proc.returncode = 0
                    mock_proc.stderr = []
                    mock_popen.return_value = mock_proc

                    # Simulate output file creation by ffmpeg
                    def _side_effect(*args, **kwargs):
                        out.write_bytes(b"combined video content")
                        return mock_proc

                    mock_popen.side_effect = _side_effect

                    res = combine_videos([v1, v2], out)
                    self.assertTrue(out.is_file())
                    self.assertEqual(res, out)
                    mock_popen.assert_called_once()
                    called_cmd = mock_popen.call_args[0][0]
                    self.assertEqual(called_cmd[0], "ffmpeg")
                    self.assertIn("concat", called_cmd)
                    self.assertIn("copy", called_cmd)


if __name__ == "__main__":
    unittest.main()

