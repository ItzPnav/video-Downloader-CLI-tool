"""
Agent Worker Module for Video Extractor.

Executes a single extraction tier (yt-dlp, static HTML, headless browser, or Scrapling)
as an independent process or thread.
Writes its PID immediately on launch and emits candidate results to a JSON output file.
"""

import argparse
import json
import os
import sys
from pathlib import Path
from typing import Optional

# Force UTF-8 stream encoding on Windows
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

try:
    from .candidate import Candidate
    from .selector import choose
except (ImportError, ValueError):
    from video_downloader.candidate import Candidate
    from video_downloader.selector import choose


def run_ytdlp_agent(url: str, requested_quality: Optional[str] = None) -> Optional[Candidate]:
    """Run yt-dlp native extraction tier."""
    try:
        from .site_extractor import available, extract_info, choose_format
    except (ImportError, ValueError):
        from video_downloader.site_extractor import available, extract_info, choose_format

    if not available():
        print("[-] [yt-dlp] yt-dlp binary is not available.")
        return None

    print(f"[+] [yt-dlp] Extracting info for: {url}")
    info = extract_info(url)
    if not info:
        print("[!] [yt-dlp] Could not extract media info.")
        return None

    format_info = choose_format(info, requested_quality)
    direct_url = format_info.get("url") if format_info else url

    candidate = Candidate(
        url=direct_url,
        source="ytdlp",
        mime_type="video/mp4",
        extension=".mp4",
        score=100,
        metadata={
            "title": info.get("title", "video"),
            "original_url": url,
            "engine": "ytdlp",
            "format": format_info,
        },
    )
    print(f"[✓] [yt-dlp] Successfully found media: {info.get('title', 'video')}")
    return candidate


def run_static_agent(url: str) -> Optional[Candidate]:
    """Run static HTML scanner (BeautifulSoup) tier."""
    try:
        from .static_scanner import StaticScanner
    except (ImportError, ValueError):
        from video_downloader.static_scanner import StaticScanner

    print(f"[+] [static] Scanning HTML DOM: {url}")
    scanner = StaticScanner(url)
    candidates = scanner.scan()
    best = choose(candidates)
    if best:
        print(f"[✓] [static] Found media candidate: {best.url} (score={best.score})")
    else:
        print("[!] [static] No media candidates found.")
    return best


def run_browser_agent(url: str) -> Optional[Candidate]:
    """Run headless Chromium / Selenium network sniffer tier."""
    try:
        from .browser_scanner import BrowserScanner
    except (ImportError, ValueError):
        from video_downloader.browser_scanner import BrowserScanner

    print(f"[+] [browser] Sniffing network streams: {url}")
    scanner = BrowserScanner(url)
    candidates = scanner.scan()
    best = choose(candidates)
    if best:
        print(f"[✓] [browser] Found media stream: {best.url} (score={best.score})")
    else:
        print("[!] [browser] No streams captured by browser.")
    return best


def run_scrapling_agent(url: str) -> Optional[Candidate]:
    """Run Scrapling adaptive fetcher and DOM scanner tier."""
    try:
        from .scrapling_scanner import ScraplingScanner, SCRAPLING_AVAILABLE
    except (ImportError, ValueError):
        from video_downloader.scrapling_scanner import ScraplingScanner, SCRAPLING_AVAILABLE

    if not SCRAPLING_AVAILABLE:
        print("[!] [scrapling] Scrapling library not installed.")
        return None

    print(f"[+] [scrapling] Adaptive scanning: {url}")
    scanner = ScraplingScanner(url)
    candidates = scanner.scan()
    best = choose(candidates)
    if best:
        print(f"[✓] [scrapling] Found media candidate: {best.url} (score={best.score})")
    else:
        print("[!] [scrapling] No candidates found by Scrapling.")
    return best


def run_tier_agent(tier: str, url: str, requested_quality: Optional[str] = None) -> Optional[Candidate]:
    """Dispatch execution to the specified tier."""
    tier_lower = tier.lower()
    if tier_lower in ("ytdlp", "yt-dlp", "site"):
        return run_ytdlp_agent(url, requested_quality)
    elif tier_lower in ("static", "static_scanner"):
        return run_static_agent(url)
    elif tier_lower in ("browser", "selenium"):
        return run_browser_agent(url)
    elif tier_lower in ("scrapling", "scrapling_scanner"):
        return run_scrapling_agent(url)
    elif tier_lower == "test_fast":
        return Candidate(
            url="https://example.com/fast.mp4",
            source="test_fast",
            mime_type="video/mp4",
            extension=".mp4",
            score=95,
            metadata={"title": "Test Fast Video"},
        )
    elif tier_lower == "test_hung":
        import time
        time.sleep(60)
        return None
    else:
        raise ValueError(f"Unknown tier: {tier}")


def candidate_to_dict(c: Candidate) -> dict:
    """Serialize Candidate dataclass to dictionary."""
    return {
        "url": c.url,
        "source": c.source,
        "mime_type": c.mime_type,
        "status": c.status,
        "extension": c.extension,
        "score": c.score,
        "metadata": c.metadata,
    }


def dict_to_candidate(d: dict) -> Candidate:
    """Deserialize dictionary back to Candidate dataclass."""
    return Candidate(
        url=d.get("url", ""),
        source=d.get("source", ""),
        mime_type=d.get("mime_type", ""),
        status=d.get("status"),
        extension=d.get("extension", ""),
        score=d.get("score", 0),
        metadata=d.get("metadata", {}),
    )


def main():
    parser = argparse.ArgumentParser(description="Video Extractor Tier Agent Worker")
    parser.add_argument("--tier", required=True, help="Tier name (ytdlp, static, browser, scrapling)")
    parser.add_argument("--url", required=True, help="Target URL to extract")
    parser.add_argument("--result-file", required=True, help="JSON file to write extraction candidate")
    parser.add_argument("--pid-file", help="File to write worker PID into")
    parser.add_argument("--quality", help="Requested quality (e.g. 1080p)")
    args = parser.parse_args()

    pid = os.getpid()

    # Write PID immediately so race controller can track and kill this process tree
    if args.pid_file:
        try:
            pid_path = Path(args.pid_file)
            pid_path.parent.mkdir(parents=True, exist_ok=True)
            pid_path.write_text(str(pid), encoding="utf-8")
        except Exception as e:
            print(f"[!] Worker could not write PID file: {e}", file=sys.stderr)

    print()
    print("=" * 60)
    print(f"        VIDEO EXTRACTOR — AGENT: [{args.tier.upper()}]")
    print(f"        PID: {pid}")
    print(f"        URL: {args.url}")
    print("=" * 60)
    print()

    result_data = {
        "success": False,
        "tier": args.tier,
        "pid": pid,
        "candidate": None,
        "error": None,
    }

    try:
        candidate = run_tier_agent(args.tier, args.url, args.quality)
        if candidate:
            result_data["success"] = True
            result_data["candidate"] = candidate_to_dict(candidate)
            print(f"\n[✓] Agent [{args.tier}] finished successfully with score {candidate.score}!")
        else:
            result_data["error"] = "No suitable media candidates found."
            print(f"\n[!] Agent [{args.tier}] finished without candidate.")
    except Exception as exc:
        result_data["error"] = str(exc)
        print(f"\n[-] Agent [{args.tier}] failed with exception: {exc}", file=sys.stderr)

    # Write result to file
    try:
        res_path = Path(args.result_file)
        res_path.parent.mkdir(parents=True, exist_ok=True)
        res_path.write_text(json.dumps(result_data, indent=2), encoding="utf-8")
    except Exception as e:
        print(f"[-] Failed to write result file: {e}", file=sys.stderr)

    return 0 if result_data["success"] else 1


if __name__ == "__main__":
    sys.exit(main())
