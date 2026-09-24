"""
File collision detection and interactive resolution system for Video Extractor.
Provides Windows-style Replace / Keep Both / Skip / Compare Info workflows.
"""

import os
import sys
import json
import shutil
import subprocess
from datetime import datetime
from pathlib import Path
from typing import Optional

# Force UTF-8 stream encoding on Windows to support status symbols (✓, ✗, ╭, ─)
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
        import ctypes
        kernel32 = ctypes.windll.kernel32
        kernel32.SetConsoleMode(kernel32.GetStdHandle(-11), 7)
    except Exception:
        pass

# ANSI Styling
RESET = "\033[0m"
BOLD = "\033[1m"
DIM = "\033[2m"
FG_CYAN = "\033[96m"
FG_WHITE = "\033[97m"
FG_GREEN = "\033[92m"
FG_YELLOW = "\033[93m"
FG_BLUE = "\033[94m"
FG_RED = "\033[91m"
FG_BLACK = "\033[30m"
BG_CYAN = "\033[46m"
BG_BLUE = "\033[44m"


def generate_unique_path(target_path: Path) -> Path:
    """
    Generate non-colliding path using standard OS numbering:
    e.g. video.mp4 -> video (1).mp4 -> video (2).mp4
    """
    if not target_path.exists():
        return target_path

    parent = target_path.parent
    stem = target_path.stem
    suffix = target_path.suffix

    counter = 1
    while True:
        candidate_path = parent / f"{stem} ({counter}){suffix}"
        if not candidate_path.exists():
            return candidate_path
        counter += 1


def probe_file_info(path: Path) -> dict:
    """Inspect local file stats and optional ffprobe stream metadata."""
    info = {
        "name": path.name,
        "exists": path.exists(),
        "size_str": "Unknown",
        "modified_str": "Unknown",
        "format": path.suffix.upper().replace(".", "") or "MP4",
        "resolution": "Unknown",
        "duration": "Unknown",
    }
    if not path.exists():
        return info

    try:
        stat = path.stat()
        size_mb = stat.st_size / (1024 * 1024)
        info["size_str"] = f"{size_mb:.2f} MB"
        dt = datetime.fromtimestamp(stat.st_mtime)
        info["modified_str"] = dt.strftime("%Y-%m-%d %H:%M")
    except Exception:
        pass

    # Fast ffprobe inspection if installed
    if shutil.which("ffprobe"):
        try:
            cmd = [
                "ffprobe", "-v", "error",
                "-select_streams", "v:0",
                "-show_entries", "stream=width,height,duration",
                "-show_entries", "format=duration",
                "-of", "json",
                str(path)
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=2.0)
            if res.returncode == 0:
                data = json.loads(res.stdout)
                streams = data.get("streams", [])
                if streams:
                    w = streams[0].get("width")
                    h = streams[0].get("height")
                    if w and h:
                        info["resolution"] = f"{w}x{h} ({h}p)"
                    dur = streams[0].get("duration") or data.get("format", {}).get("duration")
                    if dur:
                        dur_sec = int(float(dur))
                        info["duration"] = f"{dur_sec // 60}:{dur_sec % 60:02d}"
        except Exception:
            pass

    return info


def get_incoming_info(candidate, target_path: Path, requested_quality: Optional[str] = None) -> dict:
    """Extract metadata from incoming media candidate for comparison."""
    size_str = "Adaptive Stream"
    filesize = candidate.metadata.get("filesize") or candidate.metadata.get("filesize_approx")
    if filesize:
        try:
            size_str = f"~{float(filesize) / (1024 * 1024):.2f} MB"
        except Exception:
            pass

    quality = requested_quality or candidate.metadata.get("quality") or candidate.metadata.get("format_note") or "Best"
    res = candidate.metadata.get("resolution")
    if not res and candidate.metadata.get("height"):
        res = f"{candidate.metadata.get('height')}p"
    if not res:
        res = str(quality)

    dur = candidate.metadata.get("duration")
    dur_str = "Unknown"
    if dur:
        try:
            dur_sec = int(float(dur))
            dur_str = f"{dur_sec // 60}:{dur_sec % 60:02d}"
        except Exception:
            pass

    engine = candidate.metadata.get("engine") or candidate.source or "web"

    return {
        "name": target_path.name,
        "size_str": size_str,
        "date_str": datetime.now().strftime("%Y-%m-%d %H:%M (Now)"),
        "source": engine,
        "type": candidate.label,
        "quality": str(quality),
        "resolution": str(res),
        "duration": dur_str,
    }


def render_diff_table(existing_info: dict, incoming_info: dict):
    """Render a clean side-by-side comparison table."""
    print(f"{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
    print(f"{FG_CYAN}│{RESET}  {BOLD}⇆  Replace or Skip Files — File Comparison{RESET}                 {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}├─────────────────────────────┬───────────────────────────────┤{RESET}")
    print(f"{FG_CYAN}│{RESET}  {BOLD}{FG_YELLOW}Existing File (Local Disk){RESET}  {FG_CYAN}│{RESET}  {BOLD}{FG_GREEN}Incoming Stream (New){RESET}       {FG_CYAN}│{RESET}")
    print(f"{FG_CYAN}├─────────────────────────────┼───────────────────────────────┤{RESET}")

    rows = [
        ("File Name", existing_info["name"], incoming_info["name"]),
        ("File Size", existing_info["size_str"], incoming_info["size_str"]),
        ("Timestamp", existing_info["modified_str"], incoming_info["date_str"]),
        ("Resolution", existing_info["resolution"], incoming_info["resolution"]),
        ("Duration", existing_info["duration"], incoming_info["duration"]),
        ("Source", f"Local ({existing_info['format']})", f"{incoming_info['source']} ({incoming_info['type'][:12]})"),
    ]

    for label, val_left, val_right in rows:
        v_l = val_left[:25]
        v_r = val_right[:27]
        print(f"{FG_CYAN}│{RESET}  {DIM}{label:<10}:{RESET} {v_l:<15} {FG_CYAN}│{RESET}  {DIM}{label:<10}:{RESET} {v_r:<17} {FG_CYAN}│{RESET}")

    print(f"{FG_CYAN}╰─────────────────────────────┴───────────────────────────────╯{RESET}")
    print()


def resolve_file_conflict(
    target_path: Path,
    candidate,
    requested_quality: Optional[str] = None,
    conflict_policy: Optional[str] = None,
) -> Optional[Path]:
    """
    Resolve destination file collision.
    Returns:
      - target_path if 'replace'
      - unique_path (e.g. video (1).mp4) if 'keep_both'
      - None if 'skip'
    """
    if not target_path.exists():
        return target_path

    # Check command-line override policies
    if conflict_policy == "replace":
        print(f"[!] Target file exists. Overwriting as requested: {target_path.name}")
        return target_path
    elif conflict_policy == "keep_both":
        unique = generate_unique_path(target_path)
        print(f"[+] Target file exists. Saving as: {unique.name}")
        return unique
    elif conflict_policy == "skip":
        print(f"[!] Target file exists. Skipping download: {target_path.name}")
        return None

    # In non-interactive environment (pipes, headless CI), default safely to keep_both
    if not sys.stdin.isatty():
        unique = generate_unique_path(target_path)
        print(f"[+] Destination file '{target_path.name}' exists. Non-interactive mode saving as '{unique.name}'.")
        return unique

    from .menu import read_key, clear_screen, hide_cursor, show_cursor

    unique_path = generate_unique_path(target_path)
    existing_info = probe_file_info(target_path)
    incoming_info = get_incoming_info(candidate, target_path, requested_quality)

    options = [
        ("✓", "Replace the file in the destination", f"Overwrite existing file ({existing_info['size_str']})"),
        ("➕", f"Keep both files (save as \"{unique_path.name}\")", "Preserve existing file and save with new name"),
        ("↷", "Skip this file", "Do not download; cancel without changes"),
        ("⇆", "Compare info for both files", "View side-by-side size, resolution, and details"),
    ]

    selected_index = 0
    show_diff_mode = False
    hide_cursor()

    try:
        while True:
            clear_screen()

            if show_diff_mode:
                render_diff_table(existing_info, incoming_info)
                print(f" {BOLD}Choose an action:{RESET}")
                print(f"  {FG_CYAN}[1]{RESET} {BOLD}Replace{RESET}  {DIM}•{RESET}  {FG_GREEN}[2]{RESET} {BOLD}Keep Both{RESET}  {DIM}•{RESET}  {FG_RED}[3]{RESET} {BOLD}Skip{RESET}  {DIM}•{RESET}  {DIM}[Esc] Back to options{RESET}")

                key = read_key()
                if key in ("1", "r", "R"):
                    return target_path
                elif key in ("2", "k", "K"):
                    return unique_path
                elif key in ("3", "s", "S", "q", "Q"):
                    return None
                elif key in ("ESC", "b", "B"):
                    show_diff_mode = False
                continue

            # Main Conflict Dialog Card (Styled like Windows Replace or Skip Files dialog)
            dest_name = target_path.name
            if len(dest_name) > 38:
                dest_name = dest_name[:35] + "..."

            print(f"{FG_CYAN}╭─────────────────────────────────────────────────────────────╮{RESET}")
            print(f"{FG_CYAN}│{RESET}  {BOLD}Replace or Skip Files{RESET}                                      {FG_CYAN}│{RESET}")
            print(f"{FG_CYAN}├─────────────────────────────────────────────────────────────┤{RESET}")
            print(f"{FG_CYAN}│{RESET}  The destination already has a file named {BOLD}\"{dest_name}\"{RESET}   {FG_CYAN}│{RESET}")
            print(f"{FG_CYAN}│{RESET}                                                             {FG_CYAN}│{RESET}")

            for idx, (icon, title, desc) in enumerate(options):
                num = idx + 1
                if idx == selected_index:
                    badge = f"{BOLD}{BG_CYAN}{FG_BLACK} {num} {RESET}"
                    arrow = f"{BOLD}{FG_CYAN}▶{RESET}"
                    print(f"{FG_CYAN}│{RESET} {arrow} {badge} {BOLD}{FG_CYAN}{icon} {title:<46}{RESET} {FG_CYAN}│{RESET}")
                else:
                    badge = f"{DIM}[{num}]{RESET}"
                    print(f"{FG_CYAN}│{RESET}   {badge} {FG_WHITE}{icon} {title:<46}{RESET} {FG_CYAN}│{RESET}")

            print(f"{FG_CYAN}│{RESET}                                                             {FG_CYAN}│{RESET}")
            print(f"{FG_CYAN}╰─────────────────────────────────────────────────────────────╯{RESET}")
            print(f"\n{DIM}─────────────────────────────────────────────────────────────{RESET}")
            print(f" {FG_CYAN}[↑/↓]{RESET} Navigate  {DIM}•{RESET} {FG_GREEN}[Enter]{RESET} Select  {DIM}•{RESET} {FG_YELLOW}[1-4]{RESET} Quick Jump  {DIM}•{RESET} {FG_RED}[Esc/q]{RESET} Skip")

            key = read_key()

            if key == "UP":
                selected_index = (selected_index - 1) % len(options)
            elif key == "DOWN":
                selected_index = (selected_index + 1) % len(options)
            elif key == "1":
                return target_path
            elif key == "2":
                return unique_path
            elif key == "3":
                return None
            elif key == "4":
                show_diff_mode = True
            elif key == "ENTER":
                if selected_index == 0:
                    return target_path
                elif selected_index == 1:
                    return unique_path
                elif selected_index == 2:
                    return None
                elif selected_index == 3:
                    show_diff_mode = True
            elif key in ("ESC", "q", "Q"):
                return None

    except KeyboardInterrupt:
        return None
    finally:
        show_cursor()
        clear_screen()
