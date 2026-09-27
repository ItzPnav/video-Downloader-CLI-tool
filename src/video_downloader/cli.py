import sys
import warnings
# Suppress non-fatal upstream compatibility warnings on Python 3.14+
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=DeprecationWarning)

from pathlib import Path
from urllib.parse import urlparse

# Force UTF-8 stream encoding on Windows to support status symbols (✓, ✗, ➡)
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

from .utils import (
    load_config,
    get_version,
    print_banner,
    print_step,
    write_history,
    safe_filename,
    get_download_dir,
    get_config_dir,
    ROOT,
)

from urllib.parse import urlparse



def valid_url(url):

    parsed = urlparse(url)

    return parsed.scheme in (
        "http",
        "https",
    )


def show_candidates(title, candidates):

    if not candidates:
        return

    print()
    print("=" * 60)
    print(title)
    print("=" * 60)

    for index, candidate in enumerate(
        candidates,
        1,
    ):

        print()
        print(
            f"[{index}] "
            f"score={candidate.score} "
            f"type={candidate.label}"
        )

        print(
            f"    source: {candidate.source}"
        )

        print(
            f"    mime: "
            f"{candidate.mime_type or 'unknown'}"
        )

        print(
            f"    url: {candidate.url}"
        )




def clean_downloads():

    from pathlib import Path

    download_dir = get_download_dir()

    video_extensions = {
        ".mp4",
        ".mkv",
        ".webm",
        ".m4v",
        ".mov",
        ".avi",
        ".3gp",
        ".3g2",
        ".flv",
        ".f4v",
        ".wmv",
        ".ogv",
        ".mpeg",
        ".mpg",
        ".ts",
        ".m2ts",
        ".mts"
    }

    if not download_dir.exists():

        print(
            "[!] Download directory "
            "does not exist."
        )

        return 0

    videos = [
        p for p in download_dir.iterdir()
        if p.is_file()
        and p.suffix.lower()
        in video_extensions
    ]

    if not videos:

        print()
        print(
            "[+] No downloaded video files found."
        )
        print()

        return 0

    total_size = sum(
        p.stat().st_size
        for p in videos
    )

    size_mb = (
        total_size
        / (1024 * 1024)
    )

    print()
    print(
        f"[+] Found {len(videos)} "
        f"video(s)"
    )

    print(
        f"[+] Storage: "
        f"{size_mb:.1f} MB"
    )

    print()

    answer = input(
        "Delete these videos? [y/N]: "
    ).strip().lower()

    if answer != "y":

        print(
            "[+] Cleanup cancelled."
        )

        return 0

    deleted = 0

    for video in videos:

        try:

            video.unlink()

            print(
                f"[✓] Deleted: "
                f"{video.name}"
            )

            deleted += 1

        except Exception as error:

            print(
                f"[!] Could not delete "
                f"{video.name}: {error}"
            )

    print()
    print(
        f"[✓] Deleted {deleted} "
        f"video(s)."
    )

    print(
        f"[✓] Freed approximately "
        f"{size_mb:.1f} MB."
    )

    return 0



def system_open(filepath):

    import os
    import shutil
    import sys
    import subprocess
    from pathlib import Path

    path = Path(filepath)

    if not path.exists():
        print(f"[!] File not found: {path}")
        return False

    try:

        if shutil.which("termux-open"):
            subprocess.run(
                ["termux-open", str(path)],
                check=False
            )
            return True

        elif sys.platform == "win32":
            os.startfile(str(path))
            return True

        elif sys.platform == "darwin":
            subprocess.run(
                ["open", str(path)],
                check=False
            )
            return True

        elif shutil.which("xdg-open"):
            subprocess.run(
                ["xdg-open", str(path)],
                check=False
            )
            return True

        else:
            print(
                f"[!] No video opener found for: {path.name}"
            )
            return False

    except Exception as error:

        print(
            f"[!] Could not open video ({error})"
        )
        return False


def open_downloaded_video(output=None):

    from pathlib import Path

    if output:
        path = Path(output)

        if path.exists():
            print()
            print("[+] Opening video...")
            return system_open(path)

    download_dir = get_download_dir()

    if not download_dir.exists():
        return False

    extensions = {
        ".mp4",
        ".mkv",
        ".webm",
        ".m4v",
        ".mov",
        ".avi",
        ".3gp",
        ".3g2",
        ".flv"
    }

    videos = [
        p for p in download_dir.iterdir()
        if p.is_file()
        and p.suffix.lower() in extensions
    ]

    if not videos:
        return False

    latest = max(
        videos,
        key=lambda p: p.stat().st_mtime
    )

    print()
    print(f"[+] Opening: {latest.name}")

    return system_open(latest)



def open_video_picker():

    from pathlib import Path

    download_dir = get_download_dir()

    extensions = {
        ".mp4", ".mkv", ".webm",
        ".m4v", ".mov", ".avi",
        ".3gp", ".3g2", ".flv",
        ".f4v", ".wmv", ".ogv",
        ".mpeg", ".mpg", ".ts",
        ".m2ts", ".mts"
    }

    if not download_dir.exists():
        print("[!] Download directory not found.")
        return 1

    videos = sorted(
        [
            p for p in download_dir.iterdir()
            if p.is_file()
            and p.suffix.lower() in extensions
        ],
        key=lambda p: p.stat().st_mtime,
        reverse=True
    )

    if not videos:
        print("[!] No videos found in Downloads.")
        return 0

    print()
    print("=" * 60)
    print("                 YOUR VIDEOS")
    print("=" * 60)

    for i, video in enumerate(videos, 1):

        size_mb = (
            video.stat().st_size
            / (1024 * 1024)
        )

        print(
            f"{i:>3}. {video.name}"
            f"  [{size_mb:.1f} MB]"
        )

    print()
    print("  0. Cancel")
    print()

    while True:

        choice = input(
            "Select video: "
        ).strip()

        if choice == "0":
            print("[+] Cancelled.")
            return 0

        try:
            index = int(choice) - 1

            if not 0 <= index < len(videos):
                raise ValueError

        except ValueError:
            print("[!] Enter a valid number.")
            continue

        selected = videos[index]

        print()
        print(f"[+] Opening: {selected.name}")

        system_open(selected)

        return 0


def show_help():

    print("=" * 60)
    print("                 VIDEO EXTRACTOR")
    print("=" * 60)
    print()
    print(f"Version: {get_version()}")
    print()
    print("Usage:")
    print('  video "URL" [options]')
    print('  video convert <input> --to <format> [options]')
    print('  video comic <url_or_file> [options]')
    print('  video pack <folder> --to <pdf|cbz> [options]')
    print('  video ocr <image_or_folder> [options]')
    print('  video preview [url_or_file]')
    print()
    print("Commands:")
    print("  video                    Interactive terminal navigation menu")
    print('  video "URL"              Extract and download media')
    print("  video convert <file>     Convert media (video->gif, audio, images, text->pdf)")
    print("  video comic <url/file>   Scrape & download comic/image gallery chapters")
    print("  video pack <folder>      Bundle image folders into multi-page PDF or CBZ")
    print("  video ocr <img/folder>   Extract text from images using Tesseract OCR")
    print("  video preview [url/file] Launch instant browser media player / stream previewer")
    print("  --menu                   Open interactive terminal menu")
    print("  --help                   Show help")
    print("  --version                Show version")
    print("  --history                Show download history")
    print("  --update                 Update extractor")
    print("  --clean                  Delete downloaded videos")
    print("  --open                   Choose and play a video")
    print()
    print("Conversion Options (video convert):")
    print("  --to <format>            Target format (gif, mp3, mp4, wav, flac, aac, png, jpg, pdf)")
    print("  --fps 30                 Frames per second for GIF (default: 30)")
    print("  --res 504p|480p|360p     Height resolution for GIF (default: 504p)")
    print("  --quality high|med|low   Color palette quality for GIF (default: high)")
    print("  --out <path>             Custom output path or directory")
    print()
    print("Comic / Packaging Options:")
    print("  --pdf                    Auto-bundle into PDF")
    print("  --cbz                    Auto-bundle into Comic Book Zip (CBZ)")
    print("  --cookies <file.txt>     Supply Netscape cookies.txt for login/age-gates")
    print("  --respect-robots         Check and respect site robots.txt policy")
    print("  --recurse                Recursively process nested subfolders (for pack)")
    print("  --out <path>             Custom output directory")
    print()
    print("OCR Options (video ocr):")
    print("  --lang <code>            Tesseract language code (e.g. eng, jpn, deu; default: eng)")
    print("  --separate               Write individual .txt file per image instead of single combined")
    print("  --out <dir>              Custom output directory")
    print()
    print("Extraction Options:")
    print("  --quality 1080p          Request video quality (e.g. 720p, 1080p)")
    print("  --race-timeout 20        Multi-agent tier race timeout in seconds (default: 20)")
    print("  --browser-grace 2.5      Grace period before spawning heavy browser tier (default: 2.5s)")
    print("  --confidence 50          Minimum candidate score threshold to win (default: 50)")
    print("  --auto-open              Automatically open video after download")
    print("  --no-open                Don't open video after download")
    print("  --spawn-terminals        Spawn separate GUI terminal windows per tier")
    print("  --no-terminals           Run race headlessly inside current terminal")
    print("  --no-ytdlp               Exclude yt-dlp agent from race")
    print("  --no-static              Exclude static scanner agent from race")
    print("  --no-browser             Exclude headless Chromium agent from race")
    print("  --no-scrapling           Exclude Scrapling agent from race")
    print("  --replace                Overwrite destination file if it exists without prompt")
    print("  --keep-both              Save as 'name (1).mp4' if destination exists without prompt")
    print("  --skip-existing          Skip download if destination file already exists")
    print()
    print("Output:")
    print("  /sdcard/Download/ (or configured directory)")
    print()
    print("=" * 60)
    print()


def run_cli_convert(args: list) -> int:
    """Execute media conversion command from CLI arguments."""
    from .converter import (
        convert_video_to_gif,
        convert_video_to_audio,
        convert_audio_to_audio,
        convert_gif_to_mp4,
        convert_image,
        convert_text_to_pdf,
        remux_or_transcode_video,
    )
    from .utils import get_download_dir

    if not args:
        print("[-] Usage: video convert <input_file> --to <format> [options]")
        return 1

    input_file = Path(args[0]).resolve()
    if not input_file.is_file():
        print(f"[-] Input file not found: {input_file}")
        return 1

    target_fmt = None
    fps = 30
    height = 504
    colors = 256
    custom_out = None

    idx = 1
    while idx < len(args):
        a = args[idx]
        if a == "--to" and idx + 1 < len(args):
            target_fmt = args[idx + 1].lower().lstrip(".")
            idx += 1
        elif a.startswith("--to="):
            target_fmt = a.split("=", 1)[1].lower().lstrip(".")
        elif a == "--fps" and idx + 1 < len(args):
            try:
                fps = int(args[idx + 1])
            except ValueError:
                pass
            idx += 1
        elif a == "--res" and idx + 1 < len(args):
            r_str = args[idx + 1].lower().replace("p", "")
            try:
                height = int(r_str)
            except ValueError:
                pass
            idx += 1
        elif a == "--quality" and idx + 1 < len(args):
            q_str = args[idx + 1].lower()
            colors = 256 if "high" in q_str else (128 if "med" in q_str else 64)
            idx += 1
        elif a == "--out" and idx + 1 < len(args):
            custom_out = Path(args[idx + 1])
            idx += 1
        idx += 1

    if not target_fmt:
        print("[-] Target format required: specify --to <gif|mp3|mp4|wav|png|jpg|pdf|etc.>")
        return 1

    # Determine default destination
    if custom_out:
        if custom_out.is_dir():
            out_path = custom_out / f"{input_file.stem}.{target_fmt}"
        else:
            out_path = custom_out
    else:
        out_path = input_file.parent / f"{input_file.stem}.{target_fmt}"

    print(f"\n[+] Input  : {input_file.name}")
    print(f"[+] Target : {target_fmt.upper()}")
    print(f"[+] Output : {out_path}")

    def _progress(pct: int, msg: str):
        print(f"  [{pct:>3}%] {msg}")

    try:
        in_suffix = input_file.suffix.lower()
        if target_fmt == "gif":
            convert_video_to_gif(input_file, out_path, fps=fps, height=height, colors=colors, progress_callback=_progress)
        elif target_fmt == "pdf" and in_suffix in (".txt", ".md", ".csv", ".json", ".log", ".py", ".html", ".toml", ".yaml", ".yml", ".ini", ".cfg", ".sh", ".bat", ".rst"):
            convert_text_to_pdf(input_file, out_path, progress_callback=_progress)
        elif target_fmt in ("mp3", "aac", "wav", "flac", "ogg", "m4a", "opus"):
            if in_suffix in (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus", ".wma"):
                convert_audio_to_audio(input_file, out_path, audio_format=target_fmt, progress_callback=_progress)
            else:
                convert_video_to_audio(input_file, out_path, audio_format=target_fmt, progress_callback=_progress)
        elif in_suffix == ".gif" and target_fmt == "mp4":
            convert_gif_to_mp4(input_file, out_path, progress_callback=_progress)
        elif target_fmt in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
            convert_image(input_file, out_path, progress_callback=_progress)
        elif target_fmt == "mp4":
            remux_or_transcode_video(input_file, out_path, progress_callback=_progress)
        else:
            print(f"[-] Unsupported conversion: {in_suffix} -> {target_fmt}")
            return 1

        print(f"\n[✓] Conversion successful: {out_path}\n")
        return 0
    except Exception as e:
        print(f"\n[-] Conversion failed: {e}\n")
        return 1


def run_cli_comic(args: list) -> int:
    """Execute comic/gallery scraper from CLI arguments."""
    from .comic_scraper import scrape_and_download_comic
    from .utils import get_download_dir

    if not args:
        print("[-] Usage: video comic <url_or_html_file> [--pdf] [--cbz] [--cookies <cookies.txt>] [--out <dir>]")
        return 1

    source = args[0]
    auto_format = None
    custom_out = None
    cookie_file = None
    respect_robots = False

    idx = 1
    while idx < len(args):
        a = args[idx]
        if a == "--pdf":
            auto_format = "pdf"
        elif a == "--cbz":
            auto_format = "cbz"
        elif a in ("--cookies", "--cookie-file") and idx + 1 < len(args):
            cookie_file = Path(args[idx + 1])
            idx += 1
        elif a == "--respect-robots":
            respect_robots = True
        elif a == "--out" and idx + 1 < len(args):
            custom_out = Path(args[idx + 1])
            idx += 1
        idx += 1

    print(f"\n[+] Comic / Gallery Source: {source}")
    if auto_format:
        print(f"[+] Auto-pack Target: {auto_format.upper()}")
    if cookie_file:
        print(f"[+] Cookie File: {cookie_file}")

    def _progress(pct: int, msg: str):
        print(f"  [{pct:>3}%] {msg}")

    try:
        result_path = scrape_and_download_comic(
            source=source,
            output_base_dir=custom_out,
            auto_format=auto_format,
            cookie_file=cookie_file,
            respect_robots=respect_robots,
            progress_callback=_progress,
        )
        print(f"\n[✓] Scraping complete! Output: {result_path}\n")
        return 0
    except Exception as e:
        print(f"\n[-] Comic extraction failed: {e}\n")
        return 1


def run_cli_ocr(args: list) -> int:
    """Execute OCR image-to-text extraction from CLI arguments."""
    from .ocr import run_ocr

    if not args:
        print("[-] Usage: video ocr <image_or_folder> [--lang <code, default: eng>] [--separate] [--out <dir>]")
        return 1

    target = args[0]
    lang = "eng"
    combine_output = True
    custom_out = None

    idx = 1
    while idx < len(args):
        a = args[idx]
        if a == "--lang" and idx + 1 < len(args):
            lang = args[idx + 1]
            idx += 1
        elif a.startswith("--lang="):
            lang = a.split("=", 1)[1]
        elif a in ("--separate", "--no-combine"):
            combine_output = False
        elif a == "--out" and idx + 1 < len(args):
            custom_out = Path(args[idx + 1])
            idx += 1
        idx += 1

    print(f"\n[+] OCR Target: {target}")
    print(f"[+] Language  : {lang}")
    print(f"[+] Combined  : {combine_output}")

    def _progress(pct: int, msg: str):
        print(f"  [{pct:>3}%] {msg}")

    try:
        ok, out_path, preview = run_ocr(
            target=target,
            output_dir=custom_out,
            lang=lang,
            combine_output=combine_output,
            progress_callback=_progress,
        )
        print(f"\n[✓] OCR finished successfully! Saved to: {out_path}\n")
        if preview:
            print("--- Extracted Text Preview ---")
            print(preview[:400] + ("\n..." if len(preview) > 400 else ""))
            print("------------------------------\n")
        return 0
    except Exception as e:
        print(f"\n[-] OCR extraction failed: {e}\n")
        return 1


def run_cli_preview(args: list) -> int:
    """Launch instant web browser media player / stream previewer."""
    from .previewer import launch_web_previewer

    target_url = args[0] if args else None
    print(f"\n[+] Launching Video Extractor Web Previewer...")
    if target_url:
        print(f"[+] Target Stream / Video: {target_url}")

    ok = launch_web_previewer(target_url)
    if ok:
        print(f"[✓] Previewer launched in browser.\n")
        return 0
    else:
        print(f"[-] Could not open web browser previewer.\n")
        return 1


def run_cli_pack(args: list) -> int:
    """Execute image folder packaging into PDF or CBZ from CLI arguments."""
    from .packager import images_to_pdf, images_to_cbz, batch_pack_folders
    from .utils import get_download_dir

    if not args:
        print("[-] Usage: video pack <folder> --to <pdf|cbz> [--recurse] [--out <dir>]")
        return 1

    folder = Path(args[0]).resolve()
    if not folder.is_dir():
        print(f"[-] Folder not found: {folder}")
        return 1

    target_fmt = "pdf"
    recurse = False
    custom_out = None

    idx = 1
    while idx < len(args):
        a = args[idx]
        if a == "--to" and idx + 1 < len(args):
            target_fmt = args[idx + 1].lower().lstrip(".")
            idx += 1
        elif a == "--recurse":
            recurse = True
        elif a == "--out" and idx + 1 < len(args):
            custom_out = Path(args[idx + 1])
            idx += 1
        idx += 1

    print(f"\n[+] Packaging Folder: {folder}")
    print(f"[+] Output Format   : {target_fmt.upper()}")
    print(f"[+] Recursive Mode  : {recurse}")

    def _progress(pct: int, msg: str):
        print(f"  [{pct:>3}%] {msg}")

    try:
        out_dir = custom_out or folder.parent
        out_dir.mkdir(parents=True, exist_ok=True)

        if recurse:
            created = batch_pack_folders(folder, out_dir, format_type=target_fmt, recurse=True, progress_callback=_progress)
            print(f"\n[✓] Pack complete! Created {len(created)} {target_fmt.upper()} files in: {out_dir}\n")
        else:
            out_file = out_dir / f"{folder.name}.{target_fmt}"
            if target_fmt == "cbz":
                ok, count = images_to_cbz(folder, out_file, progress_callback=_progress)
            else:
                ok, count = images_to_pdf(folder, out_file, progress_callback=_progress)

            if ok:
                print(f"\n[✓] Pack complete ({count} pages): {out_file}\n")
            else:
                print(f"[-] No valid images found to pack in: {folder}")
                return 1

        return 0
    except Exception as e:
        print(f"\n[-] Packaging failed: {e}\n")
        return 1


def show_version():
    print(f"Video Extractor v{get_version()}")


def show_history():
    import json
    history_file = get_config_dir() / "history.json"

    if not history_file.exists():
        print()
        print("[!] No download history yet.")
        print()
        return

    try:
        history = json.loads(
            history_file.read_text(
                encoding="utf-8"
            )
        )
    except Exception:
        print("[!] Could not read history.")
        return

    if not history:
        print()
        print("[!] No download history yet.")
        print()
        return

    print()
    print("=" * 60)
    print("                 DOWNLOAD HISTORY")
    print("=" * 60)

    for index, item in enumerate(
        reversed(history),
        1
    ):
        print()
        print(f"[{index}]")
        print(f"URL       : {item.get('url', 'unknown')}")
        print(f"Platform  : {item.get('platform', 'unknown')}")
        print(f"Engine    : {item.get('engine', 'unknown')}")
        if item.get("race_duration_ms") is not None:
            print(f"Race Time : {item['race_duration_ms']} ms")
        if item.get("quality"):
            print(f"Quality   : {item['quality']}")
        if item.get("title"):
            print(f"Title     : {item['title']}")
        if item.get("output"):
            print(f"File      : {item['output']}")

    print()
    print("=" * 60)
    print()


def run_update():

    import subprocess

    updater = (
        Path.home()
        / "video-extractor"
        / "scripts"
        / "update.sh"
    )

    if not updater.exists():
        print("[!] Update script not found.")
        return 1

    return subprocess.call(
        [str(updater)]
    )



def main():

    import sys

    config = load_config()

    args = sys.argv[1:]

    # ========================================================
    # NO ARGUMENTS / INTERACTIVE MENU
    # ========================================================

    if not args:
        if sys.stdin.isatty():
            from .menu import run_interactive_menu
            return run_interactive_menu()

        show_help()
        return 0

    if args[0] in (
        "--menu",
        "-m",
        "menu"
    ):
        from .menu import run_interactive_menu
        return run_interactive_menu()

    # ========================================================
    # HELP
    # ========================================================

    if args[0] in (
        "--help",
        "-h",
        "help"
    ):

        show_help()

        return 0

    # ========================================================
    # VERSION
    # ========================================================

    if args[0] in (
        "--version",
        "-v",
        "version"
    ):

        show_version()

        return 0

    # ========================================================
    # HISTORY
    # ========================================================

    if args[0] in (
        "--history",
        "-H"
    ):

        show_history()

        return 0

    # ========================================================
    # CLEAN
    # ========================================================

    if args[0] in (
        "--clean",
        "clean"
    ):

        return clean_downloads()

    # ========================================================
    # OPEN
    # ========================================================

    if args[0] in (
        "--open",
        "open"
    ):

        return open_video_picker()

    # ========================================================
    # UPDATE
    # ========================================================

    if args[0] in (
        "--update",
        "update"
    ):

        return run_update()

    # ========================================================
    # CONVERT
    # ========================================================

    if args[0] in (
        "--convert",
        "convert"
    ):
        return run_cli_convert(args[1:])

    # ========================================================
    # COMIC / IMAGE GALLERY SCRAPER
    # ========================================================

    if args[0] in (
        "--comic",
        "comic"
    ):
        return run_cli_comic(args[1:])

    # ========================================================
    # PACK (IMAGES TO PDF / CBZ)
    # ========================================================

    if args[0] in (
        "--pack",
        "pack"
    ):
        return run_cli_pack(args[1:])

    # ========================================================
    # OCR (IMAGE TO TEXT)
    # ========================================================

    if args[0] in (
        "--ocr",
        "ocr"
    ):
        return run_cli_ocr(args[1:])

    # ========================================================
    # PREVIEW (WEB PREVIEWER)
    # ========================================================

    if args[0] in (
        "--preview",
        "preview"
    ):
        return run_cli_preview(args[1:])

    # ========================================================
    # PARSE OPTIONS
    # ========================================================

    no_open = False
    auto_open_flag = None
    no_browser = False
    no_ytdlp = False
    no_static = False
    no_scrapling = False
    prefer_gui = None
    race_timeout = None
    browser_grace = None
    confidence_threshold = None
    requested_quality = None
    conflict_policy = None
    url = None

    index = 0

    while index < len(args):

        arg = args[index]

        if arg == "--replace":
            conflict_policy = "replace"

        elif arg == "--keep-both":
            conflict_policy = "keep_both"

        elif arg == "--skip-existing":
            conflict_policy = "skip"

        elif arg == "--auto-open":
            auto_open_flag = True

        elif arg == "--no-open":
            auto_open_flag = False
            no_open = True

        elif arg == "--no-browser":
            no_browser = True

        elif arg == "--no-ytdlp":
            no_ytdlp = True

        elif arg == "--no-static":
            no_static = True

        elif arg == "--no-scrapling":
            no_scrapling = True

        elif arg in ("--no-terminals", "--headless-race"):
            prefer_gui = False

        elif arg == "--spawn-terminals":
            prefer_gui = True

        elif arg == "--race-timeout":
            if index + 1 >= len(args):
                print("[-] --race-timeout requires a number of seconds.")
                return 1
            try:
                race_timeout = float(args[index + 1])
            except ValueError:
                print("[-] --race-timeout must be a valid number.")
                return 1
            index += 1

        elif arg.startswith("--race-timeout="):
            try:
                race_timeout = float(arg.split("=", 1)[1])
            except ValueError:
                print("[-] --race-timeout must be a valid number.")
                return 1

        elif arg == "--browser-grace":
            if index + 1 >= len(args):
                print("[-] --browser-grace requires a number of seconds.")
                return 1
            try:
                browser_grace = float(args[index + 1])
            except ValueError:
                print("[-] --browser-grace must be a valid number.")
                return 1
            index += 1

        elif arg.startswith("--browser-grace="):
            try:
                browser_grace = float(arg.split("=", 1)[1])
            except ValueError:
                print("[-] --browser-grace must be a valid number.")
                return 1

        elif arg == "--confidence":
            if index + 1 >= len(args):
                print("[-] --confidence requires an integer score.")
                return 1
            try:
                confidence_threshold = int(args[index + 1])
            except ValueError:
                print("[-] --confidence must be an integer.")
                return 1
            index += 1

        elif arg.startswith("--confidence="):
            try:
                confidence_threshold = int(arg.split("=", 1)[1])
            except ValueError:
                print("[-] --confidence must be an integer.")
                return 1

        elif arg == "--quality":
            if index + 1 >= len(args):
                print("[-] --quality requires a value such as 1080p.")
                return 1
            requested_quality = args[index + 1]
            index += 1

        elif arg.startswith("--quality="):
            requested_quality = arg.split("=", 1)[1]

        elif arg.startswith("-"):
            print(f"[-] Unknown option: {arg}")
            print("    Use 'video --help'.")
            return 1

        elif url is None:
            url = arg

        else:
            print("[-] Multiple URLs supplied.")
            return 1

        index += 1

    # ========================================================
    # URL VALIDATION
    # ========================================================

    if not url:

        show_help()

        return 1

    if not valid_url(url):

        print()
        print(
            "[-] Invalid URL."
        )
        print(
            "    Expected http:// or https://"
        )
        print()

        return 1

    # ========================================================
    # ROUTE URL
    # ========================================================

    from .router import identify
    route = identify(url)

    print()
    print("=" * 60)
    print("                 VIDEO EXTRACTOR")
    print("=" * 60)
    print()

    print(
        f"  URL      : {url}"
    )

    print(
        f"  Platform : {route.platform}"
    )

    print(
        f"  Type     : {route.media_type}"
    )

    print()

    # ========================================================
    # CONCURRENT MULTI-AGENT EXTRACTION RACE
    # ========================================================

    from .race_controller import ExtractionRaceController
    from .downloader import download

    controller = ExtractionRaceController(
        url=url,
        requested_quality=requested_quality,
        timeout=race_timeout,
        confidence_threshold=confidence_threshold,
        no_browser=no_browser,
        no_ytdlp=no_ytdlp,
        no_static=no_static,
        no_scrapling=no_scrapling,
        prefer_gui=prefer_gui,
        browser_grace_seconds=browser_grace,
    )

    race_result = controller.run_race()

    if race_result.candidate:
        winning_candidate = race_result.candidate
        print()
        print(f"[+] Downloading media from winner [{race_result.winner_engine}]...")

        try:
            output = download(
                winning_candidate,
                filename=winning_candidate.metadata.get("title", "video"),
                requested_quality=requested_quality,
                conflict_policy=conflict_policy,
            )

            if output is None:
                return 0

            write_history({
                "url": url,
                "platform": route.platform,
                "engine": race_result.winner_engine,
                "quality": requested_quality,
                "output": str(output) if output else None,
                "race_duration_ms": race_result.duration_ms,
            })

            auto_open_cfg = config.get("auto_open", True)
            should_open = auto_open_flag if auto_open_flag is not None else (auto_open_cfg and not no_open)
            if should_open:
                open_downloaded_video(output)

            return 0

        except Exception as dl_error:
            print(f"\n[-] Download failed: {dl_error}", file=sys.stderr)
            return 1

    # ========================================================
    # FAILURE
    # ========================================================

    print()
    print("  ✗ No downloadable media found.")
    print()

    return 2


if __name__ == "__main__":

    try:

        sys.exit(
            main()
        )

    except KeyboardInterrupt:

        print(
            "\n  ! Cancelled."
        )

        sys.exit(130)
