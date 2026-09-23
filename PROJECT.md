# PROJECT.md — Video Extractor

## 1. Project Vision & Identity

**Video Extractor** is a resilient, cross-platform command-line media extraction and download utility designed for Android (Termux), Linux, macOS, and Windows. It automatically inspects, extracts, scores, and downloads online videos and adaptive streams (M3U8 HLS, MPD DASH, MP4, WebM) from virtually any web URL.

Originally designed around a sequential fallback waterfall (yt-dlp → BeautifulSoup static scan → Selenium headless browser), Video Extractor v0.2.0 shifts to a **Concurrent Multi-Agent Tier Racing** architecture powered by **LangGraph** with an integrated **Scrapling** adaptive extractor.

---

## 2. Core Architecture Diagram

```
User Input — video "URL" [--quality 1080p] [--race-timeout 20] [--no-browser]
                    |
                    v
           [ Router / Platform Identifier ]
           Matches URL: YouTube | Vimeo | Dailymotion | TNAFlix | Generic
                    |
                    v
    +==============================================================+
    |       CONCURRENT MULTI-AGENT EXTRACTION RACE (LangGraph)     |
    +==============================================================+
         |               |                    |                |
         | (parallel)    | (parallel)         | (parallel)     | (parallel)
         v               v                    v                v
  +--------------+ +--------------+    +--------------+ +--------------+
  | Tier 1 Agent | | Tier 2 Agent |    | Tier 3 Agent | | Tier 4 Agent |
  |    yt-dlp    | | Static HTML  |    |   Browser    | |  Scrapling   |
  |  Extractor   | | Scanner (BS4)|    | Sniffer (Cr) | |   Adaptive   |
  +--------------+ +--------------+    +--------------+ +--------------+
         \               |                    |                /
          \              |                    |               /
           +-------------+--------------------+--------------+
                                 |
                                 v
                +----------------------------------+
                |    Winner Reducer Node           |
                |    First valid candidate wins!   |
                |    Kills losing tier PIDs        |
                +----------------------------------+
                                 |
                                 v
                     [ FFmpeg Downloader ]
            Stream-copies or muxes tracks -> output MP4
                                 |
                                 v
            /sdcard/Download/  (or configured directory)
```

---

## 3. Four Extraction Tiers

1. **yt-dlp Extractor Agent (`src/site_extractor.py`)**:
   - Queries `yt-dlp --dump-single-json` for site-specific formats.
   - Evaluates multi-track adaptive streams (`bv*+ba/b`) and resolution filters.

2. **Static HTML Scanner Agent (`src/static_scanner.py`)**:
   - Rapid HTTP fetch via `requests` session.
   - BeautifulSoup parsing of `<video>`, `<source>`, `<iframe>`, JSON-LD structures, and JS regex patterns.
   - Performs HTTP HEAD inspection to verify MIME types.

3. **Headless Browser Sniffer Agent (`src/browser_scanner.py`)**:
   - Spawns headless Chromium via Selenium.
   - Inspects Chrome performance logs (`Network.responseReceived`) to capture dynamic M3U8, MPD, and MP4 network streams on JS-rendered sites.

4. **Scrapling Adaptive Scanner Agent (`src/scrapling_scanner.py`)**:
   - Uses Scrapling (`https://github.com/D4Vinci/Scrapling`) as a high-performance peer tier.
   - Fast plain HTTP `Fetcher.get` with intelligent escalation to `StealthyFetcher.fetch(headless=True)` if anti-bot blocks (Cloudflare, 403/429) occur.
   - Uses Scrapling's adaptive parser for DOM extraction and auto-relocating CSS selectors, with regex and clean markdown fallback.

---

## 4. Key Subsystems

- **OS-Agnostic Terminal Spawner (`src/terminal_launcher.py`)**:
  Detects host OS (Windows Terminal `wt.exe`/`start`, macOS `osascript`, Linux desktop emulators `gnome-terminal`/`konsole`/`xterm`, Termux `tmux`/subprocess) and spawns an independent terminal window or process per tier.
- **Race Controller (`src/race_controller.py`)**:
  Coordinates tier agents using LangGraph. Tracks process IDs (PIDs) and terminates all losing process trees immediately upon first qualifying winner.
- **Downloader (`src/downloader.py`)**:
  Merges adaptive streams and direct video tracks into a unified MP4 file using FFmpeg stream copying without re-encoding.
- **History & Analytics (`config/history.json`)**:
  Maintains persistent download logs with target URL, platform, winning engine, output path, and race duration in milliseconds (`race_duration_ms`).
