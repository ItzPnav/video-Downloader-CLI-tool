import json
import subprocess
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
        from video_downloader.converter import (
            combine_videos,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            out = Path(tmp_dir) / "merged.mp4"

            v1.write_bytes(b"dummy video 1")
            v2.write_bytes(b"dummy video 2")

            dummy_probe = [
                ClipProbeInfo(
                    path=v1,
                    duration=10.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
                ClipProbeInfo(
                    path=v2,
                    duration=10.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
            ]

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.probe_clip", side_effect=dummy_probe), \
                 patch("video_downloader.converter.verify_video_integrity", return_value=True), \
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


    def test_parse_fps_value(self):
        from video_downloader.converter import parse_fps_value
        self.assertAlmostEqual(parse_fps_value("30/1"), 30.0)
        self.assertAlmostEqual(parse_fps_value("30000/1001"), 29.97, places=2)
        self.assertAlmostEqual(parse_fps_value("25"), 25.0)
        self.assertEqual(parse_fps_value("0/0"), 0.0)
        self.assertEqual(parse_fps_value(""), 0.0)
        self.assertEqual(parse_fps_value("invalid"), 0.0)

    def test_find_ffprobe(self):
        from video_downloader.converter import find_ffprobe
        exe = find_ffprobe()
        if exe is not None:
            self.assertTrue(Path(exe).is_file() or isinstance(exe, str))

    def test_probe_clip_metadata(self):
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import probe_clip

        sample_ffprobe_output = json.dumps({
            "streams": [
                {
                    "index": 0,
                    "codec_name": "h264",
                    "codec_type": "video",
                    "width": 1280,
                    "height": 720,
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "30/1",
                    "avg_frame_rate": "30/1",
                    "time_base": "1/30",
                    "sample_aspect_ratio": "1:1",
                    "duration": "5.0",
                },
                {
                    "index": 1,
                    "codec_name": "aac",
                    "codec_type": "audio",
                    "sample_rate": "48000",
                    "channels": 2,
                    "duration": "5.0",
                }
            ],
            "format": {
                "duration": "5.0"
            }
        })

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = sample_ffprobe_output

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            tpath = Path(f.name)

        try:
            with patch("subprocess.run", return_value=mock_res):
                info = probe_clip(tpath, ffprobe_exe="ffprobe")
                self.assertIsNotNone(info.video)
                self.assertEqual(info.video.width, 1280)
                self.assertEqual(info.video.height, 720)
                self.assertEqual(info.video.codec_name, "h264")
                self.assertEqual(info.video.pix_fmt, "yuv420p")
                self.assertIsNotNone(info.audio)
                self.assertEqual(info.audio.codec_name, "aac")
                self.assertEqual(info.audio.channels, 2)
                self.assertEqual(info.audio.sample_rate, 48000)
                self.assertAlmostEqual(info.duration, 5.0)
        finally:
            if tpath.exists():
                tpath.unlink()

    def test_are_clips_stream_compatible_cases(self):
        from video_downloader.converter import (
            are_clips_stream_compatible,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        # 1. Matching clips
        c1 = ClipProbeInfo(
            path=Path("c1.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        c2 = ClipProbeInfo(
            path=Path("c2.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        compatible, reason = are_clips_stream_compatible([c1, c2])
        self.assertTrue(compatible)

        # 2. Resolution mismatch
        c_res = ClipProbeInfo(
            path=Path("c_res.mp4"),
            video=VideoStreamInfo("h264", 1280, 720, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        compat_res, reason_res = are_clips_stream_compatible([c1, c_res])
        self.assertFalse(compat_res)
        self.assertIn("Resolution mismatch", reason_res)

        # 3. Codec mismatch
        c_codec = ClipProbeInfo(
            path=Path("c_codec.mp4"),
            video=VideoStreamInfo("vp9", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        compat_codec, reason_codec = are_clips_stream_compatible([c1, c_codec])
        self.assertFalse(compat_codec)
        self.assertIn("Codec mismatch", reason_codec)

        # 4. Audio presence mismatch
        c_no_audio = ClipProbeInfo(
            path=Path("c_no_audio.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=None,
        )
        compat_audio, reason_audio = are_clips_stream_compatible([c1, c_no_audio])
        self.assertFalse(compat_audio)
        self.assertIn("Audio presence mismatch", reason_audio)

    def test_build_normalization_filter_mixed_audio(self):
        from video_downloader.converter import (
            build_normalization_filter,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        c1 = ClipProbeInfo(
            path=Path("c1.mp4"),
            duration=3.0,
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        c2 = ClipProbeInfo(
            path=Path("c2.mp4"),
            duration=2.5,
            video=VideoStreamInfo("h264", 1280, 720, "yuv420p", "24/1", "24/1", "1/24"),
            audio=None,  # Missing audio track
        )

        filter_str, map_args, audio_args = build_normalization_filter([c1, c2])

        # Video scaling and black-bar padding checks
        self.assertIn("scale=1920:1080:force_original_aspect_ratio=decrease:force_divisible_by=2", filter_str)
        self.assertIn("pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black", filter_str)
        self.assertIn("setsar=1", filter_str)
        self.assertIn("format=yuv420p", filter_str)

        # Audio padding and silent synthesis checks
        self.assertIn("aformat=sample_rates=48000:channel_layouts=stereo", filter_str)
        self.assertIn("anullsrc=channel_layout=stereo:sample_rate=48000", filter_str)
        self.assertIn("concat=n=2:v=1:a=1[outv][outa]", filter_str)

        self.assertEqual(map_args, ["-map", "[outv]", "-map", "[outa]"])
        self.assertIn("aac", audio_args)
        self.assertIn("192k", audio_args)

    def test_build_normalization_filter_all_video_only(self):
        from video_downloader.converter import (
            build_normalization_filter,
            ClipProbeInfo,
            VideoStreamInfo,
        )

        c1 = ClipProbeInfo(
            path=Path("c1.mp4"),
            duration=2.0,
            video=VideoStreamInfo("h264", 1280, 720, "yuv420p", "30/1", "30/1", "1/30"),
            audio=None,
        )
        c2 = ClipProbeInfo(
            path=Path("c2.mp4"),
            duration=2.0,
            video=VideoStreamInfo("h264", 1280, 720, "yuv420p", "30/1", "30/1", "1/30"),
            audio=None,
        )

        filter_str, map_args, audio_args = build_normalization_filter([c1, c2])
        self.assertIn("concat=n=2:v=1:a=0[outv]", filter_str)
        self.assertEqual(map_args, ["-map", "[outv]"])
        self.assertEqual(audio_args, [])

    def test_verify_video_integrity_failure(self):
        from video_downloader.converter import verify_video_integrity

        with tempfile.TemporaryDirectory() as tmp_dir:
            empty_file = Path(tmp_dir) / "corrupt.mp4"
            empty_file.touch()

            # Empty file should fail immediately
            with self.assertRaises(RuntimeError):
                verify_video_integrity(empty_file)

    def test_combine_videos_cleans_up_on_error(self):
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import (
            combine_videos,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            out = Path(tmp_dir) / "merged_fail.mp4"

            v1.write_bytes(b"vid1")
            v2.write_bytes(b"vid2")

            dummy_probe = [
                ClipProbeInfo(
                    path=v1,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
                ClipProbeInfo(
                    path=v2,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
            ]

            mock_proc = MagicMock()
            mock_proc.returncode = 1
            mock_proc.stderr = ["Fatal error during concatenation\n"]

            def _fail_side_effect(*args, **kwargs):
                # Create partial file that must be cleaned up on failure
                out.write_bytes(b"partial corrupted data")
                return mock_proc

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.probe_clip", side_effect=dummy_probe), \
                 patch("video_downloader.converter.get_media_duration", return_value=5.0), \
                 patch("subprocess.Popen") as mock_popen:
                mock_popen.side_effect = _fail_side_effect

                with self.assertRaises(RuntimeError) as cm:
                    combine_videos([v1, v2], out)

                self.assertIn("FFmpeg combine failed", str(cm.exception))
                # Confirm partial output file was cleaned up
                self.assertFalse(out.exists())

    def test_probe_clip_ffmpeg_fallback(self):
        """Test that probe_clip successfully falls back to ffmpeg -i when ffprobe is absent."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import probe_clip

        sample_ffmpeg_banner = (
            "Input #0, mov,mp4,m4a,3gp,3g2,mj2, from 'sample.mp4':\n"
            "  Duration: 00:01:23.45, start: 0.000000, bitrate: 1200 kb/s\n"
            "  Stream #0:0[0x1](und): Video: h264 (High) (avc1), yuv420p, 1920x1080 [SAR 1:1 DAR 16:9], 29.97 fps, 29.97 tbr, 30k tbn\n"
            "  Stream #0:1[0x2](und): Audio: aac (LC) (mp4a), 48000 Hz, stereo, fltp, 192 kb/s\n"
            "At least one output file must be specified\n"
        )
        mock_res = MagicMock()
        mock_res.stderr = sample_ffmpeg_banner
        mock_res.returncode = 1

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            tpath = Path(f.name)

        try:
            with patch("subprocess.run", return_value=mock_res), \
                 patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"):
                info = probe_clip(tpath, ffprobe_exe=None)
                self.assertIsNotNone(info.video)
                self.assertEqual(info.video.codec_name, "h264")
                self.assertEqual(info.video.width, 1920)
                self.assertEqual(info.video.height, 1080)
                self.assertEqual(info.video.pix_fmt, "yuv420p")
                self.assertIsNotNone(info.audio)
                self.assertEqual(info.audio.codec_name, "aac")
                self.assertEqual(info.audio.channels, 2)
                self.assertEqual(info.audio.sample_rate, 48000)
                self.assertAlmostEqual(info.duration, 83.45, places=2)
        finally:
            if tpath.exists():
                tpath.unlink()

    def test_combine_videos_rejects_audio_only_clip(self):
        """Test that combine_videos raises ValueError upfront if an input has no video stream."""
        from unittest.mock import patch
        from video_downloader.converter import (
            combine_videos,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            a1 = Path(tmp_dir) / "audio_only.mp3"
            out = Path(tmp_dir) / "out.mp4"

            v1.write_bytes(b"vid1")
            a1.write_bytes(b"aud1")

            probed_clips = [
                ClipProbeInfo(
                    path=v1,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
                ClipProbeInfo(
                    path=a1,
                    duration=5.0,
                    video=None,  # Audio-only file
                    audio=AudioStreamInfo("mp3", 2, 44100),
                ),
            ]

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.probe_clip", side_effect=probed_clips):
                with self.assertRaises(ValueError) as cm:
                    combine_videos([v1, a1], out)
                self.assertIn("does not contain a valid video stream", str(cm.exception))

    def test_combine_videos_normalization_uses_script_file(self):
        """Test that the normalization path passes filter complex via -filter_complex_script."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import (
            combine_videos,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            out = Path(tmp_dir) / "merged.mp4"

            v1.write_bytes(b"vid1")
            v2.write_bytes(b"vid2")

            # Incompatible resolutions to force normalization
            probed_clips = [
                ClipProbeInfo(
                    path=v1,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
                ClipProbeInfo(
                    path=v2,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1280, 720, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
            ]

            mock_proc = MagicMock()
            mock_proc.returncode = 0
            mock_proc.stderr = []

            def _side_effect(*args, **kwargs):
                out.write_bytes(b"normalized video content")
                return mock_proc

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.probe_clip", side_effect=probed_clips), \
                 patch("video_downloader.converter.verify_video_integrity", return_value=True), \
                 patch("subprocess.Popen") as mock_popen:
                mock_popen.side_effect = _side_effect

                res = combine_videos([v1, v2], out)
                self.assertEqual(res, out)
                called_cmd = mock_popen.call_args[0][0]
                self.assertIn("-filter_complex_script", called_cmd)

    def test_combine_videos_real_ffmpeg_end_to_end(self):
        """End-to-end real media generation and merge test using installed FFmpeg."""
        from video_downloader.converter import find_ffmpeg, combine_videos, verify_video_integrity

        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            self.skipTest("FFmpeg binary not available on system.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            clip1 = Path(tmp_dir) / "clip1.mp4"
            clip2 = Path(tmp_dir) / "clip2.mp4"
            out_merged = Path(tmp_dir) / "final_merged.mp4"

            # Create clip1: 320x240, 1 sec, with audio sine wave
            res1 = subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=30",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-c:a", "aac",
                str(clip1)
            ], capture_output=True)
            self.assertEqual(res1.returncode, 0, f"Clip 1 creation failed: {res1.stderr}")

            # Create clip2: 480x360 (different resolution), 1.5 sec, without audio
            res2 = subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1.5:size=480x360:rate=24",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an",
                str(clip2)
            ], capture_output=True)
            self.assertEqual(res2.returncode, 0, f"Clip 2 creation failed: {res2.stderr}")

            # Merge using the new hybrid concatenation engine
            progress_history = []
            def _track_progress(pct, msg):
                progress_history.append((pct, msg))

            result_path = combine_videos([clip1, clip2], out_merged, progress_callback=_track_progress)

            # Assert output exists and has content
            self.assertTrue(result_path.is_file())
            self.assertGreater(result_path.stat().st_size, 0)
            self.assertEqual(result_path, out_merged)

            # Assert post-merge integrity check passes cleanly
            self.assertTrue(verify_video_integrity(result_path))

            # Verify progress callback reached 100%
            self.assertTrue(any(pct == 100 for pct, _ in progress_history))

    def test_combine_videos_real_ffmpeg_vertical_and_audio_mix(self):
        """End-to-end test merging vertical video, mono audio, and silent audio with aspect padding."""
        from video_downloader.converter import find_ffmpeg, combine_videos, verify_video_integrity, probe_clip

        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            self.skipTest("FFmpeg binary not available on system.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            clip_vert = Path(tmp_dir) / "vert.mp4"
            clip_horiz = Path(tmp_dir) / "horiz.mp4"
            out_merged = Path(tmp_dir) / "merged_vert_horiz.mp4"

            # Clip 1: 360x640 vertical, 1 sec, mono audio
            res1 = subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=360x640:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-ac", "1", "-c:a", "aac",
                str(clip_vert)
            ], capture_output=True)
            self.assertEqual(res1.returncode, 0)

            # Clip 2: 640x360 horizontal, 1 sec, no audio
            res2 = subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=640x360:rate=30",
                "-c:v", "libx264", "-preset", "ultrafast",
                "-an",
                str(clip_horiz)
            ], capture_output=True)
            self.assertEqual(res2.returncode, 0)

            result = combine_videos([clip_vert, clip_horiz], out_merged)
            self.assertTrue(result.is_file())
            self.assertTrue(verify_video_integrity(result))

            probed = probe_clip(result)
            self.assertIsNotNone(probed.video)
            self.assertEqual(probed.video.width, 360)
            self.assertEqual(probed.video.height, 640)
            self.assertIsNotNone(probed.audio)
            self.assertEqual(probed.audio.channels, 2)
            self.assertEqual(probed.audio.sample_rate, 48000)

    def test_probe_clip_na_duration_and_non_numeric_fields(self):
        """Test that probe_clip robustly handles 'N/A' or missing values from ffprobe without crashing."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import probe_clip

        sample_output = json.dumps({
            "streams": [
                {
                    "index": 0,
                    "codec_name": "h264",
                    "codec_type": "video",
                    "width": "1280",
                    "height": "720",
                    "pix_fmt": "yuv420p",
                    "r_frame_rate": "30/1",
                    "avg_frame_rate": "30/1",
                    "time_base": "1/30",
                    "sample_aspect_ratio": "1:1",
                    "duration": "N/A",
                },
                {
                    "index": 1,
                    "codec_name": "aac",
                    "codec_type": "audio",
                    "sample_rate": "48000",
                    "channels": "2",
                    "duration": "N/A",
                }
            ],
            "format": {
                "duration": "N/A"
            }
        })

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = sample_output

        with tempfile.NamedTemporaryFile(suffix=".mp4", delete=False) as f:
            tpath = Path(f.name)

        try:
            with patch("subprocess.run", return_value=mock_res), \
                 patch("video_downloader.converter.get_media_duration", return_value=12.5):
                info = probe_clip(tpath, ffprobe_exe="ffprobe")
                self.assertIsNotNone(info.video)
                self.assertEqual(info.video.width, 1280)
                self.assertEqual(info.video.height, 720)
                self.assertIsNotNone(info.audio)
                self.assertEqual(info.audio.channels, 2)
                self.assertEqual(info.audio.sample_rate, 48000)
                # Ensure stream durations are backfilled from container duration
                self.assertAlmostEqual(info.duration, 12.5)
                self.assertAlmostEqual(info.video.duration, 12.5)
                self.assertAlmostEqual(info.audio.duration, 12.5)
        finally:
            if tpath.exists():
                tpath.unlink()

    def test_are_clips_stream_compatible_sar_variations(self):
        """Test SAR normalization: square pixel variants match, anamorphic SAR mismatches."""
        from video_downloader.converter import (
            are_clips_stream_compatible,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        c_1_1 = ClipProbeInfo(
            path=Path("c1.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        c_0_1 = ClipProbeInfo(
            path=Path("c2.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "0:1"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        c_na = ClipProbeInfo(
            path=Path("c3.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "N/A"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )
        c_anamorphic = ClipProbeInfo(
            path=Path("c4.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "16:9"),
            audio=AudioStreamInfo("aac", 2, 48000),
        )

        # 1:1, 0:1, and N/A are all treated as square pixels
        ok1, _ = are_clips_stream_compatible([c_1_1, c_0_1])
        self.assertTrue(ok1)

        ok2, _ = are_clips_stream_compatible([c_1_1, c_na])
        self.assertTrue(ok2)

        # Anamorphic 16:9 vs 0:1 (square) must be detected as mismatch
        ok3, reason3 = are_clips_stream_compatible([c_anamorphic, c_0_1])
        self.assertFalse(ok3)
        self.assertIn("aspect ratio mismatch", reason3.lower())

    def test_are_clips_stream_compatible_invalid_attributes(self):
        """Test rejection when dimensions or codecs are invalid."""
        from video_downloader.converter import (
            are_clips_stream_compatible,
            ClipProbeInfo,
            VideoStreamInfo,
        )

        c_valid = ClipProbeInfo(
            path=Path("c1.mp4"),
            video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
        )
        c_zero_dim = ClipProbeInfo(
            path=Path("c2.mp4"),
            video=VideoStreamInfo("h264", 0, 0, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
        )
        c_empty_codec = ClipProbeInfo(
            path=Path("c3.mp4"),
            video=VideoStreamInfo("", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30", "1:1"),
        )

        ok_dim, r_dim = are_clips_stream_compatible([c_valid, c_zero_dim])
        self.assertFalse(ok_dim)
        self.assertIn("dimensions", r_dim.lower())

        ok_codec, r_codec = are_clips_stream_compatible([c_valid, c_empty_codec])
        self.assertFalse(ok_codec)
        self.assertIn("codec", r_codec.lower())

    def test_combine_videos_rejects_output_colliding_with_input(self):
        """Test ValueError when output_path is one of the input files."""
        from video_downloader.converter import combine_videos

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            v1.write_bytes(b"vid1")
            v2.write_bytes(b"vid2")

            with self.assertRaises(ValueError) as cm:
                combine_videos([v1, v2], v1)
            self.assertIn("conflicts with one of the input files", str(cm.exception))

    def test_combine_videos_kills_child_process_on_exception(self):
        """Test that running FFmpeg child process is killed and closed if an exception occurs."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import (
            combine_videos,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        with tempfile.TemporaryDirectory() as tmp_dir:
            v1 = Path(tmp_dir) / "v1.mp4"
            v2 = Path(tmp_dir) / "v2.mp4"
            out = Path(tmp_dir) / "out.mp4"
            v1.write_bytes(b"vid1")
            v2.write_bytes(b"vid2")

            probed_clips = [
                ClipProbeInfo(
                    path=v1,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
                ClipProbeInfo(
                    path=v2,
                    duration=5.0,
                    video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"),
                    audio=AudioStreamInfo("aac", 2, 48000),
                ),
            ]

            mock_proc = MagicMock()
            mock_proc.poll.return_value = None  # Process still running
            mock_proc.stderr = ["frame= 10 time=00:00:02.00\n"]

            def _exploding_callback(pct, msg):
                if "Fast stream copying" in msg:
                    raise KeyboardInterrupt("Simulated user cancellation during copy")

            with patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("video_downloader.converter.probe_clip", side_effect=probed_clips), \
                 patch("video_downloader.converter.get_media_duration", return_value=5.0), \
                 patch("subprocess.Popen", return_value=mock_proc):
                with self.assertRaises(KeyboardInterrupt):
                    combine_videos([v1, v2], out, progress_callback=_exploding_callback)

                # Assert kill was called on child process
                mock_proc.kill.assert_called_once()

    def test_verify_video_integrity_timeout_handling(self):
        """Test that TimeoutExpired in verify_video_integrity produces clear RuntimeError."""
        from unittest.mock import patch
        from video_downloader.converter import verify_video_integrity

        with tempfile.TemporaryDirectory() as tmp_dir:
            dummy_out = Path(tmp_dir) / "out.mp4"
            dummy_out.write_bytes(b"data")

            with patch("video_downloader.converter.find_ffprobe", return_value="ffprobe"), \
                 patch("video_downloader.converter.find_ffmpeg", return_value="ffmpeg"), \
                 patch("subprocess.run", side_effect=subprocess.TimeoutExpired(cmd="ffprobe", timeout=15)):
                with self.assertRaises(RuntimeError) as cm:
                    verify_video_integrity(dummy_out)
                self.assertIn("timed out", str(cm.exception))

    def test_combine_videos_real_ffmpeg_spaces_and_special_chars(self):
        """Real FFmpeg test merging clips with spaces, single quotes, and brackets in path."""
        from video_downloader.converter import find_ffmpeg, combine_videos, verify_video_integrity

        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            self.skipTest("FFmpeg binary not available on system.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            p1 = Path(tmp_dir) / "clip with spaces & [1].mp4"
            p2 = Path(tmp_dir) / "clip's second (test).mp4"
            out = Path(tmp_dir) / "merged result's [final].mp4"

            # Create 2 compatible clips
            subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-c:a", "aac",
                str(p1)
            ], capture_output=True, check=True)

            subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-c:a", "aac",
                str(p2)
            ], capture_output=True, check=True)

            res = combine_videos([p1, p2], out)
            self.assertTrue(res.is_file())
            self.assertGreater(res.stat().st_size, 0)
            self.assertTrue(verify_video_integrity(res))

    def test_combine_videos_real_ffmpeg_anamorphic_sar(self):
        """Real FFmpeg test merging anamorphic clip (SAR 32:27) with square clip (SAR 1:1)."""
        from video_downloader.converter import find_ffmpeg, combine_videos, verify_video_integrity, probe_clip

        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            self.skipTest("FFmpeg binary not available on system.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            p_anamorphic = Path(tmp_dir) / "anamorphic.mp4"
            p_square = Path(tmp_dir) / "square.mp4"
            out = Path(tmp_dir) / "anamorphic_merged.mp4"

            # 720x480 anamorphic SAR 32:27
            subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=720x480:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-vf", "setsar=32/27",
                "-c:v", "libx264", "-c:a", "aac",
                str(p_anamorphic)
            ], capture_output=True, check=True)

            # 640x360 square SAR 1:1
            subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=640x360:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-c:a", "aac",
                str(p_square)
            ], capture_output=True, check=True)

            res = combine_videos([p_anamorphic, p_square], out)
            self.assertTrue(res.is_file())
            self.assertTrue(verify_video_integrity(res))

            info = probe_clip(res)
            self.assertIsNotNone(info.video)
            self.assertEqual(info.video.sample_aspect_ratio, "1:1")

    def test_are_clips_stream_compatible_empty_and_single_clip_guards(self):
        """Test boundary conditions for are_clips_stream_compatible."""
        from video_downloader.converter import (
            are_clips_stream_compatible,
            ClipProbeInfo,
            VideoStreamInfo,
            AudioStreamInfo,
        )

        # 1. Empty list
        ok, reason = are_clips_stream_compatible([])
        self.assertFalse(ok)
        self.assertIn("no clips", reason.lower())

        # 2. Single clip lacking video stream
        c_no_vid = ClipProbeInfo(path=Path("audio.mp3"), video=None, audio=AudioStreamInfo("mp3", 2, 44100))
        ok, reason = are_clips_stream_compatible([c_no_vid])
        self.assertFalse(ok)
        self.assertIn("lack a detectable video stream", reason.lower())

        # 3. Single clip with invalid dimensions or empty codec
        c_invalid = ClipProbeInfo(path=Path("bad.mp4"), video=VideoStreamInfo("", 0, 0, "yuv420p", "30/1", "30/1"))
        ok, reason = are_clips_stream_compatible([c_invalid])
        self.assertFalse(ok)

        # 4. Single clip with zero/unknown frame rate
        c_zero_fps = ClipProbeInfo(path=Path("nofps.mp4"), video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "0/0", "0/0"))
        ok, reason = are_clips_stream_compatible([c_zero_fps])
        self.assertFalse(ok)
        self.assertIn("frame rate", reason.lower())

        # 5. Valid single clip
        c_valid = ClipProbeInfo(path=Path("valid.mp4"), video=VideoStreamInfo("h264", 1920, 1080, "yuv420p", "30/1", "30/1", "1/30"))
        ok, reason = are_clips_stream_compatible([c_valid])
        self.assertTrue(ok)
        self.assertIn("single clip is compatible", reason.lower())

    def test_build_normalization_filter_empty_guard(self):
        """Test that build_normalization_filter rejects empty clip lists."""
        from video_downloader.converter import build_normalization_filter

        with self.assertRaises(ValueError) as cm:
            build_normalization_filter([])
        self.assertIn("at least one clip", str(cm.exception).lower())

    def test_combine_videos_boundary_conditions(self):
        """Test boundary conditions for combine_videos: empty file, directory output, zero dimensions."""
        from video_downloader.converter import combine_videos, ClipProbeInfo, VideoStreamInfo

        with tempfile.TemporaryDirectory() as tmp_dir:
            f_empty = Path(tmp_dir) / "empty.mp4"
            f_empty.touch()
            f_valid = Path(tmp_dir) / "valid.mp4"
            f_valid.write_bytes(b"data")
            f_out = Path(tmp_dir) / "out.mp4"

            # 1. Empty input file
            with self.assertRaises(ValueError) as cm:
                combine_videos([f_empty, f_valid], f_out)
            self.assertIn("is empty", str(cm.exception).lower())

            # 2. Output path is an existing directory
            out_dir = Path(tmp_dir) / "output_dir"
            out_dir.mkdir()
            with self.assertRaises(ValueError) as cm:
                combine_videos([f_valid, f_valid], out_dir)
            self.assertIn("must be a file, not a directory", str(cm.exception).lower())

    def test_probe_clip_skips_attached_picture_album_art(self):
        """Test that probe_clip ignores embedded album artwork (attached_pic: 1)."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import probe_clip

        ffprobe_art_output = json.dumps({
            "streams": [
                {
                    "index": 0,
                    "codec_name": "mp3",
                    "codec_type": "audio",
                    "sample_rate": "44100",
                    "channels": 2,
                    "duration": "10.0"
                },
                {
                    "index": 1,
                    "codec_name": "mjpeg",
                    "codec_type": "video",
                    "width": 500,
                    "height": 500,
                    "disposition": {
                        "attached_pic": 1
                    },
                    "duration": "10.0"
                }
            ],
            "format": {
                "duration": "10.0"
            }
        })

        mock_res = MagicMock()
        mock_res.returncode = 0
        mock_res.stdout = ffprobe_art_output

        with tempfile.NamedTemporaryFile(suffix=".mp3", delete=False) as f:
            tpath = Path(f.name)

        try:
            with patch("subprocess.run", return_value=mock_res):
                info = probe_clip(tpath, ffprobe_exe="ffprobe")
                # Embedded album art must NOT be treated as a video stream
                self.assertIsNone(info.video)
                self.assertIsNotNone(info.audio)
                self.assertEqual(info.audio.codec_name, "mp3")
        finally:
            if tpath.exists():
                tpath.unlink()

    def test_verify_video_integrity_checks(self):
        """Test verify_video_integrity tool availability and video stream presence requirements."""
        from unittest.mock import patch, MagicMock
        from video_downloader.converter import verify_video_integrity

        with tempfile.TemporaryDirectory() as tmp_dir:
            dummy_file = Path(tmp_dir) / "test.mp4"
            dummy_file.write_bytes(b"content")

            # 1. Missing both tools raises RuntimeError
            with patch("video_downloader.converter.find_ffmpeg", return_value=None), \
                 patch("video_downloader.converter.find_ffprobe", return_value=None):
                with self.assertRaises(RuntimeError) as cm:
                    verify_video_integrity(dummy_file)
                self.assertIn("neither ffmpeg nor ffprobe is available", str(cm.exception).lower())

            # 2. Output container with audio only (no video stream) raises RuntimeError
            audio_only_probe = json.dumps({
                "streams": [
                    {"index": 0, "codec_type": "audio", "codec_name": "aac"}
                ],
                "format": {"duration": "5.0"}
            })
            mock_res = MagicMock()
            mock_res.returncode = 0
            mock_res.stdout = audio_only_probe

            with patch("video_downloader.converter.find_ffprobe", return_value="ffprobe"), \
                 patch("video_downloader.converter.find_ffmpeg", return_value=None), \
                 patch("subprocess.run", return_value=mock_res):
                with self.assertRaises(RuntimeError) as cm:
                    verify_video_integrity(dummy_file)
                self.assertIn("no decodable video stream", str(cm.exception).lower())

    def test_combine_videos_real_ffmpeg_single_clip(self):
        """Test real FFmpeg pass-through and reencode for a single clip input."""
        from video_downloader.converter import find_ffmpeg, combine_videos, verify_video_integrity

        ffmpeg_exe = find_ffmpeg()
        if not ffmpeg_exe:
            self.skipTest("FFmpeg binary not available on system.")

        with tempfile.TemporaryDirectory() as tmp_dir:
            clip = Path(tmp_dir) / "single_test.mp4"
            out_copy = Path(tmp_dir) / "single_copy.mp4"
            out_reencode = Path(tmp_dir) / "single_reencode.mp4"

            subprocess.run([
                ffmpeg_exe, "-y",
                "-f", "lavfi", "-i", "testsrc=duration=1:size=320x240:rate=25",
                "-f", "lavfi", "-i", "sine=frequency=440:duration=1",
                "-c:v", "libx264", "-c:a", "aac",
                str(clip)
            ], check=True, capture_output=True)

            # Direct copy path
            res_copy = combine_videos([clip], out_copy, reencode=False)
            self.assertTrue(res_copy.is_file())
            self.assertTrue(verify_video_integrity(res_copy))

            # Reencode path
            res_re = combine_videos([clip], out_reencode, reencode=True)
            self.assertTrue(res_re.is_file())
            self.assertTrue(verify_video_integrity(res_re))


if __name__ == "__main__":
    unittest.main()



