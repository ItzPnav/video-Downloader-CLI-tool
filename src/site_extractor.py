import json
import shutil
import subprocess
from pathlib import Path

from progress import DownloadProgress


DOWNLOAD_DIR = Path(
    "/sdcard/Download"
)


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
    requested_quality=None
):

    if not available():

        print(
            "[!] yt-dlp is not installed."
        )

        return False

    DOWNLOAD_DIR.mkdir(
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

    print()
    print(
        f"  ▶ {title}"
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

    output_template = str(
        DOWNLOAD_DIR
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

    process = subprocess.Popen(
        command,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1
    )

    last_downloaded = 0

    try:

        for raw_line in process.stdout:

            line = raw_line.strip()

            if not line.startswith(
                "download:"
            ):
                continue

            try:

                values = line[
                    len("download:"):
                ].split("|")

                downloaded = int(
                    values[0]
                )

                total = (
                    int(values[1])
                    if values[1]
                    and values[1] != "NA"
                    else None
                )

                speed = None

                if values[2] not in (
                    "",
                    "NA",
                    "None"
                ):

                    try:
                        speed = float(
                            values[2]
                        )
                    except ValueError:
                        pass

                eta = None

                if values[3] not in (
                    "",
                    "NA",
                    "None"
                ):

                    try:
                        eta = int(
                            float(values[3])
                        )
                    except ValueError:
                        pass

                last_downloaded = downloaded

                progress.render(
                    downloaded,
                    total,
                    speed,
                    eta
                )

            except Exception:
                continue

        return_code = process.wait()

    except KeyboardInterrupt:

        print()
        print(
            "\n  ! Download cancelled."
        )

        process.terminate()

        return False

    if return_code != 0:

        print()
        print(
            "  ✗ Download failed."
        )

        return False

    progress.complete(
        last_downloaded
    )

    return True
