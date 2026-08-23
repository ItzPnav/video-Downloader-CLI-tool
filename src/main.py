import sys
from pathlib import Path
from urllib.parse import urlparse

from utils import (
    load_config,
    get_version,
    print_banner,
    print_step,
    write_history,
    safe_filename,
)

from urllib.parse import urlparse

from site_extractor import (
    download as ytdlp_download,
    extract_info,
)

from static_scanner import StaticScanner
from selector import choose
from router import identify, describe
from progress import Spinner
from browser_scanner import BrowserScanner
from downloader import download


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

    download_dir = Path(
        "/sdcard/Download"
    )

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



def open_downloaded_video(output=None):

    import subprocess
    from pathlib import Path

    if output:
        path = Path(output)

        if path.exists():
            print()
            print("[+] Opening video...")
            subprocess.run(
                ["termux-open", str(path)],
                check=False
            )
            return True

    download_dir = Path(
        "/sdcard/Download"
    )

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

    subprocess.run(
        ["termux-open", str(latest)],
        check=False
    )

    return True



def open_video_picker():

    import subprocess
    from pathlib import Path

    download_dir = Path(
        "/sdcard/Download"
    )

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

        subprocess.run(
            [
                "termux-open",
                str(selected)
            ],
            check=False
        )

        return 0


def show_help():

    print("=" * 60)
    print("                 VIDEO EXTRACTOR")
    print("=" * 60)
    print()
    print(f"Version: {get_version()}")
    print()
    print("Usage:")
    print('  video "URL"')
    print()
    print("Commands:")
    print("  video                    Show this help")
    print('  video "URL"              Extract and download')
    print("  video --help             Show help")
    print("  video --version          Show version")
    print("  video --history          Show download history")
    print("  video --update           Update extractor")
    print("  video --clean            Delete downloaded videos")
    print("  video --open             Choose and play a video")
    print()
    print("Options:")
    print("  --no-open                Don't open video after download")
    print("  --no-browser             Skip Chromium fallback")
    print("  --quality 1080p          Request video quality")
    print()
    print("Output:")
    print("  /sdcard/Download/")
    print()
    print("=" * 60)
    print()


def show_version():

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
        print(f"URL    : {item.get('url', 'unknown')}")
        print(f"Engine : {item.get('engine', 'unknown')}")

        if item.get("title"):
            print(f"Title  : {item['title']}")

        if item.get("output"):
            print(f"File   : {item['output']}")

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
    # NO ARGUMENTS
    # ========================================================

    if not args:

        show_help()

        return 0

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
    # PARSE OPTIONS
    # ========================================================

    no_open = False
    no_browser = False
    requested_quality = None
    url = None

    index = 0

    while index < len(args):

        arg = args[index]

        if arg == "--no-open":

            no_open = True

        elif arg == "--no-browser":

            no_browser = True

        elif arg == "--quality":

            if index + 1 >= len(args):

                print(
                    "[-] --quality requires "
                    "a value such as 1080p."
                )

                return 1

            requested_quality = (
                args[index + 1]
            )

            index += 1

        elif arg.startswith(
            "--quality="
        ):

            requested_quality = (
                arg.split(
                    "=",
                    1
                )[1]
            )

        elif arg.startswith("-"):

            print(
                f"[-] Unknown option: {arg}"
            )

            print(
                "    Use 'video --help'."
            )

            return 1

        elif url is None:

            url = arg

        else:

            print(
                "[-] Multiple URLs supplied."
            )

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
    # YOUTUBE
    # ========================================================

    if route.platform == "youtube":

        print(
            "  ✓ YouTube extractor selected"
        )

        if requested_quality:

            print(
                f"  ✓ Requested quality: "
                f"{requested_quality}"
            )

        from extractors.youtube import (
            download_video
        )

        success = download_video(
            route,
            requested_quality
        )

        if success:

            write_history({
                "url": url,
                "platform": "youtube",
                "type": route.media_type,
                "quality": requested_quality,
            })

            if not no_open:

                open_downloaded_video()

            return 0

        print(
            "  ! YouTube extractor failed."
        )

    # ========================================================
    # KNOWN SITES
    # ========================================================

    elif route.platform in (
        "tnaflix",
        "vimeo",
        "dailymotion"
    ):

        print(
            f"  ✓ {route.platform.title()} "
            "route selected"
        )

        if requested_quality:

            print(
                f"  ✓ Requested quality: "
                f"{requested_quality}"
            )

        # ----------------------------------------------------
        # First attempt: site-specific yt-dlp support
        # ----------------------------------------------------

        spinner = Spinner(
            "Checking site extractor"
        )

        spinner.start()

        try:

            info = extract_info(
                url
            )

            if info:

                spinner.stop(
                    True,
                    "Media detected"
                )

            else:

                spinner.stop(
                    False,
                    "Site extractor found nothing"
                )

        except Exception as error:

            spinner.stop(
                False,
                "Site extractor failed"
            )

            info = None

            success = ytdlp_download(
                url,
                requested_quality
            )

            if success:

                write_history({
                    "url": url,
                    "platform": route.platform,
                    "engine": "site",
                    "quality": requested_quality,
                })

                if not no_open:

                    open_downloaded_video()

                return 0

        # ----------------------------------------------------
        # Browser fallback
        # ----------------------------------------------------

        if (
            config.get(
                "use_browser",
                True
            )
            and not no_browser
        ):

            spinner = Spinner(
                "Starting browser scanner"
            )

            spinner.start()

            try:

                browser_candidates = (
                    BrowserScanner(
                        url
                    ).scan()
                )

                spinner.stop(
                    True,
                    "Browser scanner finished"
                )

                best = choose(
                    browser_candidates
                )

                if best:

                    print(
                        "  ✓ Browser found media."
                    )

                    output = download(
                        best,
                        "video"
                    )

                    write_history({
                        "url": url,
                        "platform": route.platform,
                        "engine": "browser",
                        "output": str(output),
                    })

                    if not no_open:

                        open_downloaded_video(
                            output
                        )

                    return 0

            except Exception as error:

                print(
                    f"  ! Browser scanner failed: "
                    f"{error}"
                )

    # ========================================================
    # GENERIC
    # ========================================================

    else:

        print(
            "  ✓ Generic URL detected"
        )

        spinner = Spinner(
            "Analyzing generic video"
        )

        spinner.start()

        try:

            info = extract_info(
                url
            )

            spinner.stop(
                True,
                "Analysis complete"
            )

        except Exception:

            spinner.stop(
                False,
                "Analysis failed"
            )

            info = None

        if info:

            print(
                "  ✓ Generic extractor "
                "recognized the page."
            )

            success = ytdlp_download(
                url,
                requested_quality
            )

            if success:

                write_history({
                    "url": url,
                    "platform": "generic",
                    "engine": "yt-dlp",
                    "quality": requested_quality,
                })

                if not no_open:

                    open_downloaded_video()

                return 0

        # ----------------------------------------------------
        # Static scanner
        # ----------------------------------------------------

        if config.get(
            "use_static_scanner",
            True
        ):

            spinner = Spinner(
                "Scanning page"
            )

            spinner.start()

            candidates = []

            try:

                candidates = (
                    StaticScanner(
                        url
                    ).scan()
                )

                spinner.stop(
                    True,
                    "Page scan finished"
                )

            except Exception as error:

                print(
                    f"  ! Static scanner unavailable: "
                    f"{error}"
                )

            best = choose(
                candidates
            )

            if best:

                try:

                    output = download(
                        best,
                        "video"
                    )

                    write_history({
                        "url": url,
                        "platform": "generic",
                        "engine": "static",
                        "output": str(output),
                    })

                    if not no_open:

                        open_downloaded_video(
                            output
                        )

                    return 0

                except Exception as error:

                    print(
                        f"  ! Static download failed: "
                        f"{error}"
                    )

        # ----------------------------------------------------
        # Browser
        # ----------------------------------------------------

        if (
            config.get(
                "use_browser",
                True
            )
            and not no_browser
        ):

            print(
                "  → Running browser network scanner..."
            )

            try:

                browser_candidates = (
                    BrowserScanner(
                        url
                    ).scan()
                )

                best = choose(
                    browser_candidates
                )

                if best:

                    print(
                        "  ✓ Browser found media."
                    )

                    output = download(
                        best,
                        "video"
                    )

                    write_history({
                        "url": url,
                        "platform": "generic",
                        "engine": "browser",
                        "output": str(output),
                    })

                    if not no_open:

                        open_downloaded_video(
                            output
                        )

                    return 0

            except Exception as error:

                print(
                    f"  ! Browser scanner failed: "
                    f"{error}"
                )

    # ========================================================
    # FAILURE
    # ========================================================

    print()
    print(
        "  ✗ No downloadable media found."
    )
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
