"""
Unit & Contract Verification Tests for Mission Control NiceGUI Frontend (gui.py),
Shared State Contract (CONTRACT.md / design-tokens.json / tokens.css / design.md),
CLI --web / --gui routing, ExtractionRaceController on_event telemetry hooks,
and 3-Step Tactical Button Feedback (Click Animation -> Loading -> Completion Approval).
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
    TacticalButtonController,
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

    def test_tokens_css_eliminates_blue_and_defines_three_step_button_states(self):
        """Verify tokens.css overrides Quasar blue via @layer theme and defines click, loading, and approval states."""
        css = load_mission_control_css()
        self.assertIn("--q-primary: #FFB627 !important", css)
        self.assertIn("@layer theme", css)
        self.assertIn("@keyframes mcClickCompress", css)
        self.assertIn("@keyframes mcHazardScroll", css)
        self.assertIn("@keyframes mcApprovalPop", css)
        self.assertIn(".mc-btn-clicked", css)
        self.assertIn(".btn-tactical-loading", css)
        self.assertIn(".btn-tactical-approved", css)
        self.assertIn(".btn-tactical-fault", css)
        self.assertIn(".mc-approval-banner", css)
        self.assertIn(".disk-dialog-card", css)
        self.assertIn(".disk-dialog-body", css)
        self.assertIn(".disk-entry-row", css)
        self.assertIn(".disk-entry-dir .disk-entry-name", css)
        self.assertIn(".disk-entry-up .disk-entry-name", css)
        self.assertIn(".disk-entry-actions .q-btn", css)
        self.assertIn(".disk-list-scroll", css)
        self.assertIn(".disk-entry-name", css)
        self.assertIn("flex-shrink: 0 !important", css)
        self.assertIn("min-height: 44px !important", css)
        # Ensure default Quasar blue hex codes are never assigned as active colors
        self.assertNotIn("#5898d4", css.lower())
        self.assertNotIn("#1976d2", css.lower())

    def test_get_download_dir_resolves_sdcard_to_user_downloads_on_non_termux(self):
        """Verify /sdcard/Download and C:\\sdcard\\Download resolve to user Downloads folder on non-Termux systems."""
        from video_downloader.utils import get_download_dir, get_tool_output_dir, is_non_termux_sdcard_path

        with patch("video_downloader.utils.is_termux", return_value=False):
            self.assertTrue(is_non_termux_sdcard_path("/sdcard/Download"))
            self.assertTrue(is_non_termux_sdcard_path("C:\\sdcard\\Download"))
            self.assertTrue(is_non_termux_sdcard_path("c:\\sdcard"))
            self.assertFalse(is_non_termux_sdcard_path(str(Path.home() / "Downloads")))

        with patch("video_downloader.utils.load_config", return_value={"download_directory": "C:\\sdcard\\Download"}), \
             patch("video_downloader.utils.is_termux", return_value=False):
            dl_dir = get_download_dir()
            self.assertNotIn("sdcard", str(dl_dir).lower())
            self.assertEqual(dl_dir, (Path.home() / "Downloads").resolve())

            conv_dir = get_tool_output_dir("converter", {"converter_output_directory": "C:\\sdcard\\Download\\Converted"})
            self.assertNotIn("sdcard", str(conv_dir).lower())
            self.assertEqual(conv_dir.name, "Converted")

    def test_lazy_export_in_package_init(self):
        """Verify launch_mission_control is exposed in video_downloader.__all__."""
        self.assertIn("launch_mission_control", video_downloader.__all__)
        self.assertIs(video_downloader.launch_mission_control, launch_mission_control)

    @unittest.skipUnless(is_nicegui_available(), "NiceGUI not installed")
    def test_build_mission_control_dashboard_dom_instantiation_and_zero_blue_buttons(self):
        """Verify all 6 sectors build cleanly, zero buttons have Quasar blue color='primary', and task vs step-1 buttons are properly separated."""
        from nicegui import Client
        from nicegui.page import page
        from video_downloader.gui import build_mission_control_dashboard

        p = page("/test-mission-control")
        with Client(p) as client:
            build_mission_control_dashboard()
            elements = list(client.elements.values())

            q_buttons = [el for el in elements if el.tag == "q-btn"]
            self.assertGreater(len(q_buttons), 15, "Dashboard should instantiate all tactical buttons")

            for btn in q_buttons:
                # No button may retain Quasar's default blue color='primary' prop
                self.assertNotEqual(
                    btn._props.get("color"),
                    "primary",
                    f"Button {btn._props.get('label')} must not use Quasar default blue color='primary'",
                )
                has_tactical_class = any(
                    c in btn._classes
                    for c in ("btn-tactical-primary", "btn-tactical-secondary", "btn-tactical-danger")
                )
                self.assertTrue(
                    has_tactical_class,
                    f"Button {btn._props.get('label')} must have a Mission Control tactical button class",
                )

            # Verify upload/download/task buttons have data-mc-task="true"
            task_labels = {
                btn._props.get("label")
                for btn in q_buttons
                if btn._props.get("data-mc-task") == "true"
            }
            for expected_task_btn in (
                "Download Video",
                "Convert",
                "Merge Videos",
                "Start Download",
                "Create Archive",
                "Extract Text",
                "File",
                "Folder",
                "+ Add Video",
                "+ Add Folder",
                "Browse",
                "Cookies",
                "Browse Folder",
            ):
                self.assertIn(
                    expected_task_btn,
                    task_labels,
                    f"Task/upload/download button '{expected_task_btn}' must use 3-step TacticalButtonController",
                )

            # Verify non-upload/download buttons only use Step 1 (no data-mc-task="true")
            step1_only_labels = {
                btn._props.get("label")
                for btn in q_buttons
                if btn._props.get("data-mc-task") != "true"
            }
            for expected_step1_btn in (
                "Close",
                "OK",
                "Go",
                "Up",
                "Downloads",
                "Home",
                "Project",
                "Clear",
                "Copy Text",
                "Change Output Folder",
                "Auto-Separate Folders",
                "Reset Defaults",
                "Refresh",
            ):
                self.assertIn(
                    expected_step1_btn,
                    step1_only_labels,
                    f"Utility button '{expected_step1_btn}' must be Step-1 click animation only",
                )

    @unittest.skipUnless(is_nicegui_available(), "NiceGUI not installed")
    def test_tactical_button_controller_three_step_lifecycle_and_edge_cases(self):
        """Verify TacticalButtonController transitions cleanly through Click -> Loading -> Approval, Fault, and Reset."""
        from nicegui import Client, ui
        from nicegui.page import page

        p = page("/test-btn-lifecycle")
        with Client(p):
            banner_box = ui.column()
            banner_box.set_visibility(False)
            btn = ui.button("Download Video", color=None).classes("btn-tactical-primary")
            ctrl = TacticalButtonController(btn, "Download Video", approval_banner_container=banner_box)

            # Initial state
            self.assertEqual(ctrl.state, "idle")
            self.assertEqual(btn._props.get("data-mc-state"), "idle")

            # Step 1: Click animation
            ctrl.pulse_click()
            self.assertIn("mc-btn-clicked", btn._classes)

            # Step 2: Loading state + live progress clamping
            ctrl.start_loading("SCANNING STREAM...")
            self.assertEqual(ctrl.state, "loading")
            self.assertIn("btn-tactical-loading", btn._classes)
            self.assertEqual(btn._props.get("data-mc-state"), "loading")
            self.assertEqual(btn.text, "SCANNING STREAM...")
            self.assertFalse(btn.enabled)

            ctrl.update_loading(145, "DOWNLOADING")
            self.assertEqual(btn.text, "DOWNLOADING · 100%")
            ctrl.update_loading(-10, "DOWNLOADING")
            self.assertEqual(btn.text, "DOWNLOADING · 0%")

            # Step 3: Completion Approval state + approval banner
            ctrl.approve("APPROVED // VIDEO DOWNLOADED", banner_detail="[✓] Saved to /tmp/video.mp4")
            self.assertEqual(ctrl.state, "approved")
            self.assertIn("btn-tactical-approved", btn._classes)
            self.assertNotIn("btn-tactical-loading", btn._classes)
            self.assertEqual(btn._props.get("data-mc-state"), "approved")
            self.assertTrue(btn.text.startswith("[✓]"))
            self.assertTrue(btn.enabled)
            self.assertTrue(banner_box.visible)

            # Fault state edge case
            ctrl.fail("[!] TIMED OUT — RETRY")
            self.assertEqual(ctrl.state, "fault")
            self.assertIn("btn-tactical-fault", btn._classes)
            self.assertNotIn("btn-tactical-approved", btn._classes)
            self.assertTrue(btn.enabled)

            # Reset to idle
            ctrl.reset()
            self.assertEqual(ctrl.state, "idle")
            self.assertEqual(btn.text, "Download Video")
            self.assertNotIn("btn-tactical-fault", btn._classes)

    @unittest.skipUnless(is_nicegui_available(), "NiceGUI not installed")
    def test_disk_browser_renders_folder_entries_properly(self):
        """Verify disk browser modal renders visible .disk-entry-row items, shows files in leaf folders in folder mode, and handles invalid paths."""
        import tempfile
        from nicegui import Client
        from nicegui.page import page
        from video_downloader.gui import build_mission_control_dashboard

        with tempfile.TemporaryDirectory() as tmp:
            tmp_path = Path(tmp)
            alpha_dir = tmp_path / "AlphaBatch"
            alpha_dir.mkdir()
            (alpha_dir / "sample_clip.mp4").write_bytes(b"0000")
            (tmp_path / "BetaClips").mkdir()
            (tmp_path / "$Recycle.Bin").mkdir()  # Should be filtered out

            with patch("video_downloader.gui.get_download_dir", return_value=tmp_path):
                p = page("/test-disk-browser")
                with Client(p) as client:
                    build_mission_control_dashboard()
                    # Trigger the 'Folder' button click on Sector 02 (Convert Media)
                    folder_btns = [
                        el for el in client.elements.values()
                        if el.tag == "q-btn" and el._props.get("label") == "Folder"
                    ]
                    self.assertGreaterEqual(len(folder_btns), 1)
                    for listener in list(folder_btns[0]._event_listeners.values()):
                        if listener.type == "click":
                            try:
                                listener.handler(None)
                            except TypeError:
                                listener.handler()

                    all_els = list(client.elements.values())
                    entry_rows = [el for el in all_els if "disk-entry-row" in getattr(el, "_classes", [])]
                    self.assertGreaterEqual(len(entry_rows), 2, "Must render folder entry rows")

                    entry_names = [
                        el._props.get("innerHTML") or getattr(el, "text", "")
                        for el in all_els
                        if "disk-entry-name" in getattr(el, "_classes", [])
                    ]
                    self.assertIn("AlphaBatch/", entry_names)
                    self.assertIn("BetaClips/", entry_names)
                    self.assertNotIn("$Recycle.Bin/", entry_names)

                    # Navigate into AlphaBatch/ (leaf folder with a file and 0 subfolders) in folder mode
                    dir_rows = [el for el in all_els if "disk-entry-dir" in getattr(el, "_classes", [])]
                    self.assertGreaterEqual(len(dir_rows), 1)
                    open_btns = [
                        el for el in all_els
                        if el.tag == "q-btn"
                        and el._props.get("label") == "Open"
                        and el.parent_slot is not None
                        and "disk-entry-actions" in getattr(el.parent_slot.parent, "_classes", [])
                    ]
                    self.assertGreaterEqual(len(open_btns), 1)
                    for listener in list(open_btns[0]._event_listeners.values()):
                        if listener.type == "click":
                            try:
                                listener.handler(None)
                            except TypeError:
                                listener.handler()

                    leaf_els = list(client.elements.values())
                    leaf_names = [
                        el._props.get("innerHTML") or getattr(el, "text", "")
                        for el in leaf_els
                        if "disk-entry-name" in getattr(el, "_classes", [])
                    ]
                    self.assertIn("sample_clip.mp4", leaf_names, "Leaf folder in folder mode must display contained files")
                    all_labels = [getattr(el, "text", "") for el in leaf_els]
                    self.assertNotIn("No matching folders or files in this directory.", all_labels)


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
