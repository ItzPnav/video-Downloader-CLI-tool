"""
Interactive Terminal Menu & Navigation System for Video Extractor.
Provides arrow-key driven workflows, clean ANSI interface, and full configuration control.
"""

import os
import sys
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from .utils import (
    load_config,
    save_config,
    get_download_dir,
    get_version,
    write_history,
    safe_filename,
)
from .cli import system_open, valid_url


# ============================================================================
# ANSI STYLING & TERMINAL SETUP
# ============================================================================

# Enable Virtual Terminal Processing on Windows
if sys.platform == "win32":
    try:
        import ctypes
        kernel32 = ctypes.windll.kernel32
        # ENABLE_PROCESSED_OUTPUT (1) | ENABLE_WRAP_AT_EOL_OUTPUT (2) | ENABLE_VIRTUAL_TERMINAL_PROCESSING (4) = 7
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# Palette
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
ITALIC = "\033[3m"
UNDERLINE = "\033[4m"

# Foreground colors
FG_BLACK = "\033[30m"
FG_RED = "\033[91m"
FG_GREEN = "\033[92m"
FG_YELLOW = "\033[93m"
FG_BLUE = "\033[94m"
FG_MAGENTA = "\033[95m"
FG_CYAN = "\033[96m"
FG_WHITE = "\033[97m"

# Background colors
BG_CYAN = "\033[46m"
BG_BLUE = "\033[44m"
BG_GRAY = "\033[100m"

# Common video file extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".m4v", ".mov", ".avi",
    ".3gp", ".3g2", ".flv", ".f4v", ".wmv", ".ogv",
    ".mpeg", ".mpg", ".ts", ".m2ts", ".mts"
}


def clear_screen():
    """Clear terminal screen and position cursor at origin."""
    if os.name == "nt":
        os.system("cls")
    else:
        sys.stdout.write("\033[2J\033[H")
        sys.stdout.flush()


def hide_cursor():
    """Hide terminal cursor for smooth menu navigation."""
    sys.stdout.write("\033[?25l")
    sys.stdout.flush()


def show_cursor():
    """Restore terminal cursor."""
    sys.stdout.write("\033[?25h")
    sys.stdout.flush()


# ============================================================================
# ZERO-DEPENDENCY CROSS-PLATFORM KEYBOARD ENGINE
# ============================================================================

def get_clipboard_text() -> str | None:
    """Retrieve text from system clipboard using platform-native APIs without third-party dependencies."""
    if sys.platform == "win32":
        try:
            import ctypes
            user32 = ctypes.windll.user32
            kernel32 = ctypes.windll.kernel32

            user32.OpenClipboard.argtypes = [ctypes.c_void_p]
            user32.OpenClipboard.restype = ctypes.c_bool
            user32.GetClipboardData.argtypes = [ctypes.c_uint]
            user32.GetClipboardData.restype = ctypes.c_void_p
            user32.CloseClipboard.argtypes = []
            user32.CloseClipboard.restype = ctypes.c_bool
            kernel32.GlobalLock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalLock.restype = ctypes.c_void_p
            kernel32.GlobalUnlock.argtypes = [ctypes.c_void_p]
            kernel32.GlobalUnlock.restype = ctypes.c_bool

            if not user32.OpenClipboard(None):
                return None
            CF_UNICODETEXT = 13
            h_mem = user32.GetClipboardData(CF_UNICODETEXT)
            if not h_mem:
                user32.CloseClipboard()
                return None
            p_mem = kernel32.GlobalLock(h_mem)
            if not p_mem:
                user32.CloseClipboard()
                return None
            text = ctypes.c_wchar_p(p_mem).value
            kernel32.GlobalUnlock(h_mem)
            user32.CloseClipboard()
            return text
        except Exception:
            pass
    elif "com.termux" in os.environ.get("PREFIX", ""):
        try:
            import subprocess
            out = subprocess.check_output(["termux-clipboard-get"], stderr=subprocess.DEVNULL, timeout=1)
            return out.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
    elif sys.platform == "darwin":
        try:
            import subprocess
            out = subprocess.check_output(["pbpaste"], stderr=subprocess.DEVNULL, timeout=1)
            return out.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
    else:
        # Linux xclip / wl-paste fallback
        try:
            import subprocess
            for cmd in (["wl-paste"], ["xclip", "-selection", "clipboard", "-o"]):
                if shutil.which(cmd[0]):
                    out = subprocess.check_output(cmd, stderr=subprocess.DEVNULL, timeout=1)
                    return out.decode("utf-8", errors="ignore").strip()
        except Exception:
            pass
    return None


def read_key() -> str:
    """
    Read a single keypress or escape sequence from terminal.
    Safely captures Ctrl+V and rapid-fire pasted streams so menus don't flicker or misfire.
    Returns: 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'SPACE', 'ESC', 'BACKSPACE',
             'CTRL_V', 'URL:<url>', 'IGNORE', or single char character like '1', 'q', etc.
    """
    if sys.platform == "win32":
        import msvcrt
        ch = msvcrt.getch()
        if ch in (b"\x00", b"\xe0"):
            sub = msvcrt.getch()
            if sub == b"H":
                return "UP"
            elif sub == b"P":
                return "DOWN"
            elif sub == b"K":
                return "LEFT"
            elif sub == b"M":
                return "RIGHT"
            return "SPECIAL"
        if ch in (b"\r", b"\n"):
            return "ENTER"
        if ch == b" ":
            return "SPACE"
        if ch == b"\x1b":
            return "ESC"
        if ch == b"\x08":
            return "BACKSPACE"
        if ch == b"\x03":
            raise KeyboardInterrupt
        if ch == b"\x16":
            # Ctrl+V key combination detected
            # Drain any trailing buffer characters sent by some terminal emulators
            extra_chars = []
            while msvcrt.kbhit():
                try:
                    c = msvcrt.getch()
                    if c not in (b"\x00", b"\xe0"):
                        extra_chars.append(c.decode("utf-8", errors="ignore"))
                except Exception:
                    pass
            extra_text = "".join(extra_chars).strip()
            if extra_text.startswith(("http://", "https://")):
                return f"URL:{extra_text}"
            return "CTRL_V"

        # Check if this character is part of a rapid-fire paste stream from terminal
        if msvcrt.kbhit():
            buf = [ch]
            while msvcrt.kbhit():
                try:
                    c = msvcrt.getch()
                    if c not in (b"\x00", b"\xe0"):
                        buf.append(c)
                except Exception:
                    pass
            try:
                full_text = b"".join(buf).decode("utf-8", errors="ignore").strip()
                if full_text.startswith(("http://", "https://")):
                    return f"URL:{full_text}"
                for part in full_text.split():
                    if part.startswith(("http://", "https://")):
                        return f"URL:{part}"
                return "IGNORE"
            except Exception:
                return "IGNORE"

        try:
            return ch.decode("utf-8", errors="ignore")
        except Exception:
            return ""
    else:
        import termios
        import tty
        import select

        fd = sys.stdin.fileno()
        old_settings = termios.tcgetattr(fd)
        try:
            tty.setraw(fd)
            ch = sys.stdin.read(1)
            if ch == "\x1b":
                r, _, _ = select.select([sys.stdin], [], [], 0.05)
                if r:
                    ch2 = sys.stdin.read(1)
                    if ch2 == "[":
                        ch3 = sys.stdin.read(1)
                        if ch3 == "A":
                            return "UP"
                        elif ch3 == "B":
                            return "DOWN"
                        elif ch3 == "C":
                            return "RIGHT"
                        elif ch3 == "D":
                            return "LEFT"
                return "ESC"
            if ch in ("\r", "\n"):
                return "ENTER"
            if ch == " ":
                return "SPACE"
            if ch in ("\x7f", "\x08"):
                return "BACKSPACE"
            if ch == "\x03":
                raise KeyboardInterrupt
            if ch == "\x16":
                return "CTRL_V"

            # Check if more characters are immediately available (terminal paste stream)
            r, _, _ = select.select([sys.stdin], [], [], 0.02)
            if r:
                buf = [ch]
                while True:
                    r2, _, _ = select.select([sys.stdin], [], [], 0.01)
                    if not r2:
                        break
                    buf.append(sys.stdin.read(1))
                full_text = "".join(buf).strip()
                if full_text.startswith(("http://", "https://")):
                    return f"URL:{full_text}"
                for part in full_text.split():
                    if part.startswith(("http://", "https://")):
                        return f"URL:{part}"
                return "IGNORE"

            return ch
        finally:
            termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)


def pause_prompt(message: str = "Press any key to return to menu..."):
    """Show prompt and wait for user keypress."""
    print(f"\n{DIM}{message}{RESET}")
    try:
        read_key()
    except KeyboardInterrupt:
        pass


# ============================================================================
# MENU RENDERING COMPONENTS
# ============================================================================

def render_banner(config: dict):
    """Render top application banner and status bar."""
    version = get_version()
    download_dir = str(get_download_dir())
    if len(download_dir) > 42:
        download_dir = "..." + download_dir[-39:]

    # Engine status indicators
    engines = []
    if config.get("use_ytdlp", True):
        engines.append(f"{FG_GREEN}yt-dlp{RESET}")
    if config.get("use_scrapling", True):
        engines.append(f"{FG_GREEN}scrapling{RESET}")
    if config.get("use_static_scanner", True):
        engines.append(f"{FG_GREEN}static{RESET}")
    if config.get("use_browser", True):
        engines.append(f"{FG_GREEN}browser{RESET}")
    engine_line = " ".join(f"[{e}]" for e in engines) or f"{FG_RED}[none]{RESET}"

    timeout = config.get("race_timeout", 20)
    grace = config.get("browser_grace_seconds", 2.5)
    fmt = config.get("merge_format", "mp4")

    print(f"{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
    print(f"{FG_CYAN}│{RESET}  {BOLD}{FG_WHITE}▶  VIDEO EXTRACTOR{RESET} {DIM}v{version}{RESET}           {FG_CYAN}Multi-Agent Media CLI{RESET}  {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}├─────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}📁 Output:{RESET}  {FG_YELLOW}{download_dir:<46}{RESET} {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}⚡ Tiers:{RESET}   {engine_line:<66} {FG_CYAN}       │{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}⏱ Race:{RESET}    {timeout}s max  {DIM}•{RESET} {DIM}Grace:{RESET} {grace}s {DIM}•{RESET}{DIM}Format:{RESET}{fmt:<16} {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
    print()


def render_menu_options(options: list, selected_index: int):
    """Render menu items with cursor highlight."""
    for idx, (icon, title, desc) in enumerate(options):
        num = idx + 1
        if idx == selected_index:
            # Highlighted item
            prefix = f"{BOLD}{FG_CYAN} ▶ {RESET}"
            num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
            title_text = f"{BOLD}{FG_CYAN}{title:<26}{RESET}"
            desc_text = f"{FG_WHITE}{desc}{RESET}"
            print(f"{prefix} {num_badge}  {title_text}  {DIM}—{RESET} {desc_text}")
        else:
            prefix = "    "
            num_badge = f"{DIM}[{num}]{RESET}"
            title_text = f"{FG_WHITE}{title:<26}{RESET}"
            desc_text = f"{DIM}{desc}{RESET}"
            print(f"{prefix} {num_badge}  {title_text}  {DIM}—{RESET} {desc_text}")
    print()


def render_footer():
    """Render footer navigation hints."""
    print(f"{DIM}─────────────────────────────────────────────────────────────{RESET}")
    print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[Ctrl+V]{RESET} Paste Link  {DIM}•{RESET} {FG_YELLOW}[1-7]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[q]{RESET} Exit")


# ============================================================================
# WORKFLOW ACTION HANDLERS
# ============================================================================

def action_download(config: dict, initial_url: str = None):
    """Action 1: Download Video with interactive prompts."""
    clear_screen()
    show_cursor()

    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print(f"                   {BOLD}DOWNLOAD VIDEO{RESET}")
    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print()

    if initial_url:
        url = initial_url
        print(f"{FG_GREEN}[✓] Pasted Video URL detected:{RESET}")
        print(f"    {BOLD}{FG_WHITE}{url}{RESET}\n")
    else:
        print(f"{DIM}Enter the video or stream URL to download.{RESET}")
        print(f"{DIM}Type 0 or press Enter on empty input to cancel.{RESET}\n")

        try:
            url = input(f"{BOLD}{FG_CYAN}Enter Video URL:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not url or url == "0":
            print(f"\n{DIM}[+] Download cancelled.{RESET}")
            time.sleep(0.5)
            return

    if not valid_url(url):
        print(f"\n{FG_RED}[-] Invalid URL: {url}{RESET}")
        print(f"{DIM}    Expected http:// or https://{RESET}")
        pause_prompt()
        return

    # Quality selector
    qualities = [
        ("best", "Best Available (Default)", "Full resolution & best audio mux"),
        ("1080p", "1080p Full HD", "Up to 1920x1080 stream"),
        ("720p", "720p HD", "Up to 1280x720 (standard streaming)"),
        ("480p", "480p SD", "Up to 854x480 (bandwidth saver)"),
        ("audio", "Audio Only (mp3/m4a)", "Extract and download soundtrack"),
    ]

    print(f"\n{BOLD}Select Desired Quality:{RESET}")
    for i, (_, label, desc) in enumerate(qualities, 1):
        print(f"  {FG_CYAN}[{i}]{RESET} {BOLD}{label:<24}{RESET} {DIM}({desc}){RESET}")

    quality_input = input(f"\n{BOLD}Choice [1-{len(qualities)}, default 1]:{RESET} ").strip()
    requested_quality = None
    if quality_input in ("1", "2", "3", "4", "5"):
        idx = int(quality_input) - 1
        q_code = qualities[idx][0]
        if q_code != "best":
            requested_quality = q_code

    # Execute extraction race
    print(f"\n{BOLD}{FG_CYAN}[+] Starting concurrent extraction race...{RESET}")
    from .router import identify
    from .race_controller import ExtractionRaceController
    from .downloader import download

    route = identify(url)
    print(f"{DIM}  Platform : {route.platform}")
    print(f"  Type     : {route.media_type}{RESET}\n")

    controller = ExtractionRaceController(
        url=url,
        requested_quality=requested_quality,
        timeout=config.get("race_timeout", 20),
        confidence_threshold=config.get("confidence_threshold", 50),
        no_browser=not config.get("use_browser", True),
        no_ytdlp=not config.get("use_ytdlp", True),
        no_static=not config.get("use_static_scanner", True),
        no_scrapling=not config.get("use_scrapling", True),
        prefer_gui=config.get("spawn_terminals", False),
        browser_grace_seconds=config.get("browser_grace_seconds", 2.5),
    )

    race_result = controller.run_race()

    if race_result.candidate:
        winning_candidate = race_result.candidate
        print(f"\n{FG_GREEN}[✓] Extracted via {race_result.winner_engine}! Downloading...{RESET}")
        try:
            output = download(
                winning_candidate,
                filename=winning_candidate.metadata.get("title", "video"),
                requested_quality=requested_quality,
            )
            if output is None:
                pause_prompt()
                return

            write_history({
                "url": url,
                "platform": route.platform,
                "engine": race_result.winner_engine,
                "quality": requested_quality,
                "output": str(output) if output else None,
                "race_duration_ms": race_result.duration_ms,
            })

            print(f"\n{FG_GREEN}[✓] Download complete! Saved to:{RESET}")
            print(f"    {output}")

            # Handle auto open vs prompt based on config
            if config.get("auto_open", True):
                print(f"\n{FG_GREEN}[+] Auto-opening video in default media player...{RESET}")
                system_open(output)
            else:
                try:
                    play_choice = input(f"\n{BOLD}Open video now? [y/N]:{RESET} ").strip().lower()
                    if play_choice in ("y", "yes"):
                        system_open(output)
                except Exception:
                    pass

        except Exception as dl_error:
            print(f"\n{FG_RED}[-] Download failed: {dl_error}{RESET}")
    else:
        print(f"\n{FG_RED}[-] No downloadable media found across all extraction tiers.{RESET}")

    pause_prompt()


def get_video_files() -> list:
    """Return sorted list of video Path objects in download directory."""
    download_dir = get_download_dir()
    if not download_dir.exists():
        return []

    videos = [
        p for p in download_dir.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    ]
    videos.sort(key=lambda p: p.stat().st_mtime, reverse=True)
    return videos


def action_open(config: dict):
    """Action 2: Browse and Open / Play Downloaded Video."""
    videos = get_video_files()
    download_dir = get_download_dir()

    if not videos:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
        print(f"                    {BOLD}YOUR VIDEOS{RESET}")
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
        print(f"{FG_YELLOW}[!] No video files found in: {download_dir}{RESET}")
        pause_prompt()
        return

    selected_idx = 0
    hide_cursor()

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}▶  OPEN / PLAY VIDEO{RESET}             {DIM}Select file to play in player{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        print(f"{DIM} Directory: {download_dir} ({len(videos)} video(s)){RESET}\n")

        # Display up to 10 items with scrolling window
        max_visible = 10
        start_idx = max(0, min(selected_idx - max_visible // 2, len(videos) - max_visible))
        end_idx = min(start_idx + max_visible, len(videos))

        for idx in range(start_idx, end_idx):
            video = videos[idx]
            size_mb = video.stat().st_size / (1024 * 1024)
            name = video.name
            if len(name) > 42:
                name = name[:39] + "..."

            if idx == selected_idx:
                print(f" {BOLD}{FG_CYAN}▶{RESET} {BOLD}{BG_CYAN}{FG_BLACK} {idx+1:>2} {RESET} {BOLD}{FG_CYAN}{name:<44}{RESET} {FG_GREEN}[{size_mb:>6.1f} MB]{RESET}")
            else:
                print(f"   {DIM}[{idx+1:>2}]{RESET} {FG_WHITE}{name:<44}{RESET} {DIM}[{size_mb:>6.1f} MB]{RESET}")

        if len(videos) > max_visible:
            print(f"\n{DIM}  (Showing {start_idx+1}-{end_idx} of {len(videos)} files — scroll with ↑/↓){RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Play Video  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(videos)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(videos)
        elif key == "ENTER":
            chosen = videos[selected_idx]
            clear_screen()
            show_cursor()
            print(f"\n{FG_GREEN}[+] Opening in default media player:{RESET} {chosen.name}")
            system_open(chosen)
            time.sleep(1.0)
            break
        elif key in ("ESC", "q", "Q"):
            break


def action_clear_selected(config: dict):
    """Action 3: Interactive Multi-Select Checklist Video Cleaner."""
    videos = get_video_files()
    download_dir = get_download_dir()

    if not videos:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
        print(f"               {BOLD}CLEAR SELECTED VIDEOS{RESET}")
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
        print(f"{FG_YELLOW}[!] No video files found to delete.{RESET}")
        pause_prompt()
        return

    # Selection state dict: {index: bool}
    selected_flags = [False] * len(videos)
    cursor_idx = 0
    hide_cursor()

    while True:
        clear_screen()
        selected_count = sum(1 for s in selected_flags if s)
        selected_size_mb = sum(
            videos[i].stat().st_size / (1024 * 1024)
            for i, s in enumerate(selected_flags) if s
        )

        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🗑  CLEAR SELECTED VIDEOS{RESET}        {DIM}Space: Toggle  •  Enter: Delete{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        print(f" Selected: {FG_YELLOW}{selected_count}{RESET} / {len(videos)} files  {DIM}•{RESET}  To free: {FG_YELLOW}{selected_size_mb:.1f} MB{RESET}\n")

        # Scroll window
        max_visible = 10
        start_idx = max(0, min(cursor_idx - max_visible // 2, len(videos) - max_visible))
        end_idx = min(start_idx + max_visible, len(videos))

        for idx in range(start_idx, end_idx):
            video = videos[idx]
            size_mb = video.stat().st_size / (1024 * 1024)
            name = video.name
            if len(name) > 40:
                name = name[:37] + "..."

            check = f"{FG_GREEN}[✓]{RESET}" if selected_flags[idx] else f"{DIM}[ ]{RESET}"

            if idx == cursor_idx:
                print(f" {BOLD}{FG_CYAN}▶{RESET} {check} {BOLD}{FG_CYAN}{name:<42}{RESET} {FG_YELLOW}[{size_mb:>6.1f} MB]{RESET}")
            else:
                print(f"   {check} {FG_WHITE}{name:<42}{RESET} {DIM}[{size_mb:>6.1f} MB]{RESET}")

        if len(videos) > max_visible:
            print(f"\n{DIM}  (Showing {start_idx+1}-{end_idx} of {len(videos)} files){RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_YELLOW}[Space]{RESET} Toggle  {DIM}•{RESET} {FG_BLUE}[a]{RESET} Select All  {DIM}•{RESET} {FG_RED}[Enter]{RESET} Delete  {DIM}•{RESET} {DIM}[Esc/q]{RESET} Cancel")

        key = read_key()
        if key == "UP":
            cursor_idx = (cursor_idx - 1) % len(videos)
        elif key == "DOWN":
            cursor_idx = (cursor_idx + 1) % len(videos)
        elif key == "SPACE":
            selected_flags[cursor_idx] = not selected_flags[cursor_idx]
        elif key in ("a", "A"):
            all_selected = all(selected_flags)
            selected_flags = [not all_selected] * len(videos)
        elif key == "ENTER":
            if selected_count == 0:
                continue

            clear_screen()
            show_cursor()
            print(f"{BOLD}{FG_RED}============================================================={RESET}")
            print(f"                   {BOLD}CONFIRM DELETION{RESET}")
            print(f"{BOLD}{FG_RED}============================================================={RESET}\n")
            print(f" You are about to permanently delete {BOLD}{selected_count} video(s){RESET}.")
            print(f" This will free approximately {BOLD}{selected_size_mb:.1f} MB{RESET}.\n")

            confirm = input(f"{BOLD}Are you sure? [y/N]:{RESET} ").strip().lower()
            if confirm in ("y", "yes"):
                deleted = 0
                for i, flag in enumerate(selected_flags):
                    if flag:
                        v = videos[i]
                        try:
                            v.unlink()
                            print(f"{FG_GREEN}[✓] Deleted:{RESET} {v.name}")
                            deleted += 1
                        except Exception as e:
                            print(f"{FG_RED}[!] Could not delete {v.name}: {e}{RESET}")
                print(f"\n{FG_GREEN}[✓] Successfully deleted {deleted} video(s) ({selected_size_mb:.1f} MB freed).{RESET}")
                pause_prompt()
            else:
                print(f"\n{DIM}[+] Deletion cancelled.{RESET}")
                time.sleep(0.8)
            break
        elif key in ("ESC", "q", "Q"):
            break


def action_clear_all(config: dict):
    """Action 4: Clear All Videos with total size calculation."""
    clear_screen()
    show_cursor()

    videos = get_video_files()
    download_dir = get_download_dir()

    print(f"{BOLD}{FG_RED}============================================================={RESET}")
    print(f"                    {BOLD}CLEAR ALL VIDEOS{RESET}")
    print(f"{BOLD}{FG_RED}============================================================={RESET}\n")

    if not videos:
        print(f"{FG_YELLOW}[+] No video files found in: {download_dir}{RESET}")
        pause_prompt()
        return

    total_size = sum(p.stat().st_size for p in videos)
    size_mb = total_size / (1024 * 1024)

    print(f" Directory : {download_dir}")
    print(f" Found     : {BOLD}{len(videos)} video file(s){RESET}")
    print(f" Storage   : {BOLD}{size_mb:.1f} MB{RESET}\n")

    confirm = input(f"{BOLD}{FG_RED}Delete ALL {len(videos)} video(s)? This cannot be undone! [y/N]:{RESET} ").strip().lower()
    if confirm in ("y", "yes"):
        deleted = 0
        for video in videos:
            try:
                video.unlink()
                print(f"{FG_GREEN}[✓] Deleted:{RESET} {video.name}")
                deleted += 1
            except Exception as e:
                print(f"{FG_RED}[!] Could not delete {video.name}: {e}{RESET}")

        print(f"\n{FG_GREEN}[✓] Complete: Deleted {deleted} video(s). Freed ~{size_mb:.1f} MB.{RESET}")
    else:
        print(f"\n{DIM}[+] Cleanup cancelled.{RESET}")

    pause_prompt()


def action_change_directory(config: dict):
    """Action 5: Change Output Directory and persist to config."""
    clear_screen()
    show_cursor()

    current_dir = get_download_dir()

    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print(f"               {BOLD}CHANGE OUTPUT DIRECTORY{RESET}")
    print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
    print(f" Current Directory: {FG_YELLOW}{current_dir}{RESET}\n")
    print(f"{DIM}Enter new folder path (e.g. /sdcard/Download, ~/Videos, C:\\Downloads).{RESET}")
    print(f"{DIM}Press Enter without typing to keep current directory.{RESET}\n")

    try:
        new_path_str = input(f"{BOLD}{FG_CYAN}New Path:{RESET} ").strip()
    except (KeyboardInterrupt, EOFError):
        return

    if not new_path_str:
        print(f"\n{DIM}[+] Keeping current directory.{RESET}")
        time.sleep(0.5)
        return

    new_path = Path(os.path.expanduser(new_path_str)).resolve()
    try:
        new_path.mkdir(parents=True, exist_ok=True)
        config["download_directory"] = str(new_path)
        if save_config(config):
            print(f"\n{FG_GREEN}[✓] Output directory successfully updated to:{RESET}")
            print(f"    {new_path}")
        else:
            print(f"\n{FG_RED}[!] Failed to write new path to config.json.{RESET}")
    except Exception as err:
        print(f"\n{FG_RED}[!] Could not create or access directory: {err}{RESET}")

    pause_prompt()


def action_settings(config: dict):
    """Action 6: Interactive Settings & Engine Configuration Sub-Menu."""
    hide_cursor()
    selected_idx = 0

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}⚙   SETTINGS & ENGINES{RESET}    {DIM}Toggle tiers, format & timeouts{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        # Current values
        ytdlp_on = config.get("use_ytdlp", True)
        scrapling_on = config.get("use_scrapling", True)
        static_on = config.get("use_static_scanner", True)
        browser_on = config.get("use_browser", True)
        terminals_on = config.get("spawn_terminals", False)
        timeout = config.get("race_timeout", 20)
        grace = config.get("browser_grace_seconds", 2.5)
        merge_fmt = config.get("merge_format", "mp4")
        confidence = config.get("confidence_threshold", 50)

        auto_open = config.get("auto_open", True)

        def badge(val: bool) -> str:
            return f"{BG_CYAN}{FG_BLACK} ON {RESET}" if val else f"{BG_GRAY}{FG_WHITE} OFF {RESET}"

        def yes_no_badge(val: bool) -> str:
            return f"{BG_CYAN}{FG_BLACK} YES {RESET}" if val else f"{BG_GRAY}{FG_WHITE} NO {RESET}"

        items = [
            ("Auto-Open on Download", yes_no_badge(auto_open), "Automatically play video after download"),
            ("Container Merge Format", f"{FG_YELLOW}{merge_fmt.upper()}{RESET}  (mp4 / mkv)", "Toggle output format"),
            ("Race Timeout", f"{FG_YELLOW}{timeout}s{RESET}", "Multi-agent tier race max wait"),
            ("Browser Tier Grace Timer", f"{FG_YELLOW}{grace}s{RESET}", "Delay before starting heavy headless browser"),
            ("Confidence Threshold", f"{FG_YELLOW}{confidence}{RESET}", "Minimum candidate score required to win"),
            ("Separate Terminal Windows", badge(terminals_on), "Spawn physical terminal windows vs single-terminal"),
            ("Tier 1: yt-dlp Native Agent", badge(ytdlp_on), "Fast direct extractor & format selector"),
            ("Tier 2: Scrapling Adaptive Agent", badge(scrapling_on), "Intelligent HTTP & stealth DOM scanner"),
            ("Tier 3: Static HTML Scanner Agent", badge(static_on), "BeautifulSoup & regex stream matcher"),
            ("Tier 4: Headless Browser Agent", badge(browser_on), "Selenium Chromium network sniffer"),
            ("← Back to Main Menu", "", "Return to main dashboard"),
        ]

        for idx, (label, val_str, desc) in enumerate(items):
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {idx+1:>2} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{label:<34}{RESET} {val_str:<22} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{idx+1:>2}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{label:<34}{RESET} {val_str:<22} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter/Space]{RESET} Toggle / Edit  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(items)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(items)
        elif key in ("ENTER", "SPACE"):
            if selected_idx == 0:  # Auto-Open
                config["auto_open"] = not auto_open
                save_config(config)
            elif selected_idx == 1:  # Merge format
                config["merge_format"] = "mkv" if merge_fmt == "mp4" else "mp4"
                save_config(config)
            elif selected_idx == 2:  # Timeout
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}Set Race Timeout (seconds):{RESET}")
                try:
                    val = input(f"Current: {timeout}s > ").strip()
                    if val.isdigit() and int(val) > 0:
                        config["race_timeout"] = int(val)
                        save_config(config)
                except Exception:
                    pass
                hide_cursor()
            elif selected_idx == 3:  # Grace
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}Set Browser Grace Timer (seconds):{RESET}")
                try:
                    val = input(f"Current: {grace}s > ").strip()
                    f_val = float(val)
                    if f_val >= 0:
                        config["browser_grace_seconds"] = f_val
                        save_config(config)
                except Exception:
                    pass
                hide_cursor()
            elif selected_idx == 4:  # Confidence
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}Set Candidate Score Confidence Threshold (1-100):{RESET}")
                try:
                    val = input(f"Current: {confidence} > ").strip()
                    if val.isdigit() and 1 <= int(val) <= 100:
                        config["confidence_threshold"] = int(val)
                        save_config(config)
                except Exception:
                    pass
                hide_cursor()
            elif selected_idx == 5:  # Terminals
                config["spawn_terminals"] = not terminals_on
                save_config(config)
            elif selected_idx == 6:  # yt-dlp
                config["use_ytdlp"] = not ytdlp_on
                save_config(config)
            elif selected_idx == 7:  # Scrapling
                config["use_scrapling"] = not scrapling_on
                save_config(config)
            elif selected_idx == 8:  # Static
                config["use_static_scanner"] = not static_on
                save_config(config)
            elif selected_idx == 9:  # Browser
                config["use_browser"] = not browser_on
                save_config(config)
            elif selected_idx == 10:  # Back
                break

        elif key in ("ESC", "q", "Q"):
            break


# ============================================================================
# MAIN MENU LOOP
# ============================================================================

def run_interactive_menu() -> int:
    """
    Main interactive dashboard controller.
    Renders top banner, active state, and navigates seamlessly with arrows.
    """
    selected_index = 0

    options = [
        ("📥", "Download Video", "Extract and download stream from any URL"),
        ("▶", "Open / Play Video", "Browse and launch downloaded videos"),
        ("🗑", "Clear Selected Videos", "Interactive multi-select deletion checklist"),
        ("💥", "Clear All Videos", "Wipe all downloaded video files from folder"),
        ("📂", "Change Output Directory", "Update and save custom download location"),
        ("⚙", "Settings & Config", "Adjust race timers, merge formats, and tiers"),
        ("🚪", "Exit", "Close Video Extractor CLI"),
    ]

    hide_cursor()

    try:
        while True:
            config = load_config()
            clear_screen()
            render_banner(config)
            render_menu_options(options, selected_index)
            render_footer()

            key = read_key()

            if key == "UP":
                selected_index = (selected_index - 1) % len(options)
            elif key == "DOWN":
                selected_index = (selected_index + 1) % len(options)
            elif isinstance(key, str) and key.startswith("URL:"):
                pasted_url = key[4:].strip()
                action_download(config, initial_url=pasted_url)
            elif key == "CTRL_V":
                clip_text = get_clipboard_text()
                target_url = None
                if clip_text:
                    clip_text = clip_text.strip()
                    if clip_text.startswith(("http://", "https://")):
                        target_url = clip_text
                    else:
                        for part in clip_text.split():
                            if part.startswith(("http://", "https://")):
                                target_url = part
                                break

                if target_url:
                    action_download(config, initial_url=target_url)
                elif clip_text:
                    print(f"\n{FG_YELLOW}[!] Clipboard does not contain a valid http(s) URL.{RESET}")
                    time.sleep(1.2)
                else:
                    print(f"\n{FG_YELLOW}[!] Clipboard is empty or could not be accessed.{RESET}")
                    time.sleep(1.2)
            elif key == "IGNORE":
                pass
            elif key in ("1", "2", "3", "4", "5", "6", "7"):
                num = int(key) - 1
                selected_index = num
                # Execute immediately on number press
                if num == 0:
                    action_download(config)
                elif num == 1:
                    action_open(config)
                elif num == 2:
                    action_clear_selected(config)
                elif num == 3:
                    action_clear_all(config)
                elif num == 4:
                    action_change_directory(config)
                elif num == 5:
                    action_settings(config)
                elif num == 6:
                    break
            elif key == "ENTER":
                if selected_index == 0:
                    action_download(config)
                elif selected_index == 1:
                    action_open(config)
                elif selected_index == 2:
                    action_clear_selected(config)
                elif selected_index == 3:
                    action_clear_all(config)
                elif selected_index == 4:
                    action_change_directory(config)
                elif selected_index == 5:
                    action_settings(config)
                elif selected_index == 6:
                    break
            elif key in ("q", "Q", "ESC"):
                break

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()
        print(f"{FG_CYAN}Thank you for using Video Extractor!{RESET}\n")

    return 0
