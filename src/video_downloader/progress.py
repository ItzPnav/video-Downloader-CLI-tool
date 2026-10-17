import os
import shutil
import sys
import time
import threading


# ANSI palette for progress bars and animations
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
DIM = "\033[2m"
BOLD = "\033[1m"
RESET = "\033[0m"


class DownloadProgress:
    """
    High-performance, flicker-free progress bar renderer with smooth braille spinner.
    Supports continuous background animation thread to prevent frozen terminals during downloads.
    """
    SPINNER_FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self):
        self.start_time = time.time()
        self.last_render = 0
        self.last_downloaded = 0
        self.last_time = self.start_time
        self.downloaded = 0
        self.total = None
        self.speed = 0
        self.eta = None
        self.finished = False
        self.spinner_idx = 0
        self._lock = threading.Lock()
        self._thread = None
        self._running = False

    def start(self):
        """Start the background animation ticker thread."""
        self._running = True
        self._thread = threading.Thread(target=self._animate_loop, daemon=True)
        self._thread.start()

    def _animate_loop(self):
        while self._running and not self.finished:
            self._draw_frame()
            time.sleep(0.08)

    @staticmethod
    def size(value):
        if value is None:
            return "--"
        value = float(value)
        units = ["B", "KB", "MB", "GB", "TB"]
        for unit in units:
            if value < 1024:
                return f"{value:.1f} {unit}"
            value /= 1024
        return f"{value:.1f} PB"

    @staticmethod
    def speed_text(value):
        if not value or value <= 0:
            return "--"
        return DownloadProgress.size(value) + "/s"

    @staticmethod
    def eta_text(seconds):
        if seconds is None:
            return "--:--"
        try:
            seconds = int(seconds)
        except (TypeError, ValueError):
            return "--:--"
        if seconds < 0:
            return "--:--"
        hours, remainder = divmod(seconds, 3600)
        minutes, seconds = divmod(remainder, 60)
        if hours:
            return f"{hours:02d}:{minutes:02d}:{seconds:02d}"
        return f"{minutes:02d}:{seconds:02d}"

    def update(self, downloaded, total=None, speed=None, eta=None):
        """Update telemetry thread-safely."""
        now = time.time()
        with self._lock:
            if speed is None:
                elapsed = now - self.last_time
                if elapsed > 0 and downloaded >= self.last_downloaded:
                    self.speed = (downloaded - self.last_downloaded) / elapsed
            else:
                self.speed = speed

            self.downloaded = downloaded
            if total is not None:
                self.total = total
            if eta is not None:
                self.eta = eta
            self.last_downloaded = downloaded
            self.last_time = now

    def render(self, downloaded=None, total=None, speed=None, eta=None):
        """Update and redraw frame immediately."""
        if downloaded is not None:
            self.update(downloaded, total, speed, eta)
        self._draw_frame()

    def _draw_frame(self):
        if self.finished:
            return

        with self._lock:
            downloaded = self.downloaded
            total = self.total
            speed = self.speed
            eta = self.eta
            idx = self.spinner_idx
            self.spinner_idx += 1

        now = time.time()
        elapsed = now - self.start_time
        frame = self.SPINNER_FRAMES[idx % len(self.SPINNER_FRAMES)]

        terminal_width = shutil.get_terminal_size(fallback=(80, 20)).columns
        bar_width = max(10, min(24, terminal_width - 50))

        if total and total > 0:
            percentage = min(100.0, max(0.0, downloaded / total * 100.0))
            filled = int(bar_width * percentage / 100.0)
            bar = f"{CYAN}{'━' * filled}{RESET}{DIM}{'━' * (bar_width - filled)}{RESET}"
            percent_text = f"{BOLD}{CYAN}{percentage:5.1f}%{RESET}"
            amount = f"{DownloadProgress.size(downloaded)}/{DownloadProgress.size(total)}"
        else:
            # Pulsing indeterminate bar
            pos = int(now * 5) % (bar_width + 1)
            bar_chars = ["░"] * bar_width
            if 0 <= pos < bar_width:
                bar_chars[pos] = "━"
            bar = f"{CYAN}{''.join(bar_chars)}{RESET}"
            percent_text = f"{DIM} --.-%{RESET}"
            amount = DownloadProgress.size(downloaded)

        spd = f"{YELLOW}{DownloadProgress.speed_text(speed)}{RESET}"
        eta_str = f"{DIM}ETA {DownloadProgress.eta_text(eta)}{RESET}" if eta is not None else f"{DIM}{DownloadProgress.eta_text(elapsed)}{RESET}"

        line = f"\r  {CYAN}{frame}{RESET} [{bar}] {percent_text}  {amount:<16} • {spd:<14} • {eta_str}"

        # Clean erase padding
        clean_len = terminal_width
        sys.stdout.write(line.ljust(clean_len)[:clean_len])
        sys.stdout.flush()

    def stop(self):
        """Halt animation thread and clean line immediately without summary."""
        if self.finished:
            return
        self.finished = True
        self._running = False
        if self._thread and self._thread.is_alive():
            self._thread.join(timeout=0.2)
        width = shutil.get_terminal_size(fallback=(80, 20)).columns
        sys.stdout.write("\r" + " " * width + "\r")
        sys.stdout.flush()

    def complete(self, downloaded=None, elapsed=None):
        if self.finished:
            return
        if elapsed is None:
            elapsed = time.time() - self.start_time
        final_dl = downloaded if downloaded is not None else self.downloaded

        self.stop()

        if final_dl and final_dl > 0:
            avg_speed = final_dl / elapsed if elapsed > 0 else 0
            print(
                f"  {GREEN}[✓] Download complete{RESET}  "
                f"{BOLD}{DownloadProgress.size(final_dl)}{RESET} "
                f"{DIM}•{RESET} {YELLOW}{DownloadProgress.speed_text(avg_speed)}{RESET} "
                f"{DIM}•{RESET} {DownloadProgress.eta_text(elapsed)}"
            )
        else:
            print(f"  {GREEN}[✓] Download complete{RESET}")
        sys.stdout.flush()


class Spinner:
    """
    Smooth, thread-safe braille spinner with clean status transitions.
    """

    FRAMES = ["⠋", "⠙", "⠹", "⠸", "⠼", "⠴", "⠦", "⠧", "⠇", "⠏"]

    def __init__(self, message="Processing"):
        self.message = message
        self.index = 0
        self.running = False

    def start(self):
        import threading

        self.running = True
        self.index = 0

        def animate():
            while self.running:
                frame = self.FRAMES[self.index % len(self.FRAMES)]
                sys.stdout.write(f"\r  {CYAN}{frame}{RESET} {self.message}...")
                sys.stdout.flush()
                self.index += 1
                time.sleep(0.08)

        self.thread = threading.Thread(target=animate, daemon=True)
        self.thread.start()

    def stop(self, success=True, message=None):
        self.running = False
        if hasattr(self, "thread"):
            self.thread.join(timeout=0.3)

        width = shutil.get_terminal_size(fallback=(80, 20)).columns
        sys.stdout.write("\r" + " " * width + "\r")

        if message:
            if success:
                print(f"  {GREEN}[✓]{RESET} {message}")
            else:
                print(f"  {YELLOW}[!]{RESET} {message}")
        sys.stdout.flush()
