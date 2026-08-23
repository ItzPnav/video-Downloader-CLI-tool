import os
import shutil
import subprocess


DOWNLOAD_DIR = "/sdcard/Download"


def command_exists(command):
    return shutil.which(command) is not None


def ensure_environment():

    if not command_exists("ffmpeg"):
        raise RuntimeError(
            "FFmpeg is not installed."
        )

    os.makedirs(
        DOWNLOAD_DIR,
        exist_ok=True,
    )


def safe_filename(name):

    if not name:
        return "video"

    invalid = '<>:"/\\|?*'

    for char in invalid:
        name = name.replace(char, "_")

    return name.strip() or "video"


def download(candidate, filename="video"):

    ensure_environment()

    extension = ".mp4"

    if candidate.extension:
        if candidate.extension in (
            ".mp4",
            ".webm",
            ".mkv",
        ):
            extension = ".mp4"

    output = os.path.join(
        DOWNLOAD_DIR,
        safe_filename(filename) + extension,
    )

    print()
    print("[+] Downloader")
    print(f"[+] Type : {candidate.label}")
    print(f"[+] URL  : {candidate.url}")
    print(f"[+] Save : {output}")
    print()

    command = [
        "ffmpeg",
        "-y",
        "-i",
        candidate.url,
        "-c",
        "copy",
        output,
    ]

    subprocess.run(
        command,
        check=True,
    )

    print()
    print("========================================")
    print("[SUCCESS] Download complete")
    print("========================================")
    print(output)

    return output
