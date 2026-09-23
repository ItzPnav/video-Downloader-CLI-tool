# FEATURES.md — Video Extractor

This document details the complete feature set of Video Extractor v0.2.0.

---

## 1. Concurrent 4-Tier Multi-Agent Racing

Rather than waiting through a slow sequential waterfall where each engine only executes after the prior one fails, Video Extractor spawns all active extractor engines simultaneously.
- **Simultaneous dispatch:** yt-dlp, static HTML scanner, headless browser sniffer, and Scrapling scanner launch in parallel.
- **First-to-finish wins:** The earliest agent to yield a valid media candidate with a confidence score above the threshold is crowned the winner.
- **Immediate cancellation:** All losing tier agents are immediately terminated, freeing system CPU, RAM, and network bandwidth.

---

## 2. Scrapling Adaptive Extraction Tier

Integrated as a native peer agent (`src/scrapling_scanner.py`):
- **Fast HTTP Fetcher:** Uses `Fetcher.get(url)` for ultra-lightweight, rapid HTTP retrieval.
- **Stealth Browser Escalation:** Automatically detects anti-bot walls (Cloudflare, 401, 403, 429, 503) and transparently escalates to `StealthyFetcher.fetch(url, headless=True)`.
- **Adaptive DOM Parser:** Queries elements using Scrapling's CSS engine with automated selector relocation if site markup mutates over time.
- **Multi-pass extraction:** Scans `<video>`, `<source>`, `<iframe>`, custom attributes (`data-src`, `data-video`, etc.), JSON-LD schemas, and JS string regexes.
- **Markdown Text Fallback:** Employs `page.markdown()` to capture media links from unstructured content when DOM elements yield no candidates.

---

## 3. OS-Agnostic Multi-Window Terminal Spawner

A cross-platform process launcher (`src/terminal_launcher.py`) that adapts to the host operating system:
- **Windows:** Launches separate console windows or tabs using Windows Terminal (`wt.exe`) when available, falling back to `cmd.exe /c start`.
- **macOS:** Spawns new Terminal.app tabs via `osascript`.
- **Linux Desktop:** Automatically discovers and uses installed GUI terminal emulators (`gnome-terminal`, `konsole`, `xfce4-terminal`, `xterm`).
- **Termux (Android):** Connects to `tmux` / `screen` sessions if active, or executes as managed concurrent background subprocesses.
- **Headless & Server Fallback:** When no graphical display is present or `--no-terminals` is passed, seamlessly falls back to concurrent subprocesses with labeled terminal output.

---

## 4. LangGraph Graph-Based Orchestration

Extraction workflow modeled as a compiled `StateGraph` in LangGraph:
- **Topology:** A start node branching to parallel tier nodes, each feeding into a centralized reducer node.
- **Reducer logic:** Ingests extraction candidates from parallel branches, verifies confidence scores, and determines the winning engine and duration.
- **Clean state transitions:** Maintains typed state throughout the lifecycle including URLs, quality parameters, active PIDs, and killed PIDs.

---

## 5. Reliable Process-Tree Termination by PID

Process cancellation terminates the entire OS process hierarchy:
- When an agent wins, the controller retrieves each losing agent's PID (from launcher handles and worker PID files).
- Uses `psutil` to traverse and kill all descendant processes (e.g. child Chromium browsers, node instances, or subshells).
- Includes OS-native fallbacks (`taskkill /F /T /PID` on Windows, `killpg` on Unix/Linux).

---

## 6. Configurable Race Timeout & Confidence Threshold

- `--race-timeout <seconds>`: Configurable per-invocation flag and config key (`"race_timeout": 20`) preventing hung processes from blocking execution indefinitely.
- `--confidence <score>`: Threshold controlling the minimum candidate score needed to trigger an immediate win (default: `50`).

---

## 7. Granular Engine Exclusion Toggles

Users can selectively disable any agent tier via CLI flags or `config/config.json`:
- `--no-ytdlp`: Excludes native yt-dlp extractor from the race.
- `--no-static`: Excludes BeautifulSoup static HTML scanner.
- `--no-browser`: Excludes headless Chromium Selenium sniffer.
- `--no-scrapling`: Excludes Scrapling adaptive scanner.
- `--no-terminals`: Disables GUI terminal windows and runs all agents as piped subprocesses.

---

## 8. Extended Download History with Race Duration

Every successful extraction records comprehensive analytics in `config/history.json`:
- Target URL
- Platform identification (YouTube, Vimeo, Dailymotion, TNAFlix, Generic)
- Winning extraction engine (`ytdlp`, `static`, `browser`, `scrapling`)
- Output video file path
- Requested quality
- `race_duration_ms`: Duration of the multi-agent race in milliseconds.

---

## 9. Stream Transcoder & Direct Video Muxing

Powered by FFmpeg (`src/downloader.py`):
- Handles both direct video files (.mp4, .webm, .mkv) and adaptive playlists (.m3u8 HLS, .mpd DASH).
- Uses `-c copy` stream copying to mux video and audio without re-encoding, preserving full original bitrate and quality.

---

## 10. Terminal Management Utilities

- `video --clean`: Scans download directory, calculates storage used by video files, and offers interactive deletion.
- `video --open`: Interactive terminal picker listing downloaded videos with timestamps and file sizes for instant playback.
- `video --history`: Displays formatted download history with winning engines and race timings.
