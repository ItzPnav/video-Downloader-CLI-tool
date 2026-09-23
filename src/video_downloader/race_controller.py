"""
Race Controller Module for Video Extractor.

Replaces the sequential waterfall with a concurrent multi-agent race across 4 tiers:
1. yt-dlp agent
2. Static HTML scanner agent (BeautifulSoup)
3. Headless browser agent (Selenium + Chromium)
4. Scrapling adaptive scanner agent

Modeled as a parallel graph using LangGraph where each node executes an extractor tier,
feeding into a single 'first successful result wins' reducer node.
Terminates all losing agent processes by PID immediately upon first winner.
"""

import json
import operator
import os
import shutil
import sys
import tempfile
import time
import warnings
from dataclasses import dataclass
from pathlib import Path
from typing import Annotated, Any, Dict, List, Optional, TypedDict

# Suppress non-fatal upstream compatibility warnings on Python 3.14+
warnings.filterwarnings("ignore", category=UserWarning, module="langchain_core")
warnings.filterwarnings("ignore", category=DeprecationWarning)

# Force UTF-8 stream encoding on Windows to support status symbols (✓, ✗, etc.)
if sys.platform == "win32":
    try:
        if hasattr(sys.stdout, "reconfigure"):
            sys.stdout.reconfigure(encoding="utf-8", errors="replace")
        if hasattr(sys.stderr, "reconfigure"):
            sys.stderr.reconfigure(encoding="utf-8", errors="replace")
    except Exception:
        pass

# Ensure src directory is in sys.path
SRC_DIR = Path(__file__).resolve().parent
if str(SRC_DIR) not in sys.path:
    sys.path.insert(0, str(SRC_DIR))

from .candidate import Candidate
from .agent_worker import dict_to_candidate, candidate_to_dict
from .terminal_launcher import spawn_tier, kill_process_by_pid, LaunchedProcess
from .utils import load_config, write_history

try:
    from langgraph.graph import StateGraph, START, END
    LANGGRAPH_AVAILABLE = True
except ImportError:
    LANGGRAPH_AVAILABLE = False


class RaceState(TypedDict, total=False):
    url: str
    requested_quality: Optional[str]
    timeout: float
    confidence_threshold: int
    active_tiers: list[str]
    session_dir: str
    prefer_gui: bool
    spawned_pids: Annotated[dict[str, int], lambda a, b: {**a, **b}]
    winning_candidate: Optional[dict]
    winning_engine: Optional[str]
    race_duration_ms: Optional[int]
    killed_pids: Annotated[list[int], operator.add]
    timed_out: bool


@dataclass
class RaceResult:
    winner_engine: Optional[str]
    candidate: Optional[Candidate]
    duration_ms: int
    spawned_pids: dict[str, int]
    killed_pids: list[int]
    timed_out: bool = False


class ExtractionRaceController:
    """
    Coordinates concurrent multi-agent tier racing.
    Spawns independent terminal/subprocess workers per tier,
    monitors for first winner above confidence threshold,
    and terminates losing processes immediately by PID.
    """

    DEFAULT_TIMEOUT = 20.0
    DEFAULT_CONFIDENCE = 50
    DEFAULT_BROWSER_GRACE = 2.5

    def __init__(
        self,
        url: str,
        requested_quality: Optional[str] = None,
        timeout: Optional[float] = None,
        confidence_threshold: Optional[int] = None,
        no_browser: bool = False,
        no_ytdlp: bool = False,
        no_static: bool = False,
        no_scrapling: bool = False,
        prefer_gui: Optional[bool] = None,
        browser_grace_seconds: Optional[float] = None,
    ):
        self.url = url
        self.requested_quality = requested_quality
        self.config = load_config()

        self.timeout = float(
            timeout
            if timeout is not None
            else self.config.get("race_timeout", self.DEFAULT_TIMEOUT)
        )
        self.confidence_threshold = int(
            confidence_threshold
            if confidence_threshold is not None
            else self.config.get("confidence_threshold", self.DEFAULT_CONFIDENCE)
        )

        grace = self.config.get("browser_grace_seconds", self.DEFAULT_BROWSER_GRACE)
        self.browser_grace_seconds = float(
            browser_grace_seconds
            if browser_grace_seconds is not None
            else grace
        )

        # Determine active tiers based on config and flags
        self.active_tiers: list[str] = []

        if not no_ytdlp and self.config.get("use_ytdlp", True):
            self.active_tiers.append("ytdlp")

        if not no_static and self.config.get("use_static_scanner", True):
            self.active_tiers.append("static")

        if not no_scrapling and self.config.get("use_scrapling", True):
            self.active_tiers.append("scrapling")

        if not no_browser and self.config.get("use_browser", True):
            self.active_tiers.append("browser")

        if prefer_gui is not None:
            self.prefer_gui = prefer_gui
        else:
            self.prefer_gui = bool(self.config.get("spawn_terminals", False))

        # Split into fast immediate tiers vs heavy deferred tiers (browser)
        self.immediate_tiers: list[str] = [
            t for t in self.active_tiers
            if t != "browser" or self.browser_grace_seconds <= 0
        ]
        self.deferred_tiers: list[str] = [
            t for t in self.active_tiers
            if t == "browser" and self.browser_grace_seconds > 0
        ]
        if not self.immediate_tiers and self.deferred_tiers:
            self.immediate_tiers = list(self.deferred_tiers)
            self.deferred_tiers = []

        # Runtime tracking
        self.session_dir = Path(tempfile.mkdtemp(prefix="video_race_"))
        self.launched_processes: dict[str, LaunchedProcess] = {}
        self.spawned_pids: dict[str, int] = {}
        self.killed_pids: list[int] = []
        self._start_time: float = 0.0

    def _spawn_single_tier(self, tier: str) -> LaunchedProcess:
        """Spawn worker process for a single tier."""
        python_exe = sys.executable
        pid_file = self.session_dir / f"{tier}.pid"
        result_file = self.session_dir / f"{tier}_result.json"
        log_file = self.session_dir / f"{tier}.log"

        worker_cmd = [
            python_exe,
            "-W", "ignore",
            "-m", "video_downloader.agent_worker",
            "--tier", tier,
            "--url", self.url,
            "--result-file", str(result_file),
            "--pid-file", str(pid_file),
        ]
        if self.requested_quality:
            worker_cmd.extend(["--quality", str(self.requested_quality)])

        # Ensure PYTHONPATH includes src directory for local dev runs
        env = os.environ.copy()
        current_pythonpath = env.get("PYTHONPATH", "")
        src_parent = str(SRC_DIR.parent)
        if src_parent not in current_pythonpath.split(os.pathsep):
            env["PYTHONPATH"] = f"{src_parent}{os.pathsep}{current_pythonpath}" if current_pythonpath else src_parent

        title = f"Extractor Agent — [{tier.upper()}]"
        proc = spawn_tier(
            tier=tier,
            command=worker_cmd,
            title=title,
            pid_file=pid_file,
            prefer_gui=self.prefer_gui,
            cwd=SRC_DIR.parent,
            env=env,
            log_file=log_file,
            echo_stdout=self.prefer_gui,
        )
        self.launched_processes[tier] = proc
        self.spawned_pids[tier] = proc.pid
        print(f"[+] Spawning agent [{tier}] (PID: {proc.pid})...")
        return proc

    def _spawn_all_tiers(self) -> None:
        """Spawn all immediate tier agents concurrently."""
        for tier in self.immediate_tiers:
            self._spawn_single_tier(tier)
        if self.deferred_tiers:
            print(f"[+] Deferred tier [browser] held in standby (grace: {self.browser_grace_seconds:.1f}s)...")

    def _run_race_reducer(self, state: RaceState) -> dict:
        """
        Reducer implementation: polls for the first candidate >= confidence threshold,
        adaptively escalates to deferred tiers if grace timer expires,
        renders single-terminal status display, and terminates losing processes by PID.
        """
        winner_tier: Optional[str] = None
        winning_candidate: Optional[Candidate] = None
        timed_out = False

        poll_interval = 0.12
        deadline = self._start_time + self.timeout
        is_interactive = sys.stdout.isatty() and not self.prefer_gui

        tier_statuses: dict[str, str] = {t: "running" for t in self.immediate_tiers}
        for t in self.deferred_tiers:
            tier_statuses[t] = f"standby ({self.browser_grace_seconds:.1f}s)"

        while time.time() < deadline:
            elapsed = time.time() - self._start_time

            # Update actual worker PIDs if reported via pid files
            for tier, handle in self.launched_processes.items():
                actual_pid = handle.get_actual_pid()
                self.spawned_pids[tier] = actual_pid

            # Check results from each tier first
            for tier in list(self.launched_processes.keys()):
                result_file = self.session_dir / f"{tier}_result.json"
                if result_file.exists():
                    try:
                        data = json.loads(result_file.read_text(encoding="utf-8"))
                        if data.get("success") and data.get("candidate"):
                            cand = dict_to_candidate(data["candidate"])
                            tier_statuses[tier] = f"score {cand.score}"
                            if cand.score >= self.confidence_threshold:
                                winner_tier = tier
                                winning_candidate = cand
                                break
                        else:
                            tier_statuses[tier] = "no media"
                    except Exception:
                        pass

            if winner_tier is not None:
                break

            # Check if we should escalate to deferred browser tier
            if "browser" in self.deferred_tiers and "browser" not in self.launched_processes:
                time_left = max(0.0, self.browser_grace_seconds - elapsed)
                tier_statuses["browser"] = f"standby ({time_left:.1f}s)"

                all_immediate_finished = bool(self.immediate_tiers) and all(
                    (self.session_dir / f"{t}_result.json").exists() for t in self.immediate_tiers
                )

                if elapsed >= self.browser_grace_seconds or all_immediate_finished:
                    if is_interactive:
                        sys.stdout.write("\r\033[K")
                        sys.stdout.flush()
                    if all_immediate_finished and elapsed < self.browser_grace_seconds:
                        print(f"[!] Fast tiers finished without qualifying media — releasing browser agent early...")
                    else:
                        print(f"[+] Grace timer elapsed ({self.browser_grace_seconds:.1f}s) — releasing browser agent...")
                    self._spawn_single_tier("browser")
                    tier_statuses["browser"] = "running"

            # Check if all processes completed without winner
            all_exited = True
            all_expected = set(self.immediate_tiers)
            if "browser" in self.launched_processes:
                all_expected.add("browser")
            elif "browser" in self.deferred_tiers:
                all_exited = False

            if all_exited:
                for tier in all_expected:
                    result_file = self.session_dir / f"{tier}_result.json"
                    if not result_file.exists():
                        all_exited = False
                        break

            if all_exited and not winner_tier:
                if is_interactive:
                    sys.stdout.write("\r\033[K")
                    sys.stdout.flush()
                print("[!] All extraction agents completed without finding qualifying media.")
                break

            # Render inline single-terminal status ticker
            if is_interactive:
                status_parts = [f"{t}: {tier_statuses.get(t, 'running')}" for t in self.active_tiers]
                line = f"\r[+] Racing ({elapsed:.1f}s / {self.timeout:.0f}s) | " + " | ".join(status_parts)
                if len(line) > 120:
                    line = line[:117] + "..."
                sys.stdout.write(line + "\033[K")
                sys.stdout.flush()

            time.sleep(poll_interval)

        if is_interactive:
            sys.stdout.write("\r\033[K")
            sys.stdout.flush()

        duration_ms = int((time.time() - self._start_time) * 1000)

        if winner_tier is None and time.time() >= deadline:
            timed_out = True
            print(f"\n[!] Race timed out after {self.timeout:.1f}s with no winner.")

        # Handle termination based on race outcome
        if winner_tier and winning_candidate:
            print()
            print("=" * 60)
            print(f"[✓] Agent [{winner_tier}] won the race in {duration_ms}ms! (Score: {winning_candidate.score})")
            print("=" * 60)

            for tier, handle in self.launched_processes.items():
                if tier != winner_tier:
                    target_pid = handle.get_actual_pid()
                    print(f"[+] Terminating losing agent [{tier}] (PID: {target_pid})...")
                    handle.kill()
                    kill_process_by_pid(target_pid)
                    print(f"[✓] Successfully killed PID: {target_pid}")
                    self.killed_pids.append(target_pid)
                else:
                    # Cleanly reap the winning process
                    handle.reap(timeout=1.0)

        elif timed_out:
            print("[+] Terminating all running agent processes due to timeout...")
            for tier, handle in self.launched_processes.items():
                target_pid = handle.get_actual_pid()
                handle.kill()
                kill_process_by_pid(target_pid)
                print(f"[✓] Killed PID: {target_pid} ({tier})")
                self.killed_pids.append(target_pid)
        else:
            # Reaping processes if all finished with failure
            for handle in self.launched_processes.values():
                handle.reap(timeout=0.5)

        return {
            "winning_candidate": candidate_to_dict(winning_candidate) if winning_candidate else None,
            "winning_engine": winner_tier,
            "race_duration_ms": duration_ms,
            "spawned_pids": self.spawned_pids,
            "killed_pids": self.killed_pids,
            "timed_out": timed_out,
        }

    def build_langgraph(self):
        """Construct the LangGraph StateGraph modeling parallel tier nodes and reducer."""
        if not LANGGRAPH_AVAILABLE:
            return None

        builder = StateGraph(RaceState)

        # Define parallel tier node that spawns the agent process
        def make_tier_node(tier_name: str):
            def tier_node(state: RaceState) -> dict:
                handle = self._spawn_single_tier(tier_name)
                return {"spawned_pids": {tier_name: handle.pid}}
            return tier_node

        for tier in self.immediate_tiers:
            builder.add_node(tier, make_tier_node(tier))
            builder.add_edge(START, tier)
            builder.add_edge(tier, "reducer")

        # Reducer node
        def reducer_node(state: RaceState) -> dict:
            return self._run_race_reducer(state)

        builder.add_node("reducer", reducer_node)
        builder.add_edge("reducer", END)

        return builder.compile()

    def run_race(self) -> RaceResult:
        """
        Execute the multi-agent tier race.
        Orchestrates parallel tier nodes into a 'first valid candidate wins' reducer.
        Terminates losing processes immediately by PID.
        """
        # Refresh immediate and deferred tiers in case active_tiers was modified
        self.immediate_tiers = [
            t for t in self.active_tiers
            if t != "browser" or self.browser_grace_seconds <= 0
        ]
        self.deferred_tiers = [
            t for t in self.active_tiers
            if t == "browser" and self.browser_grace_seconds > 0
        ]
        if not self.immediate_tiers and self.deferred_tiers:
            self.immediate_tiers = list(self.deferred_tiers)
            self.deferred_tiers = []
        print()
        print("=" * 60)
        print("           CONCURRENT MULTI-AGENT EXTRACTION RACE")
        print(f"  URL       : {self.url}")
        print(f"  Agents ({len(self.active_tiers)}): {', '.join(self.active_tiers)}")
        if self.deferred_tiers:
            print(f"  Deferred  : {', '.join(self.deferred_tiers)} (grace: {self.browser_grace_seconds:.1f}s)")
        print(f"  Mode      : {'External Windows' if self.prefer_gui else 'Single Terminal (Background)'}")
        print(f"  Timeout   : {self.timeout:.1f}s")
        print(f"  Threshold : Score >= {self.confidence_threshold}")
        print("=" * 60)
        print()

        if not self.active_tiers:
            print("[-] No extraction agents enabled for the race.")
            return RaceResult(None, None, 0, {}, [], timed_out=False)

        self._start_time = time.time()

        winner_engine: Optional[str] = None
        winning_candidate: Optional[Candidate] = None
        duration_ms: int = 0
        timed_out: bool = False

        try:
            if LANGGRAPH_AVAILABLE:
                try:
                    graph = self.build_langgraph()
                    if graph:
                        final_state = graph.invoke({
                            "url": self.url,
                            "requested_quality": self.requested_quality,
                            "timeout": self.timeout,
                            "confidence_threshold": self.confidence_threshold,
                            "active_tiers": self.active_tiers,
                            "spawned_pids": {},
                            "killed_pids": [],
                            "session_dir": str(self.session_dir),
                            "prefer_gui": self.prefer_gui,
                        })
                        winner_engine = final_state.get("winning_engine")
                        if final_state.get("winning_candidate"):
                            winning_candidate = dict_to_candidate(final_state["winning_candidate"])
                        duration_ms = final_state.get("race_duration_ms", 0)
                        timed_out = bool(final_state.get("timed_out", False))
                except Exception as graph_err:
                    print(f"[!] LangGraph invocation notice: {graph_err}, falling back to direct race coordinator.", file=sys.stderr)
                    # If LangGraph failed before spawning or in execution, direct fallback
                    if not self.launched_processes:
                        self._spawn_all_tiers()
                    res_dict = self._run_race_reducer({})
                    winner_engine = res_dict.get("winning_engine")
                    if res_dict.get("winning_candidate"):
                        winning_candidate = dict_to_candidate(res_dict["winning_candidate"])
                    duration_ms = res_dict.get("race_duration_ms", 0)
                    timed_out = bool(res_dict.get("timed_out", False))
            else:
                self._spawn_all_tiers()
                res_dict = self._run_race_reducer({})
                winner_engine = res_dict.get("winning_engine")
                if res_dict.get("winning_candidate"):
                    winning_candidate = dict_to_candidate(res_dict["winning_candidate"])
                duration_ms = res_dict.get("race_duration_ms", 0)
                timed_out = bool(res_dict.get("timed_out", False))

        finally:
            # Ensure all handles have closed pipes
            for handle in self.launched_processes.values():
                handle.close_streams()

            # Clean up temp session directory
            try:
                shutil.rmtree(self.session_dir, ignore_errors=True)
            except Exception:
                pass

        return RaceResult(
            winner_engine=winner_engine,
            candidate=winning_candidate,
            duration_ms=duration_ms,
            spawned_pids=self.spawned_pids,
            killed_pids=self.killed_pids,
            timed_out=timed_out,
        )
