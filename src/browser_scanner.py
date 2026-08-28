import json
import os
import shutil
import time

from urllib.parse import urljoin

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


MEDIA_EXTENSIONS = (
    ".mp4",
    ".webm",
    ".m4v",
    ".mov",
    ".ogv",
    ".mpeg",
    ".mpg",
    ".m2ts",
    ".mts",
    ".ts",
    ".3gp",
    ".3g2",
    ".flv",
    ".m3u8",
    ".mpd",
)


def find_chromium():

    for path in CHROMIUM_PATHS:

        if os.path.exists(path):
            return path

    for name in (
        "chromium-browser",
        "chromium",
    ):

        found = shutil.which(name)

        if found:
            return found

    return None


def find_driver():

    for name in (
        "chromedriver",
        "chromium-driver",
    ):

        found = shutil.which(name)

        if found:
            return found

    return None


class BrowserScanner:

    def __init__(self, url):

        self.url = url

        self.candidates = []

        self.seen = set()

        self.tabs_seen = set()

    # ========================================================
    # CANDIDATES
    # ========================================================

    def add_candidate(
        self,
        url,
        mime="",
        source="browser",
        metadata=None,
    ):

        if not url:
            return

        url = url.strip()

        if not url.startswith(
            (
                "http://",
                "https://",
            )
        ):
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

        if metadata:
            candidate.metadata.update(
                metadata
            )

        score_candidate(
            candidate
        )

        # Browser-observed resources are
        # stronger evidence than strings
        # found in raw HTML.
        candidate.score += 25

        lower_mime = (
            mime or ""
        ).lower()

        lower_url = url.lower()

        if lower_mime.startswith(
            "video/"
        ):

            candidate.score += 50

        if any(
            token in lower_mime
            for token in (
                "mpegurl",
                "dash+xml",
            )
        ):

            candidate.score += 50

        # Prefer resources from the
        # actual player tab.
        if metadata and metadata.get(
            "player_tab"
        ):

            candidate.score += 35

        # Direct video resources are
        # generally stronger than arbitrary
        # page resources.
        if candidate.is_direct_video:

            candidate.score += 20

        if candidate.is_stream:

            candidate.score += 15

        # Penalize obvious non-main resources.
        negative_tokens = (
            "thumbnail",
            "thumb",
            "poster",
            "preview",
            "sprite",
            "avatar",
            "logo",
            "tracking",
            "analytics",
            "pixel",
            "advert",
            "banner",
        )

        if any(
            token in lower_url
            for token in negative_tokens
        ):

            candidate.score -= 60

        self.candidates.append(
            candidate
        )

    # ========================================================
    # NETWORK LOGS
    # ========================================================

    def collect_network(
        self,
        driver,
        player_tab=False,
    ):

        try:

            logs = driver.get_log(
                "performance"
            )

        except Exception:

            return

        for entry in logs:

            try:

                message = json.loads(
                    entry["message"]
                )["message"]

            except Exception:

                continue

            if message.get(
                "method"
            ) != "Network.responseReceived":

                continue

            params = message.get(
                "params",
                {}
            )

            response = params.get(
                "response",
                {}
            )

            url = response.get(
                "url",
                ""
            )

            mime = response.get(
                "mimeType",
                ""
            )

            if not url:
                continue

            lower_url = url.lower()
            lower_mime = mime.lower()

            interesting = (
                lower_mime.startswith(
                    "video/"
                )
                or any(
                    ext in lower_url
                    for ext in MEDIA_EXTENSIONS
                )
                or any(
                    token in lower_mime
                    for token in (
                        "mpegurl",
                        "dash+xml",
                    )
                )
            )

            if not interesting:
                continue

            self.add_candidate(
                url,
                mime,
                "browser-network",
                {
                    "player_tab": player_tab,
                    "status": response.get(
                        "status"
                    ),
                },
            )

    # ========================================================
    # HTML5 VIDEO ELEMENTS
    # ========================================================

    def inspect_video_elements(
        self,
        driver,
        player_tab=False,
    ):

        try:

            videos = driver.find_elements(
                "tag name",
                "video"
            )

        except Exception:

            return

        for video in videos:

            try:

                src = driver.execute_script(
                    """
                    return arguments[0].currentSrc
                        || arguments[0].src
                        || "";
                    """,
                    video,
                )

                if src:

                    self.add_candidate(
                        src,
                        "video/*",
                        "video-element",
                        {
                            "player_tab": player_tab,
                        },
                    )

                sources = video.find_elements(
                    "tag name",
                    "source"
                )

                for source in sources:

                    source_url = (
                        source.get_attribute(
                            "src"
                        )
                    )

                    source_type = (
                        source.get_attribute(
                            "type"
                        )
                        or "video/*"
                    )

                    if source_url:

                        source_url = urljoin(
                            driver.current_url,
                            source_url,
                        )

                        self.add_candidate(
                            source_url,
                            source_type,
                            "video-source",
                            {
                                "player_tab":
                                    player_tab,
                            },
                        )

            except Exception:

                continue

    # ========================================================
    # GENERIC SOURCE ELEMENTS
    # ========================================================

    def inspect_sources(
        self,
        driver,
        player_tab=False,
    ):

        try:

            sources = driver.find_elements(
                "tag name",
                "source"
            )

        except Exception:

            return

        for source in sources:

            try:

                src = source.get_attribute(
                    "src"
                )

                mime = (
                    source.get_attribute(
                        "type"
                    )
                    or ""
                )

                if not src:
                    continue

                src = urljoin(
                    driver.current_url,
                    src,
                )

                self.add_candidate(
                    src,
                    mime,
                    "source-element",
                    {
                        "player_tab":
                            player_tab,
                    },
                )

            except Exception:

                continue

    # ========================================================
    # PERFORMANCE RESOURCE API
    # ========================================================

    def inspect_performance_resources(
        self,
        driver,
        player_tab=False,
    ):

        try:

            resources = driver.execute_script(
                """
                return performance
                    .getEntriesByType('resource')
                    .map(x => ({
                        name: x.name,
                        duration: x.duration,
                        transferSize:
                            x.transferSize || 0
                    }));
                """
            )

        except Exception:

            return

        for resource in resources:

            url = resource.get(
                "name",
                ""
            )

            lower = url.lower()

            if not any(
                ext in lower
                for ext in MEDIA_EXTENSIONS
            ):

                continue

            self.add_candidate(
                url,
                "",
                "performance-resource",
                {
                    "player_tab":
                        player_tab,
                    "duration":
                        resource.get(
                            "duration"
                        ),
                    "transfer_size":
                        resource.get(
                            "transferSize"
                        ),
                },
            )

    # ========================================================
    # TAB INSPECTION
    # ========================================================

    def inspect_tab(
        self,
        driver,
        player_tab=False,
    ):

        current = driver.current_window_handle

        self.tabs_seen.add(
            current
        )

        print(
            f"[+] Inspecting tab "
            f"{len(self.tabs_seen)}"
        )

        try:

            print(
                f"    URL   : "
                f"{driver.current_url}"
            )

        except Exception:

            pass

        try:

            print(
                f"    Title : "
                f"{driver.title}"
            )

        except Exception:

            pass

        # Let dynamically-created player
        # elements initialize.
        time.sleep(2)

        self.inspect_video_elements(
            driver,
            player_tab
        )

        self.inspect_sources(
            driver,
            player_tab
        )

        self.inspect_performance_resources(
            driver,
            player_tab
        )

        self.collect_network(
            driver,
            player_tab
        )

    # ========================================================
    # NEW TAB DETECTION
    # ========================================================

    def inspect_new_tabs(
        self,
        driver,
        original_handles,
    ):

        try:

            current_handles = set(
                driver.window_handles
            )

        except Exception:

            return

        new_handles = (
            current_handles
            - original_handles
        )

        for handle in new_handles:

            if handle in self.tabs_seen:
                continue

            print()
            print(
                "[+] New browser tab detected."
            )

            try:

                driver.switch_to.window(
                    handle
                )

                self.inspect_tab(
                    driver,
                    player_tab=True
                )

                # Give the new page a little
                # extra time for player/network
                # initialization.
                time.sleep(3)

                self.collect_network(
                    driver,
                    player_tab=True
                )

                self.inspect_performance_resources(
                    driver,
                    player_tab=True
                )

            except Exception as error:

                print(
                    f"[!] Could not inspect "
                    f"new tab: {error}"
                )

            finally:

                try:

                    driver.switch_to.window(
                        list(
                            original_handles
                        )[0]
                    )

                except Exception:

                    pass

    # ========================================================
    # MAIN SCANNER
    # ========================================================

    def scan(self):

        chromium = find_chromium()

        if not chromium:

            print(
                "[!] Chromium not found."
            )

            return []

        try:

            from selenium import webdriver
            from selenium.webdriver.chrome.options import (
                Options
            )
            from selenium.webdriver.chrome.service import (
                Service
            )

        except ImportError:

            print(
                "[!] Selenium is not installed."
            )

            return []

        driver_path = find_driver()

        if not driver_path:

            print(
                "[!] chromedriver not found."
            )

            return []

        options = Options()

        options.binary_location = chromium

        options.add_argument(
            "--headless"
        )

        options.add_argument(
            "--no-sandbox"
        )

        options.add_argument(
            "--disable-dev-shm-usage"
        )

        options.add_argument(
            "--disable-gpu"
        )

        options.add_argument(
            "--disable-software-rasterizer"
        )

        options.add_argument(
            "--window-size=1280,720"
        )

        options.set_capability(
            "goog:loggingPrefs",
            {
                "performance": "ALL",
            },
        )

        driver = None

        try:

            service = Service(
                driver_path
            )

            driver = webdriver.Chrome(
                service=service,
                options=options,
            )

            print()
            print(
                "[+] Browser scanner: "
                "launching Chromium..."
            )

            driver.set_page_load_timeout(
                45
            )

            driver.get(
                self.url
            )

            print(
                "[+] Browser scanner: "
                "waiting for page..."
            )

            # ------------------------------------------------
            # Initial page
            # ------------------------------------------------

            time.sleep(5)

            original_handles = set(
                driver.window_handles
            )

            self.inspect_tab(
                driver,
                player_tab=False
            )

            # ------------------------------------------------
            # Detect any tabs/windows that
            # were opened automatically.
            # ------------------------------------------------

            self.inspect_new_tabs(
                driver,
                original_handles
            )

            # ------------------------------------------------
            # One final network collection.
            # ------------------------------------------------

            try:

                driver.switch_to.window(
                    driver.window_handles[-1]
                )

                self.collect_network(
                    driver,
                    player_tab=True
                )

                self.inspect_video_elements(
                    driver,
                    player_tab=True
                )

            except Exception:

                pass

        except Exception as error:

            print(
                f"[!] Browser scanner error: "
                f"{error}"
            )

            return []

        finally:

            if driver:

                try:

                    driver.quit()

                except Exception:

                    pass

        # ----------------------------------------------------
        # Final ordering
        # ----------------------------------------------------

        self.candidates.sort(
            key=lambda candidate: (
                candidate.score,
                getattr(
                    candidate,
                    "height",
                    0
                ) or 0,
                getattr(
                    candidate,
                    "width",
                    0
                ) or 0,
            ),
            reverse=True,
        )

        print()
        print(
            f"[+] Browser scanner found "
            f"{len(self.candidates)} "
            f"candidate(s)."
        )

        for index, candidate in enumerate(
            self.candidates[:10],
            1
        ):

            print(
                f"    [{index}] "
                f"{candidate.label:<7} "
                f"score={candidate.score:<4} "
                f"{candidate.url[:100]}"
            )

        return self.candidates
