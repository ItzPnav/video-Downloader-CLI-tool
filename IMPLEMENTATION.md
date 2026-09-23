# IMPLEMENTATION.md — Technical Implementation Guide

This guide describes the code implementation of Video Extractor v0.2.0, detailing module responsibilities, public interfaces, debug trace contracts, and testing strategies.

---

## 1. Module Breakdown

### 1.1 `src/terminal_launcher.py`
**Responsibility:** OS-agnostic terminal window and process spawning.
- **Key Functions:**
  - `detect_platform() -> str`: Returns `"windows"`, `"darwin"`, `"linux_desktop"`, `"termux"`, or `"headless"`.
  - `find_linux_terminal() -> Optional[str]`: Probes for `gnome-terminal`, `konsole`, `xfce4-terminal`, `xterm`.
  - `kill_process_by_pid(pid: int) -> bool`: Recursively kills process trees using `psutil` with OS native fallbacks (`taskkill /F /T` on Windows, `killpg` on Unix).
  - `spawn_tier(tier, command, title, pid_file, prefer_gui, cwd, env) -> LaunchedProcess`: Spawns GUI terminal or background subprocess.
- **Data Model:**
  - `LaunchedProcess`: Contains `tier`, `pid`, `mode`, `popen`, and `pid_file`. Exposes `get_actual_pid()` and `kill()`.

### 1.2 `src/scrapling_scanner.py`
**Responsibility:** Adaptive web media scanner powered by Scrapling.
- **Key Class:** `ScraplingScanner(url: str)`
  - `fetch_page()`: Attempts `Fetcher.get(url)`. If blocked (status in `{401, 403, 429, 503}` or anti-bot keywords like `"cloudflare"`), escalates to `StealthyFetcher.fetch(url, headless=True)`.
  - `scan_video_tags(page, base_url)`: Extracts `<video>` and `<source>` tags using Scrapling's CSS query engine.
  - `scan_iframes(page, base_url)`: Identifies embed player iframes.
  - `scan_attributes(page, base_url)`: Scans elements matching media attributes (`[data-src]`, `[data-video]`, `[data-stream]`, etc.).
  - `scan_json_ld(page, base_url)`: Recursive JSON parser for video schema objects.
  - `scan_javascript(html, base_url)`: Regex passes for quoted media stream URLs (`.m3u8`, `.mpd`, `.mp4`).
  - `scan_markdown_fallback(page, base_url)`: Uses `page.markdown()` to locate media links when DOM extraction finds nothing.
  - `inspect()`: Performs HTTP HEAD probing to verify MIME type and calculate final scores via `score_candidate()`.
  - `scan() -> list[Candidate]`: Returns sorted candidates by score descending.
  - `scan_html(html: str, base_url: str) -> list[Candidate]`: Offline in-memory parser for testing.

### 1.3 `src/agent_worker.py`
**Responsibility:** Independent worker process running a single extraction tier.
- **Workflow:**
  1. Captures `os.getpid()` and immediately writes it to `--pid-file`.
  2. Dispatches to `run_tier_agent(tier, url, quality)` (`ytdlp`, `static`, `browser`, `scrapling`).
  3. Formats the resulting candidate as a serialized JSON dictionary and writes to `--result-file`.

### 1.4 `src/race_controller.py`
**Responsibility:** LangGraph orchestration, tier racing, and kill-on-first-success management.
- **Key Class:** `ExtractionRaceController`
  - `build_langgraph()`: Compiles the LangGraph `StateGraph` topology.
  - `run_race() -> RaceResult`: Spawns all active tier agents simultaneously, polls for the first candidate above `confidence_threshold` (default: 50), announces the winner, and terminates all losing agent PIDs immediately.
- **Step-by-Step Debug Trace Contract:**
  - On agent launch:
    ```
    [+] Spawning agent [<tier>] (PID: <pid>)...
    ```
  - On race win:
    ```
    [✓] Agent [<tier>] won the race in <duration>ms! (Score: <score>)
    ```
  - On terminating losing agents:
    ```
    [+] Terminating losing agent [<tier>] (PID: <pid>)...
    [✓] Successfully killed PID: <pid>
    ```
  - On timeout:
    ```
    [!] Race timed out after <timeout>s with no winner.
    [+] Terminating all running agent processes due to timeout...
    [✓] Killed PID: <pid> (<tier>)
    ```

### 1.5 `src/downloader.py`
**Responsibility:** Unified media downloader and stream muxer.
- Supports both native `yt-dlp` format downloads and direct FFmpeg stream copying (`-c copy`) for M3U8, MPD, and MP4 candidates from Scrapling, Static Scanner, and Browser Scanner.

### 1.6 `src/main.py`
**Responsibility:** CLI entry point and argument parsing.
- Dispatches URL extraction to `ExtractionRaceController`.
- Writes winning engine, URL, platform, output, and `race_duration_ms` to `config/history.json`.

---

## 2. Testing Strategy & Test Suite

The test suite is located in `tests/` and structured as follows:

1. **`tests/test_scrapling_scanner.py`**:
   - Verifies Scrapling availability.
   - Tests DOM extraction passes across `<video>`, `<source>`, `<iframe>`, custom attributes, JSON-LD, and JS regex.
   - Tests blocked page detection (`is_blocked`).
   - Tests clean markdown text fallback extraction.

2. **`tests/test_terminal_launcher.py`**:
   - Tests platform detection across OS environments.
   - Tests subprocess process tree spawning and termination by PID.
   - Tests PID file reading from `LaunchedProcess`.

3. **`tests/test_race_controller.py`**:
   - Tests active tiers resolution from CLI flags and configuration.
   - Tests LangGraph StateGraph compilation.
   - Simulates concurrent multi-agent race with winner PID kill verification.
   - Tests race timeout handling and hung process cleanup.
   - Tests download history persistence with `race_duration_ms`.

4. **`tests/test_integration.py`**:
   - Tests safe filename sanitization.
   - Tests router platform identification.
   - Tests FFmpeg downloader invocation with mocked subprocess.
   - Tests yt-dlp downloader invocation with mocked extractor.

To run the full test suite:
```bash
python -m unittest discover -s tests
```
