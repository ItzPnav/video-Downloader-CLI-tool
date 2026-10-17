# <img src="https://cdn.simpleicons.org/ffmpeg/007808" width="28" height="28" align="center"/> **Tool-Kit CLI**

### *Resilient multi-agent media extractor & utility toolkit CLI for mobile and terminal environments*

<div align="center">
<img src="https://img.shields.io/badge/Command-tools%20%2F%20video-3DDC84?style=for-the-badge">
<img src="https://img.shields.io/badge/Platform-Termux%20%2F%20Linux%20%2F%20Windows%20%2F%20macOS-3DDC84?style=for-the-badge">
<img src="https://img.shields.io/badge/Python-3.x-3776AB?style=for-the-badge">
<img src="https://img.shields.io/badge/Architecture-Concurrent%20Multi--Agent-FF6F00?style=for-the-badge">
<img src="https://img.shields.io/badge/LangGraph-Orchestrator-000000?style=for-the-badge">
<img src="https://img.shields.io/badge/yt--dlp-Extractor%20Tier-FF0000?style=for-the-badge">
<img src="https://img.shields.io/badge/Scrapling-Adaptive%20Tier-4285F4?style=for-the-badge">
<img src="https://img.shields.io/badge/FFmpeg-Stream%20Muxer-007808?style=for-the-badge">
</div>

---

# <img src="https://cdn.simpleicons.org/readme/000000" width="22" height="22" align="center"/> **Overview**

**Tool-Kit CLI** (`tools`) is a concurrent multi-agent command-line suite and media extractor for Android (Termux), Linux, macOS, and Windows. It combines multi-tier online video downloading, high-speed format conversion, comic chapter scraping, folder archiving (PDF/CBZ), optical character recognition (OCR), and an interactive terminal disk browser into one lightweight utility.

Instead of slow sequential waterfalls, Tool-Kit CLI runs a simultaneous **Concurrent Multi-Agent Race** across four independent extraction tiers:

* **yt-dlp** — primary extraction engine for thousands of supported sites and adaptive formats
* **Scrapling** — adaptive parser and stealth browser extractor with auto-relocating selectors and anti-bot escalation
* **BeautifulSoup** — static HTML DOM and JSON-LD scanner
* **Selenium + Headless Chromium** — browser-level network sniffer that captures M3U8/MPD streams from JS-rendered pages
* **FFmpeg + Pillow** — high-performance media transcoding (Video to GIF, Audio extraction, Text to PDF, CBZ packaging)

> Built for terminal environments where multi-tier extraction speed, bot resilience, file navigation, and cross-platform terminal orchestration matter.

---

# <img src="https://cdn.simpleicons.org/diagramsdotnet/F08705" width="22" height="22" align="center"/> **Architecture**

```
User Input — tools "URL" [--quality 1080p] [--race-timeout 20] [--no-browser]
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

### <img src="https://cdn.simpleicons.org/ffmpeg/007808" width="18" height="18" align="center"/> Zero-Bloat Media Converter
Transcode media using native FFmpeg and Pillow pipelines: 2-pass high quality Video to GIF, 320 kbps MP3 soundtrack extraction, Audio-to-Audio transcoding (FLAC, WAV, AAC, OGG), Text document to PDF rendering, and lossless container switching.

### <img src="https://cdn.simpleicons.org/quicktime/000000" width="18" height="18" align="center"/> Video Concatenation & Clip Merger
Merge multiple video clips sequentially into a unified MP4 video using fast zero-CPU direct stream-copying, with intelligent transcoding fallback when video dimensions or codecs differ.

### <img src="https://cdn.simpleicons.org/gitbook/3884FF" width="18" height="18" align="center"/> Comic & Manga Chapter Scraper
Scrape web comics and image galleries from URLs, local HTML files, or directories with anti-bot headers, cookie injection (`--cookies`), and automatic bundling into multi-page PDF or Comic Book Zip (.cbz) archives.

### <img src="https://cdn.simpleicons.org/googlelens/4285F4" width="18" height="18" align="center"/> Optical Character Recognition (OCR)
Extract readable text from single images or entire folders using Tesseract OCR, with options for combined or per-image transcript files and multi-language support.

### <img src="https://cdn.simpleicons.org/gnometerminal/241F31" width="18" height="18" align="center"/> Hierarchical Submenus & Disk Browser
Interactive arrow-key dashboard organized into clean submenus (`Video Tools`, `Other Tools & Utilities`, `Settings & Preferences`) with a built-in visual disk file picker, per-tool output folder configuration, smooth braille spinners, and universal `Esc` / `q` / `0` back-out navigation.

### <img src="https://cdn.simpleicons.org/files/4285F4" width="18" height="18" align="center"/> Persistent Download History
Every successful download is logged to `config/history.json` with target URL, platform, winning engine, file path, quality, and multi-agent `race_duration_ms` — viewable anytime via `tools --history`.

### <img src="https://cdn.simpleicons.org/linux/000000" width="18" height="18" align="center"/> Cross-Platform & Mobile Native
Runs natively on Android Termux, standard Linux distributions, macOS, and Windows. Uses platform-native openers (`termux-open`, `xdg-open`, `open`, `os.startfile`) for instant post-download playback.

---

# <img src="https://cdn.simpleicons.org/layers/555555" width="22" height="22" align="center"/> **Tech Stack**

| Layer | Technology |
|-------|------------|
| CLI Launcher | Bash (`bin/tools`, `bin/video`) & Windows Batch (`bin/tools.bat`) |
| Entry Point | Python 3 (`src/main.py`) |
| Terminal Dashboard | Zero-dependency keyboard UI with interactive disk browser (`src/video_downloader/menu.py`) |
| Platform Router | Custom dataclass registry (`src/video_downloader/router.py`) |
| Race Coordinator | LangGraph (`src/video_downloader/race_controller.py`) |
| Terminal Spawner | Cross-platform spawner (`src/video_downloader/terminal_launcher.py`) |
| Adaptive Extractor | Scrapling (`src/video_downloader/scrapling_scanner.py`) |
| Primary Extractor | yt-dlp (`src/video_downloader/site_extractor.py`) |
| Static Fallback | BeautifulSoup 4 + Requests (`src/video_downloader/static_scanner.py`) |
| Browser Fallback | Selenium + Headless Chromium (`src/video_downloader/browser_scanner.py`) |
| Media Converter | FFmpeg + Pillow (`src/video_downloader/converter.py`) |
| Comic Scraper | BeautifulSoup 4 + Requests (`src/video_downloader/comic_scraper.py`) |
| Document Packager | Pillow (`src/video_downloader/packager.py`) |
| OCR Engine | Tesseract OCR (`src/video_downloader/ocr.py`) |
| Candidate Scoring | Custom scorer (`src/video_downloader/candidate.py`, `src/video_downloader/selector.py`) |
| Stream Merger | FFmpeg (`src/video_downloader/downloader.py`) |
| Config + History | JSON (`config/config.json`, `config/history.json`) |
| Progress Display | Flicker-free braille spinner & animated progress bar (`src/video_downloader/progress.py`) |

---

# <img src="https://cdn.simpleicons.org/gnometerminal/241F31" width="22" height="22" align="center"/> **Setup**

### Option A: Install via pip (Recommended)

```bash
pip install toolkit-cli
```

### Option B: Install from Source

1. **Clone the repository into your home directory:**

```bash
git clone https://github.com/ItzPnav/video-Downloader-CLI-tool.git ~/toolkit-cli
```

2. **Install Python dependencies:**

```bash
pip install -r ~/toolkit-cli/requirements.txt
```

Alternatively, install in editable mode:

```bash
pip install -e ~/toolkit-cli
```

3. **Install Scrapling browser binaries for stealth fetcher:**

```bash
scrapling install
```

4. **Install system binaries (Termux):**

```bash
pkg update && pkg install ffmpeg python chromium tesseract
```

5. **Install system binaries (Debian / Ubuntu):**

```bash
sudo apt update && sudo apt install ffmpeg python3 chromium-driver tesseract-ocr
```

6. **Make the launchers executable:**

```bash
chmod +x ~/toolkit-cli/bin/tools
chmod +x ~/toolkit-cli/bin/video
chmod +x ~/toolkit-cli/bin/video-update
```

7. **Add the launcher to your PATH (Termux):**

```bash
echo 'export PATH="$HOME/toolkit-cli/bin:$PATH"' >> ~/.bashrc && source ~/.bashrc
```

Alternatively, create a symlink so the command is available system-wide:

```bash
ln -s ~/toolkit-cli/bin/tools $PREFIX/bin/tools
ln -s ~/toolkit-cli/bin/video $PREFIX/bin/video
```

8. **Grant storage access (Termux only):**

```bash
termux-setup-storage
```

9. **Run it:**

```bash
tools
```

---

# <img src="https://cdn.simpleicons.org/shieldsdotio/00B4D8" width="22" height="22" align="center"/> **Production Tips**

* Always keep `yt-dlp` updated — run `pip install -U yt-dlp` regularly as websites frequently alter extraction signatures.
* Single-terminal background execution is enabled by default. Pass `--spawn-terminals` if you want independent OS terminal windows spawned per tier for debugging.
* Fast tiers (`yt-dlp`, static scanner, Scrapling) launch immediately at $T=0\text{s}$. The heavy headless browser tier is held in standby behind an adaptive grace timer (default: 2.5s, configurable via `"browser_grace_seconds"` or `--browser-grace`) to save CPU and RAM on quick downloads.
* Set `"use_browser": false` in `config/config.json` or pass `--no-browser` on low-memory devices where Chromium is unavailable.
* Run `scrapling install` once during initial setup so Scrapling's stealth browser dependencies are cached locally.
* Adjust `"race_timeout": 20` in `config/config.json` depending on network latency conditions.
* The default download directory is `/sdcard/Download` on Termux. Update `"download_directory"` in `config/config.json` for Linux/macOS/Windows desktop setups.

---

# <img src="https://cdn.simpleicons.org/roadmapdotsh/7C3AED" width="22" height="22" align="center"/> **Roadmap**

* [ ] Cookie injection support for authenticated streams
* [ ] Playlist batch download with concurrent item queues
* [ ] Subtitle and caption extraction with MP4 embedding
* [ ] Auto-detect and install missing system dependencies
* [ ] Cloud drive sync integration (Google Drive / Nextcloud)

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
* **Tesseract OCR not found:** Ensure `tesseract` (or `tesseract-ocr`) is installed and available in PATH.
* **Storage permission denied on Android:** Run `termux-setup-storage` and grant permission when prompted by Android.

---

# <img src="https://cdn.simpleicons.org/files/4285F4" width="22" height="22" align="center"/> **Folder Structure**

```
toolkit-cli/
|
+-- bin/
|   +-- tools                  # Primary shell launcher
|   +-- tools.bat              # Windows batch launcher
|   +-- video                  # Backward-compatibility launcher
|   +-- video.bat              # Windows batch launcher
|   +-- video-update           # Automated system updater script
|
+-- config/
|   +-- config.json            # Preferences, race timeout, and engine toggles
|   +-- history.json           # Persistent download history with race_duration_ms
|
+-- src/
|   +-- main.py                # Standalone CLI entry bridge
|   +-- video_downloader/      # Core Python package
|       +-- __init__.py        # Public package exports
|       +-- cli.py             # CLI entry point and argument parser
|       +-- race_controller.py # LangGraph concurrent multi-agent race coordinator
|       +-- terminal_launcher.py # OS-agnostic terminal and process spawner
|       +-- agent_worker.py    # Independent tier worker process executor
|       +-- scrapling_scanner.py # Scrapling adaptive fetcher and DOM scanner tier
|       +-- site_extractor.py  # yt-dlp extraction wrapper and format selector
|       +-- static_scanner.py  # HTML/JSON-LD/JS regex scanner (BeautifulSoup)
|       +-- browser_scanner.py # Selenium + Chromium network performance sniffer
|       +-- converter.py       # FFmpeg & Pillow media converter (GIF, Audio, Text->PDF)
|       +-- comic_scraper.py   # Comic and image gallery chapter downloader
|       +-- packager.py        # Image folder to PDF / CBZ packager
|       +-- ocr.py             # Tesseract OCR engine wrapper
|       +-- candidate.py       # Media candidate model and scoring logic
|       +-- selector.py        # Candidate ranking algorithm
|       +-- downloader.py      # FFmpeg stream copy and download executor
|       +-- progress.py        # Terminal spinner and progress bar renderer
|       +-- utils.py           # Config loader, filename sanitizer, history writer
|       +-- router.py          # Platform identifier and route registry
|       +-- routes/            # Domain-specific matchers (youtube, vimeo, etc.)
|       +-- extractors/        # Native extractor wrappers
|
+-- tests/                     # Unit and integration test suite
|   +-- test_comic_scraper.py
|   +-- test_conflict_resolver.py
|   +-- test_converter_extended.py
|   +-- test_integration.py
|   +-- test_menu.py
|   +-- test_ocr.py
|   +-- test_race_controller.py
|   +-- test_scrapling_scanner.py
|   +-- test_terminal_launcher.py
|
+-- pyproject.toml             # Modern PEP 621 Python package configuration
+-- LICENSE                    # MIT License
+-- requirements.txt           # Python dependencies
+-- README.md                  # Project documentation
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
* [Pillow](https://python-pillow.org/) — image processing, document conversion, and PDF/CBZ bundling
* [Tesseract OCR](https://github.com/tesseract-ocr/tesseract) — optical character recognition engine

---

# Made with passion by **ItzPnav**

> *High-performance multi-tier video and stream extractor CLI tool for mobile and terminal environments.*
