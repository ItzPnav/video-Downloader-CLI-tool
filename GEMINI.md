# GEMINI.md — Tool-Kit CLI
# Project memory for Antigravity AI Agent. Read this before touching ANY file.

---

## 1. PROJECT IDENTITY

- **Name:** Tool-Kit CLI
- **Type:** CLI Media Extractor & Utility Toolkit (Termux / Linux / Windows / macOS)
- **Author handle:** ItzPnav
- **Current version:** 0.2.0
- **Purpose:** Resilient concurrent command-line media suite and utility toolkit for Android (Termux), Linux, and Windows that inspects, extracts, and downloads online streams, converts media formats, scrapes comics/mangas, archives image folders, and runs OCR text extraction.

---

## 2. FILE OWNERSHIP — WHO TOUCHES WHAT

```
bin/tools                                ← Primary executable shell launcher script for CLI
bin/tools.bat                            ← Primary Windows batch script launcher
bin/video                                ← Backward-compatibility shell launcher
bin/video.bat                            ← Backward-compatibility Windows batch launcher
bin/video-update                         ← Automated system and dependency updater script
pyproject.toml                           ← PEP 621 Python package configuration and build metadata
LICENSE                                  ← MIT License
config/config.json                       ← Application configuration and user preferences
config/history.json                      ← Persistent download history log
src/main.py                              ← Standalone CLI entry bridge
src/video_downloader/__init__.py         ← Public package exports
src/video_downloader/cli.py              ← CLI entry point, argument parser, and flow controller
src/video_downloader/terminal_launcher.py← OS-agnostic terminal and process spawner
src/video_downloader/race_controller.py  ← LangGraph concurrent multi-agent race coordinator
src/video_downloader/agent_worker.py     ← Independent worker process executor per tier
src/video_downloader/scrapling_scanner.py← Scrapling adaptive fetcher and DOM scanner tier
src/video_downloader/router.py           ← Platform identification and router registry
src/video_downloader/routes/             ← Domain matchers (youtube, vimeo, dailymotion, tnaflix, generic)
src/video_downloader/extractors/         ← Native extractor wrappers
src/video_downloader/site_extractor.py   ← Native yt-dlp extraction wrapper and format selector
src/video_downloader/static_scanner.py   ← HTML DOM, JSON-LD, and JS regex scanner using BeautifulSoup
src/video_downloader/browser_scanner.py  ← Selenium + Headless Chromium network performance sniffer
src/video_downloader/converter.py        ← FFmpeg & Pillow zero-bloat media converter
src/video_downloader/comic_scraper.py    ← Comic and image gallery chapter scraper
src/video_downloader/packager.py         ← Image folder to PDF / CBZ packager
src/video_downloader/ocr.py              ← Tesseract OCR image-to-text extraction engine
src/video_downloader/candidate.py        ← Media candidate model and scoring logic
src/video_downloader/selector.py         ← Candidate ranking algorithm
src/video_downloader/downloader.py       ← FFmpeg stream copying and download executor
src/video_downloader/conflict_resolver.py← File collision detection and diff comparison
src/video_downloader/menu.py             ← Hierarchical terminal menu with disk browser
src/video_downloader/progress.py         ← Flicker-free braille spinner and progress bar renderer
src/video_downloader/utils.py            ← Configuration loading, filename sanitization, history logger
README.md                                ← Always regenerate using README BUILDER rules in Section 7.
```

**Never create:** arbitrary root script files or temporary output directories outside `/sdcard/Download` or `config/` unless explicitly instructed.

---

## 4. DATA SCHEMA — NEVER RESHAPE THIS

Configuration lives in `config/config.json`:

```json
{
  "version": "0.2.0",
  "download_directory": "/sdcard/Download",
  "preferred_format": "bv*+ba/b",
  "merge_format": "mp4",
  "browser_wait_seconds": 8,
  "use_ytdlp": true,
  "use_static_scanner": true,
  "use_browser": true,
  "use_scrapling": true,
  "race_timeout": 20,
  "confidence_threshold": 50,
  "spawn_terminals": false,
  "browser_grace_seconds": 2.5,
  "auto_open": true
}
```

Download history lives in `config/history.json` as an array of download records:

```json
[
  {
    "url": "string",
    "platform": "string",
    "engine": "string",
    "quality": "string | null",
    "output": "string | null",
    "race_duration_ms": "number | null"
  }
]
```

**Deduplication:** Download history logs are capped at the last 100 entries.

---

## 5. TERMUX & LINUX RUNTIME HARD RULES

1. **Executable Launchers** — All shell scripts in `bin/` must have executable permissions (`chmod +x bin/tools bin/video bin/video-update`).
2. **Environment & PATH** — The CLI launchers `bin/tools` and `bin/video` rely on `$SRC` environment variable pointing to `src/` and Python 3.
3. **Storage Access** — Target output directory default is `/sdcard/Download`. In Termux, `termux-setup-storage` must be granted.
4. **Binary Dependencies** — Require `ffmpeg`, `python`, `yt-dlp`, `tesseract`, and optional `chromium` / `chromedriver` in system PATH.
5. **System-Wide CLI Availability** — `bin/tools` and `bin/video` are NOT automatically system-wide after cloning. Users must explicitly add `$HOME/toolkit-cli/bin` to PATH or create a symlink to `$PREFIX/bin/tools`.

---

## 6. DOMAIN LOGIC CONTRACTS

### Concurrent Race Controller (`src/video_downloader/race_controller.py`)
- **Model:** Parallel LangGraph StateGraph connecting 4 simultaneous extractor agents feeding into a 'first successful result wins' reducer node.
- **Winner Action:** Terminates all losing agent processes by PID immediately upon first winner above confidence threshold.
- **Timeout:** Defaults to 20s (`--race-timeout`).

### Scrapling Adaptive Scanner (`src/video_downloader/scrapling_scanner.py`)
- **Model:** Peer extraction agent alongside yt-dlp, static scanner, and browser sniffer.
- **Fetching:** Fast plain HTTP (`Fetcher.get`) by default; escalates to `StealthyFetcher.fetch(headless=True)` if blocked.
- **Parsing:** Adaptive selector DOM queries with auto-relocation, regex passes, and markdown clean-text fallback.

### Native Site Extractor (`src/video_downloader/site_extractor.py`)
- **Detection/entry condition:** Supported domains or site supported by yt-dlp.
- **Key CLI tool:** `yt-dlp --dump-single-json`
- **Output:** Native format selector (bv*+ba/b) and FFmpeg muxing.

### Media Converter (`src/video_downloader/converter.py`)
- **Pipelines:** Video to animated GIF (2-pass palettegen), Audio extraction (MP3 320k), Audio transcoder (WAV/FLAC/AAC/OGG), Text to PDF rendering, GIF to MP4, Remuxing, and Video Concatenation / Merge (`combine_videos` using fast zero-CPU concat demuxer with transcoding fallback).

### Comic & Gallery Scraper (`src/video_downloader/comic_scraper.py`)
- **Pipelines:** Multi-page chapter scraper with cookie support, anti-bot spoofing, and automatic bundling into PDF or CBZ.

### OCR Engine (`src/video_downloader/ocr.py`)
- **Pipelines:** Tesseract OCR image/folder text extraction with combined or separate transcript output.

### Per-Tool Output Directories (`src/video_downloader/utils.py`)
- **Isolation:** Each utility has its own dedicated output directory (`video` -> `download_directory`, `converter` -> `converter_output_directory`, `comic` -> `comic_output_directory`, `packager` -> `packager_output_directory`, `ocr` -> `ocr_output_directory`).
- **Dynamic Defaults:** Sub-tools default to separate subfolders under base downloads (`Converted`, `Comics`, `Packaged`, `OCR`) rather than sharing a single flat folder.
- **Auto-Separation:** `auto_separate_all_tool_dirs()` automatically configures and provisions all 5 dedicated directories.

---

## 7. README BUILDER RULES

Every time `README.md` is regenerated, follow these rules exactly — derived from the README's own current structure.

**Section order (fixed, no exceptions):**
Header → Overview → Architecture → Features → Tech Stack → Setup → Production Tips → Roadmap → Security Notes → Troubleshooting → Folder Structure → Contributing → License → Credits → Footer

**Formatting rules:**
1. Badges: `style=for-the-badge`. Wrap block in `<div align="center">`.
2. Architecture: ASCII diagram inside plain ` ``` ` code block.
3. Features: `### <img src="..." width="18" height="18" align="center"/> Title` heading style with 1–3 line descriptions.
4. Tech Stack: Markdown table with columns `Layer | Technology`.
5. Setup: Numbered steps with clear Termux concepts (Project Directory, Executable Launcher, PATH, `$PREFIX/bin`) and code blocks for commands.
6. Zero emojis anywhere in the document — SVG brand icons only (`https://cdn.simpleicons.org/...`).
7. Footer always ends with:
   ```
   # Made with passion by **ItzPnav**
   > *High-performance multi-tier video and stream extractor CLI tool for mobile and terminal environments.*
   ```

---

## 8. WHAT NOT TO DO — HARD GUARDRAILS

- **Never claim `bin/tools` or `bin/video` is automatically system-wide** — user must explicitly export PATH or create symlink.
- **Never hardcode static pixel paths or external media dependencies** — rely on `shutil.which` and environment configuration.
- **Never remove URL validation** — always enforce `http://` or `https://` protocol checks.
- **Never swallow subprocess or FFmpeg errors silently** — display clear terminal diagnostics.
- **Never mutate `config/history.json` schema** — preserve `url`, `platform`, `engine`, `quality`, and `output` keys.

---

## 9. CODING STYLE

- **Logging Prefixes:** Terminal output must use standardized status indicators:
  - `[+]` Info / Step notification
  - `[✓]` Success confirmation
  - `[!]` Warning / Fallback notice
  - `[-]` Error message
- **Python Conventions:** Clean modular imports, dataclasses for candidates and routes, explicit exception handling around network/subprocess calls.
- **Dependencies:** Standard library + `requests`, `beautifulsoup4`, `yt-dlp`, `selenium`, `scrapling`, `langgraph`, `psutil`, `pillow`.

---

## 10. QUICK REFERENCE — CURRENT STATE SNAPSHOT

| Thing | Value |
|-------|-------|
| Version | 0.2.0 |
| Environment | Android (Termux) / Linux / Windows / macOS |
| Primary Command | `tools` (Alias: `video`) |
| Architecture | Concurrent Multi-Agent Race (LangGraph) |
| Extraction Tiers | 4 (yt-dlp, Static HTML, Headless Chromium, Scrapling) |
| Utilities | Media Converter, Comic Scraper, Image to PDF/CBZ, OCR Engine |
| Storage Backend | JSON (`config/config.json`, `config/history.json`) |
| Default Download Dir | `/sdcard/Download` |
| Primary Engines | yt-dlp, Scrapling, BeautifulSoup, Selenium, FFmpeg, Pillow, Tesseract |
| Stream Transcoder | FFmpeg |
| Main Entry Point | `bin/tools` -> `src/main.py` |

---

## 12. CUSTOM SLASH COMMANDS

### /acp — Add, Commit, Push

When the user types `/acp`:

1. Stage everything: `git add .`
2. Write a commit message summarizing the actual staged changes — **max 6–7 words, imperative mood, no trailing period** (e.g. `fix popup crash on empty state`, `add streak counter to dashboard`).
3. Commit: `git commit -m "{generated message}"`
4. Push: run `git push`. If the current branch has no upstream, run `git push -u origin main` instead.
Rules:
- Never ask the user to approve or edit the commit message — write it and proceed.
- Never skip `git add .` even if only one file changed.
- If `git commit` reports nothing to commit, say so and stop — do not push.
- If the push is rejected (e.g. diverged branch), report the exact git error; do not force-push without being explicitly told to.
