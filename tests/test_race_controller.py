"""
Tests for Extraction Race Controller and LangGraph Orchestration.
"""

import json
import sys
import time
import unittest
from pathlib import Path

# Force UTF-8 stream encoding on Windows
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from video_downloader.race_controller import ExtractionRaceController, RaceResult, LANGGRAPH_AVAILABLE
    from video_downloader.candidate import Candidate
    from video_downloader.utils import write_history, ROOT
except ImportError:
    from race_controller import ExtractionRaceController, RaceResult, LANGGRAPH_AVAILABLE
    from candidate import Candidate
    from utils import write_history, ROOT


class TestRaceController(unittest.TestCase):

    def test_active_tiers_configuration(self):
        controller = ExtractionRaceController(
            url="https://example.com/video",
            no_browser=True,
            no_ytdlp=True,
        )
        self.assertNotIn("browser", controller.active_tiers)
        self.assertNotIn("ytdlp", controller.active_tiers)
        self.assertIn("static", controller.active_tiers)
        self.assertIn("scrapling", controller.active_tiers)

    def test_langgraph_graph_build(self):
        if not LANGGRAPH_AVAILABLE:
            self.skipTest("LangGraph not installed")

        controller = ExtractionRaceController(
            url="https://example.com/video",
            no_browser=True,
        )
        graph = controller.build_langgraph()
        self.assertIsNotNone(graph)

    def test_race_winner_kills_losers(self):
        """Simulate a race between test_fast and test_hung, verify winner and killed PIDs."""
        controller = ExtractionRaceController(
            url="https://example.com/video",
            timeout=5.0,
            prefer_gui=False,
        )
        controller.active_tiers = ["test_fast", "test_hung"]

        result = controller.run_race()

        self.assertEqual(result.winner_engine, "test_fast")
        self.assertIsNotNone(result.candidate)
        self.assertEqual(result.candidate.score, 95)
        self.assertFalse(result.timed_out)

        # Verify test_hung was killed
        hung_pid = result.spawned_pids.get("test_hung")
        self.assertIsNotNone(hung_pid)
        self.assertIn(hung_pid, result.killed_pids)

    def test_race_timeout(self):
        """Verify that race timeout terminates all running agents."""
        controller = ExtractionRaceController(
            url="https://example.com/video",
            timeout=0.6,
            prefer_gui=False,
        )
        controller.active_tiers = ["test_hung"]

        result = controller.run_race()

        self.assertTrue(result.timed_out)
        self.assertIsNone(result.candidate)

        hung_pid = result.spawned_pids.get("test_hung")
        self.assertIsNotNone(hung_pid)
        self.assertIn(hung_pid, result.killed_pids)

    def test_history_logging_with_race_duration(self):
        test_entry = {
            "url": "https://example.com/test-race-video",
            "platform": "generic",
            "engine": "scrapling",
            "quality": "720p",
            "output": "/sdcard/Download/test.mp4",
            "race_duration_ms": 345,
        }
        write_history(test_entry)

        history_file = ROOT / "config" / "history.json"
        self.assertTrue(history_file.exists())
        history = json.loads(history_file.read_text(encoding="utf-8"))
        latest = history[-1]

        self.assertEqual(latest["url"], "https://example.com/test-race-video")
        self.assertEqual(latest["engine"], "scrapling")
        self.assertEqual(latest["race_duration_ms"], 345)

    def test_empty_active_tiers(self):
        controller = ExtractionRaceController(
            url="https://example.com/video",
            no_browser=True,
            no_ytdlp=True,
            no_static=True,
            no_scrapling=True,
        )
        result = controller.run_race()
        self.assertIsNone(result.winner_engine)
        self.assertIsNone(result.candidate)
        self.assertFalse(result.timed_out)

    def test_confidence_threshold_filtering(self):
        # test_fast gives score 95. If threshold is 99, it should not win and exit early
        controller = ExtractionRaceController(
            url="https://example.com/video",
            timeout=5.0,
            confidence_threshold=99,
            prefer_gui=False,
        )
        controller.active_tiers = ["test_fast"]
        result = controller.run_race()
        self.assertIsNone(result.winner_engine)
        self.assertIsNone(result.candidate)
        self.assertFalse(result.timed_out)

    def test_default_prefer_gui_is_false(self):
        controller = ExtractionRaceController(url="https://example.com/video")
        self.assertFalse(controller.prefer_gui)

    def test_browser_grace_seconds_configuration(self):
        controller = ExtractionRaceController(
            url="https://example.com/video",
            browser_grace_seconds=4.0,
        )
        self.assertEqual(controller.browser_grace_seconds, 4.0)

    def test_browser_deferred_when_fast_tier_wins(self):
        """When a fast tier wins before browser_grace_seconds, browser tier should never spawn."""
        controller = ExtractionRaceController(
            url="https://example.com/video",
            timeout=5.0,
            browser_grace_seconds=4.0,
            prefer_gui=False,
        )
        controller.active_tiers = ["test_fast", "browser"]
        result = controller.run_race()

        self.assertEqual(result.winner_engine, "test_fast")
        self.assertIn("test_fast", result.spawned_pids)
        # Browser tier should never have been launched
        self.assertNotIn("browser", result.spawned_pids)


    def test_browser_spawns_after_grace_period(self):
        """When immediate tiers don't produce a winner, browser tier is released after grace."""
        controller = ExtractionRaceController(
            url="https://example.com/video",
            timeout=1.8,
            browser_grace_seconds=0.3,
            prefer_gui=False,
        )
        controller.active_tiers = ["test_hung", "browser"]
        result = controller.run_race()

        self.assertIn("test_hung", result.spawned_pids)
        self.assertIn("browser", result.spawned_pids)


if __name__ == "__main__":
    unittest.main()

