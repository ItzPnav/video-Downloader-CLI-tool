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


class TestToolDirectories(unittest.TestCase):
    """Unit tests for dedicated, independent per-tool output directory management."""

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.base_dir = Path(self.temp_dir.name)

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_distinct_default_directories_per_tool(self):
        """Verify each tool resolves to a distinct dedicated directory by default."""
        from video_downloader.utils import get_tool_output_dir, get_download_dir

        with patch("video_downloader.utils.get_download_dir", return_value=self.base_dir):
            mock_cfg = {"download_directory": str(self.base_dir)}
            v_dir = get_tool_output_dir("video", mock_cfg)
            c_dir = get_tool_output_dir("converter", mock_cfg)
            cm_dir = get_tool_output_dir("comic", mock_cfg)
            p_dir = get_tool_output_dir("packager", mock_cfg)
            o_dir = get_tool_output_dir("ocr", mock_cfg)

            # Check that each sub-tool directory ends with its dedicated name
            self.assertEqual(c_dir.name, "Converted")
            self.assertEqual(cm_dir.name, "Comics")
            self.assertEqual(p_dir.name, "Packaged")
            self.assertEqual(o_dir.name, "OCR")

            # Check that all non-video directories are unique
            dirs = [v_dir, c_dir, cm_dir, p_dir, o_dir]
            self.assertEqual(len(set(dirs)), 5, "All tool output directories must be distinct")

    def test_per_tool_custom_directory_persistence(self):
        """Verify setting a custom directory for one tool does not affect other tools."""
        from video_downloader.utils import get_tool_output_dir, set_tool_output_dir

        with patch("video_downloader.utils.get_config_dir", return_value=self.base_dir):
            custom_comic = self.base_dir / "SpecialComics"
            custom_ocr = self.base_dir / "Transcripts"

            set_tool_output_dir("comic", custom_comic)
            set_tool_output_dir("ocr", custom_ocr)

            loaded_comic = get_tool_output_dir("comic")
            loaded_ocr = get_tool_output_dir("ocr")
            loaded_converter = get_tool_output_dir("converter")

            self.assertEqual(loaded_comic, custom_comic.resolve())
            self.assertEqual(loaded_ocr, custom_ocr.resolve())
            self.assertNotEqual(loaded_comic, loaded_converter)
            self.assertNotEqual(loaded_ocr, loaded_converter)

    def test_auto_separate_all_tool_dirs(self):
        """Verify auto_separate_all_tool_dirs creates dedicated subfolders for all tools."""
        from video_downloader.utils import auto_separate_all_tool_dirs

        with patch("video_downloader.utils.get_config_dir", return_value=self.base_dir):
            result = auto_separate_all_tool_dirs(self.base_dir, create_video_subfolder=True)

            self.assertIn("video", result)
            self.assertIn("converter", result)
            self.assertIn("comic", result)
            self.assertIn("packager", result)
            self.assertIn("ocr", result)

            for tool, path in result.items():
                self.assertTrue(path.exists(), f"Directory for {tool} must exist on disk")

            # All 5 paths must be completely distinct
            self.assertEqual(len(set(result.values())), 5)

    def test_prompt_single_or_folder_mode_and_batch_converters(self):
        """Verify Single File vs Batch Folder menu selection and batch conversion helpers."""
        from video_downloader.menu import prompt_single_or_folder_mode
        from video_downloader.converter import batch_convert_gifs_to_mp4, batch_convert_videos_to_gif

        # 1. Choosing '1' selects 'file'
        with patch("video_downloader.menu.read_key", side_effect=["1"]), \
             patch("video_downloader.menu.clear_screen"):
            mode = prompt_single_or_folder_mode(
                "ANIMATED GIF -> MP4", "Single GIF File", "Desc 1", "Folder of GIFs", "Desc 2"
            )
            self.assertEqual(mode, "file")

        # 2. Choosing '2' selects 'folder'
        with patch("video_downloader.menu.read_key", side_effect=["2"]), \
             patch("video_downloader.menu.clear_screen"):
            mode = prompt_single_or_folder_mode(
                "VIDEO -> ANIMATED GIF", "Single Video File", "Desc 1", "Folder of Videos", "Desc 2"
            )
            self.assertEqual(mode, "folder")

        # 3. Choosing '0' cancels (None)
        with patch("video_downloader.menu.read_key", side_effect=["0"]), \
             patch("video_downloader.menu.clear_screen"):
            mode = prompt_single_or_folder_mode(
                "VIDEO -> ANIMATED GIF", "Single Video File", "Desc 1", "Folder of Videos", "Desc 2"
            )
            self.assertIsNone(mode)

        # 4. Batch GIF -> MP4 conversion over a folder
        gif_dir = self.base_dir / "gifs"
        gif_dir.mkdir(parents=True, exist_ok=True)
        out_dir = self.base_dir / "mp4_out"
        (gif_dir / "anim1.gif").write_bytes(b"GIF89a")
        (gif_dir / "anim2.gif").write_bytes(b"GIF89a")
        (gif_dir / "ignore.txt").write_text("not a gif")

        with patch("video_downloader.converter.convert_gif_to_mp4") as mock_gif2mp4:
            mock_gif2mp4.side_effect = lambda input_path, output_path, **kw: output_path
            res = batch_convert_gifs_to_mp4(gif_dir, out_dir)
            self.assertEqual(len(res), 2)
            self.assertEqual(mock_gif2mp4.call_count, 2)
            self.assertEqual([p.name for p in res], ["anim1.mp4", "anim2.mp4"])

        # 5. Batch Video -> GIF conversion over a folder
        vid_dir = self.base_dir / "vids"
        vid_dir.mkdir(parents=True, exist_ok=True)
        gif_out_dir = self.base_dir / "gif_out"
        (vid_dir / "clip1.mp4").write_bytes(b"mp4")
        (vid_dir / "clip2.mkv").write_bytes(b"mkv")

        with patch("video_downloader.converter.convert_video_to_gif") as mock_vid2gif:
            mock_vid2gif.side_effect = lambda input_path, output_path, **kw: output_path
            res_gifs = batch_convert_videos_to_gif(vid_dir, gif_out_dir, fps=24, height=480, colors=128)
            self.assertEqual(len(res_gifs), 2)
            self.assertEqual(mock_vid2gif.call_count, 2)
            self.assertEqual([p.name for p in res_gifs], ["clip1.gif", "clip2.gif"])


class TestConverterAndCombineArrowWorkflow(unittest.TestCase):
    """
    Unit tests for arrow-key navigation, immediate execution with optimal defaults,
    and non-blocking menu returns across action_convert and action_combine_videos.
    """

    def setUp(self):
        self.temp_dir = tempfile.TemporaryDirectory()
        self.test_dir = Path(self.temp_dir.name)
        self.cfg = {
            "version": "0.2.0",
            "download_directory": str(self.test_dir / "Downloads"),
            "converter_output_directory": str(self.test_dir / "Converted"),
            "auto_open": False,
        }

    def tearDown(self):
        self.temp_dir.cleanup()

    def test_action_combine_videos_arrow_key_navigation_and_shortcuts(self):
        """Verify full arrow-key navigation, option highlight, and number shortcuts in combine videos."""
        from video_downloader.menu import action_combine_videos

        vid1 = self.test_dir / "clip1.mp4"
        vid2 = self.test_dir / "clip2.mp4"
        vid1.write_bytes(b"vid1")
        vid2.write_bytes(b"vid2")

        # 1. Test UP/DOWN arrow navigation and ESC exit returning None
        with patch("video_downloader.menu.read_key", side_effect=["DOWN", "DOWN", "UP", "ESC"]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.get_config_dir", return_value=self.test_dir):
            ret = action_combine_videos(self.cfg)
            self.assertIsNone(ret)

        # 2. Test adding videos, removing last, clearing queue, and exiting via '0'
        browse_side_effects = [vid1, vid2]
        with patch("video_downloader.menu.read_key", side_effect=["1", "1", "3", "4", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", side_effect=browse_side_effects), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.get_config_dir", return_value=self.test_dir):
            ret = action_combine_videos(self.cfg)
            self.assertIsNone(ret)

    def test_action_combine_videos_immediate_execution_with_optimal_defaults(self):
        """Verify combining videos runs immediately with optimal defaults without blocking input or pause_prompt."""
        from video_downloader.menu import action_combine_videos

        vid1 = self.test_dir / "clip1.mp4"
        vid2 = self.test_dir / "clip2.mp4"
        vid1.write_bytes(b"vid1")
        vid2.write_bytes(b"vid2")

        expected_out = self.test_dir / "Converted" / "combined_clip1_2clips.mp4"

        # Sequence:
        # - "1" (add clip1)
        # - "1" (add clip2)
        # - "DOWN", "DOWN", "DOWN", "DOWN", "ENTER" (navigate from 0 to 4: Start Combining Videos)
        keys = ["1", "1", "DOWN", "DOWN", "DOWN", "DOWN", "ENTER", "1"]
        browse_mock = MagicMock(side_effect=[vid1, vid2])

        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.browse_interactive_path", browse_mock), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.combine_videos", return_value=expected_out) as mock_combine, \
             patch("video_downloader.utils.get_config_dir", return_value=self.test_dir), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_input, \
             patch("video_downloader.menu.pause_prompt") as mock_pause:

            ret = action_combine_videos(self.cfg)

            # Assert output returned immediately
            self.assertEqual(ret, expected_out)
            # Verify combine_videos called with smart hybrid direct copy (reencode=False)
            mock_combine.assert_called_once()
            self.assertEqual(mock_combine.call_args.kwargs.get("reencode", False), False)
            self.assertEqual([p.name for p in mock_combine.call_args.kwargs.get("video_paths", [])], ["clip1.mp4", "clip2.mp4"])
            # Verify zero blocking input() and zero pause_prompt() calls
            mock_input.assert_not_called()
            mock_pause.assert_not_called()

    def test_action_convert_conv_options_and_combine_integration(self):
        """Verify conv_options includes Combine at option 8, and arrow navigation invokes it without blocking."""
        from video_downloader.menu import action_convert

        vid_out = self.test_dir / "Converted" / "combined_sample_2clips.mp4"

        # Test selecting option 8 (Combine) via key "8", then exiting via "0"
        with patch("video_downloader.menu.read_key", side_effect=["8", "0"]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.menu.action_combine_videos", return_value=vid_out) as mock_combine_action, \
             patch("video_downloader.utils.get_config_dir", return_value=self.test_dir), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("video_downloader.menu.pause_prompt") as mock_pause, \
             patch("builtins.input") as mock_input:

            action_convert(self.cfg)
            mock_combine_action.assert_called_once()
            mock_pause.assert_not_called()
            mock_input.assert_not_called()

    def test_action_convert_arrow_navigation_to_option_8(self):
        """Verify using DOWN arrow keys down to option 8 (Combine) and pressing ENTER triggers it."""
        from video_downloader.menu import action_convert

        vid_out = self.test_dir / "Converted" / "combined_sample_2clips.mp4"

        # Index 0 to 7 requires 7 DOWN presses, then ENTER, then 0 to exit
        keys = ["DOWN"] * 7 + ["ENTER", "0"]
        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.menu.action_combine_videos", return_value=vid_out) as mock_combine_action, \
             patch("video_downloader.utils.get_config_dir", return_value=self.test_dir), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("video_downloader.menu.pause_prompt") as mock_pause, \
             patch("builtins.input") as mock_input:

            action_convert(self.cfg)
            mock_combine_action.assert_called_once()
            mock_pause.assert_not_called()
            mock_input.assert_not_called()

    def test_action_convert_zero_question_immediate_execution_all_types(self):
        """Verify each conversion type runs immediately with optimal defaults and no pause_prompt/input."""
        from video_downloader.menu import action_convert

        sample_vid = self.test_dir / "sample.mp4"
        sample_aud = self.test_dir / "audio.wav"
        sample_txt = self.test_dir / "doc.txt"
        sample_img = self.test_dir / "image.png"

        sample_vid.write_bytes(b"vid")
        sample_aud.write_bytes(b"aud")
        sample_txt.write_text("doc")
        sample_img.write_bytes(b"img")

        # 1. Video to GIF (choice 0 / Option 1)
        with patch("video_downloader.menu.read_key", side_effect=["1", "0"]), \
             patch("video_downloader.menu.prompt_single_or_folder_mode", return_value="file"), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_vid), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_video_to_gif") as mock_v2g, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_v2g.assert_called_once()
            self.assertEqual(mock_v2g.call_args.kwargs.get("fps"), 30)
            self.assertEqual(mock_v2g.call_args.kwargs.get("height"), 504)
            self.assertEqual(mock_v2g.call_args.kwargs.get("colors"), 256)
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 2. Video to MP3 (choice 1 / Option 2)
        with patch("video_downloader.menu.read_key", side_effect=["2", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_vid), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_video_to_audio") as mock_v2a, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_v2a.assert_called_once()
            self.assertEqual(mock_v2a.call_args.kwargs.get("audio_format"), "mp3")
            self.assertEqual(mock_v2a.call_args.kwargs.get("bitrate"), "320k")
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 3. Audio to Audio (choice 2 / Option 3)
        with patch("video_downloader.menu.read_key", side_effect=["3", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_aud), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_audio_to_audio") as mock_a2a, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_a2a.assert_called_once()
            self.assertEqual(mock_a2a.call_args.kwargs.get("audio_format"), "mp3")
            self.assertEqual(mock_a2a.call_args.kwargs.get("bitrate"), "320k")
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 4. Text to PDF (choice 3 / Option 4)
        with patch("video_downloader.menu.read_key", side_effect=["4", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_txt), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_text_to_pdf") as mock_t2p, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_t2p.assert_called_once()
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 5. Image Format (choice 5 / Option 6)
        with patch("video_downloader.menu.read_key", side_effect=["6", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_img), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_image") as mock_img, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_img.assert_called_once()
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 6. Video Remux (choice 6 / Option 7)
        with patch("video_downloader.menu.read_key", side_effect=["7", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_vid), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.remux_or_transcode_video") as mock_remux, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_remux.assert_called_once()
            self.assertEqual(mock_remux.call_args.kwargs.get("reencode"), False)
            mock_in.assert_not_called()
            mock_p.assert_not_called()

    def test_action_combine_videos_min_clips_guard(self):
        """Verify pressing combine with < 2 clips sets warning and does not call combine_videos."""
        from video_downloader.menu import action_combine_videos

        # Keys: '5' (try combine with 0 videos), then '0' (exit)
        with patch("video_downloader.menu.read_key", side_effect=["5", "0"]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.combine_videos") as mock_combine, \
             patch("video_downloader.utils.load_config", return_value=self.cfg):
            ret = action_combine_videos(self.cfg)
            self.assertIsNone(ret)
            mock_combine.assert_not_called()

    def test_action_convert_batch_folder_zero_question_immediate_execution(self):
        """Verify batch folder GIF conversion in action_convert runs immediately with 30fps/504p/256colors."""
        from video_downloader.menu import action_convert

        folder = self.test_dir / "vid_folder"
        folder.mkdir(parents=True, exist_ok=True)
        (folder / "v1.mp4").write_bytes(b"v1")
        (folder / "v2.mp4").write_bytes(b"v2")

        with patch("video_downloader.menu.read_key", side_effect=["1", "0"]), \
             patch("video_downloader.menu.prompt_single_or_folder_mode", return_value="folder"), \
             patch("video_downloader.menu.browse_interactive_path", return_value=folder), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.batch_convert_videos_to_gif", return_value=[Path("v1.gif"), Path("v2.gif")]) as mock_batch, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_batch.assert_called_once()
            self.assertEqual(mock_batch.call_args.kwargs.get("fps"), 30)
            self.assertEqual(mock_batch.call_args.kwargs.get("height"), 504)
            self.assertEqual(mock_batch.call_args.kwargs.get("colors"), 256)
            mock_in.assert_not_called()
            mock_p.assert_not_called()

    def test_action_convert_inline_success_banner_rendered(self):
        """Verify inline success banner is printed upon return to Media Converter menu."""
        import io
        from video_downloader.menu import action_convert

        sample_vid = self.test_dir / "test_banner.mp4"
        sample_vid.write_bytes(b"banner_vid")

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["2", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_vid), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_video_to_audio", return_value=Path("test_banner.mp3")), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)

        out_text = captured_output.getvalue()
        self.assertIn("Converted / Saved: test_banner.mp3", out_text)

    def test_action_convert_combine_inline_success_banner_rendered(self):
        """Verify combine videos renders [✓] Combined N videos into: ... banner at top of menu."""
        import io
        from video_downloader.menu import action_convert

        combined_path = Path("combined_clip_2clips.mp4")

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["8", "0"]), \
             patch("video_downloader.menu.action_combine_videos", return_value=combined_path), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)

        out_text = captured_output.getvalue()
        self.assertIn("Combined 2 videos into: combined_clip_2clips.mp4", out_text)

    def test_action_convert_exception_banner_no_blocking(self):
        """Verify conversion errors display inline error banner without blocking pause_prompt."""
        import io
        from video_downloader.menu import action_convert

        sample_vid = self.test_dir / "error_vid.mp4"
        sample_vid.write_bytes(b"err")

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["2", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_vid), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_video_to_audio", side_effect=RuntimeError("FFmpeg boom")), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("video_downloader.menu.pause_prompt") as mock_p, \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)
            mock_p.assert_not_called()

        out_text = captured_output.getvalue()
        self.assertIn("Conversion failed: FFmpeg boom", out_text)

    def test_action_convert_gif_to_mp4_single_and_batch_zero_question(self):
        """Verify Option 5 (GIF to MP4) in single and batch modes executes immediately with zero questions."""
        from video_downloader.menu import action_convert

        sample_gif = self.test_dir / "sample.gif"
        sample_gif.write_bytes(b"GIF89a")

        # 1. Single GIF to MP4
        with patch("video_downloader.menu.read_key", side_effect=["5", "0"]), \
             patch("video_downloader.menu.prompt_single_or_folder_mode", return_value="file"), \
             patch("video_downloader.menu.browse_interactive_path", return_value=sample_gif), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.convert_gif_to_mp4") as mock_g2v, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_g2v.assert_called_once()
            mock_in.assert_not_called()
            mock_p.assert_not_called()

        # 2. Batch GIFs in folder to MP4
        gif_folder = self.test_dir / "gif_folder"
        gif_folder.mkdir(parents=True, exist_ok=True)
        (gif_folder / "g1.gif").write_bytes(b"g1")
        (gif_folder / "g2.gif").write_bytes(b"g2")

        with patch("video_downloader.menu.read_key", side_effect=["5", "0"]), \
             patch("video_downloader.menu.prompt_single_or_folder_mode", return_value="folder"), \
             patch("video_downloader.menu.browse_interactive_path", return_value=gif_folder), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.batch_convert_gifs_to_mp4", return_value=[Path("g1.mp4"), Path("g2.mp4")]) as mock_bg2v, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.input") as mock_in, \
             patch("video_downloader.menu.pause_prompt") as mock_p:

            action_convert(self.cfg)
            mock_bg2v.assert_called_once()
            mock_in.assert_not_called()
            mock_p.assert_not_called()

    def test_action_video_tools_combine_videos_arrow_navigation_and_banner(self):
        """Verify action_video_tools navigates to Combine with arrow keys and displays inline success banner."""
        import io
        from video_downloader.menu import action_video_tools

        combined_path = Path("combined_vid_3clips.mp4")
        captured_output = io.StringIO()

        # In action_video_tools:
        # Index 0: Download, Index 1: Open, Index 2: Combine
        # Keys: DOWN, DOWN, ENTER -> triggers combine, then ESC -> exits action_video_tools
        keys = ["DOWN", "DOWN", "ENTER", "ESC"]
        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.action_combine_videos", return_value=combined_path) as mock_comb, \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            action_video_tools(self.cfg)
            mock_comb.assert_called_once()

        out_text = captured_output.getvalue()
        self.assertIn("Combined 3 videos into: combined_vid_3clips.mp4", out_text)

    def test_action_video_tools_stale_banner_cleared_on_next_action(self):
        """Verify status_banner is cleared in action_video_tools when a user starts another action."""
        import io
        from video_downloader.menu import action_video_tools

        combined_path = Path("combined_vid_2clips.mp4")
        # Step 1: Combine videos via key '3'
        # Step 2: Open videos via key '2'
        # Step 3: Exit via '0'
        keys = ["3", "2", "0"]

        banners_rendered = []

        def fake_clear():
            pass

        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.action_combine_videos", return_value=combined_path), \
             patch("video_downloader.menu.action_open") as mock_open, \
             patch("video_downloader.menu.clear_screen", side_effect=fake_clear), \
             patch("video_downloader.utils.load_config", return_value=self.cfg):

            action_video_tools(self.cfg)
            mock_open.assert_called_once()

    def test_action_combine_videos_queue_capping_and_stem_sanitization(self):
        """Verify action_combine_videos caps queue display at 8 items and sanitizes output filename stem."""
        import io
        from video_downloader.menu import action_combine_videos

        # Create 10 valid video clips on disk
        clips = []
        for i in range(10):
            p = self.test_dir / f"clip_item_{i:02d}.mp4"
            p.write_bytes(b"content")
            clips.append(p)

        # Mock clip with weird characters in stem to test safe_filename sanitization
        mock_weird_clip = MagicMock(spec=Path)
        mock_weird_clip.name = "bad:?*name.mp4"
        mock_weird_clip.stem = "bad:?*name"
        mock_weird_clip.suffix = ".mp4"
        mock_weird_clip.is_file.return_value = True
        mock_weird_clip.stat.return_value.st_size = 1048576

        captured_output = io.StringIO()
        # Step 1: Add weird clip via file browser (key "1")
        # Step 2: Add all 10 folder clips via folder browser (key "2")
        # Step 3: Combine clips (key "5")
        keys = ["1", "2", "5", "1"]
        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.browse_interactive_path", side_effect=[mock_weird_clip, self.test_dir]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.combine_videos", return_value=Path("out.mp4")) as mock_comb, \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            ret = action_combine_videos(self.cfg)
            self.assertIsNotNone(ret)
            mock_comb.assert_called_once()
            # Verify output filename stem had illegal chars sanitized
            out_arg = mock_comb.call_args.kwargs.get("output_path")
            self.assertNotIn("?", out_arg.name)
            self.assertNotIn("*", out_arg.name)
            self.assertNotIn(":", out_arg.name)
            self.assertTrue(out_arg.name.startswith("combined_bad___name_11clips.mp4"))

        out_text = captured_output.getvalue()
        # Verify queue capping line was rendered (11 clips total -> first 8 shown, 3 overflow)
        self.assertIn("... and 3 more clip(s)", out_text)

    def test_action_combine_videos_safe_folder_scan_on_error(self):
        """Verify action_combine_videos handles folder scanning exceptions gracefully with an inline banner."""
        from video_downloader.menu import action_combine_videos

        bad_folder = MagicMock(spec=Path)
        bad_folder.is_dir.return_value = True
        bad_folder.iterdir.side_effect = PermissionError("Access denied")

        # Keys: '2' (Add folder), then '0' (Exit)
        with patch("video_downloader.menu.read_key", side_effect=["2", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", return_value=bad_folder), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg):

            ret = action_combine_videos(self.cfg)
            self.assertIsNone(ret)

    def test_action_combine_videos_stale_banner_cleared_on_cancel(self):
        """Verify status_banner is cleared in action_combine_videos if user cancels file browser."""
        from video_downloader.menu import action_combine_videos

        vid1 = self.test_dir / "clip1.mp4"
        vid1.write_bytes(b"content")

        rendered_banners = []
        original_print = print

        def tracking_print(*args, **kwargs):
            text = " ".join(str(a) for a in args)
            if "[✓] Added: clip1.mp4" in text:
                rendered_banners.append(text)
            return original_print(*args, **kwargs)

        with patch("video_downloader.menu.read_key", side_effect=["1", "1", "0"]), \
             patch("video_downloader.menu.browse_interactive_path", side_effect=[vid1, None]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("builtins.print", side_effect=tracking_print):

            action_combine_videos(self.cfg)

        self.assertEqual(len(rendered_banners), 1)

    def test_action_combine_videos_output_collision_auto_increment(self):
        """Verify output filename auto-increments if default_name matches an input clip."""
        from video_downloader.menu import action_combine_videos
        from video_downloader.utils import get_tool_output_dir

        conv_dir = get_tool_output_dir("converter", self.cfg)
        conv_dir.mkdir(parents=True, exist_ok=True)

        vid1 = self.test_dir / "clipA.mp4"
        vid1.write_bytes(b"clipA")

        # Create input clip matching the default combined name: combined_clipA_2clips.mp4
        colliding_clip = conv_dir / "combined_clipA_2clips.mp4"
        colliding_clip.write_bytes(b"existing_clip")

        with patch("video_downloader.menu.read_key", side_effect=["1", "1", "5", "1"]), \
             patch("video_downloader.menu.browse_interactive_path", side_effect=[vid1, colliding_clip]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.combine_videos", return_value=Path("out.mp4")) as mock_comb, \
             patch("video_downloader.utils.load_config", return_value=self.cfg):

            action_combine_videos(self.cfg)
            mock_comb.assert_called_once()
            out_arg = mock_comb.call_args.kwargs.get("output_path")
            self.assertEqual(out_arg.name, "combined_clipA_2clips_1.mp4")

    def test_action_convert_combine_banner_multiple_clips_in_stem(self):
        """Verify banner regex captures the trailing combined clip count when stem has _Nclips."""
        import io
        from video_downloader.menu import action_convert

        # Clip named with _2clips in its stem, combined into 5 clips total
        combined_path = Path("combined_vid_2clips_test_5clips.mp4")

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["8", "0"]), \
             patch("video_downloader.menu.action_combine_videos", return_value=combined_path), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)

        out_text = captured_output.getvalue()
        # Must report "Combined 5 videos into:", NOT "Combined 2 videos into:"
        self.assertIn("Combined 5 videos into: combined_vid_2clips_test_5clips.mp4", out_text)

    def test_action_convert_combine_banner_with_auto_increment_counter(self):
        """Verify banner regex captures clip count when filename has auto-increment counter suffix like _1.mp4."""
        import io
        from video_downloader.menu import action_convert

        # Clip named with _2clips in its stem, 5 clips combined, with auto-increment counter _1
        combined_path = Path("combined_vid_2clips_test_5clips_1.mp4")

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["8", "0"]), \
             patch("video_downloader.menu.action_combine_videos", return_value=combined_path), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)

        out_text = captured_output.getvalue()
        self.assertIn("Combined 5 videos into: combined_vid_2clips_test_5clips_1.mp4", out_text)

    def test_action_combine_videos_output_collision_with_relative_paths(self):
        """Verify output filename auto-increments even when input clips are supplied as relative paths."""
        import os
        from video_downloader.menu import action_combine_videos
        from video_downloader.utils import get_tool_output_dir

        conv_dir = get_tool_output_dir("converter", self.cfg)
        conv_dir.mkdir(parents=True, exist_ok=True)

        vid1 = conv_dir / "clipA.mp4"
        vid1.write_bytes(b"clipA")

        # Colliding clip file on disk matching default output: combined_clipA_2clips.mp4
        colliding_clip_abs = conv_dir / "combined_clipA_2clips.mp4"
        colliding_clip_abs.write_bytes(b"existing_clip")

        # Pass as relative path from conv_dir cwd
        orig_cwd = os.getcwd()
        try:
            os.chdir(str(conv_dir))
            rel_vid1 = Path("clipA.mp4")
            rel_colliding = Path("combined_clipA_2clips.mp4")

            with patch("video_downloader.menu.read_key", side_effect=["1", "1", "5", "1"]), \
                 patch("video_downloader.menu.browse_interactive_path", side_effect=[rel_vid1, rel_colliding]), \
                 patch("video_downloader.menu.clear_screen"), \
                 patch("video_downloader.converter.combine_videos", return_value=Path("out.mp4")) as mock_comb, \
                 patch("video_downloader.utils.load_config", return_value=self.cfg):

                action_combine_videos(self.cfg)
                mock_comb.assert_called_once()
                out_arg = mock_comb.call_args.kwargs.get("output_path")
                # Output filename must have auto-incremented to _1.mp4 despite relative path inputs
                self.assertEqual(out_arg.name, "combined_clipA_2clips_1.mp4")
        finally:
            os.chdir(orig_cwd)

    def test_action_convert_combine_exception_banner_no_blocking(self):
        """Verify combine errors in action_convert display inline error banner without blocking pause_prompt."""
        import io
        from video_downloader.menu import action_convert

        captured_output = io.StringIO()
        with patch("video_downloader.menu.read_key", side_effect=["8", "0"]), \
             patch("video_downloader.menu.action_combine_videos", side_effect=RuntimeError("FFmpeg combine exploded")), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.utils.load_config", return_value=self.cfg), \
             patch("video_downloader.menu.pause_prompt") as mock_pause, \
             patch("sys.stdout", captured_output):

            action_convert(self.cfg)
            mock_pause.assert_not_called()

        out_text = captured_output.getvalue()
        self.assertIn("Video combine failed: FFmpeg combine exploded", out_text)



    def test_prompt_merge_order_mode_arrow_keys_and_selection(self):
        """Test prompt_merge_order_mode navigation with arrows and enter."""
        from video_downloader.menu import prompt_merge_order_mode

        # Test selecting option 1 (ascending) via ENTER
        with patch("video_downloader.menu.read_key", side_effect=["ENTER"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertEqual(res, "ascending")

        # Test selecting option 2 (random) via DOWN, then ENTER
        with patch("video_downloader.menu.read_key", side_effect=["DOWN", "ENTER"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertEqual(res, "random")

        # Test quick jump keys '1' and '2'
        with patch("video_downloader.menu.read_key", side_effect=["1"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertEqual(res, "ascending")

        with patch("video_downloader.menu.read_key", side_effect=["2"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertEqual(res, "random")

        # Test cancel via ESC / 0 / q
        with patch("video_downloader.menu.read_key", side_effect=["ESC"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertIsNone(res)

        with patch("video_downloader.menu.read_key", side_effect=["0"]), \
             patch("video_downloader.menu.clear_screen"):
            res = prompt_merge_order_mode("TEST HEADER", "items")
            self.assertIsNone(res)

    def test_action_combine_videos_random_order_selection(self):
        """Test action_combine_videos when user selects random shuffle order (option 2)."""
        from video_downloader.menu import action_combine_videos

        vid1 = self.test_dir / "clip1.mp4"
        vid2 = self.test_dir / "clip2.mp4"
        vid1.write_bytes(b"vid1")
        vid2.write_bytes(b"vid2")

        # Sequence: Add vid1 ('1'), Add vid2 ('1'), Start combine ('5'), Pick Random ('2')
        keys = ["1", "1", "5", "2"]
        with patch("video_downloader.menu.read_key", side_effect=keys), \
             patch("video_downloader.menu.browse_interactive_path", side_effect=[vid1, vid2]), \
             patch("video_downloader.menu.clear_screen"), \
             patch("video_downloader.converter.combine_videos", return_value=Path("out.mp4")) as mock_comb, \
             patch("video_downloader.utils.load_config", return_value=self.cfg):

            ret = action_combine_videos(self.cfg)
            self.assertIsNotNone(ret)
            mock_comb.assert_called_once()
            # Verify order='random' passed to combine_videos
            self.assertEqual(mock_comb.call_args.kwargs.get("order"), "random")

if __name__ == "__main__":
    unittest.main()

