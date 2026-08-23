import json
import re
from urllib.parse import urljoin

import requests
from bs4 import BeautifulSoup

from candidate import (
    Candidate,
    detect_extension,
    score_candidate,
)


class StaticScanner:

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

    def __init__(self, url):

        self.url = url
        self.candidates = []
        self.seen = set()

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

    def add(self, value, source, base_url=None, mime=""):

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

    def fetch(self):

        print("[+] Static scanner: fetching page...")

        response = self.session.get(
            self.url,
            timeout=30,
            allow_redirects=True,
        )

        response.raise_for_status()

        return response.text, response.url

    def scan_video_tags(self, soup, base_url):

        for video in soup.find_all("video"):

            for attr in self.ATTRIBUTES:

                value = video.get(attr)

                if value:
                    self.add(
                        value,
                        f"video:{attr}",
                        base_url,
                    )

            for source in video.find_all("source"):

                value = (
                    source.get("src")
                    or source.get("data-src")
                )

                mime = source.get("type", "")

                self.add(
                    value,
                    "source",
                    base_url,
                    mime,
                )

    def scan_iframes(self, soup, base_url):

        for iframe in soup.find_all("iframe"):

            value = (
                iframe.get("src")
                or iframe.get("data-src")
            )

            if not value:
                continue

            lower = value.lower()

            if any(
                key in lower
                for key in (
                    "video",
                    "player",
                    "embed",
                    "stream",
                )
            ):
                self.add(
                    value,
                    "iframe",
                    base_url,
                )

    def scan_attributes(self, soup, base_url):

        for tag in soup.find_all(True):

            for attr in self.ATTRIBUTES:

                value = tag.get(attr)

                if not value:
                    continue

                lower = value.lower()

                if (
                    detect_extension(value)
                    or any(
                        key in lower
                        for key in (
                            "video",
                            "stream",
                            "playlist",
                            "manifest",
                            "media",
                        )
                    )
                ):
                    self.add(
                        value,
                        f"attribute:{attr}",
                        base_url,
                    )

    def scan_json_ld(self, soup, base_url):

        for script in soup.find_all(
            "script",
            attrs={"type": "application/ld+json"},
        ):

            try:
                data = json.loads(
                    script.string or ""
                )

            except Exception:
                continue

            self.scan_json(
                data,
                base_url,
                "json-ld",
            )

    def scan_json(self, value, base_url, source):

        if isinstance(value, dict):

            for key, item in value.items():

                if isinstance(item, str):

                    if detect_extension(item):

                        self.add(
                            item,
                            f"{source}:{key}",
                            base_url,
                        )

                else:
                    self.scan_json(
                        item,
                        base_url,
                        source,
                    )

        elif isinstance(value, list):

            for item in value:

                self.scan_json(
                    item,
                    base_url,
                    source,
                )

    def scan_javascript(self, html, base_url):

        patterns = [
            r"""["'](https?://[^"'<>\\\s]+)["']""",

            r"""["']([^"']+\.(?:
                mp4|webm|m4v|mov|ogv|ogg|
                avi|mkv|flv|f4v|wmv|
                3gp|3g2|ts|m2ts|mts|
                m3u8|mpd
            )(?:\?[^"']*)?)["']""",
        ]

        for pattern in patterns:

            matches = re.findall(
                pattern,
                html,
                re.IGNORECASE | re.VERBOSE,
            )

            for value in matches:

                value = urljoin(
                    base_url,
                    value,
                )

                if detect_extension(value):

                    self.add(
                        value,
                        "javascript",
                    )

    def inspect(self):

        print(
            f"[+] Inspecting "
            f"{len(self.candidates)} candidates..."
        )

        for candidate in self.candidates:

            try:

                response = self.session.head(
                    candidate.url,
                    timeout=10,
                    allow_redirects=True,
                )

                candidate.status = (
                    response.status_code
                )

                content_type = (
                    response.headers
                    .get("Content-Type", "")
                    .split(";")[0]
                    .strip()
                    .lower()
                )

                if content_type:
                    candidate.mime_type = content_type

                if not candidate.extension:
                    candidate.extension = (
                        detect_extension(
                            response.url
                        )
                    )

                score_candidate(candidate)

            except requests.RequestException:

                score_candidate(candidate)

    def scan(self):

        html, base_url = self.fetch()

        print("[+] Static scanner: HTML")

        soup = BeautifulSoup(
            html,
            "html.parser",
        )

        self.scan_video_tags(
            soup,
            base_url,
        )

        self.scan_iframes(
            soup,
            base_url,
        )

        self.scan_attributes(
            soup,
            base_url,
        )

        self.scan_json_ld(
            soup,
            base_url,
        )

        self.scan_javascript(
            html,
            base_url,
        )

        self.inspect()

        return sorted(
            self.candidates,
            key=lambda x: x.score,
            reverse=True,
        )
