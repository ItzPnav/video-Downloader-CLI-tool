"""
Interactive Terminal Menu & Navigation System for Tool-Kit CLI.
Provides arrow-key driven workflows, clean ANSI interface, interactive disk browser, and structured submenus.
"""

import os
import re
import sys
import shutil
import time
from pathlib import Path
from urllib.parse import urlparse

from .utils import (
    load_config,
    save_config,
    get_download_dir,
    get_tool_output_dir,
    set_tool_output_dir,
    get_tool_default_dir,
    auto_separate_all_tool_dirs,
    reset_all_tool_dirs_to_defaults,
    get_version,
    write_history,
    safe_filename,
    get_config_dir,
)
from .cli import system_open, valid_url, show_history


# ============================================================================
# ANSI STYLING & TERMINAL SETUP
# ============================================================================

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

# Common media file extensions
VIDEO_EXTENSIONS = {
    ".mp4", ".mkv", ".webm", ".m4v", ".mov", ".avi",
    ".3gp", ".3g2", ".flv", ".f4v", ".wmv", ".ogv",
    ".mpeg", ".mpg", ".ts", ".m2ts", ".mts"
}

IMAGE_EXTENSIONS = {
    ".png", ".jpg", ".jpeg", ".webp", ".bmp", ".tiff", ".gif"
}

AUDIO_EXTENSIONS = {
    ".mp3", ".wav", ".flac", ".aac", ".ogg", ".m4a", ".opus", ".wma"
}

DOCUMENT_EXTENSIONS = {
    ".txt", ".md", ".csv", ".json", ".log", ".py", ".html", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".bat", ".rst"
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
# CROSS-PLATFORM KEYBOARD ENGINE & CLIPBOARD
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
    Returns: 'UP', 'DOWN', 'LEFT', 'RIGHT', 'ENTER', 'SPACE', 'ESC', 'BACKSPACE',
             'CTRL_V', 'URL:<url>', 'IGNORE', or single char character.
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


def pause_prompt(message: str = "Press any key to return..."):
    """Show prompt and wait for user keypress (Esc/Enter/Any)."""
    print(f"\n{DIM}{message}{RESET}")
    try:
        read_key()
    except KeyboardInterrupt:
        pass


# ============================================================================
# INTERACTIVE DISK & FILE / FOLDER BROWSER
# ============================================================================

def browse_interactive_path(
    mode: str = "file",
    initial_dir: Path = None,
    title: str = "Browse Files & Folders",
    allowed_exts: set = None,
) -> Path | None:
    """
    Interactive disk browser allowing user to navigate folders with arrow keys and pick files/folders.
    mode: 'file' (pick file), 'folder' (pick directory), 'any' (pick either)
    Returns: Path object selected, or None if cancelled with Esc / q / 0.
    """
    current_dir = (initial_dir or get_download_dir()).resolve()
    if not current_dir.exists():
        current_dir = Path.cwd()

    cursor_idx = 0
    hide_cursor()

    while True:
        try:
            entries = []
            if mode == "folder":
                entries.append((f"[Select This Folder: {current_dir.name or str(current_dir)}]", current_dir, "SELECT_CURRENT"))
            # Option to go up
            if current_dir.parent != current_dir:
                entries.append(("..", current_dir.parent, True))

            sub_dirs = []
            sub_files = []

            try:
                for p in current_dir.iterdir():
                    try:
                        if p.is_dir() and not p.name.startswith("."):
                            sub_dirs.append((p.name, p, True))
                        elif p.is_file() and not p.name.startswith("."):
                            if allowed_exts is None or p.suffix.lower() in allowed_exts:
                                sub_files.append((p.name, p, False))
                    except Exception:
                        pass
            except PermissionError:
                pass

            sub_dirs.sort(key=lambda x: x[0].lower())
            sub_files.sort(key=lambda x: x[0].lower())
            entries.extend(sub_dirs)
            entries.extend(sub_files)

        except Exception:
            entries = []

        if cursor_idx >= len(entries):
            cursor_idx = max(0, len(entries) - 1)

        clear_screen()
        dir_disp = str(current_dir)
        if len(dir_disp) > 52:
            dir_disp = "..." + dir_disp[-49:]

        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}📂  {title:<32}{RESET}  {DIM}Mode: {mode.upper()}{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
        print(f" {DIM}Current:{RESET} {FG_YELLOW}{dir_disp}{RESET}\n")

        if not entries:
            print(f"  {DIM}(No items found in this directory){RESET}\n")
        else:
            max_visible = 10
            start_idx = max(0, min(cursor_idx - max_visible // 2, len(entries) - max_visible))
            end_idx = min(start_idx + max_visible, len(entries))

            for idx in range(start_idx, end_idx):
                name, path_obj, is_dir = entries[idx]
                if is_dir == "SELECT_CURRENT":
                    icon = f"{FG_GREEN}✅{RESET}"
                    label = name if len(name) <= 36 else name[:33] + "...]"
                    info_str = f"{FG_GREEN}[ENTER / SPACE]{RESET}"
                elif is_dir:
                    icon = f"{FG_YELLOW}📁{RESET}"
                    label = f"{BOLD}{name}/{RESET}"
                    info_str = f"{DIM}[DIR]{RESET}"
                    if len(name) > 36:
                        label = name[:33] + "..."
                else:
                    icon = f"{FG_CYAN}📄{RESET}"
                    label = f"{name}"
                    try:
                        sz_mb = path_obj.stat().st_size / (1024 * 1024)
                        info_str = f"{DIM}[{sz_mb:.1f} MB]{RESET}"
                    except Exception:
                        info_str = ""
                    if len(name) > 36:
                        label = name[:33] + "..."

                if idx == cursor_idx:
                    prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                    num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {idx+1:>2} {RESET}"
                    print(f"{prefix} {num_badge} {icon} {BOLD}{FG_CYAN}{label:<38}{RESET} {info_str}")
                else:
                    prefix = "   "
                    num_badge = f"{DIM}[{idx+1:>2}]{RESET}"
                    print(f"{prefix} {num_badge} {icon} {FG_WHITE}{label:<38}{RESET} {info_str}")

            if len(entries) > max_visible:
                print(f"\n{DIM}  (Showing {start_idx+1}-{end_idx} of {len(entries)} items — scroll with ↑/↓){RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        if mode == "folder":
            print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select/Open  {DIM}•{RESET} {FG_YELLOW}[Space]{RESET} Select Current Folder  {DIM}•{RESET} {FG_BLUE}[p]{RESET} Type Path  {DIM}•{RESET} {FG_RED}[Esc]{RESET} Cancel")
        else:
            print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select/Open  {DIM}•{RESET} {FG_BLUE}[p]{RESET} Type Path  {DIM}•{RESET} {FG_RED}[Esc]{RESET} Cancel")

        key = read_key()
        if key == "UP":
            if entries:
                cursor_idx = (cursor_idx - 1) % len(entries)
        elif key == "DOWN":
            if entries:
                cursor_idx = (cursor_idx + 1) % len(entries)
        elif key == "SPACE" and mode == "folder":
            return current_dir
        elif key == "ENTER":
            if not entries:
                continue
            name, path_obj, is_dir = entries[cursor_idx]
            if is_dir == "SELECT_CURRENT":
                return current_dir
            elif is_dir:
                current_dir = path_obj.resolve()
                cursor_idx = 0
            else:
                if mode in ("file", "any"):
                    return path_obj
                elif mode == "folder":
                    return current_dir
        elif key in ("p", "P", "/"):
            clear_screen()
            show_cursor()
            print(f"\n{BOLD}{FG_CYAN}Manual Path Input:{RESET}")
            print(f"{DIM}Enter full or relative path, or press Enter to cancel.{RESET}\n")
            try:
                manual = input("Path: ").strip().strip('"\'')
                if manual:
                    p = Path(os.path.expanduser(manual)).resolve()
                    if p.exists():
                        return p
                    else:
                        print(f"\n{FG_RED}[-] Path not found: {p}{RESET}")
                        time.sleep(1.2)
            except Exception:
                pass
            hide_cursor()
        elif key in ("ESC", "q", "Q", "0"):
            return None


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
    print(f"{FG_CYAN}│{RESET}  {BOLD}{FG_WHITE}🛠  TOOL-KIT CLI{RESET} {DIM}v{version}{RESET}          {FG_CYAN}Multi-Agent Utility Suite{RESET}  {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}├─────────────────────────────────────────────────────────────┤{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}📁 Output:{RESET}  {FG_YELLOW}{download_dir:<46}{RESET} {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}⚡ Tiers:{RESET}   {engine_line:<66} {FG_CYAN}       │{RESET}")
    print(f"{FG_CYAN}│{RESET}  {DIM}⏱ Race:{RESET}     {timeout}s max  {DIM}•{RESET} {DIM}Grace:{RESET} {grace}s{DIM}•{RESET}{DIM}Format:{RESET}{fmt:<16}{FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
    print()


def render_menu_options(options: list, selected_index: int):
    """Render menu items with cursor highlight."""
    for idx, (icon, title, desc) in enumerate(options):
        num = idx + 1 if idx < len(options) - 1 else 0
        if idx == selected_index:
            prefix = f"{BOLD}{FG_CYAN} ▶ {RESET}"
            num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
            title_text = f"{BOLD}{FG_CYAN}{icon} {title:<26}{RESET}"
            desc_text = f"{FG_WHITE}{desc}{RESET}"
            print(f"{prefix} {num_badge}  {title_text}  {DIM}—{RESET} {desc_text}")
        else:
            prefix = "    "
            num_badge = f"{DIM}[{num}]{RESET}"
            title_text = f"{FG_WHITE}{icon} {title:<26}{RESET}"
            desc_text = f"{DIM}{desc}{RESET}"
            print(f"{prefix} {num_badge}  {title_text}  {DIM}—{RESET} {desc_text}")
    print()


def render_footer():
    """Render footer navigation hints."""
    print(f"{DIM}─────────────────────────────────────────────────────────────{RESET}")
    print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[Ctrl+V]{RESET} Paste Link  {DIM}•{RESET} {FG_YELLOW}[1-4, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Exit")


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
        print(f"{DIM}Press Enter on empty input or type 0 / q / Esc to cancel.{RESET}\n")

        try:
            url = input(f"{BOLD}{FG_CYAN}Enter Video URL:{RESET} ").strip()
        except (KeyboardInterrupt, EOFError):
            return

        if not url or url.lower() in ("0", "q", "exit", "esc"):
            print(f"\n{DIM}[+] Download cancelled.{RESET}")
            time.sleep(0.4)
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
    print(f"  {DIM}[0] Cancel & return to menu{RESET}")

    quality_input = input(f"\n{BOLD}Choice [1-{len(qualities)}, default 1]:{RESET} ").strip()
    if quality_input.lower() in ("0", "q", "esc"):
        return

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
    target_dl_dir = get_tool_output_dir("video", config)
    print(f"{DIM}  Platform : {route.platform}")
    print(f"  Type     : {route.media_type}")
    print(f"  Folder   : {target_dl_dir}{RESET}\n")

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

            if config.get("auto_open", True):
                print(f"\n{FG_GREEN}[+] Auto-opening in media player...{RESET}")
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
    """Action 3: Browse and Open / Play Downloaded Video."""
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
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Play Video  {DIM}•{RESET} {FG_RED}[Esc/q/0]{RESET} Back")

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
        elif key in ("ESC", "q", "Q", "0"):
            break


# ============================================================================
# TOOL DIRECTORY & VIDEO TOOLS ACTIONS
# ============================================================================

def action_change_tool_directory(config: dict, tool_name: str, tool_label: str = "Video Downloads"):
    """Interactive output directory configuration for a specific tool."""
    current = get_tool_output_dir(tool_name, config)
    def_p = get_tool_default_dir(tool_name)
    options = [
        ("📂", "Browse Disk Explorer", "Select directory visually with arrow-key folder browser"),
        ("⌨", "Type Directory Path", "Enter a custom absolute or relative directory path"),
        ("🔄", f"Reset to Default ({def_p.name or 'Downloads'})", f"Restore to standard {tool_label} folder"),
        ("←", "Cancel & Return", "Keep current directory"),
    ]

    selected_idx = 0
    hide_cursor()

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}📁  CHANGE {tool_label.upper():<28}{RESET}  {DIM}Custom Storage Path{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")
        print(f" {DIM}Current Directory:{RESET} {FG_YELLOW}{current}{RESET}\n")

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<28}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<28}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_RED}[Esc/q/0]{RESET} Cancel")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2", "3"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q"):
            break

        if key == "ENTER":
            if selected_idx == 0:
                picked = browse_interactive_path(
                    mode="folder",
                    initial_dir=current,
                    title=f"Select {tool_label} Folder",
                )
                if picked and picked.is_dir():
                    set_tool_output_dir(tool_name, picked)
                    clear_screen()
                    show_cursor()
                    print(f"\n{FG_GREEN}[✓] {tool_label} directory updated to:{RESET}\n    {picked}")
                    time.sleep(1.2)
                    break
            elif selected_idx == 1:
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}Enter new output directory for {tool_label}:{RESET}")
                try:
                    manual = input("Path: ").strip().strip('"\'')
                    if manual:
                        p = Path(os.path.expanduser(manual)).resolve()
                        p.mkdir(parents=True, exist_ok=True)
                        set_tool_output_dir(tool_name, p)
                        print(f"\n{FG_GREEN}[✓] {tool_label} directory updated to:{RESET}\n    {p}")
                        time.sleep(1.2)
                        break
                except Exception as err:
                    print(f"\n{FG_RED}[!] Could not set directory: {err}{RESET}")
                    time.sleep(1.2)
                hide_cursor()
            elif selected_idx == 2:
                default_p = get_tool_default_dir(tool_name)
                set_tool_output_dir(tool_name, default_p)
                clear_screen()
                show_cursor()
                print(f"\n{FG_GREEN}[✓] {tool_label} directory reset to default:{RESET}\n    {default_p}")
                time.sleep(1.2)
                break
            elif selected_idx == 3:
                break


def action_file_conflict_settings(config: dict):
    """Sub-Action: Configure Replace or Skip Files (Conflict Resolution) behavior as radio settings."""
    hide_cursor()
    selected_idx = 0

    while True:
        cfg = load_config()
        current_policy = cfg.get("conflict_policy")  # None, "ask", "replace", "keep_both", "skip", "compare"
        if current_policy == "ask":
            current_policy = None

        # Radio options: [1] Replace, [2] Keep Both, [3] Skip, [4] Compare, [0] Ask Every Time (All False / Default)
        options = [
            ("replace", "Replace the file in the destination", "Always overwrite existing file"),
            ("keep_both", "Keep both files (Auto-number)", 'Save as "video (1).mp4", "(2).mp4"'),
            ("skip", "Skip this file", "Skip download if file already exists"),
            ("compare", "Compare info for both files", "Auto-open diff metadata comparison modal"),
            (None, "Ask Every Time (Default: All False)", "Show interactive Replace/Skip dialog on collision"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}⚡  REPLACE OR SKIP FILES{RESET}             {DIM}File Conflict Policy{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")
        print(f" {DIM}Choose automatic behavior when a downloaded file already exists:{RESET}\n")

        for idx, (policy_key, title, desc) in enumerate(options):
            num = idx + 1 if idx < 4 else 0
            is_active = (current_policy == policy_key)
            radio_mark = f"{FG_GREEN}(•){RESET}" if is_active else f"{DIM}( ){RESET}"
            state_badge = f"{BG_CYAN}{FG_BLACK} ON {RESET}" if is_active else f"{BG_GRAY}{FG_WHITE} OFF {RESET}"

            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {radio_mark} {num_badge} {BOLD}{FG_CYAN}{title:<38}{RESET} {state_badge} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {radio_mark} {num_badge} {FG_WHITE}{title:<38}{RESET} {state_badge} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter/Space]{RESET} Toggle Radio  {DIM}•{RESET} {FG_YELLOW}[1-4, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2", "3", "4"):
            idx = int(key) - 1
            selected_idx = idx
            target_key = options[idx][0]
            if current_policy == target_key:
                cfg["conflict_policy"] = None
            else:
                cfg["conflict_policy"] = target_key
            save_config(cfg)
        elif key == "0":
            selected_idx = 4
            cfg["conflict_policy"] = None
            save_config(cfg)
        elif key in ("ENTER", "SPACE"):
            target_key = options[selected_idx][0]
            if current_policy == target_key:
                cfg["conflict_policy"] = None
            else:
                cfg["conflict_policy"] = target_key
            save_config(cfg)
        elif key in ("ESC", "q", "Q"):
            break


def action_video_tools(config: dict):
    """Sub-Action: Video Suite (Download, Play, Combine, Set Directory, Conflict Policy, Clean)."""
    selected_idx = 0
    status_banner: str | None = None
    hide_cursor()

    while True:
        cfg = load_config()
        vid_dir = str(get_tool_output_dir("video", cfg))
        if len(vid_dir) > 36:
            vid_dir_disp = "..." + vid_dir[-33:]
        else:
            vid_dir_disp = vid_dir

        conflict_pol = cfg.get("conflict_policy")
        conflict_label_map = {
            "replace": "Always Replace",
            "keep_both": "Always Keep Both",
            "skip": "Always Skip",
            "compare": "Always Compare",
        }
        conflict_disp = conflict_label_map.get(conflict_pol, "Ask Every Time")

        options = [
            ("📥", "Download Video / Stream", "Extract and download stream from any URL"),
            ("▶", "Open / Play Videos", "Browse and launch downloaded videos in player"),
            ("🎞", "Combine / Merge Videos", "Concatenate multiple video clips into one file"),
            ("📁", "Change Video Directory", f"Current: {vid_dir_disp}"),
            ("⚡", "Replace or Skip Files", f"Policy: {conflict_disp}"),
            ("🗑", "Clear / Manage Videos", "Delete selected or all downloaded videos"),
            ("←", "Back to Main Menu", "Return to main dashboard"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🎬  VIDEO TOOLS & UTILITIES{RESET}       {DIM}Download, combine, play & clean{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
        if status_banner:
            print(f"\n  {status_banner}\n")
        else:
            print()

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<28}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<28}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-6, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2", "3", "4", "5", "6"):
            status_banner = None
            num = int(key) - 1
            selected_idx = num
            if num == 0:
                action_download(cfg)
            elif num == 1:
                action_open(cfg)
            elif num == 2:
                try:
                    res = action_combine_videos(cfg)
                    if res:
                        m = re.search(r"_(\d+)clips(?:_\d+)?(?:\.[^.]+)?$", res.name)
                        count_str = f"{m.group(1)} " if m else ""
                        status_banner = f"{FG_GREEN}[✓] Combined {count_str}videos into: {res.name}{RESET}"
                except Exception as err:
                    status_banner = f"{FG_RED}[-] Video combine failed: {err}{RESET}"
            elif num == 3:
                action_change_tool_directory(cfg, "video", "Video Downloads")
            elif num == 4:
                action_file_conflict_settings(cfg)
            elif num == 5:
                action_clear_selected(cfg)
        elif key == "0" or (key == "ENTER" and selected_idx == 6):
            break
        elif key == "ENTER":
            status_banner = None
            if selected_idx == 0:
                action_download(cfg)
            elif selected_idx == 1:
                action_open(cfg)
            elif selected_idx == 2:
                try:
                    res = action_combine_videos(cfg)
                    if res:
                        m = re.search(r"_(\d+)clips(?:_\d+)?(?:\.[^.]+)?$", res.name)
                        count_str = f"{m.group(1)} " if m else ""
                        status_banner = f"{FG_GREEN}[✓] Combined {count_str}videos into: {res.name}{RESET}"
                except Exception as err:
                    status_banner = f"{FG_RED}[-] Video combine failed: {err}{RESET}"
            elif selected_idx == 3:
                action_change_tool_directory(cfg, "video", "Video Downloads")
            elif selected_idx == 4:
                action_file_conflict_settings(cfg)
            elif selected_idx == 5:
                action_clear_selected(cfg)
            elif selected_idx == 6:
                break
        elif key in ("ESC", "q", "Q"):
            break


def action_other_tools(config: dict):
    """Action 2: Other Tools Consolidated Sub-Menu."""
    options = [
        ("🎬", "Video Tools", "Download video, play, combine, change directory, clean"),
        ("🔄", "Media & Format Converter", "Convert Video to GIF, Audio, Text to PDF, Images"),
        ("📚", "Comic & Manga Scraper", "Scrape & download comic chapters & image galleries"),
        ("📦", "Images to PDF / CBZ Packager", "Bundle image directories into multi-page PDF or CBZ"),
        ("🔍", "OCR (Image to Text)", "Extract readable text from images using Tesseract OCR"),
        ("←", "Back to Main Menu", "Return to main dashboard"),
    ]

    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🧰  OTHER TOOLS & UTILITIES{RESET}       {DIM}Media converters & extractors{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<30}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<30}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-5, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2", "3", "4", "5"):
            num = int(key) - 1
            selected_idx = num
            if num == 0:
                action_video_tools(cfg)
            elif num == 1:
                action_convert(cfg)
            elif num == 2:
                action_comic_scraper(cfg)
            elif num == 3:
                action_pack_images(cfg)
            elif num == 4:
                action_ocr(cfg)
        elif key == "0" or (key == "ENTER" and selected_idx == 5):
            break
        elif key == "ENTER":
            if selected_idx == 0:
                action_video_tools(cfg)
            elif selected_idx == 1:
                action_convert(cfg)
            elif selected_idx == 2:
                action_comic_scraper(cfg)
            elif selected_idx == 3:
                action_pack_images(cfg)
            elif selected_idx == 4:
                action_ocr(cfg)
            elif selected_idx == 5:
                break
        elif key in ("ESC", "q", "Q"):
            break


def prompt_single_or_folder_mode(
    header_title: str,
    single_title: str,
    single_desc: str,
    folder_title: str,
    folder_desc: str,
) -> str | None:
    """
    Prompt user with an arrow-key & number-key submenu to choose between
    converting a single file ('file') or an entire folder ('folder').
    Returns 'file', 'folder', or None if cancelled.
    """
    options = [
        ("📄", single_title, single_desc),
        ("📂", folder_title, folder_desc),
        ("←", "Back to Media Converter", "Cancel and return to converter menu"),
    ]
    selected_idx = 0
    hide_cursor()

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}{header_title:<36}{RESET}  {DIM}Single or Batch Mode{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")
        print(f" {DIM}Choose whether to convert a single file or an entire folder:{RESET}\n")

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<30}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<30}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-2, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 2):
            return None

        if key == "ENTER":
            if selected_idx == 0:
                return "file"
            elif selected_idx == 1:
                return "folder"


def prompt_merge_order_mode(
    header_title: str = "MERGE SEQUENCE ORDER",
    item_type: str = "items",
) -> str | None:
    """
    Prompt user with an arrow-key & number-key submenu to choose between
    merging items in ascending sorted order ('ascending') or random order ('random').
    Returns 'ascending', 'random', or None if cancelled.
    """
    options = [
        ("🔤", "File Sorted Ascending", f"Sort {item_type} in natural numerical / alphabetical order (A-Z, 0-9)"),
        ("🎲", "Random Shuffle", f"Randomize and shuffle the order of {item_type}"),
        ("←", "Cancel / Back", "Return to previous menu"),
    ]
    selected_idx = 0
    hide_cursor()

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}{header_title:<36}{RESET}  {DIM}Select Sequence Mode{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")
        print(f" {DIM}Choose how to order the {item_type} before merging:{RESET}\n")

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon}  {title:<26}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon}  {title:<26}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-2, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 2):
            return None

        if key == "ENTER":
            if selected_idx == 0:
                return "ascending"
            elif selected_idx == 1:
                return "random"


def action_convert(config: dict):
    """Sub-Action: Interactive Media Converter."""
    from .converter import (
        convert_video_to_gif,
        batch_convert_videos_to_gif,
        convert_video_to_audio,
        convert_audio_to_audio,
        convert_gif_to_mp4,
        batch_convert_gifs_to_mp4,
        convert_image,
        convert_text_to_pdf,
        remux_or_transcode_video,
    )

    selected_idx = 0
    status_banner: str | None = None
    hide_cursor()

    while True:
        cfg = load_config()
        c_dir = str(get_tool_output_dir("converter", cfg))
        c_disp = "..." + c_dir[-33:] if len(c_dir) > 36 else c_dir

        conv_options = [
            ("🎞", "Video → Animated GIF (High Quality 2-Pass)", "Single video or batch folder to smooth GIF"),
            ("🎵", "Video → MP3 Audio (320 kbps)", "Extract high-bitrate MP3 soundtrack"),
            ("🔊", "Audio ↔ Audio Transcoder (WAV/FLAC/AAC/OGG)", "Convert audio formats with FFmpeg"),
            ("📄", "Text Document → PDF (.txt / .md / .csv)", "Render text files into formatted PDF"),
            ("🎬", "Animated GIF → MP4 Video", "Single GIF or batch folder into lightweight MP4"),
            ("🖼", "Image Format Converter (PNG / JPG / WEBP)", "Convert single image or batch"),
            ("🔄", "Video Remux / Transcode (Container Switch)", "Fast copy or re-encode video container"),
            ("🔀", "Combine / Merge Video Clips", "Concatenate multiple video files in sequence"),
            ("📁", "Change Converter Directory", f"Current: {c_disp}"),
            ("←", "Back to Other Tools", "Return to utilities menu"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🔄  MEDIA CONVERTER{RESET}        {DIM}FFmpeg & Pillow zero-bloat engine{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
        if status_banner:
            print(f"\n  {status_banner}\n")
        else:
            print()

        for idx, (icon, label, desc) in enumerate(conv_options):
            num = idx + 1 if idx < len(conv_options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num:>2} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon}  {label:<46}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num:>2}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon}  {label:<46}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-9, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(conv_options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(conv_options)
        elif key in ("1", "2", "3", "4", "5", "6", "7", "8", "9"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 9):
            break

        if key == "ENTER" and selected_idx == 7:  # Combine / Merge Video Clips
            status_banner = None
            try:
                res = action_combine_videos(cfg)
                if res:
                    m = re.search(r"_(\d+)clips(?:_\d+)?(?:\.[^.]+)?$", res.name)
                    count_str = f"{m.group(1)} " if m else ""
                    status_banner = f"{FG_GREEN}[✓] Combined {count_str}videos into: {res.name}{RESET}"
            except Exception as err:
                status_banner = f"{FG_RED}[-] Video combine failed: {err}{RESET}"
            continue
        elif key == "ENTER" and selected_idx == 8:  # Change directory
            status_banner = None
            action_change_tool_directory(cfg, "converter", "Media Converter")
            continue

        if key == "ENTER" and selected_idx < 7:
            status_banner = None
            choice_num = selected_idx
            out_dir = get_tool_output_dir("converter", cfg)

            def _progress(pct: int, msg: str):
                bar = f"{FG_CYAN}{'━' * (pct // 4)}{RESET}{DIM}{'━' * (25 - (pct // 4))}{RESET}"
                sys.stdout.write(f"\r  [{bar}] {pct:>3}% — {msg:<42}")
                sys.stdout.flush()

            # Special Single File vs Batch Folder workflow for [1] Video -> GIF and [5] GIF -> MP4
            if choice_num == 0:  # [1] Video -> Animated GIF (High Quality 2-Pass)
                target_mode = prompt_single_or_folder_mode(
                    header_title="🎞  VIDEO → ANIMATED GIF",
                    single_title="Single Video File",
                    single_desc="Pick a single video file to convert to GIF",
                    folder_title="Folder of Videos (Batch)",
                    folder_desc="Convert all video files in a folder to GIFs",
                )
                if not target_mode:
                    continue

                if target_mode == "file":
                    input_path = browse_interactive_path(
                        mode="file",
                        title="Pick Video File for GIF",
                        allowed_exts=VIDEO_EXTENSIONS,
                    )
                    if not input_path or not input_path.is_file():
                        continue

                    clear_screen()
                    show_cursor()
                    print(f"\n{BOLD}{FG_CYAN}=== {conv_options[choice_num][0]}  {conv_options[choice_num][1]} ==={RESET}")
                    print(f"{DIM}Selected Video:{RESET} {FG_GREEN}{input_path}{RESET}\n")

                    try:
                        fps = 30
                        height = 504
                        colors = 256
                        out_gif = out_dir / f"{input_path.stem}.gif"
                        print(f"[+] Converting to GIF (30 FPS, 504p, 256 colors): {out_gif.name}...")
                        convert_video_to_gif(input_path, out_gif, fps=fps, height=height, colors=colors, progress_callback=_progress)
                        status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_gif.name}{RESET}"
                    except Exception as e:
                        status_banner = f"{FG_RED}[-] Conversion failed: {e}{RESET}"

                    hide_cursor()
                    continue

                else:  # target_mode == "folder"
                    folder_path = browse_interactive_path(
                        mode="folder",
                        title="Pick Folder with Videos for GIF",
                        allowed_exts=VIDEO_EXTENSIONS,
                    )
                    if not folder_path or not folder_path.is_dir():
                        continue

                    videos = sorted(
                        p for p in folder_path.iterdir()
                        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
                    )
                    clear_screen()
                    show_cursor()
                    print(f"\n{BOLD}{FG_CYAN}=== Batch Video → Animated GIF ==={RESET}")
                    print(f"{DIM}Selected Folder:{RESET} {FG_YELLOW}{folder_path}{RESET}\n")

                    if not videos:
                        status_banner = f"{FG_YELLOW}[!] No video files found in: {folder_path.name}{RESET}"
                        hide_cursor()
                        continue

                    print(f"[+] Found {BOLD}{len(videos)}{RESET} video file(s) in folder:")
                    for i, v in enumerate(videos[:10], 1):
                        print(f"    {i:>2}. {v.name}")
                    if len(videos) > 10:
                        print(f"    ... and {len(videos) - 10} more")
                    print()

                    try:
                        fps = 30
                        height = 504
                        colors = 256
                        print(f"[+] Batch converting {len(videos)} video(s) to GIF (30 FPS, 504p, 256 colors)...")
                        created = batch_convert_videos_to_gif(
                            folder_path=folder_path,
                            output_dir=out_dir,
                            fps=fps,
                            height=height,
                            colors=colors,
                            progress_callback=_progress,
                        )
                        status_banner = f"{FG_GREEN}[✓] Converted / Saved: {len(created)} GIF(s) in {out_dir.name}{RESET}"
                    except Exception as e:
                        status_banner = f"{FG_RED}[-] Batch conversion failed: {e}{RESET}"

                    hide_cursor()
                    continue

            elif choice_num == 4:  # [5] Animated GIF -> MP4 Video
                target_mode = prompt_single_or_folder_mode(
                    header_title="🎬  ANIMATED GIF → MP4 VIDEO",
                    single_title="Single GIF File",
                    single_desc="Pick a single .gif file to convert to MP4",
                    folder_title="Folder of GIFs (Batch)",
                    folder_desc="Convert all .gif files in a folder to MP4",
                )
                if not target_mode:
                    continue

                if target_mode == "file":
                    input_path = browse_interactive_path(
                        mode="file",
                        title="Pick GIF File for MP4",
                        allowed_exts={".gif"},
                    )
                    if not input_path or not input_path.is_file():
                        continue

                    clear_screen()
                    show_cursor()
                    print(f"\n{BOLD}{FG_CYAN}=== {conv_options[choice_num][0]}  {conv_options[choice_num][1]} ==={RESET}")
                    print(f"{DIM}Selected GIF:{RESET} {FG_GREEN}{input_path}{RESET}\n")

                    try:
                        out_mp4 = out_dir / f"{input_path.stem}.mp4"
                        print(f"[+] Converting GIF to MP4: {out_mp4.name}...")
                        convert_gif_to_mp4(input_path, out_mp4, progress_callback=_progress)
                        status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_mp4.name}{RESET}"
                    except Exception as e:
                        status_banner = f"{FG_RED}[-] Conversion failed: {e}{RESET}"

                    hide_cursor()
                    continue

                else:  # target_mode == "folder"
                    folder_path = browse_interactive_path(
                        mode="folder",
                        title="Pick Folder with GIFs for MP4",
                        allowed_exts={".gif"},
                    )
                    if not folder_path or not folder_path.is_dir():
                        continue

                    gifs = sorted(
                        p for p in folder_path.iterdir()
                        if p.is_file() and p.suffix.lower() == ".gif"
                    )
                    clear_screen()
                    show_cursor()
                    print(f"\n{BOLD}{FG_CYAN}=== Batch Animated GIF → MP4 Video ==={RESET}")
                    print(f"{DIM}Selected Folder:{RESET} {FG_YELLOW}{folder_path}{RESET}\n")

                    if not gifs:
                        status_banner = f"{FG_YELLOW}[!] No .gif files found in: {folder_path.name}{RESET}"
                        hide_cursor()
                        continue

                    print(f"[+] Found {BOLD}{len(gifs)}{RESET} GIF file(s) in folder:")
                    for i, g in enumerate(gifs[:10], 1):
                        print(f"    {i:>2}. {g.name}")
                    if len(gifs) > 10:
                        print(f"    ... and {len(gifs) - 10} more")
                    print()

                    try:
                        print(f"[+] Batch converting {len(gifs)} GIF(s) to MP4...")
                        created = batch_convert_gifs_to_mp4(
                            folder_path=folder_path,
                            output_dir=out_dir,
                            progress_callback=_progress,
                        )
                        status_banner = f"{FG_GREEN}[✓] Converted / Saved: {len(created)} MP4(s) in {out_dir.name}{RESET}"
                    except Exception as e:
                        status_banner = f"{FG_RED}[-] Batch conversion failed: {e}{RESET}"

                    hide_cursor()
                    continue

            # Filter allowed extensions based on remaining single-file operations
            ext_filter = None
            if choice_num in (1, 6):
                ext_filter = VIDEO_EXTENSIONS
            elif choice_num == 2:
                ext_filter = AUDIO_EXTENSIONS
            elif choice_num == 3:
                ext_filter = DOCUMENT_EXTENSIONS
            elif choice_num == 5:
                ext_filter = IMAGE_EXTENSIONS

            input_path = browse_interactive_path(
                mode="file",
                title=f"Pick File for: {conv_options[choice_num][1][:28]}",
                allowed_exts=ext_filter,
            )

            if not input_path or not input_path.is_file():
                continue

            clear_screen()
            show_cursor()
            print(f"\n{BOLD}{FG_CYAN}=== {conv_options[choice_num][0]}  {conv_options[choice_num][1]} ==={RESET}")
            print(f"{DIM}Selected Input:{RESET} {FG_GREEN}{input_path}{RESET}\n")

            try:
                if choice_num == 1:  # Video -> MP3
                    out_mp3 = out_dir / f"{input_path.stem}.mp3"
                    print(f"[+] Extracting MP3 audio (320 kbps)...")
                    convert_video_to_audio(input_path, out_mp3, audio_format="mp3", bitrate="320k", progress_callback=_progress)
                    status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_mp3.name}{RESET}"

                elif choice_num == 2:  # Audio ↔ Audio
                    fmt = "aac" if input_path.suffix.lower() == ".mp3" else "mp3"
                    out_aud = out_dir / f"{input_path.stem}.{fmt}"
                    print(f"[+] Converting audio to {fmt.upper()} (320 kbps)...")
                    convert_audio_to_audio(input_path, out_aud, audio_format=fmt, bitrate="320k", progress_callback=_progress)
                    status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_aud.name}{RESET}"

                elif choice_num == 3:  # Text -> PDF
                    out_pdf = out_dir / f"{input_path.stem}.pdf"
                    print(f"[+] Rendering Text Document to PDF...")
                    convert_text_to_pdf(input_path, out_pdf, progress_callback=_progress)
                    status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_pdf.name}{RESET}"

                elif choice_num == 5:  # Image Format
                    fmt = "png" if input_path.suffix.lower() in (".jpg", ".jpeg", ".webp") else "jpg"
                    out_img = out_dir / f"{input_path.stem}.{fmt}"
                    print(f"[+] Converting image to {fmt.upper()}...")
                    convert_image(input_path, out_img, progress_callback=_progress)
                    status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_img.name}{RESET}"

                elif choice_num == 6:  # Remux / Transcode
                    reencode = False
                    out_vid = out_dir / f"{input_path.stem}_remux.mp4"
                    print(f"[+] Processing video (fast remux)...")
                    remux_or_transcode_video(input_path, out_vid, reencode=reencode, progress_callback=_progress)
                    status_banner = f"{FG_GREEN}[✓] Converted / Saved: {out_vid.name}{RESET}"

            except Exception as e:
                status_banner = f"{FG_RED}[-] Conversion failed: {e}{RESET}"

            hide_cursor()
            continue

        elif key in ("ESC", "q", "Q"):
            break


def action_combine_videos(config: dict):
    """Sub-Action: Interactive Multi-Video Concatenation & Merger."""
    from .converter import combine_videos

    selected_videos: list[Path] = []
    selected_idx = 0
    status_banner: str | None = None
    hide_cursor()

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🎞  COMBINE & MERGE VIDEOS{RESET}        {DIM}Fast zero-loss stream merger{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
        if status_banner:
            print(f"\n  {status_banner}\n")
        else:
            print()

        if selected_videos:
            print(f"{BOLD}Queued Video Clips ({len(selected_videos)} in sequence):{RESET}")
            total_sz = 0
            for vp in selected_videos:
                try:
                    total_sz += vp.stat().st_size / (1024 * 1024)
                except Exception:
                    pass

            max_disp = 8
            for idx, vp in enumerate(selected_videos[:max_disp], 1):
                try:
                    sz_mb = vp.stat().st_size / (1024 * 1024)
                    sz_str = f"[{sz_mb:.1f} MB]"
                except Exception:
                    sz_str = ""
                name_disp = vp.name if len(vp.name) <= 38 else vp.name[:35] + "..."
                print(f"  {FG_CYAN}{idx:>2}.{RESET} {BOLD}{name_disp:<40}{RESET} {DIM}{sz_str}{RESET}")
            if len(selected_videos) > max_disp:
                print(f"  {DIM}  ... and {len(selected_videos) - max_disp} more clip(s){RESET}")
            print(f"  {DIM}Total estimated size: ~{total_sz:.1f} MB{RESET}\n")
        else:
            print(f"  {DIM}(No videos added yet. Add at least 2 videos to combine){RESET}\n")

        opts = [
            ("➕", "Add Video from Disk Explorer", "Browse and pick a video clip to add to sequence"),
            ("📂", "Add All Videos from a Folder", "Bulk add all video files inside a chosen directory"),
            ("❌", "Remove Last Added Video", "Remove the most recently added clip from the queue"),
            ("🧹", "Clear Video Queue", "Reset and clear all selected videos"),
            ("▶", "Start Combining Videos", f"Merge {len(selected_videos)} video(s) into one output file" if len(selected_videos) >= 2 else "Requires at least 2 videos"),
            ("←", "Back to Menu", "Return to previous menu"),
        ]

        for idx, (ico, name, desc) in enumerate(opts):
            num = idx + 1 if idx < len(opts) - 1 else 0
            title = f"{ico} {name}"
            is_start_combine = (idx == 4)
            disabled = is_start_combine and len(selected_videos) < 2
            desc_text = "Requires at least 2 videos" if disabled else desc

            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                if disabled:
                    print(f"{prefix} {num_badge} {DIM}{title:<34} — {desc_text}{RESET}")
                else:
                    print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{title:<34}{RESET} {DIM}— {desc_text}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                if disabled:
                    print(f"{prefix} {num_badge} {DIM}{title:<34} — {desc_text}{RESET}")
                else:
                    print(f"{prefix} {num_badge} {FG_WHITE}{title:<34}{RESET} {DIM}— {desc_text}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-5, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(opts)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(opts)
        elif key in ("1", "2", "3", "4", "5"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 5):
            return None

        if key == "ENTER":
            status_banner = None
            if selected_idx == 0:
                picked = browse_interactive_path(
                    mode="file",
                    title=f"Pick Video #{len(selected_videos) + 1} to Combine",
                    allowed_exts=VIDEO_EXTENSIONS,
                )
                if picked and picked.is_file():
                    selected_videos.append(picked)
                    status_banner = f"{FG_GREEN}[✓] Added: {picked.name}{RESET}"
            elif selected_idx == 1:
                folder = browse_interactive_path(
                    mode="folder",
                    title="Select Folder to Bulk-Add All Videos",
                )
                if folder and folder.is_dir():
                    try:
                        found_vids = [
                            p for p in sorted(folder.iterdir())
                            if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
                        ]
                        if found_vids:
                            selected_videos.extend(found_vids)
                            status_banner = f"{FG_GREEN}[✓] Added {len(found_vids)} videos from {folder.name}{RESET}"
                        else:
                            status_banner = f"{FG_YELLOW}[!] No video files found in {folder.name}{RESET}"
                    except Exception as err:
                        status_banner = f"{FG_RED}[-] Could not read folder: {err}{RESET}"
            elif selected_idx == 2:
                if selected_videos:
                    removed = selected_videos.pop()
                    status_banner = f"{DIM}[-] Removed: {removed.name}{RESET}"
                else:
                    status_banner = f"{DIM}[!] Queue is already empty.{RESET}"
            elif selected_idx == 3:
                selected_videos.clear()
                status_banner = f"{DIM}[+] Queue cleared.{RESET}"
            elif selected_idx == 4:
                if len(selected_videos) < 2:
                    status_banner = f"{FG_YELLOW}[!] Please add at least 2 videos to combine.{RESET}"
                    continue

                order_choice = prompt_merge_order_mode(
                    header_title="🎞  COMBINE & MERGE VIDEOS",
                    item_type="videos",
                )
                if not order_choice:
                    continue

                if order_choice == "ascending":
                    def _nat_key(p: Path):
                        return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", p.name)]
                    selected_videos = sorted(selected_videos, key=_nat_key)
                elif order_choice == "random":
                    import random
                    random.shuffle(selected_videos)

                clear_screen()
                show_cursor()
                print(f"\n{BOLD}{FG_CYAN}=== Combine {len(selected_videos)} Videos ({order_choice.title()} Order) ==={RESET}\n")
                print(f"[+] Ordered sequence to merge:")
                for i, v in enumerate(selected_videos, 1):
                    print(f"    {i:>2}. {v.name}")
                print()

                conv_dir = get_tool_output_dir("converter", config)
                stem_clean = safe_filename(selected_videos[0].stem) or "clip"
                default_name = f"combined_{stem_clean}_{len(selected_videos)}clips.mp4"
                out_path = conv_dir / default_name
                resolved_inputs = {p.resolve() for p in selected_videos}
                counter = 1
                while out_path.resolve() in resolved_inputs:
                    default_name = f"combined_{stem_clean}_{len(selected_videos)}clips_{counter}.mp4"
                    out_path = conv_dir / default_name
                    counter += 1

                def _progress(pct: int, msg: str):
                    bar = f"{FG_CYAN}{'━' * (pct // 4)}{RESET}{DIM}{'━' * (25 - (pct // 4))}{RESET}"
                    sys.stdout.write(f"\r  [{bar}] {pct:>3}% — {msg}")
                    sys.stdout.flush()

                try:
                    print(f"[+] Starting video combine...")
                    result = combine_videos(
                        video_paths=selected_videos,
                        output_path=out_path,
                        reencode=False,
                        progress_callback=_progress,
                        order=order_choice,
                    )
                    print(f"\n\n{FG_GREEN}[✓] Videos merged successfully!{RESET}")
                    print(f"    Saved to: {result}")

                    if config.get("auto_open", True):
                        system_open(result)

                    hide_cursor()
                    return result
                except Exception as err:
                    print(f"\n\n{FG_RED}[-] Video combine failed: {err}{RESET}")
                    hide_cursor()
                    raise


def action_comic_scraper(config: dict):
    """Sub-Action: Comic & Image Gallery Scraper."""
    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        cm_dir = str(get_tool_output_dir("comic", cfg))
        cm_disp = "..." + cm_dir[-33:] if len(cm_dir) > 36 else cm_dir

        source_options = [
            ("📂", "Browse Disk Explorer", "Select local HTML file, saved gallery, or image folder"),
            ("🌐", "Enter Comic / Manga Web URL", "Scrape online chapter, manga, or web gallery from URL"),
            ("📁", "Change Comic Output Directory", f"Current: {cm_disp}"),
            ("←", "Back to Other Tools", "Return to utilities menu"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}📚  COMIC & MANGA SCRAPER{RESET}        {DIM}Web galleries & chapter scraper{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (icon, title, desc) in enumerate(source_options):
            num = idx + 1 if idx < len(source_options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<32}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<32}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[Ctrl+V]{RESET} Paste URL  {DIM}•{RESET} {FG_RED}[Esc/q/0]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(source_options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(source_options)
        elif isinstance(key, str) and key.startswith("URL:"):
            source = key[4:].strip()
            _run_comic_scrape_flow(cfg, source)
            break
        elif key == "CTRL_V":
            clip_text = get_clipboard_text()
            if clip_text:
                source = clip_text.strip()
                _run_comic_scrape_flow(cfg, source)
                break
            else:
                print(f"\n{FG_YELLOW}[!] Clipboard is empty or could not be accessed.{RESET}")
                time.sleep(1.0)
        elif key in ("1", "2", "3"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key == "0" or (key == "ENTER" and selected_idx == 3):
            break

        if key == "ENTER":
            if selected_idx == 0:  # Browse Disk Explorer
                picked = browse_interactive_path(
                    mode="any",
                    title="Select Comic Folder or HTML File",
                    allowed_exts={".html", ".htm", ".xhtml", ".cbz", ".zip", ".jpg", ".jpeg", ".png", ".webp"}
                )
                if not picked or not picked.exists():
                    continue
                _run_comic_scrape_flow(cfg, str(picked))
                break
            elif selected_idx == 1:  # Enter Web URL
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}{FG_CYAN}=== Enter Comic / Manga URL ==={RESET}\n")
                print(f"{DIM}Enter web URL to scrape (or 0 / Esc to cancel):{RESET}\n")
                try:
                    url_in = input(f"{BOLD}{FG_CYAN}URL:{RESET} ").strip().strip('"\'')
                except (KeyboardInterrupt, EOFError):
                    url_in = ""
                if not url_in or url_in.lower() in ("0", "q", "esc"):
                    continue
                _run_comic_scrape_flow(cfg, url_in)
                break
            elif selected_idx == 2:  # Change directory
                action_change_tool_directory(cfg, "comic", "Comic Scraper")
                continue
        elif key in ("ESC", "q", "Q"):
            break


def _run_comic_scrape_flow(config: dict, source: str):
    """Execute the packaging selection, cookie check, and extraction for a chosen source."""
    from .comic_scraper import scrape_and_download_comic

    clear_screen()
    show_cursor()

    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print(f"               {BOLD}COMIC & IMAGE GALLERY SCRAPER{RESET}")
    print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
    print(f" Source: {FG_YELLOW}{source}{RESET}\n")

    print(f"{BOLD}Select Packaging Option:{RESET}")
    print(f"  {FG_CYAN}[1]{RESET} Download Images to Folder Only")
    print(f"  {FG_CYAN}[2]{RESET} Auto-bundle into Multi-Page PDF")
    print(f"  {FG_CYAN}[3]{RESET} Auto-bundle into Comic Book Zip (.cbz)")
    print(f"  {DIM}[0] Cancel{RESET}")

    opt = input(f"\n{BOLD}Choice [1-3, default 1]:{RESET} ").strip()
    if opt.lower() in ("0", "q", "esc"):
        return

    auto_format = "pdf" if opt == "2" else ("cbz" if opt == "3" else None)
    order_choice = "ascending"
    if auto_format:
        order_choice = prompt_merge_order_mode(
            header_title="📚  COMIC & GALLERY SCRAPER",
            item_type="pages",
        )
        if not order_choice:
            return

    print(f"\n{BOLD}Cookie File for Authentication [Optional]:{RESET}")
    print(f"  {DIM}Press Enter to skip, or enter .txt path, or [b] to browse disk{RESET}")
    cookie_in = input(f"Cookie path: ").strip().strip('"\'')
    cookie_file = None
    if cookie_in.lower() == "b":
        cookie_path = browse_interactive_path(
            mode="file",
            title="Select Netscape Cookies File",
            allowed_exts={".txt", ".cookie", ".cookies"}
        )
        if cookie_path and cookie_path.is_file():
            cookie_file = cookie_path
    elif cookie_in and cookie_in not in ("0", "none"):
        p = Path(cookie_in)
        if p.is_file():
            cookie_file = p

    def _progress(pct: int, msg: str):
        bar = f"{FG_CYAN}{'━' * (pct // 4)}{RESET}{DIM}{'━' * (25 - (pct // 4))}{RESET}"
        sys.stdout.write(f"\r  [{bar}] {pct:>3}% — {msg}")
        sys.stdout.flush()

    try:
        print(f"\n{BOLD}[+] Starting extraction...{RESET}")
        res = scrape_and_download_comic(
            source=source,
            output_base_dir=get_tool_output_dir("comic", config),
            auto_format=auto_format,
            cookie_file=cookie_file,
            progress_callback=_progress,
            order=order_choice,
        )
        print(f"\n\n{FG_GREEN}[✓] Extraction finished successfully!{RESET}")
        print(f"    Saved to: {res}")
    except Exception as e:
        print(f"\n\n{FG_RED}[-] Scraping failed: {e}{RESET}")

    pause_prompt()



def _run_pack_images_flow(config: dict):
    """Execute interactive image packing into PDF or CBZ."""
    from .packager import images_to_pdf, images_to_cbz, batch_pack_folders

    folder = browse_interactive_path(
        mode="folder",
        title="Select Folder of Images to Pack",
    )

    if not folder or not folder.is_dir():
        return

    clear_screen()
    show_cursor()

    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print(f"                 {BOLD}IMAGES TO PDF / CBZ PACKAGER{RESET}")
    print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
    print(f" Target Folder: {FG_YELLOW}{folder}{RESET}\n")

    print(f"{BOLD}Select Output Format:{RESET}")
    print(f"  {FG_CYAN}[1]{RESET} Multi-Page PDF (.pdf)")
    print(f"  {FG_CYAN}[2]{RESET} Comic Book Zip (.cbz)")
    print(f"  {DIM}[0] Cancel{RESET}")

    fmt_choice = input(f"\n{BOLD}Choice [1-2, default 1]:{RESET} ").strip()
    if fmt_choice.lower() in ("0", "q", "esc"):
        return

    target_fmt = "cbz" if fmt_choice == "2" else "pdf"

    order_choice = prompt_merge_order_mode(
        header_title="📦  IMAGES TO PDF / CBZ PACKAGER",
        item_type="images",
    )
    if not order_choice:
        return

    recurse_in = input(f"\n{BOLD}Recurse into nested subfolders? [y/N]:{RESET} ").strip().lower()
    recurse = recurse_in in ("y", "yes")

    def _progress(pct: int, msg: str):
        bar = f"{FG_CYAN}{'━' * (pct // 4)}{RESET}{DIM}{'━' * (25 - (pct // 4))}{RESET}"
        sys.stdout.write(f"\r  [{bar}] {pct:>3}% — {msg}")
        sys.stdout.flush()

    try:
        out_dir = get_tool_output_dir("packager", config)
        print(f"\n{BOLD}[+] Packaging images...{RESET}")
        if recurse:
            created = batch_pack_folders(folder, out_dir, format_type=target_fmt, recurse=True, progress_callback=_progress, order=order_choice)
            print(f"\n\n{FG_GREEN}[✓] Batch complete! Created {len(created)} {target_fmt.upper()} archives in:{RESET}")
            print(f"    {out_dir}")
        else:
            out_file = out_dir / f"{folder.name}.{target_fmt}"
            if target_fmt == "cbz":
                ok, count = images_to_cbz(folder, out_file, progress_callback=_progress, order=order_choice)
            else:
                ok, count = images_to_pdf(folder, out_file, progress_callback=_progress, order=order_choice)

            if ok:
                print(f"\n\n{FG_GREEN}[✓] Successfully created {target_fmt.upper()} ({count} pages):{RESET}")
                print(f"    {out_file}")
            else:
                print(f"\n\n{FG_YELLOW}[!] No supported images found in: {folder}{RESET}")
    except Exception as e:
        print(f"\n\n{FG_RED}[-] Packaging failed: {e}{RESET}")

    pause_prompt()


def action_pack_images(config: dict):
    """Sub-Action: Image Folder to PDF / CBZ Packager Menu."""
    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        p_dir = str(get_tool_output_dir("packager", cfg))
        p_disp = "..." + p_dir[-33:] if len(p_dir) > 36 else p_dir

        pack_options = [
            ("📦", "Select Folder to Pack into PDF/CBZ", "Browse disk and select folder of images"),
            ("📁", "Change Packager Output Directory", f"Current: {p_disp}"),
            ("←", "Back to Other Tools", "Return to utilities menu"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}📦  IMAGES TO PDF / CBZ PACKAGER{RESET}  {DIM}Bundle image folders into books{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (icon, title, desc) in enumerate(pack_options):
            num = idx + 1 if idx < len(pack_options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<34}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<34}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-2, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(pack_options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(pack_options)
        elif key in ("1", "2"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 2):
            break

        if key == "ENTER":
            if selected_idx == 0:
                _run_pack_images_flow(cfg)
            elif selected_idx == 1:
                action_change_tool_directory(cfg, "packager", "Image Packager")


def _run_ocr_flow(config: dict):
    """Execute interactive OCR text extraction on image or folder."""
    from .ocr import run_ocr

    target_path = browse_interactive_path(
        mode="any",
        title="Select Image or Image Folder for OCR",
        allowed_exts=IMAGE_EXTENSIONS,
    )

    if not target_path or not target_path.exists():
        return

    clear_screen()
    show_cursor()

    print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
    print(f"                 {BOLD}OCR — IMAGE TO TEXT EXTRACTOR{RESET}")
    print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
    print(f" Target: {FG_YELLOW}{target_path}{RESET}\n")

    lang_in = input(f"{BOLD}Tesseract Language Code [default: eng, or 0 to cancel]:{RESET} ").strip() or "eng"
    if lang_in.lower() in ("0", "q", "esc"):
        return

    combine_in = input(f"{BOLD}Combine into single .txt file? [Y/n]:{RESET} ").strip().lower()
    combine = combine_in not in ("n", "no")

    order_choice = "ascending"
    if target_path.is_dir() and combine:
        order_choice = prompt_merge_order_mode(
            header_title="🔍  OCR — IMAGE TO TEXT EXTRACTOR",
            item_type="images",
        )
        if not order_choice:
            return

    def _progress(pct: int, msg: str):
        bar = f"{FG_CYAN}{'━' * (pct // 4)}{RESET}{DIM}{'━' * (25 - (pct // 4))}{RESET}"
        sys.stdout.write(f"\r  [{bar}] {pct:>3}% — {msg}")
        sys.stdout.flush()

    try:
        print(f"\n{BOLD}[+] Running OCR engine...{RESET}")
        ok, out_path, preview = run_ocr(
            target=target_path,
            output_dir=get_tool_output_dir("ocr", config),
            lang=lang_in,
            combine_output=combine,
            progress_callback=_progress,
            order=order_choice,
        )
        print(f"\n\n{FG_GREEN}[✓] OCR Extraction Successful!{RESET}")
        print(f"    Output: {out_path}\n")
        if preview:
            print("--- Extracted Text Preview ---")
            print(preview[:500] + ("\n..." if len(preview) > 500 else ""))
            print("------------------------------")
    except Exception as e:
        print(f"\n\n{FG_RED}[-] OCR failed: {e}{RESET}")

    pause_prompt()


def action_ocr(config: dict):
    """Sub-Action: OCR Image to Text Extraction Menu."""
    from .ocr import is_tesseract_available, get_tesseract_install_hint

    if not is_tesseract_available():
        clear_screen()
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
        print(f"                 {BOLD}OCR — IMAGE TO TEXT EXTRACTOR{RESET}")
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
        print(f"{FG_YELLOW}[!] {get_tesseract_install_hint()}{RESET}\n")
        pause_prompt()
        return

    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        o_dir = str(get_tool_output_dir("ocr", cfg))
        o_disp = "..." + o_dir[-33:] if len(o_dir) > 36 else o_dir

        ocr_options = [
            ("🔍", "Select Image or Folder for OCR", "Browse disk and select target to extract text"),
            ("📁", "Change OCR Output Directory", f"Current: {o_disp}"),
            ("←", "Back to Other Tools", "Return to utilities menu"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}🔍  OCR IMAGE TO TEXT EXTRACTOR{RESET} {DIM}Tesseract optical recognition{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (icon, title, desc) in enumerate(ocr_options):
            num = idx + 1 if idx < len(ocr_options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<34}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<34}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-2, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(ocr_options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(ocr_options)
        elif key in ("1", "2"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 2):
            break

        if key == "ENTER":
            if selected_idx == 0:
                _run_ocr_flow(cfg)
            elif selected_idx == 1:
                action_change_tool_directory(cfg, "ocr", "OCR Transcripts")


# ============================================================================
# SETTINGS & DIRECTORY MANAGEMENT SUBMENU
# ============================================================================

def action_manage_all_directories(config: dict):
    """Sub-Action: View & update custom output directories across all tools."""
    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        v_dir = str(get_tool_output_dir("video", cfg))
        c_dir = str(get_tool_output_dir("converter", cfg))
        cm_dir = str(get_tool_output_dir("comic", cfg))
        p_dir = str(get_tool_output_dir("packager", cfg))
        o_dir = str(get_tool_output_dir("ocr", cfg))

        items = [
            ("🎬 Video Downloads Directory", v_dir, "video", "Video Downloads"),
            ("🔄 Media Converter Directory", c_dir, "converter", "Media Converter"),
            ("📚 Comic Scraper Directory", cm_dir, "comic", "Comic Scraper"),
            ("📦 Packager Directory", p_dir, "packager", "Image Packager"),
            ("🔍 OCR Transcripts Directory", o_dir, "ocr", "OCR Transcripts"),
            ("⚡ Auto-Separate into Subfolders", "", "separate", "Separate Subfolders"),
            ("🔄 Reset to Default Subfolders", "", "reset", "Reset All"),
            ("← Back to Settings Submenu", "", "back", "Back"),
        ]

        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}📁  MANAGE OUTPUT DIRECTORIES{RESET}     {DIM}Per-tool custom storage paths{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (label, path_val, key_name, t_label) in enumerate(items):
            num = idx + 1 if idx < len(items) - 1 else 0
            disp_path = path_val
            if len(disp_path) > 34:
                disp_path = "..." + disp_path[-31:]

            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                if disp_path:
                    print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{label:<32}{RESET} {FG_YELLOW}{disp_path}{RESET}")
                else:
                    print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{label}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                if disp_path:
                    print(f"{prefix} {num_badge} {FG_WHITE}{label:<32}{RESET} {DIM}{disp_path}{RESET}")
                else:
                    print(f"{prefix} {num_badge} {FG_WHITE}{label}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-7, 0]{RESET} Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(items)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(items)
        elif key in ("1", "2", "3", "4", "5", "6", "7"):
            selected_idx = int(key) - 1
            key = "ENTER"
        elif key in ("0", "ESC", "q", "Q") or (key == "ENTER" and selected_idx == 7):
            break

        if key == "ENTER":
            if selected_idx < 5:
                _, _, t_key, t_lbl = items[selected_idx]
                action_change_tool_directory(cfg, t_key, t_lbl)
            elif selected_idx == 5:
                # Auto-separate into distinct subfolders
                clear_screen()
                show_cursor()
                cur_base = str(get_download_dir())
                print(f"\n{BOLD}{FG_CYAN}=== Auto-Separate Output Directories ==={RESET}\n")
                print("This will organize all tool outputs into distinct dedicated subfolders:")
                print(f"  • Video Downloads  → <base>/Videos")
                print(f"  • Media Converter  → <base>/Converted")
                print(f"  • Comic Scraper    → <base>/Comics")
                print(f"  • Image Packager   → <base>/Packaged")
                print(f"  • OCR Transcripts  → <base>/OCR\n")
                print(f"Base Directory: {FG_YELLOW}{cur_base}{RESET}\n")

                ans = input(f"{BOLD}Separate all tool directories under this base folder? [Y/n]: {RESET}").strip().lower()
                if ans not in ("n", "no"):
                    res = auto_separate_all_tool_dirs(cur_base, create_video_subfolder=True)
                    clear_screen()
                    print(f"\n{FG_GREEN}[✓] Successfully separated all tool directories into dedicated folders:{RESET}\n")
                    for t_name, t_p in res.items():
                        print(f"    • {t_name.capitalize():<12}: {t_p}")
                    time.sleep(1.8)
                hide_cursor()
            elif selected_idx == 6:
                # Reset to default subfolders
                clear_screen()
                show_cursor()
                print(f"\n{BOLD}{FG_CYAN}=== Reset Tool Directories to Defaults ==={RESET}\n")
                ans = input(f"{BOLD}Reset all tool directories back to default system Downloads subfolders? [y/N]: {RESET}").strip().lower()
                if ans in ("y", "yes"):
                    res = reset_all_tool_dirs_to_defaults()
                    clear_screen()
                    print(f"\n{FG_GREEN}[✓] All tool directories reset to default subfolders:{RESET}\n")
                    for t_name, t_p in res.items():
                        print(f"    • {t_name.capitalize():<12}: {t_p}")
                    time.sleep(1.8)
                hide_cursor()


def action_settings_and_cleanup(config: dict):
    """Action 3: Settings & Cleanup Consolidated Sub-Menu."""
    options = [
        ("📁", "Manage Tool Output Directories", "Configure custom storage paths for each tool"),
        ("⚙", "Engine & Extraction Settings", "Adjust race timers, merge formats, and tier toggles"),
        ("🗑", "Clear Selected Videos", "Interactive multi-select deletion checklist"),
        ("💥", "Clear All Videos", "Wipe all downloaded video files from folder"),
        ("📜", "View Download History", "Display log of previous media extractions"),
        ("←", "Back to Main Menu", "Return to main dashboard"),
    ]

    selected_idx = 0
    hide_cursor()

    while True:
        cfg = load_config()
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}⚙   SETTINGS & PREFERENCES{RESET}      {DIM}Output directories, engines & history{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

        for idx, (icon, title, desc) in enumerate(options):
            num = idx + 1 if idx < len(options) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{icon} {title:<32}{RESET} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{icon} {title:<32}{RESET} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-5, 0]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(options)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(options)
        elif key in ("1", "2", "3", "4", "5"):
            num = int(key) - 1
            selected_idx = num
            if num == 0:
                action_manage_all_directories(cfg)
            elif num == 1:
                action_settings(cfg)
            elif num == 2:
                action_clear_selected(cfg)
            elif num == 3:
                action_clear_all(cfg)
            elif num == 4:
                show_history()
                pause_prompt()
        elif key == "0" or (key == "ENTER" and selected_idx == 5):
            break
        elif key == "ENTER":
            if selected_idx == 0:
                action_manage_all_directories(cfg)
            elif selected_idx == 1:
                action_settings(cfg)
            elif selected_idx == 2:
                action_clear_selected(cfg)
            elif selected_idx == 3:
                action_clear_all(cfg)
            elif selected_idx == 4:
                show_history()
                pause_prompt()
            elif selected_idx == 5:
                break
        elif key in ("ESC", "q", "Q"):
            break


def action_settings(config: dict):
    """Sub-Action: Interactive Engine Settings Sub-Menu."""
    hide_cursor()
    selected_idx = 0

    while True:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
        print(f"{BOLD}{FG_CYAN}│{RESET}  {BOLD}⚙   ENGINE CONFIGURATION{RESET}    {DIM}Toggle tiers, format & timeouts{RESET}  {BOLD}{FG_CYAN}│{RESET}")
        print(f"{BOLD}{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}\n")

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

        conflict_pol = config.get("conflict_policy")
        conflict_label_map = {
            "replace": "Always Replace",
            "keep_both": "Always Keep Both",
            "skip": "Always Skip",
            "compare": "Always Compare",
        }
        conflict_disp = conflict_label_map.get(conflict_pol, "Ask Every Time")

        items = [
            ("Auto-Open on Download", yes_no_badge(auto_open), "Automatically play video after download"),
            ("Replace or Skip Files", f"{FG_YELLOW}{conflict_disp}{RESET}", "Collision policy: Replace, Keep Both, Skip, Compare"),
            ("Container Merge Format", f"{FG_YELLOW}{merge_fmt.upper()}{RESET}  (mp4 / mkv)", "Toggle output format"),
            ("Race Timeout", f"{FG_YELLOW}{timeout}s{RESET}", "Multi-agent tier race max wait"),
            ("Browser Tier Grace Timer", f"{FG_YELLOW}{grace}s{RESET}", "Delay before starting heavy headless browser"),
            ("Confidence Threshold", f"{FG_YELLOW}{confidence}{RESET}", "Minimum candidate score required to win"),
            ("Separate Terminal Windows", badge(terminals_on), "Spawn physical terminal windows vs single-terminal"),
            ("Tier 1: yt-dlp Native Agent", badge(ytdlp_on), "Fast direct extractor & format selector"),
            ("Tier 2: Scrapling Adaptive Agent", badge(scrapling_on), "Intelligent HTTP & stealth DOM scanner"),
            ("Tier 3: Static HTML Scanner Agent", badge(static_on), "BeautifulSoup & regex stream matcher"),
            ("Tier 4: Headless Browser Agent", badge(browser_on), "Selenium Chromium network sniffer"),
            ("← Back to Settings & Cleanup", "", "Return to previous menu"),
        ]

        for idx, (label, val_str, desc) in enumerate(items):
            num = idx + 1 if idx < len(items) - 1 else 0
            if idx == selected_idx:
                prefix = f" {BOLD}{FG_CYAN}▶{RESET}"
                num_badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num:>2} {RESET}"
                print(f"{prefix} {num_badge} {BOLD}{FG_CYAN}{label:<34}{RESET} {val_str:<22} {DIM}— {desc}{RESET}")
            else:
                prefix = "   "
                num_badge = f"{DIM}[{num:>2}]{RESET}"
                print(f"{prefix} {num_badge} {FG_WHITE}{label:<34}{RESET} {val_str:<22} {DIM}— {desc}{RESET}")

        print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter/Space]{RESET} Toggle / Edit  {DIM}•{RESET} {FG_RED}[Esc/q/0]{RESET} Back")

        key = read_key()
        if key == "UP":
            selected_idx = (selected_idx - 1) % len(items)
        elif key == "DOWN":
            selected_idx = (selected_idx + 1) % len(items)
        elif key in ("ENTER", "SPACE"):
            if selected_idx == 0:
                config["auto_open"] = not auto_open
                save_config(config)
            elif selected_idx == 1:
                action_file_conflict_settings(config)
            elif selected_idx == 2:
                config["merge_format"] = "mkv" if merge_fmt == "mp4" else "mp4"
                save_config(config)
            elif selected_idx == 3:
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
            elif selected_idx == 4:
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
            elif selected_idx == 5:
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
            elif selected_idx == 6:
                config["spawn_terminals"] = not terminals_on
                save_config(config)
            elif selected_idx == 7:
                config["use_ytdlp"] = not ytdlp_on
                save_config(config)
            elif selected_idx == 8:
                config["use_scrapling"] = not scrapling_on
                save_config(config)
            elif selected_idx == 9:
                config["use_static_scanner"] = not static_on
                save_config(config)
            elif selected_idx == 10:
                config["use_browser"] = not browser_on
                save_config(config)
            elif selected_idx == 11:
                break

        elif key in ("ESC", "q", "Q", "0"):
            break


def action_change_directory(config: dict):
    """Sub-Action: Change Output Directory using disk browser."""
    new_path = browse_interactive_path(
        mode="folder",
        title="Select New Download Storage Directory",
    )

    if not new_path:
        return

    clear_screen()
    show_cursor()
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


def action_clear_selected(config: dict):
    """Sub-Action: Interactive Multi-Select Checklist Video Cleaner."""
    videos = get_video_files()
    download_dir = get_download_dir()

    if not videos:
        clear_screen()
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}")
        print(f"               {BOLD}CLEAR SELECTED VIDEOS{RESET}")
        print(f"{BOLD}{FG_CYAN}============================================================={RESET}\n")
        print(f"{FG_YELLOW}[!] No video files found to delete in: {download_dir}{RESET}")
        pause_prompt()
        return

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
        print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_YELLOW}[Space]{RESET} Toggle  {DIM}•{RESET} {FG_BLUE}[a]{RESET} Select All  {DIM}•{RESET} {FG_RED}[Enter]{RESET} Delete  {DIM}•{RESET} {DIM}[Esc/q/0]{RESET} Cancel")

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
                time.sleep(0.6)
            break
        elif key in ("ESC", "q", "Q", "0"):
            break


def action_clear_all(config: dict):
    """Sub-Action: Clear All Videos."""
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


# ============================================================================
# MAIN MENU CONTROLLER
# ============================================================================

def run_interactive_menu() -> int:
    """
    Main interactive dashboard controller.
    Consolidated, clean hierarchy with submenus and instant disk browser.
    """
    selected_index = 0

    options = [
        ("🎬", "Video Tools", "Download video stream, play, combine clips, directory, cleanup"),
        ("🧰", "Other Tools & Utilities", "Media converter, comic scraper, PDF packager, OCR"),
        ("⚙", "Settings & Preferences", "Manage per-tool output directories, engine options, history"),
        ("🚪", "Exit", "Close Tool-Kit CLI"),
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
                    time.sleep(1.0)
                else:
                    print(f"\n{FG_YELLOW}[!] Clipboard is empty or could not be accessed.{RESET}")
                    time.sleep(1.0)
            elif key == "IGNORE":
                pass
            elif key in ("1", "2", "3"):
                num = int(key) - 1
                selected_index = num
                if num == 0:
                    action_video_tools(config)
                elif num == 1:
                    action_other_tools(config)
                elif num == 2:
                    action_settings_and_cleanup(config)
            elif key == "0":
                break
            elif key == "ENTER":
                if selected_index == 0:
                    action_video_tools(config)
                elif selected_index == 1:
                    action_other_tools(config)
                elif selected_index == 2:
                    action_settings_and_cleanup(config)
                elif selected_index == 3:
                    break
            elif key in ("q", "Q", "ESC"):
                break

    except KeyboardInterrupt:
        pass
    finally:
        show_cursor()
        clear_screen()
        print(f"{FG_CYAN}Thank you for using Tool-Kit CLI!{RESET}\n")

    return 0
