"""
Scrapling Scanner Tier for Video Extractor.

Integrates the Scrapling library (https://github.com/D4Vinci/Scrapling) as an extraction tier.
Uses fast HTTP Fetcher by default, escalating to StealthyFetcher when blocked.
Leverages Scrapling's adaptive parser for DOM extraction and auto-relocation,
with regex, JSON-LD, and markdown fallbacks.
"""

import json
import re
from urllib.parse import urljoin, urlparse

import requests

from candidate import (
    Candidate,
    detect_extension,
    score_candidate,
)

try:
    from scrapling import Fetcher, StealthyFetcher, Selector
    SCRAPLING_AVAILABLE = True
except ImportError:
    SCRAPLING_AVAILABLE = False
    Fetcher = None
    StealthyFetcher = None
    Selector = None


class ScraplingScanner:
    """
    Media extractor tier utilizing Scrapling's adaptive parser and fetchers.
    Mirrors the Candidate dataclass and score_candidate scoring pipeline.
    """

    ATTRIBUTES = (
        "src",
        "href",
        "data-src",
        "data-url",
        "data-file",
        "data-video",
        "data-video-url",
        "data-video-src",
        "data-media",
        "data-media-url",
        "data-stream",
        "data-stream-url",
        "data-playlist",
        "data-manifest",
    )

    BLOCKED_STATUS_CODES = {401, 403, 429, 503}
    BLOCKED_KEYWORDS = (
        "cloudflare",
        "just a moment",
        "attention required",
        "access denied",
        "captcha",
        "verify you are human",
        "please wait...",
    )

    def __init__(self, url: str):
        self.url = url
        self.candidates: list[Candidate] = []
        self.seen: set[str] = set()

        self.session = requests.Session()
        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Linux; Android 14) "
                "AppleWebKit/537.36 "
                "(KHTML, like Gecko) "
                "Chrome/139.0 Mobile Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })

    def add(self, value: str, source: str, base_url: str = None, mime: str = ""):
        if not value:
            return

        value = str(value).strip().strip("\"'")

        if value.startswith("data:"):
            return

        if value.startswith("//"):
            value = "https:" + value

        if base_url:
            value = urljoin(base_url, value)

        if value in self.seen:
            return

        self.seen.add(value)

        candidate = Candidate(
            url=value,
            source=source,
            mime_type=mime,
            extension=detect_extension(value),
        )

        self.candidates.append(candidate)

    def is_blocked(self, response) -> bool:
        """Detect if fast fetch was blocked by anti-bot or challenge page."""
        if getattr(response, "status", None) in self.BLOCKED_STATUS_CODES:
            return True

        text = getattr(response, "text", "") or ""
        text_lower = text.lower()
        if any(keyword in text_lower for keyword in self.BLOCKED_KEYWORDS):
            return True

        return False

    def fetch_page(self):
        """
        Fetch page using fast Fetcher first; escalate to StealthyFetcher if blocked.
        """
        if not SCRAPLING_AVAILABLE:
            raise RuntimeError("Scrapling library is not installed in this environment.")

        print(f"[+] Scrapling scanner: fast fetching {self.url}...")
        try:
            response = Fetcher.get(self.url)
            if self.is_blocked(response):
                print("[!] Scrapling scanner: fast fetch blocked. Escalating to StealthyFetcher...")
                try:
                    stealth_resp = StealthyFetcher.fetch(self.url, headless=True)
                    if stealth_resp:
                        return stealth_resp
                except Exception as stealth_err:
                    print(f"[!] Scrapling StealthyFetcher escalation failed ({stealth_err}), using fast response.")
            return response
        except Exception as fast_error:
            print(f"[!] Scrapling fast fetch failed ({fast_error}). Attempting StealthyFetcher...")
            try:
                response = StealthyFetcher.fetch(self.url, headless=True)
                return response
            except Exception as stealth_error:
                print(f"[-] Scrapling StealthyFetcher failed: {stealth_error}")
                raise

    def scan_video_tags(self, page, base_url: str):
        """Scan <video> and child <source> tags using Scrapling CSS queries."""
        try:
            videos = page.css("video")
        except Exception:
            videos = []

        for video in videos:
            attrib = getattr(video, "attrib", {})
            for attr in self.ATTRIBUTES:
                val = attrib.get(attr)
                if val:
                    self.add(val, f"scrapling:video:{attr}", base_url)

            try:
                sources = video.css("source")
            except Exception:
                sources = []

            for source in sources:
                s_attrib = getattr(source, "attrib", {})
                val = s_attrib.get("src") or s_attrib.get("data-src")
                mime = s_attrib.get("type", "")
                if val:
                    self.add(val, "scrapling:source", base_url, mime)

    def scan_iframes(self, page, base_url: str):
        """Scan <iframe> tags for embedded players."""
        try:
            iframes = page.css("iframe")
        except Exception:
            iframes = []

        for iframe in iframes:
            attrib = getattr(iframe, "attrib", {})
            val = attrib.get("src") or attrib.get("data-src")
            if not val:
                continue

            lower = val.lower()
            if any(key in lower for key in ("video", "player", "embed", "stream")):
                self.add(val, "scrapling:iframe", base_url)

    def scan_attributes(self, page, base_url: str):
        """Scan common media attributes using Scrapling selector queries."""
        for attr in self.ATTRIBUTES:
            try:
                elements = page.css(f"[{attr}]")
            except Exception:
                continue

            for el in elements:
                attrib = getattr(el, "attrib", {})
                val = attrib.get(attr)
                if not val:
                    continue

                lower = val.lower()
                if detect_extension(val) or any(
                    key in lower for key in ("video", "stream", "playlist", "manifest", "media")
                ):
                    self.add(val, f"scrapling:attribute:{attr}", base_url)

    def scan_json_ld(self, page, base_url: str):
        """Scan application/ld+json script tags."""
        try:
            scripts = page.css('script[type="application/ld+json"]')
        except Exception:
            scripts = []

        for script in scripts:
            text = getattr(script, "text", "") or ""
            if not text:
                continue
            try:
                data = json.loads(text)
                self._scan_json_data(data, base_url, "scrapling:json-ld")
            except Exception:
                continue

    def _scan_json_data(self, value, base_url: str, source: str):
        if isinstance(value, dict):
            for k, v in value.items():
                if isinstance(v, str) and detect_extension(v):
                    self.add(v, f"{source}:{k}", base_url)
                else:
                    self._scan_json_data(v, base_url, source)
        elif isinstance(value, list):
            for item in value:
                self._scan_json_data(item, base_url, source)

    def scan_javascript(self, html: str, base_url: str):
        """Regex scanning for media stream patterns in page text/scripts."""
        patterns = [
            r"""["'](https?://[^"'<>\\\s]+)["']""",
            r"""["']([^"']+\.(?:mp4|webm|m4v|mov|ogv|ogg|avi|mkv|flv|f4v|wmv|3gp|3g2|ts|m2ts|mts|m3u8|mpd)(?:\?[^"']*)?)["']""",
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE | re.VERBOSE)
            for val in matches:
                resolved = urljoin(base_url, val)
                if detect_extension(resolved):
                    self.add(resolved, "scrapling:javascript")

    def scan_markdown_fallback(self, page, base_url: str):
        """Fallback to markdown extraction if DOM passes found no media candidates."""
        if self.candidates:
            return

        try:
            markdown_text = page.markdown()
        except Exception:
            markdown_text = ""

        if not markdown_text:
            return

        print("[+] Scrapling scanner: checking markdown text fallback...")
        md_patterns = [
            r"""\((https?://[^\s)]+)\)""",
            r"""(https?://[^\s)]+\.(?:mp4|webm|m3u8|mpd|m4v|mov|mkv)(?:\?[^\s)]*)?)""",
        ]

        for pattern in md_patterns:
            matches = re.findall(pattern, markdown_text, re.IGNORECASE)
            for val in matches:
                resolved = urljoin(base_url, val)
                if detect_extension(resolved):
                    self.add(resolved, "scrapling:markdown")

    def inspect(self):
        """Probe candidate URLs via HTTP HEAD to verify mime type and calculate final scores."""
        print(f"[+] Scrapling scanner: inspecting {len(self.candidates)} candidates...")
        for candidate in self.candidates:
            try:
                response = self.session.head(
                    candidate.url,
                    timeout=10,
                    allow_redirects=True,
                )
                candidate.status = response.status_code
                content_type = (
                    response.headers.get("Content-Type", "")
                    .split(";")[0]
                    .strip()
                    .lower()
                )
                if content_type:
                    candidate.mime_type = content_type

                if not candidate.extension:
                    candidate.extension = detect_extension(response.url)

                score_candidate(candidate)
            except requests.RequestException:
                score_candidate(candidate)

    def scan_html(self, html: str, base_url: str = None) -> list[Candidate]:
        """Scan raw HTML string using Scrapling's Selector engine without network calls."""
        if not SCRAPLING_AVAILABLE or Selector is None:
            raise RuntimeError("Scrapling library is not installed in this environment.")

        target_base = base_url or self.url
        page = Selector(html)

        self.scan_video_tags(page, target_base)
        self.scan_iframes(page, target_base)
        self.scan_attributes(page, target_base)
        self.scan_json_ld(page, target_base)
        self.scan_javascript(html, target_base)
        self.scan_markdown_fallback(page, target_base)

        for candidate in self.candidates:
            score_candidate(candidate)

        return sorted(
            self.candidates,
            key=lambda c: c.score,
            reverse=True,
        )

    def scan(self) -> list[Candidate]:
        """Execute full extraction pipeline and return sorted Candidates."""
        page = self.fetch_page()
        base_url = str(getattr(page, "url", self.url))
        html_content = getattr(page, "html_content", "") or getattr(page, "text", "") or ""

        self.scan_video_tags(page, base_url)
        self.scan_iframes(page, base_url)
        self.scan_attributes(page, base_url)
        self.scan_json_ld(page, base_url)
        self.scan_javascript(html_content, base_url)
        self.scan_markdown_fallback(page, base_url)

        self.inspect()

        return sorted(
            self.candidates,
            key=lambda c: c.score,
            reverse=True,
        )
