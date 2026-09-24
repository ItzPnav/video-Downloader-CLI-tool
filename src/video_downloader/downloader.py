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

