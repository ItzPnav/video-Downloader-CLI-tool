import os
import re
import sys
import json
import subprocess
from urllib.parse import urljoin, urlparse

import requests
from bs4 import BeautifulSoup


VIDEO_EXTENSIONS = (
    ".mp4",
    ".webm",
    ".mov",
    ".m4v",
    ".avi",
    ".mkv",
)

VIDEO_MIME_TYPES = (
    "video/mp4",
    "video/webm",
    "video/ogg",
    "video/mpeg",
    "application/x-mpegURL",
    "application/vnd.apple.mpegurl",
)


class VideoExtractor:

    def __init__(self, url, output_dir="videos"):
        self.url = url
        self.output_dir = output_dir

        self.session = requests.Session()

        self.session.headers.update({
            "User-Agent": (
                "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
                "AppleWebKit/537.36 (KHTML, like Gecko) "
                "Chrome/139.0.0.0 Safari/537.36"
            ),
            "Accept": (
                "text/html,application/xhtml+xml,"
                "application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8"
            ),
            "Accept-Language": "en-US,en;q=0.9",
        })

        os.makedirs(self.output_dir, exist_ok=True)

    # ---------------------------------------------------------
    # Basic URL validation
    # ---------------------------------------------------------

    def validate_url(self):
        parsed = urlparse(self.url)

        if parsed.scheme not in ("http", "https"):
            raise ValueError("Only HTTP/HTTPS URLs are supported.")

        if not parsed.netloc:
            raise ValueError("Invalid URL.")

    # ---------------------------------------------------------
    # Download page
    # ---------------------------------------------------------

    def fetch_page(self):
        print("[+] Fetching page...")

        response = self.session.get(
            self.url,
            timeout=20,
            allow_redirects=True
        )

        response.raise_for_status()

        print(f"[+] HTTP {response.status_code}")
        print(f"[+] Final URL: {response.url}")

        return response.text, response.url

    # ---------------------------------------------------------
    # Extract <video> and <source>
    # ---------------------------------------------------------

    def extract_html_videos(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        candidates = []

        # <video src="...">
        for video in soup.find_all("video"):
            src = video.get("src")

            if src:
                candidates.append({
                    "url": urljoin(base_url, src),
                    "type": "video-tag"
                })

            # <video><source src="..."></video>
            for source in video.find_all("source"):
                src = source.get("src")

                if src:
                    candidates.append({
                        "url": urljoin(base_url, src),
                        "type": "source-tag",
                        "mime": source.get("type")
                    })

        # Standalone <source>
        for source in soup.find_all("source"):
            src = source.get("src")

            if src:
                candidates.append({
                    "url": urljoin(base_url, src),
                    "type": "source-tag",
                    "mime": source.get("type")
                })

        return candidates

    # ---------------------------------------------------------
    # Extract URLs embedded inside HTML/JS
    # ---------------------------------------------------------

    def extract_embedded_urls(self, html, base_url):
        candidates = []

        patterns = [
            # MP4/WebM/etc.
            r'https?://[^\'"\s<>]+?\.(?:mp4|webm|mov|m4v|avi|mkv)(?:\?[^\'"\s<>]*)?',

            # Relative media URLs
            r'["\']([^"\']+\.(?:mp4|webm|mov|m4v|avi|mkv)(?:\?[^"\']*)?)["\']',

            # HLS
            r'https?://[^\'"\s<>]+?\.m3u8(?:\?[^\'"\s<>]*)?',

            # DASH
            r'https?://[^\'"\s<>]+?\.mpd(?:\?[^\'"\s<>]*)?',
        ]

        for pattern in patterns:
            matches = re.findall(pattern, html, re.IGNORECASE)

            for match in matches:
                if isinstance(match, tuple):
                    match = match[0]

                candidates.append({
                    "url": urljoin(base_url, match),
                    "type": "embedded"
                })

        return candidates

    # ---------------------------------------------------------
    # JSON-LD / structured metadata
    # ---------------------------------------------------------

    def extract_json_ld(self, html, base_url):
        soup = BeautifulSoup(html, "html.parser")

        candidates = []

        for script in soup.find_all(
            "script",
            attrs={"type": "application/ld+json"}
        ):
            try:
                data = json.loads(script.string or "")
            except Exception:
                continue

            objects = data if isinstance(data, list) else [data]

            for obj in objects:
                if not isinstance(obj, dict):
                    continue

                possible_fields = [
                    "contentUrl",
                    "embedUrl",
                    "url"
                ]

                for field in possible_fields:
                    value = obj.get(field)

                    if not isinstance(value, str):
                        continue

                    if (
                        ".mp4" in value.lower()
                        or ".webm" in value.lower()
                        or ".m3u8" in value.lower()
                        or ".mpd" in value.lower()
                    ):
                        candidates.append({
                            "url": urljoin(base_url, value),
                            "type": f"json-ld:{field}"
                        })

        return candidates

    # ---------------------------------------------------------
    # Inspect URL without downloading the entire video
    # ---------------------------------------------------------

    def inspect_candidate(self, candidate_url):
        try:
            response = self.session.head(
                candidate_url,
                timeout=10,
                allow_redirects=True
            )

            content_type = response.headers.get(
                "Content-Type",
                ""
            ).lower()

            content_length = response.headers.get(
                "Content-Length"
            )

            return {
                "url": candidate_url,
                "content_type": content_type,
                "content_length": content_length,
                "valid": (
                    content_type.startswith("video/")
                    or "mpegurl" in content_type
                    or "dash+xml" in content_type
                    or self.looks_like_video_url(candidate_url)
                )
            }

        except requests.RequestException:
            return {
                "url": candidate_url,
                "content_type": "",
                "content_length": None,
                "valid": self.looks_like_video_url(candidate_url)
            }

    # ---------------------------------------------------------
    # Extension-based detection
    # ---------------------------------------------------------

    def looks_like_video_url(self, url):
        path = urlparse(url).path.lower()

        return (
            path.endswith(VIDEO_EXTENSIONS)
            or path.endswith(".m3u8")
            or path.endswith(".mpd")
        )

    # ---------------------------------------------------------
    # Remove duplicate URLs
    # ---------------------------------------------------------

    def deduplicate(self, candidates):
        seen = set()
        result = []

        for candidate in candidates:
            url = candidate["url"]

            if url in seen:
                continue

            seen.add(url)
            result.append(candidate)

        return result

    # ---------------------------------------------------------
    # yt-dlp fallback
    # ---------------------------------------------------------

    def ytdlp_extract(self):
        print("[+] Trying yt-dlp...")

        try:
            result = subprocess.run(
                [
                    sys.executable,
                    "-m",
                    "yt_dlp",
                    "--dump-single-json",
                    "--no-warnings",
                    self.url
                ],
                capture_output=True,
                text=True,
                timeout=60
            )

            if result.returncode != 0:
                print("[-] yt-dlp could not extract this page.")
                return None

            data = json.loads(result.stdout)

            formats = data.get("formats", [])

            videos = []

            for fmt in formats:
                video_url = fmt.get("url")

                if not video_url:
                    continue

                if fmt.get("vcodec") == "none":
                    continue

                videos.append({
                    "url": video_url,
                    "format": fmt.get("ext"),
                    "quality": fmt.get("format_note"),
                    "height": fmt.get("height"),
                    "width": fmt.get("width"),
                    "fps": fmt.get("fps"),
                    "filesize": fmt.get("filesize"),
                    "protocol": fmt.get("protocol"),
                })

            return {
                "title": data.get("title"),
                "duration": data.get("duration"),
                "thumbnail": data.get("thumbnail"),
                "formats": videos
            }

        except (
            subprocess.SubprocessError,
            json.JSONDecodeError,
            FileNotFoundError
        ) as e:
            print(f"[-] yt-dlp error: {e}")
            return None

    # ---------------------------------------------------------
    # Download direct video
    # ---------------------------------------------------------

    def download_direct(self, video_url, filename=None):
        print(f"[+] Downloading: {video_url}")

        if not filename:
            filename = "video.mp4"

        output_path = os.path.join(
            self.output_dir,
            filename
        )

        with self.session.get(
            video_url,
            stream=True,
            timeout=30
        ) as response:

            response.raise_for_status()

            total = int(
                response.headers.get(
                    "Content-Length",
                    0
                )
            )

            downloaded = 0

            with open(output_path, "wb") as file:

                for chunk in response.iter_content(
                    chunk_size=1024 * 1024
                ):
                    if not chunk:
                        continue

                    file.write(chunk)
                    downloaded += len(chunk)

                    if total:
                        percent = downloaded * 100 / total
                        print(
                            f"\r[+] {percent:.1f}%",
                            end=""
                        )

        print()
        print(f"[+] Saved: {output_path}")

        return output_path

    # ---------------------------------------------------------
    # Main extraction pipeline
    # ---------------------------------------------------------

    def extract(self):
        self.validate_url()

        html, base_url = self.fetch_page()

        candidates = []

        print("[+] Searching HTML <video> elements...")
        candidates.extend(
            self.extract_html_videos(
                html,
                base_url
            )
        )

        print("[+] Searching embedded URLs...")
        candidates.extend(
            self.extract_embedded_urls(
                html,
                base_url
            )
        )

        print("[+] Searching JSON-LD metadata...")
        candidates.extend(
            self.extract_json_ld(
                html,
                base_url
            )
        )

        candidates = self.deduplicate(candidates)

        print(
            f"[+] Found {len(candidates)} possible candidates."
        )

        valid_candidates = []

        for candidate in candidates:

            result = self.inspect_candidate(
                candidate["url"]
            )

            if result["valid"]:
                candidate.update(result)
                valid_candidates.append(candidate)

        # -----------------------------------------------------
        # Direct HTML extraction succeeded
        # -----------------------------------------------------

        if valid_candidates:

            print("\n[+] VIDEO CANDIDATES\n")

            for index, candidate in enumerate(
                valid_candidates,
                start=1
            ):
                print(
                    f"[{index}] "
                    f"{candidate['type']}"
                )
                print(
                    f"    {candidate['url']}"
                )
                print(
                    f"    Type: "
                    f"{candidate.get('content_type', 'unknown')}"
                )
                print()

            return valid_candidates

        # -----------------------------------------------------
        # Fallback to yt-dlp
        # -----------------------------------------------------

        print(
            "[-] No obvious video URL found."
        )

        ytdlp_result = self.ytdlp_extract()

        if ytdlp_result:
            print(
                f"[+] Title: "
                f"{ytdlp_result.get('title')}"
            )

            print(
                f"[+] Formats found: "
                f"{len(ytdlp_result['formats'])}"
            )

            return ytdlp_result

        print(
            "[-] Could not extract a video."
        )

        return None


def main():

    if len(sys.argv) < 2:
        print(
            "Usage:\n"
            "    python video_extractor.py <URL>"
        )
        sys.exit(1)

    url = sys.argv[1]

    extractor = VideoExtractor(url)

    try:
        result = extractor.extract()

        if result:
            print("\n[+] Extraction complete.")

    except KeyboardInterrupt:
        print("\n[!] Cancelled.")

    except Exception as e:
        print(
            f"\n[!] Error: {e}"
        )


if __name__ == "__main__":
    main()
