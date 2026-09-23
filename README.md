# <img src="https://cdn.simpleicons.org/ffmpeg/007808" width="28" height="28" align="center"/> **Video Extractor**

### *Resilient CLI tool that extracts and downloads video streams from any URL*

<div align="center">
<img src="https://img.shields.io/badge/Platform-Termux%20%2F%20Linux%20%2F%20Windows%20%2F%20macOS-3DDC84?style=for-the-badge">
<img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge">
<img src="https://img.shields.io/badge/Architecture-Concurrent%20Race-FF6F00?style=for-the-badge">
<img src="https://img.shields.io/badge/LangGraph-Orchestrator-000000?style=for-the-badge">
<img src="https://img.shields.io/badge/yt--dlp-Extractor%20Tier-FF0000?style=for-the-badge">
<img src="https://img.shields.io/badge/Scrapling-Adaptive%20Tier-4285F4?style=for-the-badge">
<img src="https://img.shields.io/badge/FFmpeg-Stream%20Muxer-007808?style=for-the-badge">
</div>

---

# <img src="https://cdn.simpleicons.org/readme/000000" width="22" height="22" align="center"/> **Overview**

**Video Extractor** is a concurrent multi-agent command-line media tool for Android (Termux), Linux, macOS, and Windows that inspects, extracts, and downloads online videos and adaptive streams from virtually any web URL.

Instead of a slow sequential waterfall, Video Extractor runs a simultaneous **Concurrent Multi-Agent Race** across four independent extraction tiers:

* **yt-dlp** — primary extraction engine for thousands of supported sites and adaptive formats
* **Scrapling** — adaptive parser and stealth browser extractor with auto-relocating selectors and anti-bot escalation
* **BeautifulSoup** — static HTML DOM and JSON-LD scanner
* **Selenium + Headless Chromium** — browser-level network sniffer that captures M3U8/MPD streams from JS-rendered pages
* **FFmpeg** — merges adaptive video and audio tracks into a clean MP4 output with zero re-encoding

> Built for terminal environments where multi-tier extraction speed, bot resilience, and cross-platform terminal orchestration matter.

---

# <img src="https://cdn.simpleicons.org/diagramsdotnet/F08705" width="22" height="22" align="center"/> **Architecture**

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

# <img src="https://cdn.simpleicons.org/sparkpost/FFA500" width="22" height="22" align="center"/> **Features**

### <img src="https://cdn.simpleicons.org/serverless/FD5750" width="18" height="18" align="center"/> Concurrent Multi-Agent Tier Racing
Spawns yt-dlp, static HTML scanning, headless Chromium sniffing, and Scrapling simultaneously. The earliest tier to find a valid candidate above the confidence score threshold wins, and all losing processes are killed immediately by PID.

### <img src="https://cdn.simpleicons.org/speedtest/0052CC" width="18" height="18" align="center"/> Scrapling Adaptive Extractor Tier
Leverages Scrapling for high-speed plain HTTP fetching (`Fetcher`) with seamless escalation to stealth browser browsing (`StealthyFetcher`) if challenged by anti-bot protections, featuring auto-relocating DOM selectors and markdown fallback.

### <img src="https://cdn.simpleicons.org/gnometerminal/241F31" width="18" height="18" align="center"/> OS-Agnostic Terminal Spawner
Spawns dedicated terminal windows or tabs per extraction tier across Windows (Windows Terminal `wt.exe` / `start`), macOS (`osascript`), desktop Linux (`gnome-terminal`, `konsole`, `xterm`), and Termux (`tmux` / background subprocesses).

### <img src="https://cdn.simpleicons.org/youtube/FF0000" width="18" height="18" align="center"/> Platform-Specific Routes
Dedicated route matchers for YouTube, Vimeo, Dailymotion, TNAFlix, and a Generic catch-all dispatch each URL to optimal extractor profiles without manual intervention.

### <img src="https://cdn.simpleicons.org/ffmpeg/007808" width="18" height="18" align="center"/> Adaptive Format Selection
Uses yt-dlp's `bv*+ba/b` format selector to pull the highest-fidelity video and audio tracks, then merges them into a single MP4 via FFmpeg stream copying without lossy re-encoding.

### <img src="https://cdn.simpleicons.org/qualcomm/3253DC" width="18" height="18" align="center"/> Quality Flag & Race Timeout
Pass `--quality 1080p` to enforce target resolution filters, and `--race-timeout 20` to guarantee hung network tiers terminate cleanly without blocking the CLI.

### <img src="https://cdn.simpleicons.org/files/4285F4" width="18" height="18" align="center"/> Persistent Download History
Every successful download is logged to `config/history.json` with target URL, platform, winning engine, file path, quality, and multi-agent `race_duration_ms` — viewable anytime via `video --history`.

### <img src="https://cdn.simpleicons.org/linux/000000" width="18" height="18" align="center"/> Cross-Platform & Mobile Native
Runs natively on Android Termux, standard Linux distributions, macOS, and Windows. Uses platform-native openers (`termux-open`, `xdg-open`, `open`, `os.startfile`) for instant post-download playback.

### <img src="https://cdn.simpleicons.org/amazons3/FF9900" width="18" height="18" align="center"/> Built-in Cleanup and Picker
`video --clean` scans the download directory, reports total video storage, and offers prompted cleanup. `video --open` launches an interactive numbered menu to pick and play any downloaded file.

---

# <img src="https://cdn.simpleicons.org/layers/555555" width="22" height="22" align="center"/> **Tech Stack**

| Layer | Technology |
|-------|------------|
| CLI Launcher | Bash (`bin/video`) |
| Entry Point | Python 3 (`src/main.py`) |
| Platform Router | Custom dataclass registry (`src/router.py`) |
| Race Coordinator | LangGraph (`src/race_controller.py`) |
| Terminal Spawner | Cross-platform spawner (`src/terminal_launcher.py`) |
| Adaptive Extractor | Scrapling (`src/scrapling_scanner.py`) |
| Primary Extractor | yt-dlp (`src/site_extractor.py`) |
| Static Fallback | BeautifulSoup 4 + Requests (`src/static_scanner.py`) |
| Browser Fallback | Selenium + Headless Chromium (`src/browser_scanner.py`) |
| Candidate Scoring | Custom scorer (`src/candidate.py`, `src/selector.py`) |
| Stream Merger | FFmpeg (`src/downloader.py`) |
| Config + History | JSON (`config/config.json`, `config/history.json`) |
| Progress Display | Custom terminal spinner (`src/progress.py`) |

---

# <img src="https://cdn.simpleicons.org/gnometerminal/241F31" width="22" height="22" align="center"/> **Setup**

1. **Clone the repository into your home directory:**

```bash
git clone https://github.com/ItzPnav/video-Downloader-CLI-tool.git ~/video-extractor
```

2. **Install Python dependencies:**

```bash
pip install -r ~/video-extractor/requirements.txt
```

3. **Install Scrapling browser binaries for stealth fetcher:**

```bash
scrapling install
```

4. **Install system binaries (Termux):**

```bash
pkg update && pkg install ffmpeg python chromium
```

5. **Install system binaries (Debian / Ubuntu):**

```bash
sudo apt update && sudo apt install ffmpeg python3 chromium-driver
```

6. **Make the launcher executable:**

```bash
chmod +x ~/video-extractor/bin/video
chmod +x ~/video-extractor/bin/video-update
```

7. **Add the launcher to your PATH (Termux):**

```bash
echo 'export PATH="$HOME/video-extractor/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

Alternatively, create a symlink so the command is available system-wide:

```bash
ln -s ~/video-extractor/bin/video $PREFIX/bin/video
```

8. **Grant storage access (Termux only):**

```bash
termux-setup-storage
```

9. **Run it:**

```bash
video "https://www.youtube.com/watch?v=dQw4w9WgXcQ"
```

---

# <img src="https://cdn.simpleicons.org/shieldsdotio/00B4D8" width="22" height="22" align="center"/> **Production Tips**

* Always keep `yt-dlp` updated — run `pip install -U yt-dlp` regularly as websites frequently alter extraction signatures.
* Set `"use_browser": false` in `config/config.json` or pass `--no-browser` on low-memory devices where Chromium is unavailable.
* Run `scrapling install` once during initial setup so Scrapling's stealth browser dependencies are cached locally.
* Use `--no-terminals` in headless SSH environments or script automation to suppress GUI terminal window creation.
* Adjust `"race_timeout": 20` in `config/config.json` depending on network latency conditions.
* The default download directory is `/sdcard/Download` on Termux. Update `"download_directory"` in `config/config.json` for Linux/macOS/Windows desktop setups.

---

# <img src="https://cdn.simpleicons.org/roadmapdotsh/7C3AED" width="22" height="22" align="center"/> **Roadmap**

* [ ] Cookie injection support for authenticated streams
* [ ] Playlist batch download with concurrent item queues
* [ ] Quality selection interactive terminal menu (TUI)
* [ ] Subtitle and caption extraction with MP4 embedding
* [ ] Auto-detect and install missing system dependencies
* [ ] Interactive config editor command (`video --config`)

---

# <img src="https://cdn.simpleicons.org/letsencrypt/003A70" width="22" height="22" align="center"/> **Security Notes**

* `config/history.json` stores download URLs in plaintext — keep permissions restricted on multi-user systems.
* Never commit personal cookies or API tokens to `config/config.json`.
* Browser scanner and stealth fetcher execute headless browsers with network logging enabled — only extract trusted URLs.
* URL validation enforces strict `http://` or `https://` protocol schemes.

---

# <img src="https://cdn.simpleicons.org/files/4285F4" width="22" height="22" align="center"/> **Troubleshooting**

* **Scrapling stealth fetcher missing browsers:** Run `scrapling install` in your terminal to download browser binaries.
* **Chromium version mismatch on Linux:** Ensure `chromium-driver` matches the installed `chromium` package version.
* **No GUI terminal spawning:** Pass `--no-terminals` or verify your desktop environment has `DISPLAY` or `WAYLAND_DISPLAY` set.
* **Storage permission denied on Android:** Run `termux-setup-storage` and grant permission when prompted by Android.

---

# <img src="https://cdn.simpleicons.org/files/4285F4" width="22" height="22" align="center"/> **Folder Structure**

```
video-extractor/
|
+-- bin/
|   +-- video                  # Shell launcher -- sets PYTHONPATH and exec python
|   +-- video-update           # Automated system updater script
|
+-- config/
|   +-- config.json            # Preferences, race timeout, and engine toggles
|   +-- history.json           # Persistent download history with race_duration_ms
|
+-- src/
|   +-- main.py                # CLI entry point, argument parser, race dispatcher
|   +-- race_controller.py     # LangGraph concurrent multi-agent race coordinator
|   +-- terminal_launcher.py   # OS-agnostic terminal and process spawner
|   +-- agent_worker.py        # Independent tier worker process executor
|   +-- scrapling_scanner.py   # Scrapling adaptive fetcher and DOM scanner tier
|   +-- site_extractor.py      # yt-dlp extraction wrapper and format selector
|   +-- static_scanner.py      # HTML/JSON-LD/JS regex scanner (BeautifulSoup)
|   +-- browser_scanner.py     # Selenium + Chromium network performance sniffer
|   +-- candidate.py           # Media candidate model and scoring logic
|   +-- selector.py            # Candidate ranking algorithm
|   +-- downloader.py          # FFmpeg stream copy and download executor
|   +-- progress.py            # Terminal spinner and progress bar renderer
|   +-- utils.py               # Config loader, filename sanitizer, history writer
|   +-- router.py              # Platform identifier and route registry
|   +-- routes/                # Domain-specific matchers (youtube, vimeo, etc.)
|
+-- tests/                     # Unit and integration test suite
|   +-- test_scrapling_scanner.py
|   +-- test_terminal_launcher.py
|   +-- test_race_controller.py
|   +-- test_integration.py
|
+-- requirements.txt           # Python dependencies
+-- README.md                  # Project documentation
+-- PROJECT.md                 # Architecture and project overview
+-- FEATURES.md                # Feature inventory and capabilities
+-- SPEC.md                    # Technical specification and schemas
+-- ARCHITECTURE.md            # Paradigm shift and LangGraph design
+-- IMPLEMENTATION.md          # Technical implementation guide
+-- GEMINI.md                  # Project memory and rules
```

---

# <img src="https://cdn.simpleicons.org/git/F05032" width="22" height="22" align="center"/> **Contributing**

PRs and issues are welcome. Fork freely and build on top of this.

---

# <img src="https://cdn.simpleicons.org/opensourceinitiative/3DA639" width="22" height="22" align="center"/> **License**

MIT License — use freely.

---

# <img src="https://cdn.simpleicons.org/githubsponsors/EA4AAA" width="22" height="22" align="center"/> **Credits**

* [yt-dlp](https://github.com/yt-dlp/yt-dlp) — primary video extraction engine powering the first extraction tier
* [Scrapling](https://github.com/D4Vinci/Scrapling) — adaptive parser and stealth crawler powering the fourth tier
* [FFmpeg](https://ffmpeg.org) — stream muxing and format merging for adaptive video and audio tracks
* [LangGraph](https://github.com/langchain-ai/langgraph) — orchestrator managing the concurrent multi-agent race and winner reduction
* [BeautifulSoup 4](https://www.crummy.com/software/BeautifulSoup/) — HTML DOM parsing for the static scanner tier
* [Selenium](https://selenium.dev) — browser automation driving the headless Chromium network sniffer
* [Requests](https://requests.readthedocs.io) — HTTP HEAD inspection and content-type probing in static scanning

---

# Made with passion by **ItzPnav**

> *High-performance multi-tier video and stream extractor CLI tool for mobile and terminal environments.*
