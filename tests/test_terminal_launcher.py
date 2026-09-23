"""
Tests for Terminal Launcher Module.
"""

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

# Add src to sys.path
SRC_DIR = Path(__file__).resolve().parent.parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

try:
    from video_downloader.terminal_launcher import (
        detect_platform,
        find_linux_terminal,
        kill_process_by_pid,
        spawn_tier,
        LaunchedProcess,
    )
except ImportError:
    from terminal_launcher import (
        detect_platform,
        find_linux_terminal,
        kill_process_by_pid,
        spawn_tier,
        LaunchedProcess,
    )


class TestTerminalLauncher(unittest.TestCase):

    def test_detect_platform(self):
        platform = detect_platform()
        self.assertIn(platform, ["windows", "darwin", "linux_desktop", "termux", "headless"])

    def test_spawn_and_kill_subprocess(self):
        # Spawn a long-running python sleep process
        cmd = [sys.executable, "-c", "import time; time.sleep(30)"]
        launched = spawn_tier(
            tier="test_tier",
            command=cmd,
            title="Test Process",
            prefer_gui=False,
        )

        self.assertIsNotNone(launched)
        self.assertGreater(launched.pid, 0)
        self.assertEqual(launched.tier, "test_tier")

        # Verify process is running
        self.assertIsNone(launched.popen.poll())

        # Kill by PID
        killed = kill_process_by_pid(launched.pid)
        self.assertTrue(killed)

        # Allow OS to reap
        time.sleep(0.3)
        launched.popen.poll()
        self.assertIsNotNone(launched.popen.returncode)

    def test_launched_process_pid_file(self):
        with tempfile.TemporaryDirectory() as tmpdir:
            pid_file = Path(tmpdir) / "worker.pid"
            pid_file.write_text("12345", encoding="utf-8")

            proc = LaunchedProcess(
                tier="mock",
                pid=999,
                mode="terminal",
                pid_file=pid_file,
            )

            actual_pid = proc.get_actual_pid()
            self.assertEqual(actual_pid, 12345)


if __name__ == "__main__":
    unittest.main()
