from __future__ import annotations

import shutil
import sys
import tempfile
import zipfile
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import streamlit as st

SRC_DIR = Path(__file__).resolve().parent / "src"
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

import video_downloader.downloader as dl_mod
from video_downloader.comic_scraper import scrape_and_download_comic
from video_downloader.converter import (
    convert_audio_to_audio,
    convert_gif_to_mp4,
    convert_image,
    convert_text_to_pdf,
    convert_video_to_audio,
    convert_video_to_gif,
    combine_videos,
    remux_or_transcode_video,
)
from video_downloader.downloader import download, find_ffmpeg
from video_downloader.ocr import run_ocr
from video_downloader.packager import images_to_cbz, images_to_pdf
from video_downloader.race_controller import ExtractionRaceController
from video_downloader.router import identify
from video_downloader.utils import get_version

st.set_page_config(
    page_title="TOOL-KIT // MISSION CONTROL",
    layout="wide",
    initial_sidebar_state="collapsed",
)

MISSION_CONTROL_CSS = """
<style>
@import url('https://fonts.googleapis.com/css2?family=Big+Shoulders+Display:wght@700;800;900&family=JetBrains+Mono:wght@400;500;600;700&display=swap');

:root {
  --bg: #0A0D10;
  --panel: #11161A;
  --panel-2: #151B20;
  --line: #232C31;
  --ink: #E6ECE8;
  --muted: #6C7E78;
  --green: #39FF88;
  --green-dim: #1C7A45;
  --amber: #FFB627;
  --amber-dim: #8C640F;
  --red: #FF5C4D;
  --grid: rgba(57, 255, 136, 0.05);
}

*, *::before, *::after {
  border-radius: 0 !important;
  box-shadow: none !important;
}

html, body, [data-testid="stAppViewContainer"], .stApp {
  background:
    linear-gradient(var(--grid) 1px, transparent 1px) 0 0 / 40px 40px,
    linear-gradient(90deg, var(--grid) 1px, transparent 1px) 0 0 / 40px 40px,
    var(--bg) !important;
  color: var(--ink) !important;
  font-family: 'JetBrains Mono', monospace !important;
}

/* CRT Scanline overlay */
.stApp::after {
  content: "";
  position: fixed;
  inset: 0;
  pointer-events: none;
  background: repeating-linear-gradient(
    to bottom,
    rgba(255, 255, 255, 0.012) 0px,
    rgba(255, 255, 255, 0.012) 1px,
    transparent 1px,
    transparent 3px
  );
  z-index: 99999;
}

[data-testid="stHeader"], [data-testid="stToolbar"], #MainMenu, footer {
  background: transparent !important;
}

.block-container {
  max-width: 1280px !important;
  padding-top: 1.25rem !important;
  padding-bottom: 3rem !important;
}

h1, h2, h3, .mc-display {
  font-family: 'Big Shoulders Display', sans-serif !important;
  font-weight: 800 !important;
  letter-spacing: 0.03em !important;
  text-transform: uppercase !important;
  color: var(--ink) !important;
}

p, span, label, input, textarea, select, button, code {
  font-family: 'JetBrains Mono', monospace !important;
}

/* Telemetry Header Bar */
.mc-header {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 3px solid var(--green);
  padding: 12px 18px;
  margin-bottom: 16px;
}

.mc-brand {
  display: flex;
  align-items: center;
  gap: 12px;
}

.mc-brand-title {
  font-family: 'Big Shoulders Display', sans-serif !important;
  font-size: 32px;
  font-weight: 900;
  letter-spacing: 0.06em;
  line-height: 1;
  color: var(--ink);
}

.mc-ver {
  border: 1px solid var(--line);
  background: var(--panel-2);
  color: var(--muted);
  font-size: 11px;
  padding: 3px 8px;
}

.mc-pills {
  display: flex;
  flex-wrap: wrap;
  align-items: center;
  gap: 8px;
}

.mc-pill-ok {
  border: 1px solid var(--green-dim);
  background: rgba(57, 255, 136, 0.08);
  color: var(--green);
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  letter-spacing: 0.06em;
}

.mc-pill-warn {
  border: 1px solid var(--amber-dim);
  background: rgba(255, 182, 39, 0.08);
  color: var(--amber);
  font-size: 11px;
  font-weight: 700;
  padding: 4px 10px;
  letter-spacing: 0.06em;
}

.mc-zulu {
  color: var(--muted);
  font-size: 11px;
  letter-spacing: 0.08em;
}

@keyframes radarPulse {
  0%, 100% { opacity: 0.35; transform: scale(0.85); }
  50% { opacity: 1; transform: scale(1); }
}

.mc-dot {
  display: inline-block;
  width: 7px;
  height: 7px;
  background: var(--green);
  box-shadow: 0 0 8px rgba(57, 255, 136, 0.7) !important;
  animation: radarPulse 1.8s ease-in-out infinite;
  margin-right: 6px;
}

/* Panel Header Eyebrow */
.mc-panel-head {
  background: var(--panel);
  border: 1px solid var(--line);
  border-left: 3px solid var(--amber);
  padding: 10px 14px;
  margin-bottom: 10px;
}

.mc-panel-title {
  font-family: 'Big Shoulders Display', sans-serif !important;
  font-size: 24px;
  font-weight: 800;
  letter-spacing: 0.04em;
  text-transform: uppercase;
  color: var(--ink);
  line-height: 1;
}

.mc-panel-sub {
  font-size: 11px;
  color: var(--muted);
  margin-top: 4px;
}

/* Fuel Gauge */
@keyframes fuelCrawl {
  from { background-position: 0 0; }
  to { background-position: 32px 0; }
}

.mc-gauge-wrap {
  border: 1px solid var(--line);
  background: var(--panel-2);
  padding: 8px 10px;
  margin: 8px 0 12px 0;
}

.mc-gauge-meta {
  display: flex;
  justify-content: space-between;
  font-size: 11px;
  color: var(--muted);
  margin-bottom: 6px;
}

.mc-gauge-track {
  width: 100%;
  height: 8px;
  background: #0A0D10;
  border: 1px solid var(--line);
  overflow: hidden;
}

.mc-gauge-fill-active {
  height: 100%;
  background: repeating-linear-gradient(
    90deg,
    var(--green) 0px,
    var(--green) 6px,
    var(--green-dim) 6px,
    var(--green-dim) 8px
  );
  background-size: 32px 100%;
  animation: fuelCrawl 1.6s linear infinite;
}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {
  gap: 6px;
  background: transparent;
  border-bottom: 1px solid var(--line);
  padding-bottom: 6px;
}

.stTabs [data-baseweb="tab"] {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  color: var(--muted) !important;
  font-size: 12px !important;
  padding: 8px 14px !important;
}

.stTabs [aria-selected="true"] {
  background: var(--panel-2) !important;
  border: 1px solid var(--green) !important;
  border-bottom: 2px solid var(--green) !important;
  color: var(--green) !important;
  font-weight: 700 !important;
}

/* Inputs & Selects */
.stTextInput > div > div > input,
.stTextArea textarea,
.stSelectbox > div > div,
[data-testid="stFileUploader"] section {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
  color: var(--ink) !important;
}

.stTextInput > div > div > input:focus,
.stTextArea textarea:focus {
  border-color: var(--amber) !important;
}

/* Primary CTA = Tactical Amber */
.stButton > button[kind="primary"],
.stDownloadButton > button {
  background: var(--amber) !important;
  color: #0A0D10 !important;
  border: 1px solid var(--amber) !important;
  font-weight: 700 !important;
  text-transform: uppercase !important;
  letter-spacing: 0.06em !important;
  transition: transform 120ms cubic-bezier(0.23, 1, 0.32, 1);
}

.stButton > button[kind="primary"]:active,
.stDownloadButton > button:active {
  transform: scale(0.97) !important;
}

.stButton > button[kind="secondary"] {
  background: var(--panel-2) !important;
  color: var(--ink) !important;
  border: 1px solid var(--line) !important;
  text-transform: uppercase !important;
}

[data-testid="stVerticalBlockBorderWrapper"] {
  background: var(--panel) !important;
  border: 1px solid var(--line) !important;
}
</style>
"""

st.markdown(MISSION_CONTROL_CSS, unsafe_allow_html=True)

if "mc_history" not in st.session_state:
    st.session_state.mc_history = []


def _record_history(item: dict) -> None:
    st.session_state.mc_history.insert(0, item)
    st.session_state.mc_history = st.session_state.mc_history[:25]


def _render_header() -> None:
    ffmpeg_ready = find_ffmpeg() is not None
    ocr_ready = shutil.which("tesseract") is not None
    zulu = datetime.now(timezone.utc).strftime("%H:%M:%S ZULU")
    ff_cls = "mc-pill-ok" if ffmpeg_ready else "mc-pill-warn"
    ocr_cls = "mc-pill-ok" if ocr_ready else "mc-pill-warn"
    ff_txt = "FFMPEG: READY" if ffmpeg_ready else "FFMPEG: MISSING"
    ocr_txt = "OCR: READY" if ocr_ready else "OCR: MISSING"

    st.markdown(
        f"""
        <div class="mc-header">
          <div class="mc-brand">
            <span class="mc-dot"></span>
            <span class="mc-brand-title">TOOL-KIT</span>
            <span class="mc-ver">V{get_version()} // CLOUD</span>
          </div>
          <div class="mc-pills">
            <span class="{ff_cls}">{ff_txt}</span>
            <span class="{ocr_cls}">{ocr_txt}</span>
            <span class="mc-pill-ok">SYS: ONLINE</span>
          </div>
          <div class="mc-zulu">{zulu}</div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _render_gauge(label: str, pct: int) -> None:
    st.markdown(
        f"""
        <div class="mc-gauge-wrap">
          <div class="mc-gauge-meta">
            <span>{label}</span>
            <span style="color: var(--green); font-weight: 700;">{pct}%</span>
          </div>
          <div class="mc-gauge-track">
            <div class="mc-gauge-fill-active" style="width: {max(0, min(100, pct))}%;"></div>
          </div>
        </div>
        """,
        unsafe_allow_html=True,
    )


def _save_uploaded_to_dir(uploaded_file, target_dir: Path) -> Path:
    dest = target_dir / uploaded_file.name
    dest.write_bytes(uploaded_file.getbuffer())
    return dest


_render_header()

tab_dl, tab_conv, tab_comic, tab_pack, tab_ocr, tab_hist = st.tabs([
    "1. Video Downloader",
    "2. Converter & Merger",
    "3. Comic Scraper",
    "4. Folder to PDF/CBZ",
    "5. Image OCR",
    "6. Session History",
])


# --------------------------------------------------------------------------- #
# TAB 1: VIDEO DOWNLOADER
# --------------------------------------------------------------------------- #
with tab_dl:
    col_main, col_tiers = st.columns([2, 1], gap="medium")

    with col_tiers:
        with st.container(border=True):
            st.markdown(
                '<div class="mc-panel-head"><div class="mc-panel-title">EXTRACTORS</div>'
                '<div class="mc-panel-sub">Runs enabled extractors in parallel; first match wins.</div></div>',
                unsafe_allow_html=True,
            )
            use_ytdlp = st.toggle("yt-dlp (YouTube, Vimeo & 1,000+ sites)", value=True)
            use_scrapling = st.toggle("Scrapling (Stealth anti-bot extractor)", value=True)
            use_static = st.toggle("HTML Scanner (Direct <video> & X/Twitter API)", value=True)
            use_browser = st.toggle("Browser Sniffer (Headless Chrome)", value=False, help="Disabled by default on free cloud tiers to conserve RAM.")

    with col_main:
        with st.container(border=True):
            st.markdown(
                '<div class="mc-panel-head"><div class="mc-panel-title">DOWNLOAD VIDEO</div>'
                '<div class="mc-panel-sub">PASTE A URL TO START MULTI-ENGINE EXTRACTION</div></div>',
                unsafe_allow_html=True,
            )
            url = st.text_input("Video or Page URL", placeholder="https://x.com/user/status/1234567890")
            c1, c2, c3 = st.columns(3)
            with c1:
                quality = st.selectbox("Quality", ["Best Available", "1080p", "720p", "480p", "360p", "worst"])
            with c2:
                timeout_sec = st.number_input("Timeout (sec)", min_value=5, max_value=90, value=25)
            with c3:
                st.text_input("Delivery Mode", value="Browser Download", disabled=True)

            gauge_slot = st.empty()
            with gauge_slot:
                _render_gauge("READY", 0)

            start_dl = st.button("DOWNLOAD VIDEO", type="primary", use_container_width=True)

        if start_dl:
            if not url or not url.strip().startswith(("http://", "https://")):
                st.error("[-] Invalid URL. Expected http:// or https://")
            else:
                req_q: Optional[str] = None if quality == "Best Available" else quality
                route = identify(url.strip())
                with gauge_slot:
                    _render_gauge(f"RACING ENGINES [{route.platform.upper()}]", 45)

                controller = ExtractionRaceController(
                    url=url.strip(),
                    requested_quality=req_q,
                    timeout=float(timeout_sec),
                    no_ytdlp=not use_ytdlp,
                    no_scrapling=not use_scrapling,
                    no_static=not use_static,
                    no_browser=not use_browser,
                    prefer_gui=False,
                )
                result = controller.run_race()

                if not result.candidate:
                    with gauge_slot:
                        _render_gauge("NO QUALIFYING MEDIA FOUND", 0)
                    st.error("[-] No downloadable media found. Try toggling extractors or checking if the post is public.")
                else:
                    with gauge_slot:
                        _render_gauge(f"WON BY {result.winner_engine.upper()} ({result.duration_ms}ms) — STREAMING", 80)
                    with tempfile.TemporaryDirectory(prefix="mc_dl_") as tmpdir:
                        tmp_path = Path(tmpdir)
                        orig_dl_dir = dl_mod.get_download_dir
                        dl_mod.get_download_dir = lambda: tmp_path
                        try:
                            out_path = download(
                                result.candidate,
                                filename=result.candidate.metadata.get("title", "video"),
                                requested_quality=req_q,
                                conflict_policy="replace",
                            )
                        finally:
                            dl_mod.get_download_dir = orig_dl_dir

                        if out_path and Path(out_path).is_file():
                            fp = Path(out_path)
                            data_bytes = fp.read_bytes()
                            with gauge_slot:
                                _render_gauge(f"COMPLETE: {fp.name}", 100)
                            st.success(f"[✓] Extracted via **{result.winner_engine}** in {result.duration_ms} ms")
                            st.video(data_bytes)
                            st.download_button(
                                label=f"SAVE {fp.name} TO DEVICE",
                                data=data_bytes,
                                file_name=fp.name,
                                mime="video/mp4",
                                use_container_width=True,
                            )
                            _record_history({
                                "tool": "Video Downloader",
                                "source": url.strip(),
                                "engine": result.winner_engine,
                                "file_name": fp.name,
                                "data": data_bytes,
                                "mime": "video/mp4",
                            })
                        else:
                            with gauge_slot:
                                _render_gauge("STREAM DOWNLOAD FAILED", 0)
                            st.error("[-] Extraction succeeded, but downloading the stream failed.")


# --------------------------------------------------------------------------- #
# TAB 2: CONVERTER & MERGER
# --------------------------------------------------------------------------- #
with tab_conv:
    c_left, c_right = st.columns(2, gap="medium")

    with c_left:
        with st.container(border=True):
            st.markdown(
                '<div class="mc-panel-head"><div class="mc-panel-title">CONVERT MEDIA</div>'
                '<div class="mc-panel-sub">Video → GIF/MP3/MP4, Audio transcode, Image, Text → PDF</div></div>',
                unsafe_allow_html=True,
            )
            conv_file = st.file_uploader("Upload Source File", key="conv_upload")
            target_fmt = st.selectbox("Target Format", ["gif", "mp3", "mp4", "wav", "flac", "aac", "png", "jpg", "pdf"])
            if target_fmt == "gif":
                g1, g2 = st.columns(2)
                gif_fps = g1.number_input("GIF FPS", min_value=5, max_value=60, value=24)
                gif_res = g2.selectbox("GIF Height", [504, 480, 360, 240], index=1)
            else:
                gif_fps, gif_res = 24, 480

            if st.button("CONVERT FILE", type="primary", use_container_width=True):
                if not conv_file:
                    st.error("[-] Upload a file first.")
                else:
                    with tempfile.TemporaryDirectory(prefix="mc_conv_") as tmpdir:
                        tmp_path = Path(tmpdir)
                        in_path = _save_uploaded_to_dir(conv_file, tmp_path)
                        out_path = tmp_path / f"{in_path.stem}.{target_fmt}"
                        in_sfx = in_path.suffix.lower()
                        try:
                            if target_fmt == "gif":
                                convert_video_to_gif(in_path, out_path, fps=int(gif_fps), height=int(gif_res))
                            elif target_fmt == "pdf" and in_sfx in (".txt", ".md", ".csv", ".json", ".log", ".py"):
                                convert_text_to_pdf(in_path, out_path)
                            elif target_fmt in ("mp3", "aac", "wav", "flac"):
                                if in_sfx in (".mp3", ".wav", ".flac", ".ogg", ".m4a", ".aac", ".opus"):
                                    convert_audio_to_audio(in_path, out_path, audio_format=target_fmt)
                                else:
                                    convert_video_to_audio(in_path, out_path, audio_format=target_fmt)
                            elif in_sfx == ".gif" and target_fmt == "mp4":
                                convert_gif_to_mp4(in_path, out_path)
                            elif target_fmt in ("png", "jpg"):
                                convert_image(in_path, out_path)
                            elif target_fmt == "mp4":
                                remux_or_transcode_video(in_path, out_path, reencode=False)
                            else:
                                raise ValueError(f"Unsupported conversion: {in_sfx} -> {target_fmt}")

                            out_bytes = out_path.read_bytes()
                            st.success(f"[✓] Converted to {out_path.name}")
                            st.download_button(
                                label=f"SAVE {out_path.name}",
                                data=out_bytes,
                                file_name=out_path.name,
                                use_container_width=True,
                            )
                            _record_history({
                                "tool": "Converter",
                                "source": conv_file.name,
                                "engine": "ffmpeg/pillow",
                                "file_name": out_path.name,
                                "data": out_bytes,
                                "mime": "application/octet-stream",
                            })
                        except Exception as exc:
                            st.error(f"[-] Conversion failed: {exc}")

    with c_right:
        with st.container(border=True):
            st.markdown(
                '<div class="mc-panel-head"><div class="mc-panel-title">COMBINE VIDEOS</div>'
                '<div class="mc-panel-sub">Concatenate multiple clips into a single MP4</div></div>',
                unsafe_allow_html=True,
            )
            merge_files = st.file_uploader("Upload 2+ Video Clips", accept_multiple_files=True, key="merge_upload")
            merge_reencode = st.checkbox("Force Re-encode (use if clips have different codecs/resolutions)", value=False)
            if st.button("COMBINE VIDEOS", type="primary", use_container_width=True):
                if not merge_files or len(merge_files) < 2:
                    st.error("[-] Upload at least 2 video files.")
                else:
                    with tempfile.TemporaryDirectory(prefix="mc_merge_") as tmpdir:
                        tmp_path = Path(tmpdir)
                        saved = [_save_uploaded_to_dir(f, tmp_path) for f in merge_files]
                        out_path = tmp_path / f"combined_{len(saved)}clips.mp4"
                        try:
                            combine_videos(saved, out_path, reencode=merge_reencode)
                            out_bytes = out_path.read_bytes()
                            st.success(f"[✓] Combined {len(saved)} clips into {out_path.name}")
                            st.video(out_bytes)
                            st.download_button(
                                label=f"SAVE {out_path.name}",
                                data=out_bytes,
                                file_name=out_path.name,
                                mime="video/mp4",
                                use_container_width=True,
                            )
                        except Exception as exc:
                            st.error(f"[-] Combine failed: {exc}")


# --------------------------------------------------------------------------- #
# TAB 3: COMIC SCRAPER
# --------------------------------------------------------------------------- #
with tab_comic:
    with st.container(border=True):
        st.markdown(
            '<div class="mc-panel-head"><div class="mc-panel-title">COMIC & GALLERY SCRAPER</div>'
            '<div class="mc-panel-sub">Scrape chapter image galleries and bundle into PDF / CBZ / ZIP</div></div>',
            unsafe_allow_html=True,
        )
        comic_url = st.text_input("Chapter / Gallery URL", placeholder="https://example.com/chapter-1")
        cc1, cc2 = st.columns(2)
        comic_fmt = cc1.selectbox("Output Bundle", ["pdf", "cbz", "zip (raw images)"])
        comic_cookies = cc2.file_uploader("Optional cookies.txt", type=["txt"], key="comic_cookies")

        if st.button("SCRAPE & BUNDLE", type="primary", use_container_width=True):
            if not comic_url or not comic_url.strip().startswith(("http://", "https://")):
                st.error("[-] Enter a valid http:// or https:// URL.")
            else:
                with tempfile.TemporaryDirectory(prefix="mc_comic_") as tmpdir:
                    tmp_path = Path(tmpdir)
                    cookie_path = _save_uploaded_to_dir(comic_cookies, tmp_path) if comic_cookies else None
                    auto_fmt = None if comic_fmt.startswith("zip") else comic_fmt
                    try:
                        res_path = Path(scrape_and_download_comic(
                            source=comic_url.strip(),
                            output_base_dir=tmp_path,
                            auto_format=auto_fmt,
                            cookie_file=cookie_path,
                        ))
                        if res_path.is_dir():
                            zip_out = tmp_path / f"{res_path.name}.zip"
                            with zipfile.ZipFile(zip_out, "w", zipfile.ZIP_DEFLATED) as zf:
                                for f in sorted(res_path.rglob("*")):
                                    if f.is_file():
                                        zf.write(f, f.relative_to(res_path))
                            res_path = zip_out
                        out_bytes = res_path.read_bytes()
                        st.success(f"[✓] Scraped & packaged: {res_path.name}")
                        st.download_button(
                            label=f"SAVE {res_path.name}",
                            data=out_bytes,
                            file_name=res_path.name,
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.error(f"[-] Comic scrape failed: {exc}")


# --------------------------------------------------------------------------- #
# TAB 4: FOLDER TO PDF / CBZ
# --------------------------------------------------------------------------- #
with tab_pack:
    with st.container(border=True):
        st.markdown(
            '<div class="mc-panel-head"><div class="mc-panel-title">IMAGES TO PDF / CBZ</div>'
            '<div class="mc-panel-sub">Upload ordered images and package into a single PDF or CBZ archive</div></div>',
            unsafe_allow_html=True,
        )
        pack_files = st.file_uploader(
            "Upload Images",
            type=["png", "jpg", "jpeg", "webp", "bmp"],
            accept_multiple_files=True,
            key="pack_upload",
        )
        pc1, pc2 = st.columns(2)
        pack_name = pc1.text_input("Archive Name", value="packaged_images")
        pack_fmt = pc2.selectbox("Format", ["pdf", "cbz"])

        if st.button("BUILD ARCHIVE", type="primary", use_container_width=True):
            if not pack_files:
                st.error("[-] Upload at least 1 image.")
            else:
                with tempfile.TemporaryDirectory(prefix="mc_pack_") as tmpdir:
                    tmp_path = Path(tmpdir)
                    img_dir = tmp_path / "imgs"
                    img_dir.mkdir(parents=True, exist_ok=True)
                    for f in pack_files:
                        _save_uploaded_to_dir(f, img_dir)
                    out_file = tmp_path / f"{pack_name.strip() or 'packaged'}.{pack_fmt}"
                    try:
                        if pack_fmt == "cbz":
                            ok, count = images_to_cbz(img_dir, out_file)
                        else:
                            ok, count = images_to_pdf(img_dir, out_file)
                        if not ok:
                            st.error("[-] No valid images found to package.")
                        else:
                            out_bytes = out_file.read_bytes()
                            st.success(f"[✓] Packaged {count} page(s) into {out_file.name}")
                            st.download_button(
                                label=f"SAVE {out_file.name}",
                                data=out_bytes,
                                file_name=out_file.name,
                                use_container_width=True,
                            )
                    except Exception as exc:
                        st.error(f"[-] Packaging failed: {exc}")


# --------------------------------------------------------------------------- #
# TAB 5: IMAGE OCR
# --------------------------------------------------------------------------- #
with tab_ocr:
    with st.container(border=True):
        st.markdown(
            '<div class="mc-panel-head"><div class="mc-panel-title">IMAGE TO TEXT (TESSERACT OCR)</div>'
            '<div class="mc-panel-sub">Extract optical text from uploaded images</div></div>',
            unsafe_allow_html=True,
        )
        ocr_files = st.file_uploader(
            "Upload Image(s)",
            type=["png", "jpg", "jpeg", "webp", "bmp", "tiff"],
            accept_multiple_files=True,
            key="ocr_upload",
        )
        ocr_lang = st.text_input("Tesseract Language Code", value="eng")

        if st.button("RUN OCR EXTRACTION", type="primary", use_container_width=True):
            if not ocr_files:
                st.error("[-] Upload at least 1 image.")
            else:
                with tempfile.TemporaryDirectory(prefix="mc_ocr_") as tmpdir:
                    tmp_path = Path(tmpdir)
                    img_dir = tmp_path / "imgs"
                    out_dir = tmp_path / "out"
                    img_dir.mkdir(parents=True, exist_ok=True)
                    out_dir.mkdir(parents=True, exist_ok=True)
                    for f in ocr_files:
                        _save_uploaded_to_dir(f, img_dir)
                    try:
                        ok, out_txt, preview = run_ocr(
                            target=str(img_dir),
                            output_dir=out_dir,
                            lang=ocr_lang.strip() or "eng",
                            combine_output=True,
                        )
                        txt_path = Path(out_txt)
                        txt_bytes = txt_path.read_bytes()
                        st.success(f"[✓] OCR complete: {txt_path.name}")
                        st.text_area("Extracted Text", value=preview, height=220)
                        st.download_button(
                            label=f"SAVE {txt_path.name}",
                            data=txt_bytes,
                            file_name=txt_path.name,
                            mime="text/plain",
                            use_container_width=True,
                        )
                    except Exception as exc:
                        st.error(f"[-] OCR failed: {exc}")


# --------------------------------------------------------------------------- #
# TAB 6: SESSION HISTORY
# --------------------------------------------------------------------------- #
with tab_hist:
    with st.container(border=True):
        st.markdown(
            '<div class="mc-panel-head"><div class="mc-panel-title">SESSION TELEMETRY HISTORY</div>'
            '<div class="mc-panel-sub">Downloads & conversions processed in this cloud session</div></div>',
            unsafe_allow_html=True,
        )
        if not st.session_state.mc_history:
            st.info("No operations recorded in this session yet.")
        else:
            for idx, rec in enumerate(st.session_state.mc_history):
                c1, c2 = st.columns([4, 1])
                c1.markdown(
                    f"**[{rec['tool']}]** `{rec['file_name']}` via `{rec['engine']}`  \n"
                    f"<span style='color:#6C7E78;font-size:11px;'>{rec['source']}</span>",
                    unsafe_allow_html=True,
                )
                c2.download_button(
                    label="SAVE",
                    data=rec["data"],
                    file_name=rec["file_name"],
                    mime=rec.get("mime", "application/octet-stream"),
                    key=f"hist_dl_{idx}",
                    use_container_width=True,
                )
