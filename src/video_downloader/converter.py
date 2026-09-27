"""
Media Converter Engine for Video Extractor CLI.
Provides high-performance, cross-platform conversions for Video, GIF, Audio, Images, and Text Documents
using native FFmpeg subprocess pipelines, Pillow, and ReportLab.
Zero heavy GUI dependencies (no Tkinter, PySide6, MoviePy, or PyDub required).
"""

import os
import re
import sys
import time
import shutil
import tempfile
import subprocess
from pathlib import Path
from typing import Callable, Optional

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
    ffprobe_exe = shutil.which("ffprobe") or (shutil.which("ffprobe.exe") if sys.platform == "win32" else None)
    if not ffprobe_exe:
        ffmpeg_exe = find_ffmpeg()
        if ffmpeg_exe:
            candidate = Path(ffmpeg_exe).parent / ("ffprobe.exe" if sys.platform == "win32" else "ffprobe")
            if candidate.is_file():
                ffprobe_exe = str(candidate)

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
                val = float(res.stdout.strip())
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
