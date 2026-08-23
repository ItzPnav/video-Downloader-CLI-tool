# GEMINI.md — Video Extractor
# Project memory for Antigravity AI Agent. Read this before touching ANY file.

---

## 1. PROJECT IDENTITY

- **Name:** Video Extractor
- **Type:** CLI Media Extractor Tool (Termux / Linux)
- **Author handle:** ItzPnav
- **Current version:** 0.2.0
- **Purpose:** Resilient command-line tool for Android (Termux) and Linux environments that inspects, extracts, and downloads online videos and adaptive streams from virtually any web URL.

---

## 2. FILE OWNERSHIP — WHO TOUCHES WHAT

```
bin/video                  ← Executable shell launcher script for CLI
bin/video-update           ← Automated system and dependency updater script
config/config.json         ← Application configuration and user preferences
config/history.json        ← Persistent download history log
src/main.py                ← CLI entry point, argument parser, and flow controller
src/router.py              ← Platform identification and router registry
src/routes/                ← Domain matchers (youtube, vimeo, dailymotion, tnaflix, generic)
src/site_extractor.py      ← Native yt-dlp extraction wrapper and format selector
src/static_scanner.py      ← HTML DOM, JSON-LD, and JS regex scanner using BeautifulSoup
src/browser_scanner.py     ← Selenium + Headless Chromium network performance sniffer
src/candidate.py           ← Media candidate model and scoring logic
src/selector.py            ← Candidate ranking algorithm
src/downloader.py          ← FFmpeg stream copying and download executor
src/progress.py            ← Terminal spinner and progress bar renderer
src/utils.py               ← Configuration loading, filename sanitization, history logger
README.md                  ← Always regenerate using README BUILDER rules in Section 7.
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
  "use_browser": true
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
    "output": "string | null"
  }
]
```

**Deduplication:** Download history logs are capped at the last 100 entries.

---

## 5. TERMUX & LINUX RUNTIME HARD RULES

1. **Executable Launchers** — All shell scripts in `bin/` must have executable permissions (`chmod +x bin/video bin/video-update`).
2. **Environment & PATH** — The CLI launcher `bin/video` relies on `$SRC` environment variable pointing to `src/` and Python 3.
3. **Storage Access** — Target output directory default is `/sdcard/Download`. In Termux, `termux-setup-storage` must be granted.
4. **Binary Dependencies** — Require `ffmpeg`, `python`, `yt-dlp`, and optional `chromium` / `chromedriver` in system PATH.
5. **System-Wide CLI Availability** — `bin/video` is NOT automatically system-wide after cloning. Users must explicitly add `$HOME/video-Downloader-CLI-tool/bin` to PATH or create a symlink to `$PREFIX/bin/video`.

---

## 6. EXTRACTION ENGINE CONTRACTS

### Native Site Extractor (`src/site_extractor.py`)
- **Detection/entry condition:** Supported domains or site supported by yt-dlp.
- **Key CLI tool:** `yt-dlp --dump-single-json`
- **Fallback:** Falls back to Static Scanner if yt-dlp extraction fails or returns no formats.

### Static HTML Scanner (`src/static_scanner.py`)
- **Detection/entry condition:** Generic URLs or site extractor fallback.
- **Key DOM/API:** BeautifulSoup parsing of `<video>`, `<iframe>`, `source`, `JSON-LD`, and JS string regex patterns.
- **Fallback:** Performs HTTP HEAD inspection scoring; falls back to Browser Scanner if no candidates found.

### Headless Browser Sniffer (`src/browser_scanner.py`)
- **Detection/entry condition:** Triggered when static scanning yields no media candidates or JS rendering is required.
- **Key API:** Selenium Chrome performance logs (`Network.responseReceived`).
- **Fallback:** Filters for M3U8, MPD, MP4 streams; aborts gracefully if Chromium or Chromedriver is missing.

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

- **Never claim `bin/video` is automatically system-wide** — user must explicitly export PATH or create symlink.
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
- **Dependencies:** Standard library + `requests`, `beautifulsoup4`, `yt-dlp`, `selenium`.

---

## 10. QUICK REFERENCE — CURRENT STATE SNAPSHOT

| Thing | Value |
|-------|-------|
| Version | 0.2.0 |
| Environment | Android (Termux) / Linux |
| Storage Backend | JSON (`config/config.json`, `config/history.json`) |
| Default Download Dir | `/sdcard/Download` |
| Primary Extractor | yt-dlp |
| Browser Automation | Selenium + Headless Chromium |
| Stream Transcoder | FFmpeg |
| Main Entry Point | `bin/video` -> `src/main.py` |

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
