import shutil
import sys
import time


class DownloadProgress:

    def __init__(self):

        self.start_time = time.time()
        self.last_render = 0
        self.last_downloaded = 0
        self.last_time = self.start_time
        self.speed = 0
        self.finished = False

    @staticmethod
    def size(value):

        if value is None:
            return "--"

        value = float(value)

        units = [
            "B",
            "KiB",
            "MiB",
            "GiB",
            "TiB"
        ]

        for unit in units:

            if value < 1024:
                return f"{value:.1f} {unit}"

            value /= 1024

        return f"{value:.1f} PiB"

    @staticmethod
    def speed_text(value):

        if not value or value <= 0:
            return "--"

        return (
            DownloadProgress.size(value)
            + "/s"
        )

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

        hours, remainder = divmod(
            seconds,
            3600
        )

        minutes, seconds = divmod(
            remainder,
            60
        )

        if hours:
            return (
                f"{hours:02d}:"
                f"{minutes:02d}:"
                f"{seconds:02d}"
            )

        return (
            f"{minutes:02d}:"
            f"{seconds:02d}"
        )

    def render(
        self,
        downloaded,
        total=None,
        speed=None,
        eta=None
    ):

        now = time.time()

        # Don't redraw hundreds of times per second.
        if (
            now - self.last_render < 0.08
            and total != downloaded
        ):
            return

        self.last_render = now

        # Calculate our own speed if yt-dlp didn't provide it.
        if speed is None:

            elapsed = now - self.last_time

            if elapsed > 0:

                self.speed = (
                    downloaded
                    - self.last_downloaded
                ) / elapsed

        else:
            self.speed = speed

        self.last_downloaded = downloaded
        self.last_time = now

        terminal_width = shutil.get_terminal_size(
            fallback=(80, 20)
        ).columns

        # Keep the bar usable on narrow Android terminals.
        bar_width = max(
            12,
            min(
                36,
                terminal_width - 42
            )
        )

        if total and total > 0:

            percentage = min(
                100,
                max(
                    0,
                    downloaded / total * 100
                )
            )

            filled = int(
                bar_width
                * percentage
                / 100
            )

            bar = (
                "━" * filled
                + "░" * (
                    bar_width - filled
                )
            )

            percent_text = (
                f"{percentage:5.1f}%"
            )

            amount = (
                f"{self.size(downloaded)}"
                f" / "
                f"{self.size(total)}"
            )

        else:

            # Unknown-size download.
            position = int(
                now * 4
            ) % (bar_width + 1)

            bar = (
                "░" * position
                + "━"
                + "░" * (
                    bar_width - position - 1
                )
            )

            percent_text = "  --"

            amount = self.size(
                downloaded
            )

        line = (
            f"\r  ↓ {bar} "
            f"{percent_text}  "
            f"{amount}  "
            f"• {self.speed_text(self.speed)}  "
            f"ETA {self.eta_text(eta)}"
        )

        # Make sure an older, longer line gets erased.
        if len(line) < terminal_width:
            line += " " * (
                terminal_width - len(line)
            )

        sys.stdout.write(
            line[:terminal_width]
        )

        sys.stdout.flush()

    def complete(
        self,
        downloaded=None,
        elapsed=None
    ):

        if self.finished:
            return

        self.finished = True

        if elapsed is None:
            elapsed = (
                time.time()
                - self.start_time
            )

        sys.stdout.write(
            "\r"
            + " " * shutil.get_terminal_size(
                fallback=(80, 20)
            ).columns
            + "\r"
        )

        if downloaded is not None:

            average_speed = (
                downloaded / elapsed
                if elapsed > 0
                else 0
            )

            print(
                f"  ✓ Download complete  "
                f"{self.size(downloaded)}"
                f" • "
                f"{self.speed_text(average_speed)}"
                f" • "
                f"{self.eta_text(elapsed)}"
            )

        else:

            print(
                "  ✓ Download complete"
            )

class Spinner:

    FRAMES = ["/", "|", "-", "\\"]

    def __init__(self, message="Working"):
        self.message = message
        self.index = 0
        self.running = False

    def start(self):
        import sys
        import threading
        import time

        self.running = True
        self.index = 0

        def animate():

            while self.running:

                frame = self.FRAMES[
                    self.index % len(self.FRAMES)
                ]

                sys.stdout.write(
                    f"\r  → {self.message}... {frame}"
                )

                sys.stdout.flush()

                self.index += 1

                time.sleep(0.12)

        self.thread = threading.Thread(
            target=animate,
            daemon=True
        )

        self.thread.start()

    def stop(self, success=True, message=None):

        import sys

        self.running = False

        if hasattr(self, "thread"):
            self.thread.join(
                timeout=0.3
            )

        # Clear current spinner line.
        sys.stdout.write(
            "\r"
            + " " * 100
            + "\r"
        )

        if message:

            symbol = "✓" if success else "✗"

            print(
                f"  {symbol} {message}"
            )

        sys.stdout.flush()

