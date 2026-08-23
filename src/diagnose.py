import re
import sys
import socket
import subprocess
from urllib.parse import urljoin, urlparse

import requests


VIDEO_EXTENSIONS = (
    ".mp4",
    ".webm",
    ".m4v",
    ".mov",
    ".avi",
    ".mkv",
    ".ts",
    ".m3u8",
)

MEDIA_PATTERNS = [
    r'https?://[^"\']+\.m3u8[^"\']*',
    r'https?://[^"\']+\.mp4[^"\']*',
    r'https?://[^"\']+\.webm[^"\']*',
    r'https?://[^"\']+\.m4v[^"\']*',
]


def line():
    print("-" * 60)


def check_dns(host):
    print("[1] DNS")

    try:
        addresses = socket.getaddrinfo(
            host,
            443,
            type=socket.SOCK_STREAM
        )

        ips = sorted({
            item[4][0]
            for item in addresses
        })

        print(f"    ✓ Resolved: {', '.join(ips)}")

        return True

    except Exception as e:

        print(f"    ✗ DNS failed: {e}")

        return False


def fetch_page(url):

    print()
    print("[2] HTTPS request")

    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Linux; Android 13) "
            "AppleWebKit/537.36 "
            "(KHTML, like Gecko) "
            "Chrome/131.0 Mobile Safari/537.36"
        ),
        "Accept": (
            "text/html,application/xhtml+xml,"
            "application/xml;q=0.9,*/*;q=0.8"
        ),
        "Accept-Language": "en-US,en;q=0.9",
    }

    try:

        response = requests.get(
            url,
            headers=headers,
            timeout=15,
            allow_redirects=True
        )

        print(
            f"    ✓ HTTP {response.status_code}"
        )

        print(
            f"    ✓ Final URL: {response.url}"
        )

        print(
            f"    ✓ Content-Type: "
            f"{response.headers.get('content-type', '?')}"
        )

        print(
            f"    ✓ Size: "
            f"{len(response.content):,} bytes"
        )

        return response

    except requests.exceptions.Timeout:

        print(
            "    ✗ HTTPS request timed out."
        )

    except requests.exceptions.ConnectionError as e:

        print(
            f"    ✗ Connection failed: {e}"
        )

    except Exception as e:

        print(
            f"    ✗ Request failed: {e}"
        )

    return None


def inspect_html(html, base_url):

    print()
    print("[3] HTML inspection")

    if not html:

        print("    ✗ Empty response")

        return

    text = html.decode(
        "utf-8",
        errors="ignore"
    )

    print(
        f"    ✓ HTML characters: {len(text):,}"
    )

    # --------------------------------------------------------
    # VIDEO TAGS
    # --------------------------------------------------------

    videos = re.findall(
        r"<video\b[^>]*>",
        text,
        flags=re.I
    )

    print(
        f"    video tags: {len(videos)}"
    )

    for tag in videos[:10]:

        print(
            "      VIDEO:",
            tag[:300]
        )

    # --------------------------------------------------------
    # SOURCE TAGS
    # --------------------------------------------------------

    sources = re.findall(
        r"<source\b[^>]*>",
        text,
        flags=re.I
    )

    print(
        f"    source tags: {len(sources)}"
    )

    for tag in sources[:20]:

        print(
            "      SOURCE:",
            tag[:300]
        )

    # --------------------------------------------------------
    # IFRAME
    # --------------------------------------------------------

    iframes = re.findall(
        r"<iframe\b[^>]*>",
        text,
        flags=re.I
    )

    print(
        f"    iframe tags: {len(iframes)}"
    )

    for tag in iframes[:20]:

        print(
            "      IFRAME:",
            tag[:300]
        )

    # --------------------------------------------------------
    # MEDIA URLS
    # --------------------------------------------------------

    print()
    print("[4] Media URL patterns")

    found = set()

    for pattern in MEDIA_PATTERNS:

        for match in re.findall(
            pattern,
            text,
            flags=re.I
        ):

            absolute = urljoin(
                base_url,
                match
            )

            found.add(absolute)

    if found:

        for url in sorted(found):

            print(
                f"    ✓ {url[:500]}"
            )

    else:

        print(
            "    ✗ No obvious MP4/WebM/HLS URL "
            "found in raw HTML."
        )

    # --------------------------------------------------------
    # PLAYER KEYWORDS
    # --------------------------------------------------------

    print()
    print("[5] Player indicators")

    keywords = [
        "videojs",
        "jwplayer",
        "plyr",
        "flowplayer",
        "mediaelement",
        "hls",
        "m3u8",
        "dash",
        "mpd",
        "player",
        "video",
        "source",
    ]

    lower = text.lower()

    for keyword in keywords:

        count = lower.count(keyword)

        if count:

            print(
                f"    {keyword:<15} {count}"
            )


def run_ytdlp(url):

    print()
    print("[6] yt-dlp capability test")

    try:

        result = subprocess.run(
            [
                "yt-dlp",
                "--no-warnings",
                "--skip-download",
                "--dump-single-json",
                url
            ],
            capture_output=True,
            text=True,
            timeout=60
        )

        if result.returncode == 0:

            import json

            info = json.loads(
                result.stdout
            )

            print(
                "    ✓ yt-dlp recognized the URL"
            )

            print(
                f"    Title: "
                f"{info.get('title', '?')}"
            )

            formats = info.get(
                "formats",
                []
            )

            print(
                f"    Formats: {len(formats)}"
            )

            for fmt in formats[-10:]:

                print(
                    "      "
                    f"id={fmt.get('format_id')} "
                    f"ext={fmt.get('ext')} "
                    f"height={fmt.get('height')} "
                    f"protocol={fmt.get('protocol')}"
                )

            return

        print(
            "    ✗ yt-dlp did not extract media."
        )

        stderr = result.stderr.strip()

        if stderr:

            print()
            print("    yt-dlp message:")

            for line_ in stderr.splitlines()[-15:]:

                print(
                    f"      {line_}"
                )

    except FileNotFoundError:

        print(
            "    ✗ yt-dlp is not installed."
        )

    except subprocess.TimeoutExpired:

        print(
            "    ✗ yt-dlp timed out."
        )

    except Exception as e:

        print(
            f"    ✗ yt-dlp test failed: {e}"
        )


def main():

    if len(sys.argv) != 2:

        print(
            'Usage: python src/diagnose.py "URL"'
        )

        return 1

    url = sys.argv[1]

    parsed = urlparse(url)

    if parsed.scheme not in (
        "http",
        "https"
    ):

        print(
            "✗ URL must start with http:// or https://"
        )

        return 1

    print()
    print("=" * 60)
    print("             VIDEO EXTRACTION DIAGNOSTIC")
    print("=" * 60)

    print()
    print(f"URL: {url}")

    host = parsed.hostname

    print(f"Host: {host}")

    line()

    if not check_dns(host):

        return 1

    response = fetch_page(url)

    if response:

        inspect_html(
            response.content,
            response.url
        )

    else:

        print()
        print(
            "[!] Raw HTTPS request failed."
        )

        print(
            "    This does NOT necessarily mean "
            "the browser cannot access it."
        )

    run_ytdlp(url)

    print()
    line()

    print("DIAGNOSIS")

    if response is None:

        print(
            "  → First blocker: direct HTTPS access."
        )

        print(
            "  → Next investigation: Chromium/network layer."
        )

    else:

        print(
            "  → HTTPS access works."
        )

        print(
            "  → Check the media/yt-dlp results above "
            "to identify the next layer."
        )

    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
