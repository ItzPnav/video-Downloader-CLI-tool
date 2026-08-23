import json
import os
import shutil

from candidate import (
    Candidate,
    detect_extension,
    score_candidate,
)


CHROMIUM_PATHS = [
    "/data/data/com.termux/files/usr/bin/chromium-browser",
    "/data/data/com.termux/files/usr/bin/chromium",
]

VIDEO_MIME = (
    "video/",
    "application/vnd.apple.mpegurl",
    "application/x-mpegurl",
    "application/dash+xml",
)


def find_chromium():

    for path in CHROMIUM_PATHS:
        if os.path.exists(path):
            return path

    for name in ("chromium-browser", "chromium"):
        found = shutil.which(name)

        if found:
            return found

    return None


def find_driver():

    for name in ("chromedriver", "chromium-driver"):
        found = shutil.which(name)

        if found:
            return found

    return None


class BrowserScanner:

    def __init__(self, url):

        self.url = url
        self.candidates = []
        self.seen = set()

    def add_candidate(self, url, mime="", source="browser"):

        if not url:
            return

        url = url.strip()

        if not url.startswith(("http://", "https://")):
            return

        if url in self.seen:
            return

        self.seen.add(url)

        candidate = Candidate(
            url=url,
            source=source,
            mime_type=mime or "",
            extension=detect_extension(url),
        )

        score_candidate(candidate)

        # Browser network traffic is strong evidence.
        candidate.score += 25

        if mime.lower().startswith("video/"):
            candidate.score += 50

        if any(
            token in mime.lower()
            for token in (
                "mpegurl",
                "dash+xml",
            )
        ):
            candidate.score += 50

        self.candidates.append(candidate)

    def scan(self):

        chromium = find_chromium()

        if not chromium:
            print(
                "[!] Chromium not found. "
                "Browser scanner skipped."
            )
            return []

        try:
            from selenium import webdriver
            from selenium.webdriver.chrome.options import Options
            from selenium.webdriver.chrome.service import Service

        except ImportError:
            print(
                "[!] Selenium is not installed. "
                "Browser scanner skipped."
            )
            return []

        driver_path = find_driver()

        options = Options()

        options.binary_location = chromium

        options.add_argument("--headless")
        options.add_argument("--no-sandbox")
        options.add_argument("--disable-dev-shm-usage")
        options.add_argument("--disable-gpu")
        options.add_argument("--disable-software-rasterizer")
        options.add_argument("--window-size=1280,720")

        options.set_capability(
            "goog:loggingPrefs",
            {
                "performance": "ALL",
            },
        )

        try:

            if driver_path:
                service = Service(driver_path)

                driver = webdriver.Chrome(
                    service=service,
                    options=options,
                )

            else:
                print(
                    "[!] chromedriver not found."
                )

                print(
                    "[!] Browser scanner skipped."
                )

                return []

            print()
            print(
                "[+] Browser scanner: "
                "launching Chromium..."
            )

            driver.get(self.url)

            print(
                "[+] Browser scanner: "
                "waiting for page..."
            )

            # Give JavaScript/video players time
            # to initialize.
            import time
            time.sleep(8)

            logs = driver.get_log("performance")

            for entry in logs:

                try:

                    message = json.loads(
                        entry["message"]
                    )["message"]

                except Exception:
                    continue

                if message.get("method") != (
                    "Network.responseReceived"
                ):
                    continue

                params = message.get(
                    "params",
                    {},
                )

                response = params.get(
                    "response",
                    {},
                )

                url = response.get("url", "")

                mime = response.get(
                    "mimeType",
                    "",
                )

                if not url:
                    continue

                lower_url = url.lower()
                lower_mime = mime.lower()

                interesting = (
                    lower_mime.startswith("video/")
                    or any(
                        ext in lower_url
                        for ext in (
                            ".mp4",
                            ".webm",
                            ".m4v",
                            ".mov",
                            ".m3u8",
                            ".mpd",
                            ".ts",
                            ".m2ts",
                            ".mkv",
                            ".flv",
                            ".3gp",
                        )
                    )
                    or any(
                        token in lower_mime
                        for token in (
                            "mpegurl",
                            "dash+xml",
                        )
                    )
                )

                if interesting:

                    self.add_candidate(
                        url,
                        mime,
                        "browser-network",
                    )

            try:
                driver.quit()
            except Exception:
                pass

        except Exception as error:

            print(
                f"[!] Browser scanner error: {error}"
            )

            try:
                driver.quit()
            except Exception:
                pass

            return []

        self.candidates.sort(
            key=lambda x: x.score,
            reverse=True,
        )

        print(
            f"[+] Browser scanner found "
            f"{len(self.candidates)} candidates."
        )

        return self.candidates
