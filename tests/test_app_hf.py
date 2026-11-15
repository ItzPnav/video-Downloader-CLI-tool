import sys
import types
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

try:
    import gradio as gr
except ImportError:
    class _DummyError(Exception):
        pass

    class _DummyCtx:
        def __init__(self, *args, **kwargs):
            pass
        def __enter__(self):
            return self
        def __exit__(self, *args):
            return False

    class _DummyComp:
        def __init__(self, *args, **kwargs):
            pass
        def click(self, *args, **kwargs):
            pass

    gr = types.ModuleType("gradio")
    gr.Error = _DummyError
    gr.Blocks = _DummyCtx
    gr.Row = _DummyCtx
    gr.Markdown = _DummyComp
    gr.Textbox = _DummyComp
    gr.Dropdown = _DummyComp
    gr.Button = _DummyComp
    gr.Video = _DummyComp
    gr.File = _DummyComp
    sys.modules["gradio"] = gr

ROOT = Path(__file__).resolve().parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

import app as hf_app
import video_downloader.downloader as dl_mod
import video_downloader.site_extractor as se_mod
import video_downloader.utils as utils_mod
from video_downloader.candidate import Candidate
from video_downloader.race_controller import RaceResult


class TestHFApp(unittest.TestCase):
    def test_empty_url_raises_gradio_error(self):
        with self.assertRaises(gr.Error):
            hf_app.extract_and_download("   ", "best")

    def test_ytdlp_uses_patched_temp_download_dir_and_restores(self):
        orig_utils = utils_mod.get_download_dir
        orig_dl = dl_mod.get_download_dir
        orig_se = se_mod.get_download_dir

        cand = Candidate(
            url="https://example.com/watch?v=123",
            source="ytdlp",
            score=100,
            metadata={"title": "Sample Title", "engine": "ytdlp"},
        )
        race_res = RaceResult(
            winner_engine="ytdlp",
            candidate=cand,
            duration_ms=42,
            spawned_pids={},
            killed_pids=[],
        )

        def fake_ytdlp_download(url, requested_quality=None, output_path=None):
            target_dir = se_mod.get_target_download_dir()
            out = Path(output_path) if output_path else (target_dir / "Actual Title.mp4")
            out.parent.mkdir(parents=True, exist_ok=True)
            out.write_bytes(b"fake-mp4-bytes")
            return True

        with patch("app.ExtractionRaceController") as mock_ctrl_cls, \
             patch("video_downloader.downloader.ensure_environment"), \
             patch("video_downloader.site_extractor.download", side_effect=fake_ytdlp_download):
            mock_ctrl = MagicMock()
            mock_ctrl.run_race.return_value = race_res
            mock_ctrl_cls.return_value = mock_ctrl

            status, preview_path, file_path = hf_app.extract_and_download(
                "https://example.com/watch?v=123", "best"
            )

        self.assertIn("ytdlp", status)
        self.assertEqual(preview_path, file_path)
        self.assertTrue(Path(file_path).is_file())
        self.assertIn("toolkit_hf_", file_path)

        # Ensure monkey-patches were restored
        self.assertIs(utils_mod.get_download_dir, orig_utils)
        self.assertIs(dl_mod.get_download_dir, orig_dl)
        self.assertIs(se_mod.get_download_dir, orig_se)

    def test_restores_get_download_dir_on_failure(self):
        orig_utils = utils_mod.get_download_dir
        orig_dl = dl_mod.get_download_dir
        orig_se = se_mod.get_download_dir

        cand = Candidate(
            url="https://example.com/watch?v=err",
            source="ytdlp",
            score=100,
            metadata={"title": "Fail", "engine": "ytdlp"},
        )
        race_res = RaceResult(
            winner_engine="ytdlp",
            candidate=cand,
            duration_ms=10,
            spawned_pids={},
            killed_pids=[],
        )

        with patch("app.ExtractionRaceController") as mock_ctrl_cls, \
             patch("app.download", side_effect=RuntimeError("boom")):
            mock_ctrl = MagicMock()
            mock_ctrl.run_race.return_value = race_res
            mock_ctrl_cls.return_value = mock_ctrl

            with self.assertRaises(RuntimeError):
                hf_app.extract_and_download("https://example.com/watch?v=err", "best")

        self.assertIs(utils_mod.get_download_dir, orig_utils)
        self.assertIs(dl_mod.get_download_dir, orig_dl)
        self.assertIs(se_mod.get_download_dir, orig_se)


if __name__ == "__main__":
    unittest.main()
