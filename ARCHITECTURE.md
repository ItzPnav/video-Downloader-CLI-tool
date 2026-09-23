# ARCHITECTURE.md — System Architecture

## 1. Paradigm Shift: Sequential Waterfall vs. Concurrent Multi-Agent Race

In version 0.1.0, Video Extractor used a sequential waterfall architecture:
```
[URL Input] ──> [yt-dlp Extractor]
                      │ (fails)
                      ▼
               [Static HTML Scanner]
                      │ (fails)
                      ▼
               [Browser Sniffer] ──> [Download / Fail]
```
**Bottlenecks of the Waterfall Model:**
1. **Compounding Latency:** When yt-dlp encounters an unsupported domain, it often exhausts network retry timeouts (up to 30–60s) before falling back to static scanning.
2. **Resource Inefficiency:** A fast tier (like Scrapling or static HTML) was held hostage behind slower tiers.
3. **Fragility:** Failure in one tier's detection could prevent lighter, specialized extractors from executing.

In version 0.2.0, the system transitions to a **Concurrent Multi-Agent Race**:
```
                           [URL Input]
                                │
       ┌────────────────────────┼────────────────────────┐
       ▼                        ▼                        ▼
[yt-dlp Agent]        [Static Scanner Agent]    [Browser Sniffer Agent]    [Scrapling Agent]
       │                        │                        │                        │
       └────────────────────────┼────────────────────────┘                        │
                                │                                                 │
                                └─────────────────────────────────────────────────┘
                                                       │
                                                       ▼
                                            [LangGraph Reducer Node]
                                         "First valid candidate wins!"
                                                       │
                                        ┌──────────────┴──────────────┐
                                        ▼                             ▼
                            [Kill Losing Agent PIDs]       [FFmpeg Stream Download]
```

---

## 2. Framework Justification: LangGraph vs. LangChain Runnables

The system orchestrator was evaluated between **LangGraph** (`StateGraph`) and **LangChain Parallel Runnables** (`RunnableParallel`).

### Chosen: LangGraph

**Key Architectural Justifications:**
1. **Explicit Graph Topology:**
   LangGraph natively models workflows as directed graphs with state reducers. The race topology (`START` branching to parallel nodes feeding into a single reducer node) matches LangGraph's execution primitives directly.
2. **Deterministic State Accumulation:**
   The `RaceState` TypedDict specifies explicit reducer rules (e.g. `Annotated[list, operator.add]` and dictionary merging). This allows each tier node to register its PID and candidate results into a unified state without race conditions or shared-memory corruption.
3. **Early-Exit & Lifecycle Termination:**
   LangChain's `RunnableParallel` enforces full branch completion before yielding results, making early cancellation of losing branches awkward and reliant on external task cancellation. LangGraph allows the reducer node to evaluate the first qualifying candidate and trigger process termination while maintaining clean execution metrics.
4. **Reduced Overhead & Minimal Dependencies:**
   LangGraph provides direct graph compiling without bringing in the sprawling chaining surface, prompts, and prompt templates that LangChain core bundles.

---

## 3. Component Architecture

```
+-------------------------------------------------------------------------------+
|                                 CLI Entrypoint                                |
|                                 (src/main.py)                                 |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                           Platform Router Registry                            |
|                                (src/router.py)                                |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                           Extraction Race Controller                          |
|                            (src/race_controller.py)                           |
|       - Spawns agents simultaneously                                          |
|       - LangGraph state tracking                                              |
|       - Polls for first candidate >= confidence threshold                     |
|       - Kills losing PIDs immediately                                         |
+---------------------------------------+---------------------------------------+
                                        |
         +-----------------+------------+-------------+-----------------+
         |                 |                          |                 |
         v                 v                          v                 v
+-----------------+ +-----------------+    +-----------------+ +-----------------+
|   yt-dlp Agent  | |  Static Agent   |    |  Browser Agent  | | Scrapling Agent |
| (src/site_      | | (src/static_    |    | (src/browser_   | | (src/scrapling_ |
|  extractor.py)  | |  scanner.py)    |    |  scanner.py)    | |  scanner.py)    |
+-----------------+ +-----------------+    +-----------------+ +-----------------+
         |                 |                          |                 |
         +-----------------+------------+-------------+-----------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                            Cross-Platform Spawner                             |
|                          (src/terminal_launcher.py)                           |
|       Windows: wt.exe / start cmd.exe                                         |
|       macOS: osascript Terminal.app                                           |
|       Linux: gnome-terminal, konsole, xterm                                   |
|       Termux: tmux, screen, background subprocess                             |
+---------------------------------------+---------------------------------------+
                                        |
                                        v
+-------------------------------------------------------------------------------+
|                               Stream Downloader                               |
|                              (src/downloader.py)                              |
|       - yt-dlp adaptive stream muxing (bv*+ba/b)                              |
|       - FFmpeg copy muxer for M3U8, MPD, MP4 streams                          |
+-------------------------------------------------------------------------------+
```

---

## 4. Scrapling Extraction Tier Design

`src/scrapling_scanner.py` acts as a high-speed, adaptive extractor designed to thrive against bot mitigation and mutating DOMs.

```
                  Scrapling Extraction Pipeline
                               │
                               v
                     [ Fetcher.get(url) ]
                    (Fast plain HTTP fetch)
                               │
            ┌──────────────────┴──────────────────┐
            ▼ (blocked: 401/403/429/Cloudflare)   ▼ (status 200 OK)
   [ StealthyFetcher.fetch ]                      │
   (Headless stealth browser)                     │
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                               v
                    [ Adaptive Selector DOM ]
            • Scans <video>, <source>, <iframe>
            • Scans custom attributes ([data-src], [data-video])
            • Scans JSON-LD schema structures
            • Regex scanning on script contents
                               │
            ┌──────────────────┴──────────────────┐
            ▼ (candidates found)                  ▼ (no candidates)
   [ HTTP HEAD Inspection ]              [ Markdown Fallback ]
   (Probes status and MIME type)         (Extracts links from page.markdown())
            │                                     │
            └──────────────────┬──────────────────┘
                               │
                               v
                    [ Candidate Scorer ]
                    (Candidate dataclass)
```

**Key Capabilities:**
- **Two-tier fetch strategy:** Tries ultra-fast HTTP `Fetcher` first, saving browser overhead on standard pages, and automatically escalates to `StealthyFetcher` only when challenged.
- **Adaptive Selector Relocation:** Scrapling's selector engine dynamically adapts to DOM mutations, surviving minor class/attribute renames by content publishers.
- **Markdown Text Mining:** When JavaScript-heavy sites strip standard media DOM tags, `page.markdown()` strips boilerplate and exposes raw media URLs.

---

## 5. Process Lifecycle and Tree Termination

When multiple processes are spawned across independent terminal windows, normal logical task cancellation does not terminate child processes (such as spawned Chromium browsers or subshells).

Video Extractor solves this with a **Two-Tier PID Tracking & Tree Killing Protocol**:

1. **PID File Handshake:** Each worker process (`src/agent_worker.py`) writes its real system PID (`os.getpid()`) to a session PID file `<session_dir>/<tier>.pid` immediately on launch.
2. **Process Tree Kill:** When a winner emerges, `kill_process_by_pid(pid)` uses `psutil.Process(pid).children(recursive=True)` to enumerate and kill every descendant process in the tree before killing the parent.
3. **OS-Level Fallback:** On Windows, `taskkill /F /T /PID <pid>` ensures associated console windows close. On Unix/Linux/macOS, `os.killpg(os.getpgid(pid), signal.SIGKILL)` terminates the process group.
