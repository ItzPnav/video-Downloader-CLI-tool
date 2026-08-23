# <img src="https://cdn.simpleicons.org/python/3776AB" width="28" height="28" align="center"/> **Video Extractor**

### *High-performance multi-tier CLI video and stream extractor for mobile and terminal environments*

<div align="center">
<img src="https://img.shields.io/badge/Language-Python_3.10+-3776AB?style=for-the-badge">
<img src="https://img.shields.io/badge/Environment-Termux_Linux-04DE71?style=for-the-badge">
<img src="https://img.shields.io/badge/Engine-yt--dlp-FF6C37?style=for-the-badge">
<img src="https://img.shields.io/badge/Automation-Selenium-43B02A?style=for-the-badge">
<img src="https://img.shields.io/badge/Processing-FFmpeg-007808?style=for-the-badge">
</div>

---

# <img src="https://cdn.simpleicons.org/gnubash/4EAA25" width="22" height="22" align="center"/> **Overview**

**Video Extractor** is a resilient command-line tool for Android (Termux) and Linux environments that inspects, extracts, and downloads online videos and adaptive streams from virtually any web URL.

It uses:

* **yt-dlp Engine** — Primary high-speed native format extraction and adaptive stream muxing
* **Static DOM Scanner** — BeautifulSoup4 and Requests for parsing HTML video tags, JSON-LD, and embedded scripts
* **Headless Browser Sniffer** — Selenium and Chromium performance log interception for JavaScript-rendered players
* **FFmpeg Pipeline** — Direct stream copying, muxing, and formatted media saving to local storage

> Designed specifically for command-line power users who need reliable video downloads across both supported streaming sites and arbitrary web pages with embedded players.

---

# <img src="https://cdn.simpleicons.org/diagramsdotnet/F08705" width="22" height="22" align="center"/> **Architecture**

```
                     [ User Input / CLI Invocation ]
                                    ↓
                     [ Router Platform Identification ]
                                    ↓
       ┌──────────────────────────────────────────────────────────┐
       │             3-TIER EXTRACTION CASCADE ENGINE             │
       │                                                          │
       │ 1. Native Site Extractor (yt-dlp)                        │
       │    └── Fast direct format extraction & resolution match   │
       │                                                          │
       │ 2. Static HTML / DOM Scanner (Requests + BeautifulSoup)  │
       │    └── Inspects <video>, <iframe>, JSON-LD & JS patterns │
       │                                                          │
       │ 3. Headless Browser Sniffer (Selenium + Chromium)        │
       │    └── Intercepts network logs for M3U8, MPD & JS media  │
       └──────────────────────────────────────────────────────────┘
                                    ↓
                     [ Selector Candidate Scoring ]
                                    ↓
                  [ FFmpeg Stream Copy & Muxing Engine ]
                                    ↓
                     [ Output Saved to /sdcard/Download ]
```

---

# <img src="https://cdn.simpleicons.org/element/00D1B2" width="22" height="22" align="center"/> **Features**

### <img src="https://cdn.simpleicons.org/youtube/FF0000" width="18" height="18" align="center"/> Multi-Tiered Extraction Cascade
Automatically attempts direct site extraction via yt-dlp, falling back to static HTML DOM scanning, and finally headless browser network interception if JavaScript rendering is required.

### <img src="https://cdn.simpleicons.org/speedtest/00C4B3" width="18" height="18" align="center"/> Intelligent Media Scoring Engine
Evaluates media candidates by resolution, height, width, bitrate, frame rate, MIME type, and protocol priority (M3U8 HLS, MPD DASH, direct MP4/WebM).

### <img src="https://cdn.simpleicons.org/selenium/43B02A" width="18" height="18" align="center"/> Headless Browser Sniffer
Launches headless Chromium via Selenium to capture dynamic media network traffic, bypass anti-scraping layers, and locate hidden video stream manifests.

### <img src="https://cdn.simpleicons.org/android/34A853" width="18" height="18" align="center"/> Termux & Storage Utilities
Includes integrated history tracking (`--history`), video storage cleanup (`--clean`), direct Android player launching (`termux-open`), and automated updater shell scripts (`--update`).

---

# <img src="https://cdn.simpleicons.org/stackblitz/1389FD" width="22" height="22" align="center"/> **Tech Stack**

| Layer | Technology |
|-------|------------|
| Core Language | Python 3.10+ |
| Shell CLI | Bash / Termux |
| Primary Extractor | yt-dlp |
| HTML Parser | BeautifulSoup4 & Requests |
| Network Automation | Selenium WebDriver |
| Headless Browser | Chromium / Chromedriver |
| Media Transcoding | FFmpeg |
| Storage & Configuration | JSON (`config.json`, `history.json`) |

---

# <img src="https://cdn.simpleicons.org/terminal/4D4D4D" width="22" height="22" align="center"/> **Setup**

### **Termux Key Concepts**
Before installing, note the distinction between these key elements in Termux:
* **Project Directory**: The root folder containing the codebase (`$HOME/video-Downloader-CLI-tool`).
* **Executable Launcher**: The shell script at `bin/video` that executes the application.
* **PATH**: The environment variable (`$PATH`) listing directories where the shell searches for executable commands.
* **Termux System Bin (`$PREFIX/bin`)**: Termux's default system binary directory (`/data/data/com.termux/files/usr/bin`), which is included in `$PATH` by default.

> **Note:** Cloning the repository does **not** automatically make `video` available globally in your shell. You must explicitly configure your PATH or create a symlink as shown in Step 5.

---

### **Installation & Setup Steps**

1. **Install Prerequisites:**

Ensure Android + Termux are installed, then update packages and install required tools:

```bash
pkg update && pkg install git python ffmpeg x11-repo chromium -y
```

2. **Clone and Enter the Repository:**

```bash
git clone https://github.com/ItzPnav/video-Downloader-CLI-tool.git
cd video-Downloader-CLI-tool
```

3. **Install Python Dependencies:**

```bash
pip install -r requirements.txt
```

4. **Make CLI Launchers Executable:**

```bash
chmod +x bin/video bin/video-update
```

5. **Make `video` Available System-Wide:**

Choose **Option A (Preferred)** or **Option B**:

* **Option A: Add `bin` to PATH (Preferred)**
  Adds the project's `bin` directory (`$HOME/video-Downloader-CLI-tool/bin`) to your shell environment. This does not copy or move any scripts into system folders, making it ideal if you may move or pull updates to the repository directory later.

  ```bash
  echo 'export PATH="$HOME/video-Downloader-CLI-tool/bin:$PATH"' >> ~/.bashrc
  source ~/.bashrc
  ```

* **Option B: Symlink to `$PREFIX/bin` (Alternative)**
  Creates a symbolic link inside Termux's standard system binary folder (`$PREFIX/bin`), which is already included in PATH. Convenient when the project repository remains in a fixed location (`$HOME/video-Downloader-CLI-tool`).

  ```bash
  ln -s "$HOME/video-Downloader-CLI-tool/bin/video" "$PREFIX/bin/video"
  ```

Verify system-wide availability:

```bash
video --help
```

6. **Grant Storage Permission:**

```bash
termux-setup-storage
```

---

### **Usage & First-Run Examples**

1. **Display Help and CLI Options:**

```bash
video --help
```

2. **Basic Video Download:**

```bash
video "https://www.youtube.com/watch?v=example"
```

3. **Specify Video Quality:**

```bash
video --quality 1080p "https://www.youtube.com/watch?v=example"
```

> The downloader requests the specified resolution (e.g., `1080p`) when available, falling back to the nearest suitable format based on the project's quality-selection logic.

4. **Useful Management Commands:**

* Check version and download history:
  ```bash
  video --version
  ```
* Open an interactive picker to play downloaded videos:
  ```bash
  video --open
  ```
* Scan and interactively clean up downloaded video files to free storage space:
  ```bash
  video --clean
  ```

---

# <img src="https://cdn.simpleicons.org/shield/FFD700" width="22" height="22" align="center"/> **Production Tips**

* Keep `yt-dlp` updated regularly using `./bin/video-update` or `pip install --upgrade yt-dlp` to maintain site compatibility.
* Adjust `browser_wait_seconds` in `config/config.json` when downloading from heavy single-page applications or slow connections.
* Pass the `--no-browser` flag for faster extraction on plain HTML sites or simple media links.
* Use `--quality 1080p` to explicitly specify maximum resolution targets.

---

# <img src="https://cdn.simpleicons.org/roadmapdotsh/000000" width="22" height="22" align="center"/> **Roadmap**

* [ ] Batch URL downloading from input files
* [ ] Audio-only extraction mode (MP3/AAC convert flags)
* [ ] Multi-threaded segment download acceleration for fragmented streams

---

# <img src="https://cdn.simpleicons.org/1password/0094F5" width="22" height="22" align="center"/> **Security Notes**

* Always keep Python dependencies (`requests`, `yt-dlp`) updated to patch potential media parsing vulnerabilities.
* The browser scanner runs Chromium with security flags in headless mode (`--no-sandbox`, `--disable-gpu`).
* Downloaded files undergo string sanitization to prevent directory traversal or unsafe shell characters in file names.

---

# <img src="https://cdn.simpleicons.org/matrix/000000" width="22" height="22" align="center"/> **Troubleshooting**

* **`video: command not found`**
  Ensure Step 5 of Setup was executed. Add `$HOME/video-Downloader-CLI-tool/bin` to `~/.bashrc` and run `source ~/.bashrc`, or create the symlink via `ln -s "$HOME/video-Downloader-CLI-tool/bin/video" "$PREFIX/bin/video"`.

* **Python Dependency Errors**
  If module import errors occur, re-run `pip install -r requirements.txt`. Ensure `python` and `pip` are updated in Termux.

* **Missing FFmpeg Error**
  If stream copy or muxing fails due to a missing FFmpeg binary, install FFmpeg via Termux:
  ```bash
  pkg install ffmpeg -y
  ```

* **Missing yt-dlp Error**
  If native site extraction fails, update or reinstall yt-dlp:
  ```bash
  pip install --upgrade yt-dlp
  ```

* **Chromium / Selenium Problems**
  If the headless browser sniffer fails, verify Chromium is installed (`pkg install x11-repo && pkg install chromium -y`). If browser scanning is not required for your target URL, pass `--no-browser` to bypass Selenium initialization.

---

# <img src="https://cdn.simpleicons.org/filepath/2A2A2A" width="22" height="22" align="center"/> **Folder Structure**

```
video-Downloader-CLI-tool/
│
├── bin/
│   ├── video                  # Executable CLI launcher script
│   └── video-update           # Automated system & dependency updater
│
├── config/
│   ├── config.json            # Extractor settings & user preferences
│   └── history.json           # Log of previous downloads
│
├── src/
│   ├── extractors/            # Specialized engine wrappers (youtube, generic)
│   ├── routes/                # URL pattern matchers and domain handlers
│   ├── browser_scanner.py     # Selenium network sniffer engine
│   ├── candidate.py           # Candidate model and scoring logic
│   ├── downloader.py          # FFmpeg stream downloader
│   ├── main.py                # Main CLI entry point and flag dispatcher
│   ├── progress.py            # Terminal spinner and progress bar renderer
│   ├── router.py              # Platform router registry
│   ├── selector.py            # Resolution and candidate ranking algorithm
│   ├── site_extractor.py      # Native yt-dlp integration wrapper
│   ├── static_scanner.py      # HTML/DOM BeautifulSoup scanner
│   └── utils.py               # Shared utility functions and logging
│
├── .gitignore                 # Git ignored files configuration
├── README.md                  # Project documentation
├── requirements.txt           # Python dependency requirements
└── VERSION                    # Extractor version indicator
```

---

# <img src="https://cdn.simpleicons.org/git/F05032" width="22" height="22" align="center"/> **Contributing**

PRs and issues are welcome. Feel free to fork the repository, add new site routing rules, or submit performance improvements.

---

# <img src="https://cdn.simpleicons.org/opensourceinitiative/3DA639" width="22" height="22" align="center"/> **License**

MIT License — use freely.

---

# <img src="https://cdn.simpleicons.org/github/181717" width="22" height="22" align="center"/> **Credits**

* [yt-dlp](https://github.com/yt-dlp/yt-dlp) — Primary media extraction engine
* [FFmpeg](https://ffmpeg.org/) — Stream processing and video muxing
* [BeautifulSoup4](https://www.crummy.com/software/BeautifulSoup/) — HTML DOM parsing library
* [Selenium](https://www.selenium.dev/) — Headless browser network sniffer

---

# Made with passion by **ItzPnav**

> *High-performance multi-tier video and stream extractor CLI tool for mobile and terminal environments.*
