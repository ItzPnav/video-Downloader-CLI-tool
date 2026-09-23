# SPEC.md — Video Extractor Specification

This document defines the formal technical specification for Video Extractor v0.2.0.

---

## 1. CLI Usage Specification

### Command Syntax

```bash
video [COMMAND | "URL"] [OPTIONS]
```

### Commands

| Command | Description |
|---------|-------------|
| `video` | Displays help and usage screen |
| `video "URL"` | Executes concurrent multi-agent race to extract and download media |
| `video --help`, `-h` | Displays detailed usage and option flags |
| `video --version`, `-v` | Outputs current application version |
| `video --history`, `-H` | Displays historical download log with race durations |
| `video --clean` | Interactively scans and prompts to delete downloaded video files |
| `video --open` | Interactive numbered video selector and launcher |
| `video --update` | Executes project dependency and source updater |

### Options & Flags

| Flag | Parameter | Default | Description |
|------|-----------|---------|-------------|
| `--quality` | `<resolution>` (e.g. `1080p`, `720p`) | Best available | Requests specific video height/format |
| `--race-timeout` | `<seconds>` (e.g. `20`) | `20.0` | Maximum time to wait for a tier race winner |
| `--confidence` | `<score>` (integer) | `50` | Minimum score threshold for a candidate to win |
| `--no-open` | None | `False` | Disables automated opening of downloaded video |
| `--no-terminals` | None | `False` | Disables GUI terminal windows, runs in background |
| `--spawn-terminals`| None | Config default | Forces GUI terminal windows if display available |
| `--no-ytdlp` | None | `False` | Excludes yt-dlp agent tier from the race |
| `--no-static` | None | `False` | Excludes BeautifulSoup static scanner tier from the race |
| `--no-browser` | None | `False` | Excludes headless Chromium Selenium tier from the race |
| `--no-scrapling` | None | `False` | Excludes Scrapling adaptive scanner tier from the race |

### Exit Codes

| Code | Meaning |
|------|---------|
| `0` | Extraction and download succeeded, or help/info displayed |
| `1` | Invalid argument, malformed URL, or fatal download error |
| `2` | No downloadable media candidates found (all tiers failed/timed out) |
| `130` | Execution interrupted by user (`SIGINT` / `Ctrl+C`) |

---

## 2. Configuration Schema (`config/config.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoExtractorConfig",
  "type": "object",
  "properties": {
    "version": { "type": "string" },
    "download_directory": { "type": "string" },
    "preferred_format": { "type": "string" },
    "merge_format": { "type": "string", "enum": ["mp4", "mkv", "webm"] },
    "browser_wait_seconds": { "type": "integer", "minimum": 1 },
    "use_ytdlp": { "type": "boolean" },
    "use_static_scanner": { "type": "boolean" },
    "use_browser": { "type": "boolean" },
    "use_scrapling": { "type": "boolean" },
    "race_timeout": { "type": "number", "minimum": 1.0 },
    "confidence_threshold": { "type": "integer", "minimum": 0 },
    "spawn_terminals": { "type": "boolean" },
    "github": {
      "type": "object",
      "properties": {
        "repository": { "type": "string" },
        "branch": { "type": "string" }
      }
    }
  },
  "required": [
    "version",
    "download_directory",
    "preferred_format",
    "merge_format",
    "use_ytdlp",
    "use_static_scanner",
    "use_browser",
    "use_scrapling",
    "race_timeout",
    "confidence_threshold"
  ]
}
```

---

## 3. History Schema (`config/history.json`)

```json
{
  "$schema": "http://json-schema.org/draft-07/schema#",
  "title": "VideoExtractorHistory",
  "type": "array",
  "items": {
    "type": "object",
    "properties": {
      "url": { "type": "string", "format": "uri" },
      "platform": { "type": "string" },
      "engine": { "type": "string", "enum": ["ytdlp", "static", "browser", "scrapling", "unknown"] },
      "quality": { "type": ["string", "null"] },
      "output": { "type": ["string", "null"] },
      "title": { "type": ["string", "null"] },
      "race_duration_ms": { "type": ["integer", "null"] }
    },
    "required": ["url", "engine"]
  },
  "maxItems": 100
}
```

---

## 4. Candidate Data Model (`src/candidate.py`)

```python
@dataclass
class Candidate:
    url: str
    source: str
    mime_type: str = ""
    status: Optional[int] = None
    extension: str = ""
    score: int = 0
    metadata: dict = field(default_factory=dict)

    @property
    def is_stream(self) -> bool:
        return self.extension.lower() in {".m3u8", ".mpd", ".ism", ".isml", ".m3u"}

    @property
    def is_direct_video(self) -> bool:
        return self.extension.lower() in {".mp4", ".webm", ".m4v", ".mov", ".mkv", ".avi", ".flv"}

    @property
    def label(self) -> str:
        if self.is_stream:
            return "STREAM"
        if self.is_direct_video:
            return "VIDEO"
        return "UNKNOWN"
```

### Scoring Rubric

- `.m3u8` / `.mpd` extension: `+100`
- `.mp4` extension: `+95`
- `.webm` extension: `+90`
- Other recognized video extensions: `+70`
- `video/*` MIME type: `+50`
- `mpegurl` / `dash+xml` in MIME: `+50`
- Keyword in URL (`master`: `+15`, `playlist`: `+10`, `manifest`: `+10`)
- HTTP 200 verification status: `+10`

---

## 5. Worker IPC Protocol

Tier agents run in isolated processes spawned by `src/terminal_launcher.py`. Communication with `src/race_controller.py` follows a file-based IPC protocol:

1. **PID File (`<session_dir>/<tier>.pid`):**
   - The worker writes its exact OS PID (`os.getpid()`) as ASCII text immediately on launch.
   - Allows the controller to track and terminate the child process tree even if launched via intermediate terminal shells.

2. **Result File (`<session_dir>/<tier>_result.json`):**
   - On completion, the worker atomically writes the result payload:
   ```json
   {
     "success": true,
     "tier": "scrapling",
     "pid": 28412,
     "candidate": {
       "url": "https://example.com/stream.m3u8",
       "source": "scrapling:video:src",
       "mime_type": "application/x-mpegURL",
       "status": 200,
       "extension": ".m3u8",
       "score": 160,
       "metadata": {}
     },
     "error": null
   }
   ```
   - If no candidate was found or an exception occurred:
   ```json
   {
     "success": false,
     "tier": "scrapling",
     "pid": 28412,
     "candidate": null,
     "error": "No media elements found"
   }
   ```
