import os
import shutil
import subprocess


from .utils import get_download_dir


def command_exists(command):
    return shutil.which(command) is not None


def ensure_environment():

    if not command_exists("ffmpeg"):
        raise RuntimeError(
            "FFmpeg is not installed."
        )

    download_dir = get_download_dir()
    os.makedirs(
        str(download_dir),
        exist_ok=True,
    )


def safe_filename(name):

    if not name:
        return "video"

    invalid = '<>:"/\\|?*'

    for char in invalid:
        name = name.replace(char, "_")

    return name.strip() or "video"


def download(candidate, filename="video", requested_quality=None):

    ensure_environment()

    # If the candidate was extracted by yt-dlp, use yt-dlp download engine with ffmpeg muxing
    if candidate.source == "ytdlp" or candidate.metadata.get("engine") == "ytdlp":
        orig_url = candidate.metadata.get("original_url") or candidate.url
        try:
            from .site_extractor import download as ytdlp_download
        except (ImportError, ValueError):
            from video_downloader.site_extractor import download as ytdlp_download
        success = ytdlp_download(orig_url, requested_quality)
        if success:
            download_dir = get_download_dir()
            title = candidate.metadata.get("title") or filename
            target = download_dir / f"{safe_filename(title)}.mp4"
            if target.is_file():
                return str(target)
            video_files = [p for p in download_dir.glob("*.mp4") if p.is_file()]
            if video_files:
                latest = max(video_files, key=lambda p: p.stat().st_mtime)
                return str(latest)
            return str(target)
        else:
            raise RuntimeError("yt-dlp extraction download failed.")

    extension = ".mp4"

    if candidate.extension:
        if candidate.extension in (
            ".mp4",
            ".webm",
            ".mkv",
        ):
            extension = ".mp4"

    output_title = candidate.metadata.get("title") or filename
    output = os.path.join(
        str(get_download_dir()),
        safe_filename(output_title) + extension,
    )

    print()
    print("[+] Downloader (FFmpeg)")
    print(f"[+] Type : {candidate.label}")
    print(f"[+] Source: {candidate.source}")
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
