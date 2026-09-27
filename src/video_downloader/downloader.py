import os
import shutil
import subprocess


from pathlib import Path
from .utils import get_download_dir
from .conflict_resolver import resolve_file_conflict


def find_ffmpeg() -> str | None:
    """
    Locate the FFmpeg executable across PATH, OS registries, and standard package locations.
    If discovered outside the current PATH, injects the directory into os.environ['PATH']
    so subsequent child processes (yt-dlp, ffmpeg) find it automatically.
    """
    import sys
    exe = shutil.which("ffmpeg") or (shutil.which("ffmpeg.exe") if sys.platform == "win32" else None)
    if exe:
        return exe

    # Windows fallback: Registry and common package manager paths
    if sys.platform == "win32":
        try:
            import winreg
            candidate_dirs = []
            for hkey, subkey in [
                (winreg.HKEY_CURRENT_USER, r"Environment"),
                (winreg.HKEY_LOCAL_MACHINE, r"SYSTEM\CurrentControlSet\Control\Session Manager\Environment"),
            ]:
                try:
                    with winreg.OpenKey(hkey, subkey) as key:
                        val, _ = winreg.QueryValueEx(key, "Path")
                        candidate_dirs.extend(val.split(";"))
                except Exception:
                    pass

            for d in candidate_dirs:
                if not d.strip():
                    continue
                p = Path(d.strip()) / "ffmpeg.exe"
                if p.is_file():
                    os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
                    return str(p)
        except Exception:
            pass

        # Check standard WinGet, Chocolatey, Scoop, and Program Files locations
        local_app_data = os.environ.get("LOCALAPPDATA", "")
        search_paths = []
        if local_app_data:
            search_paths.append(Path(local_app_data) / "Microsoft" / "WinGet" / "Links" / "ffmpeg.exe")
            winget_pkgs = Path(local_app_data) / "Microsoft" / "WinGet" / "Packages"
            if winget_pkgs.exists():
                try:
                    for match in winget_pkgs.glob("**/ffmpeg.exe"):
                        if match.is_file():
                            search_paths.append(match)
                except Exception:
                    pass

        search_paths.extend([
            Path.home() / "scoop" / "shims" / "ffmpeg.exe",
            Path(os.environ.get("SystemDrive", "C:")) / "ProgramData" / "chocolatey" / "bin" / "ffmpeg.exe",
        ])

        program_files = [os.environ.get("ProgramFiles", "C:\\Program Files"), os.environ.get("ProgramFiles(x86)", "C:\\Program Files (x86)")]
        for pf in program_files:
            if pf and Path(pf).exists():
                try:
                    for ffmpeg_dir in Path(pf).glob("ffmpeg*"):
                        search_paths.append(ffmpeg_dir / "bin" / "ffmpeg.exe")
                        search_paths.append(ffmpeg_dir / "ffmpeg.exe")
                except Exception:
                    pass

        for p in search_paths:
            if p.is_file():
                os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
                return str(p)

    else:
        # Linux / Termux / macOS fallback locations
        unix_paths = [
            Path("/data/data/com.termux/files/usr/bin/ffmpeg"),
            Path("/usr/local/bin/ffmpeg"),
            Path("/usr/bin/ffmpeg"),
            Path("/opt/homebrew/bin/ffmpeg"),
            Path("/usr/local/opt/ffmpeg/bin/ffmpeg"),
        ]
        for p in unix_paths:
            if p.is_file() and os.access(p, os.X_OK):
                os.environ["PATH"] = str(p.parent) + os.pathsep + os.environ.get("PATH", "")
                return str(p)

    return None


def command_exists(command):
    if command == "ffmpeg":
        return find_ffmpeg() is not None
    return shutil.which(command) is not None


def ensure_environment():
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        import sys
        if sys.platform == "win32":
            hint = (
                "FFmpeg is not installed or not in PATH.\n"
                "    To install it on Windows, run:\n"
                "        winget install Gyan.FFmpeg\n"
                "    If already installed, restart your PowerShell/Terminal window so PATH is reloaded."
            )
        elif "com.termux" in os.environ.get("PREFIX", ""):
            hint = "FFmpeg is not installed. Please run: pkg install ffmpeg"
        elif sys.platform == "darwin":
            hint = "FFmpeg is not installed. Please run: brew install ffmpeg"
        else:
            hint = "FFmpeg is not installed. Please install it using: sudo apt install ffmpeg"

        raise RuntimeError(hint)

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


def download(candidate, filename="video", requested_quality=None, conflict_policy=None):

    ensure_environment()
    download_dir = Path(get_download_dir())

    extension = ".mp4"
    if candidate.extension:
        if candidate.extension in (
            ".mp4",
            ".webm",
            ".mkv",
        ):
            extension = candidate.extension

    output_title = candidate.metadata.get("title") or filename
    target_path = download_dir / f"{safe_filename(output_title)}{extension}"

    # Resolve filename collisions (Replace / Keep Both / Skip / Compare Info)
    resolved_path = resolve_file_conflict(
        target_path,
        candidate=candidate,
        requested_quality=requested_quality,
        conflict_policy=conflict_policy,
    )

    if resolved_path is None:
        print("\n[!] Download skipped.")
        return None

    # If the candidate was extracted by yt-dlp, use yt-dlp download engine with ffmpeg muxing
    if candidate.source == "ytdlp" or candidate.metadata.get("engine") == "ytdlp":
        orig_url = candidate.metadata.get("original_url") or candidate.url
        try:
            from .site_extractor import download as ytdlp_download
        except (ImportError, ValueError):
            from video_downloader.site_extractor import download as ytdlp_download

        # If replacing, unlink existing file to prevent yt-dlp from skipping
        if resolved_path.exists() and resolved_path == target_path:
            try:
                resolved_path.unlink()
            except Exception:
                pass

        if resolved_path != target_path:
            success = ytdlp_download(orig_url, requested_quality, output_path=resolved_path)
        else:
            success = ytdlp_download(orig_url, requested_quality)
        if success:
            if resolved_path.is_file():
                return str(resolved_path)
            video_files = [p for p in download_dir.glob("*.mp4") if p.is_file()]
            if video_files:
                latest = max(video_files, key=lambda p: p.stat().st_mtime)
                return str(latest)
            return str(resolved_path)
        else:
            raise RuntimeError("yt-dlp extraction download failed.")

    output = str(resolved_path)

    # Check for direct video stream acceleration via parallel byte-ranges
    url_lower = candidate.url.lower().split("?")[0]
    is_direct_video = any(url_lower.endswith(ext) for ext in (".mp4", ".webm", ".mkv", ".mov", ".avi", ".ts"))

    if is_direct_video:
        try:
            if download_parallel_stream(candidate.url, resolved_path):
                print()
                print("========================================")
                print("[SUCCESS] Parallel download complete")
                print("========================================")
                print(output)
                return output
        except Exception as parallel_err:
            print(f"[!] Parallel download fallback to FFmpeg: {parallel_err}")

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


def download_parallel_stream(url: str, dest_path: Path, threads: int = 4, timeout: int = 20) -> bool:
    """
    Attempt high-speed parallel chunk download using HTTP Range bytes headers.
    Returns True if successfully downloaded and assembled, False if server does not support ranges.
    """
    import threading
    from concurrent.futures import ThreadPoolExecutor, as_completed
    import requests

    headers = {
        "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36"
    }

    try:
        head_resp = requests.head(url, headers=headers, allow_redirects=True, timeout=timeout)
        content_length = head_resp.headers.get("Content-Length")
        accept_ranges = head_resp.headers.get("Accept-Ranges", "").lower()

        if not content_length or not content_length.isdigit() or "bytes" not in accept_ranges:
            return False

        total_bytes = int(content_length)
        # Only use parallel download if file is larger than 2MB
        if total_bytes < 2 * 1024 * 1024:
            return False

        print(f"[+] Accelerated Parallel Downloader ({threads} threads, {total_bytes / (1024*1024):.1f} MB)")
        part_size = total_bytes // threads
        ranges = []
        for i in range(threads):
            start = i * part_size
            end = (start + part_size - 1) if i < threads - 1 else total_bytes - 1
            ranges.append((start, end))

        temp_parts = []
        dest_path = Path(dest_path)
        dest_path.parent.mkdir(parents=True, exist_ok=True)
        part_all = dest_path.with_suffix(dest_path.suffix + ".partall")

        def _fetch_range(idx: int, start: int, end: int) -> Path:
            part_file = dest_path.with_suffix(f"{dest_path.suffix}.part{idx}")
            temp_parts.append(part_file)
            req_h = dict(headers)
            req_h["Range"] = f"bytes={start}-{end}"
            with requests.get(url, headers=req_h, stream=True, timeout=timeout) as r:
                r.raise_for_status()
                with open(part_file, "wb") as pf:
                    for chunk in r.iter_content(chunk_size=64 * 1024):
                        if chunk:
                            pf.write(chunk)
            return part_file

        with ThreadPoolExecutor(max_workers=threads) as executor:
            futures = {executor.submit(_fetch_range, i, s, e): i for i, (s, e) in enumerate(ranges)}
            for fut in as_completed(futures):
                fut.result()

        # Combine parts into final file
        with open(part_all, "wb") as out_f:
            for i in range(threads):
                p_file = dest_path.with_suffix(f"{dest_path.suffix}.part{i}")
                with open(p_file, "rb") as in_f:
                    shutil.copyfileobj(in_f, out_f)

        if part_all.exists() and part_all.stat().st_size == total_bytes:
            os.replace(part_all, dest_path)
            for p_file in temp_parts:
                try:
                    p_file.unlink(missing_ok=True)
                except Exception:
                    pass
            return True

    except Exception:
        # Cleanup temporary files on failure
        for p in dest_path.parent.glob(f"{dest_path.name}.part*"):
            try:
                p.unlink(missing_ok=True)
            except Exception:
                pass
        return False

    return False


