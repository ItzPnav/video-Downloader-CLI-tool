# file_converter.py
# Convertify — Gorgeous File Converter
# Adds: video preview playback + smoother ffmpeg progress parsing for video->gif

import sys
import os
import re
import traceback
import subprocess
import tempfile
import time
from pathlib import Path
from typing import Optional

from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QHBoxLayout, QLabel, QPushButton,
    QFileDialog, QComboBox, QProgressBar, QTextEdit, QMessageBox, QFrame,
    QSlider
)
from PySide6.QtGui import QPixmap, QDragEnterEvent, QDropEvent, QIcon
from PySide6.QtCore import Qt, QThread, Signal, QUrl, QSize

# Multimedia imports (for preview)
try:
    from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
    from PySide6.QtMultimediaWidgets import QVideoWidget
    MULTIMEDIA_AVAILABLE = True
except Exception:
    MULTIMEDIA_AVAILABLE = False

# Optional libs
try:
    from PIL import Image
    PIL_AVAILABLE = True
except Exception:
    PIL_AVAILABLE = False

try:
    import moviepy.editor as mpy
    MOVIEPY_AVAILABLE = True
except Exception:
    MOVIEPY_AVAILABLE = False

try:
    from pydub import AudioSegment
    PYDUB_AVAILABLE = True
except Exception:
    PYDUB_AVAILABLE = False

try:
    from reportlab.pdfgen import canvas
    REPORTLAB_AVAILABLE = True
except Exception:
    REPORTLAB_AVAILABLE = False

# Extensions
IMAGE_EXTS = {".png", ".jpg", ".jpeg", ".bmp", ".gif", ".tiff", ".webp"}
VIDEO_EXTS = {".mp4", ".mov", ".avi", ".mkv", ".webm", ".flv"}
AUDIO_EXTS = {".mp3", ".wav", ".ogg", ".flac", ".m4a", ".aac"}
TEXT_EXTS = {".txt", ".md", ".csv"}
PDF_EXTS = {".pdf"}

# ---------- Worker thread ----------
class ConverterThread(QThread):
    progress = Signal(int)
    finished = Signal(bool, str)

    def __init__(self, func, *args, **kwargs):
        super().__init__()
        self.func = func
        self.args = args
        self.kwargs = kwargs

    def run(self):
        try:
            def report(p):
                try:
                    self.progress.emit(int(p))
                except Exception:
                    pass
            result = self.func(*self.args, progress_callback=report, **self.kwargs)
            self.finished.emit(True, result or "Conversion finished")
        except Exception as e:
            tb = traceback.format_exc()
            self.finished.emit(False, f"{e}\n\n{tb}")

# ---------- Conversion functions ----------
def convert_image(input_path: str, output_path: str, *, progress_callback=None):
    if not PIL_AVAILABLE:
        raise RuntimeError("Pillow is not installed.")
    with Image.open(input_path) as im:
        im.save(output_path)
    if progress_callback:
        progress_callback(100)
    return f"Saved {output_path}"

def convert_gif_to_mp4(input_path: str, output_path: str, *, progress_callback=None):
    if not MOVIEPY_AVAILABLE:
        raise RuntimeError("moviepy is not installed.")
    clip = mpy.VideoFileClip(input_path)
    clip.write_videofile(output_path, codec="libx264", audio=False, fps=24, verbose=False, logger=None)
    if progress_callback:
        progress_callback(100)
    return f"Saved {output_path}"

def convert_audio(input_path: str, output_path: str, *, progress_callback=None):
    if not PYDUB_AVAILABLE:
        raise RuntimeError("pydub is not installed.")
    ext = Path(output_path).suffix.lower().lstrip(".")
    audio = AudioSegment.from_file(input_path)
    audio.export(output_path, format=ext)
    if progress_callback:
        progress_callback(100)
    return f"Saved {output_path}"

def text_to_pdf(input_path: str, output_path: str, *, progress_callback=None):
    if not REPORTLAB_AVAILABLE:
        raise RuntimeError("reportlab is not installed.")
    with open(input_path, "r", encoding="utf-8", errors="ignore") as f:
        content = f.read()
    c = canvas.Canvas(output_path)
    width, height = 595, 842
    margin = 40
    y = height - margin
    lines = content.splitlines()
    for line in lines:
        wrapped = [line[i:i+90] for i in range(0, len(line), 90)]
        for w in wrapped:
            if y < margin:
                c.showPage()
                y = height - margin
            c.setFont("Helvetica", 10)
            c.drawString(margin, y, w)
            y -= 12
    c.save()
    if progress_callback:
        progress_callback(100)
    return f"Saved {output_path}"

# ---------- Helpers for ffmpeg progress ----------
def ffmpeg_exists() -> bool:
    try:
        res = subprocess.run(["ffmpeg", "-version"], capture_output=True, text=True)
        return res.returncode == 0
    except Exception:
        return False

def _ffprobe_duration(input_path: str) -> float:
    try:
        cmd = ["ffprobe", "-v", "error", "-show_entries", "format=duration",
               "-of", "default=noprint_wrappers=1:nokey=1", input_path]
        res = subprocess.run(cmd, capture_output=True, text=True)
        if res.returncode == 0:
            return float(res.stdout.strip())
    except Exception:
        pass
    return 0.0

_TIME_RE = re.compile(r"time=(\d+):(\d+):(\d+\.\d+)")  # parse ffmpeg time=HH:MM:SS.ms

def _parse_ffmpeg_time_from_line(line: str) -> Optional[float]:
    m = _TIME_RE.search(line)
    if not m:
        return None
    hh = int(m.group(1))
    mm = int(m.group(2))
    ss = float(m.group(3))
    return hh * 3600 + mm * 60 + ss

# Convert video -> gif using ffmpeg and parse stderr for progress (time=...)
def convert_video_to_gif_with_progress(input_path: str, output_path: str,
                                      fps: int = 30, height: int = 504,
                                      max_duration: float = 60.0, max_colors: int = 256,
                                      *, progress_callback=None):
    if not ffmpeg_exists():
        raise RuntimeError("ffmpeg not found on PATH. Install ffmpeg (winget install ffmpeg).")

    # clamp values
    fps = min(max(1, int(fps)), 60)
    if max_colors not in (64, 128, 256):
        max_colors = 256

    # get duration
    duration = 0.0
    if MOVIEPY_AVAILABLE:
        try:
            clip = mpy.VideoFileClip(input_path)
            duration = clip.duration
            # close readers
            try:
                clip.reader.close()
            except Exception:
                pass
            try:
                if clip.audio and hasattr(clip.audio, "reader"):
                    clip.audio.reader.close_proc()
            except Exception:
                pass
        except Exception:
            duration = _ffprobe_duration(input_path)
    else:
        duration = _ffprobe_duration(input_path)

    use_duration = min(duration if duration > 0 else max_duration, max_duration)

    out_path = Path(output_path)
    temp_dir = Path(tempfile.gettempdir())
    palette_path = temp_dir / (out_path.stem + "_palette.png")

    # scale expression - preserve aspect
    scale_expr = f"scale=-1:{height}:flags=lanczos"
    vf_for_palette = f"fps={fps},{scale_expr},palettegen=max_colors={max_colors}"
    vf_for_use = f"fps={fps},{scale_expr}"

    # palette generation command (we'll capture stderr but palettegen doesn't output time; give small progress)
    cmd_palette = [
        "ffmpeg", "-y", "-v", "warning", "-i", str(input_path),
        "-t", str(use_duration),
        "-vf", vf_for_palette,
        str(palette_path)
    ]

    # gif creation command: using palette
    cmd_gif = [
        "ffmpeg", "-y", "-v", "warning", "-i", str(input_path), "-i", str(palette_path),
        "-t", str(use_duration),
        "-filter_complex", f"[0:v]{vf_for_use}[x];[x][1:v]paletteuse",
        "-loop", "0", str(out_path)
    ]

    # Run palette generation (progress 0-20%)
    if progress_callback:
        progress_callback(5)
    p1 = subprocess.run(cmd_palette, capture_output=True, text=True)
    if p1.returncode != 0:
        raise RuntimeError(f"ffmpeg palette generation failed:\n{p1.stderr}")

    if progress_callback:
        progress_callback(20)

    # Run gif creation with real-time stderr parsing
    # ffmpeg prints progress-like lines to stderr containing "time=HH:MM:SS.xx"
    proc = subprocess.Popen(cmd_gif, stderr=subprocess.PIPE, text=True, bufsize=1)

    last_percent = 20
    start_time = time.time()
    try:
        if proc.stderr:
            for raw_line in proc.stderr:
                line = raw_line.strip()
                # try parse time
                t = _parse_ffmpeg_time_from_line(line)
                if t is not None and use_duration > 0:
                    frac = min(max(t / use_duration, 0.0), 1.0)
                    percent = int(20 + frac * 75)  # map from 20-95 (leave some room)
                    if percent > last_percent:
                        last_percent = percent
                        if progress_callback:
                            progress_callback(percent)
                # Also, provide small heartbeat updates
                else:
                    # if some stderr while no time, bump a little
                    elapsed = time.time() - start_time
                    # avoid over-updating
                    if elapsed < 1:
                        continue
                    # small incremental bump up to 90% while running
                    heartbeat = min(90, last_percent + 1)
                    if heartbeat > last_percent:
                        last_percent = heartbeat
                        if progress_callback:
                            progress_callback(last_percent)
        proc.wait()
        if proc.returncode != 0:
            # capture stderr output for message
            raise RuntimeError(f"ffmpeg failed during gif creation (return code {proc.returncode}).")
    finally:
        # cleanup palette
        try:
            palette_path.unlink(missing_ok=True)
        except Exception:
            pass

    if progress_callback:
        progress_callback(100)
    return f"Saved {output_path} (duration: {use_duration:.2f}s, fps: {fps}, height: {height}, colors: {max_colors})"

# ---------- Category helper ----------
def infer_category(path: str):
    ext = Path(path).suffix.lower()
    if ext in IMAGE_EXTS:
        return "image"
    if ext in VIDEO_EXTS:
        return "video"
    if ext in AUDIO_EXTS:
        return "audio"
    if ext in TEXT_EXTS:
        return "text"
    if ext in PDF_EXTS:
        return "pdf"
    return "unknown"

# ---------- UI ----------
class GorgeousConverter(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("✨ Convertify — Gorgeous File Converter")
        self.setMinimumSize(920, 560)
        self.setAcceptDrops(True)

        self.file_path = None
        self.output_folder = None
        self.thread: Optional[ConverterThread] = None

        # multimedia objects
        self.player = None
        self.video_widget = None
        self.audio_output = None

        self.init_ui()
        self.apply_styles()

    def init_ui(self):
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(12)

        # header
        header = QHBoxLayout()
        title = QLabel("<h2>Convertify</h2>")
        subtitle = QLabel("Drop a file, pick a target, tweak video→gif options, and convert.")
        subtitle.setStyleSheet("color: #cfcfcf;")
        left_head = QVBoxLayout()
        left_head.addWidget(title)
        left_head.addWidget(subtitle)
        header.addLayout(left_head)
        header.addStretch()
        btn_about = QPushButton("About")
        btn_about.clicked.connect(self.show_about)
        header.addWidget(btn_about)
        root.addLayout(header)

        # main card
        card = QFrame()
        card.setObjectName("card")
        card_layout = QHBoxLayout(card)
        card_layout.setContentsMargins(12, 12, 12, 12)
        card_layout.setSpacing(12)

        # left: preview + controls
        left = QVBoxLayout()
        left.setSpacing(8)

        # preview frame (video/image)
        self.preview_frame = QFrame()
        self.preview_frame.setObjectName("preview_frame")
        pf_layout = QVBoxLayout(self.preview_frame)
        pf_layout.setContentsMargins(8, 8, 8, 8)

        # If multimedia is available, create video widget and player
        if MULTIMEDIA_AVAILABLE:
            self.video_widget = QVideoWidget()
            self.video_widget.setMinimumSize(420, 280)
            pf_layout.addWidget(self.video_widget)
            # media player
            self.player = QMediaPlayer()
            self.audio_output = QAudioOutput()
            self.player.setAudioOutput(self.audio_output)
            self.player.setVideoOutput(self.video_widget)
            # playback slider
            self.play_slider = QSlider(Qt.Horizontal)
            self.play_slider.setRange(0, 1000)
            self.play_slider.sliderMoved.connect(self.on_slider_moved)
            pf_layout.addWidget(self.play_slider)
            # play/pause button
            controls = QHBoxLayout()
            self.btn_play = QPushButton("Play")
            self.btn_play.clicked.connect(self.toggle_play)
            controls.addWidget(self.btn_play)
            self.btn_stop = QPushButton("Stop")
            self.btn_stop.clicked.connect(self.stop_preview)
            controls.addWidget(self.btn_stop)
            controls.addStretch()
            pf_layout.addLayout(controls)
            # connect to position changes
            self.player.positionChanged.connect(self.on_position_changed)
            self.player.durationChanged.connect(self.on_duration_changed)
        else:
            # fallback: static preview label
            self.preview_label = QLabel("Preview not available (PySide6 multimedia missing)")
            self.preview_label.setAlignment(Qt.AlignCenter)
            self.preview_label.setMinimumSize(420, 280)
            pf_layout.addWidget(self.preview_label)

        left.addWidget(self.preview_frame)

        btn_choose = QPushButton("Choose File")
        btn_choose.clicked.connect(self.pick_file)
        left.addWidget(btn_choose)

        card_layout.addLayout(left)

        # right: options and conversion
        right = QVBoxLayout()
        right.setSpacing(8)
        self.input_label = QLabel("No file chosen")
        right.addWidget(self.input_label)

        right.addWidget(QLabel("Target format:"))
        self.combo = QComboBox()
        self.combo.addItem("— choose file first —")
        self.combo.currentIndexChanged.connect(self.on_target_changed)
        right.addWidget(self.combo)

        # Video->GIF options
        self.video_options_widget = QFrame()
        vopts = QHBoxLayout(self.video_options_widget)
        vopts.setContentsMargins(0, 0, 0, 0)
        vopts.setSpacing(8)

        # Resolution
        res_layout = QVBoxLayout()
        res_layout.addWidget(QLabel("Resolution:"))
        self.combo_res = QComboBox()
        self.combo_res.addItems(["504p (default)", "480p", "360p"])
        res_layout.addWidget(self.combo_res)
        vopts.addLayout(res_layout)

        # Quality
        q_layout = QVBoxLayout()
        q_layout.addWidget(QLabel("Quality:"))
        self.combo_quality = QComboBox()
        self.combo_quality.addItems(["HIGH (default)", "MEDIUM", "LOW"])
        q_layout.addWidget(self.combo_quality)
        vopts.addLayout(q_layout)

        # FPS
        fps_layout = QVBoxLayout()
        fps_layout.addWidget(QLabel("FPS:"))
        self.combo_fps = QComboBox()
        # default shown first then others
        self.combo_fps.addItems(["30 (default)", "60", "45", "30", "15", "10", "5", "1"])
        self.combo_fps.setCurrentIndex(0)
        fps_layout.addWidget(self.combo_fps)
        vopts.addLayout(fps_layout)

        self.video_options_widget.setVisible(False)
        right.addWidget(self.video_options_widget)

        self.btn_output = QPushButton("Select Output Folder")
        self.btn_output.clicked.connect(self.select_output_folder)
        right.addWidget(self.btn_output)

        self.btn_convert = QPushButton("Convert")
        self.btn_convert.setEnabled(False)
        self.btn_convert.clicked.connect(self.start_conversion)
        right.addWidget(self.btn_convert)

        self.progress = QProgressBar()
        self.progress.setValue(0)
        right.addWidget(self.progress)

        self.log = QTextEdit()
        self.log.setReadOnly(True)
        self.log.setMaximumHeight(160)
        right.addWidget(self.log)

        card_layout.addLayout(right)
        root.addWidget(card)

        footer = QLabel("Supported: images (png/jpg/webp/gif), video→gif (with options), gif→mp4, audio, text→pdf. ffmpeg required for video/audio ops.")
        footer.setStyleSheet("color: #bdbdbd;")
        root.addWidget(footer)

    def apply_styles(self):
        self.setStyleSheet("""
            QWidget { background: qlineargradient(x1:0,y1:0,x2:1,y2:1, stop:0 #0f1720, stop:1 #111827); color: #e6eef5; font-family: Inter, Arial;}
            #card { background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 rgba(255,255,255,0.03), stop:1 rgba(255,255,255,0.01)); border-radius: 12px; padding: 8px; }
            #preview_frame { border: 2px dashed rgba(255,255,255,0.04); border-radius: 8px; min-height: 280px; }
            QPushButton { padding: 8px 12px; border-radius: 8px; background: rgba(255,255,255,0.03); }
            QPushButton:hover { background: rgba(255,255,255,0.05); }
            QComboBox { padding: 6px; border-radius: 8px; background: rgba(255,255,255,0.02); }
            QProgressBar { height: 14px; border-radius: 7px; background: rgba(255,255,255,0.03); }
        """)

    # ---------- Multimedia preview helpers ----------
    def load_preview(self, path: str):
        cat = infer_category(path)
        if cat == "image" and PIL_AVAILABLE:
            try:
                pix = QPixmap(path).scaled(420, 280, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                if MULTIMEDIA_AVAILABLE:
                    # hide video widget and show pixmap inside video widget area using label overlay
                    # easiest: set a label instead of videowidget if image
                    if hasattr(self, "preview_label"):
                        self.preview_label.setPixmap(pix)
                    else:
                        # create a temporary label and replace video_widget visually
                        self.preview_label = QLabel()
                        self.preview_label.setPixmap(pix)
                        self.preview_label.setAlignment(Qt.AlignCenter)
                        # we place it inside preview_frame replacing video_widget if exists
                        if self.video_widget:
                            self.video_widget.hide()
                        layout = self.preview_frame.layout()
                        layout.insertWidget(0, self.preview_label)
                else:
                    self.preview_label.setPixmap(pix)
            except Exception:
                if MULTIMEDIA_AVAILABLE:
                    self.preview_label.setText("Preview unavailable")
                else:
                    pass
        elif cat == "video" and MULTIMEDIA_AVAILABLE:
            # load video
            try:
                self.player.setSource(QUrl.fromLocalFile(path))
                self.player.pause()
                self.play_slider.setValue(0)
                self.btn_play.setText("Play")
                # ensure video widget visible
                if hasattr(self, "preview_label"):
                    try:
                        self.preview_label.hide()
                    except Exception:
                        pass
                if self.video_widget:
                    self.video_widget.show()
            except Exception:
                pass
        else:
            # fallback text
            if MULTIMEDIA_AVAILABLE and hasattr(self, "preview_label"):
                self.preview_label.setText(Path(path).name + "\n\n(" + infer_category(path) + ")")
            else:
                # create or update simple label
                if not MULTIMEDIA_AVAILABLE:
                    self.preview_label.setText(Path(path).name + "\n\n(" + infer_category(path) + ")")
                else:
                    pass

    def toggle_play(self):
        if not MULTIMEDIA_AVAILABLE or self.player is None:
            return
        state = self.player.playbackState()
        # QMediaPlayer.PlaybackState enum: PlayingState=1
        if state == QMediaPlayer.PlayingState:
            self.player.pause()
            self.btn_play.setText("Play")
        else:
            self.player.play()
            self.btn_play.setText("Pause")

    def stop_preview(self):
        if MULTIMEDIA_AVAILABLE and self.player:
            self.player.stop()
            self.btn_play.setText("Play")

    def on_position_changed(self, pos):
        # update slider (pos in ms)
        if not hasattr(self, "play_slider"):
            return
        dur = self.player.duration() if self.player else 0
        if dur > 0:
            v = int((pos / dur) * 1000)
            self.play_slider.blockSignals(True)
            self.play_slider.setValue(v)
            self.play_slider.blockSignals(False)

    def on_duration_changed(self, dur):
        # nothing needed; slider range fixed to 1000
        pass

    def on_slider_moved(self, val):
        if MULTIMEDIA_AVAILABLE and self.player:
            dur = self.player.duration()
            if dur > 0:
                ms = int((val / 1000) * dur)
                self.player.setPosition(ms)

    # ---------- File selection ----------
    def pick_file(self):
        path, _ = QFileDialog.getOpenFileName(self, "Pick a file to convert", str(Path.home()))
        if path:
            self.load_file(path)

    def load_file(self, path):
        self.file_path = path
        self.input_label.setText(f"Input: {path}")
        self.output_folder = str(Path(path).parent)
        self.btn_output.setText(f"Output folder: {self.output_folder}")
        # preview
        self.load_preview(path)
        self.update_targets(path)

    def update_targets(self, path):
        import shutil  # local import for shutil ffmpeg check if needed
        self.combo.clear()
        cat = infer_category(path)
        options = []
        ext = Path(path).suffix.lower()

        if cat == "image" and PIL_AVAILABLE:
            if ext == ".gif" and MOVIEPY_AVAILABLE:
                options = ["mp4", "png", "jpg", "webp"]
            else:
                options = ["png", "jpg", "jpeg", "webp", "gif", "bmp", "tiff"]
        elif cat == "video":
            if MOVIEPY_AVAILABLE or ffmpeg_exists():
                options = ["gif", "mp4 (remux)", "mp4 (re-encode)"]
            else:
                options = ["(moviepy/ffmpeg not installed — video conversions disabled)"]
        elif cat == "audio" and PYDUB_AVAILABLE:
            options = ["mp3", "wav", "ogg", "flac", "m4a"]
        elif cat == "text" and REPORTLAB_AVAILABLE:
            options = ["pdf"]
        elif cat == "pdf":
            options = ["pdf (copy)"]
        else:
            options = ["Change extension (manual)"]

        # missing libs hints
        if cat == "image" and not PIL_AVAILABLE:
            options = ["(Pillow not installed — image conversions disabled)"]
        if cat == "video" and not (MOVIEPY_AVAILABLE or ffmpeg_exists()):
            options = ["(moviepy/ffmpeg not installed — video conversions disabled)"]
        if cat == "audio" and not PYDUB_AVAILABLE:
            options = ["(pydub/ffmpeg not installed — audio conversions disabled)"]
        if cat == "text" and not REPORTLAB_AVAILABLE:
            options = ["(reportlab not installed — text→pdf disabled)"]

        for o in options:
            self.combo.addItem(o)

        # show video options if gif conversion available
        has_gif_option = any("gif" in str(o).lower() for o in options)
        self.video_options_widget.setVisible(has_gif_option)
        self.btn_convert.setEnabled(bool(options) and self.file_path is not None)

    def on_target_changed(self, idx):
        txt = self.combo.currentText().lower()
        if "gif" in txt:
            self.video_options_widget.setVisible(True)
        else:
            self.video_options_widget.setVisible(False)

    def select_output_folder(self):
        folder = QFileDialog.getExistingDirectory(self, "Select output folder", self.output_folder or str(Path.home()))
        if folder:
            self.output_folder = folder
            self.btn_output.setText(f"Output folder: {self.output_folder}")

    # ---------- Conversion orchestration ----------
    def start_conversion(self):
        if not self.file_path:
            QMessageBox.warning(self, "No file", "Pick an input file first.")
            return
        target = self.combo.currentText()
        if not target or target.startswith("("):
            QMessageBox.warning(self, "Can't Convert", "The selected conversion is not available.")
            return

        in_path = Path(self.file_path)
        out_name = in_path.stem
        cat = infer_category(self.file_path)
        suffix = in_path.suffix.lower()

        func = None
        outfile = None

        # VIDEO -> GIF with options
        if cat == "video" and "gif" in target.lower() and (MOVIEPY_AVAILABLE or ffmpeg_exists()):
            outfile = Path(self.output_folder) / f"{out_name}.gif"
            # resolution
            res_txt = self.combo_res.currentText()
            height = 504 if "504" in res_txt else (480 if "480" in res_txt else 360)
            # quality
            q_txt = self.combo_quality.currentText().lower()
            colors = 256 if "high" in q_txt else (128 if "medium" in q_txt else 64)
            # fps
            fps_txt = self.combo_fps.currentText()
            try:
                fps = int(fps_txt.split()[0])
            except Exception:
                fps = 30
            fps = min(fps, 60)
            def wrapper(inp, out, progress_callback=None):
                return convert_video_to_gif_with_progress(inp, out, fps=fps, height=height,
                                                          max_duration=60.0, max_colors=colors,
                                                          progress_callback=progress_callback)
            func = wrapper

        # GIF -> MP4 (image input)
        elif cat == "image" and suffix == ".gif" and target.lower().startswith("mp4") and MOVIEPY_AVAILABLE:
            outfile = Path(self.output_folder) / f"{out_name}.mp4"
            func = convert_gif_to_mp4

        # Image conversions
        elif cat == "image" and PIL_AVAILABLE:
            chosen = target.split()[0]
            out_ext = "jpg" if chosen.startswith("jpg") else chosen
            outfile = Path(self.output_folder) / f"{out_name}.{out_ext}"
            func = convert_image

        # Video -> others (fallback: re-encode to mp4)
        elif cat == "video" and (MOVIEPY_AVAILABLE or ffmpeg_exists()):
            outfile = Path(self.output_folder) / f"{out_name}.mp4"
            def wrapper(inp, out, progress_callback=None):
                if MOVIEPY_AVAILABLE:
                    clip = mpy.VideoFileClip(inp)
                    clip.write_videofile(out, codec="libx264", audio=True, verbose=False, logger=None)
                    if progress_callback:
                        progress_callback(100)
                    return f"Saved {out}"
                else:
                    cmd = ["ffmpeg", "-y", "-i", inp, "-c", "copy", out]
                    p = subprocess.run(cmd, capture_output=True, text=True)
                    if p.returncode != 0:
                        raise RuntimeError(f"ffmpeg failed: {p.stderr}")
                    if progress_callback:
                        progress_callback(100)
                    return f"Saved {out}"
            func = wrapper

        # Audio
        elif cat == "audio" and PYDUB_AVAILABLE:
            out_ext = target
            outfile = Path(self.output_folder) / f"{out_name}.{out_ext}"
            func = convert_audio

        # Text -> PDF
        elif cat == "text" and REPORTLAB_AVAILABLE:
            outfile = Path(self.output_folder) / f"{out_name}.pdf"
            func = text_to_pdf

        else:
            # fallback: copy with changed extension
            choice_ext = target.replace("Change extension (manual)", suffix).split()[0]
            outfile = Path(self.output_folder) / f"{out_name}.{choice_ext}"
            def rename_func(inp, out, *, progress_callback=None):
                import shutil
                shutil.copy2(inp, out)
                if progress_callback:
                    progress_callback(100)
                return f"Copied to {out}"
            func = rename_func

        if outfile.exists():
            res = QMessageBox.question(self, "Overwrite?", f"{outfile} exists. Overwrite?", QMessageBox.Yes | QMessageBox.No)
            if res != QMessageBox.Yes:
                return

        # run conversion in thread
        self.progress.setValue(0)
        self.log.append(f"Starting conversion -> {outfile}")
        self.btn_convert.setEnabled(False)
        self.thread = ConverterThread(func, str(in_path), str(outfile))
        self.thread.progress.connect(self.progress.setValue)
        self.thread.finished.connect(self.conversion_done)
        self.thread.start()

    def conversion_done(self, ok: bool, message: str):
        self.btn_convert.setEnabled(True)
        if ok:
            self.progress.setValue(100)
            self.log.append("✅ Success: " + str(message))
            QMessageBox.information(self, "Done", str(message))
            # if result is gif, optionally preview it by loading it in preview (if multimedia supports)
            if str(message).lower().endswith(".gif") or ".gif" in str(message).lower():
                # attempt to load gif (some platforms support gif playback in videowidget)
                try:
                    out_path = message.split("Saved ")[-1].split(" ")[0].strip()
                    if out_path and Path(out_path).exists():
                        self.load_preview(out_path)
                except Exception:
                    pass
        else:
            self.log.append("❌ Error: " + str(message))
            QMessageBox.critical(self, "Conversion failed", str(message))

    # ---------- Drag & drop ----------
    def dragEnterEvent(self, ev: QDragEnterEvent):
        if ev.mimeData().hasUrls():
            ev.acceptProposedAction()

    def dropEvent(self, ev: QDropEvent):
        urls = ev.mimeData().urls()
        if urls:
            local = urls[0].toLocalFile()
            if os.path.isfile(local):
                self.load_file(local)

    def show_about(self):
        QMessageBox.information(self, "About Convertify",
                                "Convertify v1 — quick multi-format converter\nNow with video preview & smoother progress.")

# ---------- main ----------
def main():
    app = QApplication(sys.argv)
    w = GorgeousConverter()
    w.show()
    sys.exit(app.exec())

if __name__ == "__main__":
    main()
