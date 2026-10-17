import os
import json
import shutil
import subprocess
from pathlib import Path

from .progress import DownloadProgress
from .utils import get_download_dir


def get_target_download_dir():
    return get_download_dir()


def available():

    return (
        shutil.which("yt-dlp")
        is not None
    )


def extract_info(url):

    if not available():
        return None

    try:

        result = subprocess.run(
            [
                "yt-dlp",
                "--dump-single-json",
                "--no-warnings",
                "--skip-download",
                url
            ],
            capture_output=True,
            text=True,
            timeout=90
        )

        if result.returncode != 0:
            return None

        return json.loads(
            result.stdout
        )

    except Exception:

        return None


def choose_format(
    info,
    requested_quality=None
):

    formats = info.get(
        "formats",
        []
    )

    if not formats:
        return None

    video_formats = [
        f for f in formats
        if f.get("vcodec") != "none"
        and f.get("height")
    ]

    if not video_formats:
        return None

    if requested_quality:

        try:

            requested_height = int(
                str(requested_quality)
                .lower()
                .replace("p", "")
            )

        except ValueError:

            requested_height = None

        if requested_height:

            exact = [
                f for f in video_formats
                if f.get("height")
                == requested_height
            ]

            if exact:

                return max(
                    exact,
                    key=lambda f: (
                        f.get("fps") or 0,
                        f.get("tbr") or 0
                    )
                )

            suitable = [
                f for f in video_formats
                if f.get("height", 0)
                <= requested_height
            ]

            if suitable:

                return max(
                    suitable,
                    key=lambda f: (
                        f.get("height") or 0,
                        f.get("fps") or 0,
                        f.get("tbr") or 0
                    )
                )

    return max(
        video_formats,
        key=lambda f: (
            f.get("height") or 0,
            f.get("width") or 0,
            f.get("fps") or 0,
            f.get("tbr") or 0
        )
    )


def download(
    url,
    requested_quality=None,
    output_path=None
):

    if not available():

        print(
            "[!] yt-dlp is not installed."
        )

        return False

    download_dir = get_target_download_dir()
    download_dir.mkdir(
        parents=True,
        exist_ok=True
    )

    info = extract_info(url)

    if not info:

        print(
            "[!] yt-dlp could not "
            "identify this URL."
        )

        return False

    title = info.get(
        "title",
        "video"
    )

    display_title = Path(output_path).stem if output_path else title
    display_dir = Path(output_path).parent if output_path else download_dir

    print()
    print(
        f"  ▶ {display_title}"
    )
    print(
        f"    \033[2mFolder: {display_dir}\033[0m"
    )

    if requested_quality:

        selected = choose_format(
            info,
            requested_quality
        )

        if selected:

            requested = str(
                requested_quality
            ).lower().replace(
                "p",
                ""
            )

            actual = selected.get(
                "height",
                "?"
            )

            if str(actual) == requested:

                print(
                    f"  ✓ Quality: {actual}p"
                )

            else:

                print(
                    f"  ! {requested_quality} "
                    f"unavailable → {actual}p"
                )

    if requested_quality:

        try:

            height = int(
                str(requested_quality)
                .lower()
                .replace("p", "")
            )

            format_selector = (
                f"bv*[height={height}]"
                f"+ba/"
                f"bv*[height<={height}]"
                f"+ba/"
                f"bv*+ba/"
                f"b"
            )

        except ValueError:

            format_selector = (
                "bv*+ba/b"
            )

    else:

        format_selector = (
            "bv*+ba/b"
        )

    if output_path:
        output_template = str(output_path)
    else:
        output_template = str(
            download_dir
            / "%(title)s.%(ext)s"
        )

    command = [
        "yt-dlp",

        "--no-playlist",

        "--newline",

        "--progress",

        "--progress-template",
        "download:%(progress.downloaded_bytes)s|%(progress.total_bytes)s|%(progress.speed)s|%(progress.eta)s",

        "-f",
        format_selector,

        "--merge-output-format",
        "mp4",

        "-o",
        output_template,

        url
    ]

    progress = DownloadProgress()
    last_downloaded = 0

    try:
        progress.start()
        env = {**os.environ, "PYTHONUNBUFFERED": "1"}

        process = subprocess.Popen(
            command,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
            bufsize=1,
            env=env,
        )

        for raw_line in process.stdout:
            line = raw_line.strip()
            if not line.startswith("download:"):
                continue

            try:
                values = line[len("download:"):].split("|")
                downloaded = int(values[0])
                total = int(values[1]) if values[1] and values[1] != "NA" else None
                speed = float(values[2]) if values[2] not in ("", "NA", "None") else None
                eta = int(float(values[3])) if values[3] not in ("", "NA", "None") else None
                last_downloaded = downloaded
                progress.update(downloaded, total, speed, eta)
            except Exception:
                continue

        return_code = process.wait()

        if return_code != 0:
            progress.stop()
            print()
            print("  \033[91m✗ Download failed.\033[0m")
            return False

        if last_downloaded == 0:
            if output_path and Path(output_path).is_file():
                last_downloaded = Path(output_path).stat().st_size
            else:
                mp4s = list(download_dir.glob("*.mp4"))
                if mp4s:
                    latest = max(mp4s, key=lambda p: p.stat().st_mtime)
                    last_downloaded = latest.stat().st_size

        progress.complete(last_downloaded if last_downloaded > 0 else None)
        return True

    except KeyboardInterrupt:
        progress.stop()
        print()
        print("\n  ! Download cancelled.")
        try:
            process.terminate()
        except Exception:
            pass
        return False
    except Exception as e:
        progress.stop()
        raise e
    finally:
        progress.stop()
