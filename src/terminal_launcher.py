"""
Terminal Launcher Module for Video Extractor.

OS-Agnostic terminal and process spawning:
- Detects OS (Windows, macOS, Linux desktop, Termux, Headless)
- Spawns new terminal windows/tabs when GUI environment is available:
  - Windows: wt.exe (Windows Terminal) or cmd.exe start
  - macOS: osascript Terminal.app / iTerm
  - Linux (desktop): gnome-terminal, konsole, xfce4-terminal, alacritty, kitty, xterm
  - Termux: tmux / screen simulation, or background subprocess
- Gracefully falls back to concurrent background subprocesses with labeled terminal output if no GUI is available
- Tracks process IDs (PIDs) and reliably terminates entire process trees on cancellation
"""

import os
import shlex
import shutil
import signal
import subprocess
import sys
import threading
from dataclasses import dataclass, field
from pathlib import Path
from typing import Optional

try:
    import psutil
    PSUTIL_AVAILABLE = True
except ImportError:
    PSUTIL_AVAILABLE = False


@dataclass
class LaunchedProcess:
    tier: str
    pid: int
    mode: str  # "terminal" or "subprocess"
    popen: Optional[subprocess.Popen] = None
    pid_file: Optional[Path] = None
    reader_thread: Optional[threading.Thread] = None
    stop_event: Optional[threading.Event] = None

    def get_actual_pid(self) -> int:
        """Read the real worker PID from pid_file if written by the worker."""
        if self.pid_file and self.pid_file.exists():
            try:
                content = self.pid_file.read_text(encoding="utf-8").strip()
                if content:
                    real_pid = int(content)
                    self.pid = real_pid
                    return real_pid
            except Exception:
                pass
        return self.pid

    def close_streams(self) -> None:
        """Signal reader thread to stop and close popen stdout/stderr."""
        if self.stop_event:
            self.stop_event.set()
        if self.popen:
            for stream in (self.popen.stdout, self.popen.stderr):
                if stream:
                    try:
                        stream.close()
                    except Exception:
                        pass
        if self.reader_thread and self.reader_thread.is_alive():
            self.reader_thread.join(timeout=0.5)

    def kill(self) -> bool:
        """Kill this process and all its child processes, then close streams."""
        actual_pid = self.get_actual_pid()
        killed = kill_process_by_pid(actual_pid)
        if self.popen:
            try:
                self.popen.kill()
                self.popen.poll()
            except Exception:
                pass
        self.close_streams()
        return killed

    def reap(self, timeout: float = 1.0) -> None:
        """Wait for process termination and cleanly close streams and file descriptors."""
        if self.popen:
            try:
                self.popen.wait(timeout=timeout)
            except Exception:
                try:
                    self.popen.kill()
                    self.popen.poll()
                except Exception:
                    pass
        self.close_streams()


def detect_platform() -> str:
    """Detect runtime platform: 'termux', 'windows', 'darwin', 'linux_desktop', or 'headless'."""
    prefix = os.environ.get("PREFIX", "")
    if "com.termux" in prefix or (shutil.which("termux-open") and sys.platform.startswith("linux")):
        return "termux"

    if sys.platform == "win32":
        return "windows"

    if sys.platform == "darwin":
        return "darwin"

    if sys.platform.startswith("linux"):
        has_display = bool(os.environ.get("DISPLAY") or os.environ.get("WAYLAND_DISPLAY"))
        if has_display:
            return "linux_desktop"
        return "headless"

    return "headless"


def find_linux_terminal() -> Optional[str]:
    """Find available terminal emulator on desktop Linux."""
    candidates = ["gnome-terminal", "konsole", "xfce4-terminal", "alacritty", "kitty", "xterm"]
    for terminal in candidates:
        if shutil.which(terminal):
            return terminal
    return None


def kill_process_by_pid(pid: int) -> bool:
    """
    Terminate a process and all of its descendants by PID.
    Uses psutil for reliable cross-platform process tree killing,
    with OS-native fallbacks (taskkill on Windows, SIGKILL / process groups on Unix).
    """
    if not pid or pid <= 0:
        return False

    success = False

    if PSUTIL_AVAILABLE:
        try:
            parent = psutil.Process(pid)
            children = parent.children(recursive=True)
            for child in children:
                try:
                    child.kill()
                except (psutil.NoSuchProcess, psutil.AccessDenied):
                    pass
            parent.kill()
            psutil.wait_procs(children + [parent], timeout=1.5)
            success = True
        except (psutil.NoSuchProcess, psutil.AccessDenied):
            success = True
        except Exception:
            success = False

    # OS-native fallbacks
    if not success or not PSUTIL_AVAILABLE:
        if sys.platform == "win32":
            try:
                subprocess.run(
                    ["taskkill", "/F", "/T", "/PID", str(pid)],
                    stdout=subprocess.DEVNULL,
                    stderr=subprocess.DEVNULL,
                    check=False,
                )
                success = True
            except Exception:
                pass
        else:
            try:
                os.killpg(os.getpgid(pid), signal.SIGKILL)
                success = True
            except Exception:
                try:
                    os.kill(pid, signal.SIGKILL)
                    success = True
                except Exception:
                    pass

    return success


def _stream_worker_output(proc: subprocess.Popen, tier: str, stop_event: threading.Event) -> None:
    """Read lines from worker process stdout and print with tier prefix."""
    try:
        if not proc.stdout:
            return
        for raw_line in iter(proc.stdout.readline, ""):
            if stop_event.is_set():
                break
            line = raw_line.rstrip()
            if line:
                print(f"[{tier}] {line}")
    except Exception:
        pass
    finally:
        try:
            if proc.stdout:
                proc.stdout.close()
        except Exception:
            pass


def _spawn_subprocess(
    tier: str,
    command: list[str],
    cwd: Optional[str],
    env: dict,
    pid_file: Optional[Path],
) -> LaunchedProcess:
    """Spawn worker as a background subprocess with streaming labeled terminal output."""
    proc = subprocess.Popen(
        command,
        cwd=cwd,
        env=env,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        encoding="utf-8",
        errors="replace",
    )
    stop_event = threading.Event()
    reader_thread = threading.Thread(
        target=_stream_worker_output,
        args=(proc, tier, stop_event),
        daemon=True,
    )
    reader_thread.start()

    return LaunchedProcess(
        tier=tier,
        pid=proc.pid,
        mode="subprocess",
        popen=proc,
        pid_file=pid_file,
        reader_thread=reader_thread,
        stop_event=stop_event,
    )


def spawn_tier(
    tier: str,
    command: list[str],
    title: str,
    pid_file: Optional[Path] = None,
    prefer_gui: bool = True,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> LaunchedProcess:
    """
    Spawn a worker command in a new terminal window if possible and requested,
    otherwise spawn as a background subprocess with labeled terminal output.

    Returns LaunchedProcess containing the PID and process control handle.
    """
    platform = detect_platform()
    working_dir = str(cwd) if cwd else None
    process_env = os.environ.copy()
    if env:
        process_env.update(env)

    # If GUI terminal spawning is disabled or not possible, run as background subprocess
    if not prefer_gui:
        return _spawn_subprocess(tier, command, working_dir, process_env, pid_file)

    # Platform-specific terminal window spawning
    try:
        if platform == "windows":
            wt_path = shutil.which("wt.exe") or shutil.which("wt")
            cmd_str = subprocess.list2cmdline(command)
            if wt_path:
                launch_args = [wt_path, "--title", title, "cmd.exe", "/c", cmd_str]
                proc = subprocess.Popen(
                    launch_args,
                    cwd=working_dir,
                    env=process_env,
                    creationflags=subprocess.CREATE_NEW_CONSOLE,
                )
                return LaunchedProcess(
                    tier=tier,
                    pid=proc.pid,
                    mode="terminal",
                    popen=proc,
                    pid_file=pid_file,
                )
            else:
                full_cmd = f'start "{title}" cmd.exe /c "{cmd_str}"'
                proc = subprocess.Popen(
                    full_cmd,
                    shell=True,
                    cwd=working_dir,
                    env=process_env,
                )
                return LaunchedProcess(
                    tier=tier,
                    pid=proc.pid,
                    mode="terminal",
                    popen=proc,
                    pid_file=pid_file,
                )

        elif platform == "darwin":
            escaped_cmd = " ".join(shlex.quote(c) for c in command)
            apple_script = f'tell application "Terminal" to do script "{escaped_cmd}"'
            proc = subprocess.Popen(
                ["osascript", "-e", apple_script],
                cwd=working_dir,
                env=process_env,
            )
            return LaunchedProcess(
                tier=tier,
                pid=proc.pid,
                mode="terminal",
                popen=proc,
                pid_file=pid_file,
            )

        elif platform == "linux_desktop":
            terminal = find_linux_terminal()
            if terminal:
                if terminal == "gnome-terminal":
                    launch_args = ["gnome-terminal", "--title", title, "--"] + command
                elif terminal in ("konsole", "xfce4-terminal", "alacritty", "kitty", "xterm"):
                    launch_args = [terminal, "-e"] + command
                else:
                    launch_args = [terminal, "-e"] + command

                proc = subprocess.Popen(
                    launch_args,
                    cwd=working_dir,
                    env=process_env,
                )
                return LaunchedProcess(
                    tier=tier,
                    pid=proc.pid,
                    mode="terminal",
                    popen=proc,
                    pid_file=pid_file,
                )

        elif platform == "termux":
            if os.environ.get("TMUX") and shutil.which("tmux"):
                proc = subprocess.Popen(
                    ["tmux", "new-window", "-n", title] + command,
                    cwd=working_dir,
                    env=process_env,
                )
                return LaunchedProcess(
                    tier=tier,
                    pid=proc.pid,
                    mode="terminal",
                    popen=proc,
                    pid_file=pid_file,
                )
            elif (os.environ.get("STY") or shutil.which("screen")) and shutil.which("screen"):
                proc = subprocess.Popen(
                    ["screen", "-t", title] + command,
                    cwd=working_dir,
                    env=process_env,
                )
                return LaunchedProcess(
                    tier=tier,
                    pid=proc.pid,
                    mode="terminal",
                    popen=proc,
                    pid_file=pid_file,
                )

    except Exception as launch_err:
        print(f"[!] Terminal GUI spawn failed for {tier} ({launch_err}), falling back to background subprocess.")

    # Graceful fallback: background subprocess with streaming labeled terminal output
    return _spawn_subprocess(tier, command, working_dir, process_env, pid_file)
