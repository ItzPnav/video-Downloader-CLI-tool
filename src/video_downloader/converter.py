"""
Media Converter Engine for Video Extractor CLI.
Provides high-performance, cross-platform conversions for Video, GIF, Audio, Images, and Text Documents
using native FFmpeg subprocess pipelines, Pillow, and ReportLab.
Zero heavy GUI dependencies (no Tkinter, PySide6, MoviePy, or PyDub required).
"""

import os
import re
import sys
import json
import time
import shutil
import tempfile
import subprocess
from dataclasses import dataclass
from pathlib import Path
from typing import Callable, Optional, Tuple

from .downloader import find_ffmpeg

# Optional Pillow import for image operations
try:
    from PIL import Image, ImageDraw, ImageFont
    PILLOW_AVAILABLE = True
except ImportError:
    PILLOW_AVAILABLE = False

# Optional ReportLab import for rich PDF generation
try:
    from reportlab.pdfgen import canvas as rl_canvas
    REPORTLAB_AVAILABLE = True
except ImportError:
    REPORTLAB_AVAILABLE = False


_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+(?:\.\d+)?)")

IMAGE_EXTENSIONS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTENSIONS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv", ".ts", ".m4v", ".wmv"}
AUDIO_EXTENSIONS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac", ".opus", ".wma"}
TEXT_EXTENSIONS = {".txt", ".md", ".csv", ".json", ".log", ".py", ".html"}


def find_ffprobe() -> Optional[str]:
    """Locate the FFprobe executable across PATH and FFmpeg binary sibling directories."""
    ffmpeg_exe = find_ffmpeg()
    if ffmpeg_exe:
        if Path(ffmpeg_exe).is_file():
            candidate = Path(ffmpeg_exe).parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if candidate.is_file():
                return str(candidate)
        elif not shutil.which(ffmpeg_exe):
            # ffmpeg was configured or mocked to a non-existent binary; ffprobe cannot be paired
            return None

    exe = shutil.which("ffprobe") or (shutil.which("ffprobe.exe") if sys.platform == "win32" else None)
    if exe:
        return exe
    return None


def parse_ffmpeg_time(line: str) -> Optional[float]:
    """Extract elapsed seconds from FFmpeg stderr line 'time=HH:MM:SS.ms'."""
    match = _TIME_RE.search(line)
    if not match:
        return None
    hh = int(match.group(1))
    mm = int(match.group(2))
    ss = float(match.group(3))
    return hh * 3600 + mm * 60 + ss


def get_media_duration(input_path: str | Path) -> float:
    """Determine media duration in seconds using ffprobe or ffmpeg header parsing."""
    ffprobe_exe = find_ffprobe()
    if ffprobe_exe:
        try:
            cmd = [
                ffprobe_exe,
                "-v", "error",
                "-show_entries", "format=duration",
                "-of", "default=noprint_wrappers=1:nokey=1",
                str(input_path),
            ]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            if res.returncode == 0 and res.stdout.strip():
                val = _safe_float(res.stdout.strip())
                if val > 0:
                    return val
        except Exception:
            pass

    # Fallback to ffmpeg -i info parse
    ffmpeg_exe = find_ffmpeg()
    if ffmpeg_exe:
        try:
            cmd = [ffmpeg_exe, "-i", str(input_path)]
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
            dur_match = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", res.stderr)
            if dur_match:
                hh, mm, ss = int(dur_match.group(1)), int(dur_match.group(2)), float(dur_match.group(3))
                return hh * 3600 + mm * 60 + ss
        except Exception:
            pass

    return 0.0


def convert_video_to_gif(
    input_path: str | Path,
    output_path: str | Path,
    fps: int = 30,
    height: int = 504,
    colors: int = 256,
    max_duration: float = 60.0,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """
    Convert a video file to a high-quality animated GIF using two-pass FFmpeg palette generation.
    """
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        raise RuntimeError("FFmpeg is required for video to GIF conversion. Please install FFmpeg.")

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    fps = min(max(1, int(fps)), 60)
    height = max(120, int(height))
    colors = 256 if colors not in (64, 128, 256) else colors

    total_duration = get_media_duration(input_path)
    use_duration = min(total_duration if total_duration > 0 else max_duration, max_duration)

    temp_dir = Path(tempfile.gettempdir())
    palette_path = temp_dir / f"palette_{os.getpid()}_{int(time.time()*1000)}.png"

    scale_expr = f"scale=-1:{height}:flags=lanczos"
    vf_palette = f"fps={fps},{scale_expr},palettegen=max_colors={colors}"
    vf_render = f"fps={fps},{scale_expr}"

    cmd_palette = [
        ffmpeg_exe, "-y", "-v", "warning",
        "-i", str(input_path),
        "-t", str(use_duration),
        "-vf", vf_palette,
        str(palette_path),
    ]

    cmd_gif = [
        ffmpeg_exe, "-y", "-v", "warning",
        "-i", str(input_path),
        "-i", str(palette_path),
        "-t", str(use_duration),
        "-filter_complex", f"[0:v]{vf_render}[x];[x][1:v]paletteuse",
        "-loop", "0",
        str(output_path),
    ]

    if progress_callback:
        progress_callback(5, "Generating color palette (Pass 1/2)...")

    # Pass 1: Palette Generation
    p1 = subprocess.run(cmd_palette, capture_output=True, text=True)
    if p1.returncode != 0:
        if palette_path.exists():
            palette_path.unlink(missing_ok=True)
        raise RuntimeError(f"FFmpeg palette generation failed:\n{p1.stderr}")

    if progress_callback:
        progress_callback(20, "Rendering GIF frames (Pass 2/2)...")

    # Pass 2: Render GIF with progress monitoring
    last_pct = 20
    try:
        proc = subprocess.Popen(
            cmd_gif,
            stderr=subprocess.PIPE,
            text=True,
            bufsize=1,
            universal_newlines=True,
        )

        if proc.stderr:
            for raw_line in proc.stderr:
                line = raw_line.strip()
                t = parse_ffmpeg_time(line)
                if t is not None and use_duration > 0:
                    frac = min(max(t / use_duration, 0.0), 1.0)
                    pct = int(20 + frac * 75)
                    if pct > last_pct:
                        last_pct = pct
                        if progress_callback:
                            progress_callback(pct, f"Rendering GIF: {pct}%")

        proc.wait()
        if proc.returncode != 0:
            raise RuntimeError(f"FFmpeg GIF encoding failed with exit code {proc.returncode}")

    finally:
        if palette_path.exists():
            try:
                palette_path.unlink(missing_ok=True)
            except Exception:
                pass

    if progress_callback:
        progress_callback(100, f"Saved: {output_path.name}")

    return output_path


def batch_convert_videos_to_gif(
    folder_path: str | Path,
    output_dir: str | Path,
    fps: int = 30,
    height: int = 504,
    colors: int = 256,
    max_duration: float = 60.0,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> list[Path]:
    """
    Batch convert all video files in a directory to high-quality animated GIFs.
    Returns a list of created GIF file paths.
    """
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder}")

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    videos = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() in VIDEO_EXTENSIONS
    )
    if not videos:
        return []

    created: list[Path] = []
    total = len(videos)

    for idx, video_file in enumerate(videos, 1):
        out_gif = out_dir / f"{video_file.stem}.gif"

        def _item_progress(pct: int, msg: str, _idx=idx, _name=video_file.name):
            if progress_callback:
                overall = int(((_idx - 1) + (pct / 100.0)) / total * 100)
                progress_callback(overall, f"[{_idx}/{total}] {_name}: {msg}")

        res = convert_video_to_gif(
            input_path=video_file,
            output_path=out_gif,
            fps=fps,
            height=height,
            colors=colors,
            max_duration=max_duration,
            progress_callback=_item_progress,
        )
        created.append(res)

    if progress_callback:
        progress_callback(100, f"Converted {len(created)}/{total} video(s) to GIF")

    return created



def convert_video_to_audio(
    input_path: str | Path,
    output_path: str | Path,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """Extract audio from a video file using FFmpeg."""
    return convert_audio_to_audio(
        input_path=input_path,
        output_path=output_path,
        audio_format=audio_format,
        bitrate=bitrate,
        progress_callback=progress_callback,
    )


def convert_audio_to_audio(
    input_path: str | Path,
    output_path: str | Path,
    audio_format: str = "mp3",
    bitrate: str = "320k",
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """Convert or transcode audio between formats (MP3, WAV, FLAC, AAC, OGG, M4A, Opus) using FFmpeg."""
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        raise RuntimeError("FFmpeg is required for audio conversions. Please install FFmpeg.")

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    audio_format = audio_format.lower().lstrip(".")
    codec_map = {
        "mp3": ["-c:a", "libmp3lame", "-b:a", bitrate],
        "aac": ["-c:a", "aac", "-b:a", bitrate],
        "m4a": ["-c:a", "aac", "-b:a", bitrate],
        "flac": ["-c:a", "flac"],
        "wav": ["-c:a", "pcm_s16le"],
        "ogg": ["-c:a", "libvorbis", "-q:a", "6"],
        "opus": ["-c:a", "libopus", "-b:a", "128k"],
    }
    codec_args = codec_map.get(audio_format, ["-c:a", "copy"])

    cmd = [
        ffmpeg_exe, "-y", "-v", "warning",
        "-i", str(input_path),
        "-vn",
        *codec_args,
        str(output_path),
    ]

    total_duration = get_media_duration(input_path)
    if progress_callback:
        progress_callback(10, f"Converting audio to {audio_format.upper()}...")

    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, bufsize=1)
    if proc.stderr and total_duration > 0:
        for raw_line in proc.stderr:
            t = parse_ffmpeg_time(raw_line.strip())
            if t is not None:
                pct = int(min(max(t / total_duration, 0.0), 1.0) * 90)
                if progress_callback:
                    progress_callback(pct, f"Processing audio: {pct}%")

    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Audio conversion failed with exit code {proc.returncode}")

    if progress_callback:
        progress_callback(100, f"Saved: {output_path.name}")

    return output_path


def convert_gif_to_mp4(
    input_path: str | Path,
    output_path: str | Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """Convert an animated GIF to a web-compatible H.264 MP4 video."""
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        raise RuntimeError("FFmpeg is required for GIF to MP4 conversion. Please install FFmpeg.")

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    cmd = [
        ffmpeg_exe, "-y", "-v", "warning",
        "-i", str(input_path),
        "-movflags", "faststart",
        "-pix_fmt", "yuv420p",
        "-vf", "scale=trunc(iw/2)*2:trunc(ih/2)*2",
        "-c:v", "libx264",
        "-crf", "20",
        str(output_path),
    ]

    if progress_callback:
        progress_callback(20, "Converting GIF to MP4 video...")

    res = subprocess.run(cmd, capture_output=True, text=True)
    if res.returncode != 0:
        raise RuntimeError(f"GIF to MP4 conversion failed:\n{res.stderr}")

    if progress_callback:
        progress_callback(100, f"Saved: {output_path.name}")

    return output_path


def batch_convert_gifs_to_mp4(
    folder_path: str | Path,
    output_dir: str | Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> list[Path]:
    """
    Batch convert all animated GIF files in a directory to web-compatible H.264 MP4 videos.
    Returns a list of created MP4 file paths.
    """
    folder = Path(folder_path).resolve()
    if not folder.is_dir():
        raise NotADirectoryError(f"Directory not found: {folder}")

    out_dir = Path(output_dir).resolve()
    out_dir.mkdir(parents=True, exist_ok=True)

    gifs = sorted(
        p for p in folder.iterdir()
        if p.is_file() and p.suffix.lower() == ".gif"
    )
    if not gifs:
        return []

    created: list[Path] = []
    total = len(gifs)

    for idx, gif_file in enumerate(gifs, 1):
        out_mp4 = out_dir / f"{gif_file.stem}.mp4"

        def _item_progress(pct: int, msg: str, _idx=idx, _name=gif_file.name):
            if progress_callback:
                overall = int(((_idx - 1) + (pct / 100.0)) / total * 100)
                progress_callback(overall, f"[{_idx}/{total}] {_name}: {msg}")

        res = convert_gif_to_mp4(
            input_path=gif_file,
            output_path=out_mp4,
            progress_callback=_item_progress,
        )
        created.append(res)

    if progress_callback:
        progress_callback(100, f"Converted {len(created)}/{total} GIF(s) to MP4")

    return created


def convert_image(
    input_path: str | Path,
    output_path: str | Path,
    quality: int = 95,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """Convert between image formats (PNG, JPG, WEBP, BMP, TIFF) using Pillow."""
    if not PILLOW_AVAILABLE:
        raise RuntimeError("Pillow is required for image conversion. Run: pip install pillow")

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if progress_callback:
        progress_callback(10, f"Converting {input_path.name}...")

    with Image.open(input_path) as img:
        target_ext = output_path.suffix.lower()
        if target_ext in (".jpg", ".jpeg") and img.mode in ("RGBA", "P", "LA"):
            img = img.convert("RGB")
        img.save(str(output_path), quality=quality)

    if progress_callback:
        progress_callback(100, f"Saved: {output_path.name}")

    return output_path


def convert_text_to_pdf(
    input_path: str | Path,
    output_path: str | Path,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """
    Convert plain text, Markdown, or CSV documents into a formatted PDF.
    Uses ReportLab if available; falls back to clean Pillow bitmap PDF rendering.
    """
    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if not input_path.is_file():
        raise FileNotFoundError(f"Text file not found: {input_path}")

    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        text_content = f.read()

    lines = text_content.splitlines()

    if progress_callback:
        progress_callback(10, f"Rendering text document ({len(lines)} lines)...")

    if REPORTLAB_AVAILABLE:
        c = rl_canvas.Canvas(str(output_path))
        width, height = 595, 842  # A4 points
        margin = 40
        y = height - margin
        c.setFont("Helvetica", 10)

        for line in lines:
            # Wrap long lines at 90 characters
            chunks = [line[i:i + 90] for i in range(0, max(len(line), 1), 90)]
            for chunk in chunks:
                if y < margin:
                    c.showPage()
                    c.setFont("Helvetica", 10)
                    y = height - margin
                c.drawString(margin, y, chunk)
                y -= 14
        c.save()

    elif PILLOW_AVAILABLE:
        # Fallback using Pillow page rendering
        page_width, page_height = 1240, 1754  # A4 @ 150 DPI
        margin = 80
        line_height = 24
        max_lines_per_page = (page_height - 2 * margin) // line_height

        pages = []
        current_lines = []

        for line in lines:
            chunks = [line[i:i + 75] for i in range(0, max(len(line), 1), 75)]
            for chunk in chunks:
                if len(current_lines) >= max_lines_per_page:
                    # Render page
                    img = Image.new("RGB", (page_width, page_height), color="white")
                    draw = ImageDraw.Draw(img)
                    cur_y = margin
                    for l in current_lines:
                        draw.text((margin, cur_y), l, fill="black")
                        cur_y += line_height
                    pages.append(img)
                    current_lines = []
                current_lines.append(chunk)

        if current_lines or not pages:
            img = Image.new("RGB", (page_width, page_height), color="white")
            draw = ImageDraw.Draw(img)
            cur_y = margin
            for l in current_lines:
                draw.text((margin, cur_y), l, fill="black")
                cur_y += line_height
            pages.append(img)

        pages[0].save(str(output_path), save_all=True, append_images=pages[1:])
    else:
        raise RuntimeError("Neither ReportLab nor Pillow is installed. Run: pip install reportlab pillow")

    if progress_callback:
        progress_callback(100, f"Saved PDF: {output_path.name}")

    return output_path


def remux_or_transcode_video(
    input_path: str | Path,
    output_path: str | Path,
    reencode: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
) -> Path:
    """Fast remux (copy stream container) or full re-encode of video."""
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        raise RuntimeError("FFmpeg is required. Please install FFmpeg.")

    input_path = Path(input_path).resolve()
    output_path = Path(output_path).resolve()
    output_path.parent.mkdir(parents=True, exist_ok=True)

    if reencode:
        cmd = [
            ffmpeg_exe, "-y", "-v", "warning",
            "-i", str(input_path),
            "-c:v", "libx264", "-crf", "23", "-preset", "medium",
            "-c:a", "aac", "-b:a", "192k",
            str(output_path),
        ]
    else:
        cmd = [
            ffmpeg_exe, "-y", "-v", "warning",
            "-i", str(input_path),
            "-c", "copy",
            str(output_path),
        ]

    total_duration = get_media_duration(input_path)
    if progress_callback:
        progress_callback(10, "Remuxing/Transcoding video...")

    proc = subprocess.Popen(cmd, stderr=subprocess.PIPE, text=True, bufsize=1)
    if proc.stderr and total_duration > 0:
        for raw_line in proc.stderr:
            t = parse_ffmpeg_time(raw_line.strip())
            if t is not None:
                pct = int(min(max(t / total_duration, 0.0), 1.0) * 90)
                if progress_callback:
                    progress_callback(pct, f"Processing: {pct}%")

    proc.wait()
    if proc.returncode != 0:
        raise RuntimeError(f"Video operation failed with exit code {proc.returncode}")

    if progress_callback:
        progress_callback(100, f"Saved: {output_path.name}")

    return output_path


@dataclass
class VideoStreamInfo:
    codec_name: str = ""
    width: int = 0
    height: int = 0
    pix_fmt: str = ""
    r_frame_rate: str = ""
    avg_frame_rate: str = ""
    time_base: str = ""
    sample_aspect_ratio: str = "1:1"
    duration: float = 0.0


@dataclass
class AudioStreamInfo:
    codec_name: str = ""
    channels: int = 0
    sample_rate: int = 0
    duration: float = 0.0


@dataclass
class ClipProbeInfo:
    path: Path
    duration: float = 0.0
    video: Optional[VideoStreamInfo] = None
    audio: Optional[AudioStreamInfo] = None


def parse_fps_value(fps_str: str) -> float:
    """Parse fractional or decimal FPS string from FFprobe to float value."""
    if not fps_str or fps_str == "0/0":
        return 0.0
    try:
        if "/" in fps_str:
            num, den = fps_str.split("/", 1)
            den_f = float(den)
            return float(num) / den_f if den_f != 0 else 0.0
        return float(fps_str)
    except Exception:
        return 0.0


def _safe_float(val, default: float = 0.0) -> float:
    """Safely parse float value, ignoring 'N/A', empty strings, None, or invalid numbers."""
    if val is None:
        return default
    try:
        f = float(val)
        return f if f == f else default
    except (ValueError, TypeError):
        return default


def _safe_int(val, default: int = 0) -> int:
    """Safely parse int value, ignoring 'N/A', empty strings, None, or invalid numbers."""
    if val is None:
        return default
    try:
        return int(float(val))
    except (ValueError, TypeError):
        return default


def _normalize_sar(sar: str) -> str:
    """Normalize sample aspect ratio string (e.g. 1:1, 1/1, 0:1, N/A) to standard ratio."""
    s = (sar or "").strip().lower()
    if s in ("", "0:1", "0/1", "n/a", "1:1", "1/1"):
        return "1:1"
    return s.replace("/", ":")


def _probe_clip_with_ffmpeg(clip_path: Path, info: Optional[ClipProbeInfo] = None) -> ClipProbeInfo:
    """
    Fallback stream probe using ffmpeg -i stream banners and stderr logs
    when ffprobe is not installed or returns incomplete stream metadata.
    """
    if info is None:
        info = ClipProbeInfo(path=clip_path)

    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        if info.duration <= 0.0:
            info.duration = get_media_duration(clip_path)
        return info

    try:
        cmd = [ffmpeg_exe, "-i", str(clip_path)]
        res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        stderr = res.stderr or ""

        # Duration: HH:MM:SS.ms
        dur_m = re.search(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)", stderr)
        if dur_m and info.duration <= 0.0:
            hh, mm, ss = int(dur_m.group(1)), int(dur_m.group(2)), float(dur_m.group(3))
            info.duration = hh * 3600 + mm * 60 + ss

        # Video stream: Stream #0:0...: Video: codec, pix_fmt, WxH...
        if info.video is None:
            for line in stderr.splitlines():
                if "Video:" in line and "(attached pic)" not in line:
                    v_match = re.search(
                        r"Stream #\d+:\d+.*?: Video:\s*([a-zA-Z0-9_-]+).*?,\s*([a-zA-Z0-9_]+).*?,\s*(\d+)x(\d+)",
                        line,
                    )
                    if v_match:
                        codec, pix_fmt, w, h = v_match.groups()
                        fps_m = re.search(r"(\d+(?:\.\d+)?)\s*fps", line)
                        fps_str = f"{fps_m.group(1)}/1" if fps_m else "30/1"
                        sar_m = re.search(r"SAR\s+(\d+:\d+)", line)
                        sar = sar_m.group(1) if sar_m else "1:1"
                        tbn_m = re.search(r"(\d+)\s*tbn", line)
                        tbase = f"1/{tbn_m.group(1)}" if tbn_m else "1/30"
                        info.video = VideoStreamInfo(
                            codec_name=codec.lower(),
                            width=int(w),
                            height=int(h),
                            pix_fmt=pix_fmt.lower(),
                            r_frame_rate=fps_str,
                            avg_frame_rate=fps_str,
                            time_base=tbase,
                            sample_aspect_ratio=sar,
                            duration=info.duration,
                        )
                        break

        # Audio stream: Stream #0:1...: Audio: codec, X Hz, layout/channels...
        if info.audio is None:
            a_match = re.search(
                r"Stream #\d+:\d+.*?: Audio:\s*([a-zA-Z0-9_-]+).*?,\s*(\d+)\s*Hz,\s*([^,\n]+)",
                stderr,
            )
            if a_match:
                acodec, srate, ch_raw = a_match.groups()
                ch = 2 if "stereo" in ch_raw.lower() else (1 if "mono" in ch_raw.lower() else 2)
                ch_num = re.search(r"(\d+)\s*channels", ch_raw)
                if ch_num:
                    ch = int(ch_num.group(1))
                info.audio = AudioStreamInfo(
                    codec_name=acodec.lower(),
                    channels=ch,
                    sample_rate=int(srate),
                    duration=info.duration,
                )
    except Exception:
        pass

    if info.duration <= 0.0:
        info.duration = get_media_duration(clip_path)

    return info


def probe_clip(clip_path: str | Path, ffprobe_exe: Optional[str] = None) -> ClipProbeInfo:
    """
    Inspect input clip via ffprobe (with ffmpeg -i fallback) to extract video/audio codec,
    dimensions, aspect ratio, frame rate, pixel format, timebase, and duration.
    """
    p = Path(clip_path).resolve()
    if not ffprobe_exe:
        ffprobe_exe = find_ffprobe()

    info = ClipProbeInfo(path=p)

    if ffprobe_exe:
        cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries",
            "stream=index,codec_type,codec_name,width,height,r_frame_rate,avg_frame_rate,pix_fmt,time_base,sample_aspect_ratio,sample_rate,channels,duration:stream_disposition=attached_pic:format=duration",
            "-of", "json",
            str(p),
        ]

        try:
            res = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
            if res.returncode == 0 and res.stdout.strip():
                data = json.loads(res.stdout)
                fmt_dur = _safe_float(data.get("format", {}).get("duration"))
                info.duration = fmt_dur

                for s in data.get("streams", []):
                    stype = s.get("codec_type")
                    disp = s.get("disposition") or {}
                    is_attached = _safe_int(disp.get("attached_pic")) == 1
                    if stype == "video" and not is_attached and info.video is None:
                        v_dur = _safe_float(s.get("duration")) or fmt_dur
                        info.video = VideoStreamInfo(
                            codec_name=str(s.get("codec_name", "") or "").lower(),
                            width=_safe_int(s.get("width")),
                            height=_safe_int(s.get("height")),
                            pix_fmt=str(s.get("pix_fmt", "") or "").lower(),
                            r_frame_rate=str(s.get("r_frame_rate", "") or ""),
                            avg_frame_rate=str(s.get("avg_frame_rate", "") or ""),
                            time_base=str(s.get("time_base", "") or ""),
                            sample_aspect_ratio=str(s.get("sample_aspect_ratio", "1:1") or "1:1"),
                            duration=v_dur,
                        )
                        if info.duration <= 0.0:
                            info.duration = v_dur

                    elif stype == "audio" and info.audio is None:
                        a_dur = _safe_float(s.get("duration")) or fmt_dur
                        info.audio = AudioStreamInfo(
                            codec_name=str(s.get("codec_name", "") or "").lower(),
                            channels=_safe_int(s.get("channels")),
                            sample_rate=_safe_int(s.get("sample_rate")),
                            duration=a_dur,
                        )
        except Exception:
            pass

    # If ffprobe was unavailable or could not detect video/audio streams, fall back to ffmpeg -i probe
    if info.video is None or (info.audio is None and info.duration <= 0.0):
        info = _probe_clip_with_ffmpeg(p, info)

    if info.duration <= 0.0:
        info.duration = get_media_duration(p)

    # Backfill stream durations if format duration was discovered later
    if info.duration > 0.0:
        if info.video and info.video.duration <= 0.0:
            info.video.duration = info.duration
        if info.audio and info.audio.duration <= 0.0:
            info.audio.duration = info.duration

    return info


def are_clips_stream_compatible(clips: list[ClipProbeInfo]) -> Tuple[bool, str]:
    """
    Compare video codec, dimensions, aspect ratio, frame rate, pixel format,
    timebase, and audio stream properties to determine if safe direct stream-copy
    (-c copy) is possible.
    """
    if not clips:
        return False, "No clips provided"

    if any(c.video is None for c in clips):
        return False, "One or more clips lack a detectable video stream"

    ref = clips[0]
    ref_v = ref.video
    assert ref_v is not None

    if not ref_v.codec_name:
        return False, "Unknown video codec prevents direct stream copy"

    if ref_v.width <= 0 or ref_v.height <= 0:
        return False, "Invalid video dimensions prevent direct stream copy"

    ref_fps = parse_fps_value(ref_v.avg_frame_rate or ref_v.r_frame_rate)
    if ref_fps <= 0.0:
        return False, "Unknown or invalid frame rate prevents direct stream copy"

    if not ref_v.pix_fmt:
        return False, "Unknown pixel format prevents direct stream copy"

    if not ref_v.time_base:
        return False, "Unknown time base prevents direct stream copy"

    if len(clips) == 1:
        return True, "Single clip is compatible"

    for i, c in enumerate(clips[1:], start=1):
        cv = c.video
        assert cv is not None

        if not cv.codec_name:
            return False, "Unknown video codec prevents direct stream copy"

        if cv.codec_name != ref_v.codec_name:
            return False, f"Codec mismatch between clip 1 ({ref_v.codec_name}) and clip {i+1} ({cv.codec_name})"

        if cv.width <= 0 or cv.height <= 0:
            return False, "Invalid video dimensions prevent direct stream copy"

        if cv.width != ref_v.width or cv.height != ref_v.height:
            return False, f"Resolution mismatch between clip 1 ({ref_v.width}x{ref_v.height}) and clip {i+1} ({cv.width}x{cv.height})"

        if not cv.pix_fmt or cv.pix_fmt != ref_v.pix_fmt:
            return False, f"Pixel format mismatch between clip 1 ({ref_v.pix_fmt}) and clip {i+1} ({cv.pix_fmt})"

        if not cv.time_base or cv.time_base != ref_v.time_base:
            return False, f"Time base mismatch between clip 1 ({ref_v.time_base}) and clip {i+1} ({cv.time_base})"

        c_fps = parse_fps_value(cv.avg_frame_rate or cv.r_frame_rate)
        if c_fps <= 0.0 or abs(ref_fps - c_fps) > 0.01:
            return False, f"Frame rate mismatch between clip 1 ({ref_fps:.2f}fps) and clip {i+1} ({c_fps:.2f}fps)"

        ref_sar = _normalize_sar(ref_v.sample_aspect_ratio)
        c_sar = _normalize_sar(cv.sample_aspect_ratio)
        if ref_sar != c_sar:
            return False, f"Sample aspect ratio mismatch ({ref_sar} vs {c_sar})"

        # Audio compatibility
        has_ref_a = ref.audio is not None
        has_c_a = c.audio is not None
        if has_ref_a != has_c_a:
            return False, f"Audio presence mismatch between clip 1 ({'audio' if has_ref_a else 'no-audio'}) and clip {i+1} ({'audio' if has_c_a else 'no-audio'})"

        if has_ref_a and has_c_a:
            ref_a = ref.audio
            ca = c.audio
            assert ref_a is not None and ca is not None
            if not ref_a.codec_name or not ca.codec_name or ca.codec_name != ref_a.codec_name:
                return False, f"Audio codec mismatch ({ref_a.codec_name} vs {ca.codec_name})"
            if ref_a.channels <= 0 or ca.channels <= 0 or ca.channels != ref_a.channels:
                return False, f"Audio channel count mismatch ({ref_a.channels} vs {ca.channels})"
            if ref_a.sample_rate <= 0 or ca.sample_rate <= 0 or ca.sample_rate != ref_a.sample_rate:
                return False, f"Audio sample rate mismatch ({ref_a.sample_rate}Hz vs {ca.sample_rate}Hz)"

    return True, "Streams are identical and compatible for direct stream copy"


def build_normalization_filter(
    clips: list[ClipProbeInfo],
) -> Tuple[str, list[str], list[str]]:
    """
    Build FFmpeg filter_complex script that:
    1. Scales and pads with black bars (letterbox/pillarbox) to preserve aspect ratio without distortion.
    2. Forces constant framerate and yuv420p pixel format.
    3. Normalizes audio to 48kHz stereo AAC or synthesizes silence for clips without audio.
    4. Concat all normalized video and audio tracks.

    Returns: (filter_complex_string, map_args, audio_codec_args)
    """
    if not clips:
        raise ValueError("At least one clip is required to build normalization filter.")

    # 1. Target resolution: choose best clip resolution (max w*h), fallback 1920x1080
    best_w, best_h = 1920, 1080
    max_pixels = -1
    for c in clips:
        if c.video and c.video.width > 0 and c.video.height > 0:
            pixels = c.video.width * c.video.height
            if pixels > max_pixels:
                max_pixels = pixels
                best_w = c.video.width
                best_h = c.video.height

    tw = best_w if best_w % 2 == 0 else best_w + 1
    th = best_h if best_h % 2 == 0 else best_h + 1

    # 2. Target FPS
    fps_vals = []
    for c in clips:
        if c.video:
            fps = parse_fps_value(c.video.avg_frame_rate or c.video.r_frame_rate)
            if 1.0 <= fps <= 120.0:
                fps_vals.append(fps)
    target_fps = max(fps_vals) if fps_vals else 30.0

    if abs(target_fps - round(target_fps)) < 0.01:
        fps_str = str(int(round(target_fps)))
    elif abs(target_fps - 29.97) < 0.05:
        fps_str = "30000/1001"
    elif abs(target_fps - 23.976) < 0.05:
        fps_str = "24000/1001"
    elif abs(target_fps - 59.94) < 0.05:
        fps_str = "60000/1001"
    else:
        fps_str = f"{target_fps:.2f}"

    has_any_audio = any(c.audio is not None for c in clips)

    video_filters = []
    audio_filters = []
    concat_inputs = []

    for i, c in enumerate(clips):
        # Clip duration for audio alignment: prefer video duration to avoid frozen video or premature cut-offs
        dur = (
            c.video.duration
            if c.video and c.video.duration > 0.0
            else (c.duration if c.duration > 0.0 else 1.0)
        )
        if dur < 0.1:
            dur = 1.0
        dur_str = f"{dur:.3f}"

        # Video filter: scale with decrease, force divisible by 2, pad centered, setsar=1, fps, yuv420p
        sar_norm = _normalize_sar(c.video.sample_aspect_ratio if c.video else "1:1")
        sar_prefilter = "scale=trunc(iw*sar/2)*2:ih," if sar_norm != "1:1" else ""
        vf = (
            f"[{i}:v:0]"
            f"{sar_prefilter}"
            f"scale={tw}:{th}:force_original_aspect_ratio=decrease:force_divisible_by=2,"
            f"pad={tw}:{th}:(ow-iw)/2:(oh-ih)/2:color=black,"
            f"setsar=1,fps={fps_str},format=yuv420p[v{i}]"
        )
        video_filters.append(vf)

        if has_any_audio:
            if c.audio is not None:
                # Normalize existing audio to 48kHz stereo, pad with silence if shorter, trim if longer
                af = (
                    f"[{i}:a:0]"
                    f"aformat=sample_rates=48000:channel_layouts=stereo,"
                    f"apad=whole_dur={dur_str},atrim=0:{dur_str}[a{i}]"
                )
            else:
                # Synthesize silent audio matching the clip duration
                af = f"anullsrc=channel_layout=stereo:sample_rate=48000,atrim=duration={dur_str}[a{i}]"
            audio_filters.append(af)
            concat_inputs.append(f"[v{i}][a{i}]")
        else:
            concat_inputs.append(f"[v{i}]")

    num_clips = len(clips)
    if has_any_audio:
        concat_str = f"{''.join(concat_inputs)}concat=n={num_clips}:v=1:a=1[outv][outa]"
        all_filters = video_filters + audio_filters + [concat_str]
        map_args = ["-map", "[outv]", "-map", "[outa]"]
        audio_codec_args = ["-c:a", "aac", "-b:a", "192k", "-ar", "48000"]
    else:
        concat_str = f"{''.join(concat_inputs)}concat=n={num_clips}:v=1:a=0[outv]"
        all_filters = video_filters + [concat_str]
        map_args = ["-map", "[outv]"]
        audio_codec_args = []

    filter_complex_str = "; ".join(all_filters)
    return filter_complex_str, map_args, audio_codec_args


def verify_video_integrity(
    video_path: str | Path,
    ffmpeg_exe: Optional[str] = None,
    ffprobe_exe: Optional[str] = None,
) -> bool:
    """
    Run post-merge integrity check on produced video file using ffprobe
    and FFmpeg null container decoding (ffmpeg -v error -i <output> -f null -)
    to verify container well-formedness, track decodability, and zero corrupt packets.
    """
    vp = Path(video_path).resolve()
    if not vp.is_file() or vp.stat().st_size == 0:
        raise RuntimeError(f"Video output file does not exist or is empty: {vp}")

    if not ffmpeg_exe:
        ffmpeg_exe = find_ffmpeg()
    if not ffprobe_exe:
        ffprobe_exe = find_ffprobe()

    if not ffmpeg_exe and not ffprobe_exe:
        raise RuntimeError("Neither FFmpeg nor FFprobe is available to verify video integrity.")

    dur = get_media_duration(vp)
    timeout = max(60, int(dur * 2) if dur > 0 else 120)

    # 1. FFprobe container & stream structure verification
    if ffprobe_exe:
        probe_cmd = [
            ffprobe_exe,
            "-v", "error",
            "-show_entries", "format=duration,size:stream=index,codec_type,codec_name",
            "-of", "json",
            str(vp),
        ]
        try:
            res = subprocess.run(probe_cmd, capture_output=True, text=True, timeout=15)
            if res.returncode != 0:
                err = res.stderr.strip() or f"ffprobe exited with code {res.returncode}"
                raise RuntimeError(f"Output container structure is corrupted or unreadable: {err}")
            data = json.loads(res.stdout or "{}")
            streams = data.get("streams", [])
            if not streams:
                raise RuntimeError("No decodable streams detected in merged video file")
            if not any(s.get("codec_type") == "video" for s in streams):
                raise RuntimeError("No decodable video stream detected in merged video file")
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            raise RuntimeError("ffprobe integrity check timed out after 15s")
        except json.JSONDecodeError as e:
            raise RuntimeError(f"Output container metadata corrupted: {e}")

    # 2. FFmpeg null container full decoding verification
    if ffmpeg_exe:
        decode_cmd = [
            ffmpeg_exe,
            "-v", "error",
            "-i", str(vp),
            "-f", "null",
            "-",
        ]
        try:
            res = subprocess.run(decode_cmd, capture_output=True, text=True, timeout=timeout)
            if res.returncode != 0:
                err = res.stderr.strip() or f"FFmpeg null decode exited with code {res.returncode}"
                raise RuntimeError(f"Video decodability integrity check failed: {err}")
            if res.stderr.strip():
                # FFmpeg error messages under -v error signify corrupted packets or stream decode failures
                raise RuntimeError(f"Video decodability corruption detected: {res.stderr.strip()}")
        except FileNotFoundError:
            pass
        except subprocess.TimeoutExpired:
            raise RuntimeError(f"FFmpeg null decode integrity check timed out after {timeout}s")

    return True


def combine_videos(
    video_paths: list[str | Path],
    output_path: str | Path,
    reencode: bool = False,
    progress_callback: Optional[Callable[[int, str], None]] = None,
    order: Optional[str] = None,
) -> Path:
    """
    Concatenate and merge multiple video files into a single unified video file.
    Inspects stream compatibility via ffprobe:
    - Direct Stream-Copy Path: If all clips have matching codecs, dimensions, timebase,
      frame rates, and audio properties, uses -f concat demuxer with -c copy -movflags +faststart.
    - Normalization & Transcode Path: If properties differ or direct copy is unsafe,
      re-encodes to H.264 (libx264) yuv420p, scales and letterboxes/pillarboxes to preserve
      aspect ratio, harmonizes framerate, synthesizes silent audio for clips lacking audio,
      and normalizes audio to AAC 48kHz stereo.
    - Post-Merge Integrity Check: Runs automated ffprobe and null container decoding
      verification on the output file before reporting completion.
    """
    ffmpeg_exe = find_ffmpeg()
    if not ffmpeg_exe:
        raise RuntimeError("FFmpeg is required to combine videos. Please install FFmpeg.")

    if not video_paths:
        raise ValueError("At least one video file is required to combine.")

    valid_paths = [Path(p).resolve() for p in video_paths]
    for p in valid_paths:
        if not p.is_file():
            raise FileNotFoundError(f"Video file not found: {p}")
        if p.stat().st_size == 0:
            raise ValueError(f"Input video file is empty: {p.name}")

    if order == "ascending":
        def _nat_sort_key(p: Path):
            return [int(c) if c.isdigit() else c.lower() for c in re.split(r"(\d+)", p.name)]
        valid_paths = sorted(valid_paths, key=_nat_sort_key)
    elif order == "random":
        import random
        random.shuffle(valid_paths)

    output_path = Path(output_path).resolve()
    if output_path.is_dir():
        raise ValueError(f"Output path must be a file, not a directory: {output_path}")
    if output_path in valid_paths:
        raise ValueError(f"Output path '{output_path.name}' conflicts with one of the input files.")
    output_path.parent.mkdir(parents=True, exist_ok=True)

    ffprobe_exe = find_ffprobe()

    if progress_callback:
        progress_callback(5, f"Probing {len(valid_paths)} video clips for stream compatibility...")

    # R1: Pre-validation and stream compatibility probe
    probed_clips = [probe_clip(p, ffprobe_exe) for p in valid_paths]

    # Validate that every clip has a detectable video stream
    for c in probed_clips:
        if c.video is None or c.video.width <= 0 or c.video.height <= 0:
            raise ValueError(f"Input file '{c.path.name}' does not contain a valid video stream.")

    can_copy, diff_reason = are_clips_stream_compatible(probed_clips)

    total_duration = sum(c.duration for c in probed_clips)
    if total_duration <= 0:
        total_duration = sum(get_media_duration(p) for p in valid_paths)

    temp_list_file = None
    temp_script_file = None
    try:
        # R2: Direct Stream-Copy Path (if streams match and reencode is not forced)
        if not reencode and can_copy:
            if progress_callback:
                progress_callback(10, f"Streams compatible ({diff_reason}) — attempting fast direct copy...")

            with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
                temp_list_file = Path(f.name)
                for p in valid_paths:
                    escaped_path = p.as_posix().replace("'", "'\\''")
                    f.write(f"file '{escaped_path}'\n")

            copy_cmd = [
                ffmpeg_exe, "-y", "-v", "warning",
                "-f", "concat", "-safe", "0",
                "-i", str(temp_list_file),
                "-c", "copy",
                "-movflags", "+faststart",
                str(output_path),
            ]

            proc = None
            try:
                proc = subprocess.Popen(copy_cmd, stderr=subprocess.PIPE, text=True, bufsize=1)
                error_output = []
                if proc.stderr:
                    for raw_line in proc.stderr:
                        error_output.append(raw_line)
                        if total_duration > 0:
                            t = parse_ffmpeg_time(raw_line.strip())
                            if t is not None:
                                pct = int(min(max(t / total_duration, 0.0), 1.0) * 85)
                                if progress_callback:
                                    progress_callback(pct, f"Fast stream copying: {pct}%")

                proc.wait()
            finally:
                if proc and proc.poll() is None:
                    try:
                        proc.kill()
                        proc.wait(timeout=2)
                    except Exception:
                        pass
                if proc and proc.stderr:
                    try:
                        proc.stderr.close()
                    except Exception:
                        pass

            if proc.returncode == 0 and output_path.is_file() and output_path.stat().st_size > 0:
                # R3: Verify post-merge integrity
                try:
                    verify_video_integrity(output_path, ffmpeg_exe=ffmpeg_exe, ffprobe_exe=ffprobe_exe)
                    if progress_callback:
                        progress_callback(100, f"Combined {len(valid_paths)} videos successfully via direct copy!")
                    return output_path
                except Exception as integ_err:
                    if progress_callback:
                        progress_callback(15, f"Direct copy integrity check failed ({integ_err}) — falling back to normalization...")
                    if output_path.exists():
                        try:
                            output_path.unlink()
                        except Exception:
                            pass
            else:
                if progress_callback:
                    err_hint = "".join(error_output[-2:]).strip() if error_output else "non-zero return code"
                    progress_callback(15, f"Direct stream copy failed ({err_hint}) — falling back to normalization...")
                if output_path.exists():
                    try:
                        output_path.unlink()
                    except Exception:
                        pass

        # R2: Normalization & Transcode Path
        if progress_callback:
            msg = "Streams differ — normalizing & re-encoding video/audio..." if not reencode else "Re-encoding requested — normalizing video/audio..."
            progress_callback(20, msg)

        filter_str, map_args, audio_args = build_normalization_filter(probed_clips)

        # Write filter complex to a temporary script file to avoid Windows CLI length limits (>8192 chars)
        with tempfile.NamedTemporaryFile("w", encoding="utf-8", suffix=".txt", delete=False) as f:
            temp_script_file = Path(f.name)
            f.write(filter_str)

        inputs_args = []
        for p in valid_paths:
            inputs_args.extend(["-i", str(p)])

        reencode_cmd = [
            ffmpeg_exe, "-y", "-v", "warning",
            *inputs_args,
            "-filter_complex_script", str(temp_script_file),
            *map_args,
            "-c:v", "libx264", "-preset", "fast", "-crf", "23",
            "-pix_fmt", "yuv420p",
            *audio_args,
            "-movflags", "+faststart",
            str(output_path),
        ]

        proc = None
        try:
            proc = subprocess.Popen(reencode_cmd, stderr=subprocess.PIPE, text=True, bufsize=1)
            err_lines = []
            if proc.stderr:
                for raw_line in proc.stderr:
                    err_lines.append(raw_line)
                    if len(err_lines) > 50:
                        err_lines.pop(0)
                    if total_duration > 0:
                        t = parse_ffmpeg_time(raw_line.strip())
                        if t is not None:
                            pct = int(min(max(t / total_duration, 0.0), 1.0) * 85)
                            if progress_callback:
                                progress_callback(pct, f"Merging & encoding: {pct}%")

            proc.wait()
        finally:
            if proc and proc.poll() is None:
                try:
                    proc.kill()
                    proc.wait(timeout=2)
                except Exception:
                    pass
            if proc and proc.stderr:
                try:
                    proc.stderr.close()
                except Exception:
                    pass

        if proc.returncode != 0:
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            err_msg = "".join(err_lines[-5:]).strip() or f"FFmpeg exited with code {proc.returncode}"
            raise RuntimeError(f"FFmpeg combine failed: {err_msg}")

        # R3: Verify post-merge integrity
        if progress_callback:
            progress_callback(90, "Verifying output video integrity...")

        try:
            verify_video_integrity(output_path, ffmpeg_exe=ffmpeg_exe, ffprobe_exe=ffprobe_exe)
        except Exception as e:
            if output_path.exists():
                try:
                    output_path.unlink()
                except Exception:
                    pass
            raise RuntimeError(f"Output video integrity check failed: {e}")

        if progress_callback:
            progress_callback(100, f"Combined {len(valid_paths)} videos successfully!")

        return output_path

    except Exception:
        # In the event of an unrecoverable FFmpeg error, ensure corrupt temporary output files are cleaned up
        if output_path.exists():
            try:
                output_path.unlink()
            except Exception:
                pass
        raise

    finally:
        if temp_list_file and temp_list_file.exists():
            try:
                temp_list_file.unlink()
            except Exception:
                pass
        if temp_script_file and temp_script_file.exists():
            try:
                temp_script_file.unlink()
            except Exception:
                pass


