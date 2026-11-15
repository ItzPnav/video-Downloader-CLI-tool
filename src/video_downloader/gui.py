# /* Hallmark · pre-emit critique: P5 H5 E5 S5 R5 V5 */
"""
Mission Control (Cyber Terminal) Visual UI Frontend for Tool-Kit CLI.

Synthesized via Design & Motion Studio:
- Orchestrator: design-lead
- Structure & Anti-Slop Discipline: hallmark (P5 H5 E5 S5 R5 V5)
- Micro-Interactions & Keyframes: frontend-ui-animator
- Aesthetic Dialect: mission-control-design (strictly isolated from apple-design)

Provides a 100% Python, WebSocket-driven Web & Desktop operations console
powered by NiceGUI + FastAPI across all 5 Tool-Kit CLI engines:
  01 // 4-Agent Concurrent Extraction Race Cockpit (LangGraph + psutil)
  02 // Media Converter & Multi-Clip Video Combiner (FFmpeg + Pillow)
  03 // Comic & Gallery Chapter Scraper (Anti-Bot + PDF/CBZ)
  04 // Image Folder Archive Packager (PDF / CBZ + Recursive Batch)
  05 // Tesseract OCR Optical Text Extraction Engine
  06 // Per-Tool Storage Matrix & Persistent Telemetry History
"""

from __future__ import annotations

import asyncio
import json
import os
import queue
import sys
import threading
import time
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .utils import (
    ROOT,
    auto_separate_all_tool_dirs,
    get_config_dir,
    get_download_dir,
    get_tool_output_dir,
    get_version,
    is_termux,
    load_config,
    reset_all_tool_dirs_to_defaults,
     safe_filename,
    save_config,
    set_tool_output_dir,
    write_history,
)

UI_DIR = Path(__file__).resolve().parent / "ui"
TOKENS_CSS_PATH = UI_DIR / "tokens.css"
TOKENS_JSON_PATH = UI_DIR / "design-tokens.json"
CONTRACT_MD_PATH = UI_DIR / "CONTRACT.md"
DESIGN_MD_PATH = UI_DIR / "design.md"


def load_design_tokens() -> dict[str, Any]:
    """Load the W3C DTCG Mission Control design tokens contract."""
    if TOKENS_JSON_PATH.is_file():
        try:
            return json.loads(TOKENS_JSON_PATH.read_text(encoding="utf-8"))
        except Exception:
            pass
    return {}


def load_mission_control_css() -> str:
    """Load the Mission Control CSS tokens and Quasar zero-radius overrides."""
    if TOKENS_CSS_PATH.is_file():
        try:
            return TOKENS_CSS_PATH.read_text(encoding="utf-8")
        except Exception:
            pass
    return "*, *::before, *::after { border-radius: 0 !important; }"


def is_nicegui_available() -> bool:
    """Return True if NiceGUI is installed in the current Python environment."""
    try:
        import nicegui  # noqa: F401
        return True
    except ImportError:
        return False


def is_pywebview_available() -> bool:
    """Return True if pywebview is installed for standalone desktop window mode."""
    try:
        import webview  # noqa: F401
        return True
    except ImportError:
        return False


def acquire_termux_wake_lock() -> bool:
    """Acquire Termux wake-lock on Android so backgrounding Termux for Chrome does not throttle races."""
    if not is_termux():
        return False
    import shutil
    import subprocess
    if shutil.which("termux-wake-lock"):
        try:
            subprocess.Popen(
                ["termux-wake-lock"],
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
            )
            return True
        except Exception:
            return False
    return False


# ============================================================================
# MISSION CONTROL UI BUILDER (NICEGUI)
# ============================================================================

def build_mission_control_dashboard() -> None:
    """Construct the full 6-sector Mission Control interface inside the active NiceGUI page context."""
    from nicegui import ui

    from .cli import system_open, valid_url
    from .comic_scraper import scrape_and_download_comic
    from .converter import (
         AUDIO_EXTENSIONS,
        IMAGE_EXTENSIONS,
        TEXT_EXTENSIONS,
        VIDEO_EXTENSIONS,
        batch_convert_gifs_to_mp4,
        batch_convert_videos_to_gif,
        combine_videos,
        convert_audio_to_audio,
        convert_gif_to_mp4,
        convert_image,
        convert_text_to_pdf,
        convert_video_to_audio,
        convert_video_to_gif,
        detect_hardware_encoder,
        remux_or_transcode_video,
    )
    from .downloader import download as execute_download, find_ffmpeg
    from .ocr import find_tesseract_binary, get_tesseract_install_hint, is_tesseract_available, run_ocr
    from .packager import batch_pack_folders, get_sorted_images_in_folder, images_to_cbz, images_to_pdf
    from .race_controller import ExtractionRaceController
    from .router import identify

    # 1. Inject Mission Control CSS, CRT scanline layer, and ZULU Clock script
    css_text = load_mission_control_css()
    ui.add_head_html(f"<style>{css_text}</style>")
    ui.add_body_html('<div class="scanline" aria-hidden="true"></div>')
    ui.add_head_html(
        """
        <script>
        function updateMissionZuluClock() {
            const el = document.getElementById('mc-zulu-clock-val');
            if (el) {
                const now = new Date();
                const utc = now.toISOString().slice(11, 19);
                el.textContent = utc + ' ZULU';
            }
        }
        setInterval(updateMissionZuluClock, 1000);
        document.addEventListener('DOMContentLoaded', updateMissionZuluClock);
        function toggleMissionTheme(isLight) {
            if (isLight) {
                document.documentElement.setAttribute('data-theme', 'light');
            } else {
                document.documentElement.removeAttribute('data-theme');
            }
        }
        </script>
        """
    )

    config = load_config()
    event_queue: "queue.Queue[Callable[[], None]]" = queue.Queue()

    def dispatch_ui(fn: Callable[[], None]) -> None:
        """Schedule a UI mutation safely from a worker thread."""
        event_queue.put(fn)

    def drain_ui_queue() -> None:
        while not event_queue.empty():
            try:
                callback = event_queue.get_nowait()
                callback()
            except Exception:
                pass

    ui.timer(0.1, drain_ui_queue)

    # ------------------------------------------------------------------------
    # REUSABLE MISSION CONTROL COMPONENTS
    # ------------------------------------------------------------------------

    def create_rocker_switch(
        label_text: str,
        initial: bool,
        on_toggle: Optional[Callable[[bool], None]] = None,
        sub_label: str = "",
    ):
        """Render a physical Mission Control mechanical rocker switch with phosphor bloom."""
        state = {"checked": bool(initial)}

        def _mount_btn() -> None:
            btn = ui.element("button").classes(
                f"rocker-switch shrink-0 {'active' if state['checked'] else ''}"
            )
            btn.props('type="button" role="switch"')

            def _handle_click() -> None:
                state["checked"] = not state["checked"]
                if state["checked"]:
                    btn.classes(add="active")
                else:
                    btn.classes(remove="active")
                if on_toggle:
                    on_toggle(state["checked"])

            btn.on("click", _handle_click)

        if label_text:
            with ui.row().classes("items-center justify-between py-1 gap-2 no-wrap min-w-0"):
                with ui.column().classes("gap-0 min-w-0 flex-1 overflow-hidden"):
                    ui.label(label_text).style(
                        "font-size: 11px; font-weight: 600; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                    )
                    if sub_label:
                        ui.label(sub_label).style(
                            "font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                        )
                _mount_btn()
        else:
            _mount_btn()

        return state

    def create_fuel_gauge(label_prefix: str = "Progress", initial_status: str = "Ready"):
        """Render a crawling striped Mission Control progress bar with simple status text."""
        with ui.element("div").classes("gauge-block") as block:
            with ui.element("div").classes("gauge-top"):
                status_lbl = ui.label(initial_status).classes("gauge-status-text").style(
                    "font-size: 11px; letter-spacing: 0.04em; color: var(--muted);"
                )
                pct_lbl = ui.label("0%").classes("val").style(
                    "color: var(--green); font-size: 13px; font-weight: 700;"
                )
            with ui.element("div").classes("gauge-track"):
                fill_el = ui.element("div").classes("gauge-fill").style("width: 0%;")

        def set_gauge(pct: int, text: str) -> None:
            clamped = max(0, min(100, int(pct)))
            status_lbl.set_text(text)
            pct_lbl.set_text(f"{clamped}%")
            fill_el.style(f"width: {clamped}%;")

        return block, set_gauge

    # Custom System Dialog Modal (Law #5: No window.alert / window.confirm)
    with ui.dialog() as sys_dialog, ui.card().classes("mc-panel p-0 w-[440px] max-w-[95vw]"):
        with ui.row().classes("w-full items-center justify-between px-4 py-2").style(
            "background: var(--panel-2); border-bottom: 1px solid var(--line);"
        ):
            dialog_eyebrow = ui.label("NOTICE").classes("eyebrow")
            ui.button("Close", on_click=sys_dialog.close).classes("btn-tactical-secondary py-1 px-2")
        with ui.column().classes("p-4 gap-3 w-full"):
            dialog_title = ui.label("STATUS").classes("display-title text-xl")
            dialog_msg = ui.label("").style("font-size: 12px; color: var(--ink); line-height: 1.5; word-break: break-all;")
            with ui.row().classes("w-full justify-end gap-2 pt-2"):
                ui.button("OK", on_click=sys_dialog.close).classes("btn-tactical-primary")

    def show_system_modal(title: str, message: str, is_fault: bool = False) -> None:
        dialog_eyebrow.set_text("ERROR" if is_fault else "NOTICE")
        dialog_title.set_text(title)
        dialog_title.style(f"color: {'var(--red)' if is_fault else 'var(--ink)'};")
        dialog_msg.set_text(message)
        sys_dialog.open()

    # Custom Server-Side Local Disk Browser Modal
    browser_state: dict[str, Any] = {
        "current_dir": get_download_dir(),
        "mode": "file",
        "allowed_exts": None,
        "on_select": None,
        "title": "Select File or Folder",
    }

    with ui.dialog() as disk_dialog, ui.card().classes("mc-panel p-0 w-[680px] max-w-[96vw]"):
        with ui.row().classes("w-full items-center justify-between px-4 py-2").style(
            "background: var(--panel-2); border-bottom: 1px solid var(--line);"
        ):
            disk_header_lbl = ui.label("SELECT PATH").classes("eyebrow")
            ui.button("Close", on_click=disk_dialog.close).classes("btn-tactical-secondary")

        with ui.column().classes("p-4 gap-3 w-full"):
            with ui.row().classes("w-full items-center gap-2"):
                disk_path_input = ui.input("Folder Path").classes("mc-input flex-grow").props("dense outlined")
                ui.button("Go", on_click=lambda: _navigate_disk_to(Path(disk_path_input.value))).classes("btn-tactical-secondary")
                ui.button("Up", on_click=lambda: _navigate_disk_to(browser_state["current_dir"].parent)).classes("btn-tactical-secondary")

            with ui.row().classes("w-full items-center gap-2 flex-wrap"):
                ui.button("Downloads", on_click=lambda: _navigate_disk_to(get_download_dir())).classes("btn-tactical-secondary")
                ui.button("Home", on_click=lambda: _navigate_disk_to(Path.home())).classes("btn-tactical-secondary")
                ui.button("Project", on_click=lambda: _navigate_disk_to(ROOT)).classes("btn-tactical-secondary")
                if Path("/sdcard/Download").exists():
                    ui.button("SDCard", on_click=lambda: _navigate_disk_to(Path("/sdcard/Download"))).classes("btn-tactical-secondary")

            disk_select_folder_row = ui.row().classes("w-full")
            disk_list_container = ui.column().classes("w-full gap-1 max-h-[340px] overflow-y-auto pr-1")

    def _render_disk_entries() -> None:
        curr: Path = browser_state["current_dir"]
        disk_path_input.value = str(curr)
        disk_select_folder_row.clear()
        disk_list_container.clear()

        mode = browser_state["mode"]
        exts = browser_state["allowed_exts"]

        if mode in ("folder", "any"):
            with disk_select_folder_row:
                def _pick_current_folder(target_dir=curr) -> None:
                    disk_dialog.close()
                    if browser_state["on_select"]:
                        browser_state["on_select"](target_dir)

                ui.button(
                    f"Use This Folder: {curr.name or str(curr)}",
                    on_click=_pick_current_folder,
                ).classes("btn-tactical-primary w-full")

        dirs: list[Path] = []
        files: list[Path] = []
        try:
            for entry in curr.iterdir():
                if entry.name.startswith("."):
                    continue
                if entry.is_dir():
                    dirs.append(entry)
                elif entry.is_file() and mode in ("file", "any"):
                    if exts is None or entry.suffix.lower() in exts:
                        files.append(entry)
        except Exception as err:
            with disk_list_container:
                ui.label(f"[-] Access denied: {err}").style("color: var(--red); font-size: 11px;")
            return

        dirs.sort(key=lambda p: p.name.lower())
        files.sort(key=lambda p: p.name.lower())

        with disk_list_container:
            if not dirs and not files:
                ui.label("Empty folder").style("color: var(--muted); font-size: 11px; padding: 12px;")
                return

            for d in dirs[:150]:
                with ui.row().classes("tactical-row w-full items-center justify-between px-3 py-2 cursor-pointer"):
                    ui.label(f"📁 {d.name}/").style("color: var(--amber); font-size: 12px; font-weight: 600;")
                    ui.button("Open", on_click=lambda _e, target=d: _navigate_disk_to(target)).classes("btn-tactical-secondary py-1 px-2")

            for f in files[:200]:
                try:
                    sz_mb = f.stat().st_size / (1024 * 1024)
                    sz_str = f"{sz_mb:.1f} MB"
                except Exception:
                    sz_str = ""
                with ui.row().classes("tactical-row selected w-full items-center justify-between px-3 py-2"):
                    ui.label(f.name).style("color: var(--ink); font-size: 12px; word-break: break-all;")
                    with ui.row().classes("items-center gap-2 no-wrap"):
                        if sz_str:
                            ui.label(sz_str).classes("mc-badge-muted")
                        def _pick_file(_e=None, target=f) -> None:
                            disk_dialog.close()
                            if browser_state["on_select"]:
                                browser_state["on_select"](target)
                        ui.button("Select", on_click=_pick_file).classes("btn-tactical-primary py-1 px-3")

    def _navigate_disk_to(new_dir: Path) -> None:
        try:
            resolved = new_dir.resolve()
            if resolved.is_dir():
                browser_state["current_dir"] = resolved
                _render_disk_entries()
            elif resolved.is_file():
                browser_state["current_dir"] = resolved.parent
                _render_disk_entries()
        except Exception:
            pass

    def open_disk_browser(
        mode: str,
        on_select: Callable[[Path], None],
        title: str = "Select Path",
        allowed_exts: Optional[set[str]] = None,
        initial_dir: Optional[Path] = None,
    ) -> None:
        browser_state["mode"] = mode
        browser_state["on_select"] = on_select
        browser_state["allowed_exts"] = allowed_exts
        browser_state["title"] = title
        start_dir = initial_dir or browser_state.get("current_dir") or get_download_dir()
        if start_dir.is_file():
            start_dir = start_dir.parent
        if not start_dir.exists():
            start_dir = get_download_dir()
        browser_state["current_dir"] = start_dir.resolve()
        disk_header_lbl.set_text(title.upper())
        _render_disk_entries()
        disk_dialog.open()

    # ------------------------------------------------------------------------
    # TOP BAR (Simple & Clean)
    # ------------------------------------------------------------------------
    ffmpeg_path = find_ffmpeg()
    try:
        enc_name, enc_desc, is_hw = detect_hardware_encoder(ffmpeg_path)
    except Exception:
        enc_name, enc_desc, is_hw = ("libx264", "CPU Software Fallback", False)
    tess_ready = is_tesseract_available()

    with ui.element("header").classes("mc-panel w-full px-5 py-3").style(
        "border-top: none; border-left: none; border-right: none; border-bottom: 1px solid var(--line);"
    ):
        with ui.row().classes("w-full max-w-[1360px] mx-auto items-center justify-between gap-4 flex-wrap"):
            with ui.row().classes("items-center gap-3"):
                ui.label("TOOL-KIT").classes("display-title text-3xl tracking-wider")
                ui.label(f"v{get_version()}").classes("mc-badge-muted")

            with ui.row().classes("items-center gap-2 flex-wrap"):
                ui.label(f"FFmpeg: {'Ready' if ffmpeg_path else 'Missing'}").classes(
                    "mc-badge-green" if ffmpeg_path else "mc-badge-red"
                )
                ui.label(f"Encoder: {'GPU' if is_hw else 'CPU'}").classes(
                    "mc-badge-green" if is_hw else "mc-badge-amber"
                )
                ui.label(f"OCR: {'Ready' if tess_ready else 'Not Installed'}").classes(
                    "mc-badge-green" if tess_ready else "mc-badge-muted"
                )

            with ui.row().classes("items-center gap-4"):
                create_rocker_switch(
                    "Light Mode",
                    initial=False,
                    on_toggle=lambda is_light: ui.run_javascript(f"toggleMissionTheme({str(is_light).lower()});"),
                )
                ui.html(
                    '<span class="zulu-clock" style="font-family: \'JetBrains Mono\', monospace; font-size: 11px; color: var(--muted);">'
                    '<span id="mc-zulu-clock-val" style="color: var(--ink); font-weight: 600;">--:--:--</span>'
                    '</span>'
                )

    # ------------------------------------------------------------------------
    # SIMPLE 6-TAB NAVIGATION BAR
    # ------------------------------------------------------------------------
    sectors = [
        ("01", "1. Video Downloader"),
        ("02", "2. Converter & Merger"),
        ("03", "3. Comic Scraper"),
        ("04", "4. Folder to PDF/CBZ"),
        ("05", "5. Image OCR"),
        ("06", "6. Folders & History"),
    ]

    nav_buttons: dict[str, Any] = {}
    sector_containers: dict[str, Any] = {}

    def switch_sector(code: str) -> None:
        for k, btn in nav_buttons.items():
            if k == code:
                btn.classes(add="active")
            else:
                btn.classes(remove="active")
        for k, container in sector_containers.items():
            container.set_visibility(k == code)

    with ui.column().classes("w-full max-w-[1360px] mx-auto px-4 py-4 gap-4"):
        with ui.element("div").classes("sector-nav-grid"):
            for code, title in sectors:
                with ui.element("button").classes(
                    f"sector-nav-btn {'active' if code == '01' else ''}"
                ) as b:
                    b.on("click", lambda _e, c=code: switch_sector(c))
                    ui.label(title).classes("sector-nav-title")
                nav_buttons[code] = b

        # ====================================================================
        # TAB 01 // VIDEO DOWNLOADER
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec01:
            sector_containers["01"] = sec01

            with ui.row().classes("w-full gap-4 items-stretch flex-wrap"):
                # Left: Main Download Card
                with ui.column().classes("mc-panel p-5 gap-4 flex-[2] min-w-[320px]"):
                    with ui.row().classes("w-full items-center justify-between gap-2"):
                        ui.label("DOWNLOAD VIDEO").classes("display-title text-2xl")
                        race_route_badge = ui.label("Paste a URL to start").classes("mc-badge-muted")

                    race_url_input = ui.input(
                        "Video or Page URL",
                        placeholder="https://...",
                    ).classes("mc-input w-full").props("outlined dense")

                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        race_quality_sel = ui.select(
                            options={
                                "Best (bv*+ba/b)": "Best Available",
                                "1080p": "1080p Full HD",
                                "720p": "720p HD",
                                "480p": "480p",
                                "360p": "360p",
                            },
                            value="Best (bv*+ba/b)",
                            label="Quality",
                        ).classes("mc-input flex-1 min-w-[150px]").props("outlined dense")

                        race_conflict_sel = ui.select(
                            options={
                                "keep_both": "Keep Both (Auto-Number)",
                                "replace": "Overwrite Existing",
                                "skip": "Skip if Exists",
                            },
                            value="keep_both",
                            label="If File Exists",
                        ).classes("mc-input flex-1 min-w-[170px]").props("outlined dense")

                        race_timeout_num = ui.number(
                            label="Timeout (sec)",
                            value=float(config.get("race_timeout", 20)),
                            min=5,
                            max=120,
                        ).classes("mc-input w-[130px]").props("outlined dense")

                    _, update_race_gauge = create_fuel_gauge("Download", "Ready")

                    with ui.row().classes("w-full items-center justify-between gap-3 pt-1 flex-wrap"):
                        ui.button(
                            "Change Output Folder",
                            on_click=lambda: open_disk_browser(
                                mode="folder",
                                title="Select Video Download Folder",
                                on_select=lambda p: (
                                    set_tool_output_dir("video", p),
                                    show_system_modal("Folder Updated", f"Videos will be saved to:\n{p}"),
                                ),
                            ),
                        ).classes("btn-tactical-secondary")
                        race_start_btn = ui.button("Download Video").classes("btn-tactical-primary px-6")

                    race_result_summary = ui.label("").style("font-size: 12px; color: var(--muted);")
                    race_action_row = ui.row().classes("gap-2 items-center")

                # Right: Extractors (Toggle + Live Status in one clean list)
                with ui.column().classes("mc-panel p-5 gap-3 flex-1 min-w-[280px]"):
                    ui.label("EXTRACTORS").classes("display-title text-2xl")
                    ui.label("Runs enabled extractors in parallel; first match wins.").style(
                        "font-size: 11px; color: var(--muted);"
                    )

                    agent_cards: dict[str, dict[str, Any]] = {}
                    tier_rows_cfg = [
                        ("ytdlp", "yt-dlp", "YouTube, Vimeo & 1,000+ sites", config.get("use_ytdlp", True)),
                        ("scrapling", "Scrapling", "Stealth anti-bot extractor", config.get("use_scrapling", True)),
                        ("static", "HTML Scanner", "Direct <video> & page parser", config.get("use_static_scanner", True)),
                        ("browser", "Browser Sniffer", "Headless Chrome stream capture", config.get("use_browser", True)),
                    ]
                    tier_switches: dict[str, dict[str, bool]] = {}

                    for t_key, t_title, t_sub, t_init in tier_rows_cfg:
                        with ui.row().classes("tactical-row w-full items-center justify-between px-3 py-2 gap-2 no-wrap") as row_el:
                            with ui.column().classes("gap-0 min-w-0 flex-1"):
                                with ui.row().classes("items-center gap-2 no-wrap"):
                                    ui.label(t_title).style("font-size: 12px; font-weight: 700; color: var(--ink);")
                                    badge_el = ui.label("Idle").classes("mc-badge-muted")
                                ui.label(t_sub).style(
                                    "font-size: 10px; color: var(--muted); white-space: nowrap; overflow: hidden; text-overflow: ellipsis;"
                                )
                            sw_state = create_rocker_switch("", initial=t_init)
                            tier_switches[t_key] = sw_state
                            agent_cards[t_key] = {"card": row_el, "badge": badge_el}

                    sw_ytdlp = tier_switches["ytdlp"]
                    sw_scrapling = tier_switches["scrapling"]
                    sw_static = tier_switches["static"]
                    sw_browser = tier_switches["browser"]

            def _set_agent_card_state(tier: str, status: str, pid: Optional[int] = None, score: Optional[int] = None) -> None:
                info = agent_cards.get(tier)
                if not info:
                    return
                card = info["card"]
                badge = info["badge"]
                card.classes(remove="selected completed fault active-amber")
                badge.classes(remove="mc-badge-green mc-badge-amber mc-badge-red mc-badge-muted")

                st_upper = status.upper()
                badge.set_text(status)
                if "WIN" in st_upper or "SCORE" in st_upper or "MATCH" in st_upper:
                    card.classes(add="completed")
                    badge.classes(add="mc-badge-green")
                elif "RUN" in st_upper or "RACING" in st_upper or "SPAWN" in st_upper or "SCAN" in st_upper:
                    card.classes(add="active-amber")
                    badge.classes(add="mc-badge-amber")
                elif "KILL" in st_upper or "STOP" in st_upper or "TIMEOUT" in st_upper or "FAIL" in st_upper:
                    card.classes(add="fault")
                    badge.classes(add="mc-badge-red")
                else:
                    badge.classes(add="mc-badge-muted")

            def _start_extraction_race() -> None:
                raw_url = (race_url_input.value or "").strip()
                if not valid_url(raw_url):
                    show_system_modal(
                        "Invalid URL",
                        "Please enter a valid URL starting with http:// or https://",
                        is_fault=True,
                    )
                    return

                route = identify(raw_url)
                race_route_badge.set_text(f"Site: {route.platform}")
                race_route_badge.classes(remove="mc-badge-muted", add="mc-badge-green")

                for t_key in agent_cards:
                    _set_agent_card_state(t_key, "Idle")

                update_race_gauge(8, f"Scanning {route.platform}...")
                race_result_summary.set_text("")
                race_action_row.clear()
                race_start_btn.disable()

                q_val = race_quality_sel.value
                req_quality = None if not q_val or q_val.startswith("Best") else q_val
                conflict_pol = race_conflict_sel.value or "keep_both"
                timeout_s = float(race_timeout_num.value or 20.0)
                conf_thresh = int(config.get("confidence_threshold", 50))

                def _on_race_event(ev: dict[str, Any]) -> None:
                    etype = ev.get("type", "")
                    if etype == "tier_spawned":
                        t = ev.get("tier", "")
                        dispatch_ui(lambda t=t: _set_agent_card_state(t, "Scanning"))
                    elif etype == "tier_tick":
                        statuses = ev.get("statuses", {})
                        elapsed = ev.get("elapsed_ms", 0)
                        pct = min(65, 10 + int((elapsed / max(1000, timeout_s * 1000)) * 55))
                        def _apply_tick() -> None:
                            update_race_gauge(pct, f"Searching stream ({elapsed / 1000:.1f}s)...")
                            for tk, st in statuses.items():
                                _set_agent_card_state(tk, st)
                        dispatch_ui(_apply_tick)
                    elif etype == "tier_result":
                        t = ev.get("tier", "")
                        ok = ev.get("success", False)
                        dispatch_ui(
                            lambda t=t, ok=ok: _set_agent_card_state(
                                t, "Matched" if ok else "No Match"
                            )
                        )
                    elif etype == "tier_killed":
                        t = ev.get("tier", "")
                        dispatch_ui(lambda t=t: _set_agent_card_state(t, "Stopped"))

                def _worker() -> None:
                    acquire_termux_wake_lock()
                    try:
                        controller = ExtractionRaceController(
                            url=raw_url,
                            requested_quality=req_quality,
                            timeout=timeout_s,
                            confidence_threshold=conf_thresh,
                            no_ytdlp=not sw_ytdlp["checked"],
                            no_scrapling=not sw_scrapling["checked"],
                            no_static=not sw_static["checked"],
                            no_browser=not sw_browser["checked"],
                            prefer_gui=False,
                            on_event=_on_race_event,
                        )
                        result = controller.run_race()

                        if result.candidate and result.winner_engine:
                            win_tier = result.winner_engine
                            cand = result.candidate

                            def _mark_winner() -> None:
                                _set_agent_card_state(win_tier, "Winner")
                                update_race_gauge(70, f"Downloading via {win_tier}...")

                            dispatch_ui(_mark_winner)

                            out_file = execute_download(
                                cand,
                                filename=cand.metadata.get("title", "video"),
                                requested_quality=req_quality,
                                conflict_policy=conflict_pol,
                                progress_callback=lambda p, m: dispatch_ui(
                                    lambda p=p, m=m: update_race_gauge(70 + int(p * 0.3), m)
                                ),
                            )

                            write_history({
                                "url": raw_url,
                                "platform": route.platform,
                                "engine": win_tier,
                                "quality": req_quality,
                                "output": str(out_file) if out_file else None,
                                "race_duration_ms": result.duration_ms,
                            })

                            def _finish_ok() -> None:
                                update_race_gauge(100, f"Saved: {Path(out_file).name if out_file else 'Skipped'}")
                                race_result_summary.set_text(f"[✓] Saved to: {out_file}")
                                race_result_summary.style("color: var(--green); font-size: 12px; font-weight: 600;")
                                race_action_row.clear()
                                if out_file and Path(out_file).exists():
                                    with race_action_row:
                                        ui.button(
                                            "Play Video",
                                            on_click=lambda p=out_file: system_open(Path(p)),
                                        ).classes("btn-tactical-primary")
                                        ui.button(
                                            "Open Folder",
                                            on_click=lambda p=out_file: system_open(Path(p).parent),
                                        ).classes("btn-tactical-secondary")
                                race_start_btn.enable()
                                _refresh_history_panel()

                            dispatch_ui(_finish_ok)
                        else:
                            def _finish_fail() -> None:
                                reason = "Timed out" if result.timed_out else "No video stream found"
                                update_race_gauge(0, reason)
                                race_result_summary.set_text(f"[-] {reason}. Try enabling Browser Sniffer or increasing timeout.")
                                race_result_summary.style("color: var(--red); font-size: 12px;")
                                race_start_btn.enable()

                            dispatch_ui(_finish_fail)
                    except Exception as exc:
                        def _finish_err(err_msg=str(exc)) -> None:
                            update_race_gauge(0, "Error")
                            race_result_summary.set_text(f"[-] {err_msg}")
                            race_result_summary.style("color: var(--red); font-size: 12px;")
                            race_start_btn.enable()
                            show_system_modal("Download Failed", err_msg, is_fault=True)

                        dispatch_ui(_finish_err)

                threading.Thread(target=_worker, daemon=True).start()

            race_start_btn.on("click", _start_extraction_race)

        # ====================================================================
        # TAB 02 // MEDIA CONVERTER & VIDEO COMBINER
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec02:
            sector_containers["02"] = sec02
            sec02.set_visibility(False)

            with ui.row().classes("w-full gap-4 items-start flex-wrap"):
                # 2A: Format Converter
                with ui.column().classes("mc-panel p-5 gap-3 flex-1 min-w-[340px]"):
                    ui.label("CONVERT MEDIA").classes("display-title text-2xl")

                    with ui.row().classes("w-full items-center gap-2"):
                        conv_input_path = ui.input(
                            "Source File or Folder",
                            placeholder="Select video, audio, GIF, image, or text...",
                        ).classes("mc-input flex-grow").props("outlined dense")
                        ui.button(
                            "File",
                            on_click=lambda: open_disk_browser(
                                mode="file",
                                title="Select File to Convert",
                                on_select=lambda p: conv_input_path.set_value(str(p)),
                            ),
                        ).classes("btn-tactical-secondary")
                        ui.button(
                            "Folder",
                            on_click=lambda: open_disk_browser(
                                mode="folder",
                                title="Select Folder to Batch Convert",
                                on_select=lambda p: conv_input_path.set_value(str(p)),
                            ),
                        ).classes("btn-tactical-secondary")

                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        conv_target_sel = ui.select(
                            options=["gif", "mp3", "mp4", "wav", "flac", "aac", "ogg", "png", "jpg", "webp", "pdf"],
                            value="gif",
                            label="Output Format",
                        ).classes("mc-input flex-1 min-w-[120px]").props("outlined dense")

                        conv_hw_sel = ui.select(
                            options=["auto", "gpu", "nvenc", "qsv", "amf", "cpu"],
                            value=config.get("video_hwaccel", "auto"),
                            label="Hardware",
                        ).classes("mc-input flex-1 min-w-[110px]").props("outlined dense")

                        conv_preset_sel = ui.select(
                            options=["ultrafast", "veryfast", "fast", "medium", "slow"],
                            value=config.get("encoding_preset", "ultrafast"),
                            label="Speed",
                        ).classes("mc-input flex-1 min-w-[120px]").props("outlined dense")

                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        conv_fps_num = ui.number(label="GIF FPS", value=30, min=5, max=60).classes("mc-input flex-1").props("outlined dense")
                        conv_res_num = ui.number(label="GIF Height (px)", value=504, min=120, max=2160).classes("mc-input flex-1").props("outlined dense")
                        conv_colors_sel = ui.select(
                            options={256: "256 Colors", 128: "128 Colors", 64: "64 Colors"},
                            value=256,
                            label="GIF Colors",
                        ).classes("mc-input flex-1").props("outlined dense")

                    conv_reencode_sw = create_rocker_switch(
                        "Force Re-encode",
                        initial=False,
                        sub_label="Off = fast stream copy when compatible",
                    )

                    _, update_conv_gauge = create_fuel_gauge("Convert", "Ready")
                    conv_status_lbl = ui.label("").style("font-size: 11px; color: var(--muted);")

                    def _run_conversion() -> None:
                        src_val = (conv_input_path.value or "").strip()
                        if not src_val:
                            show_system_modal("Missing Input", "Please select a file or folder first.", is_fault=True)
                            return
                        src_path = Path(src_val).resolve()
                        if not src_path.exists():
                            show_system_modal("Path Not Found", f"File or folder not found:\n{src_path}", is_fault=True)
                            return

                        target_fmt = (conv_target_sel.value or "gif").lower()
                        fps_val = int(conv_fps_num.value or 30)
                        height_val = int(conv_res_num.value or 504)
                        colors_val = int(conv_colors_sel.value or 256)
                        hw_val = conv_hw_sel.value or "auto"
                        preset_val = conv_preset_sel.value or "ultrafast"
                        force_re = conv_reencode_sw["checked"]

                        out_dir = get_tool_output_dir("converter")
                        out_dir.mkdir(parents=True, exist_ok=True)

                        def _prog(pct: int, msg: str) -> None:
                            dispatch_ui(lambda pct=pct, msg=msg: update_conv_gauge(pct, msg))

                        def _conv_worker() -> None:
                            try:
                                if src_path.is_dir():
                                    if target_fmt == "gif":
                                        outs = batch_convert_videos_to_gif(
                                            src_path, out_dir, fps=fps_val, height=height_val, colors=colors_val, progress_callback=_prog
                                        )
                                    elif target_fmt == "mp4":
                                        outs = batch_convert_gifs_to_mp4(src_path, out_dir, progress_callback=_prog)
                                    else:
                                        raise ValueError("Folder batch mode supports Video -> GIF or GIF -> MP4.")
                                    msg_done = f"[✓] Converted {len(outs)} file(s) to {out_dir}"
                                else:
                                    out_path = out_dir / f"{src_path.stem}.{target_fmt}"
                                    in_suf = src_path.suffix.lower()
                                    if target_fmt == "gif":
                                        convert_video_to_gif(
                                            src_path, out_path, fps=fps_val, height=height_val, colors=colors_val, progress_callback=_prog
                                        )
                                    elif target_fmt == "pdf" and in_suf in TEXT_EXTENSIONS:
                                        convert_text_to_pdf(src_path, out_path, progress_callback=_prog)
                                    elif target_fmt in ("mp3", "aac", "wav", "flac", "ogg", "m4a", "opus"):
                                        if in_suf in AUDIO_EXTENSIONS:
                                            convert_audio_to_audio(src_path, out_path, audio_format=target_fmt, progress_callback=_prog)
                                        else:
                                            convert_video_to_audio(src_path, out_path, audio_format=target_fmt, progress_callback=_prog)
                                    elif in_suf == ".gif" and target_fmt == "mp4":
                                        convert_gif_to_mp4(src_path, out_path, progress_callback=_prog)
                                    elif target_fmt in ("png", "jpg", "jpeg", "webp", "bmp", "tiff"):
                                        convert_image(src_path, out_path, progress_callback=_prog)
                                    elif target_fmt == "mp4":
                                        remux_or_transcode_video(
                                            src_path, out_path, reencode=force_re, preset=preset_val, hwaccel=hw_val, progress_callback=_prog
                                        )
                                    else:
                                        raise ValueError(f"Unsupported conversion: {in_suf} -> .{target_fmt}")
                                    msg_done = f"[✓] Saved: {out_path}"

                                def _done() -> None:
                                    update_conv_gauge(100, "Done")
                                    conv_status_lbl.set_text(msg_done)
                                    conv_status_lbl.style("color: var(--green); font-size: 11px; font-weight: 600;")

                                dispatch_ui(_done)
                            except Exception as exc:
                                def _err(e_str=str(exc)) -> None:
                                    update_conv_gauge(0, "Error")
                                    conv_status_lbl.set_text(f"[-] {e_str}")
                                    conv_status_lbl.style("color: var(--red); font-size: 11px;")
                                    show_system_modal("Conversion Failed", e_str, is_fault=True)

                                dispatch_ui(_err)

                        threading.Thread(target=_conv_worker, daemon=True).start()

                    ui.button("Convert", on_click=_run_conversion).classes("btn-tactical-primary w-full")

                # 2B: Multi-Clip Video Combiner
                with ui.column().classes("mc-panel p-5 gap-3 flex-1 min-w-[340px]"):
                    ui.label("COMBINE VIDEOS").classes("display-title text-2xl")

                    combine_queue: list[Path] = []
                    combine_list_box = ui.column().classes("w-full gap-1 max-h-[160px] overflow-y-auto p-2").style(
                        "background: var(--bg); border: 1px solid var(--line);"
                    )

                    def _refresh_combine_queue() -> None:
                        combine_list_box.clear()
                        with combine_list_box:
                            if not combine_queue:
                                ui.label("Add 2 or more video clips to merge").style("font-size: 11px; color: var(--muted);")
                                return
                            for idx, clip in enumerate(combine_queue, 1):
                                with ui.row().classes("tactical-row selected w-full items-center justify-between px-2 py-1 gap-2 no-wrap"):
                                    ui.label(f"{idx}. {clip.name}").style(
                                        "font-size: 11px; color: var(--ink); white-space: nowrap; overflow: hidden; text-overflow: ellipsis; min-width: 0; flex: 1;"
                                    )
                                    ui.button(
                                        "Remove",
                                        on_click=lambda _e, i=idx - 1: (combine_queue.pop(i), _refresh_combine_queue()),
                                    ).classes("btn-tactical-danger py-0 px-2 shrink-0")

                    _refresh_combine_queue()

                    def _add_clip_file(p: Path) -> None:
                        if p.is_file() and p not in combine_queue:
                            combine_queue.append(p)
                            _refresh_combine_queue()

                    def _add_clip_folder(folder: Path) -> None:
                        if folder.is_dir():
                            for f in sorted(folder.iterdir(), key=lambda x: x.name.lower()):
                                if f.is_file() and f.suffix.lower() in VIDEO_EXTENSIONS and f not in combine_queue:
                                    combine_queue.append(f)
                            _refresh_combine_queue()

                    with ui.row().classes("w-full gap-2 flex-wrap"):
                        ui.button(
                            "+ Add Video",
                            on_click=lambda: open_disk_browser(
                                mode="file",
                                title="Add Video Clip",
                                allowed_exts=VIDEO_EXTENSIONS,
                                on_select=_add_clip_file,
                            ),
                        ).classes("btn-tactical-secondary flex-1")
                        ui.button(
                            "+ Add Folder",
                            on_click=lambda: open_disk_browser(
                                mode="folder",
                                title="Add Videos from Folder",
                                on_select=_add_clip_folder,
                            ),
                        ).classes("btn-tactical-secondary flex-1")
                        ui.button(
                            "Clear",
                            on_click=lambda: (combine_queue.clear(), _refresh_combine_queue()),
                        ).classes("btn-tactical-danger")

                    with ui.row().classes("w-full gap-3 flex-wrap"):
                        comb_order_sel = ui.select(
                            options={"ascending": "Ascending", "random": "Random Shuffle"},
                            value="ascending",
                            label="Clip Order",
                        ).classes("mc-input flex-1").props("outlined dense")
                        comb_res_sel = ui.select(
                            options=["auto", "1080p", "720p", "4k"],
                            value=config.get("merge_resolution", "auto"),
                            label="Resolution",
                        ).classes("mc-input flex-1").props("outlined dense")

                    comb_reencode_sw = create_rocker_switch(
                        "Force Re-encode",
                        initial=False,
                        sub_label="Off = fast lossless merge when clips match",
                    )

                    _, update_comb_gauge = create_fuel_gauge("Merge", "Ready")
                    comb_status_lbl = ui.label("").style("font-size: 11px; color: var(--muted);")

                    def _run_combine() -> None:
                        if len(combine_queue) < 2:
                            show_system_modal("Need More Clips", "Add at least 2 video files before merging.", is_fault=True)
                            return
                        clips_copy = list(combine_queue)
                        order_val = comb_order_sel.value or "ascending"
                        res_val = None if comb_res_sel.value == "auto" else comb_res_sel.value
                        reencode_val = comb_reencode_sw["checked"]
                        out_dir = get_tool_output_dir("converter")
                        out_dir.mkdir(parents=True, exist_ok=True)
                        first_stem = safe_filename(clips_copy[0].stem)
                        out_file = out_dir / f"combined_{first_stem}_{len(clips_copy)}clips.mp4"

                        def _c_worker() -> None:
                            try:
                                final_p = combine_videos(
                                    clips_copy,
                                    out_file,
                                    reencode=reencode_val,
                                    order=order_val,
                                    preset=conv_preset_sel.value or "ultrafast",
                                    hwaccel=conv_hw_sel.value or "auto",
                                    resolution=res_val,
                                    progress_callback=lambda pct, msg: dispatch_ui(
                                        lambda pct=pct, msg=msg: update_comb_gauge(pct, msg)
                                    ),
                                )
                                def _c_done() -> None:
                                    update_comb_gauge(100, f"Merged {len(clips_copy)} clips")
                                    comb_status_lbl.set_text(f"[✓] Saved: {final_p}")
                                    comb_status_lbl.style("color: var(--green); font-size: 11px; font-weight: 600;")
                                dispatch_ui(_c_done)
                            except Exception as exc:
                                def _c_err(e_str=str(exc)) -> None:
                                    update_comb_gauge(0, "Error")
                                    comb_status_lbl.set_text(f"[-] {e_str}")
                                    comb_status_lbl.style("color: var(--red); font-size: 11px;")
                                    show_system_modal("Merge Failed", e_str, is_fault=True)
                                dispatch_ui(_c_err)

                        threading.Thread(target=_c_worker, daemon=True).start()

                    ui.button("Merge Videos", on_click=_run_combine).classes("btn-tactical-primary w-full")

        # ====================================================================
        # TAB 03 // COMIC & GALLERY SCRAPER
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec03:
            sector_containers["03"] = sec03
            sec03.set_visibility(False)

            with ui.column().classes("mc-panel p-5 gap-3 w-full"):
                ui.label("COMIC & GALLERY DOWNLOADER").classes("display-title text-2xl")

                with ui.row().classes("w-full items-center gap-2"):
                    comic_src_input = ui.input(
                        "Chapter URL or Local Folder",
                        placeholder="https://example.com/chapter-1 or local path...",
                    ).classes("mc-input flex-grow").props("outlined dense")
                    ui.button(
                        "Browse",
                        on_click=lambda: open_disk_browser(
                            mode="any",
                            title="Select HTML File or Folder",
                            on_select=lambda p: comic_src_input.set_value(str(p)),
                        ),
                    ).classes("btn-tactical-secondary")

                with ui.row().classes("w-full gap-3 flex-wrap"):
                    comic_fmt_sel = ui.select(
                        options={"pdf": "PDF Document (.pdf)", "cbz": "Comic Archive (.cbz)", "none": "Images Only"},
                        value="pdf",
                        label="Save As",
                    ).classes("mc-input flex-1 min-w-[160px]").props("outlined dense")

                    comic_order_sel = ui.select(
                        options={"ascending": "Ascending", "random": "Random Shuffle"},
                        value="ascending",
                        label="Page Order",
                    ).classes("mc-input flex-1 min-w-[160px]").props("outlined dense")

                    comic_cookie_input = ui.input(
                        "Cookies.txt (Optional)",
                        placeholder="Optional cookie file path...",
                    ).classes("mc-input flex-1 min-w-[200px]").props("outlined dense")
                    ui.button(
                        "Cookies",
                        on_click=lambda: open_disk_browser(
                            mode="file",
                            title="Select cookies.txt",
                            allowed_exts={".txt"},
                            on_select=lambda p: comic_cookie_input.set_value(str(p)),
                        ),
                    ).classes("btn-tactical-secondary")

                comic_robots_sw = create_rocker_switch(
                    "Respect robots.txt",
                    initial=False,
                )

                _, update_comic_gauge = create_fuel_gauge("Scraper", "Ready")
                comic_result_lbl = ui.label("").style("font-size: 12px; color: var(--muted);")

                def _run_comic_scraper() -> None:
                    src = (comic_src_input.value or "").strip()
                    if not src:
                        show_system_modal("Missing URL", "Enter a chapter URL or select a local folder.", is_fault=True)
                        return
                    fmt_val = None if comic_fmt_sel.value == "none" else comic_fmt_sel.value
                    cookie_val = (comic_cookie_input.value or "").strip() or None
                    order_val = comic_order_sel.value or "ascending"
                    robots_val = comic_robots_sw["checked"]

                    def _cm_worker() -> None:
                        try:
                            out_p = scrape_and_download_comic(
                                source=src,
                                output_base_dir=get_tool_output_dir("comic"),
                                auto_format=fmt_val,
                                cookie_file=cookie_val,
                                respect_robots=robots_val,
                                order=order_val,
                                progress_callback=lambda pct, msg: dispatch_ui(
                                    lambda pct=pct, msg=msg: update_comic_gauge(pct, msg)
                                ),
                            )
                            def _cm_done() -> None:
                                update_comic_gauge(100, f"Saved: {out_p.name}")
                                comic_result_lbl.set_text(f"[✓] Saved to: {out_p}")
                                comic_result_lbl.style("color: var(--green); font-size: 12px; font-weight: 600;")
                            dispatch_ui(_cm_done)
                        except Exception as exc:
                            def _cm_err(e_str=str(exc)) -> None:
                                update_comic_gauge(0, "Error")
                                comic_result_lbl.set_text(f"[-] {e_str}")
                                comic_result_lbl.style("color: var(--red); font-size: 12px;")
                                show_system_modal("Scraper Failed", e_str, is_fault=True)
                            dispatch_ui(_cm_err)

                    threading.Thread(target=_cm_worker, daemon=True).start()

                ui.button("Start Download", on_click=_run_comic_scraper).classes("btn-tactical-primary w-full")

        # ====================================================================
        # TAB 04 // FOLDER TO PDF / CBZ PACKAGER
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec04:
            sector_containers["04"] = sec04
            sec04.set_visibility(False)

            with ui.column().classes("mc-panel p-5 gap-3 w-full"):
                with ui.row().classes("w-full items-center justify-between gap-2"):
                    ui.label("FOLDER TO PDF / CBZ").classes("display-title text-2xl")
                    pack_count_badge = ui.label("No folder selected").classes("mc-badge-muted")

                def _on_pack_folder_selected(p: Path) -> None:
                    pack_folder_input.set_value(str(p))
                    imgs = get_sorted_images_in_folder(p)
                    pack_count_badge.set_text(f"{len(imgs)} image(s) found")
                    pack_count_badge.classes(remove="mc-badge-muted", add="mc-badge-green" if imgs else "mc-badge-amber")

                with ui.row().classes("w-full items-center gap-2"):
                    pack_folder_input = ui.input(
                        "Image Folder",
                        placeholder="Select a folder containing images...",
                    ).classes("mc-input flex-grow").props("outlined dense")
                    ui.button(
                        "Browse Folder",
                        on_click=lambda: open_disk_browser(
                            mode="folder",
                            title="Select Image Folder",
                            on_select=_on_pack_folder_selected,
                        ),
                    ).classes("btn-tactical-secondary")

                with ui.row().classes("w-full gap-3 flex-wrap"):
                    pack_fmt_sel = ui.select(
                        options={"pdf": "PDF Document (.pdf)", "cbz": "Comic Archive (.cbz)"},
                        value="pdf",
                        label="Format",
                    ).classes("mc-input flex-1").props("outlined dense")
                    pack_order_sel = ui.select(
                        options={"ascending": "Ascending (1, 2, 10)", "random": "Random Shuffle"},
                        value="ascending",
                        label="Sort Order",
                    ).classes("mc-input flex-1").props("outlined dense")

                pack_recurse_sw = create_rocker_switch(
                    "Include Subfolders (Batch Mode)",
                    initial=False,
                    sub_label="Creates one PDF/CBZ per subfolder",
                )

                _, update_pack_gauge = create_fuel_gauge("Packager", "Ready")
                pack_result_lbl = ui.label("").style("font-size: 12px; color: var(--muted);")

                def _run_packager() -> None:
                    f_val = (pack_folder_input.value or "").strip()
                    if not f_val:
                        show_system_modal("Missing Folder", "Select an image folder first.", is_fault=True)
                        return
                    folder_p = Path(f_val).resolve()
                    if not folder_p.is_dir():
                        show_system_modal("Invalid Folder", f"Directory not found:\n{folder_p}", is_fault=True)
                        return
                    fmt = pack_fmt_sel.value or "pdf"
                    order_v = pack_order_sel.value or "ascending"
                    recurse_v = pack_recurse_sw["checked"]
                    out_base = get_tool_output_dir("packager")
                    out_base.mkdir(parents=True, exist_ok=True)

                    def _pk_worker() -> None:
                        try:
                            if recurse_v:
                                results = batch_pack_folders(
                                    folder_p,
                                    output_dir=out_base,
                                    fmt=fmt,
                                    recurse=True,
                                    order=order_v,
                                    progress_callback=lambda pct, msg: dispatch_ui(
                                        lambda pct=pct, msg=msg: update_pack_gauge(pct, msg)
                                    ),
                                )
                                summary = f"[✓] Created {len(results)} archive(s) in {out_base}"
                            else:
                                dest_file = out_base / f"{safe_filename(folder_p.name)}.{fmt}"
                                if fmt == "cbz":
                                    ok, cnt = images_to_cbz(
                                        folder_p,
                                        dest_file,
                                        order=order_v,
                                        progress_callback=lambda pct, msg: dispatch_ui(
                                            lambda pct=pct, msg=msg: update_pack_gauge(pct, msg)
                                        ),
                                    )
                                else:
                                    ok, cnt = images_to_pdf(
                                        folder_p,
                                        dest_file,
                                        order=order_v,
                                        progress_callback=lambda pct, msg: dispatch_ui(
                                            lambda pct=pct, msg=msg: update_pack_gauge(pct, msg)
                                        ),
                                    )
                                if not ok:
                                    raise RuntimeError("No images found in selected folder.")
                                summary = f"[✓] Saved {cnt} pages -> {dest_file}"

                            def _pk_done() -> None:
                                update_pack_gauge(100, "Done")
                                pack_result_lbl.set_text(summary)
                                pack_result_lbl.style("color: var(--green); font-size: 12px; font-weight: 600;")

                            dispatch_ui(_pk_done)
                        except Exception as exc:
                            def _pk_err(e_str=str(exc)) -> None:
                                update_pack_gauge(0, "Error")
                                pack_result_lbl.set_text(f"[-] {e_str}")
                                pack_result_lbl.style("color: var(--red); font-size: 12px;")
                                show_system_modal("Packager Failed", e_str, is_fault=True)

                            dispatch_ui(_pk_err)

                    threading.Thread(target=_pk_worker, daemon=True).start()

                ui.button("Create Archive", on_click=_run_packager).classes("btn-tactical-primary w-full")

        # ====================================================================
        # TAB 05 // IMAGE OCR
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec05:
            sector_containers["05"] = sec05
            sec05.set_visibility(False)

            with ui.column().classes("mc-panel p-5 gap-3 w-full"):
                with ui.row().classes("w-full items-center justify-between flex-wrap"):
                    ui.label("IMAGE TO TEXT (OCR)").classes("display-title text-2xl")
                    tess_bin = find_tesseract_binary()
                    ui.label(
                        "Tesseract Ready" if tess_bin else "Tesseract Missing"
                    ).classes("mc-badge-green" if tess_bin else "mc-badge-red")

                with ui.row().classes("w-full items-center gap-2"):
                    ocr_target_input = ui.input(
                        "Image File or Folder",
                        placeholder="Select an image or folder of images...",
                    ).classes("mc-input flex-grow").props("outlined dense")
                    ui.button(
                        "File",
                        on_click=lambda: open_disk_browser(
                            mode="file",
                            title="Select Image for OCR",
                            allowed_exts=IMAGE_EXTENSIONS,
                            on_select=lambda p: ocr_target_input.set_value(str(p)),
                        ),
                    ).classes("btn-tactical-secondary")
                    ui.button(
                        "Folder",
                        on_click=lambda: open_disk_browser(
                            mode="folder",
                            title="Select Folder for Batch OCR",
                            on_select=lambda p: ocr_target_input.set_value(str(p)),
                        ),
                    ).classes("btn-tactical-secondary")

                with ui.row().classes("w-full gap-3 flex-wrap"):
                    ocr_lang_sel = ui.select(
                        options={
                            "eng": "English (eng)",
                            "jpn": "Japanese (jpn)",
                            "chi_sim": "Chinese Simplified (chi_sim)",
                            "deu": "German (deu)",
                            "fra": "French (fra)",
                            "spa": "Spanish (spa)",
                            "kor": "Korean (kor)",
                            "rus": "Russian (rus)",
                        },
                        value="eng",
                        label="Language",
                    ).classes("mc-input flex-1").props("outlined dense")

                    ocr_order_sel = ui.select(
                        options={"ascending": "Ascending", "random": "Random Shuffle"},
                        value="ascending",
                        label="Order",
                    ).classes("mc-input flex-1").props("outlined dense")

                ocr_combine_sw = create_rocker_switch(
                    "Combine into single .txt file",
                    initial=True,
                )

                _, update_ocr_gauge = create_fuel_gauge("OCR", "Ready")

                ocr_preview_area = ui.textarea(
                    label="Extracted Text",
                    placeholder="Extracted text will appear here...",
                ).classes("mc-input w-full").props("outlined rows=8 readonly")

                with ui.row().classes("w-full gap-2"):
                    def _run_ocr_job() -> None:
                        t_val = (ocr_target_input.value or "").strip()
                        if not t_val:
                            show_system_modal("Missing Image", "Select an image file or folder first.", is_fault=True)
                            return
                        if not is_tesseract_available():
                            show_system_modal("Tesseract Not Installed", get_tesseract_install_hint(), is_fault=True)
                            return

                        lang_v = ocr_lang_sel.value or "eng"
                        comb_v = ocr_combine_sw["checked"]
                        ord_v = ocr_order_sel.value or "ascending"

                        def _o_worker() -> None:
                            try:
                                ok, out_p, preview_txt = run_ocr(
                                    target=t_val,
                                    output_dir=get_tool_output_dir("ocr"),
                                    lang=lang_v,
                                    combine_output=comb_v,
                                    order=ord_v,
                                    progress_callback=lambda pct, msg: dispatch_ui(
                                        lambda pct=pct, msg=msg: update_ocr_gauge(pct, msg)
                                    ),
                                )
                                def _o_done() -> None:
                                    update_ocr_gauge(100, f"Saved: {out_p.name}")
                                    ocr_preview_area.set_value(preview_txt or "(No text detected)")
                                dispatch_ui(_o_done)
                            except Exception as exc:
                                def _o_err(e_str=str(exc)) -> None:
                                    update_ocr_gauge(0, "Error")
                                    show_system_modal("OCR Failed", e_str, is_fault=True)
                                dispatch_ui(_o_err)

                        threading.Thread(target=_o_worker, daemon=True).start()

                    ui.button("Extract Text", on_click=_run_ocr_job).classes("btn-tactical-primary flex-grow")
                    ui.button(
                        "Copy Text",
                        on_click=lambda: (
                            ui.run_javascript(f"navigator.clipboard.writeText({json.dumps(ocr_preview_area.value or '')});"),
                            show_system_modal("Copied", "Text copied to clipboard."),
                        ),
                    ).classes("btn-tactical-secondary")

        # ====================================================================
        # TAB 06 // FOLDERS & HISTORY
        # ====================================================================
        with ui.column().classes("w-full gap-4") as sec06:
            sector_containers["06"] = sec06
            sec06.set_visibility(False)

            with ui.row().classes("w-full gap-4 items-start flex-wrap"):
                # 6A: Output Folders
                with ui.column().classes("mc-panel p-5 gap-3 flex-1 min-w-[340px]"):
                    ui.label("OUTPUT FOLDERS").classes("display-title text-2xl")

                    dir_rows_box = ui.column().classes("w-full gap-2")

                    def _render_dir_matrix() -> None:
                        dir_rows_box.clear()
                        cfg_now = load_config()
                        tools_list = [
                            ("video", "Video Downloads"),
                            ("converter", "Converted Media"),
                            ("comic", "Comics & Galleries"),
                            ("packager", "PDF / CBZ Archives"),
                            ("ocr", "OCR Text"),
                        ]
                        with dir_rows_box:
                            for t_id, t_label in tools_list:
                                resolved_p = get_tool_output_dir(t_id, cfg_now)
                                with ui.row().classes("tactical-row selected w-full items-center justify-between p-2 gap-2 no-wrap"):
                                    with ui.column().classes("gap-0 min-w-0 flex-1"):
                                        ui.label(t_label).style("font-size: 11px; font-weight: 700; color: var(--green);")
                                        ui.label(str(resolved_p)).style("font-size: 11px; color: var(--ink); word-break: break-all;")
                                    with ui.row().classes("gap-1 no-wrap shrink-0"):
                                        ui.button(
                                            "Change",
                                            on_click=lambda _e, tool_key=t_id: open_disk_browser(
                                                mode="folder",
                                                title=f"Select {tool_key.capitalize()} Folder",
                                                initial_dir=get_tool_output_dir(tool_key),
                                                on_select=lambda new_p, tk=tool_key: (
                                                    set_tool_output_dir(tk, new_p),
                                                    _render_dir_matrix(),
                                                ),
                                            ),
                                        ).classes("btn-tactical-secondary py-1 px-2")
                                        ui.button(
                                            "Open",
                                            on_click=lambda _e, rp=resolved_p: system_open(rp),
                                        ).classes("btn-tactical-secondary py-1 px-2")

                    _render_dir_matrix()

                    with ui.row().classes("w-full gap-2 pt-2 flex-wrap"):
                        ui.button(
                            "Auto-Separate Folders",
                            on_click=lambda: (
                                auto_separate_all_tool_dirs(),
                                _render_dir_matrix(),
                                show_system_modal("Folders Updated", "Created separate subfolders (Converted, Comics, Packaged, OCR)."),
                            ),
                        ).classes("btn-tactical-primary flex-1")
                        ui.button(
                            "Reset Defaults",
                            on_click=lambda: (
                                reset_all_tool_dirs_to_defaults(),
                                _render_dir_matrix(),
                                show_system_modal("Reset Complete", "All output folders reset to default Downloads."),
                            ),
                        ).classes("btn-tactical-secondary")

                # 6B: Recent Downloads
                with ui.column().classes("mc-panel p-5 gap-3 flex-1 min-w-[340px]"):
                    with ui.row().classes("w-full items-center justify-between"):
                        ui.label("RECENT DOWNLOADS").classes("display-title text-2xl")
                        ui.button("Refresh", on_click=lambda: _refresh_history_panel()).classes("btn-tactical-secondary py-1 px-2")

                    history_box = ui.column().classes("w-full gap-2 max-h-[380px] overflow-y-auto pr-1")

                    def _refresh_history_panel() -> None:
                        history_box.clear()
                        hist_path = get_config_dir() / "history.json"
                        records: list[dict[str, Any]] = []
                        if hist_path.is_file():
                            try:
                                records = json.loads(hist_path.read_text(encoding="utf-8"))
                            except Exception:
                                records = []
                        with history_box:
                            if not records:
                                ui.label("No downloads yet.").style("font-size: 11px; color: var(--muted);")
                                return
                            for rec in reversed(records[-25:]):
                                out_str = rec.get("output") or ""
                                eng = rec.get("engine") or "unknown"
                                plat = rec.get("platform") or "video"
                                with ui.column().classes("tactical-row selected w-full p-2 gap-1"):
                                    with ui.row().classes("w-full items-center justify-between"):
                                        ui.label(f"{plat} ({eng})").style(
                                            "font-size: 11px; font-weight: 700; color: var(--green);"
                                        )
                                        if out_str and Path(out_str).exists():
                                            ui.button(
                                                "Play",
                                                on_click=lambda _e, p=out_str: system_open(Path(p)),
                                            ).classes("btn-tactical-secondary py-0 px-2")
                                    ui.label(rec.get("url", "")).style(
                                        "font-size: 10px; color: var(--muted); word-break: break-all;"
                                    )
                                    if out_str:
                                        ui.label(out_str).style("font-size: 11px; color: var(--ink); word-break: break-all;")

                    _refresh_history_panel()


def launch_mission_control(
    native: bool = False,
    port: int = 8080,
    host: str = "127.0.0.1",
    open_browser: bool = True,
    reload: bool = False,
) -> int:
    """
    Launch the Mission Control NiceGUI dashboard in either Web (`--web`) or Desktop (`--gui`) mode.
    Returns process exit code (0 on clean shutdown, 1 on missing optional dependency).
    """
    if not is_nicegui_available():
        print("\n[-] NiceGUI is not installed in the current Python environment.")
        print("    Install it with: pip install nicegui")
        print("    Or with desktop window support: pip install \"toolkit-cli[gui]\"\n")
        return 1

    from nicegui import ui

    use_native = bool(native)
    if use_native and not is_pywebview_available():
        print("[!] Notice: 'pywebview' is not installed; falling back to local browser window mode.")
        print("    (To enable standalone desktop windows, run: pip install pywebview)")
        use_native = False

    if is_termux():
        acquire_termux_wake_lock()
        use_native = False

    @ui.page("/")
    def _index_page() -> None:
        ui.page_title("TOOL-KIT // MISSION CONTROL CONSOLE")
        build_mission_control_dashboard()

    mode_label = "Desktop Native Window" if use_native else f"Browser Console (http://{host}:{port})"
    print(f"\n[+] Launching Tool-Kit Mission Control UI [{mode_label}]...")
    print("[+] Dialect : Mission Control Cyber Terminal (0-Radius / #39FF88 / #FFB627)")

    ui.run(
        host=host,
        port=port,
        title="TOOL-KIT // MISSION CONTROL",
        dark=True,
        native=use_native,
        show=open_browser if not use_native else True,
        reload=reload,
    )
    return 0
