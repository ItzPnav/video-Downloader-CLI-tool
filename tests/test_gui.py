"""
Unit & Contract Verification Tests for Mission Control NiceGUI Frontend (gui.py),
Shared State Contract (CONTRACT.md / design-tokens.json / tokens.css / design.md),
CLI --web / --gui routing, and ExtractionRaceController on_event telemetry hooks.
"""

import json
import sys
import unittest
from pathlib import Path
from unittest.mock import MagicMock, patch

SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import video_downloader
from video_downloader.cli import main as cli_main, run_cli_gui
from video_downloader.gui import (
    CONTRACT_MD_PATH,
    DESIGN_MD_PATH,
    TOKENS_CSS_PATH,
    TOKENS_JSON_PATH,
    is_nicegui_available,
    launch_mission_control,
    load_design_tokens,
    load_mission_control_css,
)
from video_downloader.race_controller import ExtractionRaceController


class TestMissionControlDesignContract(unittest.TestCase):
    """Verify Design & Motion Studio Shared State Contract and Mission Control Five Unbreakable Laws."""

    def test_state_contract_files_exist(self):
        """All 4 CONTRACT.md state artifacts must exist in src/video_downloader/ui/."""
        self.assertTrue(CONTRACT_MD_PATH.is_file(), "CONTRACT.md must exist")
        self.assertTrue(TOKENS_JSON_PATH.is_file(), "design-tokens.json must exist")
        self.assertTrue(DESIGN_MD_PATH.is_file(), "design.md must exist")
        self.assertTrue(TOKENS_CSS_PATH.is_file(), "tokens.css must exist")

    def test_design_tokens_json_schema_and_axioms(self):
        """Verify W3C DTCG design-tokens.json enforces Mission Control axioms and colors."""
        tokens = load_design_tokens()
        self.assertEqual(tokens.get("axioms", {}).get("dialect"), "mission-control-design")
        self.assertTrue(tokens.get("axioms", {}).get("geometry", {}).get("enforceZeroRadius"))
        self.assertEqual(tokens.get("axioms", {}).get("geometry", {}).get("borderRadius"), "0px")
        self.assertEqual(tokens.get("color", {}).get("bg", {}).get("$value"), "#0A0D10")
        self.assertEqual(tokens.get("color", {}).get("accentStatus", {}).get("$value"), "#39FF88")
        self.assertEqual(tokens.get("color", {}).get("accentAction", {}).get("$value"), "#FFB627")
        self.assertEqual(tokens.get("color", {}).get("accentDestructive", {}).get("$value"), "#FF5C4D")

    def test_tokens_css_five_unbreakable_laws_and_a11y(self):
        """Verify tokens.css enforces 0-radius, fonts, scanline, fuelCrawl, radarPulse, and reduced-motion."""
        css = load_mission_control_css()
        self.assertIn("Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V5", css)
        self.assertIn("border-radius: 0 !important", css)
        self.assertIn("#39FF88", css)
        self.assertIn("#FFB627", css)
        self.assertIn("#FF5C4D", css)
        self.assertIn("Big Shoulders Display", css)
        self.assertIn("JetBrains Mono", css)
        self.assertIn(".scanline", css)
        self.assertIn(".rocker-switch", css)
        self.assertIn(".gauge-fill", css)
        self.assertIn("@keyframes fuelCrawl", css)
        self.assertIn("@keyframes radarPulse", css)
        self.assertIn("prefers-reduced-motion: reduce", css)

    def test_tokens_css_prevents_quasar_icon_and_text_overflow(self):
        """Verify tokens.css preserves Material Icons font and prevents sector/input/button bleed."""
        css = load_mission_control_css()
        self.assertIn(".q-select__dropdown-icon", css)
        self.assertIn("'Material Icons'", css)
        self.assertIn(".sector-nav-grid", css)
        self.assertIn(".sector-nav-title", css)
        self.assertIn("text-overflow: ellipsis", css)
        self.assertIn(".q-btn.btn-tactical-primary.bg-primary", css)

    def test_lazy_export_in_package_init(self):
        """Verify launch_mission_control is exposed in video_downloader.__all__."""
        self.assertIn("launch_mission_control", video_downloader.__all__)
        self.assertIs(video_downloader.launch_mission_control, launch_mission_control)

    @unittest.skipUnless(is_nicegui_available(), "NiceGUI not installed")
    def test_build_mission_control_dashboard_dom_instantiation(self):
        """Verify all 6 Mission Control sectors build cleanly inside a live NiceGUI 4.0 Client context."""
        from nicegui import Client
        from nicegui.page import page
        from video_downloader.gui import build_mission_control_dashboard

        p = page("/test-mission-control")
        with Client(p):
            build_mission_control_dashboard()


class TestCLIGuiAndWebRouting(unittest.TestCase):
    """Verify CLI flag parsing and routing for --web, web, --gui, gui, --ui."""

    def test_cli_web_flag_routes_to_launch_mission_control(self):
        """Verify 'tools --web --port 9090 --no-open' dispatches with native=False."""
        with patch("video_downloader.gui.launch_mission_control", return_value=0) as mock_launch:
            code = cli_main(["--web", "--port", "9090", "--host", "0.0.0.0", "--no-open"])
            self.assertEqual(code, 0)
            mock_launch.assert_called_once_with(
                native=False,
                port=9090,
                host="0.0.0.0",
                open_browser=False,
            )

    def test_cli_gui_flag_routes_to_native_mode(self):
        """Verify 'tools --gui' dispatches with native=True."""
        with patch("video_downloader.gui.launch_mission_control", return_value=0) as mock_launch:
            code = cli_main(["--gui", "--port=8181"])
            self.assertEqual(code, 0)
            mock_launch.assert_called_once_with(
                native=True,
                port=8181,
                host="127.0.0.1",
                open_browser=True,
            )

    def test_cli_invalid_port_returns_error(self):
        """Verify invalid --port value returns exit code 1."""
        code = run_cli_gui(["--port", "not_a_number"])
        self.assertEqual(code, 1)


class TestRaceControllerTelemetryCallbacks(unittest.TestCase):
    """Verify ExtractionRaceController emits structured on_event dicts without breaking on callback errors."""

    def test_on_event_emits_race_start_and_complete(self):
        events = []
        controller = ExtractionRaceController(
            url="https://example.com/video",
            no_ytdlp=True,
            no_scrapling=True,
            no_static=True,
            no_browser=True,
            on_event=lambda ev: events.append(ev),
        )
        controller._start_time = 1000.0
        controller._emit("race_start", url="https://example.com/video")
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0]["type"], "race_start")
        self.assertEqual(events[0]["url"], "https://example.com/video")
        self.assertIn("elapsed_ms", events[0])

    def test_on_event_swallows_callback_exceptions_safely(self):
        def _bad_callback(_ev):
            raise RuntimeError("UI listener disconnected")

        controller = ExtractionRaceController(
            url="https://example.com/video",
            no_ytdlp=True,
            no_scrapling=True,
            no_static=True,
            no_browser=True,
            on_event=_bad_callback,
        )
        # Must not raise
        controller._emit("tier_spawned", tier="scrapling", pid=1234)


if __name__ == "__main__":
    unittest.main()
